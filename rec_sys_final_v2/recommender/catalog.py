import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def split_genres(text):
    return [name.strip() for name in (text or "").split(",") if name.strip()]


def popularity_scores(movies):
    if not movies:
        return np.zeros(0)
    votes = np.array([max(0, m.vote_count or 0) for m in movies], dtype=float)
    ratings = np.array([max(0, min(10, m.vote_average or 0)) for m in movies], dtype=float)
    popularity = np.array([max(0, m.popularity or 0) for m in movies], dtype=float)

    mean_rating = float(np.mean(ratings))
    min_votes = float(np.percentile(votes, 60))
    bayes = (votes / (votes + min_votes + 1e-9)) * ratings + (min_votes / (votes + min_votes + 1e-9)) * mean_rating
    peak = float(popularity.max())
    normalized = popularity / peak if peak > 0 else np.zeros_like(popularity)
    return 0.8 * (bayes / 10.0) + 0.2 * normalized


def content_matrix(movies):
    documents = [f"{m.genres_text or ''} {m.title or ''} {m.overview or ''} {m.tagline or ''}" for m in movies]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=50000, ngram_range=(1, 2))
    try:
        return vectorizer.fit_transform(documents).tocsr()
    except ValueError:
        return None


class Catalog:
    __slots__ = ("ids", "idx", "genre_lists", "popularity", "matrix")

    def __init__(self, movies):
        self.ids = [m.id for m in movies]
        self.idx = {movie_id: position for position, movie_id in enumerate(self.ids)}
        self.genre_lists = [split_genres(m.genres_text) for m in movies]
        self.popularity = popularity_scores(movies)
        self.matrix = content_matrix(movies)

    def __len__(self):
        return len(self.ids)

    def __contains__(self, movie_id):
        return movie_id in self.idx

    def __getitem__(self, movie_id):
        return self.idx[movie_id]

    def __iter__(self):
        return iter(self.ids)

    def __repr__(self):
        return f"Catalog(movies={len(self.ids)})"
