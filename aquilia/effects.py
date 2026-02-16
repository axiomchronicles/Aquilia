"""
Effect system - Typed capabilities with providers.
Effects represent side-effects (DB, Cache, Queue) that handlers declare.
"""

from typing import Any, Generic, TypeVar, Protocol, Optional
from abc import ABC, abstractmethod
from enum import Enum


T = TypeVar("T")


class EffectKind(Enum):
    """Categories of effects."""
    DB = "db"
    CACHE = "cache"
    QUEUE = "queue"
    HTTP = "http"
    STORAGE = "storage"
    CUSTOM = "custom"


class Effect(Generic[T]):
    """
    Effect token representing a capability.
    
    Example:
        DBTx['read']  - Read-only database transaction
        DBTx['write'] - Read-write database transaction
        Cache['user'] - User cache namespace
    """
    
    def __init__(self, name: str, mode: Optional[T] = None, kind: EffectKind = EffectKind.CUSTOM):
        self.name = name
        self.mode = mode
        self.kind = kind
    
    def __class_getitem__(cls, mode):
        """Support DBTx['read'] syntax."""
        instance = cls.__new__(cls)
        instance.mode = mode
        return instance
    
    def __repr__(self):
        if self.mode:
            return f"Effect({self.name}[{self.mode}])"
        return f"Effect({self.name})"


class EffectProvider(ABC):
    """
    Base class for effect providers.
    Providers implement the actual capability (e.g., database connection).
    """
    
    @abstractmethod
    async def initialize(self):
        """Initialize the provider (called once at startup)."""
        pass
    
    @abstractmethod
    async def acquire(self, mode: Optional[str] = None) -> Any:
        """
        Acquire a resource for this effect (called per-request).
        
        Args:
            mode: Optional mode specifier (e.g., 'read', 'write')
            
        Returns:
            Resource handle
        """
        pass
    
    @abstractmethod
    async def release(self, resource: Any, success: bool = True):
        """
        Release the resource (called at end of request).
        
        Args:
            resource: Resource handle from acquire()
            success: Whether request completed successfully
        """
        pass
    
    async def finalize(self):
        """Finalize provider (called at shutdown)."""
        pass


class DBTx(Effect):
    """Database transaction effect."""
    
    def __init__(self, mode: str = "read"):
        super().__init__("DBTx", mode=mode, kind=EffectKind.DB)


class CacheEffect(Effect):
    """Cache effect."""
    
    def __init__(self, namespace: str = "default"):
        super().__init__("Cache", mode=namespace, kind=EffectKind.CACHE)


class QueueEffect(Effect):
    """Queue/message publish effect."""
    
    def __init__(self, topic: Optional[str] = None):
        super().__init__("Queue", mode=topic, kind=EffectKind.QUEUE)


# Example providers

class DBTxProvider(EffectProvider):
    """Example database transaction provider."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool."""
        # In real implementation, create connection pool
        self.pool = {"initialized": True}
    
    async def acquire(self, mode: Optional[str] = None):
        """Acquire database connection."""
        # In real implementation, get connection from pool
        return {
            "connection": self.pool,
            "mode": mode or "read",
            "transaction": None,
        }
    
    async def release(self, resource: Any, success: bool = True):
        """Release connection and commit/rollback transaction."""
        if success:
            # Commit transaction
            pass
        else:
            # Rollback transaction
            pass
        # Return connection to pool


class CacheProvider(EffectProvider):
    """
    Cache effect provider backed by the real CacheService.

    If a :class:`~aquilia.cache.service.CacheService` is provided it is used
    for all acquire/release operations; otherwise falls back to a simple
    in-memory dict (useful in tests or when the cache subsystem is disabled).
    """

    def __init__(self, backend: str = "memory", *, cache_service: Any = None):
        self.backend = backend
        self._svc = cache_service  # Optional CacheService
        self._fallback: dict = {}

    async def initialize(self):
        """Initialize cache backend."""
        if self._svc is not None:
            try:
                await self._svc.initialize()
            except Exception:
                pass  # CacheService.initialize is idempotent

    async def acquire(self, mode: Optional[str] = None):
        """Get cache handle for namespace."""
        namespace = mode or "default"
        if self._svc is not None:
            return CacheServiceHandle(self._svc, namespace)
        return CacheHandle(self._fallback, namespace)

    async def release(self, resource: Any, success: bool = True):
        """Nothing to release for cache."""
        pass

    async def finalize(self):
        """Shutdown underlying cache service."""
        if self._svc is not None:
            try:
                await self._svc.shutdown()
            except Exception:
                pass


class CacheServiceHandle:
    """Handle wrapping real CacheService for a given namespace."""

    __slots__ = ("_svc", "_ns")

    def __init__(self, svc: Any, namespace: str):
        self._svc = svc
        self._ns = namespace

    async def get(self, key: str) -> Optional[Any]:
        return await self._svc.get(key, namespace=self._ns)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self._svc.set(key, value, ttl=ttl, namespace=self._ns)

    async def delete(self, key: str):
        await self._svc.delete(key, namespace=self._ns)


class CacheHandle:
    """Handle for cache operations in a namespace."""
    
    def __init__(self, cache: dict, namespace: str):
        self._cache = cache
        self._namespace = namespace
    
    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(self._key(key))
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        self._cache[self._key(key)] = value
    
    async def delete(self, key: str):
        """Delete value from cache."""
        self._cache.pop(self._key(key), None)


class EffectRegistry:
    """
    Registry for effect providers.
    Validates effect availability and instantiates providers.
    
    Integrates with DI system - can be registered as an app-scoped
    singleton and provides lifecycle hooks for startup/shutdown.
    """
    
    def __init__(self):
        self.providers: dict[str, EffectProvider] = {}
        self._initialized = False
    
    def register(self, effect_name: str, provider: EffectProvider):
        """Register an effect provider."""
        self.providers[effect_name] = provider
    
    async def initialize_all(self):
        """Initialize all registered providers (lifecycle startup hook)."""
        if self._initialized:
            return
        for name, provider in self.providers.items():
            await provider.initialize()
        self._initialized = True
    
    async def finalize_all(self):
        """Finalize all providers (lifecycle shutdown hook)."""
        for provider in self.providers.values():
            await provider.finalize()
        self._initialized = False
    
    # DI lifecycle aliases
    async def startup(self):
        """DI lifecycle startup hook."""
        await self.initialize_all()
    
    async def shutdown(self):
        """DI lifecycle shutdown hook."""
        await self.finalize_all()
    
    def has_effect(self, effect_name: str) -> bool:
        """Check if effect is available."""
        return effect_name in self.providers
    
    def get_provider(self, effect_name: str) -> EffectProvider:
        """Get provider for effect."""
        if effect_name not in self.providers:
            raise KeyError(f"Effect '{effect_name}' not registered")
        return self.providers[effect_name]
    
    def register_with_container(self, container: "Any"):
        """
        Register this EffectRegistry and all effect providers with a DI container.
        
        Args:
            container: DI Container instance
        """
        from aquilia.di.providers import ValueProvider
        
        # Register the registry itself
        container.register(ValueProvider(
            value=self,
            token=EffectRegistry,
            scope="app",
        ))
        
        # Register individual providers by effect name
        for effect_name, provider in self.providers.items():
            try:
                container.register(ValueProvider(
                    value=provider,
                    token=f"effect:{effect_name}",
                    scope="app",
                ))
            except ValueError:
                pass  # Already registered
