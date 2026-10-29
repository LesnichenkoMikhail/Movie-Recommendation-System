from fastapi import HTTPException

from database.models import Movie, User, UserGenrePreference
from recommender.config import PREFERENCE_MAX, PREFERENCE_MIN


def ensure_user(db, user_id):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


def ensure_movie(db, movie_id):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return movie


def adjust_genres(db, user_id, movie_id, delta):
    movie = db.get(Movie, movie_id)
    if movie is None:
        return
    for genre in movie.genres:
        preference = db.get(UserGenrePreference, (user_id, genre.id))
        if preference is None:
            preference = UserGenrePreference(user_id=user_id, genre_id=genre.id, weight=1.0)
            db.add(preference)
        preference.weight = max(PREFERENCE_MIN, min(PREFERENCE_MAX, preference.weight + delta))
