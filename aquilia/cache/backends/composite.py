"""
AquilaCache — Composite (L1/L2) backend.

Implements a two-level cache architecture:
- **L1** (Memory): Fast, small, short TTL
- **L2** (Redis/other): Distributed, larger, longer TTL

Read path:  L1 → L2 → miss
Write path: Write to both L1 and L2 (optionally async L2)
Delete path: Invalidate both L1 and L2

This provides sub-microsecond reads for hot data while maintaining
consistency across multiple server instances via the distributed L2.

Resilience:
- L2 failures on read degrade gracefully to L1 only
- L2 failures on write are logged but don't break the request
- Async L2 write mode available for lowest latency
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core import CacheBackend, CacheEntry, CacheStats

logger = logging.getLogger("aquilia.cache.composite")


class CompositeBackend(CacheBackend):
    """
    Two-level cache: L1 (fast/local) + L2 (distributed/persistent).
    
    Read-through: L1 → L2 → miss (promote to L1 on L2 hit)
    Write-through: Write to both L1 and L2
    
    Features:
    - L2 error resilience (degrades to L1 on failure)
    - Optional async L2 writes (fire-and-forget)
    - Promotion of L2 hits into L1
    """
    
    __slots__ = ("_l1", "_l2", "_promote_on_l2_hit", "_async_l2_write", "_l2_healthy")
    
    def __init__(
        self,
        l1: CacheBackend,
        l2: CacheBackend,
        promote_on_l2_hit: bool = True,
        async_l2_write: bool = False,
    ):
        """
        Args:
            l1: Fast local backend (typically MemoryBackend)
            l2: Distributed backend (typically RedisBackend)
            promote_on_l2_hit: Promote L2 hits into L1
            async_l2_write: Fire-and-forget L2 writes for lower latency
        """
        self._l1 = l1
        self._l2 = l2
        self._promote_on_l2_hit = promote_on_l2_hit
        self._async_l2_write = async_l2_write
        self._l2_healthy = True
    
    @property
    def name(self) -> str:
        return f"composite({self._l1.name}+{self._l2.name})"
    
    @property
    def is_distributed(self) -> bool:
        return self._l2.is_distributed
    
    async def initialize(self) -> None:
        """Initialize both backends."""
        await self._l1.initialize()
        await self._l2.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown both backends."""
        await self._l1.shutdown()
        await self._l2.shutdown()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Read-through: L1 → L2, promoting on L2 hit. L2 errors degrade gracefully."""
        # Try L1 first
        entry = await self._l1.get(key)
        if entry is not None:
            return entry
        
        # Try L2 with error resilience
        try:
            entry = await self._l2.get(key)
        except Exception as e:
            logger.warning(f"L2 GET failed (degrading to L1-only): {e}")
            self._l2_healthy = False
            return None
        
        if entry is not None:
            self._l2_healthy = True
            # Promote to L1
            if self._promote_on_l2_hit:
                ttl = int(entry.ttl_remaining) if entry.ttl_remaining else None
                await self._l1.set(
                    key,
                    entry.value,
                    ttl=ttl,
                    tags=entry.tags,
                    namespace=entry.namespace,
                )
            return entry
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Tuple[str, ...] = (),
        namespace: str = "default",
    ) -> None:
        """Write-through: write to L1 always, L2 with optional async mode."""
        # L1 always synchronous
        await self._l1.set(key, value, ttl=ttl, tags=tags, namespace=namespace)
        
        # L2: async fire-and-forget or synchronous with error handling
        if self._async_l2_write:
            asyncio.ensure_future(self._safe_l2_set(key, value, ttl, tags, namespace))
        else:
            await self._safe_l2_set(key, value, ttl, tags, namespace)
    
    async def _safe_l2_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int],
        tags: Tuple[str, ...],
        namespace: str,
    ) -> None:
        """L2 set with error resilience."""
        try:
            await self._l2.set(key, value, ttl=ttl, tags=tags, namespace=namespace)
            self._l2_healthy = True
        except Exception as e:
            logger.warning(f"L2 SET failed for key '{key}': {e}")
            self._l2_healthy = False
    
    async def delete(self, key: str) -> bool:
        """Invalidate in both levels."""
        l1_result = await self._l1.delete(key)
        l2_result = await self._l2.delete(key)
        return l1_result or l2_result
    
    async def exists(self, key: str) -> bool:
        """Check existence in either level."""
        if await self._l1.exists(key):
            return True
        return await self._l2.exists(key)
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear both levels."""
        l1_count = await self._l1.clear(namespace)
        l2_count = await self._l2.clear(namespace)
        return l1_count + l2_count
    
    async def keys(self, pattern: str = "*", namespace: Optional[str] = None) -> List[str]:
        """Union of keys from both levels."""
        l1_keys = set(await self._l1.keys(pattern, namespace))
        l2_keys = set(await self._l2.keys(pattern, namespace))
        return list(l1_keys | l2_keys)
    
    async def stats(self) -> CacheStats:
        """Combined stats from both levels."""
        l1_stats = await self._l1.stats()
        l2_stats = await self._l2.stats()
        
        return CacheStats(
            hits=l1_stats.hits + l2_stats.hits,
            misses=l2_stats.misses,  # Only L2 misses are true misses
            sets=l2_stats.sets,      # L2 sets == total sets
            deletes=l2_stats.deletes,
            evictions=l1_stats.evictions + l2_stats.evictions,
            errors=l1_stats.errors + l2_stats.errors,
            size=l1_stats.size + l2_stats.size,
            max_size=l1_stats.max_size + l2_stats.max_size,
            memory_bytes=l1_stats.memory_bytes + l2_stats.memory_bytes,
            backend=f"composite({l1_stats.backend}+{l2_stats.backend})",
            uptime_seconds=max(l1_stats.uptime_seconds, l2_stats.uptime_seconds),
        )
    
    async def delete_by_tags(self, tags: Set[str]) -> int:
        """Invalidate by tags in both levels."""
        l1_count = await self._l1.delete_by_tags(tags)
        l2_count = await self._l2.delete_by_tags(tags)
        return max(l1_count, l2_count)
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[CacheEntry]]:
        """Batch get with L1 → L2 fallback."""
        # Get from L1
        l1_results = await self._l1.get_many(keys)
        
        # Find L1 misses
        missed_keys = [k for k, v in l1_results.items() if v is None]
        
        if not missed_keys:
            return l1_results
        
        # Get misses from L2
        l2_results = await self._l2.get_many(missed_keys)
        
        # Promote L2 hits to L1
        if self._promote_on_l2_hit:
            for key, entry in l2_results.items():
                if entry is not None:
                    ttl = int(entry.ttl_remaining) if entry.ttl_remaining else None
                    await self._l1.set(key, entry.value, ttl=ttl, tags=entry.tags, namespace=entry.namespace)
        
        # Merge results
        final = {}
        for key in keys:
            final[key] = l1_results.get(key) or l2_results.get(key)
        return final
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> None:
        """Write-through batch set with async L2 option."""
        await self._l1.set_many(items, ttl=ttl, namespace=namespace)
        if self._async_l2_write:
            asyncio.ensure_future(self._safe_l2_set_many(items, ttl, namespace))
        else:
            await self._safe_l2_set_many(items, ttl, namespace)
    
    async def _safe_l2_set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int],
        namespace: str,
    ) -> None:
        """L2 batch set with error resilience."""
        try:
            await self._l2.set_many(items, ttl=ttl, namespace=namespace)
            self._l2_healthy = True
        except Exception as e:
            logger.warning(f"L2 SET_MANY failed: {e}")
            self._l2_healthy = False
    
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment in L2 (authoritative) and update L1."""
        result = await self._l2.increment(key, delta)
        if result is not None:
            # Update L1 with new value
            entry = await self._l2.get(key)
            if entry:
                ttl = int(entry.ttl_remaining) if entry.ttl_remaining else None
                await self._l1.set(key, result, ttl=ttl, namespace=entry.namespace)
        return result
    
    async def health_check(self) -> bool:
        """Check health of both levels."""
        l1_ok = True
        l2_ok = True
        
        if hasattr(self._l1, 'health_check'):
            l1_ok = await self._l1.health_check()
        if hasattr(self._l2, 'health_check'):
            l2_ok = await self._l2.health_check()
        
        self._l2_healthy = l2_ok
        return l1_ok  # L1 health is critical; L2 degradation is acceptable
    
    @property
    def l2_healthy(self) -> bool:
        """Whether the L2 backend is currently healthy."""
        return self._l2_healthy
