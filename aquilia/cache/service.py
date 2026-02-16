"""
AquilaCache — CacheService: High-level API for cache operations.

DI-injectable service that wraps the configured backend with:
- Namespace isolation
- Automatic key building
- TTL jitter (thundering herd prevention)
- Stampede prevention (singleflight for get_or_set)
- Fault handling with structured fault emission
- Get-or-set (cache-aside) pattern
- Bulk warmup / preloading
- Health checks
- Statistics and diagnostics

Registered in DI as a singleton, available for injection in
controllers, services, and middleware.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple, TypeVar

from .core import CacheBackend, CacheConfig, CacheEntry, CacheStats
from .key_builder import DefaultKeyBuilder
from .faults import (
    CacheBackendFault,
    CacheConnectionFault,
    CacheMissFault,
    CacheSerializationFault,
)

logger = logging.getLogger("aquilia.cache")

T = TypeVar("T")


class CacheService:
    """
    High-level cache service — the primary API for application code.
    
    Provides a clean, async interface for all cache operations with
    automatic key prefixing, namespace isolation, TTL jitter, 
    stampede prevention, and fault handling.
    
    Usage::
    
        # Via DI injection
        class UserController(Controller):
            def __init__(self, cache: CacheService):
                self.cache = cache
        
            @GET("/users/{id}")
            async def get_user(self, ctx, id: int):
                user = await self.cache.get(f"user:{id}")
                if user is None:
                    user = await self.repo.find(id)
                    await self.cache.set(f"user:{id}", user, ttl=300)
                return user
        
        # Cache-aside with stampede prevention
        user = await cache.get_or_set(
            "user:123",
            loader=lambda: repo.find(123),
            ttl=300,
        )
    """
    
    __slots__ = (
        "_backend",
        "_config",
        "_key_builder",
        "_default_ttl",
        "_default_namespace",
        "_key_prefix",
        "_initialized",
        "_inflight",
        "_inflight_lock",
        "_health_task",
        "_healthy",
    )
    
    def __init__(
        self,
        backend: CacheBackend,
        config: Optional[CacheConfig] = None,
    ):
        self._backend = backend
        self._config = config or CacheConfig()
        self._key_builder = DefaultKeyBuilder()
        self._default_ttl = self._config.default_ttl
        self._default_namespace = self._config.namespace
        self._key_prefix = self._config.key_prefix
        self._initialized = False
        
        # Stampede prevention: in-flight computation futures
        self._inflight: Dict[str, asyncio.Future] = {}
        self._inflight_lock = asyncio.Lock()
        
        # Health monitoring
        self._health_task: Optional[asyncio.Task] = None
        self._healthy = True
    
    # ── Lifecycle ────────────────────────────────────────────────────
    
    async def initialize(self) -> None:
        """Initialize the cache service and its backend."""
        if self._initialized:
            return
        try:
            await self._backend.initialize()
            self._initialized = True
            self._healthy = True
            logger.info(f"Cache service initialized (backend={self._backend.name})")
            
            # Start health check loop
            if self._config.health_check_interval > 0:
                try:
                    loop = asyncio.get_running_loop()
                    self._health_task = loop.create_task(self._health_check_loop())
                except RuntimeError:
                    pass
        except Exception as e:
            logger.error(f"Cache service initialization failed: {e}")
            self._healthy = False
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the cache service and its backend."""
        if not self._initialized:
            return
        
        # Cancel health check task
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Cancel any in-flight computations
        async with self._inflight_lock:
            for key, future in self._inflight.items():
                if not future.done():
                    future.cancel()
            self._inflight.clear()
        
        await self._backend.shutdown()
        self._initialized = False
        logger.info("Cache service shut down")
    
    # DI lifecycle aliases
    async def startup(self) -> None:
        """DI lifecycle startup hook."""
        await self.initialize()
    
    async def async_init(self) -> None:
        """DI async initialization hook."""
        await self.initialize()
    
    # ── Core Operations ──────────────────────────────────────────────
    
    async def get(
        self,
        key: str,
        namespace: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace override
            default: Value to return on miss
            
        Returns:
            Cached value or default. Never raises — returns default on error.
        """
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        
        try:
            entry = await self._backend.get(full_key)
            if entry is None:
                return default
            return entry.value
        except Exception as e:
            logger.warning(f"Cache GET failed for key '{key}': {e}")
            self._emit_fault(CacheBackendFault(
                backend=self._backend.name,
                operation="get",
                reason=str(e),
            ))
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Tuple[str, ...] = (),
    ) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            namespace: Optional namespace override
            tags: Tags for group invalidation
        """
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        
        # Apply TTL jitter to prevent thundering herd
        effective_ttl = self._config.apply_jitter(effective_ttl)
        
        try:
            await self._backend.set(
                full_key,
                value,
                ttl=effective_ttl,
                tags=tags,
                namespace=ns,
            )
        except Exception as e:
            logger.warning(f"Cache SET failed for key '{key}': {e}")
            self._emit_fault(CacheBackendFault(
                backend=self._backend.name,
                operation="set",
                reason=str(e),
            ))
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete a value from cache."""
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        return await self._backend.delete(full_key)
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists in cache."""
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        return await self._backend.exists(full_key)
    
    # ── Advanced Operations ──────────────────────────────────────────
    
    async def get_or_set(
        self,
        key: str,
        loader: Callable[[], Coroutine[Any, Any, T]],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Tuple[str, ...] = (),
    ) -> T:
        """
        Cache-aside pattern with stampede prevention.
        
        On a cache miss, only ONE concurrent caller computes the value.
        All other callers for the same key wait for the first computation
        to finish and reuse the result. This prevents the "thundering herd"
        or "cache stampede" problem.
        
        Args:
            key: Cache key
            loader: Async callable to produce the value on miss
            ttl: TTL in seconds
            namespace: Optional namespace
            tags: Tags for group invalidation
            
        Returns:
            Cached or freshly computed value
        """
        # Try cache first (fast path)
        value = await self.get(key, namespace=namespace)
        if value is not None:
            return value
        
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        
        # Stampede prevention: check for in-flight computation
        if self._config.stampede_prevention:
            async with self._inflight_lock:
                if full_key in self._inflight:
                    # Another coroutine is computing this value — wait for it
                    future = self._inflight[full_key]
                    stats = await self._backend.stats()
                    stats.stampede_joins += 1
                    
            # Wait outside the lock
            if full_key in self._inflight:
                try:
                    return await asyncio.wait_for(
                        asyncio.shield(self._inflight[full_key]),
                        timeout=self._config.stampede_timeout,
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning(f"Stampede wait timed out for key '{key}', computing independently")
                except Exception:
                    pass  # Fall through to compute independently
            
            # Register as the computing coroutine
            loop = asyncio.get_running_loop()
            future: asyncio.Future = loop.create_future()
            async with self._inflight_lock:
                self._inflight[full_key] = future
            
            try:
                # Compute the value
                if inspect.iscoroutinefunction(loader):
                    value = await loader()
                else:
                    value = loader()
                
                # Store in cache
                await self.set(key, value, ttl=ttl, namespace=namespace, tags=tags)
                
                # Resolve the future for waiting coroutines
                if not future.done():
                    future.set_result(value)
                
                return value
            except Exception as e:
                # Propagate exception to waiting coroutines
                if not future.done():
                    future.set_exception(e)
                raise
            finally:
                # Clean up in-flight entry
                async with self._inflight_lock:
                    self._inflight.pop(full_key, None)
        else:
            # No stampede prevention — simple get-or-set
            if inspect.iscoroutinefunction(loader):
                value = await loader()
            else:
                value = loader()
            
            await self.set(key, value, ttl=ttl, namespace=namespace, tags=tags)
            return value
    
    async def get_many(
        self,
        keys: List[str],
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Batch get multiple keys.
        
        Returns:
            Dict mapping keys to values (None for misses)
        """
        ns = namespace or self._default_namespace
        full_keys = [self._key_builder.build(ns, k, self._key_prefix) for k in keys]
        
        entries = await self._backend.get_many(full_keys)
        
        result = {}
        for original_key, full_key in zip(keys, full_keys):
            entry = entries.get(full_key)
            result[original_key] = entry.value if entry else None
        return result
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Batch set multiple key-value pairs."""
        ns = namespace or self._default_namespace
        effective_ttl = ttl if ttl is not None else self._default_ttl
        
        prefixed = {
            self._key_builder.build(ns, k, self._key_prefix): v
            for k, v in items.items()
        }
        
        await self._backend.set_many(prefixed, ttl=effective_ttl, namespace=ns)
    
    async def delete_many(self, keys: List[str], namespace: Optional[str] = None) -> int:
        """Batch delete multiple keys."""
        ns = namespace or self._default_namespace
        full_keys = [self._key_builder.build(ns, k, self._key_prefix) for k in keys]
        return await self._backend.delete_many(full_keys)
    
    async def invalidate_tags(self, *tags: str) -> int:
        """Invalidate all entries matching given tags."""
        return await self._backend.delete_by_tags(set(tags))
    
    async def invalidate_namespace(self, namespace: str) -> int:
        """Clear all entries in a namespace."""
        return await self._backend.clear(namespace)
    
    async def increment(
        self,
        key: str,
        delta: int = 1,
        namespace: Optional[str] = None,
    ) -> Optional[int]:
        """Atomically increment a numeric value."""
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        return await self._backend.increment(full_key, delta)
    
    async def decrement(
        self,
        key: str,
        delta: int = 1,
        namespace: Optional[str] = None,
    ) -> Optional[int]:
        """Atomically decrement a numeric value."""
        ns = namespace or self._default_namespace
        full_key = self._key_builder.build(ns, key, self._key_prefix)
        return await self._backend.decrement(full_key, delta)
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear all or namespace-scoped entries."""
        return await self._backend.clear(namespace)
    
    async def keys(
        self,
        pattern: str = "*",
        namespace: Optional[str] = None,
    ) -> List[str]:
        """List keys matching pattern."""
        return await self._backend.keys(pattern, namespace)
    
    async def stats(self) -> CacheStats:
        """Get cache statistics."""
        return await self._backend.stats()
    
    # ── Properties ───────────────────────────────────────────────────
    
    @property
    def backend(self) -> CacheBackend:
        """Access underlying backend."""
        return self._backend
    
    @property
    def config(self) -> CacheConfig:
        """Access cache configuration."""
        return self._config
    
    @property
    def is_distributed(self) -> bool:
        """Whether the backend supports distributed caching."""
        return self._backend.is_distributed
    
    @property
    def is_healthy(self) -> bool:
        """Whether the cache service is healthy."""
        return self._healthy and self._initialized
    
    # ── Extended Operations ──────────────────────────────────────────
    
    async def touch(self, key: str, ttl: int, namespace: Optional[str] = None) -> bool:
        """
        Refresh the TTL of a key without changing its value.
        
        Useful for extending cache lifetime on access patterns
        like session tokens or rate-limit counters.
        
        Args:
            key: Cache key
            ttl: New TTL in seconds
            namespace: Optional namespace override
            
        Returns:
            True if key existed and was refreshed
        """
        value = await self.get(key, namespace=namespace)
        if value is None:
            return False
        await self.set(key, value, ttl=ttl, namespace=namespace)
        return True
    
    async def warm(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Tuple[str, ...] = (),
    ) -> int:
        """
        Bulk-preload cache entries (cache warming).
        
        Used during application startup to preload hot data
        and avoid cold-start cache misses.
        
        Args:
            items: Dict of key→value pairs to preload
            ttl: TTL for all entries (uses default if None)
            namespace: Namespace for all entries
            tags: Tags for all entries
            
        Returns:
            Number of entries successfully warmed
            
        Usage::
        
            # Warm up on startup
            products = await db.fetch_hot_products()
            await cache.warm(
                {f"product:{p.id}": p.to_dict() for p in products},
                ttl=600,
                namespace="products",
                tags=("products",),
            )
        """
        count = 0
        for key, value in items.items():
            try:
                await self.set(key, value, ttl=ttl, namespace=namespace, tags=tags)
                count += 1
            except Exception as e:
                logger.warning(f"Cache warm failed for key '{key}': {e}")
        
        if count > 0:
            logger.info(f"Cache warmed with {count}/{len(items)} entries (ns={namespace or self._default_namespace})")
        return count
    
    async def health_check(self) -> bool:
        """
        Check if the cache backend is reachable and functioning.
        
        Returns:
            True if backend is healthy
        """
        try:
            # Test write + read + delete
            health_key = f"{self._key_prefix}__health_check__"
            await self._backend.set(health_key, "ok", ttl=10)
            entry = await self._backend.get(health_key)
            await self._backend.delete(health_key)
            self._healthy = entry is not None and entry.value == "ok"
            return self._healthy
        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            self._healthy = False
            return False
    
    async def get_or_default(
        self,
        key: str,
        default_factory: Callable[[], T],
        namespace: Optional[str] = None,
    ) -> T:
        """
        Get a cached value, or compute default (without caching it).
        
        Unlike ``get_or_set``, this does NOT store the result.
        Useful when you want fallback behavior without polluting cache.
        
        Args:
            key: Cache key
            default_factory: Callable to produce default value
            namespace: Optional namespace override
            
        Returns:
            Cached value or default
        """
        value = await self.get(key, namespace=namespace)
        if value is not None:
            return value
        if inspect.iscoroutinefunction(default_factory):
            return await default_factory()
        return default_factory()
    
    # ── Internal ─────────────────────────────────────────────────────
    
    def _emit_fault(self, fault: Any) -> None:
        """Emit a fault to the fault engine if available."""
        try:
            from aquilia.faults.core import FaultEngine
            engine = FaultEngine._current
            if engine:
                engine.emit(fault)
        except Exception:
            pass  # Fault emission is best-effort
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self._config.health_check_interval)
                was_healthy = self._healthy
                await self.health_check()
                
                if was_healthy and not self._healthy:
                    logger.error("Cache backend became unhealthy")
                    self._emit_fault(CacheConnectionFault(
                        backend=self._backend.name,
                        reason="Health check failed",
                    ))
                elif not was_healthy and self._healthy:
                    logger.info("Cache backend recovered")
            except asyncio.CancelledError:
                break
            except Exception:
                pass
