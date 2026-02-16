"""
AquilaCache — Production-grade, async-first caching system for Aquilia.

Provides a multi-backend, DI-integrated, fault-aware caching layer with:
- **Multiple backends**: Memory (LRU/LFU/TTL), Redis, Composite (L1/L2)
- **Serialization**: Pluggable serializers (JSON, msgpack, pickle)
- **DI integration**: Auto-registered providers, injectable CacheService
- **Fault domain**: Typed cache faults with recovery strategies
- **Effect system**: CacheEffect for handler capability declarations
- **Middleware**: Response caching middleware with ETags
- **Trace integration**: Cache stats in .aquilia/diagnostics.json
- **CLI commands**: ``aq cache stats``, ``aq cache clear``, ``aq cache keys``
- **Decorators**: ``@cached``, ``@cache_aside``, ``@invalidate``
- **Key building**: Deterministic, collision-free key generation

Architecture follows Aquilia conventions:
    Integration.cache() → ConfigLoader → Server._setup_cache() → DI → CacheService

Usage::

    from aquilia.cache import CacheService, cached, MemoryBackend

    # Via DI (recommended)
    class ProductController(Controller):
        def __init__(self, cache: CacheService):
            self.cache = cache

        @GET("/products/{id}")
        async def get_product(self, ctx, id: int):
            return await self.cache.get_or_set(
                f"product:{id}",
                lambda: self.repo.find(id),
                ttl=300,
            )

    # Via decorator
    @cached(ttl=60, namespace="api")
    async def get_users():
        return await db.fetch_all("SELECT * FROM users")
"""

__version__ = "1.0.0"

from .core import (
    CacheBackend,
    CacheEntry,
    CacheStats,
    CacheConfig,
    CacheSerializer,
    CacheKeyBuilder,
    EvictionPolicy,
)

from .backends.memory import MemoryBackend
from .backends.redis import RedisBackend
from .backends.composite import CompositeBackend
from .backends.null import NullBackend

from .service import CacheService

from .decorators import cached, cache_aside, invalidate, set_default_cache_service, get_default_cache_service

from .serializers import (
    JsonCacheSerializer,
    PickleCacheSerializer,
    MsgpackCacheSerializer,
)

from .faults import (
    CacheFault,
    CacheMissFault,
    CacheConnectionFault,
    CacheSerializationFault,
    CacheCapacityFault,
    CacheBackendFault,
    CacheConfigFault,
    CacheStampedeFault,
    CacheHealthFault,
)

from .middleware import CacheMiddleware

from .key_builder import DefaultKeyBuilder, HashKeyBuilder

__all__ = [
    # Core
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "CacheConfig",
    "CacheSerializer",
    "CacheKeyBuilder",
    "EvictionPolicy",
    # Backends
    "MemoryBackend",
    "RedisBackend",
    "CompositeBackend",
    "NullBackend",
    # Service
    "CacheService",
    # Decorators
    "cached",
    "cache_aside",
    "invalidate",
    # Serializers
    "JsonCacheSerializer",
    "PickleCacheSerializer",
    "MsgpackCacheSerializer",
    # Faults
    "CacheFault",
    "CacheMissFault",
    "CacheConnectionFault",
    "CacheSerializationFault",
    "CacheCapacityFault",
    "CacheBackendFault",
    "CacheConfigFault",
    "CacheStampedeFault",
    "CacheHealthFault",
    # Middleware
    "CacheMiddleware",
    # Key builders
    "DefaultKeyBuilder",
    "HashKeyBuilder",
    # Decorator utilities
    "set_default_cache_service",
    "get_default_cache_service",
]
