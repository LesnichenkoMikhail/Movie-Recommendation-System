from types import SimpleNamespace

from recommender.catalog import Catalog

GENRES = ["Drama", "Comedy", "Action", "Horror", "Romance", "Science Fiction"]


def make_movie(movie_id, genres, votes=100, average=7.0, popularity=10.0):
    return SimpleNamespace(
        id=movie_id,
        title=f"Movie {movie_id}",
        overview=f"{' '.join(genres)} story number {movie_id}",
        tagline="",
        genres_text=", ".join(genres),
        vote_count=votes,
        vote_average=average,
        popularity=popularity,
    )


def make_catalog(size=12):
    movies = [
        make_movie(index, [GENRES[index % len(GENRES)], GENRES[(index + 1) % len(GENRES)]],
                   votes=50 + index * 10, average=5 + (index % 5), popularity=float(index))
        for index in range(1, size + 1)
    ]
    return Catalog(movies)
