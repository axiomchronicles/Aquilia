"""
Aquilia - Production-ready async Python web framework

Complete integration of:
- Aquilary: Manifest-driven app registry with dependency resolution
- Flow: Typed flow-first routing with composable pipelines
- DI: Scoped dependency injection with lifecycle management
- Sessions: Cryptographic session management with policies
- Auth: OAuth2/OIDC, MFA, RBAC/ABAC authorization
- Faults: Structured error handling with fault domains
- Middleware: Composable middleware with effect awareness
- Patterns: Auto-fix, retry, circuit breaker patterns

Everything deeply integrated for seamless developer experience.
"""

__version__ = "2.0.0"

# ============================================================================
# Core Framework
# ============================================================================

from .manifest import AppManifest
from .config import Config, ConfigLoader
from .request import Request
from .response import Response
from .server import AquiliaServer

# ============================================================================
# Aquilary Registry (Replaces Legacy Registry)
# ============================================================================

from .aquilary import (
    Aquilary,
    AquilaryRegistry,
    RuntimeRegistry,
    AppContext,
    RegistryMode,
    RegistryFingerprint,
    RegistryError,
    DependencyCycleError,
    RouteConflictError,
    ManifestValidationError,
)

# ============================================================================
# Controller System (NEW - First-class controllers)
# ============================================================================

from .controller import (
    Controller,
    RequestCtx,
    GET, POST, PUT, PATCH, DELETE,
    HEAD, OPTIONS, WS,
    route,
    ControllerMetadata,
    RouteMetadata,
    ParameterMetadata,
    extract_controller_metadata,
    ControllerFactory,
    InstantiationMode,
)

# ============================================================================
# Engine
# ============================================================================

from .engine import RequestCtx

# ============================================================================
# DI System (Complete)
# ============================================================================

from .di import (
    Container,
    Registry as DIRegistry,
    Provider,
    ProviderMeta,
    ClassProvider,
    FactoryProvider,
    ValueProvider,
    service,
    factory,
    inject,
    Inject,
)

# ============================================================================
# Sessions System
# ============================================================================

from .sessions import (
    Session,
    SessionID,
    SessionPolicy,
    SessionEngine,
    MemoryStore as SessionMemoryStore,
    CookieTransport,
    SessionFault,
    SessionExpiredFault,
)

# ============================================================================
# Auth System (Complete Integration)
# ============================================================================

from .auth.core import (
    Identity,
    IdentityStatus,
    TokenClaims,
)

from .auth.manager import AuthManager
from .auth.tokens import TokenManager, KeyRing
from .auth.hashing import PasswordHasher
from .auth.authz import AuthzEngine, RBACEngine, ABACEngine

# Auth Integration
from .auth.integration.aquila_sessions import (
    AuthPrincipal,
    SessionAuthBridge,
    bind_identity,
    user_session_policy,
    api_session_policy,
)

from .auth.integration.di_providers import (
    register_auth_providers,
    create_auth_container,
    AuthConfig,
)

from .auth.integration.middleware import (
    AquilAuthMiddleware,
    create_auth_middleware_stack,
)

# Note: Flow guards removed - use controller-based auth with middleware
# from .auth.integration.flow_guards import (
#     require_auth,
#     require_scopes,
#     require_roles,
# )

# ============================================================================
# Faults System
# ============================================================================

from .faults import (
    Fault,
    FaultContext,
    FaultEngine,
    FaultHandler,
)

# ============================================================================
# Middleware System
# ============================================================================

from .middleware import (
    Middleware,
    Handler,
    MiddlewareStack,
    RequestIdMiddleware,
    LoggingMiddleware,
)

# ============================================================================
# Effects & Patterns
# ============================================================================

from .effects import Effect, EffectProvider, EffectRegistry

# ============================================================================
# Lifecycle
# ============================================================================

from .lifecycle import (
    LifecycleCoordinator,
    LifecyclePhase,
    LifecycleError,
)

# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Core
    "AquiliaServer",
    "AppManifest",
    "Config",
    "ConfigLoader",
    "Request",
    "Response",
    
    # Aquilary
    "Aquilary",
    "AquilaryRegistry",
    "RuntimeRegistry",
    "AppContext",
    "RegistryMode",
    
    # Controller (NEW - First-class)
    "Controller",
    "RequestCtx",
    "GET", "POST", "PUT", "PATCH", "DELETE",
    "HEAD", "OPTIONS", "WS",
    "route",
    "ControllerMetadata",
    "extract_controller_metadata",
    "ControllerFactory",
    "InstantiationMode",
    
    # Flow (Legacy)
    "flow",
    "Flow",
    "FlowBuilder",
    "FlowEngine",
    
    # Router
    "Router",
    "RouteMatch",
    
    # DI
    "Container",
    "DIRegistry",
    "Provider",
    "ProviderMeta",
    "ClassProvider",
    "FactoryProvider",
    "ValueProvider",
    "service",
    "factory",
    "inject",
    "Inject",
    
    # Sessions
    "Session",
    "SessionID",
    "SessionPolicy",
    "SessionEngine",
    "SessionMemoryStore",
    "CookieTransport",
    
    # Auth - Core
    "Identity",
    "AuthManager",
    "TokenManager",
    "KeyRing",
    "PasswordHasher",
    "AuthzEngine",
    
    # Auth - Integration
    "AuthPrincipal",
    "SessionAuthBridge",
    "bind_identity",
    "user_session_policy",
    "api_session_policy",
    "register_auth_providers",
    "create_auth_container",
    "AuthConfig",
    "AquilAuthMiddleware",
    "create_auth_middleware_stack",
    "require_auth",
    "require_scopes",
    "require_roles",
    
    # Faults
    "Fault",
    "FaultContext",
    "FaultEngine",
    
    # Middleware
    "Middleware",
    "Handler",
    "MiddlewareStack",
    
    # Effects
    "Effect",
    "EffectProvider",
    
    # Lifecycle
    "LifecycleCoordinator",
]
