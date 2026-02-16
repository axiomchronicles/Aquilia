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
    OpenAPIGenerator,
    OpenAPIConfig,
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
# Cache System
# ============================================================================

from .cache import (
    # Core types
    CacheBackend,
    CacheEntry,
    CacheStats,
    CacheConfig,
    EvictionPolicy,
    # Backends
    MemoryBackend,
    RedisBackend,
    CompositeBackend,
    NullBackend,
    # Service
    CacheService,
    # Decorators
    cached,
    cache_aside,
    invalidate,
    set_default_cache_service,
    get_default_cache_service,
    # Faults
    CacheFault,
    CacheMissFault,
    CacheConnectionFault,
    CacheSerializationFault,
    CacheCapacityFault,
    CacheBackendFault,
    CacheConfigFault,
    CacheStampedeFault,
    CacheHealthFault,
    # Middleware
    CacheMiddleware,
    # Key builders
    DefaultKeyBuilder,
    HashKeyBuilder,
    # Serializers
    JsonCacheSerializer,
    PickleCacheSerializer,
)

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
    # Serializer faults
    SerializerFault,
    SerializerValidationFault,
    SerializerFieldFault,
    SerializerConfigFault,
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
    CSRFError,
    CSRFMiddleware,
    HSTSMiddleware,
    HTTPSRedirectMiddleware,
    ProxyFixMiddleware,
    SecurityHeadersMiddleware,
    csrf_exempt,
    csrf_token_func,
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
# Mail (AquilaMail)
# ============================================================================

from .mail import (
    # Message types
    EmailMessage,
    EmailMultiAlternatives,
    TemplateMessage,
    # Convenience API
    send_mail,
    asend_mail,
    # Envelope
    MailEnvelope,
    EnvelopeStatus,
    Priority,
    # Config
    MailConfig,
    # Providers
    IMailProvider,
    ProviderResult,
    ProviderResultStatus,
    # Faults
    MailFault,
    MailSendFault,
    MailTemplateFault,
    MailConfigFault,
    MailSuppressedFault,
    MailRateLimitFault,
    MailValidationFault,
)

from .mail.service import MailService

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
# Serializers (DRF-inspired)
# ============================================================================

from .serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    # Fields
    SerializerField,
    BooleanField as SerializerBooleanField,
    CharField as SerializerCharField,
    EmailField as SerializerEmailField,
    IntegerField as SerializerIntegerField,
    FloatField as SerializerFloatField,
    DecimalField as SerializerDecimalField,
    DateField as SerializerDateField,
    DateTimeField as SerializerDateTimeField,
    ListField as SerializerListField,
    DictField as SerializerDictField,
    JSONField as SerializerJSONField,
    ReadOnlyField,
    HiddenField,
    SerializerMethodField,
    ChoiceField as SerializerChoiceField,
    FileField as SerializerFileField,
    ConstantField,
    # DI-aware Defaults
    CurrentUserDefault,
    CurrentRequestDefault,
    InjectDefault,
    # Relations
    RelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
    StringRelatedField,
    # Validators
    UniqueValidator,
    UniqueTogetherValidator,
    RangeValidator,
    CompoundValidator,
    ConditionalValidator,
    # Faults (also in .faults)
    SerializationFault,
    ValidationFault,
    FieldValidationFault,
)

# ============================================================================
# Lifecycle
# ============================================================================

from .lifecycle import (
    LifecycleCoordinator,
    LifecycleManager,
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
# Artifact System
# ============================================================================

from .artifacts import (
    Artifact,
    ArtifactEnvelope,
    ArtifactKind,
    ArtifactProvenance,
    ArtifactIntegrity,
    register_artifact_kind,
    ArtifactBuilder,
    ArtifactStore,
    MemoryArtifactStore,
    FilesystemArtifactStore,
    ArtifactReader,
    CodeArtifact,
    ModelArtifact,
    ConfigArtifact,
    TemplateArtifact,
    MigrationArtifact,
    RegistryArtifact,
    RouteArtifact,
    DIGraphArtifact,
    BundleArtifact,
)

# ============================================================================
# Trace System (.aquilia/ directory)
# ============================================================================

from .trace import (
    AquiliaTrace,
    TraceManifest,
    TraceRouteMap,
    TraceDIGraph,
    TraceSchemaLedger,
    TraceLifecycleJournal,
    TraceConfigSnapshot,
    TraceDiagnostics,
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
    
    # Cache
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "CacheConfig",
    "EvictionPolicy",
    "MemoryBackend",
    "RedisBackend",
    "CompositeBackend",
    "NullBackend",
    "CacheService",
    "cached",
    "cache_aside",
    "invalidate",
    "set_default_cache_service",
    "get_default_cache_service",
    "CacheFault",
    "CacheMissFault",
    "CacheConnectionFault",
    "CacheSerializationFault",
    "CacheCapacityFault",
    "CacheBackendFault",
    "CacheConfigFault",
    "CacheStampedeFault",
    "CacheHealthFault",
    "CacheMiddleware",
    "DefaultKeyBuilder",
    "HashKeyBuilder",
    "JsonCacheSerializer",
    "PickleCacheSerializer",
    
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
    
    # Serializer faults
    "SerializerFault",
    "SerializerValidationFault",
    "SerializerFieldFault",
    "SerializerConfigFault",
    
    # Middleware
    "Middleware",
    "Handler",
    "MiddlewareStack",
    "CORSMiddleware",
    "CSPMiddleware",
    "CSPPolicy",
    "CSRFError",
    "CSRFMiddleware",
    "HSTSMiddleware",
    "HTTPSRedirectMiddleware",
    "ProxyFixMiddleware",
    "SecurityHeadersMiddleware",
    "csrf_exempt",
    "csrf_token_func",
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
    
    # Mail (AquilaMail)
    "EmailMessage",
    "EmailMultiAlternatives",
    "TemplateMessage",
    "send_mail",
    "asend_mail",
    "MailEnvelope",
    "EnvelopeStatus",
    "Priority",
    "MailConfig",
    "MailService",
    "IMailProvider",
    "ProviderResult",
    "ProviderResultStatus",
    "MailFault",
    "MailSendFault",
    "MailTemplateFault",
    "MailConfigFault",
    "MailSuppressedFault",
    "MailRateLimitFault",
    "MailValidationFault",
    
    # Patterns
    "PatternCompiler",
    "PatternMatcher",
    "CompiledPattern",
    "PatternTypeRegistry",
    
    # Discovery
    "PackageScanner",
    
    # Serializers
    "Serializer",
    "ModelSerializer",
    "ListSerializer",
    "SerializerField",
    "SerializerBooleanField",
    "SerializerCharField",
    "SerializerEmailField",
    "SerializerIntegerField",
    "SerializerFloatField",
    "SerializerDecimalField",
    "SerializerDateField",
    "SerializerDateTimeField",
    "SerializerListField",
    "SerializerDictField",
    "SerializerJSONField",
    "ReadOnlyField",
    "HiddenField",
    "SerializerMethodField",
    "SerializerChoiceField",
    "SerializerFileField",
    "ConstantField",
    "CurrentUserDefault",
    "CurrentRequestDefault",
    "InjectDefault",
    "RelatedField",
    "PrimaryKeyRelatedField",
    "SlugRelatedField",
    "StringRelatedField",
    "UniqueValidator",
    "UniqueTogetherValidator",
    "RangeValidator",
    "CompoundValidator",
    "ConditionalValidator",
    "SerializationFault",
    "ValidationFault",
    "FieldValidationFault",
    
    # Lifecycle
    "LifecycleCoordinator",
    "LifecycleManager",
    
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
    
    # Artifacts
    "Artifact",
    "ArtifactEnvelope",
    "ArtifactKind",
    "ArtifactProvenance",
    "ArtifactIntegrity",
    "register_artifact_kind",
    "ArtifactBuilder",
    "ArtifactStore",
    "MemoryArtifactStore",
    "FilesystemArtifactStore",
    "ArtifactReader",
    "CodeArtifact",
    "ModelArtifact",
    "ConfigArtifact",
    "TemplateArtifact",
    "MigrationArtifact",
    "RegistryArtifact",
    "RouteArtifact",
    "DIGraphArtifact",
    "BundleArtifact",

    # Trace System
    "AquiliaTrace",
    "TraceManifest",
    "TraceRouteMap",
    "TraceDIGraph",
    "TraceSchemaLedger",
    "TraceLifecycleJournal",
    "TraceConfigSnapshot",
    "TraceDiagnostics",
]
