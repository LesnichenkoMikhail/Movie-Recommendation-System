import argparse
import random

from sqlalchemy import select

from database.connection import Base, SessionLocal, engine
from database.models import Genre, Interaction, Movie, Rating, User, UserGenrePreference
from recommender.config import INITIAL_PREFERENCE

POOL_SIZE = 600


def build_parser():
    parser = argparse.ArgumentParser(description="Создание демонстрационных пользователей с оценками")
    parser.add_argument("--users", type=int, default=40)
    parser.add_argument("--ratings", type=int, default=25)
    parser.add_argument("--seed", type=int, default=7)
    return parser


def pick_rating(generator, matches):
    base = 2.0 + 1.2 * matches + generator.gauss(0, 0.6)
    return max(0.5, min(5.0, round(base * 2) / 2))


def main():
    arguments = build_parser().parse_args()
    generator = random.Random(arguments.seed)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        genres = {genre.name: genre for genre in db.scalars(select(Genre)).all()}
        rows = db.execute(
            select(Movie.id, Movie.popularity, Movie.genres_text).order_by(Movie.popularity.desc()).limit(POOL_SIZE)
        ).all()
        if not rows or not genres:
            raise SystemExit("Каталог пуст. Сначала выполни импорт фильмов: python -m etl.load_movies")

        pool = [(movie_id, genres_text or "") for movie_id, _, genres_text in rows]
        existing = {name for name in db.scalars(select(User.name)).all()}
        created = 0

        for number in range(1, arguments.users + 1):
            name = f"demo_{number:02d}"
            if name in existing:
                continue
            user = User(name=name)
            db.add(user)
            db.flush()

            favorites = generator.sample(sorted(genres), k=min(3, len(genres)))
            for favorite in favorites:
                db.add(UserGenrePreference(user_id=user.id, genre_id=genres[favorite].id,
                                           weight=INITIAL_PREFERENCE))

            chosen = generator.sample(pool, k=min(arguments.ratings, len(pool)))
            for movie_id, genres_text in chosen:
                movie_genres = {item.strip() for item in genres_text.split(",") if item.strip()}
                matches = len(movie_genres & set(favorites))
                value = pick_rating(generator, matches)
                db.add(Rating(user_id=user.id, movie_id=movie_id, rating=value))
                db.add(Interaction(user_id=user.id, movie_id=movie_id, action="rate", details={"rating": value}))
            created += 1

        db.commit()
    print(f"Создано демонстрационных пользователей: {created}")


if __name__ == "__main__":
    main()
