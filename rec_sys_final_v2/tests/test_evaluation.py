import math

from recommender.evaluation import evaluate, ndcg_at_k, precision_at_k, recall_at_k


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
