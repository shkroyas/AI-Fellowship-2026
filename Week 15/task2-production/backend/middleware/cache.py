"""
Response Cache Module.

Implements an in-memory LRU cache for prompt/response pairs
to reduce latency and API costs for repeated queries.
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Thread-safe in-memory LRU cache for AI responses.

    Features:
    - LRU eviction when max size is reached
    - TTL (time-to-live) expiration
    - Cache key generation from request parameters
    - Hit/miss statistics
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = Lock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def make_key(message: str, provider: Optional[str] = None, style: str = "balanced") -> str:
        """Generate a cache key from request parameters."""
        key_data = json.dumps({
            "message": message.strip().lower(),
            "provider": provider or "default",
            "style": style,
        }, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[dict]:
        """Get a cached response by key."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check TTL
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                self._evictions += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1

            return entry["data"]

    def set(self, key: str, data: dict) -> None:
        """Store a response in the cache."""
        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                del self._cache[key]

            # Evict LRU if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[key] = {
                "data": data,
                "timestamp": time.time(),
            }

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate_percent": round(hit_rate, 2),
        }
