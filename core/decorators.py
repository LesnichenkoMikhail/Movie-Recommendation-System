import functools
import logging
import threading
import time
from collections import defaultdict

logger = logging.getLogger("recsys")

TIMINGS = defaultdict(lambda: {"calls": 0, "total_ms": 0.0, "last_ms": 0.0})
_timings_lock = threading.Lock()


def timed(name=None):
    def decorator(func):
        label = name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - started) * 1000
                with _timings_lock:
                    entry = TIMINGS[label]
                    entry["calls"] += 1
                    entry["total_ms"] += elapsed
                    entry["last_ms"] = elapsed
                logger.info("%s выполнено за %.1f мс", label, elapsed)

        return wrapper

    return decorator


def ttl_cache(seconds, key=None):
    def decorator(func):
        lock = threading.Lock()
        store = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key(*args, **kwargs) if key else (args, tuple(sorted(kwargs.items())))
            with lock:
                now = time.monotonic()
                hit = store.get(cache_key)
                if hit is not None and now - hit[0] < seconds:
                    return hit[1]
                value = func(*args, **kwargs)
                expired = [k for k, (stamp, _) in store.items() if now - stamp >= seconds]
                for stale in expired:
                    del store[stale]
                store[cache_key] = (time.monotonic(), value)
                return value

        def cache_clear():
            with lock:
                store.clear()

        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator
