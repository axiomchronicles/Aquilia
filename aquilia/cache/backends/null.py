"""
AquilaCache — Null (no-op) backend.

Used for testing, development, or when caching should be disabled
without changing application code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from ..core import CacheBackend, CacheEntry, CacheStats


class NullBackend(CacheBackend):
    """
    No-op cache backend — all operations are pass-through.
    
    Useful for:
    - Disabling cache in test environments
    - Bypassing cache during development
    - Measuring baseline performance without caching
    """
    
    __slots__ = ("_stats",)
    
    def __init__(self):
        self._stats = CacheStats(backend="null")
    
    @property
    def name(self) -> str:
        return "null"
    
    async def initialize(self) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        self._stats.misses += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Tuple[str, ...] = (),
        namespace: str = "default",
    ) -> None:
        self._stats.sets += 1
    
    async def delete(self, key: str) -> bool:
        return False
    
    async def exists(self, key: str) -> bool:
        return False
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        return 0
    
    async def keys(self, pattern: str = "*", namespace: Optional[str] = None) -> List[str]:
        return []
    
    async def stats(self) -> CacheStats:
        return self._stats
