import os

import pandas as pd
from sqlalchemy import select

from database.connection import Base, SessionLocal, engine
from database.models import Genre, Movie
from etl.parsing import clean_text, parse_genres, to_float, to_int

CSV_PATH = os.getenv("MOVIES_CSV", "data/movies.csv")


def read_catalog(path):
    try:
        return pd.read_csv(path)
    except pd.errors.ParserError:
        return pd.read_csv(path, engine="python", on_bad_lines="skip")


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"Не найден файл {CSV_PATH}. Помести свой CSV в data/movies.csv "
            "или задай переменную MOVIES_CSV."
        )
    frame = read_catalog(CSV_PATH)
    title_column = "original_title" if "original_title" in frame.columns else ("title" if "title" in frame.columns else None)
    if "id" not in frame.columns or title_column is None or "genre" not in frame.columns:
        raise ValueError("Ожидаются как минимум столбцы id, original_title (или title), genre.")

    if "release_date" in frame.columns:
        frame["_release"] = pd.to_datetime(frame["release_date"], errors="coerce")
    else:
        frame["_release"] = pd.NaT

    Base.metadata.create_all(bind=engine)
    created = updated = 0

    with SessionLocal() as db:
        genres = {genre.name: genre for genre in db.scalars(select(Genre)).all()}
        movies = {movie.id: movie for movie in db.scalars(select(Movie)).all()}

        for record in frame.to_dict("records"):
            movie_id = to_int(record.get("id"), -1)
            title = str(record.get(title_column, "")).strip()
            if movie_id < 0 or not title or title.lower() == "nan":
                continue

            release = record.get("_release")
            release_date = None if pd.isna(release) else release.to_pydatetime().replace(tzinfo=None)
            release_year = None if pd.isna(release) else int(release.year)

            movie = movies.get(movie_id)
            if movie is None:
                movie = Movie(id=movie_id, title=title)
                db.add(movie)
                movies[movie_id] = movie
                created += 1
            else:
                updated += 1

            names = list(dict.fromkeys(parse_genres(record.get("genre"))))
            movie.title = title
            movie.original_language = clean_text(record.get("original_language"), 10)
            movie.release_date = release_date
            movie.release_year = release_year
            movie.popularity = to_float(record.get("popularity"))
            movie.vote_average = to_float(record.get("vote_average"))
            movie.vote_count = to_int(record.get("vote_count"))
            movie.overview = clean_text(record.get("overview"))
            movie.revenue = to_int(record.get("revenue"))
            movie.runtime = to_int(record.get("runtime"), 0) or None
            movie.tagline = clean_text(record.get("tagline"))
            movie.genres_text = ", ".join(names)

            linked = []
            for name in names:
                genre = genres.get(name)
                if genre is None:
                    genre = Genre(name=name)
                    db.add(genre)
                    db.flush()
                    genres[name] = genre
                linked.append(genre)
            movie.genres = linked

        db.commit()
    print(f"ETL завершён. Добавлено: {created}, обновлено: {updated}, строк в CSV: {len(frame)}")


if __name__ == "__main__":
    main()
