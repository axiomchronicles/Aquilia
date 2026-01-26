"""
AquiliaServer - Main server orchestrating all components with lifecycle management.

Fully integrated with Aquilary manifest-driven registry system.
"""

from typing import Optional, List, Any
import logging

from .config import ConfigLoader
from .engine import RequestCtx
from .middleware import MiddlewareStack, RequestIdMiddleware, ExceptionMiddleware, LoggingMiddleware
from .asgi import ASGIAdapter
from .controller.router import ControllerRouter
from .aquilary import Aquilary, RuntimeRegistry, RegistryMode, AquilaryRegistry
from .lifecycle import LifecycleCoordinator, LifecycleManager, LifecycleError
from .middleware_ext.session_middleware import SessionMiddleware
from .controller.openapi import OpenAPIGenerator
from .response import Response
# Auth Integration
from .auth.manager import AuthManager
from .auth.integration.middleware import AquilAuthMiddleware, create_auth_middleware_stack
from .auth.tokens import TokenConfig


class AquiliaServer:
    """
    Main Aquilia server that orchestrates all components with lifecycle management.
    
    Integrates:
    - Aquilary registry for app discovery and validation
    - RuntimeRegistry for DI and route compilation
    - LifecycleCoordinator for startup/shutdown hooks
    - Controller-based routing with ControllerRouter
    - ASGI adapter for HTTP handling
    
    Architecture:
        Manifests → Aquilary → RuntimeRegistry → Controllers → ASGI
    """
    
    def __init__(
        self,
        manifests: Optional[List[Any]] = None,
        config: Optional[ConfigLoader] = None,
        mode: RegistryMode = RegistryMode.PROD,
        aquilary_registry: Optional[AquilaryRegistry] = None,
    ):
        """
        Initialize AquiliaServer with Aquilary registry.
        
        Args:
            manifests: List of manifest classes for app discovery
            config: Configuration loader
            mode: Registry mode (DEV, PROD, TEST)
            aquilary_registry: Pre-built AquilaryRegistry (advanced usage)
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger("aquilia.server")
        self.logger.info("🔍 Initializing AquiliaServer...")
        self.logger.info(f"📦 Config has sessions: {'sessions' in self.config.to_dict()}")
        self.mode = mode
        
        # Build or use provided Aquilary registry
        if aquilary_registry is not None:
            self.aquilary = aquilary_registry
        else:
            if manifests is None:
                raise ValueError("Must provide either manifests or aquilary_registry")
            
            # Build Aquilary registry from manifests
            self.aquilary = Aquilary.from_manifests(
                manifests=manifests,
                config=self.config,
                mode=mode,
            )
        
        # Create runtime registry (lazy compilation phase)
        self.runtime = RuntimeRegistry.from_metadata(self.aquilary, self.config)
        
        # CRITICAL: Register services immediately so DI containers are populated
        # before controller factory is created
        self.runtime._register_services()
        
        # Create lifecycle coordinator for app startup/shutdown hooks
        self.coordinator = LifecycleCoordinator(self.runtime, self.config)
        
        # Initialize controller router and middleware
        self.controller_router = ControllerRouter()
        self.middleware_stack = MiddlewareStack()
        
        # Setup middleware
        self._setup_middleware()
        
        # Get base DI container for controller factory
        base_container = self._get_base_container()
        
        # Create controller components
        from .controller.factory import ControllerFactory
        from .controller.engine import ControllerEngine
        from .controller.compiler import ControllerCompiler
        
        self.controller_factory = ControllerFactory(app_container=base_container)
        self.controller_engine = ControllerEngine(self.controller_factory)
        self.controller_compiler = ControllerCompiler()
        
        # Track startup state
        self._startup_complete = False
        self._startup_lock = None  # Will be created in async context
        
        # Create ASGI app with server reference for lifecycle management
        self.app = ASGIAdapter(
            controller_router=self.controller_router,
            controller_engine=self.controller_engine,
            middleware_stack=self.middleware_stack,
            server=self,  # Pass server for lifecycle callbacks
        )
    
    def _get_base_container(self):
        """Get base DI container from runtime registry."""
        # Use first app's container as base, or create empty one
        if self.runtime.di_containers:
            return next(iter(self.runtime.di_containers.values()))
        
        # Fallback: create empty container
        from .di import Container
        return Container(scope="app")
    
    def _setup_middleware(self):
        """Setup default middleware stack with Aquilary integration."""
        # Add default middleware in order
        self.middleware_stack.add(
            ExceptionMiddleware(debug=self._is_debug()),
            scope="global",
            priority=1,
            name="exception",
        )
        
        # Add request scope middleware with RuntimeRegistry
        from .middleware_ext.request_scope import SimplifiedRequestScopeMiddleware
        
        async def request_scope_mw(request, ctx, next_handler):
            """Request scope middleware with RuntimeRegistry DI containers."""
            # Get app-scoped container from runtime
            app_name = request.state.get("app_name", "default")
            app_container = self.runtime.di_containers.get(app_name)
            
            if app_container:
                # Create request-scoped container
                request_container = app_container.create_request_scope()
                request.state["di_container"] = request_container
                request.state["app_container"] = app_container
                
                # Update ctx container to use request scope
                ctx.container = request_container
                
                try:
                    return await next_handler(request, ctx)
                finally:
                    # Cleanup request scope
                    await request_container.shutdown()
            else:
                return await next_handler(request, ctx)
        
        self.middleware_stack.add(
            request_scope_mw,
            scope="global",
            priority=5,
            name="request_scope",
        )
        
        self.middleware_stack.add(
            RequestIdMiddleware(),
            scope="global",
            priority=10,
            name="request_id",
        )
        
        self.middleware_stack.add(
            LoggingMiddleware(),
            scope="global",
            priority=20,
            name="logging",
        )
        
        # Add session/auth middleware if enabled
        session_config = self.config.get_session_config()
        auth_config = self.config.get_auth_config()
        
        self.logger.debug(f"Session config: {session_config}")
        self.logger.debug(f"Auth config: {auth_config}")
        
        # Initialize SessionEngine if either Sessions or Auth is enabled
        # Auth REQUIRES sessions
        use_sessions = session_config.get("enabled", False)
        use_auth = auth_config.get("enabled", False)
        
        if use_auth:
            # Force enable sessions config if auth is enabled
            use_sessions = True
            
        self._session_engine = None
        self._auth_manager = None
        
        if use_sessions:
            self.logger.info("🔄 Initializing session management...")
            try:
                # Create session engine
                session_engine = self._create_session_engine(session_config)
                self._session_engine = session_engine
                
                # Check for Auth
                if use_auth:
                    self.logger.info("🔐 Initializing authentication system...")
                    
                    # Create AuthManager
                    auth_manager = self._create_auth_manager(auth_config)
                    self._auth_manager = auth_manager
                    
                    # Add Unified Auth Middleware (handles both sessions and auth)
                    self.middleware_stack.add(
                        AquilAuthMiddleware(
                            session_engine=session_engine,
                            auth_manager=auth_manager,
                            require_auth=auth_config.get("security", {}).get("require_auth_by_default", False),
                            fault_engine=None, # TODO: integrate fault engine from server
                        ),
                        scope="global",
                        priority=15, # Replaces session middleware
                        name="auth",
                    )
                    
                    from .di.providers import ValueProvider
                    for container in self.runtime.di_containers.values():
                        # Core manager
                        container.register(
                            ValueProvider(
                                token=AuthManager,
                                value=auth_manager,
                                scope="app",
                                name="auth_manager_instance"
                            )
                        )
                        # Register sub-components so Services can use them
                        # We use string tokens to ensure consistent resolution with type hints
                        container.register(ValueProvider(value=auth_manager.identity_store, token="aquilia.auth.stores.MemoryIdentityStore", scope="app"))
                        container.register(ValueProvider(value=auth_manager.credential_store, token="aquilia.auth.stores.MemoryCredentialStore", scope="app"))
                        container.register(ValueProvider(value=auth_manager.token_manager, token="aquilia.auth.tokens.TokenManager", scope="app"))
                        container.register(ValueProvider(value=auth_manager.password_hasher, token="aquilia.auth.hashing.PasswordHasher", scope="app"))
                        
                    self.logger.info("✅ Auth system components registered in DI")
                    
                else:
                    # Sessions only
                    self.middleware_stack.add(
                        SessionMiddleware(session_engine),
                        scope="global",
                        priority=15,
                        name="session",
                    )
                    self.logger.info("✅ Session management enabled (Auth disabled)")
                
                # Register SessionEngine in DI (common for both)
                from aquilia.di.providers import ValueProvider
                from aquilia.sessions import SessionEngine
                
                engine_provider = ValueProvider(
                    token=SessionEngine,
                    value=session_engine,
                    scope="app",
                    name="session_engine_instance"
                )
                
                for container in self.runtime.di_containers.values():
                    container.register(engine_provider)
                
            except Exception as e:
                self.logger.error(f"Failed to initialize session/auth system: {e}", exc_info=True)
                self._session_engine = None
                self._auth_manager = None
        else:
            self.logger.info("Session/Auth management disabled")
            
        # Register app-specific middlewares from Aquilary manifest
        if hasattr(self, "aquilary"):
            for ctx in self.aquilary.app_contexts:
                for mw_config in ctx.middlewares:
                    try:
                        self._register_app_middleware(mw_config)
                    except Exception as e:
                        self.logger.error(f"Failed to register middleware from app {ctx.name}: {e}")

    def _register_app_middleware(self, mw_config: Any):
        """Register application middleware from config."""
        import importlib
        
        # Extract config details
        # Handle both dict and object (MiddlewareConfig)
        if isinstance(mw_config, dict):
            class_path = mw_config.get("class_path") or mw_config.get("path")
            scope = mw_config.get("scope", "global")
            priority = mw_config.get("priority", 50)
            config = mw_config.get("config", {})
            name = mw_config.get("name")
        else:
            class_path = getattr(mw_config, "class_path", None)
            scope = getattr(mw_config, "scope", "global")
            priority = getattr(mw_config, "priority", 50)
            config = getattr(mw_config, "config", {})
            name = getattr(mw_config, "name", None)
            
        if not class_path:
            return

        # Import class
        if ":" in class_path:
            module_path, class_name = class_path.split(":", 1)
        else:
            module_path, class_name = class_path.rsplit(".", 1)
            
        module = importlib.import_module(module_path)
        mw_class = getattr(module, class_name)
        
        # Instantiate
        # Some middlewares take config in __init__, others don't.
        # We try to pass kwargs if config exists
        try:
            if config:
                instance = mw_class(**config)
            else:
                instance = mw_class()
        except TypeError:
            # Fallback for no-arg init
            instance = mw_class()
            
        # Register
        self.middleware_stack.add(
            instance,
            scope=scope,
            priority=priority,
            name=name or class_name,
        )
        self.logger.info(f"✓ Registered app middleware: {class_name} (priority={priority})")
    
    def _is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.config.get("debug", False)
    
    def _create_session_engine(self, session_config: dict):
        """
        Create SessionEngine from configuration.
        
        Args:
            session_config: Session configuration dictionary
            
        Returns:
            Configured SessionEngine
        """
        from datetime import timedelta
        from aquilia.sessions import (
            SessionEngine,
            SessionPolicy,
            PersistencePolicy,
            ConcurrencyPolicy,
            TransportPolicy,
            MemoryStore,
            FileStore,
            CookieTransport,
            HeaderTransport,
        )
        
        # Handle different config formats - workspace vs traditional config
        if "policy" in session_config and not isinstance(session_config["policy"], dict):
            # Workspace format - direct policy objects
            policy = session_config["policy"]
            store = session_config.get("store")
            transport_config = session_config.get("transport")
            
            # Create store from config or default
            if store is None:
                store = MemoryStore(max_sessions=10000)
            elif isinstance(store, dict):
                # Store config is a dictionary - create store object
                store_type = store.get("type", "memory")
                if store_type == "memory":
                    store = MemoryStore(max_sessions=store.get("max_sessions", 10000))
                elif store_type == "file":
                    directory = store.get("directory", "/tmp/aquilia_sessions")
                    store = FileStore(directory=directory)
                else:
                    # Default to memory
                    store = MemoryStore(max_sessions=10000)
                
            # Create transport from policy or config
            if transport_config is None:
                transport = CookieTransport(policy.transport)
            elif isinstance(transport_config, dict):
                # Transport config is a dictionary - create transport object
                adapter = transport_config.get("adapter", "cookie")
                if adapter == "cookie":
                    transport = CookieTransport(policy.transport)
                elif adapter == "header":
                    transport = HeaderTransport(policy.transport)
                else:
                    # Default to cookie
                    transport = CookieTransport(policy.transport)
            else:
                # Transport config is already a transport object
                transport = transport_config
                
            return SessionEngine(policy=policy, store=store, transport=transport)
        
        # Traditional config format - build from dictionaries
        policy_config = session_config.get("policy", {})
        policy = SessionPolicy(
            name=policy_config.get("name", "user_default"),
            ttl=timedelta(days=policy_config.get("ttl_days", 7)),
            idle_timeout=timedelta(minutes=policy_config.get("idle_timeout_minutes", 30)),
            rotate_on_use=False,
            rotate_on_privilege_change=policy_config.get("rotate_on_privilege_change", True),
            persistence=PersistencePolicy(
                enabled=True,
                store_name="default",
                write_through=True,
            ),
            concurrency=ConcurrencyPolicy(
                max_sessions_per_principal=policy_config.get("max_sessions_per_principal", 5),
                behavior_on_limit="evict_oldest",
            ),
            transport=TransportPolicy(
                adapter=session_config.get("transport", {}).get("adapter", "cookie"),
                cookie_name=session_config.get("transport", {}).get("cookie_name", "aquilia_session"),
                cookie_httponly=session_config.get("transport", {}).get("cookie_httponly", True),
                cookie_secure=session_config.get("transport", {}).get("cookie_secure", True),
                cookie_samesite=session_config.get("transport", {}).get("cookie_samesite", "lax"),
                header_name=session_config.get("transport", {}).get("header_name", "X-Session-ID"),
            ),
            scope="user",
        )
        
        # Create store
        store_config = session_config.get("store", {})
        store_type = store_config.get("type", "memory")
        
        if store_type == "memory":
            store = MemoryStore(max_sessions=store_config.get("max_sessions", 10000))
        elif store_type == "file":
            directory = store_config.get("directory", "/tmp/aquilia_sessions")
            store = FileStore(directory=directory)
        else:
            # Default to memory
            self.logger.warning(f"Unknown store type '{store_type}', using memory store")
            store = MemoryStore(max_sessions=10000)
        
        # Create transport
        transport_config = session_config.get("transport", {})
        adapter = transport_config.get("adapter", "cookie")
        
        if adapter == "cookie":
            transport = CookieTransport(policy.transport)
        elif adapter == "header":
            transport = HeaderTransport(policy.transport)
        else:
            # Default to cookie
            self.logger.warning(f"Unknown transport adapter '{adapter}', using cookie transport")
            transport = CookieTransport(policy.transport)
        
        # Create engine
        engine = SessionEngine(
            policy=policy,
            store=store,
            transport=transport,
        )
        
        self.logger.info(
            f"SessionEngine initialized: policy={policy.name}, "
            f"store={store_type}, transport={adapter}"
        )
        
        return engine
    
    def _create_auth_manager(self, auth_config: dict) -> AuthManager:
        """
        Create AuthManager from configuration.
        
        Args:
            auth_config: Auth configuration dictionary
            
        Returns:
            Configured AuthManager
        """
        from .auth.stores import MemoryIdentityStore, MemoryTokenStore, MemoryCredentialStore
        from .auth.tokens import TokenManager, TokenConfig, KeyRing, KeyDescriptor
        from datetime import timedelta
        
        # 1. Identity Store
        store_config = auth_config.get("store", {})
        store_type = store_config.get("type", "memory")
        
        if store_type == "memory":
            identity_store = MemoryIdentityStore()
            credential_store = MemoryCredentialStore()
            # TODO: Load initial users if configured?
        else:
            self.logger.warning(f"Unknown auth store type '{store_type}', using memory store")
            identity_store = MemoryIdentityStore()
            credential_store = MemoryCredentialStore()
            
        # 2. Token Manager
        token_config = auth_config.get("tokens", {})
        secret = token_config.get("secret_key", "dev_secret")
        
        if secret == "aquilia_insecure_dev_secret" and self.mode != RegistryMode.DEV:
            self.logger.warning("⚠️  USING INSECURE DEFAULT SECRET KEY IN NON-DEV MODE")
            
        # Generate KeyRing (simple for now, just one RS256 key)
        # In prod, this should load from file/KMS
        key = KeyDescriptor.generate(kid="active", algorithm="RS256")
        key_ring = KeyRing([key])
        
        token_store = MemoryTokenStore()
        
        token_manager = TokenManager(
            key_ring=key_ring,
            token_store=token_store,
            config=TokenConfig(
                # secret_key no longer needed for JWT with RS256, but maybe for HS256 if supported
                issuer=token_config.get("issuer", "aquilia"),
                audience=[token_config.get("audience", "aquilia-app")], # Audience is list in new config
                access_token_ttl=token_config.get("access_token_ttl_minutes", 60) * 60,
                refresh_token_ttl=token_config.get("refresh_token_ttl_days", 30) * 86400,
            )
        )
        
        return AuthManager(
            identity_store=identity_store,
            credential_store=credential_store,
            token_manager=token_manager,
            password_hasher=None, # Uses default (Argon2 via Passlib)
        )
    
    def _load_controllers(self):
        """Load and compile controllers from all apps."""
        if not self.controller_compiler:
            return
        
        # Keep track of all compiled controllers for validation
        compiled_controllers = []

        for app_ctx in self.runtime.meta.app_contexts:
            # Import and compile controllers
            for controller_path in app_ctx.controllers:
                try:
                    controller_class = self._import_controller_class(controller_path)
                    
                    # Get route prefix from manifest if available
                    route_prefix = getattr(app_ctx.manifest, "route_prefix", None)
                    
                    # VERSIONING: If version support is enabled, prepend version?
                    # This is better done if route_prefix was smart, but let's check config
                    # Currently basic implementation: just use route_prefix
                    
                    # Compile controller
                    compiled = self.controller_compiler.compile_controller(
                        controller_class,
                        base_prefix=route_prefix,
                    )
                    
                    # Inject app context info for DI resolution
                    for route in compiled.routes:
                        route.app_name = app_ctx.name
                    
                    # Register with controller router
                    self.controller_router.add_controller(compiled)
                    compiled_controllers.append(compiled)
                    
                    self.logger.info(
                        f"Loaded controller {controller_class.__name__} "
                        f"from {app_ctx.name} with {len(compiled.routes)} routes "
                        f"(mount: {route_prefix or '/'})"
                    )
                
                except Exception as e:
                    self.logger.error(
                        f"Error loading controller {controller_path} from {app_ctx.name}: {e}",
                        exc_info=True
                    )
        
        # VALIDATION: Check for conflicts in the fully assembled tree
        conflicts = self.controller_compiler.validate_route_tree(compiled_controllers)
        if conflicts:
            self.logger.critical("❌ ROUTE CONFLICTS DETECTED:")
            for c in conflicts:
                self.logger.critical(
                    f"  {c['method']} {c['route1']['path']}: "
                    f"{c['route1']['controller']} vs {c['route2']['controller']}"
                )
            raise RuntimeError(f"Found {len(conflicts)} route conflicts. check logs.")

        # Initialize controller router
        self.controller_router.initialize()

        # Step 2: Register OpenAPI/Docs routes if enabled
        if self.config.get("docs_enabled", True):
            self._register_docs_routes()
    
    def _register_docs_routes(self):
        """Register OpenAPI and Swagger UI routes."""
        generator = OpenAPIGenerator(
            title=self.config.get("api_title", "Aquilia API"),
            version=self.config.get("api_version", "1.0.0")
        )
        
        async def openapi_handler(request, ctx):
            spec = generator.generate(self.controller_router)
            return Response.json(spec)
            
        async def docs_handler(request, ctx):
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
                <title>Aquilia API Docs</title>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
                <script>
                    window.onload = () => {
                        window.ui = SwaggerUIBundle({
                            url: '/openapi.json',
                            dom_id: '#swagger-ui',
                        });
                    };
                </script>
            </body>
            </html>
            """
            return Response.html(html)
            
        # We need a way to manually add routes to the router that bypass controller compilation
        # For now, let's just add them to the routes_by_method directly
        # or use a pseudo-controller. 
        # A better way is to move this to the compiler or have a 'manual_route' helper.
        
        from .controller.metadata import RouteMetadata
        from .controller.compiler import CompiledRoute
        from .patterns import parse_pattern, PatternCompiler
        
        pc = PatternCompiler()
        
        # OpenAPI JSON
        route_json = CompiledRoute(
            controller_class=self.__class__,
            controller_metadata=None,
            route_metadata=RouteMetadata(
                http_method="GET",
                path_template="/openapi.json",
                full_path="/openapi.json",
                handler_name="openapi_handler"
            ),
            compiled_pattern=pc.compile(parse_pattern("/openapi.json")),
            full_path="/openapi.json",
            http_method="GET",
            specificity=1000
        )
        route_json.handler = openapi_handler # Monkeypatch for engine
        
        # Swagger UI
        route_docs = CompiledRoute(
            controller_class=self.__class__,
            controller_metadata=None,
            route_metadata=RouteMetadata(
                http_method="GET",
                path_template="/docs",
                full_path="/docs",
                handler_name="docs_handler"
            ),
            compiled_pattern=pc.compile(parse_pattern("/docs")),
            full_path="/docs",
            http_method="GET",
            specificity=1000
        )
        route_docs.handler = docs_handler
        
        self.controller_router.routes_by_method.setdefault("GET", []).append(route_json)
        self.controller_router.routes_by_method.setdefault("GET", []).append(route_docs)
        self.logger.info("📡 Registered documentation routes at /docs and /openapi.json")

    
    def _import_controller_class(self, controller_path: str) -> type:
        """
        Import controller class from path.
        
        Args:
            controller_path: Import path in format "module.path:ClassName"
            
        Returns:
            Controller class
            
        Raises:
            ImportError: If module or class cannot be imported
            TypeError: If imported object is not a class
        """
        import importlib
        
        if ":" not in controller_path:
            raise ValueError(
                f"Invalid controller path '{controller_path}': "
                f"Expected format 'module.path:ClassName'"
            )
        
        try:
            module_path, class_name = controller_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            controller_class = getattr(module, class_name)
            
            if not isinstance(controller_class, type):
                raise TypeError(
                    f"{controller_path} resolved to {type(controller_class).__name__}, "
                    f"expected a class"
                )
            
            return controller_class
            
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{module_path}' for controller {controller_path}: {e}"
            ) from e
        except AttributeError as e:
            raise ImportError(
                f"Class '{class_name}' not found in module '{module_path}': {e}"
            ) from e
    
    async def startup(self):
        """
        Execute startup sequence with Aquilary lifecycle management.
        
        Flow:
        1. Load and compile controllers from manifests
        2. Compile routes (includes service/effect registration)
        3. Start lifecycle coordinator (runs app startup hooks in dependency order)
        4. Log registered routes and apps
        5. Server ready
        
        This method is idempotent and thread-safe.
        """
        # Prevent duplicate startup
        if self._startup_complete:
            return
        
        # Initialize lock in async context if needed
        if self._startup_lock is None:
            import asyncio
            self._startup_lock = asyncio.Lock()
        
        async with self._startup_lock:
            # Double-check after acquiring lock
            if self._startup_complete:
                return
            
            self.logger.info("Starting Aquilia server with Aquilary registry...")
            
            # Log registry information
            self.logger.info(f"Registry fingerprint: {self.aquilary.fingerprint}")
            self.logger.info(f"Mode: {self.mode.value}")
            self.logger.info(f"Apps loaded: {len(self.runtime.meta.app_contexts)}")
            
            # Step 0: Perform runtime auto-discovery
            self.logger.info("Performing runtime auto-discovery...")
            self.runtime.perform_autodiscovery()
            
            # Step 1: Load and compile controllers
            self.logger.info("Loading controllers from manifests...")
            self._load_controllers()
        
        # Step 2: Compile routes (includes service registration and handler wrapping)
        self.logger.info("Compiling routes with DI integration...")
        self.runtime.compile_routes()
        
        # Step 3: Start lifecycle (runs app startup hooks in dependency order)
        self.logger.info("Starting app lifecycle hooks...")
        try:
            await self.coordinator.startup()
        except Exception as e:
            from .lifecycle import LifecycleError
            self.logger.error(f"Lifecycle startup failed: {e}")
            raise LifecycleError(f"Startup failed: {e}") from e
        
        # Step 4: Log registered routes
        routes = self.controller_router.get_routes()
        if routes:
            self.logger.info(f"Registered {len(routes)} controller routes:")
            for route in routes[:10]:  # Show first 10
                self.logger.info(
                    f"  {route.get('method', 'GET'):7} "
                    f"{route.get('path', '/'):30} "
                    f"-> {route.get('handler', 'unknown')}"
                )
            if len(routes) > 10:
                self.logger.info(f"  ... and {len(routes) - 10} more")
        
        # Log DI container information
        total_services = sum(
            len(container._providers)
            for container in self.runtime.di_containers.values()
        )
        self.logger.info(f"DI containers: {len(self.runtime.di_containers)} apps, {total_services} services")
        
        # Mark startup complete
        self._startup_complete = True
        self.logger.info(f"✅ Server ready with {len(self.runtime.meta.app_contexts)} apps")
    
    async def shutdown(self):
        """
        Execute shutdown sequence with Aquilary lifecycle management.
        
        Flow:
        1. Stop lifecycle coordinator (runs app shutdown hooks in reverse order)
        2. Cleanup DI containers
        3. Finalize effects
        
        This method is idempotent and safe to call multiple times.
        """
        if not self._startup_complete:
            return  # Nothing to shut down
        
        self.logger.info("Shutting down Aquilia server...")
        
        # Run lifecycle shutdown hooks
        await self.coordinator.shutdown()
        
        # Cleanup DI containers
        for app_name, container in self.runtime.di_containers.items():
            try:
                await container.shutdown()
                self.logger.debug(f"Cleaned up DI container for app '{app_name}'")
            except Exception as e:
                self.logger.warning(f"Error cleaning up container for '{app_name}': {e}")
        
        # Reset startup state
        self._startup_complete = False
        self.logger.info("✅ All apps stopped")
    
    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
        log_level: str = "info",
    ):
        """
        Run the development server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload
            log_level: Logging level
        """
        import asyncio
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
        
        # Run startup
        asyncio.run(self.startup())
        
        try:
            # Try to import uvicorn
            import uvicorn
            
            self.logger.info(f"Starting uvicorn server on {host}:{port}")
            
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                reload=reload,
                log_level=log_level,
            )
        
        except ImportError:
            self.logger.error(
                "uvicorn is not installed. "
                "Install it with: pip install uvicorn"
            )
            raise
        
        finally:
            # Run shutdown
            asyncio.run(self.shutdown())
    
    def get_asgi_app(self):
        """Get the ASGI application for external servers."""
        return self.app
