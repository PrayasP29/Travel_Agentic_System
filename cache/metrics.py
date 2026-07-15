"""In-memory cache metrics counters."""
from threading import Lock


class CacheMetrics:
    """Thread-safe in-memory counters for cache operations."""

    def __init__(self):
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._deletes = 0
        self._errors = 0

    def record_hit(self):
        with self._lock:
            self._hits += 1

    def record_miss(self):
        with self._lock:
            self._misses += 1

    def record_write(self):
        with self._lock:
            self._writes += 1

    def record_delete(self):
        with self._lock:
            self._deletes += 1

    def record_error(self):
        with self._lock:
            self._errors += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "deletes": self._deletes,
                "errors": self._errors,
            }

    def reset(self):
        with self._lock:
            self._hits = self._misses = self._writes = self._deletes = self._errors = 0


metrics = CacheMetrics()
