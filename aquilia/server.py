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
        
        # Add session middleware if enabled
        session_config = self.config.get_session_config()
        if session_config.get("enabled", False):
            try:
                # Create session engine
                session_engine = self._create_session_engine(session_config)
                
                # Add session middleware
                self.middleware_stack.add(
                    SessionMiddleware(session_engine),
                    scope="global",
                    priority=15,
                    name="session",
                )
                
                # Store engine reference for later use
                self._session_engine = session_engine
                
                self.logger.info("✅ Session management enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize session management: {e}", exc_info=True)
                self._session_engine = None
        else:
            self._session_engine = None
    
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
        
        # Build session policy from config
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
    
    def _load_controllers(self):
        """Load and compile controllers from all apps."""
        if not self.controller_compiler:
            return
        
        for app_ctx in self.runtime.meta.app_contexts:
            # Import and compile controllers
            for controller_path in app_ctx.controllers:
                try:
                    controller_class = self._import_controller_class(controller_path)
                    
                    # Compile controller
                    compiled = self.controller_compiler.compile_controller(controller_class)
                    
                    # Inject app context info for DI resolution
                    for route in compiled.routes:
                        route.app_name = app_ctx.name
                    
                    # Register with controller router
                    self.controller_router.add_controller(compiled)
                    
                    self.logger.info(
                        f"Loaded controller {controller_class.__name__} "
                        f"from {app_ctx.name} with {len(compiled.routes)} routes"
                    )
                
                except Exception as e:
                    self.logger.error(
                        f"Error loading controller {controller_path} from {app_ctx.name}: {e}",
                        exc_info=True
                    )
        
        # Initialize controller router
        self.controller_router.initialize()
    
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
