from functools import cached_property

import numpy as np

from recommender.config import (
    DEFAULT_GENRE_WEIGHT, GENRE_ADJUSTMENT_SCALE, MIN_RATINGS_FOR_CF, MIN_USERS_FOR_CF, RATING_NEUTRAL,
)


def content_scores_from_ratings(matrix, rated, size):
    scores = np.zeros(size)
    if matrix is None or not rated:
        return scores
    columns = [position for position, _ in rated]
    preference = np.array([(value - RATING_NEUTRAL) / 2.0 for _, value in rated], dtype=float)
    similarity = (matrix @ matrix[columns].T).toarray()
    numerator = similarity @ preference
    denominator = np.abs(similarity).sum(axis=1)
    nonzero = denominator > 0
    scores[nonzero] = numerator[nonzero] / denominator[nonzero]
    return scores


class UserContext:
    def __init__(self, catalog, ratings, matrix, weights, seen, selected_genres=()):
        self.catalog = catalog
        self.ratings = dict(ratings)
        self.matrix = matrix
        self.weights = dict(weights)
        for genre in selected_genres:
            self.weights.setdefault(genre, DEFAULT_GENRE_WEIGHT)
        self.seen = set(seen) | set(self.ratings)

    @property
    def enough(self):
        return self.matrix.n_users >= MIN_USERS_FOR_CF and self.matrix.n_ratings >= MIN_RATINGS_FOR_CF

    @cached_property
    def rated(self):
        return [(self.catalog[movie_id], value) for movie_id, value in self.ratings.items() if movie_id in self.catalog]

    @cached_property
    def content_scores(self):
        scores = content_scores_from_ratings(self.catalog.matrix, self.rated, len(self.catalog))
        if self.weights:
            for position, names in enumerate(self.catalog.genre_lists):
                if names:
                    genre_score = sum(self.weights.get(name, 0.0) for name in names) / len(names)
                    scores[position] += GENRE_ADJUSTMENT_SCALE * (genre_score - 1.0)
        return scores

    @cached_property
    def collaborative_scores(self):
        return self.matrix.item_item_scores(len(self.catalog), self.ratings)

    @cached_property
    def candidates(self):
        return np.array([position for position, movie_id in enumerate(self.catalog.ids)
                         if movie_id not in self.seen], dtype=int)
