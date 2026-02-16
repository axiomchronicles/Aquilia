"""
AquilaCache — Decorators for declarative caching.

Provides ``@cached``, ``@cache_aside``, and ``@invalidate``
decorators for controller methods and service functions.

Features:
- Automatic cache key generation from function arguments
- Custom key functions for complex key strategies
- Conditional caching (skip caching based on result)
- Module-level CacheService singleton support
- Full introspection metadata on decorated functions
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional, Tuple, TypeVar

from .key_builder import DefaultKeyBuilder

logger = logging.getLogger("aquilia.cache.decorators")

T = TypeVar("T")

_key_builder = DefaultKeyBuilder()

# Module-level cache service registry for decorators
# Set via `set_default_cache_service()` during app startup
_default_cache_service: Optional[Any] = None


def set_default_cache_service(service: Any) -> None:
    """
    Register a module-level CacheService for decorator resolution.
    
    Called automatically during ``Server._setup_cache()``.
    Enables decorators to work on standalone functions (not just
    controller methods with ``self.cache``).
    
    Args:
        service: CacheService instance
    """
    global _default_cache_service
    _default_cache_service = service


def get_default_cache_service() -> Optional[Any]:
    """Get the module-level default CacheService."""
    return _default_cache_service


def cached(
    ttl: int = 300,
    namespace: str = "default",
    key: Optional[str] = None,
    key_func: Optional[Callable[..., str]] = None,
    tags: Tuple[str, ...] = (),
    unless: Optional[Callable[..., bool]] = None,
    condition: Optional[Callable[[Any], bool]] = None,
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        namespace: Cache namespace
        key: Explicit cache key (auto-generated from args if None)
        key_func: Custom key builder ``(func, args, kwargs) → str``
        tags: Tags for group invalidation
        unless: Callable ``(*args, **kwargs) → bool`` — skip caching if True
        condition: Callable ``(result) → bool`` — only cache if True.
                   Useful for skipping error results or empty lists.
        
    Usage::
    
        @cached(ttl=60, namespace="users")
        async def get_user(user_id: int):
            return await db.fetch_user(user_id)
        
        @cached(ttl=120, key="all_products", tags=("products",))
        async def list_products():
            return await db.fetch_all_products()
        
        # Custom key function
        @cached(ttl=60, key_func=lambda f, a, kw: f"user:{kw.get('user_id')}")
        async def get_user_profile(user_id: int):
            ...
        
        # Conditional caching — don't cache empty results
        @cached(ttl=60, condition=lambda result: result is not None and len(result) > 0)
        async def search_products(query: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get cache service from first arg (controller self)
            cache_service = _resolve_cache_service(args)
            
            if cache_service is None:
                # No cache available — just call the function
                return await _call_func(func, args, kwargs)
            
            # Check unless condition
            if unless and unless(*args, **kwargs):
                return await _call_func(func, args, kwargs)
            
            # Build cache key
            if key:
                cache_key = key
            elif key_func:
                cache_key = key_func(func, args, kwargs)
            else:
                # Skip 'self' arg for key generation
                skip = 1 if args and hasattr(args[0], "__class__") else 0
                cache_key = _key_builder.from_args(
                    namespace=namespace,
                    func_name=func.__qualname__,
                    args=args[skip:],
                    kwargs=kwargs,
                )
            
            # Try cache
            cached_value = await cache_service.get(cache_key, namespace=namespace)
            if cached_value is not None:
                return cached_value
            
            # Cache miss — compute
            result = await _call_func(func, args, kwargs)
            
            # Check condition before caching
            should_cache = True
            if condition is not None:
                try:
                    should_cache = condition(result)
                except Exception:
                    should_cache = False
            
            # Store result (only if not None and condition passes)
            if result is not None and should_cache:
                await cache_service.set(
                    cache_key,
                    result,
                    ttl=ttl,
                    namespace=namespace,
                    tags=tags,
                )
            
            return result
        
        # Attach metadata for introspection
        wrapper.__cached__ = True
        wrapper.__cache_ttl__ = ttl
        wrapper.__cache_namespace__ = namespace
        wrapper.__cache_tags__ = tags
        
        return wrapper
    return decorator


def cache_aside(
    ttl: int = 300,
    namespace: str = "default",
    tags: Tuple[str, ...] = (),
):
    """
    Cache-aside decorator — identical to @cached but semantically
    indicates the function is the authoritative data source.
    
    Usage::
    
        @cache_aside(ttl=120, namespace="products")
        async def find_product(product_id: int):
            return await db.find_product(product_id)
    """
    return cached(ttl=ttl, namespace=namespace, tags=tags)


def invalidate(
    *keys: str,
    namespace: str = "default",
    tags: Tuple[str, ...] = (),
):
    """
    Decorator to invalidate cache entries after function execution.
    
    Useful for write operations that should clear related cache entries.
    
    Args:
        *keys: Specific cache keys to invalidate
        namespace: Cache namespace
        tags: Tags to invalidate
        
    Usage::
    
        @invalidate("all_products", tags=("products",))
        async def create_product(data: dict):
            return await db.insert_product(data)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first
            result = await _call_func(func, args, kwargs)
            
            # Then invalidate
            cache_service = _resolve_cache_service(args)
            if cache_service:
                # Invalidate specific keys
                for key in keys:
                    await cache_service.delete(key, namespace=namespace)
                
                # Invalidate by tags
                if tags:
                    await cache_service.invalidate_tags(*tags)
            
            return result
        
        wrapper.__invalidates__ = True
        wrapper.__invalidate_keys__ = keys
        wrapper.__invalidate_tags__ = tags
        
        return wrapper
    return decorator


# ── Helpers ──────────────────────────────────────────────────────────

def _resolve_cache_service(args: tuple):
    """
    Try to find a CacheService from function arguments.
    
    Resolution order:
    1. ``self.cache`` on the first argument (controller/service)
    2. ``self._cache`` on the first argument
    3. Module-level default (set via ``set_default_cache_service()``)
    """
    from .service import CacheService
    
    if args and hasattr(args[0], "__class__"):
        obj = args[0]
        # Check for cache attribute on controller/service
        cache = getattr(obj, "cache", None)
        if isinstance(cache, CacheService):
            return cache
        
        # Check for _cache attribute
        cache = getattr(obj, "_cache", None)
        if isinstance(cache, CacheService):
            return cache
    
    # Fall back to module-level default
    if _default_cache_service is not None:
        return _default_cache_service
    
    return None


async def _call_func(func, args, kwargs):
    """Call a sync or async function."""
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)
