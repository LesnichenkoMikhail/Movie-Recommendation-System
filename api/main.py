import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from api.guards import require_user
from api.routers import analytics, quality
from api.schemas import FeedbackIn, InteractionIn, RatingIn, UserCreate
from api.services import adjust_genres, ensure_movie, ensure_user
from core.decorators import TIMINGS
from database.connection import Base, engine, get_db
from database.models import (
    Genre, Interaction, Movie, Rating, Recommendation, RecommendationFeedback, User, UserGenrePreference, utcnow,
)
from recommender.config import (
    ACTION_DELTAS, ACTIONS, FEEDBACK_DELTA_FACTOR, FEEDBACK_NEUTRAL, INITIAL_PREFERENCE, MAX_LIMIT, MODELS,
    PREFERENCE_MAX, PREFERENCE_STEP, RATING_DELTA_FACTOR, RATING_NEUTRAL,
)
from recommender.engine import recommend
from recommender.payload import movie_payload

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Movie Recommender API",
    version="2.0.0",
    description="Персональные рекомендации фильмов на основе каталога и поведения пользователей.",
    lifespan=lifespan,
)
app.include_router(analytics.router)
app.include_router(quality.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models")
def list_models():
    return [{"key": key, "label": label} for key, label in MODELS.items()]


@app.get("/metrics")
def metrics():
    return {
        name: {
            "calls": entry["calls"],
            "last_ms": round(entry["last_ms"], 2),
            "avg_ms": round(entry["total_ms"] / entry["calls"], 2) if entry["calls"] else 0.0,
        }
        for name, entry in TIMINGS.items()
    }


@app.get("/genres")
def list_genres(db: Session = Depends(get_db)):
    return [genre.name for genre in db.scalars(select(Genre).order_by(Genre.name)).all()]


@app.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Имя профиля не может быть пустым")
    user = db.scalar(select(User).where(User.name == name))
    if user is None:
        user = User(name=name)
        db.add(user)
        db.flush()
    available = {genre.name: genre for genre in db.scalars(select(Genre)).all()}
    for genre_name in dict.fromkeys(payload.genres):
        genre = available.get(genre_name)
        if genre is None:
            continue
        preference = db.get(UserGenrePreference, (user.id, genre.id))
        if preference is None:
            db.add(UserGenrePreference(user_id=user.id, genre_id=genre.id, weight=INITIAL_PREFERENCE))
        else:
            preference.weight = min(PREFERENCE_MAX, preference.weight + PREFERENCE_STEP)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name}


@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": user.id, "name": user.name} for user in db.scalars(select(User).order_by(User.name)).all()]


@app.get("/users/{user_id}/preferences")
@require_user
def preferences(user_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Genre.name, UserGenrePreference.weight)
        .join(UserGenrePreference, UserGenrePreference.genre_id == Genre.id)
        .where(UserGenrePreference.user_id == user_id)
        .order_by(desc(UserGenrePreference.weight))
    ).all()
    return [{"genre": name, "weight": round(float(weight), 3)} for name, weight in rows]


@app.get("/movies")
def list_movies(q: str | None = None, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    statement = select(Movie)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Movie.title.ilike(f"%{escaped}%", escape="\\"))
    statement = statement.order_by(desc(Movie.popularity)).limit(limit)
    return [movie_payload(movie) for movie in db.scalars(statement).all()]


@app.get("/movies/{movie_id}")
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    return movie_payload(ensure_movie(db, movie_id))


@app.get("/users/{user_id}/recommendations")
@require_user
def get_recommendations(user_id: int, model: str = "hybrid", genres: str = "",
                        limit: int = Query(20, ge=1, le=MAX_LIMIT), db: Session = Depends(get_db)):
    if model not in MODELS:
        raise HTTPException(400, f"model должен быть одним из: {', '.join(MODELS)}")
    selected = [name.strip() for name in genres.split(",") if name.strip()]
    items = recommend(db, user_id, model, limit, selected)
    records = [Recommendation(user_id=user_id, movie_id=item["id"], model=model, score=item["score"] or 0)
               for item in items]
    db.add_all(records)
    db.flush()
    for item, record in zip(items, records):
        item["recommendation_id"] = record.id
    db.commit()
    return items


@app.post("/ratings")
def rate_movie(payload: RatingIn, db: Session = Depends(get_db)):
    ensure_user(db, payload.user_id)
    ensure_movie(db, payload.movie_id)
    rating = db.scalar(select(Rating).where(Rating.user_id == payload.user_id,
                                            Rating.movie_id == payload.movie_id))
    if rating is None:
        db.add(Rating(user_id=payload.user_id, movie_id=payload.movie_id, rating=payload.rating))
    else:
        rating.rating = payload.rating
        rating.created_at = utcnow()
    db.add(Interaction(user_id=payload.user_id, movie_id=payload.movie_id, action="rate",
                       details={"rating": payload.rating}))
    adjust_genres(db, payload.user_id, payload.movie_id, (payload.rating - RATING_NEUTRAL) * RATING_DELTA_FACTOR)
    db.commit()
    return {"status": "saved", "rating": payload.rating}


@app.post("/interactions")
def add_interaction(payload: InteractionIn, db: Session = Depends(get_db)):
    ensure_user(db, payload.user_id)
    ensure_movie(db, payload.movie_id)
    if payload.action not in ACTIONS:
        raise HTTPException(400, f"action должен быть одним из {list(ACTIONS)}")
    db.add(Interaction(user_id=payload.user_id, movie_id=payload.movie_id, action=payload.action,
                       details={"recommendation_id": payload.recommendation_id}))
    delta = ACTION_DELTAS.get(payload.action, 0)
    if delta:
        adjust_genres(db, payload.user_id, payload.movie_id, delta)
    db.commit()
    return {"status": "saved", "action": payload.action}


@app.post("/feedback")
def rate_recommendation(payload: FeedbackIn, db: Session = Depends(get_db)):
    record = db.get(Recommendation, payload.recommendation_id)
    if not record:
        raise HTTPException(404, "Рекомендация не найдена")
    db.add(RecommendationFeedback(recommendation_id=record.id, feedback=payload.feedback))
    adjust_genres(db, record.user_id, record.movie_id, (payload.feedback - FEEDBACK_NEUTRAL) * FEEDBACK_DELTA_FACTOR)
    db.commit()
    return {"status": "saved"}


@app.get("/users/{user_id}/history")
@require_user
def history(user_id: int, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Interaction, Movie).join(Movie, Movie.id == Interaction.movie_id)
        .where(Interaction.user_id == user_id).order_by(desc(Interaction.timestamp)).limit(limit)
    ).all()
    result = []
    for interaction, movie in rows:
        item = movie_payload(movie)
        item.update({"action": interaction.action, "timestamp": interaction.timestamp.isoformat(),
                     "details": interaction.details})
        result.append(item)
    return result


@app.get("/users/{user_id}/stats")
@require_user
def stats(user_id: int, db: Session = Depends(get_db)):
    actions = dict(db.execute(
        select(Interaction.action, func.count(Interaction.id))
        .where(Interaction.user_id == user_id).group_by(Interaction.action)
    ).all())
    rating_count, rating_average = db.execute(
        select(func.count(Rating.id), func.avg(Rating.rating)).where(Rating.user_id == user_id)
    ).one()
    return {
        "interactions": sum(actions.values()),
        "ratings": rating_count,
        "actions": actions,
        "average_rating": round(float(rating_average), 2) if rating_average is not None else None,
    }
