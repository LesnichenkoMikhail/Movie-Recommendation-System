import time

from core.decorators import TIMINGS, timed, ttl_cache


def test_timed_records_calls():
    @timed("unit_test_label")
    def work(value):
        return value * 2

    assert work(4) == 8
    assert work(5) == 10
    assert TIMINGS["unit_test_label"]["calls"] == 2
    assert work.__name__ == "work"


def test_ttl_cache_hits_and_expires():
    calls = []

    @ttl_cache(0.05)
    def compute(value):
        calls.append(value)
        return value + 1

    assert compute(1) == 2
    assert compute(1) == 2
    assert len(calls) == 1
    time.sleep(0.08)
    assert compute(1) == 2
    assert len(calls) == 2


def test_ttl_cache_custom_key_and_clear():
    calls = []

    @ttl_cache(10, key=lambda holder, signature: signature)
    def build(holder, signature):
        calls.append(signature)
        return object()

    first = build(object(), "a")
    second = build(object(), "a")
    assert first is second
    build(object(), "b")
    assert calls == ["a", "b"]
    build.cache_clear()
    build(object(), "a")
    assert calls == ["a", "b", "a"]
