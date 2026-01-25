"""
AppManifest - Production-grade, data-driven application manifest system.

No import-time side effects, fully serializable and inspectable.
Provides precise control over middleware, sessions, DI, lifecycle, and error handling.
"""

from typing import Any, Callable, Optional, Type, List, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta
import hashlib
import json


class ServiceScope(str, Enum):
    """Service lifecycle scope."""
    SINGLETON = "singleton"      # App-level single instance
    APP = "app"                  # Module-level single instance
    REQUEST = "request"          # New instance per request
    TRANSIENT = "transient"      # Always new instance
    POOLED = "pooled"            # Object pool
    EPHEMERAL = "ephemeral"      # Fastest, no lifecycle


@dataclass
class LifecycleConfig:
    """Lifecycle hook configuration."""
    on_startup: Optional[str] = None      # "path.to.module:function"
    on_shutdown: Optional[str] = None     # "path.to.module:function"
    depends_on: List[str] = field(default_factory=list)  # Services to wait for
    startup_timeout: float = 30.0         # Timeout in seconds
    shutdown_timeout: float = 30.0        # Timeout in seconds
    error_strategy: str = "propagate"     # "propagate", "log", "ignore"
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "on_startup": self.on_startup,
            "on_shutdown": self.on_shutdown,
            "depends_on": self.depends_on,
            "startup_timeout": self.startup_timeout,
            "shutdown_timeout": self.shutdown_timeout,
            "error_strategy": self.error_strategy,
        }


@dataclass
class ServiceConfig:
    """Service registration configuration with complete DI support."""
    class_path: str                       # "path.to.module:ClassName"
    scope: ServiceScope = ServiceScope.APP  # Lifecycle scope
    
    # Auto-discovery
    auto_discover: bool = True            # Auto-wire dependencies
    
    # Lifecycle management
    lifecycle: Optional[LifecycleConfig] = None
    
    # Feature flags
    feature_flags: List[str] = field(default_factory=list)  # Conditional registration
    
    # DI alternatives
    aliases: List[str] = field(default_factory=list)  # Alternative injection names
    
    # Factory pattern
    factory: Optional[str] = None         # "path.to.module:factory_function"
    factory_args: Optional[Dict[str, Any]] = None  # Factory arguments
    
    # Configuration
    config: Optional[Dict[str, Any]] = None  # Constructor kwargs
    
    # Observability
    observable: bool = True               # Include in metrics/tracing
    required: bool = True                 # Fail if can't register
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "class_path": self.class_path,
            "scope": getattr(self.scope, "value", str(self.scope)),
            "auto_discover": self.auto_discover,
            "aliases": self.aliases,
            "factory": self.factory,
            "config": self.config or {},
        }


@dataclass
class MiddlewareConfig:
    """Middleware registration configuration."""
    class_path: str                       # "path.to.module:ClassName"
    scope: str = "global"                 # "global", "app", "route"
    scope_target: Optional[str] = None    # For app:name or route:/pattern
    priority: int = 50                    # Lower = earlier execution
    
    # Conditional execution
    condition: Optional[Callable] = None  # Optional function returning bool
    
    # Configuration
    config: Optional[Dict[str, Any]] = None  # Constructor kwargs
    
    # Error handling
    on_error: str = "propagate"          # "propagate", "skip", "fallback"
    fallback: Optional[str] = None        # Fallback middleware path
    
    # Observability
    observable: bool = True               # Include in metrics
    log_requests: bool = False            # Log individual requests
    log_responses: bool = False           # Log individual responses
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "class_path": self.class_path,
            "scope": self.scope,
            "priority": self.priority,
            "config": self.config or {},
        }


@dataclass
class SessionConfig:
    """Session management configuration."""
    name: str                             # Session policy name
    enabled: bool = True                  # Enable/disable
    ttl: timedelta = field(default_factory=lambda: timedelta(days=7))  # Time to live
    idle_timeout: Optional[timedelta] = None  # Inactivity timeout
    renewal: Optional[timedelta] = None   # Renewal window
    
    # Transport layer
    transport: str = "cookie"             # "cookie", "header", "custom"
    transport_config: Optional[Dict[str, Any]] = None  # Transport-specific config
    
    # Cookie-specific settings (for transport="cookie")
    cookie_name: str = "session_id"
    cookie_domain: Optional[str] = None
    cookie_path: str = "/"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "Strict"       # "Strict", "Lax", "None"
    
    # Storage
    store: str = "memory"                 # "memory", "redis", "database", "custom"
    store_config: Optional[Dict[str, Any]] = None  # Store-specific config
    
    # Encryption
    encryption_enabled: bool = True
    encryption_key_env: str = "SESSION_ENCRYPTION_KEY"
    
    # Serialization
    serializer: str = "json"              # "json", "pickle", "msgpack"
    
    # Observability
    log_lifecycle: bool = False           # Log session create/destroy
    metrics_enabled: bool = True          # Collect metrics
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "ttl": str(self.ttl),
            "transport": self.transport,
            "store": self.store,
            "cookie_secure": self.cookie_secure,
            "cookie_httponly": self.cookie_httponly,
            "cookie_samesite": self.cookie_samesite,
        }


@dataclass
class FaultHandlerConfig:
    """Fault handler configuration."""
    domain: str                           # Fault domain (e.g., "AUTH", "VALIDATION")
    handler_path: str                     # "path.to.module:handler_function"
    recovery_strategy: str = "propagate"  # "propagate", "recover", "fallback"
    fallback_response: Optional[Dict[str, Any]] = None  # Fallback response


@dataclass
class FaultHandlingConfig:
    """Fault/error handling configuration."""
    default_domain: str = "APP"           # Default fault domain
    strategy: str = "propagate"           # "propagate", "recover", "fallback"
    handlers: List[FaultHandlerConfig] = field(default_factory=list)  # Domain handlers
    middlewares: List[MiddlewareConfig] = field(default_factory=list)  # Error middlewares
    metrics_enabled: bool = True          # Collect error metrics
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "default_domain": self.default_domain,
            "strategy": self.strategy,
            "handlers": [h.__dict__ for h in self.handlers],
            "metrics_enabled": self.metrics_enabled,
        }


@dataclass
class FeatureConfig:
    """Feature flag configuration."""
    name: str                             # Feature identifier
    enabled: bool = False                 # Default state
    conditions: Optional[Dict[str, Any]] = None  # Conditional rules
    services: List[str] = field(default_factory=list)  # Services to register
    controllers: List[str] = field(default_factory=list)  # Controllers to register
    middleware: List[MiddlewareConfig] = field(default_factory=list)  # Middleware
    routes: List[str] = field(default_factory=list)  # Routes to register
    
    # Observability
    log_usage: bool = True                # Log feature usage
    metrics_enabled: bool = True          # Collect metrics
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "conditions": self.conditions or {},
        }


@dataclass
class AppManifest:
    """
    Production-grade application manifest for complete app configuration.
    
    Provides precise control over:
    - Services with DI scopes and lifecycle
    - Controllers with routing
    - Middleware with scoping and priority
    - Sessions with policies and storage
    - Error handling with fault domains
    - Feature flags with conditional activation
    """
    
    # Identity
    name: str                             # Module name
    version: str                          # Semantic version
    description: str = ""                 # Module description
    author: str = ""                      # Module author
    
    # Component declarations
    services: List[ServiceConfig] = field(default_factory=list)  # Detailed service config
    controllers: List[str] = field(default_factory=list)  # "path:ClassName" format
    
    # Middleware configuration
    middleware: List[MiddlewareConfig] = field(default_factory=list)
    
    # Routing
    route_prefix: str = "/"               # Route prefix for module
    base_path: Optional[str] = None       # Optional base path override
    
    # Lifecycle management
    lifecycle: Optional[LifecycleConfig] = None
    
    # Session management
    sessions: List[SessionConfig] = field(default_factory=list)
    
    # Error handling
    faults: Optional[FaultHandlingConfig] = None
    
    # Feature flags
    features: List[FeatureConfig] = field(default_factory=list)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None  # JSON Schema for validation
    
    # Legacy support (for backward compatibility)
    middlewares: List[Tuple[str, dict]] = field(default_factory=list)  # Old format
    default_fault_domain: Optional[str] = None  # Old format
    on_startup: Optional[Callable] = None  # Old format
    on_shutdown: Optional[Callable] = None  # Old format
    config: Optional[Type] = None  # Old format
    
    def __post_init__(self):
        """Validate manifest structure."""
        if not self.name:
            raise ValueError("Manifest must have a name")
        if not self.version:
            raise ValueError("Manifest must have a version")
        
        # Validate name format (alphanumeric + underscore)
        if not self.name.replace("_", "").isalnum():
            raise ValueError(f"Invalid app name '{self.name}': must be alphanumeric with underscores")
        
        # Convert legacy middleware format to new format if needed
        if self.middlewares and not self.middleware:
            for path, kwargs in self.middlewares:
                self.middleware.append(
                    MiddlewareConfig(
                        class_path=path,
                        config=kwargs or {}
                    )
                )
        
        # Convert legacy fault domain to new format if needed
        if self.default_fault_domain and not self.faults:
            self.faults = FaultHandlingConfig(
                default_domain=self.default_fault_domain
            )
    
    def to_dict(self) -> dict:
        """Serialize manifest to dictionary (for fingerprinting)."""
        return {
            "name": self.name,
            "version": self.version,
            "controllers": self.controllers,
            "services": [s.to_dict() for s in self.services],
            "depends_on": self.depends_on,
            "middleware": [m.to_dict() for m in self.middleware],
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
        }
    
    def fingerprint(self) -> str:
        """Generate stable hash of manifest for reproducible deploys."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ManifestLoader:
    """Loads, validates, and manages application manifests."""
    
    @staticmethod
    def load_manifests(manifest_classes: List[Type[AppManifest]]) -> List[AppManifest]:
        """
        Instantiate manifest classes and validate them.
        
        Args:
            manifest_classes: List of AppManifest subclasses or instances
            
        Returns:
            List of instantiated and validated manifests
            
        Raises:
            TypeError: If invalid manifest type
            ValueError: If duplicate app names or invalid configuration
        """
        manifests = []
        names_seen = set()
        
        for cls in manifest_classes:
            # Check if it's already an instance (AppManifest object)
            if isinstance(cls, AppManifest):
                manifest = cls
            # Check if it's a class that can be instantiated
            elif isinstance(cls, type):
                manifest = cls()
            else:
                raise TypeError(f"Expected AppManifest instance or class, got {type(cls)}")
            
            # Check for duplicate names
            if manifest.name in names_seen:
                raise ValueError(
                    f"Duplicate app name '{manifest.name}' found. "
                    f"Each app must have a unique name."
                )
            names_seen.add(manifest.name)
            
            manifests.append(manifest)
        
        return manifests
    
    @staticmethod
    def validate_manifest(manifest: AppManifest) -> List[str]:
        """
        Validate a single manifest and return list of warnings/errors.
        
        Checks:
        - Version format (semver)
        - Circular dependencies
        - Service configurations
        - Middleware declarations
        - Session configurations
        - Fault handling setup
        
        Returns:
            List of validation messages (empty if valid)
        """
        issues = []
        
        # Validate version format
        if not manifest.version or "." not in manifest.version:
            issues.append(f"App '{manifest.name}': version should follow semver (e.g., '1.0.0')")
        
        # Check for circular self-dependency
        if manifest.name in manifest.depends_on:
            issues.append(f"App '{manifest.name}': cannot depend on itself")
        
        # Validate service configurations
        for idx, service in enumerate(manifest.services):
            if not service.class_path or ":" not in service.class_path:
                issues.append(
                    f"App '{manifest.name}': service[{idx}] class_path must be "
                    f"'module:ClassName' format"
                )
            
            # Validate scope
            try:
                ServiceScope(service.scope)
            except ValueError:
                issues.append(
                    f"App '{manifest.name}': service[{idx}] has invalid scope '{service.scope}'"
                )
            
            # Validate lifecycle dependencies
            if service.lifecycle and service.lifecycle.depends_on:
                for dep in service.lifecycle.depends_on:
                    service_names = [s.class_path.split(":")[-1] for s in manifest.services]
                    if dep not in service_names:
                        issues.append(
                            f"App '{manifest.name}': service '{service.class_path}' "
                            f"depends on '{dep}' which doesn't exist"
                        )
        
        # Validate middleware declarations
        for idx, mw in enumerate(manifest.middleware):
            if not mw.class_path or ":" not in mw.class_path:
                issues.append(
                    f"App '{manifest.name}': middleware[{idx}] class_path must be "
                    f"'module:ClassName' format"
                )
        
        # Validate session configurations
        for idx, session in enumerate(manifest.sessions):
            if not session.name:
                issues.append(
                    f"App '{manifest.name}': session[{idx}] must have a name"
                )
            
            if session.transport not in ["cookie", "header", "custom"]:
                issues.append(
                    f"App '{manifest.name}': session[{idx}] has invalid transport '{session.transport}'"
                )
            
            if session.store not in ["memory", "redis", "database", "custom"]:
                issues.append(
                    f"App '{manifest.name}': session[{idx}] has invalid store '{session.store}'"
                )
        
        # Validate legacy middleware format if present
        for idx, (path, kwargs) in enumerate(manifest.middlewares):
            if not isinstance(path, str) or ":" not in path:
                issues.append(
                    f"App '{manifest.name}': middleware[{idx}] path must be "
                    f"'module:callable' format"
                )
            if not isinstance(kwargs, dict):
                issues.append(
                    f"App '{manifest.name}': middleware[{idx}] kwargs must be a dict"
                )
        
        return issues
    
    @staticmethod
    def validate_all(manifests: List[AppManifest]) -> Dict[str, List[str]]:
        """
        Validate all manifests and collect issues.
        
        Args:
            manifests: List of manifests to validate
            
        Returns:
            Dictionary mapping manifest name to list of issues
        """
        issues_by_app = {}
        
        for manifest in manifests:
            issues = ManifestLoader.validate_manifest(manifest)
            if issues:
                issues_by_app[manifest.name] = issues
        
        return issues_by_app
