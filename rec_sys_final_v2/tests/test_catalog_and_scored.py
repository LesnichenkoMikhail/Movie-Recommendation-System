from heapq import nlargest

from recommender.scored import ScoredMovie
from tests.helpers import make_catalog


def test_catalog_dunder_methods():
    catalog = make_catalog(8)
    assert len(catalog) == 8
    assert 3 in catalog
    assert 99 not in catalog
    assert catalog[1] == 0
    assert list(catalog) == list(range(1, 9))
    assert "8" in repr(catalog)
    assert len(catalog.popularity) == 8


def test_scored_movie_comparison():
    low = ScoredMovie(1, 0.2, "hybrid")
    high = ScoredMovie(2, 0.9, "hybrid")
    assert low < high
    assert high > low
    assert low <= high
    assert max(low, high) is high
    assert ScoredMovie(1, 0.2, "hybrid") == low
    assert low != ScoredMovie(1, 0.2, "content")
    assert low != ScoredMovie(3, 0.2, "hybrid")
    assert len({low, ScoredMovie(1, 0.2, "hybrid")}) == 1
    assert len({low, ScoredMovie(1, 0.5, "hybrid")}) == 2
    assert float(high) == 0.9
    assert "movie_id=2" in repr(high)


def test_scored_movie_sorting_with_nlargest():
    items = [ScoredMovie(i, score, "m") for i, score in enumerate([0.1, 0.8, 0.5, 0.9])]
    assert [item.movie_id for item in nlargest(2, items)] == [3, 1]
