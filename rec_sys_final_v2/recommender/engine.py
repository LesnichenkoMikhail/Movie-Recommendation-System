from heapq import nlargest

from sqlalchemy import func, select

from core.decorators import timed, ttl_cache
from database.models import Genre, Interaction, Movie, Rating, UserGenrePreference
from recommender.catalog import Catalog
from recommender.config import CATALOG_TTL_SECONDS, MAX_LIMIT, SEEN_ACTIONS
from recommender.context import UserContext
from recommender.payload import movie_payload
from recommender.ratings import RatingMatrix
from recommender.recommenders import build_recommender
from recommender.scored import ScoredMovie


def get_movies(db):
    return db.scalars(select(Movie).order_by(Movie.id)).all()


def get_user_weights(db, user_id):
    rows = db.execute(
        select(Genre.name, UserGenrePreference.weight)
        .join(UserGenrePreference, UserGenrePreference.genre_id == Genre.id)
        .where(UserGenrePreference.user_id == user_id)
    ).all()
    return {name: float(weight) for name, weight in rows}


def catalog_signature(db):
    count, max_id = db.execute(select(func.count(Movie.id), func.max(Movie.id))).one()
    return count, max_id


@ttl_cache(CATALOG_TTL_SECONDS, key=lambda db, signature: signature)
def build_catalog(db, signature):
    return Catalog(get_movies(db))


def get_catalog(db):
    signature = catalog_signature(db)
    if not signature[0]:
        return None
    return build_catalog(db, signature)


def load_context(db, catalog, user_id, selected_genres=None):
    seen = {row[0] for row in db.execute(
        select(Interaction.movie_id).where(Interaction.user_id == user_id,
                                           Interaction.action.in_(SEEN_ACTIONS))
    ).all()}
    rating_rows = db.execute(select(Rating.user_id, Rating.movie_id, Rating.rating)).all()
    ratings = {movie_id: value for owner, movie_id, value in rating_rows if owner == user_id}
    matrix = RatingMatrix.from_rows(catalog, rating_rows)
    weights = get_user_weights(db, user_id)
    return UserContext(catalog, ratings, matrix, weights, seen, selected_genres or [])


def rank_scores(scores, context, model, limit):
    size = max(1, min(int(limit), MAX_LIMIT))
    ids = context.catalog.ids
    items = (ScoredMovie(ids[position], scores[position], model) for position in context.candidates)
    return nlargest(size, items)


@timed("recommend")
def recommend(db, user_id, model="hybrid", limit=20, selected_genres=None):
    catalog = get_catalog(db)
    if catalog is None:
        return []
    context = load_context(db, catalog, user_id, selected_genres)
    scores = build_recommender(model, context.enough).score(context)
    top = rank_scores(scores, context, model, limit)
    ids = [item.movie_id for item in top]
    movies = {m.id: m for m in db.scalars(select(Movie).where(Movie.id.in_(ids))).all()}
    return [movie_payload(movies[item.movie_id], item.score, model) for item in top if item.movie_id in movies]
