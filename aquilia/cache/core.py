"""
AquilaCache — Core types, protocols, and data structures.

Defines the fundamental contracts, data structures, and algorithms
that power the caching subsystem.
"""

from __future__ import annotations

import random
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


T = TypeVar("T")


# ============================================================================
# Eviction Policies
# ============================================================================

class EvictionPolicy(str, Enum):
    """Cache eviction strategies."""
    LRU = "lru"       # Least Recently Used
    LFU = "lfu"       # Least Frequently Used
    TTL = "ttl"       # Time-To-Live only (no capacity eviction)
    FIFO = "fifo"     # First In First Out
    RANDOM = "random" # Random eviction


# ============================================================================
# Cache Entry
# ============================================================================

@dataclass(slots=True)
class CacheEntry:
    """
    Single cache entry with metadata.
    
    Compact, slotted dataclass for minimal memory overhead.
    """
    key: str
    value: Any
    created_at: float = field(default_factory=time.monotonic)
    expires_at: Optional[float] = None
    last_accessed: float = field(default_factory=time.monotonic)
    access_count: int = 0
    size_bytes: int = 0
    tags: Tuple[str, ...] = ()
    namespace: str = "default"
    version: int = 1
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at
    
    @property
    def ttl_remaining(self) -> Optional[float]:
        """Remaining TTL in seconds, or None if no expiry."""
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.monotonic()
        return max(0.0, remaining)
    
    @property
    def age(self) -> float:
        """Age of entry in seconds since creation."""
        return time.monotonic() - self.created_at
    
    def touch(self) -> None:
        """Update access metadata."""
        self.last_accessed = time.monotonic()
        self.access_count += 1
    
    def __repr__(self) -> str:
        ttl = f", ttl={self.ttl_remaining:.1f}s" if self.ttl_remaining else ""
        return f"<CacheEntry key={self.key!r} ns={self.namespace!r} hits={self.access_count}{ttl}>"


# ============================================================================
# Cache Stats
# ============================================================================

@dataclass
class CacheStats:
    """Aggregate cache statistics for observability."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    stampede_joins: int = 0      # Times a stampede was prevented
    size: int = 0               # Current number of entries
    max_size: int = 0           # Maximum capacity
    memory_bytes: int = 0       # Estimated memory usage
    backend: str = "unknown"
    uptime_seconds: float = 0.0
    
    # Latency tracking (in milliseconds)
    _get_latencies: list = field(default_factory=list, repr=False)
    _set_latencies: list = field(default_factory=list, repr=False)
    _max_latency_samples: int = field(default=1000, repr=False)
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100.0
    
    @property
    def total_operations(self) -> int:
        """Total number of operations."""
        return self.hits + self.misses + self.sets + self.deletes
    
    @property
    def avg_get_latency_ms(self) -> float:
        """Average GET latency in milliseconds."""
        if not self._get_latencies:
            return 0.0
        return sum(self._get_latencies) / len(self._get_latencies)
    
    @property
    def avg_set_latency_ms(self) -> float:
        """Average SET latency in milliseconds."""
        if not self._set_latencies:
            return 0.0
        return sum(self._set_latencies) / len(self._set_latencies)
    
    @property
    def p99_get_latency_ms(self) -> float:
        """P99 GET latency in milliseconds."""
        if not self._get_latencies:
            return 0.0
        sorted_lat = sorted(self._get_latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    def record_get_latency(self, latency_ms: float) -> None:
        """Record a GET operation latency sample."""
        self._get_latencies.append(latency_ms)
        if len(self._get_latencies) > self._max_latency_samples:
            self._get_latencies.pop(0)
    
    def record_set_latency(self, latency_ms: float) -> None:
        """Record a SET operation latency sample."""
        self._set_latencies.append(latency_ms)
        if len(self._set_latencies) > self._max_latency_samples:
            self._set_latencies.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for diagnostics/trace."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "errors": self.errors,
            "stampede_joins": self.stampede_joins,
            "hit_rate": round(self.hit_rate, 2),
            "size": self.size,
            "max_size": self.max_size,
            "memory_bytes": self.memory_bytes,
            "backend": self.backend,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "total_operations": self.total_operations,
            "avg_get_latency_ms": round(self.avg_get_latency_ms, 3),
            "avg_set_latency_ms": round(self.avg_set_latency_ms, 3),
            "p99_get_latency_ms": round(self.p99_get_latency_ms, 3),
        }


# ============================================================================
# Cache Configuration
# ============================================================================

@dataclass
class CacheConfig:
    """
    Cache subsystem configuration.
    
    Loaded from workspace config via ``ConfigLoader.get_cache_config()``.
    """
    enabled: bool = True
    backend: str = "memory"          # "memory", "redis", "composite", "null"
    default_ttl: int = 300           # Default TTL in seconds (5 minutes)
    max_size: int = 10000            # Max entries for memory backend
    eviction_policy: str = "lru"     # "lru", "lfu", "ttl", "fifo", "random"
    namespace: str = "default"       # Default namespace
    key_prefix: str = "aq:"          # Key prefix for all entries
    serializer: str = "json"         # "json", "pickle", "msgpack"
    
    # TTL jitter — prevents thundering herd on mass expiry
    ttl_jitter: bool = True          # Add randomness to TTL
    ttl_jitter_percent: float = 0.1  # ±10% jitter by default
    
    # Stampede prevention — singleflight for get_or_set
    stampede_prevention: bool = True  # Coalesce concurrent loads for same key
    stampede_timeout: float = 30.0    # Max wait for in-flight computation
    
    # Health check
    health_check_interval: float = 60.0   # Seconds between health checks (0 = disabled)
    
    # Capacity warnings
    capacity_warning_threshold: float = 0.85  # Warn at 85% capacity
    
    # Key versioning
    key_version: int = 1             # Increment to mass-invalidate all keys
    
    # Redis-specific
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0
    redis_retry_on_timeout: bool = True
    redis_decode_responses: bool = True
    
    # Composite (L1/L2) specific
    l1_max_size: int = 1000          # L1 (memory) size
    l1_ttl: int = 60                 # L1 TTL in seconds
    l2_backend: str = "redis"        # L2 backend type
    l2_async_write: bool = False     # Fire-and-forget L2 writes
    
    # Middleware
    middleware_enabled: bool = False
    middleware_cacheable_methods: Tuple[str, ...] = ("GET", "HEAD")
    middleware_default_ttl: int = 60
    middleware_vary_headers: Tuple[str, ...] = ("Accept", "Accept-Encoding")
    middleware_stale_while_revalidate: int = 0  # Serve stale content while refreshing (seconds)
    
    # Observability
    trace_enabled: bool = True
    metrics_enabled: bool = True
    log_level: str = "WARNING"
    
    def apply_jitter(self, ttl: int) -> int:
        """
        Apply TTL jitter to prevent thundering herd.
        
        Returns TTL with random ±jitter_percent variation.
        """
        if not self.ttl_jitter or ttl <= 0:
            return ttl
        jitter = int(ttl * self.ttl_jitter_percent)
        if jitter == 0:
            return ttl
        return ttl + random.randint(-jitter, jitter)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "default_ttl": self.default_ttl,
            "max_size": self.max_size,
            "eviction_policy": self.eviction_policy,
            "namespace": self.namespace,
            "key_prefix": self.key_prefix,
            "serializer": self.serializer,
            "ttl_jitter": self.ttl_jitter,
            "stampede_prevention": self.stampede_prevention,
            "key_version": self.key_version,
            "redis_url": self.redis_url,
            "redis_max_connections": self.redis_max_connections,
            "l1_max_size": self.l1_max_size,
            "l1_ttl": self.l1_ttl,
            "l2_backend": self.l2_backend,
            "l2_async_write": self.l2_async_write,
            "middleware_enabled": self.middleware_enabled,
            "middleware_stale_while_revalidate": self.middleware_stale_while_revalidate,
            "trace_enabled": self.trace_enabled,
            "metrics_enabled": self.metrics_enabled,
            "health_check_interval": self.health_check_interval,
            "capacity_warning_threshold": self.capacity_warning_threshold,
        }


# ============================================================================
# Cache Serializer Protocol
# ============================================================================

@runtime_checkable
class CacheSerializer(Protocol):
    """Protocol for cache value serialization."""
    
    def serialize(self, value: Any) -> bytes:
        """Serialize a value to bytes."""
        ...
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to a value."""
        ...


# ============================================================================
# Cache Key Builder Protocol
# ============================================================================

@runtime_checkable
class CacheKeyBuilder(Protocol):
    """Protocol for building cache keys."""
    
    def build(self, namespace: str, key: str, prefix: str = "") -> str:
        """
        Build a fully qualified cache key.
        
        Args:
            namespace: Cache namespace
            key: Raw key
            prefix: Global prefix
            
        Returns:
            Qualified cache key string
        """
        ...


# ============================================================================
# Cache Backend Protocol
# ============================================================================

class CacheBackend(ABC):
    """
    Abstract cache backend — defines the storage contract.
    
    All backends must implement async lifecycle and CRUD operations.
    Backends are responsible for their own eviction and TTL enforcement.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize backend resources (connection pools, etc.)."""
        ...
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up backend resources."""
        ...
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """
        Retrieve entry by key.
        
        Returns None if key doesn't exist or has expired.
        """
        ...
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Tuple[str, ...] = (),
        namespace: str = "default",
    ) -> None:
        """
        Store a value with optional TTL and tags.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None = no expiry)
            tags: Tags for group invalidation
            namespace: Logical namespace
        """
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete entry by key.
        
        Returns True if the key existed and was deleted.
        """
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        ...
    
    @abstractmethod
    async def clear(self, namespace: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            namespace: If provided, clear only entries in this namespace.
                       If None, clear all entries.
                       
        Returns:
            Number of entries cleared.
        """
        ...
    
    @abstractmethod
    async def keys(self, pattern: str = "*", namespace: Optional[str] = None) -> List[str]:
        """
        List keys matching pattern.
        
        Args:
            pattern: Glob-style pattern
            namespace: Optional namespace filter
            
        Returns:
            List of matching keys
        """
        ...
    
    @abstractmethod
    async def stats(self) -> CacheStats:
        """Get backend statistics."""
        ...
    
    async def delete_by_tags(self, tags: Set[str]) -> int:
        """
        Delete all entries matching any of the given tags.
        
        Default implementation scans all keys. Backends may override
        with more efficient implementations.
        
        Returns:
            Number of entries deleted.
        """
        count = 0
        all_keys = await self.keys()
        for key in all_keys:
            entry = await self.get(key)
            if entry and set(entry.tags) & tags:
                if await self.delete(key):
                    count += 1
        return count
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[CacheEntry]]:
        """
        Batch get multiple keys.
        
        Default implementation calls get() for each key.
        Backends may override with pipelined implementations.
        """
        results = {}
        for key in keys:
            results[key] = await self.get(key)
        return results
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> None:
        """
        Batch set multiple key-value pairs.
        
        Default implementation calls set() for each item.
        """
        for key, value in items.items():
            await self.set(key, value, ttl=ttl, namespace=namespace)
    
    async def delete_many(self, keys: List[str]) -> int:
        """
        Batch delete multiple keys.
        
        Returns number of keys actually deleted.
        """
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count
    
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Atomically increment a numeric value.
        
        Returns the new value, or None if key doesn't exist.
        Default implementation is non-atomic.
        """
        entry = await self.get(key)
        if entry is None:
            return None
        try:
            new_value = int(entry.value) + delta
            await self.set(
                key,
                new_value,
                ttl=int(entry.ttl_remaining) if entry.ttl_remaining else None,
                tags=entry.tags,
                namespace=entry.namespace,
            )
            return new_value
        except (TypeError, ValueError):
            return None
    
    async def decrement(self, key: str, delta: int = 1) -> Optional[int]:
        """Atomically decrement a numeric value."""
        return await self.increment(key, -delta)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for diagnostics."""
        ...
    
    @property
    def is_distributed(self) -> bool:
        """Whether this backend supports distributed caching."""
        return False
