import random

import pytest

from recommender import benchmark
from recommender.benchmark import confidence_interval, run_benchmark, split_user_ratings
from recommender.config import BASELINE_MODELS, LIKE_THRESHOLD, MODELS
from recommender.evaluation import METRIC_KEYS
from tests.helpers import GENRES, make_catalog


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _statement):
        return FakeResult(self.rows)


def make_rows(users=12, per_user=20, movies=60):
    generator = random.Random(3)
    rows = []
    for user_id in range(1, users + 1):
        favorite = GENRES[user_id % len(GENRES)]
        for movie_id in generator.sample(range(1, movies + 1), per_user):
            genres = {GENRES[movie_id % len(GENRES)], GENRES[(movie_id + 1) % len(GENRES)]}
            rows.append((user_id, movie_id, 4.5 if favorite in genres else 2.0))
    return rows


@pytest.fixture
def prepared(monkeypatch):
    catalog = make_catalog(60)
    monkeypatch.setattr(benchmark, "get_catalog", lambda db: catalog)
    return FakeDB(make_rows())


def test_split_keeps_sizes_and_has_liked_item_in_test():
    ratings = {movie_id: 5.0 if movie_id <= 3 else 2.0 for movie_id in range(1, 21)}
    for seed in range(30):
        train, test = split_user_ratings(ratings, 0.3, random.Random(seed))
        assert len(train) + len(test) == 20 and not set(train) & set(test)
        assert len(test) == 6
        assert any(ratings[movie_id] >= LIKE_THRESHOLD for movie_id in test)


def test_split_returns_none_without_liked_items():
    ratings = {movie_id: 2.0 for movie_id in range(1, 11)}
    assert split_user_ratings(ratings, 0.3, random.Random(0)) is None


def test_confidence_interval():
    assert confidence_interval([0.5]) == 0.0
    assert confidence_interval([1.0, 1.0, 1.0]) == 0.0
    assert confidence_interval([0.0, 1.0, 0.0, 1.0]) > 0.0


def test_benchmark_reports_all_models_and_metrics(prepared):
    result = run_benchmark(prepared, k=5, min_ratings=8, max_users=12, negatives=20)
    assert result["users_evaluated"] > 0
    assert result["protocol"] == "sampled"
    assert {item["model"] for item in result["models"]} == set(MODELS) | set(BASELINE_MODELS)
    for item in result["models"]:
        for key in METRIC_KEYS:
            assert 0.0 <= item[key] <= 1.0
            assert item["ci"][key] >= 0.0
    assert any(item["ndcg"] > 0 for item in result["models"])


def test_benchmark_is_reproducible(prepared):
    first = run_benchmark(prepared, k=5, max_users=12, seed=11, negatives=20)
    second = run_benchmark(prepared, k=5, max_users=12, seed=11, negatives=20)
    assert first == second


def test_benchmark_full_catalog_mode(prepared):
    result = run_benchmark(prepared, k=5, max_users=12, negatives=0)
    assert result["protocol"] == "full"
    assert result["users_evaluated"] > 0


def test_benchmark_without_ratings(monkeypatch):
    monkeypatch.setattr(benchmark, "get_catalog", lambda db: make_catalog(10))
    result = run_benchmark(FakeDB([]))
    assert result["models"] == [] and result["users_evaluated"] == 0
