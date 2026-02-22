"""
Aquilia Dependency Injection System

Production-grade, async-first DI with manifest awareness, multi-tenant safety,
and comprehensive observability.

Key Features:
- Explicit scopes: singleton, app, request, transient, pooled, ephemeral
- Manifest-aware registry with cross-app dependency enforcement
- Async lifecycle hooks with deterministic disposal
- Low-overhead hot path: <3µs cached lookups
- Cycle detection with safe lazy resolution
- OpenTelemetry tracing and metrics
- LSP integration via di_manifest.json
"""

__version__ = "1.0.0"

from .core import (
    Provider,
    ProviderMeta,
    Container,
    Registry,
    ResolveCtx,
)

from .providers import (
    ClassProvider,
    FactoryProvider,
    ValueProvider,
    PoolProvider,
    AliasProvider,
    LazyProxyProvider,
    ScopedProvider,
    SerializerProvider,
)

from .scopes import (
    Scope,
    ServiceScope,
    ScopeValidator,
)

from .decorators import (
    service,
    factory,
    inject,
    Inject,
    provides,
    auto_inject,
)

from .lifecycle import (
    Lifecycle,
    LifecycleHook,
    DisposalStrategy,
    LifecycleContext,
)

from .graph import (
    DependencyGraph,
)

from .errors import (
    DIError,
    ProviderNotFoundError,
    DependencyCycleError,
    ScopeViolationError,
    AmbiguousProviderError,
)

from .testing import (
    TestRegistry,
    MockProvider,
)

from .dep import (
    Dep,
    Header,
    Query,
    Body,
)

from .request_dag import (
    RequestDAG,
)

# Legacy compatibility
from .compat import RequestCtx

__all__ = [
    # Core types
    "Provider",
    "ProviderMeta",
    "Container",
    "Registry",
    "ResolveCtx",
    
    # Providers
    "ClassProvider",
    "FactoryProvider",
    "ValueProvider",
    "PoolProvider",
    "AliasProvider",
    "LazyProxyProvider",
    "ScopedProvider",
    "SerializerProvider",
    
    # Scopes
    "Scope",
    "ServiceScope",
    "ScopeValidator",
    
    # Decorators
    "service",
    "factory",
    "inject",
    "Inject",
    "provides",
    "auto_inject",
    
    # Lifecycle
    "Lifecycle",
    "LifecycleHook",
    "DisposalStrategy",
    "LifecycleContext",
    
    # Graph
    "DependencyGraph",
    
    # Errors
    "DIError",
    "ProviderNotFoundError",
    "DependencyCycleError",
    "ScopeViolationError",
    "AmbiguousProviderError",
    
    # Testing
    "TestRegistry",
    "MockProvider",
    
    # Dep (annotation-driven DI)
    "Dep",
    "Header",
    "Query",
    "Body",
    "RequestDAG",
    
    # Legacy
    "RequestCtx",
]
