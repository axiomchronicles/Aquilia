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

# Use inspect.iscoroutinefunction (asyncio version deprecated in 3.16)
_is_coroutine = inspect.iscoroutinefunction

# Module-level cache: type → "module.qualname" string
_type_key_cache: Dict[type, str] = {}

# Scopes that should cache instances (frozen for O(1) lookup)
_CACHEABLE_SCOPES = frozenset(("singleton", "app", "request"))


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


class ResolveCtx:
    """
    Context for resolution operations.
    
    Tracks resolution stack for cycle detection and diagnostics.
    Uses __slots__ for minimal allocation overhead.
    """
    __slots__ = ("container", "stack", "cache")

    def __init__(self, container: "Container"):
        self.container = container
        self.stack: List[str] = []
        self.cache: Dict[str, Any] = {}
    
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
        "_diagnostics",
        "_lifecycle",
    )
    
    def __init__(
        self,
        scope: str = "app",
        parent: Optional["Container"] = None,
        diagnostics: Optional[Any] = None,
    ):
        from .diagnostics import DIDiagnostics
        from .lifecycle import Lifecycle

        self._providers: Dict[str, Provider] = {}  # {cache_key: provider}
        self._cache: Dict[str, Any] = {}  # {cache_key: instance}
        self._scope = scope
        self._parent = parent
        self._finalizers: List[Callable[[], Coroutine]] = []  # LIFO cleanup
        self._resolve_plans: Dict[str, List[str]] = {}  # Precomputed dependency lists
        self._diagnostics = diagnostics or DIDiagnostics()
        self._lifecycle = Lifecycle()
    
    def register(self, provider: Provider, tag: Optional[str] = None):
        """
        Register a provider.
        
        Args:
            provider: Provider instance
            tag: Optional tag for disambiguation
        """
        meta = provider.meta
        token = meta.token
        key = self._make_cache_key(token, tag)
        
        # Check for duplicates
        if key in self._providers:
            existing = self._providers[key]
            # Idempotency: if same provider, ignore. If different, error.
            if existing == provider:
                return
            raise ValueError(
                f"Provider for {token} (tag={tag}) already registered: {existing.meta.name}"
            )
        
        self._providers[key] = provider

        # Emit diagnostic event
        from .diagnostics import DIEventType
        self._diagnostics.emit(
            DIEventType.REGISTRATION,
            token=token,
            tag=tag,
            provider_name=meta.name
        )

    def bind(self, interface: Type, implementation: Type, scope: str = "app", tag: Optional[str] = None):
        """
        Bind an interface to an implementation class.
        
        Example:
            container.bind(UserRepository, SqlUserRepository)
        
        Args:
            interface: Abstract base class or protocol
            implementation: Concrete class
            scope: Lifecycle scope
            tag: Optional tag
        """
        from .providers import ClassProvider
        provider = ClassProvider(implementation, scope=scope)
        
        # Register under the INTERFACE token
        meta = provider.meta
        # Hack: mutate the token to match the interface, but keep the implementation logic
        # A cleaner way would be to wrap or use AliasProvider, but ClassProvider is flexible.
        token = self._token_to_key(interface)
        
        # We manually register it under the interface key
        key = self._make_cache_key(token, tag)
        self._providers[key] = provider

        # Emit diagnostic event
        from .diagnostics import DIEventType
        self._diagnostics.emit(
            DIEventType.REGISTRATION,
            token=token,
            tag=tag,
            provider_name=provider.meta.name,
            metadata={"binding": "interface"}
        )
        
    async def register_instance(
        self,
        token: Type[T] | str,
        instance: T,
        scope: str = "request",
        tag: Optional[str] = None,
    ):
        """
        Register a pre-instantiated object as a provider.
        
        This is useful for registering request-scoped instances like Session
        that are created outside the DI system.
        
        Args:
            token: Type or string key
            instance: Pre-instantiated object
            scope: Scope for the instance (default: "request")
            tag: Optional tag for disambiguation
            
        Example:
            >>> session = await engine.resolve(request)
            >>> await container.register_instance(Session, session, scope="request")
        """
        from .providers import ValueProvider
        
        # Create a ValueProvider for the instance
        provider = ValueProvider(
            token=token,
            value=instance,
            scope=scope,
            name=f"{token.__name__ if hasattr(token, '__name__') else token}_instance",
        )
        
        # Register the provider
        self.register(provider, tag=tag)
    
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

        Performance (v3):
        - Inlined token_to_key for common cases (str pass-through, type cache).
        - Single dict.get on _cache for the fast path.
        - No method call overhead for the >99% cached-hit case.
        - _should_cache uses frozenset constant.
        """
        # ── Inline token_to_key for speed ──
        if isinstance(token, str):
            token_key = token
        elif isinstance(token, type):
            token_key = _type_key_cache.get(token)
            if token_key is None:
                token_key = f"{token.__module__}.{token.__qualname__}"
                _type_key_cache[token] = token_key
        else:
            token_key = str(token)
        
        # ── Inline _make_cache_key ──
        cache_key = f"{token_key}#{tag}" if tag else token_key
        
        # Fast path: check cache (no diagnostics overhead)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Lookup provider
        provider = self._lookup_provider(token_key, tag)
        
        if provider is None:
            if optional:
                return None
            self._raise_not_found(token_key, tag)
        
        # Scope Delegation: singleton/app → parent
        if self._parent and provider.meta.scope in ("singleton", "app"):
            return await self._parent.resolve_async(token, tag=tag, optional=optional)
        
        # Create resolution context
        ctx = ResolveCtx(container=self)
        ctx.push(cache_key)
        
        try:
            instance = await provider.instantiate(ctx)
            
            # Cache if appropriate for scope
            if provider.meta.scope in _CACHEABLE_SCOPES:
                self._cache[cache_key] = instance
                await self._check_lifecycle_hooks(instance, provider.meta.name)
                if hasattr(instance, "__aexit__") or hasattr(instance, "shutdown"):
                    self._register_finalizer(instance)
            
            return instance
        finally:
            ctx.pop()

    async def _check_lifecycle_hooks(self, instance: Any, name: str) -> None:
        """Check and register lifecycle hooks for an instance."""
        if hasattr(instance, "on_startup"):
            hook = instance.on_startup
            self._lifecycle.on_startup(
                hook if _is_coroutine(hook) else lambda: asyncio.to_thread(hook),
                name=f"{name}.on_startup"
            )
        
        if hasattr(instance, "on_shutdown"):
            hook = instance.on_shutdown
            self._lifecycle.on_shutdown(
                hook if _is_coroutine(hook) else lambda: asyncio.to_thread(hook),
                name=f"{name}.on_shutdown"
            )

    async def startup(self) -> None:
        """
        Run startup hooks for all registered providers.
        """
        from .diagnostics import DIEventType
        self._diagnostics.emit(DIEventType.LIFECYCLE_STARTUP, metadata={"scope": self._scope})
        await self._lifecycle.run_startup_hooks()

    
    def is_registered(self, token: Type[T] | str, tag: Optional[str] = None) -> bool:
        """Check if a provider is registered for the token."""
        token_key = self._token_to_key(token)
        return self._lookup_provider(token_key, tag) is not None

    def create_request_scope(self) -> "Container":
        """
        Create a request-scoped child container (very cheap).

        Performance (v2):
        - No import of DIDiagnostics/Lifecycle at call time (cached).
        - Lifecycle is a lightweight NullLifecycle for request scope.
        - Shared diagnostics reference from parent.
        """
        child = Container.__new__(Container)
        child._providers = self._providers  # Share by reference
        child._cache = {}  # Fresh cache per request
        child._scope = "request"
        child._parent = self
        child._finalizers = []
        child._resolve_plans = self._resolve_plans  # Read-only, share by ref
        child._diagnostics = self._diagnostics  # Share parent diagnostics
        child._lifecycle = _NullLifecycle  # Singleton no-op lifecycle
        return child
    
    async def shutdown(self) -> None:
        """
        Shutdown container - run lifecycle hooks and finalizers in LIFO order.

        Performance (v2): Short-circuit for empty request-scoped containers.
        """
        # Fast path: request scope with nothing to clean up
        if self._scope == "request" and not self._finalizers and not self._cache:
            return

        from .diagnostics import DIEventType
        self._diagnostics.emit(DIEventType.LIFECYCLE_SHUTDOWN, metadata={"scope": self._scope})

        # Run lifecycle shutdown hooks
        await self._lifecycle.run_shutdown_hooks()
        await self._lifecycle.run_finalizers()

        # Compatibility with existing finalizers
        for finalizer in reversed(self._finalizers):
            try:
                await finalizer()
            except Exception as e:
                print(f"Error during finalizer: {e}")

        self._finalizers.clear()
        self._cache.clear()
        self._lifecycle.clear()
    
    def _token_to_key(self, token: Type | str) -> str:
        """Convert type or string to cache key.

        Performance: type→key results are cached in a module-level dict
        to avoid repeated f-string formatting (~0.12µs → ~0.04µs).
        """
        if isinstance(token, str):
            return token
        
        if isinstance(token, type):
            key = _type_key_cache.get(token)
            if key is None:
                key = f"{token.__module__}.{token.__qualname__}"
                _type_key_cache[token] = key
            return key
        
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
        key = self._make_cache_key(token, tag)
        if key in self._providers:
            return self._providers[key]
        
        # Check parent
        if self._parent:
            return self._parent._lookup_provider(token, tag)
        
        return None
    
    def _should_cache(self, scope: str) -> bool:
        """Check if scope should cache instances."""
        return scope in _CACHEABLE_SCOPES
    
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
        for key, provider in self._providers.items():
            if token in key:
                 candidates.append(key)
        
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
        if not hasattr(manifest, 'services') or not manifest.services:
            return
        
        from .providers import ClassProvider
        import importlib
        
        for service_entry in manifest.services:
            # Handle both string format and dict format
            if isinstance(service_entry, str):
                # Format: "module.path:ClassName"
                service_str = service_entry
                scope = "singleton"  # Default scope
            elif isinstance(service_entry, dict):
                # Format: {"class": "module.path:ClassName", "scope": "singleton"}
                service_str = service_entry.get("class")
                scope = service_entry.get("scope", "singleton")
            else:
                continue
            
            if not service_str or ':' not in service_str:
                continue
            
            # Parse module path and class name
            module_path, class_name = service_str.rsplit(':', 1)
            
            try:
                # Import module
                module = importlib.import_module(module_path)
                
                # Get class
                service_class = getattr(module, class_name)
                
                # Create provider
                provider = ClassProvider(
                    cls=service_class,
                    scope=scope,
                )
                
                # Add to registry
                self._providers.append(provider)
                
            except (ImportError, AttributeError) as e:
                # Log error but continue
                print(f"Warning: Could not load service {service_str}: {e}")
    
    def _build_dependency_graph(self) -> None:
        """
        Build dependency graph from registered providers (phase 2).
        
        Extracts dependencies from ClassProvider constructors and builds
        the dependency graph for analysis.
        
        Raises:
            MissingDependencyError: If a required dependency is not registered
        """
        from .graph import DependencyGraph
        from .errors import MissingDependencyError
        import inspect
        
        # Create dependency graph
        self._dep_graph = DependencyGraph()
        
        # Add all providers to graph
        for provider in self._providers:
            dependencies = []
            
            # Extract dependencies from ClassProvider
            if hasattr(provider, 'cls'):
                try:
                    # Get constructor signature
                    sig = inspect.signature(provider.cls.__init__)
                    
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        
                        # Get type annotation
                        if param.annotation != inspect.Parameter.empty:
                            # Handle Optional types
                            param_type = param.annotation
                            
                            # Skip if Optional (not required)
                            origin = getattr(param_type, '__origin__', None)
                            if origin is not None:
                                # Handle Union types (Optional is Union[T, None])
                                import typing
                                if origin is typing.Union:
                                    args = getattr(param_type, '__args__', ())
                                    # If None in args, it's optional
                                    if type(None) in args:
                                        continue
                                    # Otherwise use first non-None type
                                    param_type = next((a for a in args if a is not type(None)), param_type)
                            
                            # Get token from type
                            if hasattr(param_type, '__module__') and hasattr(param_type, '__name__'):
                                dep_token = f"{param_type.__module__}.{param_type.__name__}"
                                dependencies.append(dep_token)
                        
                        # If no annotation but has default, skip (optional)
                        elif param.default != inspect.Parameter.empty:
                            continue
                
                except Exception as e:
                    # Log warning but continue
                    print(f"Warning: Could not extract dependencies from {provider.meta.token}: {e}")
            
            # Add to graph
            self._dep_graph.add_provider(provider, dependencies)
            self._graph[provider.meta.token] = dependencies
        
        # Validate all dependencies exist
        missing = []
        for token, deps in self._graph.items():
            for dep in deps:
                if not any(p.meta.token == dep for p in self._providers):
                    missing.append((token, dep))
        
        if missing:
            # Report first missing dependency
            service_token, dep_token = missing[0]
            provider = next((p for p in self._providers if p.meta.token == service_token), None)
            location = None
            if provider and provider.meta.module and provider.meta.line:
                location = (provider.meta.module, provider.meta.line)
            
            raise MissingDependencyError(
                service_token=service_token,
                dependency_token=dep_token,
                service_location=location,
            )
    
    def _detect_cycles(self) -> None:
        """
        Detect cycles using Tarjan's algorithm (phase 3).
        
        Uses the DependencyGraph's Tarjan implementation to find
        strongly connected components (cycles).
        
        Raises:
            CircularDependencyError: If circular dependencies detected
        """
        from .errors import CircularDependencyError
        
        if not hasattr(self, '_dep_graph'):
            # Graph not built yet
            return
        
        # Detect cycles using Tarjan's algorithm
        cycles = self._dep_graph.detect_cycles()
        
        if cycles:
            # Collect location information for error reporting
            locations = {}
            for cycle in cycles:
                for token in cycle:
                    provider = next((p for p in self._providers if p.meta.token == token), None)
                    if provider and provider.meta.module and provider.meta.line:
                        locations[token] = (provider.meta.module, provider.meta.line)
            
            raise CircularDependencyError(cycles=cycles, locations=locations)
    
    def _validate_cross_app_deps(self, manifests: List[Any]) -> None:
        """
        Validate cross-app dependencies (phase 4).
        
        Ensures that:
        1. Cross-app dependencies are declared in manifest depends_on
        2. No circular app dependencies
        3. Dependency load order is correct
        
        Args:
            manifests: List of AppManifest instances
            
        Raises:
            CrossAppDependencyError: If cross-app dependency rules violated
        """
        from .errors import CrossAppDependencyError
        
        # Build app -> services mapping
        app_services: Dict[str, List[str]] = {}
        for manifest in manifests:
            app_name = getattr(manifest, 'name', 'unknown')
            services = []
            
            if hasattr(manifest, 'services'):
                for service_entry in manifest.services:
                    if isinstance(service_entry, str):
                        service_str = service_entry
                    elif isinstance(service_entry, dict):
                        service_str = service_entry.get('class', '')
                    else:
                        continue
                    
                    if ':' in service_str:
                        # Convert to token format
                        module_path, class_name = service_str.rsplit(':', 1)
                        token = f"{module_path}.{class_name}"
                        services.append(token)
            
            app_services[app_name] = services
        
        # Build app dependencies from manifest
        app_depends_on: Dict[str, List[str]] = {}
        for manifest in manifests:
            app_name = getattr(manifest, 'name', 'unknown')
            depends_on = getattr(manifest, 'depends_on', [])
            app_depends_on[app_name] = depends_on
        
        # Check each service's dependencies
        for manifest in manifests:
            consumer_app = getattr(manifest, 'name', 'unknown')
            consumer_services = app_services.get(consumer_app, [])
            
            for service_token in consumer_services:
                # Get dependencies of this service
                deps = self._graph.get(service_token, [])
                
                for dep_token in deps:
                    # Find which app provides this dependency
                    provider_app = None
                    for app, services in app_services.items():
                        if dep_token in services:
                            provider_app = app
                            break
                    
                    # If dependency is from another app, check if declared
                    if provider_app and provider_app != consumer_app:
                        if provider_app not in app_depends_on.get(consumer_app, []):
                            raise CrossAppDependencyError(
                                consumer_app=consumer_app,
                                provider_app=provider_app,
                                provider_token=dep_token,
                            )


# ── Lightweight null lifecycle for request-scoped containers ──

class _NullLifecycleType:
    """No-op lifecycle singleton — avoids allocating a real Lifecycle
    per request container."""
    __slots__ = ()

    async def run_startup_hooks(self): pass
    async def run_shutdown_hooks(self): pass
    async def run_finalizers(self): pass
    def on_startup(self, *a, **kw): pass
    def on_shutdown(self, *a, **kw): pass
    def clear(self): pass

_NullLifecycle = _NullLifecycleType()
