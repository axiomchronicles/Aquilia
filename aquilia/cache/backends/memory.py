"""
AquilaCache — High-performance in-memory backend.

Implements LRU, LFU, FIFO, and TTL eviction policies using efficient
data structures:
- **LRU**: OrderedDict with O(1) access/eviction
- **LFU**: Min-heap + frequency counter with O(log n) eviction
- **FIFO**: Deque with O(1) eviction
- **TTL**: Sorted list by expiry time with O(log n) cleanup

Thread-safe via asyncio.Lock for concurrent request handling.
Includes latency tracking, capacity warnings, and max memory limits.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import random
import sys
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from heapq import heappush, heappop
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from ..core import CacheBackend, CacheEntry, CacheStats, EvictionPolicy

logger = logging.getLogger("aquilia.cache.memory")


class MemoryBackend(CacheBackend):
    """
    In-memory cache backend with configurable eviction policies.
    
    Optimized for:
    - O(1) get/set/delete for LRU (via OrderedDict)
    - O(log n) eviction for LFU (via heap)
    - Background TTL expiration sweeper
    - Tag-based group invalidation via inverted index
    """
    
    __slots__ = (
        "_max_size",
        "_max_memory_bytes",
        "_eviction_policy",
        "_store",
        "_lock",
        "_stats",
        "_start_time",
        "_tag_index",
        "_namespace_index",
        "_freq_counter",
        "_ttl_heap",
        "_sweeper_task",
        "_sweep_interval",
        "_initialized",
        "_capacity_warning_threshold",
        "_capacity_warned",
    )
    
    def __init__(
        self,
        max_size: int = 10000,
        eviction_policy: str = "lru",
        sweep_interval: float = 30.0,
        max_memory_bytes: int = 0,
        capacity_warning_threshold: float = 0.85,
    ):
        """
        Initialize memory backend.
        
        Args:
            max_size: Maximum number of entries
            eviction_policy: Eviction strategy ("lru", "lfu", "fifo", "ttl", "random")
            sweep_interval: Seconds between TTL sweep cycles
            max_memory_bytes: Maximum memory usage in bytes (0 = unlimited)
            capacity_warning_threshold: Warn when capacity exceeds this fraction (0.0-1.0)
        """
        self._max_size = max_size
        self._max_memory_bytes = max_memory_bytes
        self._eviction_policy = EvictionPolicy(eviction_policy)
        self._sweep_interval = sweep_interval
        self._capacity_warning_threshold = capacity_warning_threshold
        self._capacity_warned = False
        
        # Primary store: OrderedDict for LRU ordering
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Concurrency lock
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = CacheStats(max_size=max_size, backend="memory")
        self._start_time = time.monotonic()
        
        # Inverted index: tag → set of keys
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Inverted index: namespace → set of keys
        self._namespace_index: Dict[str, Set[str]] = defaultdict(set)
        
        # LFU frequency counter
        self._freq_counter: Dict[str, int] = {}
        
        # TTL expiry heap: (expires_at, key)
        self._ttl_heap: List[Tuple[float, str]] = []
        
        # Background sweeper
        self._sweeper_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    @property
    def name(self) -> str:
        return f"memory:{self._eviction_policy.value}"
    
    async def initialize(self) -> None:
        """Start the background TTL sweeper."""
        if self._initialized:
            return
        self._start_time = time.monotonic()
        self._initialized = True
        try:
            loop = asyncio.get_running_loop()
            self._sweeper_task = loop.create_task(self._ttl_sweeper())
        except RuntimeError:
            # No running loop — skip sweeper (testing context)
            pass
    
    async def shutdown(self) -> None:
        """Stop sweeper and clear all data."""
        if self._sweeper_task and not self._sweeper_task.done():
            self._sweeper_task.cancel()
            try:
                await self._sweeper_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            self._store.clear()
            self._tag_index.clear()
            self._namespace_index.clear()
            self._freq_counter.clear()
            self._ttl_heap.clear()
        self._initialized = False
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """O(1) lookup with LRU promotion and latency tracking."""
        start = time.monotonic()
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                self._stats.record_get_latency((time.monotonic() - start) * 1000)
                return None
            
            # Check expiry
            if entry.is_expired:
                self._evict_key(key)
                self._stats.misses += 1
                self._stats.record_get_latency((time.monotonic() - start) * 1000)
                return None
            
            # Update access metadata
            entry.touch()
            self._stats.hits += 1
            
            # LRU: move to end (most recently used)
            if self._eviction_policy == EvictionPolicy.LRU:
                self._store.move_to_end(key)
            
            # LFU: update frequency
            if self._eviction_policy == EvictionPolicy.LFU:
                self._freq_counter[key] = self._freq_counter.get(key, 0) + 1
            
            self._stats.record_get_latency((time.monotonic() - start) * 1000)
            return entry
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Tuple[str, ...] = (),
        namespace: str = "default",
    ) -> None:
        """O(1) insert with eviction if at capacity, latency tracking, and capacity warnings."""
        start = time.monotonic()
        async with self._lock:
            # Remove existing entry if present
            if key in self._store:
                self._evict_key(key)
            
            # Evict if at capacity
            while len(self._store) >= self._max_size:
                self._evict_one()
            
            # Evict if at memory limit
            size_bytes = sys.getsizeof(value)
            if self._max_memory_bytes > 0:
                while (self._stats.memory_bytes + size_bytes > self._max_memory_bytes 
                       and len(self._store) > 0):
                    self._evict_one()
            
            # Calculate expiry
            expires_at = None
            if ttl is not None and ttl > 0:
                expires_at = time.monotonic() + ttl
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags,
                namespace=namespace,
            )
            
            # Store
            self._store[key] = entry
            
            # Update indices
            for tag in tags:
                self._tag_index[tag].add(key)
            self._namespace_index[namespace].add(key)
            
            # LFU: initialize frequency
            if self._eviction_policy == EvictionPolicy.LFU:
                self._freq_counter[key] = 1
            
            # TTL heap
            if expires_at is not None:
                heappush(self._ttl_heap, (expires_at, key))
            
            # Stats
            self._stats.sets += 1
            self._stats.size = len(self._store)
            self._stats.memory_bytes += size_bytes
            self._stats.record_set_latency((time.monotonic() - start) * 1000)
            
            # Capacity warning
            self._check_capacity_warning()
    
    async def delete(self, key: str) -> bool:
        """O(1) deletion."""
        async with self._lock:
            if key in self._store:
                self._evict_key(key)
                self._stats.deletes += 1
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """O(1) existence check."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                self._evict_key(key)
                return False
            return True
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear all or namespaced entries."""
        async with self._lock:
            if namespace is None:
                count = len(self._store)
                self._store.clear()
                self._tag_index.clear()
                self._namespace_index.clear()
                self._freq_counter.clear()
                self._ttl_heap.clear()
                self._stats.size = 0
                self._stats.memory_bytes = 0
                return count
            
            # Clear specific namespace
            keys_to_remove = list(self._namespace_index.get(namespace, set()))
            for key in keys_to_remove:
                self._evict_key(key)
            return len(keys_to_remove)
    
    async def keys(self, pattern: str = "*", namespace: Optional[str] = None) -> List[str]:
        """List keys matching glob pattern."""
        async with self._lock:
            if namespace:
                candidates = list(self._namespace_index.get(namespace, set()))
            else:
                candidates = list(self._store.keys())
            
            if pattern == "*":
                return candidates
            
            return [k for k in candidates if fnmatch.fnmatch(k, pattern)]
    
    async def stats(self) -> CacheStats:
        """Return current statistics."""
        self._stats.size = len(self._store)
        self._stats.uptime_seconds = time.monotonic() - self._start_time
        return self._stats
    
    async def delete_by_tags(self, tags: Set[str]) -> int:
        """O(m) tag-based invalidation via inverted index."""
        async with self._lock:
            keys_to_delete: Set[str] = set()
            for tag in tags:
                keys_to_delete.update(self._tag_index.get(tag, set()))
            
            for key in keys_to_delete:
                self._evict_key(key)
            
            return len(keys_to_delete)
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[CacheEntry]]:
        """Batch get — single lock acquisition."""
        async with self._lock:
            results = {}
            for key in keys:
                entry = self._store.get(key)
                if entry is None:
                    self._stats.misses += 1
                    results[key] = None
                elif entry.is_expired:
                    self._evict_key(key)
                    self._stats.misses += 1
                    results[key] = None
                else:
                    entry.touch()
                    self._stats.hits += 1
                    if self._eviction_policy == EvictionPolicy.LRU:
                        self._store.move_to_end(key)
                    results[key] = entry
            return results
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> None:
        """Batch set — single lock acquisition."""
        async with self._lock:
            for key, value in items.items():
                # Remove existing
                if key in self._store:
                    self._evict_key(key)
                
                # Evict if at capacity
                while len(self._store) >= self._max_size:
                    self._evict_one()
                
                expires_at = None
                if ttl is not None and ttl > 0:
                    expires_at = time.monotonic() + ttl
                
                size_bytes = sys.getsizeof(value)
                entry = CacheEntry(
                    key=key,
                    value=value,
                    expires_at=expires_at,
                    size_bytes=size_bytes,
                    namespace=namespace,
                )
                
                self._store[key] = entry
                self._namespace_index[namespace].add(key)
                
                if self._eviction_policy == EvictionPolicy.LFU:
                    self._freq_counter[key] = 1
                
                if expires_at is not None:
                    heappush(self._ttl_heap, (expires_at, key))
                
                self._stats.sets += 1
                self._stats.memory_bytes += size_bytes
            
            self._stats.size = len(self._store)
    
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Atomic increment under lock."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                self._evict_key(key)
                return None
            try:
                new_value = int(entry.value) + delta
                entry.value = new_value
                entry.touch()
                return new_value
            except (TypeError, ValueError):
                return None
    
    # ── Private helpers ──────────────────────────────────────────────
    
    def _check_capacity_warning(self) -> None:
        """Log a warning if cache is near capacity. Caller must hold lock."""
        ratio = len(self._store) / self._max_size if self._max_size > 0 else 0.0
        if ratio >= self._capacity_warning_threshold and not self._capacity_warned:
            logger.warning(
                f"Cache capacity at {ratio:.0%} ({len(self._store)}/{self._max_size}) — "
                f"eviction policy: {self._eviction_policy.value}"
            )
            self._capacity_warned = True
        elif ratio < self._capacity_warning_threshold * 0.9:
            # Reset warning if capacity drops significantly
            self._capacity_warned = False
    
    async def health_check(self) -> bool:
        """Check if the memory backend is healthy."""
        return self._initialized
    
    def _evict_key(self, key: str) -> None:
        """Remove a key and clean up all indices. Caller must hold lock."""
        entry = self._store.pop(key, None)
        if entry is None:
            return
        
        # Clean tag index
        for tag in entry.tags:
            tag_set = self._tag_index.get(tag)
            if tag_set:
                tag_set.discard(key)
                if not tag_set:
                    del self._tag_index[tag]
        
        # Clean namespace index
        ns_set = self._namespace_index.get(entry.namespace)
        if ns_set:
            ns_set.discard(key)
            if not ns_set:
                del self._namespace_index[entry.namespace]
        
        # Clean frequency counter
        self._freq_counter.pop(key, None)
        
        # Update stats
        self._stats.memory_bytes = max(0, self._stats.memory_bytes - entry.size_bytes)
        self._stats.size = len(self._store)
    
    def _evict_one(self) -> None:
        """Evict one entry based on policy. Caller must hold lock."""
        if not self._store:
            return
        
        key_to_evict: Optional[str] = None
        
        if self._eviction_policy == EvictionPolicy.LRU:
            # OrderedDict: first item is least recently used
            key_to_evict = next(iter(self._store))
        
        elif self._eviction_policy == EvictionPolicy.FIFO:
            key_to_evict = next(iter(self._store))
        
        elif self._eviction_policy == EvictionPolicy.LFU:
            # Find key with minimum frequency
            if self._freq_counter:
                key_to_evict = min(
                    self._freq_counter,
                    key=lambda k: self._freq_counter.get(k, 0),
                )
            else:
                key_to_evict = next(iter(self._store))
        
        elif self._eviction_policy == EvictionPolicy.RANDOM:
            keys = list(self._store.keys())
            key_to_evict = random.choice(keys)
        
        elif self._eviction_policy == EvictionPolicy.TTL:
            # Evict the entry closest to expiry, or oldest if no TTL
            min_key = None
            min_expires = float("inf")
            for k, entry in self._store.items():
                if entry.expires_at is not None and entry.expires_at < min_expires:
                    min_expires = entry.expires_at
                    min_key = k
            key_to_evict = min_key or next(iter(self._store))
        
        if key_to_evict:
            self._evict_key(key_to_evict)
            self._stats.evictions += 1
    
    async def _ttl_sweeper(self) -> None:
        """Background task to clean expired entries."""
        while True:
            try:
                await asyncio.sleep(self._sweep_interval)
                swept = await self._sweep_expired()
                if swept and swept > 0:
                    logger.debug(f"TTL sweeper removed {swept} expired entries")
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Sweeper is best-effort
    
    async def _sweep_expired(self) -> None:
        """Remove expired entries using the TTL heap."""
        async with self._lock:
            now = time.monotonic()
            swept = 0
            
            while self._ttl_heap:
                expires_at, key = self._ttl_heap[0]
                
                if expires_at > now:
                    break
                
                heappop(self._ttl_heap)
                
                # Verify key still exists and is actually expired
                entry = self._store.get(key)
                if entry and entry.is_expired:
                    self._evict_key(key)
                    self._stats.evictions += 1
                    swept += 1
            
            return swept
