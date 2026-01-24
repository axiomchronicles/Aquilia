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
    """Example cache provider."""
    
    def __init__(self, backend: str = "memory"):
        self.backend = backend
        self.cache = {}
    
    async def initialize(self):
        """Initialize cache backend."""
        pass
    
    async def acquire(self, mode: Optional[str] = None):
        """Get cache instance for namespace."""
        namespace = mode or "default"
        return CacheHandle(self.cache, namespace)
    
    async def release(self, resource: Any, success: bool = True):
        """Nothing to release for cache."""
        pass


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
    """
    
    def __init__(self):
        self.providers: dict[str, EffectProvider] = {}
    
    def register(self, effect_name: str, provider: EffectProvider):
        """Register an effect provider."""
        self.providers[effect_name] = provider
    
    async def initialize_all(self):
        """Initialize all registered providers."""
        for provider in self.providers.values():
            await provider.initialize()
    
    async def finalize_all(self):
        """Finalize all providers."""
        for provider in self.providers.values():
            await provider.finalize()
    
    def has_effect(self, effect_name: str) -> bool:
        """Check if effect is available."""
        return effect_name in self.providers
    
    def get_provider(self, effect_name: str) -> EffectProvider:
        """Get provider for effect."""
        if effect_name not in self.providers:
            raise KeyError(f"Effect '{effect_name}' not registered")
        return self.providers[effect_name]
