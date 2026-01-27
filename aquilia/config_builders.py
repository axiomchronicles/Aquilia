"""
Fluent Configuration Builders for Aquilia.

Provides a unique, type-safe, fluent API for configuring Aquilia workspaces.
Replaces YAML configuration with Python for better IDE support and validation.

Example:
    >>> workspace = (
    ...     Workspace("myapp", version="0.1.0")
    ...     .runtime(mode="dev", port=8000)
    ...     .module(Module("users").route_prefix("/users"))
    ...     .integrate(Integration.sessions(...))
    ... )
"""

from typing import Optional, List, Any, Dict
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class RuntimeConfig:
    """Runtime configuration."""
    mode: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    workers: int = 1


@dataclass
class ModuleConfig:
    """Module configuration."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    fault_domain: Optional[str] = None
    route_prefix: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    controllers: List[str] = field(default_factory=list)
    routes: List[Dict[str, Any]] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    providers: List[Dict[str, Any]] = field(default_factory=list)
    middlewares: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Discovery configuration
    auto_discover: bool = True  # Default to True for convenience
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fault_domain": self.fault_domain or self.name.upper(),
            "route_prefix": self.route_prefix or f"/{self.name}",
            "depends_on": self.depends_on,
            "controllers": self.controllers,
            "routes": self.routes,
            "services": self.services,
            "providers": self.providers,
            "middlewares": self.middlewares,
            "tags": self.tags,
            "auto_discover": self.auto_discover,
        }


class Module:
    """Fluent module builder."""
    
    def __init__(self, name: str, version: str = "0.1.0", description: str = ""):
        self._config = ModuleConfig(
            name=name,
            version=version,
            description=description,
            auto_discover=True,
        )
    
    def auto_discover(self, enabled: bool = True) -> "Module":
        """
        Configure auto-discovery behavior.
        
        If enabled (default), the runtime will automatically scan:
        - .controllers for Controller subclasses
        - .services for Service classes
        
        Args:
            enabled: Whether to enable auto-discovery
        """
        self._config.auto_discover = enabled
        return self
    
    def fault_domain(self, domain: str) -> "Module":
        """Set fault domain."""
        self._config.fault_domain = domain
        return self
    
    def route_prefix(self, prefix: str) -> "Module":
        """Set route prefix."""
        self._config.route_prefix = prefix
        return self
    
    def depends_on(self, *modules: str) -> "Module":
        """Set module dependencies."""
        self._config.depends_on = list(modules)
        return self
    
    def tags(self, *module_tags: str) -> "Module":
        """Set module tags for organization and filtering."""
        self._config.tags = list(module_tags)
        return self

    def register_controllers(self, *controllers: str) -> "Module":
        """Register explicit controllers."""
        self._config.controllers.extend(controllers)
        return self

    def register_services(self, *services: str) -> "Module":
        """Register explicit services."""
        self._config.services.extend(services)
        return self
        
    def register_providers(self, *providers: Dict[str, Any]) -> "Module":
        """Register explicit DI providers."""
        self._config.providers.extend(providers)
        return self
        
    def register_routes(self, *routes: Dict[str, Any]) -> "Module":
        """Register explicit routes."""
        self._config.routes.extend(routes)
        return self

    def register_middlewares(self, *middlewares: str) -> "Module":
        """Register explicit middlewares."""
        self._config.middlewares.extend(middlewares)
        return self
    
    def build(self) -> ModuleConfig:
        """Build module configuration."""
        return self._config


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enabled: bool = True
    store_type: str = "memory"
    secret_key: str = "aquilia_insecure_dev_secret"
    algorithm: str = "HS256"
    issuer: str = "aquilia"
    audience: str = "aquilia-app"
    access_token_ttl_minutes: int = 60
    refresh_token_ttl_days: int = 30
    require_auth_by_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "enabled": self.enabled,
            "store": {
                "type": self.store_type,
            },
            "tokens": {
                "secret_key": self.secret_key,
                "algorithm": self.algorithm,
                "issuer": self.issuer,
                "audience": self.audience,
                "access_token_ttl_minutes": self.access_token_ttl_minutes,
                "refresh_token_ttl_days": self.refresh_token_ttl_days,
            },
            "security": {
                "require_auth_by_default": self.require_auth_by_default,
            }
        }


class Integration:
    """Integration configuration builders."""
    
    @staticmethod
    def auth(
        config: Optional[AuthConfig] = None,
        enabled: bool = True,
        store_type: str = "memory",
        secret_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Configure authentication.
        
        Args:
            config: AuthConfig object (optional)
            enabled: Enable authentication
            store_type: Store type (memory, etc.)
            secret_key: Secret key for tokens
            **kwargs: Overrides
            
        Returns:
            Auth configuration dictionary
        """
        if config:
            # Use provided config object
            conf_dict = config.to_dict()
        else:
            # Build from arguments using defaults from AuthConfig
            defaults = AuthConfig()
            conf_dict = {
                "enabled": enabled,
                "store": {
                    "type": store_type,
                },
                "tokens": {
                    "secret_key": secret_key or defaults.secret_key,
                    "algorithm": defaults.algorithm,
                    "issuer": defaults.issuer,
                    "audience": defaults.audience,
                    "access_token_ttl_minutes": defaults.access_token_ttl_minutes,
                    "refresh_token_ttl_days": defaults.refresh_token_ttl_days,
                },
                "security": {
                    "require_auth_by_default": defaults.require_auth_by_default,
                }
            }
            
        # Apply kwargs overrides (deep merge logic simplified for common top-level overrides)
        # Note: A real deep merge might be better but for now we trust the structure
        conf_dict.update(kwargs)
        
        return conf_dict

    
    @staticmethod
    def sessions(
        policy: Optional[Any] = None,
        store: Optional[Any] = None,
        transport: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Configure session integration with Aquilia's unique fluent syntax.
        
        Unique Features:
        - Chained policy builders: SessionPolicy.for_users().lasting(days=7).rotating_on_auth()
        - Smart defaults: Auto-configures based on environment
        - Policy templates: .web_users(), .api_tokens(), .mobile_apps()
        
        Args:
            policy: SessionPolicy instance or policy builder
            store: Store instance or store config
            transport: Transport instance or transport config
            **kwargs: Additional session configuration
            
        Returns:
            Session configuration dictionary
            
        Examples:
            # Unique Aquilia syntax:
            .integrate(Integration.sessions(
                policy=SessionPolicy.for_web_users()
                    .lasting(days=14)
                    .idle_timeout(hours=2)
                    .rotating_on_privilege_change()
                    .scoped_to("tenant"),
                store=MemoryStore.with_capacity(50000),
                transport=CookieTransport.secure_defaults()
            ))
            
            # Template syntax:
            .integrate(Integration.sessions.web_app())
            .integrate(Integration.sessions.api_service())
            .integrate(Integration.sessions.mobile_app())
        """
        from aquilia.sessions import SessionPolicy, MemoryStore, CookieTransport, TransportPolicy
        
        # Smart policy creation with Aquilia's unique builders
        if policy is None:
            policy = SessionPolicy.for_web_users().with_smart_defaults()
        
        # Smart store selection
        if store is None:
            store = MemoryStore.optimized_for_development()
        
        # Smart transport with security defaults
        if transport is None:
            if hasattr(policy, 'transport') and policy.transport:
                transport = CookieTransport.from_policy(policy.transport)
            else:
                transport = CookieTransport.with_aquilia_defaults()
        
        return {
            "enabled": True,
            "policy": policy,
            "store": store,
            "transport": transport,
            "aquilia_syntax_version": "2.0",  # Mark as enhanced syntax
            **kwargs
        }
    
    @staticmethod
    def di(auto_wire: bool = True, **kwargs) -> Dict[str, Any]:
        """Configure dependency injection."""
        return {
            "enabled": True,
            "auto_wire": auto_wire,
            **kwargs
        }
    
    # ========================================================================
    # Unique Aquilia Session Templates
    # ========================================================================
    
    class sessions:
        """Unique Aquilia session configuration templates."""
        
        @staticmethod
        def web_app(**overrides) -> Dict[str, Any]:
            """Optimized for web applications with users."""
            from aquilia.sessions import SessionPolicy, MemoryStore, CookieTransport
            
            policy = SessionPolicy.for_web_users().lasting(days=7).idle_timeout(hours=2).web_defaults().build()
            store = MemoryStore.web_optimized()
            transport = CookieTransport.for_web_browsers()
            
            return {
                "enabled": True,
                "policy": policy,
                "store": store,
                "transport": transport,
                "aquilia_syntax_version": "2.0",
                **overrides
            }
        
        @staticmethod
        def api_service(**overrides) -> Dict[str, Any]:
            """Optimized for API services with token-based auth."""
            from aquilia.sessions import SessionPolicy, MemoryStore, HeaderTransport
            
            policy = SessionPolicy.for_api_tokens().lasting(hours=1).no_idle_timeout().api_defaults().build()
            store = MemoryStore.api_optimized()
            transport = HeaderTransport.for_rest_apis()
            
            return {
                "enabled": True,
                "policy": policy,
                "store": store,
                "transport": transport,
                "aquilia_syntax_version": "2.0",
                **overrides
            }
        
        @staticmethod  
        def mobile_app(**overrides) -> Dict[str, Any]:
            """Optimized for mobile applications with long-lived sessions."""
            from aquilia.sessions import SessionPolicy, MemoryStore, CookieTransport
            
            policy = SessionPolicy.for_mobile_users().lasting(days=90).idle_timeout(days=30).mobile_defaults().build()
            store = MemoryStore.mobile_optimized()
            transport = CookieTransport.for_mobile_webviews()
            
            return {
                "enabled": True,
                "policy": policy,
                "store": store,
                "transport": transport,
                "aquilia_syntax_version": "2.0",
                **overrides
            }
    
    @staticmethod
    def registry(**kwargs) -> Dict[str, Any]:
        """Configure registry."""
        return {
            "enabled": True,
            **kwargs
        }
    
    @staticmethod
    def routing(strict_matching: bool = True, **kwargs) -> Dict[str, Any]:
        """Configure routing."""
        return {
            "enabled": True,
            "strict_matching": strict_matching,
            **kwargs
        }
    
    @staticmethod
    def fault_handling(default_strategy: str = "propagate", **kwargs) -> Dict[str, Any]:
        """Configure fault handling."""
        return {
            "enabled": True,
            "default_strategy": default_strategy,
            **kwargs
        }
    
    class templates:
        """
        Fluent template configuration builder.
        
        Unique Syntax:
            Integration.templates.source("...").secure().cached()
        """
        
        class Builder(dict):
            """Fluent builder inheriting from dict for compatibility."""
            
            def __init__(self, defaults: Optional[Dict] = None):
                super().__init__(defaults or {
                    "enabled": True,
                    "search_paths": ["templates"],
                    "cache": "memory",
                    "sandbox": True,
                    "precompile": False,
                })
                
            def source(self, *paths: str) -> "Integration.templates.Builder":
                """Add template search paths."""
                current = self.get("search_paths", [])
                if current == ["templates"]:  # Replace default
                    current = []
                self["search_paths"] = current + list(paths)
                return self
                
            def scan_modules(self) -> "Integration.templates.Builder":
                """Enable module auto-discovery."""
                # This is implicit in server logic but good for intent
                return self
                
            def cached(self, strategy: str = "memory") -> "Integration.templates.Builder":
                """Enable bytecode caching."""
                self["cache"] = strategy
                return self
                
            def secure(self, strict: bool = True) -> "Integration.templates.Builder":
                """Enable sandbox with security policy."""
                self["sandbox"] = True
                self["sandbox_policy"] = "strict" if strict else "permissive"
                return self
                
            def unsafe_dev_mode(self) -> "Integration.templates.Builder":
                """Disable sandbox/caching for development."""
                self["sandbox"] = False
                self["cache"] = "none"
                return self
                
            def precompile(self) -> "Integration.templates.Builder":
                """Enable startup precompilation."""
                self["precompile"] = True
                return self
        
        @classmethod
        def source(cls, *paths: str) -> "Integration.templates.Builder":
            """Start builder with source paths."""
            return cls.Builder().source(*paths)
            
        @classmethod
        def defaults(cls) -> "Integration.templates.Builder":
            """Start with default configuration."""
            return cls.Builder()

    @staticmethod
    def patterns(**kwargs) -> Dict[str, Any]:
        """Configure patterns."""
        return {
            "enabled": True,
            **kwargs
        }


class Workspace:
    """Fluent workspace builder."""
    
    def __init__(self, name: str, version: str = "0.1.0", description: str = ""):
        self._name = name
        self._version = version
        self._description = description
        self._runtime = RuntimeConfig()
        self._modules: List[ModuleConfig] = []
        self._integrations: Dict[str, Dict[str, Any]] = {}
        self._sessions_config: Optional[Dict[str, Any]] = None
        self._security_config: Optional[Dict[str, Any]] = None
        self._telemetry_config: Optional[Dict[str, Any]] = None
    
    def runtime(
        self,
        mode: str = "dev",
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = True,
        workers: int = 1,
    ) -> "Workspace":
        """Configure runtime settings."""
        self._runtime = RuntimeConfig(
            mode=mode,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
        )
        return self
    
    def module(self, module: Module) -> "Workspace":
        """Add a module to the workspace."""
        self._modules.append(module.build())
        return self
    
    def integrate(self, integration: Dict[str, Any]) -> "Workspace":
        """Add an integration."""
        # Determine integration type from keys
        if "tokens" in integration and "security" in integration:
            self._integrations["auth"] = integration
        elif "policy" in integration or "store" in integration:
            self._integrations["sessions"] = integration
        elif "auto_wire" in integration:
            self._integrations["dependency_injection"] = integration
        elif "strict_matching" in integration:
            self._integrations["routing"] = integration
        elif "default_strategy" in integration:
            self._integrations["fault_handling"] = integration
        elif "search_paths" in integration and "cache" in integration:
            self._integrations["templates"] = integration
        else:
            # Generic integration
            for key, value in integration.items():
                if key != "enabled":
                    self._integrations[key] = integration
                    break
        return self
    
    def sessions(self, policies: Optional[List[Any]] = None, **kwargs) -> "Workspace":
        """
        Configure session management.
        
        Args:
            policies: List of SessionPolicy instances
            **kwargs: Additional session configuration
        """
        self._sessions_config = {
            "enabled": True,
            "policies": policies or [],
            **kwargs
        }
        return self
    
    def security(
        self,
        cors_enabled: bool = False,
        csrf_protection: bool = False,
        helmet_enabled: bool = True,
        rate_limiting: bool = False,
        **kwargs
    ) -> "Workspace":
        """
        Configure security features.
        
        Args:
            cors_enabled: Enable CORS
            csrf_protection: Enable CSRF protection
            helmet_enabled: Enable Helmet.js security headers
            rate_limiting: Enable rate limiting
            **kwargs: Additional security configuration
        """
        self._security_config = {
            "enabled": True,
            "cors_enabled": cors_enabled,
            "csrf_protection": csrf_protection,
            "helmet_enabled": helmet_enabled,
            "rate_limiting": rate_limiting,
            **kwargs
        }
        return self
    
    def telemetry(
        self,
        tracing_enabled: bool = False,
        metrics_enabled: bool = True,
        logging_enabled: bool = True,
        **kwargs
    ) -> "Workspace":
        """
        Configure telemetry and observability.
        
        Args:
            tracing_enabled: Enable distributed tracing
            metrics_enabled: Enable metrics collection
            logging_enabled: Enable structured logging
            **kwargs: Additional telemetry configuration
        """
        self._telemetry_config = {
            "enabled": True,
            "tracing_enabled": tracing_enabled,
            "metrics_enabled": metrics_enabled,
            "logging_enabled": logging_enabled,
            **kwargs
        }
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert workspace to dictionary format compatible with ConfigLoader.
        
        Returns:
            Configuration dictionary
        """
        config = {
            "workspace": {
                "name": self._name,
                "version": self._version,
                "description": self._description,
            },
            "runtime": {
                "mode": self._runtime.mode,
                "host": self._runtime.host,
                "port": self._runtime.port,
                "reload": self._runtime.reload,
                "workers": self._runtime.workers,
            },
            "modules": [m.to_dict() for m in self._modules],
            "integrations": self._integrations,
        }
        
        # Add optional configurations
        if self._sessions_config:
            config["sessions"] = self._sessions_config
            # Also add to integrations for compatibility
            if "integrations" not in config:
                config["integrations"] = {}
            config["integrations"]["sessions"] = self._sessions_config
        if self._security_config:
            config["security"] = self._security_config
        if self._telemetry_config:
            config["telemetry"] = self._telemetry_config
        
        return config
    
    def __repr__(self) -> str:
        return f"Workspace(name='{self._name}', version='{self._version}', modules={len(self._modules)})"


__all__ = [
    "Workspace",
    "Module",
    "Integration",
    "RuntimeConfig",
    "ModuleConfig",
]
