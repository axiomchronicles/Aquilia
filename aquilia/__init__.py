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

__version__ = "0.2.0"

# ============================================================================
# Core Framework
# ============================================================================

from .manifest import AppManifest, DatabaseConfig
from .config import Config, ConfigLoader
from .config_builders import Workspace, Module, Integration
from .request import Request
from .response import Response
from .server import AquiliaServer

# Request data structures
from ._datastructures import (
    MultiDict,
    Headers,
    URL,
    ParsedContentType,
    Range,
)

# Upload handling
from ._uploads import (
    UploadFile,
    FormData,
    UploadStore,
    LocalUploadStore,
)

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

# Note: RequestCtx is imported from .controller above; do not re-import
# from .engine to avoid shadowing.

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
    SessionPrincipal,
    MemoryStore as SessionMemoryStore,
    CookieTransport,
    SessionFault,
    SessionExpiredFault,
)

# Session decorators and state (NEW - Unique Aquilia syntax)
from .sessions.decorators import (
    session,
    authenticated,
    stateful,
    SessionRequiredFault,
    AuthenticationRequiredFault,
)

from .sessions.state import (
    SessionState,
    Field as SessionField,
    CartState,
    UserPreferencesState,
)

# Enhanced session features (NEW - Advanced patterns)
from .sessions.enhanced import (
    SessionContext,
    SessionGuard,
    requires,
    AdminGuard,
    VerifiedEmailGuard,
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
    RecoveryStrategy,
    # Model faults
    ModelFault,
    AMDLParseFault,
    ModelNotFoundFault,
    ModelRegistrationFault,
    MigrationFault,
    MigrationConflictFault,
    QueryFault,
    DatabaseConnectionFault,
    SchemaFault,
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

# Extended Middleware (Security, Rate Limiting, Static Files)
from .middleware_ext.security import (
    CORSMiddleware,
    CSPMiddleware,
    CSPPolicy,
    HSTSMiddleware,
    HTTPSRedirectMiddleware,
    ProxyFixMiddleware,
    SecurityHeadersMiddleware,
)
from .middleware_ext.rate_limit import (
    RateLimitMiddleware,
    RateLimitRule,
)
from .middleware_ext.static import StaticMiddleware

# ============================================================================
# Debug Pages
# ============================================================================

from .debug import (
    DebugPageRenderer,
    render_debug_exception_page,
    render_http_error_page,
    render_welcome_page,
)

# ============================================================================
# Effects & Patterns
# ============================================================================

from .effects import Effect, EffectProvider, EffectRegistry

# ============================================================================
# Sockets (WebSockets)
# ============================================================================

from .sockets import (
    SocketController,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AquilaSockets,
    SocketRouter,
    SocketGuard,
)

# ============================================================================
# Templates
# ============================================================================

from .templates import (
    TemplateEngine,
    TemplateMiddleware,
)

# ============================================================================
# Patterns
# ============================================================================

from .patterns import (
    PatternCompiler,
    PatternMatcher,
    CompiledPattern,
    TypeRegistry as PatternTypeRegistry,
)

# ============================================================================
# Discovery
# ============================================================================

from .discovery import PackageScanner

# ============================================================================
# Lifecycle
# ============================================================================

from .lifecycle import (
    LifecycleCoordinator,
    LifecyclePhase,
    LifecycleError,
)

# ============================================================================
# Model System (Pure Python ORM)
# ============================================================================

from .models import (
    # New pure-Python model system
    Model,
    ModelMeta,
    ModelRegistry,
    Q,
    # Fields
    Field,
    FieldValidationError,
    Index,
    UniqueConstraint,
    AutoField,
    BigAutoField,
    IntegerField,
    BigIntegerField,
    SmallIntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    FloatField,
    DecimalField,
    CharField,
    TextField,
    SlugField,
    EmailField,
    URLField,
    UUIDField,
    FilePathField,
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    BooleanField,
    BinaryField,
    JSONField,
    ForeignKey,
    OneToOneField,
    ManyToManyField,
    GenericIPAddressField,
    FileField,
    ImageField,
    ArrayField,
    HStoreField,
    GeneratedField,
    # Legacy AMDL (backward compat)
    ModelNode,
    SlotNode,
    LinkNode,
    IndexNode as LegacyIndexNode,
    HookNode,
    MetaNode,
    NoteNode,
    AMDLFile,
    FieldType,
    LinkKind,
    parse_amdl,
    parse_amdl_file,
    parse_amdl_directory,
    AMDLParseError,
    ModelProxy,
    # Migrations
    MigrationRunner,
    MigrationOps,
    generate_migration_file,
)

from .db import (
    AquiliaDatabase,
    configure_database,
    get_database,
    set_database,
    DatabaseError,
)

# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Core
    "AquiliaServer",
    "AppManifest",
    "DatabaseConfig",
    "Config",
    "ConfigLoader",
    "Request",
    "Response",
    
    # Request data structures
    "MultiDict",
    "Headers",
    "URL",
    "ParsedContentType",
    "Range",
    
    # Upload handling
    "UploadFile",
    "FormData",
    "UploadStore",
    "LocalUploadStore",
    
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
    "SessionPrincipal",
    "SessionMemoryStore",
    "CookieTransport",
    
    # Session decorators (NEW - Unique syntax)
    "session",
    "authenticated",
    "stateful",
    "SessionState",
    "SessionField",
    "CartState",
    "UserPreferencesState",
    
    # Enhanced session features (NEW - Advanced patterns)
    "SessionContext",
    "SessionGuard",
    "requires",
    "AdminGuard",
    "VerifiedEmailGuard",
    
    # Config builders (NEW - Python config)
    "Workspace",
    "Module",
    "Integration",
    
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
    
    # Faults
    "Fault",
    "FaultContext",
    "FaultEngine",
    "FaultHandler",
    "RecoveryStrategy",
    "ModelFault",
    "AMDLParseFault",
    "ModelNotFoundFault",
    "ModelRegistrationFault",
    "MigrationFault",
    "MigrationConflictFault",
    "QueryFault",
    "DatabaseConnectionFault",
    "SchemaFault",
    
    # Middleware
    "Middleware",
    "Handler",
    "MiddlewareStack",
    "CORSMiddleware",
    "CSPMiddleware",
    "CSPPolicy",
    "HSTSMiddleware",
    "HTTPSRedirectMiddleware",
    "ProxyFixMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "RateLimitRule",
    "StaticMiddleware",
    
    # Debug Pages
    "DebugPageRenderer",
    "render_debug_exception_page",
    "render_http_error_page",
    "render_welcome_page",
    
    # Effects
    "Effect",
    "EffectProvider",
    "EffectRegistry",
    
    # Sockets (WebSockets)
    "SocketController",
    "Socket",
    "OnConnect",
    "OnDisconnect",
    "Event",
    "AquilaSockets",
    "SocketRouter",
    "SocketGuard",
    
    # Templates
    "TemplateEngine",
    "TemplateMiddleware",
    
    # Patterns
    "PatternCompiler",
    "PatternMatcher",
    "CompiledPattern",
    "PatternTypeRegistry",
    
    # Discovery
    "PackageScanner",
    
    # Lifecycle
    "LifecycleCoordinator",
    
    # Model System (Pure Python ORM)
    "Model",
    "ModelMeta",
    "ModelRegistry",
    "Q",
    "Field",
    "FieldValidationError",
    "Index",
    "UniqueConstraint",
    "AutoField",
    "BigAutoField",
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "FloatField",
    "DecimalField",
    "CharField",
    "TextField",
    "SlugField",
    "EmailField",
    "URLField",
    "UUIDField",
    "FilePathField",
    "DateField",
    "TimeField",
    "DateTimeField",
    "DurationField",
    "BooleanField",
    "BinaryField",
    "JSONField",
    "ForeignKey",
    "OneToOneField",
    "ManyToManyField",
    "GenericIPAddressField",
    "FileField",
    "ImageField",
    "ArrayField",
    "HStoreField",
    "GeneratedField",
    # Legacy AMDL (backward compat)
    "ModelNode",
    "SlotNode",
    "LinkNode",
    "LegacyIndexNode",
    "HookNode",
    "MetaNode",
    "NoteNode",
    "AMDLFile",
    "FieldType",
    "LinkKind",
    "parse_amdl",
    "parse_amdl_file",
    "parse_amdl_directory",
    "AMDLParseError",
    "ModelProxy",
    # Migrations
    "MigrationRunner",
    "MigrationOps",
    "generate_migration_file",
    
    # Database
    "AquiliaDatabase",
    "configure_database",
    "get_database",
    "set_database",
    "DatabaseError",
]
