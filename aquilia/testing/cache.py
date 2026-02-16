"""
Aquilia Testing - Cache Testing Utilities.

Provides :class:`MockCacheBackend` and :class:`CacheTestMixin`.
"""

from __future__ import annotations

import time as _time
from typing import Any, Dict, List, Optional, Tuple


class MockCacheBackend:
    """
    In-memory cache backend for testing with TTL tracking.

    Mirrors the :class:`~aquilia.cache.core.CacheBackend` async protocol
    but stores everything in a plain dict for zero-overhead testing.
    TTLs are tracked and honoured — expired keys are transparently evicted.

    Usage::

        cache = MockCacheBackend()
        await cache.set("key", "value", ttl=60)
        assert await cache.get("key") == "value"
        assert cache.set_count == 1
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._ttls: Dict[str, float] = {}  # key → expiry timestamp
        self.get_count = 0
        self.set_count = 0
        self.delete_count = 0
        self.clear_count = 0
        self._connected = False

    # -- TTL helpers -----------------------------------------------------

    def _is_expired(self, key: str) -> bool:
        if key in self._ttls and _time.monotonic() >= self._ttls[key]:
            del self._store[key]
            del self._ttls[key]
            return True
        return False

    def _set_ttl(self, key: str, ttl: Optional[int]) -> None:
        if ttl is not None and ttl > 0:
            self._ttls[key] = _time.monotonic() + ttl
        else:
            self._ttls.pop(key, None)

    def get_ttl(self, key: str) -> Optional[float]:
        """Return remaining TTL in seconds, or None if no TTL set."""
        if key not in self._ttls:
            return None
        remaining = self._ttls[key] - _time.monotonic()
        return max(0.0, remaining)

    # -- CacheBackend protocol -------------------------------------------

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def get(self, key: str) -> Optional[Any]:
        self.get_count += 1
        self._is_expired(key)
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self.set_count += 1
        self._store[key] = value
        self._set_ttl(key, ttl)

    async def get_or_set(
        self,
        key: str,
        default: Any,
        ttl: Optional[int] = None,
    ) -> Any:
        """Get existing value or set & return default."""
        value = await self.get(key)
        if value is None:
            await self.set(key, default, ttl=ttl)
            return default
        return value

    async def delete(self, key: str) -> bool:
        self.delete_count += 1
        self._ttls.pop(key, None)
        return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        self._is_expired(key)
        return key in self._store

    async def clear(self):
        self.clear_count += 1
        self._store.clear()
        self._ttls.clear()

    async def keys(self, pattern: str = "*") -> List[str]:
        # Evict expired keys first
        for key in list(self._ttls):
            self._is_expired(key)
        if pattern == "*":
            return list(self._store.keys())
        import fnmatch
        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric cache value."""
        current = self._store.get(key, 0)
        new_val = int(current) + delta
        self._store[key] = new_val
        return new_val

    async def decrement(self, key: str, delta: int = 1) -> int:
        """Decrement a numeric cache value."""
        return await self.increment(key, -delta)

    async def mget(self, *keys: str) -> List[Optional[Any]]:
        """Get multiple values at once."""
        return [await self.get(k) for k in keys]

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set multiple values at once."""
        for key, value in mapping.items():
            await self.set(key, value, ttl=ttl)

    async def health_check(self) -> bool:
        return True

    # -- Test helpers ----------------------------------------------------

    @property
    def store(self) -> Dict[str, Any]:
        """Direct access to the underlying store for assertions."""
        return self._store

    @property
    def size(self) -> int:
        """Number of keys currently in the store."""
        return len(self._store)

    def reset(self):
        """Clear store, TTLs, and counters."""
        self._store.clear()
        self._ttls.clear()
        self.get_count = 0
        self.set_count = 0
        self.delete_count = 0
        self.clear_count = 0


class CacheTestMixin:
    """
    Mixin providing cache-specific test helpers.

    Mix into a test case to gain ``assert_cached``, ``assert_not_cached``,
    ``populate_cache``, etc.

    Expects ``self.cache_service`` or ``self.cache_backend`` to be available.
    """

    def _get_cache(self):
        """Resolve the cache backend / service from the test case."""
        if hasattr(self, "cache_backend"):
            return self.cache_backend
        if hasattr(self, "cache_service"):
            return self.cache_service
        if hasattr(self, "server"):
            return getattr(self.server, "cache_service", None)
        return None

    async def assert_cached(self, key: str, msg: str = ""):
        """Assert a key is present in the cache."""
        cache = self._get_cache()
        assert cache is not None, "No cache backend/service available"
        value = await cache.get(key)
        assert value is not None, f"Key {key!r} not found in cache. {msg}"

    async def assert_not_cached(self, key: str, msg: str = ""):
        """Assert a key is NOT present in the cache."""
        cache = self._get_cache()
        assert cache is not None, "No cache backend/service available"
        value = await cache.get(key)
        assert value is None, f"Key {key!r} unexpectedly found in cache. {msg}"

    async def assert_cache_value(self, key: str, expected: Any, msg: str = ""):
        """Assert a cached key equals an expected value."""
        cache = self._get_cache()
        assert cache is not None, "No cache backend/service available"
        value = await cache.get(key)
        assert value is not None, f"Key {key!r} not found in cache. {msg}"
        assert value == expected, (
            f"Cache key {key!r}: expected {expected!r}, got {value!r}. {msg}"
        )

    async def assert_cache_count(self, expected: int, pattern: str = "*", msg: str = ""):
        """Assert the number of keys in the cache."""
        cache = self._get_cache()
        assert cache is not None, "No cache backend/service available"
        keys = await cache.keys(pattern)
        actual = len(keys)
        assert actual == expected, (
            f"Expected {expected} cache keys (pattern={pattern!r}), got {actual}. {msg}"
        )

    async def populate_cache(self, data: Dict[str, Any], ttl: Optional[int] = None):
        """Bulk-populate cache entries."""
        cache = self._get_cache()
        assert cache is not None, "No cache backend/service available"
        for key, value in data.items():
            await cache.set(key, value, ttl=ttl)

    async def flush_cache(self):
        """Clear the entire cache."""
        cache = self._get_cache()
        if cache is not None:
            await cache.clear()
