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
from .faults.engine import FaultEngine, FaultMiddleware
from .response import Response
# Template Integration
from .templates.middleware import TemplateMiddleware
from .templates.di_providers import register_template_providers
# Auth Integration
from .auth.manager import AuthManager
from .auth.integration.middleware import AquilAuthMiddleware, create_auth_middleware_stack
from .auth.tokens import TokenConfig
# WebSockets
from .sockets.runtime import AquilaSockets, SocketRouter
from .sockets.adapters import InMemoryAdapter


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
        
        # Initialize fault engine
        self.fault_engine = FaultEngine(debug=self._is_debug())
        
        # Apply fault integration patches to subsystems (registry, DI)
        try:
            from .faults.integrations import patch_all_subsystems
            patch_all_subsystems()
        except Exception as e:
            self.logger.warning(f"Fault integration patches failed (non-fatal): {e}")
        
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
        
        # Register EffectRegistry and FaultEngine in DI containers
        from .di.providers import ValueProvider
        from .effects import EffectRegistry
        for container in self.runtime.di_containers.values():
            container.register(ValueProvider(
                value=self.fault_engine,
                token=FaultEngine,
                scope="app",
            ))
            container.register(ValueProvider(
                value=EffectRegistry(),
                token=EffectRegistry,
                scope="app",
            ))
        
        # Create lifecycle coordinator for app startup/shutdown hooks
        self.coordinator = LifecycleCoordinator(self.runtime, self.config)
        
        # Connect lifecycle events to fault observability
        def _lifecycle_fault_observer(event):
            if event.error:
                self.logger.error(
                    f"Lifecycle fault in phase {event.phase.value}: "
                    f"app={event.app_name}, error={event.error}"
                )
        self.coordinator.on_event(_lifecycle_fault_observer)
        
        # Initialize controller router and middleware
        self.controller_router = ControllerRouter()
        self.middleware_stack = MiddlewareStack()
        
        # Setup middleware (also initializes aquila_sockets)
        self._setup_middleware()
        
        # Get base DI container for controller factory
        base_container = self._get_base_container()
        
        # Create controller components
        from .controller.factory import ControllerFactory
        from .controller.engine import ControllerEngine
        from .controller.compiler import ControllerCompiler
        
        self.controller_factory = ControllerFactory(app_container=base_container)
        self.controller_engine = ControllerEngine(
            self.controller_factory,
            fault_engine=self.fault_engine,
        )
        self.controller_compiler = ControllerCompiler()
        
        # Track startup state
        self._startup_complete = False
        self._startup_lock = None  # Will be created in async context
        
        # Create ASGI app with server reference for lifecycle management
        # Note: self.aquila_sockets is initialized in _setup_middleware()
        self.app = ASGIAdapter(
            controller_router=self.controller_router,
            controller_engine=self.controller_engine,
            socket_runtime=self.aquila_sockets,
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
        
        # Add Fault engine middleware
        self.middleware_stack.add(
            FaultMiddleware(self.fault_engine),
            scope="global",
            priority=2,
            name="faults",
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
            except Exception as e:
                self.logger.error(f"Failed to create session engine: {e}", exc_info=True)
                self._session_engine = None
            
            # Try to set up auth if requested AND session engine succeeded
            auth_initialized = False
            if use_auth and self._session_engine is not None:
                self.logger.info("🔐 Initializing authentication system...")
                try:
                    # Create AuthManager
                    auth_manager = self._create_auth_manager(auth_config)
                    self._auth_manager = auth_manager
                    
                    # Add Unified Auth Middleware (handles both sessions and auth)
                    self.middleware_stack.add(
                        AquilAuthMiddleware(
                            session_engine=self._session_engine,
                            auth_manager=auth_manager,
                            require_auth=auth_config.get("security", {}).get("require_auth_by_default", False),
                            fault_engine=self.fault_engine,
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
                    auth_initialized = True
                    
                except Exception as e:
                    self.logger.error(
                        f"Failed to initialize auth system: {e}. "
                        f"Falling back to session-only middleware.",
                        exc_info=True,
                    )
                    self._auth_manager = None
            
            # Fallback: add session-only middleware if auth wasn't initialized
            if not auth_initialized and self._session_engine is not None:
                self.middleware_stack.add(
                    SessionMiddleware(self._session_engine),
                    scope="global",
                    priority=15,
                    name="session",
                )
                self.logger.info("✅ Session management enabled (Auth disabled or failed)")
            
            # Register SessionEngine in DI (if engine was created)
            if self._session_engine is not None:
                from aquilia.di.providers import ValueProvider
                from aquilia.sessions import SessionEngine
                
                engine_provider = ValueProvider(
                    token=SessionEngine,
                    value=self._session_engine,
                    scope="app",
                    name="session_engine_instance"
                )
                
                for container in self.runtime.di_containers.values():
                    container.register(engine_provider)
        else:
            self.logger.info("Session/Auth management disabled")

        # Add template engine integration
        template_config = self.config.get_template_config()
        use_templates = template_config.get("enabled", False)
        
        # Auto-enable if any app manifest has templates
        if not use_templates and hasattr(self, "aquilary"):
            for ctx in self.aquilary.app_contexts:
                if hasattr(ctx.manifest, "templates") and ctx.manifest.templates and ctx.manifest.templates.enabled:
                    use_templates = True
                    break
        
        if use_templates:
            self.logger.info("🎨 Initializing template engine...")
            
            # Step 1: Initialize Engine with config
            from .templates import TemplateEngine
            from .templates.loader import TemplateLoader
            from pathlib import Path

            search_paths = []
            
            # 1. Config paths
            if template_config.get("search_paths"):
                for p in template_config["search_paths"]:
                    search_paths.append(Path(p))
                    
            # 2. Manifest paths (auto-discovery)
            if hasattr(self, "aquilary"):
                 for ctx in self.aquilary.app_contexts:
                     # Try to derive path from manifest source
                     manifest_src = getattr(ctx.manifest, "__source__", None)
                     
                     found_path = False
                     if manifest_src and isinstance(manifest_src, str):
                         try:
                             # Check if it looks like a path
                             src_path = Path(manifest_src)
                             if src_path.exists() or src_path.is_absolute():
                                 app_template_dir = src_path.parent / "templates"
                                 if app_template_dir.exists():
                                     search_paths.append(app_template_dir)
                                     found_path = True
                         except Exception:
                             pass
                     
                     if not found_path:
                        # Fallback to convention: /modules/<name>/templates
                        convention_path = Path("modules") / ctx.name / "templates"
                        if convention_path.exists():
                            search_paths.append(convention_path)
            
            # Deduplicate
            search_paths = list(dict.fromkeys(search_paths))
            self.logger.debug(f"Template search paths: {search_paths}")

            # Register loader with discovered paths
            loader = TemplateLoader(search_paths=search_paths)
            
            # Create engine with production/dev settings based on config
            # (Here we use a generic engine, but factory methods in providers.py 
            # allow for customized creation if resolved via DI)
            self.template_engine = TemplateEngine(
                loader=loader,
                bytecode_cache=None if template_config.get("cache") == "none" else None # Default to memory if not specified or handled by provider logic
            )

            # Register providers for each container
            for container in self.runtime.di_containers.values():
                # Pass engine instance
                register_template_providers(container, engine=self.template_engine)
            
            # Register middleware
            self.middleware_stack.add(
                TemplateMiddleware(
                    url_for=self.controller_router.url_for,
                    config=self.config
                ),
                scope="global",
                priority=25,  # Processed after Auth/Session
                name="templates",
            )
            self.logger.info("✅ Template engine initialized and middleware registered")
            
        # Initialize WebSockets with DI container factory for per-connection scopes
        self.socket_router = SocketRouter()
        
        def _socket_container_factory(app_name: str = "default"):
            """Create request-scoped DI container for WebSocket connections."""
            app_container = self.runtime.di_containers.get(app_name)
            if app_container and hasattr(app_container, 'create_request_scope'):
                return app_container.create_request_scope()
            return app_container
        
        self.aquila_sockets = AquilaSockets(
            router=self.socket_router,
            adapter=InMemoryAdapter(),
            container_factory=_socket_container_factory,
            auth_manager=self._auth_manager,
            session_engine=self._session_engine,
        )
        self.logger.info("🔌 Initialized WebSocket subsystem")
            
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
        """Check if debug mode is enabled.

        Checks multiple locations for the debug flag:
        1. Top-level ``debug`` key (set by generated runtime/app.py)
        2. ``server.debug`` (dev.yaml / prod.yaml convention)
        3. ``AQUILIA_ENV`` environment variable (``dev`` implies debug)
        """
        if self.config.get("debug", False):
            return True
        if self.config.get("server.debug", False):
            return True
        import os
        if os.environ.get("AQUILIA_ENV", "").lower() == "dev":
            return True
        return False
    
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
        
        _INSECURE_SECRETS = {"aquilia_insecure_dev_secret", "dev_secret", "", None}
        is_dev = (
            self.mode == RegistryMode.DEV
            or self.config.get("mode", "") == "dev"
            or self.config.get("server.mode", "") == "dev"
            or self._is_debug()
        )
        if secret in _INSECURE_SECRETS and not is_dev:
            raise ValueError(
                "FATAL: Auth secret_key is insecure or unset in non-DEV mode. "
                "Set a strong secret via AQ_AUTH__TOKENS__SECRET_KEY or config."
            )
            
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
    
    async def _load_controllers(self):
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
        
        # Step 1.1: Auto-load starter controller in debug mode
        starter_compiled = await self._load_starter_controller()
        if starter_compiled:
            compiled_controllers.append(starter_compiled)

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

        # Step 1.2: Load socket controllers
        self.logger.info("Loading socket controllers...")
        await self._load_socket_controllers()

        # Initialize controller router
        self.controller_router.initialize()
        
        # Step 1.5: Register fault handlers from manifests
        self._register_fault_handlers()

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

    async def _load_socket_controllers(self):
        """Load and register WebSocket controllers."""
        from .sockets.runtime import RouteMetadata
        import inspect
        
        if not hasattr(self, "aquila_sockets"):
            return

        for app_ctx in self.runtime.meta.app_contexts:
            if not hasattr(app_ctx.manifest, "socket_controllers"):
                continue

            for controller_path in app_ctx.manifest.socket_controllers:
                try:
                    cls = self._import_controller_class(controller_path)
                    
                    if not hasattr(cls, "__socket_metadata__"):
                        self.logger.warning(f"Socket controller {controller_path} missing @Socket decorator")
                        continue
                        
                    meta = cls.__socket_metadata__
                    namespace = meta["path"]
                    
                    # Ensure unique namespace
                    if namespace in self.socket_router.routes:
                        self.logger.warning(f"Duplicate socket namespace {namespace}, skipping {controller_path}")
                        continue

                    handlers = {}
                    schemas = {}
                    guards = [] 
                    
                    # Scan methods
                    for name, method in inspect.getmembers(cls, inspect.isfunction):
                        if hasattr(method, "__socket_handler__"):
                            h_meta = method.__socket_handler__
                            h_type = h_meta.get("type")
                            
                            if h_type in ("event", "subscribe", "unsubscribe"):
                                event = h_meta.get("event")
                                handlers[event] = method
                                if h_meta.get("schema"):
                                    schemas[event] = h_meta.get("schema")
                            elif h_type == "guard":
                                # TODO: Instantiate guards
                                pass
                    
                    route_meta = RouteMetadata(
                        namespace=namespace,
                        path_pattern=namespace, # Pattern matching TODO
                        controller_class=cls,
                        handlers=handlers,
                        schemas=schemas,
                        guards=guards,
                        allowed_origins=meta.get("allowed_origins"),
                        max_connections=meta.get("max_connections"),
                        message_rate_limit=meta.get("message_rate_limit"),
                        max_message_size=meta.get("max_message_size", 1024 * 1024),
                    )
                    
                    self.socket_router.register(namespace, route_meta)
                    
                    # Create singleton instance (controllers should be stateless generally, 
                    # or manage state via Connection object)
                    # We try to inject deps from app container if available
                    instance = None
                    app_container = self.runtime.di_containers.get(app_ctx.name)
                    
                    if app_container:
                        # Ensure controller is registered
                        if not app_container.is_registered(cls):
                            from aquilia.di.providers import ClassProvider
                            provider = ClassProvider(cls, scope="singleton")
                            app_container.register(provider)
                            
                        # Resolve with dependencies (async)
                        instance = await app_container.resolve_async(cls)
                    else:
                        instance = cls()
                    
                    # Ensure namespace is injected
                    instance.namespace = namespace
                        
                    self.aquila_sockets.controller_instances[namespace] = instance
                    self.logger.info(f"🔌 Loaded socket controller {cls.__name__} at {namespace}")
                    
                except Exception as e:
                    self.logger.error(
                        f"Error loading socket controller {controller_path} from {app_ctx.name}: {e}",
                        exc_info=True
                    )

    
    async def _load_starter_controller(self):
        """Auto-load starter.py controller from workspace root when debug=True.

        Discovers a ``StarterController`` in the workspace ``starter.py``
        file and registers it so that new projects have a welcome page
        at ``/`` out of the box.

        The starter controller is only loaded if:
        - Debug mode is enabled
        - ``starter.py`` exists in the working directory
        - No other controller has already claimed ``GET /``
        """
        if not self._is_debug():
            return None

        import importlib
        import importlib.util
        from pathlib import Path

        # Look for starter.py in cwd (the workspace root)
        starter_path = Path.cwd() / "starter.py"
        if not starter_path.exists():
            return None

        # Check if any existing route already handles GET /
        try:
            existing_match = await self.controller_router.match("/", "GET", {})
            if existing_match:
                self.logger.debug("Starter controller skipped — GET / already registered")
                return None
        except Exception:
            pass

        try:
            spec = importlib.util.spec_from_file_location("starter", str(starter_path))
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            # Register in sys.modules so inspect.getfile() can resolve
            # the class back to its source file.
            import sys as _sys
            _sys.modules["starter"] = module
            spec.loader.exec_module(module)

            # Find Controller subclasses in the module
            from .controller import Controller
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Controller)
                    and obj is not Controller
                ):
                    compiled = self.controller_compiler.compile_controller(
                        obj, base_prefix=None,
                    )
                    # Tag routes so DI can fall back gracefully
                    for route in compiled.routes:
                        route.app_name = "__starter__"
                    self.controller_router.add_controller(compiled)
                    self.logger.info(
                        f"🚀 Loaded starter controller {obj.__name__} "
                        f"with {len(compiled.routes)} routes"
                    )
                    return compiled

        except Exception as e:
            self.logger.warning(f"Could not load starter controller: {e}")

        return None

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

    def _register_fault_handlers(self):
        """Register fault handlers from manifests."""
        import importlib
        
        for app_ctx in self.runtime.meta.app_contexts:
            # Check for faults config in manifest
            manifest = app_ctx.manifest
            if not manifest or not hasattr(manifest, "faults") or not manifest.faults:
                continue
            
            fault_config = manifest.faults
            if not hasattr(fault_config, "handlers"):
                continue

            for handler_cfg in fault_config.handlers:
                try:
                    handler_path = handler_cfg.handler_path
                    if ":" in handler_path:
                        mod_path, attr_name = handler_path.split(":", 1)
                    elif "." in handler_path:
                        mod_path, attr_name = handler_path.rsplit(".", 1)
                    else:
                        self.logger.error(f"Invalid handler path format: {handler_path}")
                        continue
                        
                    mod = importlib.import_module(mod_path)
                    handler_obj = getattr(mod, attr_name)
                    
                    if isinstance(handler_obj, type):
                        handler_instance = handler_obj()
                    else:
                        handler_instance = handler_obj
                        
                    self.fault_engine.register_app(app_ctx.name, handler_instance)
                    self.logger.info(f"✓ Registered fault handler from {app_ctx.name} manifest")
                except Exception as e:
                    self.logger.error(f"Failed to register fault handler {handler_cfg.handler_path} for app {app_ctx.name}: {e}")
    
    async def _register_amdl_models(self) -> None:
        """
        Register models discovered by the Aquilary pipeline.

        Supports both legacy AMDL (.amdl) files and new pure-Python Model
        subclasses (.py files with Model subclasses).

        Uses manifest-driven discovery (AppContext.models) populated by
        RuntimeRegistry.perform_autodiscovery() and explicit manifest
        declarations.  Also scans global ``models/`` and ``modules/``
        directories as a fallback for workspace-level model files.

        Lifecycle:
        1. Collect model paths from AppContexts + global scan
        2. Parse AMDL files / import Python model modules
        3. Configure database from manifest DatabaseConfig or config
        4. Optionally create tables / run migrations
        5. Register AquiliaDatabase + registries in all DI containers
        """
        from pathlib import Path

        try:
            from .models.parser import parse_amdl_file
            from .models.runtime import ModelRegistry as LegacyRegistry
            from .models.base import ModelRegistry, Model
            from .db.engine import AquiliaDatabase, configure_database, set_database
        except ImportError:
            self.logger.debug("Model system not available (missing deps?)")
            return

        # ── Phase 1: Collect model paths ──────────────────────────────────
        model_files: list[Path] = []
        workspace_root = Path.cwd()

        # 1a. From AppContexts (populated by Aquilary auto-discovery + manifests)
        for ctx in self.runtime.meta.app_contexts:
            for model_path in ctx.models:
                p = Path(model_path)
                if p.is_file() and p not in model_files:
                    model_files.append(p)

        # 1b. Global fallback scan (workspace-level models/ and modules/)
        for search_dir in [workspace_root / "models", workspace_root / "modules"]:
            if search_dir.is_dir():
                for amdl in search_dir.rglob("*.amdl"):
                    if amdl not in model_files:
                        model_files.append(amdl)
                # Only pick up Python files that are inside a "models" directory
                # or are themselves named "models.py" — never controllers/services/etc.
                for pyf in search_dir.rglob("*.py"):
                    if pyf.name.startswith("_"):
                        continue
                    # Accept: models.py, or any .py inside a models/ package
                    is_model_file = (
                        pyf.stem == "models"
                        or "models" in pyf.parent.parts
                    )
                    if not is_model_file:
                        continue
                    if pyf not in model_files:
                        model_files.append(pyf)

        amdl_files = [f for f in model_files if f.suffix == ".amdl"]
        py_files = [f for f in model_files if f.suffix == ".py"]

        if not amdl_files and not py_files:
            self.logger.debug("No model files found — skipping model registration")
            return

        total_count = len(amdl_files) + len(py_files)
        self.logger.info(f"Found {total_count} model file(s), registering models...")

        # ── Phase 2a: Parse and register AMDL (legacy) ────────────────────
        legacy_registry = getattr(self.runtime, '_model_registry', None) or LegacyRegistry()
        amdl_count = 0

        for amdl_path in amdl_files:
            try:
                amdl_file = parse_amdl_file(str(amdl_path))
                for model in amdl_file.models:
                    if model.name not in legacy_registry._models:
                        legacy_registry.register_model(model)
                        self.logger.debug(f"  Registered AMDL model: {model.name}")
                        amdl_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to parse {amdl_path}: {e}")

        # ── Phase 2b: Import and register Python models ───────────────────
        import importlib
        import importlib.util
        import sys
        py_count = 0

        for py_path in py_files:
            try:
                # Try package-aware import first (supports relative imports).
                # Compute a dotted module name relative to the workspace root.
                try:
                    rel = py_path.relative_to(workspace_root)
                except ValueError:
                    rel = None

                if rel is not None:
                    # e.g. modules/products/models/__init__.py → modules.products.models
                    parts = list(rel.with_suffix("").parts)
                    if parts and parts[-1] == "__init__":
                        parts = parts[:-1]
                    dotted = ".".join(parts)

                    # Ensure workspace root is on sys.path
                    ws_str = str(workspace_root)
                    if ws_str not in sys.path:
                        sys.path.insert(0, ws_str)

                    # Ensure parent packages exist in sys.modules
                    for i in range(1, len(parts)):
                        parent_dotted = ".".join(parts[:i])
                        if parent_dotted not in sys.modules:
                            parent_path = workspace_root / Path(*parts[:i])
                            init_file = parent_path / "__init__.py"
                            if init_file.is_file():
                                parent_spec = importlib.util.spec_from_file_location(
                                    parent_dotted, str(init_file),
                                    submodule_search_locations=[str(parent_path)]
                                )
                                if parent_spec and parent_spec.loader:
                                    parent_mod = importlib.util.module_from_spec(parent_spec)
                                    sys.modules[parent_dotted] = parent_mod
                                    try:
                                        parent_spec.loader.exec_module(parent_mod)
                                    except Exception:
                                        pass  # parent init may fail; that's ok
                            else:
                                # Create a namespace package stub
                                import types
                                ns_mod = types.ModuleType(parent_dotted)
                                ns_mod.__path__ = [str(parent_path)]
                                ns_mod.__package__ = parent_dotted
                                sys.modules[parent_dotted] = ns_mod

                    # Now import the actual model module
                    if dotted in sys.modules:
                        mod = sys.modules[dotted]
                    else:
                        mod = importlib.import_module(dotted)
                else:
                    # Fallback: file outside workspace, use spec_from_file_location
                    module_name = f"_aquilia_models_{py_path.stem}_{id(py_path)}"
                    spec = importlib.util.spec_from_file_location(module_name, str(py_path))
                    if spec is None or spec.loader is None:
                        continue
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                
                # Models self-register via metaclass; count them
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Model)
                        and attr is not Model
                    ):
                        py_count += 1
                        self.logger.debug(f"  Registered Python model: {attr.__name__}")
            except Exception as e:
                self.logger.warning(f"Failed to import {py_path}: {e}")

        # ── Phase 3: Resolve database configuration ───────────────────────
        db_url = None
        auto_create = False
        auto_migrate = False
        migrations_dir = "migrations"

        # 3a. Check manifest DatabaseConfig across all app contexts
        for ctx in self.runtime.meta.app_contexts:
            manifest = ctx.manifest
            if manifest and hasattr(manifest, "database") and manifest.database:
                db_cfg = manifest.database
                db_url = db_url or getattr(db_cfg, "url", None)
                auto_create = auto_create or getattr(db_cfg, "auto_create", False)
                auto_migrate = auto_migrate or getattr(db_cfg, "auto_migrate", False)
                migrations_dir = getattr(db_cfg, "migrations_dir", migrations_dir)

        # 3b. Check config dict (Workspace.database() / Integration.database())
        if not db_url:
            if hasattr(self.config, 'get'):
                db_url = self.config.get("database.url", None)
                auto_create = auto_create or self.config.get("database.auto_create", False)
                auto_migrate = auto_migrate or self.config.get("database.auto_migrate", False)
            elif hasattr(self.config, 'to_dict'):
                cfg_dict = self.config.to_dict()
                db_section = cfg_dict.get("database", {})
                db_url = db_url or db_section.get("url")
                auto_create = auto_create or db_section.get("auto_create", False)
                auto_migrate = auto_migrate or db_section.get("auto_migrate", False)

        # ── Phase 4: Connect and create tables ────────────────────────────
        if db_url:
            db = configure_database(db_url)
            await db.connect()
            self._amdl_database = db

            # Wire database to both registries
            if legacy_registry._models:
                legacy_registry.set_database(db)
            if ModelRegistry._models:
                ModelRegistry.set_database(db)

            if auto_create:
                # Create tables for both AMDL and Python models
                if legacy_registry._models:
                    await legacy_registry.create_tables()
                if ModelRegistry._models:
                    await ModelRegistry.create_tables()
                self.logger.info("Model tables auto-created")

            if auto_migrate:
                try:
                    from .models.migrations import MigrationRunner
                    runner = MigrationRunner(db, migrations_dir)
                    await runner.migrate()
                    self.logger.info("Migrations applied")
                except Exception as e:
                    self.logger.warning(f"Auto-migration failed: {e}")

            # ── Phase 5: Register in DI containers ────────────────────────
            from .di.providers import ValueProvider
            for container in self.runtime.di_containers.values():
                try:
                    container.register(ValueProvider(
                        value=db,
                        token=AquiliaDatabase,
                        scope="app",
                    ))
                except (ValueError, Exception):
                    pass

                if legacy_registry._models:
                    try:
                        container.register(ValueProvider(
                            value=legacy_registry,
                            token=LegacyRegistry,
                            scope="app",
                        ))
                    except (ValueError, Exception):
                        pass

                if ModelRegistry._models:
                    try:
                        container.register(ValueProvider(
                            value=ModelRegistry,
                            token=ModelRegistry,
                            scope="app",
                        ))
                    except (ValueError, Exception):
                        pass

            model_total = amdl_count + py_count
            self.logger.info(
                f"✓ Models registered: "
                f"{model_total} model(s) ({amdl_count} AMDL + {py_count} Python), DB={db.driver}"
            )
        else:
            self._amdl_database = None
            self.logger.debug(
                "No database.url in config — models registered without DB connection"
            )

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
            await self._load_controllers()
        
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
        
        # Step 3.1: Register AMDL models from apps (if any .amdl files exist)
        await self._register_amdl_models()
        
        # Step 3.5: Register effects from manifests and initialize providers
        self.logger.info("Registering and initializing effect providers...")
        self.runtime._register_effects()
        try:
            from .effects import EffectRegistry
            # Retrieve the SAME EffectRegistry from DI (registered in __init__)
            base_container = self._get_base_container()
            try:
                effect_registry = await base_container.resolve_async(EffectRegistry, optional=True)
            except Exception:
                effect_registry = None
            
            if effect_registry is None:
                effect_registry = EffectRegistry()
            
            await effect_registry.initialize_all()
            self._effect_registry = effect_registry
            self.logger.info(f"Effect providers initialized ({len(effect_registry.providers)} registered)")
        except Exception as e:
            self._effect_registry = None
            self.logger.debug(f"No effect providers to initialize: {e}")
        
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
        4. Disconnect database
        
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
        
        # Finalize effect providers
        if hasattr(self, '_effect_registry') and self._effect_registry:
            try:
                await self._effect_registry.finalize_all()
                self.logger.info("Effect providers finalized")
            except Exception as e:
                self.logger.warning(f"Error finalizing effect providers: {e}")
        
        # Disconnect AMDL database if connected
        if hasattr(self, '_amdl_database') and self._amdl_database:
            try:
                await self._amdl_database.disconnect()
                self.logger.info("AMDL database disconnected")
            except Exception as e:
                self.logger.warning(f"Error disconnecting AMDL database: {e}")
        
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
