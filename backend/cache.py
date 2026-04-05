"""
In-memory TTL cache with LRU eviction.

Caches full ChatResponse objects keyed by a normalized version of the
user's query. This avoids repeated vector searches, RMP lookups, and
LLM calls for identical or near-identical questions.

Design decisions:
  - Keys are lowercase, stripped, and whitespace-collapsed so "Who is
    Prof. Smith?" and "who is prof. smith?" hit the same entry.
  - TTL is per-entry so stale data expires even under low traffic.
  - OrderedDict gives O(1) LRU eviction when the cache is full.
"""

import time
import re
from collections import OrderedDict
from threading import Lock
from typing import Optional, Any
from config import CACHE_TTL_SECONDS, CACHE_MAX_SIZE


def _normalize_key(query: str) -> str:
    """Collapse whitespace, lowercase, strip punctuation for cache key."""
    key = query.lower().strip()
    key = re.sub(r"\s+", " ", key)
    key = re.sub(r"[^\w\s]", "", key)
    return key


class QueryCache:
    """Thread-safe LRU cache with per-entry TTL expiration."""

    def __init__(
        self,
        ttl: int = CACHE_TTL_SECONDS,
        max_size: int = CACHE_MAX_SIZE,
    ):
        self._ttl = ttl
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()

        # Analytics counters
        self.hits = 0
        self.misses = 0

    # ── Public API ───────────────────────────────────────────────────

    def get(self, query: str) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        key = _normalize_key(query)

        with self._lock:
            if key not in self._store:
                self.misses += 1
                return None

            value, inserted_at = self._store[key]

            if time.time() - inserted_at > self._ttl:
                # Entry expired — remove it
                del self._store[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self._store.move_to_end(key)
            self.hits += 1
            return value

    def put(self, query: str, value: Any) -> None:
        """Insert or update a cache entry."""
        key = _normalize_key(query)

        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = (value, time.time())
                return

            # Evict oldest entry if at capacity
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)

            self._store[key] = (value, time.time())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
