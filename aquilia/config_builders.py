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
    socket_controllers: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Database configuration (per-module override)
    database: Optional[Dict[str, Any]] = None
    
    # Discovery configuration
    auto_discover: bool = True  # Default to True for convenience
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
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
            "socket_controllers": self.socket_controllers,
            "models": self.models,
            "tags": self.tags,
            "auto_discover": self.auto_discover,
        }
        if self.database:
            result["database"] = self.database
        return result


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

    def register_sockets(self, *sockets: str) -> "Module":
        """Register explicit WebSocket controllers."""
        self._config.socket_controllers.extend(sockets)
        return self

    def register_middlewares(self, *middlewares: str) -> "Module":
        """Register explicit middlewares."""
        self._config.middlewares.extend(middlewares)
        return self
    
    def register_models(self, *models: str) -> "Module":
        """
        Register explicit model files or glob patterns.
        
        Supports both legacy .amdl files and new Python model modules.
        
        Args:
            *models: Paths to model files or glob patterns.
                     E.g. "models/user.py", "models/*.py", "models/legacy.amdl"
        """
        self._config.models.extend(models)
        return self
    
    def database(
        self,
        url: str = "sqlite:///db.sqlite3",
        auto_connect: bool = True,
        auto_create: bool = True,
        auto_migrate: bool = False,
        migrations_dir: str = "migrations",
        **kwargs,
    ) -> "Module":
        """
        Configure database for this module.
        
        Args:
            url: Database URL
            auto_connect: Connect on startup
            auto_create: Create tables automatically
            auto_migrate: Run pending migrations on startup
            migrations_dir: Migration files directory
            **kwargs: Additional database options
        """
        self._config.database = {
            "url": url,
            "auto_connect": auto_connect,
            "auto_create": auto_create,
            "auto_migrate": auto_migrate,
            "migrations_dir": migrations_dir,
            **kwargs,
        }
        return self
    
    def build(self) -> ModuleConfig:
        """Build module configuration."""
        return self._config


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enabled: bool = True
    store_type: str = "memory"
    secret_key: Optional[str] = None  # MUST be set explicitly; no insecure default
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
                    "secret_key": secret_key or defaults.secret_key,  # None if not provided
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
    
    @staticmethod
    def database(
        url: str = "sqlite:///db.sqlite3",
        auto_connect: bool = True,
        auto_create: bool = True,
        auto_migrate: bool = False,
        migrations_dir: str = "migrations",
        pool_size: int = 5,
        echo: bool = False,
        model_paths: Optional[List[str]] = None,
        scan_dirs: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure database and AMDL model integration.
        
        Args:
            url: Database URL (sqlite:///path, postgresql://..., etc.)
            auto_connect: Connect database on server startup
            auto_create: Automatically create tables from discovered models
            auto_migrate: Run pending migrations on startup
            migrations_dir: Directory for migration files
            pool_size: Connection pool size
            echo: Log SQL statements
            model_paths: Explicit .amdl file paths
            scan_dirs: Directories to scan for .amdl files
            **kwargs: Additional database options
        
        Returns:
            Database configuration dictionary
            
        Example:
            ```python
            .integrate(Integration.database(
                url="sqlite:///app.db",
                auto_create=True,
                scan_dirs=["models", "modules/*/models"],
            ))
            ```
        """
        return {
            "enabled": True,
            "url": url,
            "auto_connect": auto_connect,
            "auto_create": auto_create,
            "auto_migrate": auto_migrate,
            "migrations_dir": migrations_dir,
            "pool_size": pool_size,
            "echo": echo,
            "model_paths": model_paths or [],
            "scan_dirs": scan_dirs or ["models"],
            **kwargs,
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

    @staticmethod
    def static_files(
        directories: Optional[Dict[str, str]] = None,
        cache_max_age: int = 86400,
        immutable: bool = False,
        etag: bool = True,
        gzip: bool = True,
        brotli: bool = True,
        memory_cache: bool = True,
        html5_history: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure static file serving middleware.

        Args:
            directories: Mapping of URL prefix → filesystem directory.
                         Example: {"/static": "static", "/media": "uploads"}
            cache_max_age: Cache-Control max-age in seconds (default 1 day).
            immutable: Set Cache-Control: immutable for fingerprinted assets.
            etag: Enable ETag generation.
            gzip: Serve pre-compressed .gz files.
            brotli: Serve pre-compressed .br files.
            memory_cache: Enable in-memory LRU file cache.
            html5_history: Serve index.html for SPA 404s.

        Returns:
            Static files configuration dictionary.

        Example::

            .integrate(Integration.static_files(
                directories={"/static": "static", "/media": "uploads"},
                cache_max_age=86400,
                etag=True,
            ))
        """
        return {
            "_integration_type": "static_files",
            "enabled": True,
            "directories": directories or {"/static": "static"},
            "cache_max_age": cache_max_age,
            "immutable": immutable,
            "etag": etag,
            "gzip": gzip,
            "brotli": brotli,
            "memory_cache": memory_cache,
            "html5_history": html5_history,
            **kwargs,
        }

    @staticmethod
    def cors(
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
        allow_origin_regex: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure CORS middleware.

        Args:
            allow_origins: Allowed origins (supports globs like "*.example.com").
            allow_methods: Allowed HTTP methods.
            allow_headers: Allowed request headers.
            expose_headers: Headers exposed to the browser.
            allow_credentials: Allow cookies / Authorization header.
            max_age: Preflight cache duration (seconds).
            allow_origin_regex: Regex pattern for origin matching.

        Returns:
            CORS configuration dictionary.

        Example::

            .integrate(Integration.cors(
                allow_origins=["https://example.com", "*.staging.example.com"],
                allow_credentials=True,
                max_age=3600,
            ))
        """
        return {
            "_integration_type": "cors",
            "enabled": True,
            "allow_origins": allow_origins or ["*"],
            "allow_methods": allow_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
            "allow_headers": allow_headers or ["accept", "accept-language", "content-language", "content-type", "authorization", "x-requested-with"],
            "expose_headers": expose_headers or [],
            "allow_credentials": allow_credentials,
            "max_age": max_age,
            "allow_origin_regex": allow_origin_regex,
            **kwargs,
        }

    @staticmethod
    def csp(
        policy: Optional[Dict[str, List[str]]] = None,
        report_only: bool = False,
        nonce: bool = True,
        preset: str = "strict",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure Content-Security-Policy middleware.

        Args:
            policy: CSP directives dict (e.g. {"default-src": ["'self'"]}).
            report_only: Use Content-Security-Policy-Report-Only header.
            nonce: Enable per-request nonce generation.
            preset: "strict" or "relaxed" (used when policy is None).

        Returns:
            CSP configuration dictionary.

        Example::

            .integrate(Integration.csp(
                policy={
                    "default-src": ["'self'"],
                    "script-src": ["'self'", "'nonce-{nonce}'"],
                    "style-src": ["'self'", "'unsafe-inline'"],
                },
                nonce=True,
            ))
        """
        return {
            "_integration_type": "csp",
            "enabled": True,
            "policy": policy,
            "report_only": report_only,
            "nonce": nonce,
            "preset": preset,
            **kwargs,
        }

    @staticmethod
    def rate_limit(
        limit: int = 100,
        window: int = 60,
        algorithm: str = "sliding_window",
        per_user: bool = False,
        burst: Optional[int] = None,
        exempt_paths: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure rate limiting middleware.

        Args:
            limit: Maximum requests per window.
            window: Window size in seconds.
            algorithm: "sliding_window" or "token_bucket".
            per_user: Use user identity as key (requires auth).
            burst: Extra burst capacity (token_bucket only).
            exempt_paths: Paths to skip rate limiting.

        Returns:
            Rate limit configuration dictionary.

        Example::

            .integrate(Integration.rate_limit(
                limit=200,
                window=60,
                algorithm="token_bucket",
                burst=50,
            ))
        """
        return {
            "_integration_type": "rate_limit",
            "enabled": True,
            "limit": limit,
            "window": window,
            "algorithm": algorithm,
            "per_user": per_user,
            "burst": burst,
            "exempt_paths": exempt_paths or ["/health", "/healthz", "/ready"],
            **kwargs,
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
        self._database_config: Optional[Dict[str, Any]] = None
    
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
        # Check for explicit integration type marker
        integration_type = integration.get("_integration_type")
        if integration_type:
            self._integrations[integration_type] = integration
            # Wire specific types to their config slots
            if integration_type == "cors":
                if not self._security_config:
                    self._security_config = {"enabled": True}
                self._security_config["cors_enabled"] = True
                self._security_config["cors"] = integration
            elif integration_type == "csp":
                if not self._security_config:
                    self._security_config = {"enabled": True}
                self._security_config["csp"] = integration
            elif integration_type == "rate_limit":
                if not self._security_config:
                    self._security_config = {"enabled": True}
                self._security_config["rate_limiting"] = True
                self._security_config["rate_limit"] = integration
            elif integration_type == "static_files":
                self._integrations["static_files"] = integration
            return self

        # Determine integration type from keys (legacy detection)
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
        elif "url" in integration and ("auto_create" in integration or "scan_dirs" in integration):
            self._integrations["database"] = integration
            self._database_config = integration
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
        https_redirect: bool = False,
        hsts: bool = True,
        proxy_fix: bool = False,
        **kwargs
    ) -> "Workspace":
        """
        Configure security features.
        
        These flags control which security middleware are automatically
        added to the middleware stack during server startup.

        For fine-grained control, use Integration.cors(), Integration.csp(),
        Integration.rate_limit() instead (or in addition).
        
        Args:
            cors_enabled: Enable CORS middleware (default origins: *)
            csrf_protection: Enable CSRF protection
            helmet_enabled: Enable Helmet-style security headers
            rate_limiting: Enable rate limiting (100 req/min default)
            https_redirect: Enable HTTP→HTTPS redirect
            hsts: Enable HSTS header (Strict-Transport-Security)
            proxy_fix: Enable X-Forwarded-* header processing
            **kwargs: Additional security configuration
        """
        self._security_config = {
            "enabled": True,
            "cors_enabled": cors_enabled,
            "csrf_protection": csrf_protection,
            "helmet_enabled": helmet_enabled,
            "rate_limiting": rate_limiting,
            "https_redirect": https_redirect,
            "hsts": hsts,
            "proxy_fix": proxy_fix,
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
    
    def database(
        self,
        url: str = "sqlite:///db.sqlite3",
        auto_connect: bool = True,
        auto_create: bool = True,
        auto_migrate: bool = False,
        migrations_dir: str = "migrations",
        **kwargs,
    ) -> "Workspace":
        """
        Configure global database for the workspace.
        
        This sets the default database for all modules.
        Individual modules can override with Module.database().
        
        Args:
            url: Database URL
            auto_connect: Connect on startup
            auto_create: Create tables on startup
            auto_migrate: Run pending migrations on startup
            migrations_dir: Migration files directory
            **kwargs: Additional database options
            
        Example:
            ```python
            workspace = (
                Workspace("myapp")
                .database(url="sqlite:///app.db", auto_create=True)
                .module(Module("blog").register_models("models/blog.amdl"))
            )
            ```
        """
        self._database_config = {
            "enabled": True,
            "url": url,
            "auto_connect": auto_connect,
            "auto_create": auto_create,
            "auto_migrate": auto_migrate,
            "migrations_dir": migrations_dir,
            **kwargs,
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
        if self._database_config:
            config["database"] = self._database_config
            # Also add to integrations for compatibility
            config["integrations"]["database"] = self._database_config
        
        return config
    
    def __repr__(self) -> str:
        return f"Workspace(name='{self._name}', version='{self._version}', modules={len(self._modules)})"


__all__ = [
    "Workspace",
    "Module",
    "Integration",
    "RuntimeConfig",
    "ModuleConfig",
    "AuthConfig",
]
