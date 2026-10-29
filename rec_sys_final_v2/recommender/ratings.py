import copy

import numpy as np

from recommender.config import RATING_NEUTRAL


class RatingMatrix:
    def __init__(self, user_row, item_col, catalog_index, values, mask):
        self.user_row = user_row
        self.item_col = item_col
        self.catalog_index = catalog_index
        self.values = values
        self.mask = mask

    @classmethod
    def from_rows(cls, catalog, rows):
        rows = [(user_id, movie_id, float(value)) for user_id, movie_id, value in rows if movie_id in catalog]
        users = sorted({user_id for user_id, _, _ in rows})
        movie_ids = sorted({movie_id for _, movie_id, _ in rows})
        user_row = {user_id: position for position, user_id in enumerate(users)}
        item_col = {movie_id: position for position, movie_id in enumerate(movie_ids)}
        catalog_index = np.array([catalog[movie_id] for movie_id in movie_ids], dtype=int)
        values = np.zeros((len(users), len(movie_ids)))
        mask = np.zeros((len(users), len(movie_ids)))
        for user_id, movie_id, value in rows:
            row, col = user_row[user_id], item_col[movie_id]
            values[row, col] = value
            mask[row, col] = 1.0
        return cls(user_row, item_col, catalog_index, values, mask)

    @property
    def n_users(self):
        return int((self.mask.sum(axis=1) > 0).sum()) if self.mask.size else 0

    @property
    def n_ratings(self):
        return int(self.mask.sum())

    def hide(self, user_id, movie_ids):
        clone = copy.copy(self)
        clone.values = self.values.copy()
        clone.mask = self.mask.copy()
        row = self.user_row.get(user_id)
        if row is not None:
            for movie_id in movie_ids:
                col = self.item_col.get(movie_id)
                if col is not None:
                    clone.values[row, col] = 0.0
                    clone.mask[row, col] = 0.0
        return clone

    def item_item_scores(self, size, rated):
        scores = np.zeros(size)
        pairs = [(self.item_col[movie_id], value) for movie_id, value in rated.items() if movie_id in self.item_col]
        if not pairs:
            return scores
        target_cols = np.array([col for col, _ in pairs], dtype=int)
        preferences = np.array([value - RATING_NEUTRAL for _, value in pairs], dtype=float)

        xa, ma = self.values, self.mask
        xb, mb = xa[:, target_cols], ma[:, target_cols]
        common = ma.T @ mb
        sum_a = xa.T @ mb
        sum_b = ma.T @ xb
        sum_ab = xa.T @ xb
        sum_aa = (xa * xa).T @ mb
        sum_bb = ma.T @ (xb * xb)

        with np.errstate(divide="ignore", invalid="ignore"):
            covariance = sum_ab - sum_a * sum_b / common
            variance_a = sum_aa - sum_a * sum_a / common
            variance_b = sum_bb - sum_b * sum_b / common
            correlation = covariance / np.sqrt(variance_a * variance_b)

        valid = (common >= 2) & (variance_a > 1e-9) & (variance_b > 1e-9) & np.isfinite(correlation)
        valid &= np.arange(xa.shape[1])[:, None] != target_cols[None, :]
        correlation = np.where(valid, correlation, 0.0)

        numerator = correlation @ preferences
        denominator = np.abs(correlation).sum(axis=1)
        result = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
        scores[self.catalog_index] = result
        return scores

    def __len__(self):
        return self.n_ratings

    def __repr__(self):
        return f"RatingMatrix(users={self.n_users}, items={self.values.shape[1]}, ratings={self.n_ratings})"
