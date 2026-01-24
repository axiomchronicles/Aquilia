"""
Core DI types and protocols.

Defines the fundamental contracts for the DI system.
"""

from typing import (
    Any,
    Callable,
    Coroutine,
    Type,
    Optional,
    Protocol,
    Dict,
    List,
    TypeVar,
    Generic,
    runtime_checkable,
)
from dataclasses import dataclass, field
from enum import Enum
import inspect
import asyncio
from contextvars import ContextVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderMeta:
    """
    Compact, serializable provider metadata.
    
    Stored in di_manifest.json for LSP integration.
    """
    name: str
    token: str  # Type name or string key
    scope: str  # "singleton", "app", "request", "transient", "pooled", "ephemeral"
    tags: tuple[str, ...] = field(default_factory=tuple)
    module: str = ""
    qualname: str = ""
    line: Optional[int] = None
    version: Optional[str] = None
    allow_lazy: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for manifest JSON."""
        return {
            "name": self.name,
            "token": self.token,
            "scope": self.scope,
            "tags": list(self.tags),
            "module": self.module,
            "qualname": self.qualname,
            "line": self.line,
            "version": self.version,
            "allow_lazy": self.allow_lazy,
        }


@dataclass
class ResolveCtx:
    """
    Context for resolution operations.
    
    Tracks resolution stack for cycle detection and diagnostics.
    """
    container: "Container"
    stack: List[str] = field(default_factory=list)
    cache: Dict[str, Any] = field(default_factory=dict)
    
    def push(self, token: str) -> None:
        """Push token onto resolution stack."""
        self.stack.append(token)
    
    def pop(self) -> None:
        """Pop token from resolution stack."""
        self.stack.pop()
    
    def in_cycle(self, token: str) -> bool:
        """Check if token is currently being resolved (cycle)."""
        return token in self.stack
    
    def get_trace(self) -> List[str]:
        """Get current resolution trace for error messages."""
        return self.stack.copy()


@runtime_checkable
class Provider(Protocol):
    """
    Provider protocol - how to instantiate a dependency.
    
    All providers must implement this interface.
    """
    
    @property
    def meta(self) -> ProviderMeta:
        """Provider metadata."""
        ...
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """
        Instantiate the provider.
        
        Args:
            ctx: Resolution context with container and stack
            
        Returns:
            The instantiated object
        """
        ...
    
    async def shutdown(self) -> None:
        """
        Shutdown hook for cleanup.
        
        Called in reverse order of instantiation.
        """
        ...


class Container:
    """
    DI Container - manages provider instances and scopes.
    
    Optimized for low-overhead hot path (<3µs cached lookups).
    """
    
    __slots__ = (
        "_providers",
        "_cache",
        "_scope",
        "_parent",
        "_finalizers",
        "_resolve_plans",
    )
    
    def __init__(
        self,
        scope: str = "app",
        parent: Optional["Container"] = None,
    ):
        self._providers: Dict[str, Dict[Optional[str], Provider]] = {}  # {token: {tag: provider}}
        self._cache: Dict[str, Any] = {}  # {cache_key: instance}
        self._scope = scope
        self._parent = parent
        self._finalizers: List[Callable[[], Coroutine]] = []  # LIFO cleanup
        self._resolve_plans: Dict[str, List[str]] = {}  # Precomputed dependency lists
    
    def register(self, provider: Provider, tag: Optional[str] = None) -> None:
        """
        Register a provider.
        
        Args:
            provider: Provider instance
            tag: Optional tag for disambiguation
        """
        token = provider.meta.token
        
        if token not in self._providers:
            self._providers[token] = {}
        
        if tag in self._providers[token]:
            raise ValueError(
                f"Provider for token={token} with tag={tag} already registered"
            )
        
        self._providers[token] = self._providers.get(token, {})
        self._providers[token][tag] = provider
    
    def resolve(
        self,
        token: Type[T] | str,
        *,
        tag: Optional[str] = None,
        optional: bool = False,
    ) -> T:
        """
        Resolve a dependency (hot path - optimized).
        
        Args:
            token: Type or string key
            tag: Optional tag for disambiguation
            optional: If True, return None if not found instead of raising
            
        Returns:
            The resolved instance
            
        Raises:
            ProviderNotFoundError: If provider not found and not optional
        """
        # Convert type to string key
        token_key = self._token_to_key(token)
        cache_key = self._make_cache_key(token_key, tag)
        
        # Fast path: check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Lookup provider
        provider = self._lookup_provider(token_key, tag)
        
        if provider is None:
            if optional:
                return None
            self._raise_not_found(token_key, tag)
        
        # Async instantiation requires event loop
        # For sync access, we need to handle this carefully
        try:
            loop = asyncio.get_running_loop()
            # We're in async context, but resolve() is sync
            # This is a design trade-off; in practice, handlers use async
            raise RuntimeError(
                "resolve() called from async context; use await resolve_async() instead"
            )
        except RuntimeError:
            # No running loop - create one (for testing/sync usage)
            instance = asyncio.run(self.resolve_async(token, tag=tag, optional=optional))
            return instance
    
    async def resolve_async(
        self,
        token: Type[T] | str,
        *,
        tag: Optional[str] = None,
        optional: bool = False,
    ) -> T:
        """
        Async resolve (primary resolution path).
        
        Args:
            token: Type or string key
            tag: Optional tag for disambiguation
            optional: If True, return None if not found
            
        Returns:
            The resolved instance
        """
        token_key = self._token_to_key(token)
        cache_key = self._make_cache_key(token_key, tag)
        
        # Fast path: check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Lookup provider
        provider = self._lookup_provider(token_key, tag)
        
        if provider is None:
            if optional:
                return None
            self._raise_not_found(token_key, tag)
        
        # Create resolution context
        ctx = ResolveCtx(container=self)
        ctx.push(cache_key)
        
        try:
            # Instantiate
            instance = await provider.instantiate(ctx)
            
            # Cache if appropriate for scope
            if self._should_cache(provider.meta.scope):
                self._cache[cache_key] = instance
                
                # Register finalizer for cleanup
                if hasattr(instance, "__aexit__") or hasattr(instance, "shutdown"):
                    self._register_finalizer(instance)
            
            return instance
        finally:
            ctx.pop()
    
    def create_request_scope(self) -> "Container":
        """
        Create a request-scoped child container (very cheap).
        
        Returns:
            New container with request scope
        """
        child = Container(scope="request", parent=self)
        # Share provider registry but not cache
        child._providers = self._providers
        child._resolve_plans = self._resolve_plans
        return child
    
    async def shutdown(self) -> None:
        """
        Shutdown container - run finalizers in LIFO order.
        """
        # Run finalizers in reverse order
        for finalizer in reversed(self._finalizers):
            try:
                await finalizer()
            except Exception as e:
                # Log but don't fail shutdown
                print(f"Error during finalizer: {e}")
        
        self._finalizers.clear()
        self._cache.clear()
    
    def _token_to_key(self, token: Type | str) -> str:
        """Convert type or string to cache key."""
        if isinstance(token, str):
            return token
        
        if isinstance(token, type):
            return f"{token.__module__}.{token.__qualname__}"
        
        # Handle typing generics
        return str(token)
    
    def _make_cache_key(self, token: str, tag: Optional[str]) -> str:
        """Create cache key from token and tag."""
        if tag:
            return f"{token}#{tag}"
        return token
    
    def _lookup_provider(
        self,
        token: str,
        tag: Optional[str],
    ) -> Optional[Provider]:
        """
        Lookup provider in current container or parent.
        
        Returns:
            Provider or None if not found
        """
        # Check current container
        if token in self._providers:
            providers = self._providers[token]
            if tag in providers:
                return providers[tag]
            if None in providers and tag is None:
                return providers[None]
        
        # Check parent
        if self._parent:
            return self._parent._lookup_provider(token, tag)
        
        return None
    
    def _should_cache(self, scope: str) -> bool:
        """Check if scope should cache instances."""
        return scope in ("singleton", "app", "request")
    
    def _register_finalizer(self, instance: Any) -> None:
        """Register finalizer for cleanup."""
        if hasattr(instance, "__aexit__"):
            self._finalizers.append(
                lambda: instance.__aexit__(None, None, None)
            )
        elif hasattr(instance, "shutdown"):
            self._finalizers.append(instance.shutdown)
    
    def _raise_not_found(self, token: str, tag: Optional[str]) -> None:
        """Raise ProviderNotFoundError with helpful diagnostics."""
        from .errors import ProviderNotFoundError
        
        # Find similar providers
        candidates = []
        for t, providers in self._providers.items():
            for p_tag, provider in providers.items():
                if token in t or t in token:
                    tag_str = f" (tag={p_tag})" if p_tag else ""
                    candidates.append(f"{t}{tag_str}")
        
        raise ProviderNotFoundError(
            token=token,
            tag=tag,
            candidates=candidates,
        )


class Registry:
    """
    Registry - builds and validates provider graph from manifests.
    
    Performs static analysis, cycle detection, and generates manifest JSON.
    """
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self._providers: List[Provider] = []
        self._graph: Dict[str, List[str]] = {}  # {provider: [dependencies]}
    
    @classmethod
    def from_manifests(
        cls,
        manifests: List[Any],
        config: Optional[Any] = None,
        *,
        enforce_cross_app: bool = True,
    ) -> "Registry":
        """
        Build registry from manifests.
        
        Args:
            manifests: List of AppManifest instances
            config: Optional config object
            enforce_cross_app: If True, enforce depends_on rules
            
        Returns:
            Validated registry
        """
        registry = cls(config=config)
        
        # Phase 1: Load provider metadata (no imports yet)
        for manifest in manifests:
            registry._load_manifest_services(manifest)
        
        # Phase 2: Build dependency graph
        registry._build_dependency_graph()
        
        # Phase 3: Detect cycles
        registry._detect_cycles()
        
        # Phase 4: Validate cross-app dependencies
        if enforce_cross_app:
            registry._validate_cross_app_deps(manifests)
        
        return registry
    
    def build_container(self) -> Container:
        """
        Build container from registry.
        
        Returns:
            Configured container
        """
        container = Container(scope="app")
        
        for provider in self._providers:
            # Extract tag from metadata if present
            tag = provider.meta.tags[0] if provider.meta.tags else None
            container.register(provider, tag=tag)
        
        return container
    
    def _load_manifest_services(self, manifest: Any) -> None:
        """Load services from manifest (phase 1)."""
        # Implementation in next phase
        pass
    
    def _build_dependency_graph(self) -> None:
        """Build dependency graph (phase 2)."""
        # Implementation in next phase
        pass
    
    def _detect_cycles(self) -> None:
        """Detect cycles using Tarjan's algorithm (phase 3)."""
        # Implementation in next phase
        pass
    
    def _validate_cross_app_deps(self, manifests: List[Any]) -> None:
        """Validate cross-app dependencies (phase 4)."""
        # Implementation in next phase
        pass
