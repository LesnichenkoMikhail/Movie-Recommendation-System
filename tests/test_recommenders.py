import numpy as np

from recommender.context import UserContext
from recommender.ratings import RatingMatrix
from recommender.recommenders import (
    CollaborativeRecommender, ContentRecommender, HybridRecommender, PopularityRecommender, build_recommender,
    normalize,
)
from tests.helpers import make_catalog


def make_context(catalog, rows, user_id=1, weights=None, seen=()):
    matrix = RatingMatrix.from_rows(catalog, rows)
    ratings = {movie_id: value for owner, movie_id, value in rows if owner == user_id}
    return UserContext(catalog, ratings, matrix, weights or {}, seen)


def sample_rows():
    return [
        (1, 1, 5.0), (1, 2, 4.0), (1, 3, 1.0),
        (2, 1, 5.0), (2, 2, 4.0), (2, 3, 2.0), (2, 4, 5.0),
        (3, 1, 4.0), (3, 2, 5.0), (3, 3, 1.0), (3, 4, 4.5),
        (4, 1, 1.0), (4, 2, 2.0), (4, 3, 5.0), (4, 5, 1.0),
    ]


def test_normalize_range_and_constant():
    scaled = normalize(np.array([1.0, 3.0, 5.0]))
    assert scaled.min() == 0.0 and scaled.max() == 1.0
    assert np.allclose(normalize(np.array([2.0, 2.0])), 0.5)


def test_operators_build_hybrid():
    popularity, content = PopularityRecommender(), ContentRecommender()
    mixed = 0.7 * popularity + 0.3 * content
    assert isinstance(mixed, HybridRecommender)
    assert len(mixed) == 2
    assert [weight for _, weight in mixed] == [0.7, 0.3]
    extended = mixed + CollaborativeRecommender()
    assert len(extended) == 3
    assert len(mixed) == 2
    assert isinstance(popularity + content, HybridRecommender)
    assert "PopularityRecommender" in repr(mixed)


def test_hybrid_score_is_weighted_average():
    catalog = make_catalog()
    context = make_context(catalog, sample_rows())
    popularity, content = PopularityRecommender(), ContentRecommender()
    mixed = 3 * popularity + 1 * content
    expected = (3 * popularity.score(context) + content.score(context)) / 4
    assert np.allclose(mixed.score(context), expected)


def test_hybrid_rejects_empty():
    try:
        HybridRecommender([])
    except ValueError:
        return
    raise AssertionError("ожидалось ValueError")


def test_build_recommender_switches_on_enough_data():
    cold = build_recommender("hybrid", enough=False)
    warm = build_recommender("hybrid", enough=True)
    assert len(cold) == 2
    assert len(warm) == 3
    assert isinstance(build_recommender("popularity", True), PopularityRecommender)
    assert len(build_recommender("collaborative", False)) == 2
    assert len(build_recommender("collaborative", True)) == 3
    assert len(build_recommender("content", True)) == 2


def test_context_excludes_seen_and_rated():
    catalog = make_catalog()
    context = make_context(catalog, sample_rows(), seen=[6, 7])
    candidate_ids = {catalog.ids[i] for i in context.candidates}
    assert not candidate_ids & {1, 2, 3, 6, 7}
    assert 8 in candidate_ids


def test_enough_flag():
    catalog = make_catalog()
    assert make_context(catalog, sample_rows()).enough
    assert not make_context(catalog, sample_rows()[:5]).enough


def test_genre_weights_shift_content_scores():
    catalog = make_catalog()
    base = make_context(catalog, sample_rows()).content_scores
    boosted = make_context(catalog, sample_rows(), weights={"Horror": 3.0}).content_scores
    horror = [i for i, names in enumerate(catalog.genre_lists) if "Horror" in names]
    other = [i for i, names in enumerate(catalog.genre_lists) if "Horror" not in names]
    assert all(boosted[i] > base[i] for i in horror)
    assert all(boosted[i] < base[i] for i in other)


def test_all_models_return_one_score_per_movie():
    catalog = make_catalog()
    context = make_context(catalog, sample_rows())
    for name in ("popularity", "content", "collaborative", "hybrid"):
        scores = build_recommender(name, context.enough).score(context)
        assert scores.shape == (len(catalog),)
        assert np.all(np.isfinite(scores))
