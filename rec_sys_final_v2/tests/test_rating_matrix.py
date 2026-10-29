import numpy as np

from recommender.ratings import RatingMatrix
from tests.helpers import make_catalog


def naive_scores(rows, catalog, user_id):
    by_movie = {}
    for owner, movie_id, value in rows:
        by_movie.setdefault(movie_id, {})[owner] = value
    rated = {m: v for o, m, v in rows if o == user_id}
    scores = np.zeros(len(catalog))
    for movie_id, raters in by_movie.items():
        numerator = denominator = 0.0
        for other_id, value in rated.items():
            if other_id == movie_id:
                continue
            common = set(raters) & set(by_movie[other_id])
            if len(common) < 2:
                continue
            a = np.array([raters[u] for u in common])
            b = np.array([by_movie[other_id][u] for u in common])
            if a.std() == 0 or b.std() == 0:
                continue
            correlation = float(np.corrcoef(a, b)[0, 1])
            numerator += correlation * (value - 3.0)
            denominator += abs(correlation)
        if denominator > 0:
            scores[catalog[movie_id]] = numerator / denominator
    return scores


def random_rows(seed, users=15, movies=12):
    generator = np.random.default_rng(seed)
    rows = []
    for user_id in range(1, users + 1):
        for movie_id in generator.choice(np.arange(1, movies + 1), size=7, replace=False):
            rows.append((user_id, int(movie_id), float(generator.integers(1, 6))))
    return rows


def test_vectorized_matches_naive_reference():
    catalog = make_catalog(12)
    for seed in range(5):
        rows = random_rows(seed)
        matrix = RatingMatrix.from_rows(catalog, rows)
        rated = {m: v for o, m, v in rows if o == 1}
        fast = matrix.item_item_scores(len(catalog), rated)
        slow = naive_scores(rows, catalog, 1)
        assert np.allclose(fast, slow, atol=1e-8)


def test_counts_and_repr():
    catalog = make_catalog(6)
    matrix = RatingMatrix.from_rows(catalog, [(1, 1, 4.0), (1, 2, 5.0), (2, 1, 3.0)])
    assert matrix.n_users == 2
    assert matrix.n_ratings == 3
    assert len(matrix) == 3
    assert "ratings=3" in repr(matrix)


def test_hide_removes_only_requested_entries():
    catalog = make_catalog(6)
    matrix = RatingMatrix.from_rows(catalog, [(1, 1, 4.0), (1, 2, 5.0), (2, 1, 3.0)])
    hidden = matrix.hide(1, [2])
    assert hidden.n_ratings == 2
    assert matrix.n_ratings == 3
    assert hidden.hide(99, [1]).n_ratings == 2


def test_empty_matrix_is_safe():
    catalog = make_catalog(4)
    matrix = RatingMatrix.from_rows(catalog, [])
    assert matrix.n_users == 0
    assert matrix.n_ratings == 0
    assert not matrix.item_item_scores(len(catalog), {1: 5.0}).any()
