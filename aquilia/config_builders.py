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
    serializers: List[str] = field(default_factory=list)
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
            "serializers": self.serializers,
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
    
    def register_serializers(self, *serializers: str) -> "Module":
        """
        Register explicit serializer classes for this module.
        
        Args:
            *serializers: Import paths in ``"module.path:ClassName"`` format.
                          E.g. ``"modules.users.serializers:UserSerializer"``
        
        Example::
        
            Module("users")
                .register_serializers(
                    "modules.users.serializers:UserSerializer",
                    "modules.users.serializers:UserCreateSerializer",
                )
        """
        self._config.serializers.extend(serializers)
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
    def cache(
        backend: str = "memory",
        default_ttl: int = 300,
        max_size: int = 10000,
        eviction_policy: str = "lru",
        namespace: str = "default",
        key_prefix: str = "aq:",
        serializer: str = "json",
        redis_url: str = "redis://localhost:6379/0",
        redis_max_connections: int = 10,
        l1_max_size: int = 1000,
        l1_ttl: int = 60,
        l2_backend: str = "redis",
        middleware_enabled: bool = False,
        middleware_default_ttl: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure the caching subsystem.

        Supports memory (LRU/LFU), Redis, composite (L1+L2), and null
        backends with pluggable serialization and middleware.

        Args:
            backend: Backend type — ``"memory"``, ``"redis"``,
                     ``"composite"``, or ``"null"``.
            default_ttl: Default time-to-live in seconds.
            max_size: Maximum entries for memory backend.
            eviction_policy: ``"lru"``, ``"lfu"``, ``"fifo"``, ``"ttl"``,
                             or ``"random"``.
            namespace: Default namespace for key isolation.
            key_prefix: Global key prefix.
            serializer: ``"json"``, ``"pickle"``, or ``"msgpack"``.
            redis_url: Redis connection URL.
            redis_max_connections: Redis connection pool size.
            l1_max_size: L1 (memory) size for composite backend.
            l1_ttl: L1 TTL for composite backend.
            l2_backend: L2 backend for composite (``"redis"``).
            middleware_enabled: Enable HTTP response caching middleware.
            middleware_default_ttl: Response cache TTL.
            **kwargs: Additional overrides.

        Returns:
            Cache configuration dictionary.

        Examples::

            # Simple in-memory LRU cache
            .integrate(Integration.cache())

            # Redis backend
            .integrate(Integration.cache(
                backend="redis",
                redis_url="redis://cache.internal:6379/0",
                default_ttl=600,
            ))

            # Two-level composite cache
            .integrate(Integration.cache(
                backend="composite",
                l1_max_size=500,
                l1_ttl=30,
                redis_url="redis://localhost:6379/0",
            ))
        """
        return {
            "_integration_type": "cache",
            "enabled": True,
            "backend": backend,
            "default_ttl": default_ttl,
            "max_size": max_size,
            "eviction_policy": eviction_policy,
            "namespace": namespace,
            "key_prefix": key_prefix,
            "serializer": serializer,
            "redis_url": redis_url,
            "redis_max_connections": redis_max_connections,
            "l1_max_size": l1_max_size,
            "l1_ttl": l1_ttl,
            "l2_backend": l2_backend,
            "middleware_enabled": middleware_enabled,
            "middleware_default_ttl": middleware_default_ttl,
            **kwargs,
        }

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

    @staticmethod
    def openapi(
        title: str = "Aquilia API",
        version: str = "1.0.0",
        description: str = "",
        terms_of_service: str = "",
        contact_name: str = "",
        contact_email: str = "",
        contact_url: str = "",
        license_name: str = "",
        license_url: str = "",
        servers: Optional[List[Dict[str, str]]] = None,
        docs_path: str = "/docs",
        openapi_json_path: str = "/openapi.json",
        redoc_path: str = "/redoc",
        include_internal: bool = False,
        group_by_module: bool = True,
        infer_request_body: bool = True,
        infer_responses: bool = True,
        detect_security: bool = True,
        external_docs_url: str = "",
        external_docs_description: str = "",
        swagger_ui_theme: str = "",
        swagger_ui_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure OpenAPI specification generation and interactive documentation.

        Enables automatic API documentation from controller metadata, type hints,
        and docstrings. Serves Swagger UI at ``docs_path`` and ReDoc at ``redoc_path``.

        Args:
            title: API title shown in documentation.
            version: API version string.
            description: Markdown description for the API overview.
            terms_of_service: URL to Terms of Service.
            contact_name: Maintainer / team name.
            contact_email: Contact email address.
            contact_url: Contact URL.
            license_name: License name (e.g. "MIT", "Apache-2.0").
            license_url: URL to the full license text.
            servers: List of server dicts ``[{"url": "...", "description": "..."}]``.
            docs_path: URL path for Swagger UI (default ``/docs``).
            openapi_json_path: URL path for raw JSON spec (default ``/openapi.json``).
            redoc_path: URL path for ReDoc viewer (default ``/redoc``).
            include_internal: Include ``/_internal`` routes in the spec.
            group_by_module: Group tags by module.
            infer_request_body: Infer request bodies from source analysis.
            infer_responses: Infer response schemas from source analysis.
            detect_security: Auto-detect security schemes from pipeline guards.
            external_docs_url: URL to external documentation.
            external_docs_description: Description for external docs link.
            swagger_ui_theme: Swagger UI theme ("dark", "" for default).
            swagger_ui_config: Extra Swagger UI configuration overrides.
            enabled: Enable/disable OpenAPI routes entirely.

        Returns:
            OpenAPI configuration dictionary.

        Example::

            .integrate(Integration.openapi(
                title="My App API",
                version="2.0.0",
                description="Production API for My App",
                contact_name="Backend Team",
                contact_email="api@myapp.com",
                license_name="MIT",
                servers=[
                    {"url": "https://api.myapp.com", "description": "Production"},
                    {"url": "https://staging-api.myapp.com", "description": "Staging"},
                ],
                swagger_ui_theme="dark",
            ))
        """
        return {
            "_integration_type": "openapi",
            "enabled": enabled,
            "title": title,
            "version": version,
            "description": description,
            "terms_of_service": terms_of_service,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_url": contact_url,
            "license_name": license_name,
            "license_url": license_url,
            "servers": servers or [],
            "docs_path": docs_path,
            "openapi_json_path": openapi_json_path,
            "redoc_path": redoc_path,
            "include_internal": include_internal,
            "group_by_module": group_by_module,
            "infer_request_body": infer_request_body,
            "infer_responses": infer_responses,
            "detect_security": detect_security,
            "external_docs_url": external_docs_url,
            "external_docs_description": external_docs_description,
            "swagger_ui_theme": swagger_ui_theme,
            "swagger_ui_config": swagger_ui_config or {},
            **kwargs,
        }

    @staticmethod
    def csrf(
        secret_key: str = "",
        token_length: int = 32,
        header_name: str = "X-CSRF-Token",
        field_name: str = "_csrf_token",
        cookie_name: str = "_csrf_cookie",
        cookie_path: str = "/",
        cookie_domain: Optional[str] = None,
        cookie_secure: bool = True,
        cookie_samesite: str = "Lax",
        cookie_httponly: bool = False,
        cookie_max_age: int = 3600,
        safe_methods: Optional[List[str]] = None,
        exempt_paths: Optional[List[str]] = None,
        exempt_content_types: Optional[List[str]] = None,
        trust_ajax: bool = True,
        rotate_token: bool = False,
        failure_status: int = 403,
        enabled: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure CSRF (Cross-Site Request Forgery) protection integration.

        Produces a config dict consumed by ``CSRFMiddleware`` in
        ``aquilia.middleware_ext.security``.

        Args:
            secret_key: HMAC key for cookie-based token signing.
            token_length: Length of generated CSRF tokens in bytes.
            header_name: HTTP header name for token submission.
            field_name: Form field name for token submission.
            cookie_name: Cookie name for double-submit fallback.
            cookie_path: Cookie path attribute.
            cookie_domain: Cookie domain attribute (None = current domain).
            cookie_secure: Set Secure flag on cookie.
            cookie_samesite: SameSite attribute (Strict, Lax, None).
            cookie_httponly: Set HttpOnly flag on cookie.
            cookie_max_age: Cookie max-age in seconds.
            safe_methods: HTTP methods that skip CSRF validation.
            exempt_paths: URL paths exempt from CSRF checks.
            exempt_content_types: Content types exempt from CSRF checks.
            trust_ajax: Trust X-Requested-With header for AJAX requests.
            rotate_token: Generate new token after each successful validation.
            failure_status: HTTP status code returned on CSRF failure.
            enabled: Enable/disable CSRF protection.
            **kwargs: Extra config passed through.

        Returns:
            Config dict with ``_integration_type: "csrf"``.

        Example::

            app = Aquilia(
                integrations=[Integration.csrf(
                    secret_key="my-secret-key",
                    exempt_paths=["/api/webhooks", "/health"],
                    cookie_secure=True,
                    cookie_samesite="Strict",
                )]
            )
        """
        return {
            "_integration_type": "csrf",
            "enabled": enabled,
            "secret_key": secret_key,
            "token_length": token_length,
            "header_name": header_name,
            "field_name": field_name,
            "cookie_name": cookie_name,
            "cookie_path": cookie_path,
            "cookie_domain": cookie_domain,
            "cookie_secure": cookie_secure,
            "cookie_samesite": cookie_samesite,
            "cookie_httponly": cookie_httponly,
            "cookie_max_age": cookie_max_age,
            "safe_methods": safe_methods or ["GET", "HEAD", "OPTIONS", "TRACE"],
            "exempt_paths": exempt_paths or [],
            "exempt_content_types": exempt_content_types or [],
            "trust_ajax": trust_ajax,
            "rotate_token": rotate_token,
            "failure_status": failure_status,
            **kwargs,
        }

    @staticmethod
    def logging(
        format: str = "%(method)s %(path)s %(status)s %(duration_ms).1fms",
        level: str = "INFO",
        slow_threshold_ms: float = 1000.0,
        skip_paths: Optional[List[str]] = None,
        include_headers: bool = False,
        include_query: bool = True,
        include_user_agent: bool = False,
        log_request_body: bool = False,
        log_response_body: bool = False,
        colorize: bool = True,
        enabled: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure request/response logging integration.

        Produces a config dict consumed by ``LoggingMiddleware`` in
        ``aquilia.middleware_ext.logging``.

        Args:
            format: Log message format string.
            level: Default log level for normal requests.
            slow_threshold_ms: Threshold (ms) above which requests are flagged slow.
            skip_paths: URL paths to skip logging for (e.g. health checks).
            include_headers: Include request headers in log output.
            include_query: Include query string in log output.
            include_user_agent: Include User-Agent header in log output.
            log_request_body: Log request body (use with caution).
            log_response_body: Log response body (use with caution).
            colorize: Colorize log output (for development).
            enabled: Enable/disable request logging.
            **kwargs: Extra config passed through.

        Returns:
            Config dict with ``_integration_type: "logging"``.

        Example::

            app = Aquilia(
                integrations=[Integration.logging(
                    slow_threshold_ms=500,
                    skip_paths=["/health", "/metrics"],
                    include_headers=True,
                )]
            )
        """
        return {
            "_integration_type": "logging",
            "enabled": enabled,
            "format": format,
            "level": level,
            "slow_threshold_ms": slow_threshold_ms,
            "skip_paths": skip_paths or ["/health", "/healthz", "/ready", "/metrics"],
            "include_headers": include_headers,
            "include_query": include_query,
            "include_user_agent": include_user_agent,
            "log_request_body": log_request_body,
            "log_response_body": log_response_body,
            "colorize": colorize,
            **kwargs,
        }

    @staticmethod
    def mail(
        default_from: str = "noreply@localhost",
        default_reply_to: Optional[str] = None,
        subject_prefix: str = "",
        providers: Optional[List[Dict[str, Any]]] = None,
        console_backend: bool = False,
        preview_mode: bool = False,
        template_dirs: Optional[List[str]] = None,
        retry_max_attempts: int = 5,
        retry_base_delay: float = 1.0,
        rate_limit_global: int = 1000,
        rate_limit_per_domain: int = 100,
        dkim_enabled: bool = False,
        dkim_domain: Optional[str] = None,
        dkim_selector: str = "aquilia",
        require_tls: bool = True,
        pii_redaction: bool = False,
        metrics_enabled: bool = True,
        tracing_enabled: bool = False,
        enabled: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure AquilaMail — the production-ready async mail subsystem.

        Args:
            default_from: Default sender address.
            default_reply_to: Default reply-to address.
            subject_prefix: Prefix prepended to all subjects.
            providers: List of provider config dicts.
            console_backend: Print mail to console instead of sending.
            preview_mode: Render-only, no delivery.
            template_dirs: ATS template search paths.
            retry_max_attempts: Max retry attempts for transient failures.
            retry_base_delay: Base delay (seconds) for exponential backoff.
            rate_limit_global: Global rate limit (messages/minute).
            rate_limit_per_domain: Per-domain rate limit (messages/minute).
            dkim_enabled: Enable DKIM signing.
            dkim_domain: DKIM signing domain.
            dkim_selector: DKIM selector.
            require_tls: Require TLS for SMTP connections.
            pii_redaction: Redact PII in logs.
            metrics_enabled: Enable mail metrics.
            tracing_enabled: Enable distributed tracing.
            enabled: Enable/disable the mail subsystem.
            **kwargs: Additional mail configuration.

        Returns:
            Mail configuration dictionary.

        Example::

            .integrate(Integration.mail(
                default_from="noreply@myapp.com",
                console_backend=True,  # dev mode
                providers=[
                    {"name": "smtp", "type": "smtp", "host": "smtp.example.com", "port": 587},
                ],
            ))
        """
        return {
            "_integration_type": "mail",
            "enabled": enabled,
            "default_from": default_from,
            "default_reply_to": default_reply_to,
            "subject_prefix": subject_prefix,
            "providers": providers or [],
            "console_backend": console_backend,
            "preview_mode": preview_mode,
            "templates": {
                "template_dirs": template_dirs or ["mail_templates"],
            },
            "retry": {
                "max_attempts": retry_max_attempts,
                "base_delay": retry_base_delay,
            },
            "rate_limit": {
                "global_per_minute": rate_limit_global,
                "per_domain_per_minute": rate_limit_per_domain,
            },
            "security": {
                "dkim_enabled": dkim_enabled,
                "dkim_domain": dkim_domain,
                "dkim_selector": dkim_selector,
                "require_tls": require_tls,
                "pii_redaction_enabled": pii_redaction,
            },
            "metrics_enabled": metrics_enabled,
            "tracing_enabled": tracing_enabled,
            **kwargs,
        }

    @staticmethod
    def mlops(
        *,
        enabled: bool = True,
        registry_db: str = "registry.db",
        blob_root: str = ".aquilia-store",
        storage_backend: str = "filesystem",
        drift_method: str = "psi",
        drift_threshold: float = 0.2,
        drift_num_bins: int = 10,
        max_batch_size: int = 16,
        max_latency_ms: float = 50.0,
        batching_strategy: str = "hybrid",
        sample_rate: float = 0.01,
        log_dir: str = "prediction_logs",
        hmac_secret: Optional[str] = None,
        signing_private_key: Optional[str] = None,
        signing_public_key: Optional[str] = None,
        encryption_key: Optional[Any] = None,
        plugin_auto_discover: bool = True,
        scaling_policy: Optional[Dict[str, Any]] = None,
        rollout_default_strategy: str = "canary",
        auto_rollback: bool = True,
        metrics_model_name: str = "",
        metrics_model_version: str = "",
        # Ecosystem integration
        cache_enabled: bool = True,
        cache_ttl: int = 60,
        cache_namespace: str = "mlops",
        artifact_store_dir: str = "artifacts",
        fault_engine_debug: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure MLOps platform integration.

        Wires model packaging, registry, serving, observability, release
        management, scheduling, security, and plugins into the Aquilia
        framework via DI, lifecycle hooks, and middleware.

        Ecosystem wiring:
        - **CacheService** — MLOps controller caches model metadata,
          registry listings, and capability introspections.
        - **FaultEngine** — All MLOps exceptions flow through the engine
          with scoped handlers for observability and recovery.
        - **ArtifactStore** — Model packs are managed via the Aquilia
          artifact system with content-addressed storage and integrity
          verification.
        - **Effects** — Controller methods declare ``CacheEffect`` to
          participate in the effect middleware pipeline.

        Args:
            enabled: Enable/disable MLOps integration.
            registry_db: Path to the registry SQLite database.
            blob_root: Root directory for blob storage.
            storage_backend: ``"filesystem"`` or ``"s3"``.
            drift_method: ``"psi"``, ``"ks_test"``, or ``"distribution"``.
            drift_threshold: Drift score threshold for alerts.
            drift_num_bins: Number of histogram bins for PSI.
            max_batch_size: Dynamic batcher max batch size.
            max_latency_ms: Dynamic batcher max wait time (ms).
            batching_strategy: ``"size"``, ``"time"``, or ``"hybrid"``.
            sample_rate: Prediction logging sampling rate (0.0–1.0).
            log_dir: Directory for prediction log files.
            hmac_secret: HMAC secret for artifact signing.
            signing_private_key: Path to RSA private key for signing.
            signing_public_key: Path to RSA public key for verification.
            encryption_key: Fernet key for blob encryption at rest.
            plugin_auto_discover: Scan entry points for plugins.
            scaling_policy: Autoscaler policy dict.
            rollout_default_strategy: Default rollout strategy.
            auto_rollback: Enable automatic rollback on metric degradation.
            metrics_model_name: Default model name for metrics labels.
            metrics_model_version: Default model version for metrics labels.
            cache_enabled: Enable CacheService for MLOps caching.
            cache_ttl: Default cache TTL in seconds.
            cache_namespace: Cache namespace prefix.
            artifact_store_dir: Directory for artifact storage.
            fault_engine_debug: Enable FaultEngine debug mode.
            **kwargs: Additional MLOps configuration.

        Returns:
            MLOps configuration dictionary.

        Example::

            .integrate(Integration.mlops(
                registry_db="registry.db",
                drift_method="psi",
                drift_threshold=0.25,
                max_batch_size=32,
                plugin_auto_discover=True,
                cache_enabled=True,
                cache_ttl=120,
            ))
        """
        return {
            "_integration_type": "mlops",
            "enabled": enabled,
            "registry": {
                "db_path": registry_db,
                "blob_root": blob_root,
                "storage_backend": storage_backend,
            },
            "serving": {
                "max_batch_size": max_batch_size,
                "max_latency_ms": max_latency_ms,
                "batching_strategy": batching_strategy,
            },
            "observe": {
                "drift_method": drift_method,
                "drift_threshold": drift_threshold,
                "drift_num_bins": drift_num_bins,
                "sample_rate": sample_rate,
                "log_dir": log_dir,
                "metrics_model_name": metrics_model_name,
                "metrics_model_version": metrics_model_version,
            },
            "release": {
                "rollout_default_strategy": rollout_default_strategy,
                "auto_rollback": auto_rollback,
            },
            "security": {
                "hmac_secret": hmac_secret,
                "signing_private_key": signing_private_key,
                "signing_public_key": signing_public_key,
                "encryption_key": encryption_key,
            },
            "plugins": {
                "auto_discover": plugin_auto_discover,
            },
            "scaling_policy": scaling_policy,
            "ecosystem": {
                "cache_enabled": cache_enabled,
                "cache_ttl": cache_ttl,
                "cache_namespace": cache_namespace,
                "artifact_store_dir": artifact_store_dir,
                "fault_engine_debug": fault_engine_debug,
            },
            **kwargs,
        }

    @staticmethod
    def serializers(
        *,
        auto_discover: bool = True,
        strict_validation: bool = True,
        raise_on_error: bool = False,
        date_format: str = "iso-8601",
        datetime_format: str = "iso-8601",
        coerce_decimal_to_string: bool = True,
        compact_json: bool = True,
        enabled: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Configure global serializer settings.

        Args:
            auto_discover: Auto-discover serializers in modules.
            strict_validation: Reject unknown fields in input.
            raise_on_error: Raise ``ValidationFault`` instead of
                            returning errors dict.
            date_format: Default output format for DateField.
            datetime_format: Default output format for DateTimeField.
            coerce_decimal_to_string: Render Decimal as string (default).
            compact_json: Use compact JSON output (no indent).
            enabled: Enable/disable the serializer integration.
            **kwargs: Additional serializer configuration.

        Returns:
            Serializer integration configuration dictionary.

        Example::

            .integrate(Integration.serializers(
                strict_validation=True,
                raise_on_error=True,
                coerce_decimal_to_string=False,
            ))
        """
        return {
            "_integration_type": "serializers",
            "enabled": enabled,
            "auto_discover": auto_discover,
            "strict_validation": strict_validation,
            "raise_on_error": raise_on_error,
            "date_format": date_format,
            "datetime_format": datetime_format,
            "coerce_decimal_to_string": coerce_decimal_to_string,
            "compact_json": compact_json,
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
        self._mail_config: Optional[Dict[str, Any]] = None
        self._mlops_config: Optional[Dict[str, Any]] = None
        self._cache_config: Optional[Dict[str, Any]] = None
    
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
            elif integration_type == "openapi":
                self._integrations["openapi"] = integration
            elif integration_type == "mail":
                self._integrations["mail"] = integration
                self._mail_config = integration
            elif integration_type == "mlops":
                self._integrations["mlops"] = integration
                self._mlops_config = integration
            elif integration_type == "cache":
                self._integrations["cache"] = integration
                self._cache_config = integration
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
    
    def mlops(
        self,
        enabled: bool = True,
        registry_db: str = "registry.db",
        blob_root: str = ".aquilia-store",
        drift_method: str = "psi",
        drift_threshold: float = 0.2,
        max_batch_size: int = 16,
        max_latency_ms: float = 50.0,
        plugin_auto_discover: bool = True,
        **kwargs,
    ) -> "Workspace":
        """
        Configure MLOps platform for this workspace.

        Shorthand for ``.integrate(Integration.mlops(...))``.

        Args:
            enabled: Enable MLOps subsystem.
            registry_db: Path to registry database.
            blob_root: Root directory for blob storage.
            drift_method: Drift detection method.
            drift_threshold: Drift alert threshold.
            max_batch_size: Dynamic batcher max batch size.
            max_latency_ms: Dynamic batcher max wait (ms).
            plugin_auto_discover: Auto-discover plugins.
            **kwargs: Additional MLOps configuration.

        Example::

            workspace = (
                Workspace("ml-app")
                .mlops(
                    registry_db="models.db",
                    drift_method="psi",
                    max_batch_size=32,
                )
            )
        """
        config = Integration.mlops(
            enabled=enabled,
            registry_db=registry_db,
            blob_root=blob_root,
            drift_method=drift_method,
            drift_threshold=drift_threshold,
            max_batch_size=max_batch_size,
            max_latency_ms=max_latency_ms,
            plugin_auto_discover=plugin_auto_discover,
            **kwargs,
        )
        self._mlops_config = config
        self._integrations["mlops"] = config
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
        if self._mail_config:
            config["mail"] = self._mail_config
            config["integrations"]["mail"] = self._mail_config
        if self._mlops_config:
            config["mlops"] = self._mlops_config
            config["integrations"]["mlops"] = self._mlops_config
        if self._cache_config:
            config["cache"] = self._cache_config
            config["integrations"]["cache"] = self._cache_config
        
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
