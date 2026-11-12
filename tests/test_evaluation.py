import math

from recommender.evaluation import (
    METRIC_KEYS, average_precision_at_k, evaluate, evaluate_all, hit_rate_at_k, ndcg_at_k, precision_at_k,
    recall_at_k, reciprocal_rank_at_k,
)


def test_precision():
    assert precision_at_k([1, 2, 3, 4], [1, 3], k=4) == 0.5
    assert precision_at_k([], [1], k=3) == 0.0


def test_recall():
    assert recall_at_k([1, 2, 3], [1, 3, 9, 10], k=3) == 0.5
    assert recall_at_k([1, 2, 3], [], k=3) == 0.0


def test_ndcg_perfect_and_empty():
    assert math.isclose(ndcg_at_k([1, 2], [1, 2], k=2), 1.0)
    assert ndcg_at_k([5, 6], [1, 2], k=2) == 0.0


def test_ndcg_prefers_earlier_hits():
    early = ndcg_at_k([1, 5, 6], [1], k=3)
    late = ndcg_at_k([5, 6, 1], [1], k=3)
    assert early > late


def test_evaluate_keys():
    result = evaluate([1, 2, 3], [1], k=3)
    assert set(result) == {"precision@3", "recall@3", "ndcg@3"}


def test_hit_rate():
    assert hit_rate_at_k([5, 6, 1], [1], k=3) == 1.0
    assert hit_rate_at_k([5, 6, 1], [1], k=2) == 0.0


def test_average_precision():
    # попадания на позициях 1 и 3: (1/1 + 2/3) / 2
    assert math.isclose(average_precision_at_k([1, 9, 2], [1, 2], k=3), (1 + 2 / 3) / 2)
    assert average_precision_at_k([9, 8], [1], k=2) == 0.0
    assert average_precision_at_k([1], [], k=1) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank_at_k([9, 8, 1], [1], k=3) == 1 / 3
    assert reciprocal_rank_at_k([9, 8, 1], [1], k=2) == 0.0


def test_evaluate_all_keys_and_bounds():
    result = evaluate_all([1, 2, 3], [1, 3], k=3)
    assert set(result) == set(METRIC_KEYS)
    assert all(0.0 <= value <= 1.0 for value in result.values())
