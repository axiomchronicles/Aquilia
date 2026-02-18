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
from .controller.openapi import OpenAPIGenerator, OpenAPIConfig, generate_swagger_html, generate_redoc_html
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

        # Connect lifecycle events to trace journal
        def _lifecycle_trace_observer(event):
            try:
                phase_name = event.phase.value if event.phase else "unknown"
                error_str = str(event.error) if event.error else None
                self.trace.journal.record_phase(
                    f"lifecycle:{phase_name}",
                    app_name=event.app_name or "",
                    error=error_str,
                    detail=event.message,
                )
            except Exception:
                pass  # Trace is non-fatal
        self.coordinator.on_event(_lifecycle_trace_observer)
        
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
        
        # Trace directory (.aquilia/)
        from .trace import AquiliaTrace
        self.trace = AquiliaTrace()

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
        # Note: The ASGI adapter already creates a request-scoped container.
        # This middleware just stores references and handles cleanup.
        from .middleware_ext.request_scope import SimplifiedRequestScopeMiddleware
        
        runtime_ref = self.runtime  # capture for closure
        
        async def request_scope_mw(request, ctx, next_handler):
            """Request scope middleware — stores container refs and cleans up."""
            request.state["di_container"] = ctx.container
            app_name = request.state.get("app_name", "default")
            app_container = runtime_ref.di_containers.get(app_name)
            if app_container:
                request.state["app_container"] = app_container
            try:
                return await next_handler(request, ctx)
            finally:
                # Cleanup request scope
                if ctx.container and hasattr(ctx.container, 'shutdown'):
                    await ctx.container.shutdown()
        
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
                    config=self.config,
                    static_url_prefix=self._get_static_prefix(),
                ),
                scope="global",
                priority=25,  # Processed after Auth/Session
                name="templates",
            )
            self.logger.info("✅ Template engine initialized and middleware registered")

        # ── Mail subsystem ───────────────────────────────────────────────
        self._setup_mail()

        # ── Cache subsystem ──────────────────────────────────────────────
        self._setup_cache()

        # ── Security & Infrastructure Middleware ──────────────────────────
        self._setup_security_middleware()

        # Initialize WebSockets with DI container factory for per-connection scopes
        self.socket_router = SocketRouter()
        
        async def _socket_container_factory(request=None, app_name: str = "default"):
            """Create request-scoped DI container for WebSocket connections.
            
            This factory is called by the socket runtime during handshake.
            It accepts an optional request object (for extracting app context)
            and returns a request-scoped child DI container.
            """
            # If request has app_name in state, use it for more precise scoping
            if request and hasattr(request, 'state'):
                req_app = request.state.get('app_name')
                if req_app:
                    app_name = req_app
            
            app_container = self.runtime.di_containers.get(app_name)
            if not app_container and self.runtime.di_containers:
                # Fallback to first available container
                app_container = next(iter(self.runtime.di_containers.values()))
            
            if app_container and hasattr(app_container, 'create_request_scope'):
                return app_container.create_request_scope()
            
            # Fallback: create a minimal container
            from .di import Container
            return Container(scope="request")
        
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

    def _get_static_prefix(self) -> str:
        """Get the static URL prefix from config or default."""
        static_config = self.config.get("integrations.static_files", {})
        if static_config:
            dirs = static_config.get("directories", {})
            if dirs:
                return next(iter(dirs))
        return "/static"

    def _discover_module_static_dirs(self) -> dict:
        """
        Auto-discover static/ directories inside loaded modules.

        Works like Django's AppDirectoriesFinder: scans each module's
        package directory for a ``static/`` subdirectory.  Found directories
        are grouped under the configured static URL prefix so that
        ``{{ static('js/chat.js') }}`` resolves correctly regardless of
        which module owns the file.

        Returns:
            Dict mapping URL prefix → list of filesystem paths for every
            discovered module static directory.
        """
        from pathlib import Path
        import importlib

        # Group all discovered dirs under the static prefix
        static_prefix = self._get_static_prefix()   # e.g. "/static"
        discovered: list = []
        seen_packages: set = set()

        for ctx in self.runtime.meta.app_contexts:
            # Derive module package from any registered import path.
            # Controller paths look like "modules.chat.controllers:ChatController"
            import_paths = list(ctx.controllers) + list(ctx.services)
            for import_path in import_paths:
                if ":" in import_path:
                    mod_dotted = import_path.split(":", 1)[0]
                else:
                    mod_dotted = import_path.rsplit(".", 1)[0]

                # Go one level up to get the package dir (modules.chat)
                pkg_dotted = mod_dotted.rsplit(".", 1)[0] if "." in mod_dotted else mod_dotted

                if pkg_dotted in seen_packages:
                    continue
                seen_packages.add(pkg_dotted)

                try:
                    pkg = importlib.import_module(pkg_dotted)
                except ImportError:
                    continue

                pkg_dir = Path(pkg.__file__).parent if hasattr(pkg, "__file__") and pkg.__file__ else None
                if pkg_dir is None:
                    continue

                static_dir = pkg_dir / "static"
                if static_dir.is_dir():
                    resolved = str(static_dir.resolve())
                    discovered.append(resolved)
                    self.logger.debug(
                        f"Discovered module static dir: {ctx.name} → {resolved}"
                    )

        if discovered:
            return {static_prefix: discovered}
        return {}

    def _setup_security_middleware(self):
        """
        Wire security configuration to actual middleware instances.

        Reads from:
        - self.config["security"]  (set by Workspace.security())
        - self.config["integrations"]["static_files"]
        - self.config["integrations"]["cors"]
        - self.config["integrations"]["csp"]
        - self.config["integrations"]["rate_limit"]

        Middleware priority layout:
            3  - ProxyFixMiddleware  (must run before IP-dependent middleware)
            4  - HTTPSRedirectMiddleware
            6  - StaticMiddleware  (serve files before heavy processing)
            7  - SecurityHeadersMiddleware (helmet)
            8  - HSTSMiddleware
            9  - CSPMiddleware
            10 - CSRFMiddleware  (after session, before route handlers)
            11 - CORSMiddleware
            12 - RateLimitMiddleware
        """
        security_config = self.config.get("security", {})
        integrations = self.config.get("integrations", {})

        # ── Proxy Fix (priority 3) ───────────────────────────────────────
        if security_config.get("proxy_fix"):
            from .middleware_ext.security import ProxyFixMiddleware
            proxy_cfg = security_config.get("proxy_fix_config", {})
            if isinstance(proxy_cfg, bool):
                proxy_cfg = {}
            mw = ProxyFixMiddleware(
                trusted_proxies=proxy_cfg.get("trusted_proxies"),
                x_for=proxy_cfg.get("x_for", 1),
                x_proto=proxy_cfg.get("x_proto", 1),
                x_host=proxy_cfg.get("x_host", 1),
                x_port=proxy_cfg.get("x_port", 0),
            )
            self.middleware_stack.add(mw, scope="global", priority=3, name="proxy_fix")
            self.logger.info("🔧 ProxyFix middleware enabled")

        # ── HTTPS Redirect (priority 4) ──────────────────────────────────
        if security_config.get("https_redirect"):
            from .middleware_ext.security import HTTPSRedirectMiddleware
            https_cfg = security_config.get("https_redirect_config", {})
            if isinstance(https_cfg, bool):
                https_cfg = {}
            mw = HTTPSRedirectMiddleware(
                redirect_status=https_cfg.get("redirect_status", 301),
                exclude_paths=https_cfg.get("exclude_paths"),
                exclude_hosts=https_cfg.get("exclude_hosts"),
            )
            self.middleware_stack.add(mw, scope="global", priority=4, name="https_redirect")
            self.logger.info("🔒 HTTPS redirect middleware enabled")

        # ── Static Files (priority 6) ────────────────────────────────────
        static_config = integrations.get("static_files", {})
        if static_config.get("enabled"):
            from .middleware_ext.static import StaticMiddleware

            # Explicitly configured directories
            directories = dict(static_config.get("directories", {"/static": "static"}))

            # Auto-discover static/ dirs inside loaded modules
            # (like Django's AppDirectoriesFinder)
            module_static_dirs = self._discover_module_static_dirs()

            mw = StaticMiddleware(
                directories=directories,
                cache_max_age=static_config.get("cache_max_age", 86400),
                immutable=static_config.get("immutable", False),
                etag=static_config.get("etag", True),
                gzip=static_config.get("gzip", True),
                brotli=static_config.get("brotli", True),
                memory_cache=static_config.get("memory_cache", True),
                html5_history=static_config.get("html5_history", False),
                extra_directories=module_static_dirs,
            )
            self.middleware_stack.add(mw, scope="global", priority=6, name="static_files")
            self._static_middleware = mw
            all_dirs = dict(directories)
            for prefix, paths in module_static_dirs.items():
                for p in paths:
                    all_dirs[f"{prefix} (module)"] = p
            self.logger.info(
                f"📁 Static files middleware enabled: "
                f"{', '.join(f'{k}→{v}' for k, v in all_dirs.items())}"
            )

        # ── Security Headers / Helmet (priority 7) ───────────────────────
        if security_config.get("helmet_enabled", False):
            from .middleware_ext.security import SecurityHeadersMiddleware
            helmet_cfg = security_config.get("helmet_config", {})
            if isinstance(helmet_cfg, bool):
                helmet_cfg = {}
            mw = SecurityHeadersMiddleware(
                frame_options=helmet_cfg.get("frame_options", "DENY"),
                referrer_policy=helmet_cfg.get("referrer_policy", "strict-origin-when-cross-origin"),
                permissions_policy=helmet_cfg.get("permissions_policy"),
                cross_origin_opener_policy=helmet_cfg.get("cross_origin_opener_policy", "same-origin"),
                cross_origin_resource_policy=helmet_cfg.get("cross_origin_resource_policy", "same-origin"),
                content_type_nosniff=helmet_cfg.get("content_type_nosniff", True),
                remove_server_header=helmet_cfg.get("remove_server_header", True),
            )
            self.middleware_stack.add(mw, scope="global", priority=7, name="security_headers")
            self.logger.info("🛡️ Security headers (helmet) middleware enabled")

        # ── HSTS (priority 8) ────────────────────────────────────────────
        if security_config.get("hsts", False):
            from .middleware_ext.security import HSTSMiddleware
            hsts_cfg = security_config.get("hsts_config", {})
            if isinstance(hsts_cfg, bool):
                hsts_cfg = {}
            mw = HSTSMiddleware(
                max_age=hsts_cfg.get("max_age", 31536000),
                include_subdomains=hsts_cfg.get("include_subdomains", True),
                preload=hsts_cfg.get("preload", False),
            )
            self.middleware_stack.add(mw, scope="global", priority=8, name="hsts")
            self.logger.info("🔐 HSTS middleware enabled")

        # ── CSP (priority 9) ─────────────────────────────────────────────
        csp_config = security_config.get("csp") or integrations.get("csp", {})
        if csp_config and csp_config.get("enabled"):
            from .middleware_ext.security import CSPMiddleware, CSPPolicy
            policy_dict = csp_config.get("policy")
            if policy_dict:
                policy = CSPPolicy(directives=policy_dict)
            else:
                preset = csp_config.get("preset", "strict")
                policy = CSPPolicy.strict() if preset == "strict" else CSPPolicy.relaxed()
            mw = CSPMiddleware(
                policy=policy,
                report_only=csp_config.get("report_only", False),
                nonce=csp_config.get("nonce", True),
            )
            self.middleware_stack.add(mw, scope="global", priority=9, name="csp")
            self.logger.info("📋 CSP middleware enabled")

        # ── CORS (priority 11) ───────────────────────────────────────────
        cors_config = security_config.get("cors") or integrations.get("cors", {})
        if security_config.get("cors_enabled") or (cors_config and cors_config.get("enabled")):
            from .middleware_ext.security import CORSMiddleware as EnhancedCORSMiddleware
            if cors_config and cors_config.get("enabled"):
                mw = EnhancedCORSMiddleware(
                    allow_origins=cors_config.get("allow_origins", ["*"]),
                    allow_methods=cors_config.get("allow_methods"),
                    allow_headers=cors_config.get("allow_headers"),
                    expose_headers=cors_config.get("expose_headers"),
                    allow_credentials=cors_config.get("allow_credentials", False),
                    max_age=cors_config.get("max_age", 600),
                    allow_origin_regex=cors_config.get("allow_origin_regex"),
                )
            else:
                # Simple flag — use permissive defaults
                mw = EnhancedCORSMiddleware(allow_origins=["*"])
            self.middleware_stack.add(mw, scope="global", priority=11, name="cors")
            self.logger.info("🌐 CORS middleware enabled")

        # ── CSRF Protection (priority 10) ────────────────────────────────
        # Must run AFTER session middleware (priority 15) so session is available,
        # but BEFORE route handlers. Priority 10 places it between CSP and CORS.
        if security_config.get("csrf_protection"):
            from .middleware_ext.security import CSRFMiddleware, csrf_token_func as _csrf_token_func
            csrf_cfg = security_config.get("csrf_config", {})
            if isinstance(csrf_cfg, bool):
                csrf_cfg = {}
            mw = CSRFMiddleware(
                secret_key=csrf_cfg.get("secret_key"),
                token_length=csrf_cfg.get("token_length", 32),
                header_name=csrf_cfg.get("header_name", "X-CSRF-Token"),
                field_name=csrf_cfg.get("field_name", "_csrf_token"),
                cookie_name=csrf_cfg.get("cookie_name", "_csrf_cookie"),
                cookie_path=csrf_cfg.get("cookie_path", "/"),
                cookie_domain=csrf_cfg.get("cookie_domain"),
                cookie_secure=csrf_cfg.get("cookie_secure", False),
                cookie_samesite=csrf_cfg.get("cookie_samesite", "Lax"),
                cookie_httponly=csrf_cfg.get("cookie_httponly", False),
                cookie_max_age=csrf_cfg.get("cookie_max_age", 3600),
                exempt_paths=csrf_cfg.get("exempt_paths"),
                exempt_content_types=csrf_cfg.get("exempt_content_types"),
                trust_ajax=csrf_cfg.get("trust_ajax", True),
                rotate_token=csrf_cfg.get("rotate_token", False),
                failure_status=csrf_cfg.get("failure_status", 403),
            )
            self.middleware_stack.add(mw, scope="global", priority=10, name="csrf")
            self.logger.info("🛡️ CSRF protection middleware enabled")

            # Wire CSRF token function into TemplateMiddleware if present
            self._csrf_token_func = _csrf_token_func

        # ── Rate Limiting (priority 12) ──────────────────────────────────
        rl_config = security_config.get("rate_limit") or integrations.get("rate_limit", {})
        if security_config.get("rate_limiting") or (rl_config and rl_config.get("enabled")):
            from .middleware_ext.rate_limit import RateLimitMiddleware, RateLimitRule
            from .middleware_ext.rate_limit import ip_key_extractor, user_key_extractor
            rules = []
            if rl_config and rl_config.get("enabled"):
                key_func = user_key_extractor if rl_config.get("per_user") else ip_key_extractor
                rules.append(RateLimitRule(
                    limit=rl_config.get("limit", 100),
                    window=rl_config.get("window", 60),
                    algorithm=rl_config.get("algorithm", "sliding_window"),
                    key_func=key_func,
                    burst=rl_config.get("burst"),
                ))
                exempt = rl_config.get("exempt_paths")
            else:
                rules.append(RateLimitRule(limit=100, window=60))
                exempt = None
            mw = RateLimitMiddleware(
                rules=rules,
                exempt_paths=exempt,
            )
            self.middleware_stack.add(mw, scope="global", priority=12, name="rate_limit")
            self.logger.info("⏱️ Rate limiting middleware enabled")
    
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
    
    def _setup_mail(self):
        """
        Initialize AquilaMail subsystem from workspace config.

        Reads ``Integration.mail()`` configuration, creates :class:`MailService`,
        registers it in DI containers (with MailConfig and MailProviderRegistry),
        and sets the module-level singleton so ``send_mail``/``asend_mail`` just work.

        Uses the mail DI providers module for proper wiring:
        - MailConfig is validated through Serializers and registered in DI
        - MailService is registered in DI via ValueProvider
        - MailProviderRegistry auto-discovers IMailProvider implementations
          using Aquilia's PackageScanner (discovery system)

        The actual provider connections happen during :meth:`startup` (async).
        """
        mail_config = self.config.get_mail_config()
        if not mail_config.get("enabled", False):
            self._mail_service = None
            self.logger.debug("Mail subsystem disabled")
            return

        self.logger.info("📧 Initializing mail subsystem...")

        from .mail.di_providers import register_mail_providers
        from .mail.service import set_mail_service

        # Register in every DI container via the DI providers module
        svc = None
        for container in self.runtime.di_containers.values():
            svc = register_mail_providers(
                container=container,
                config_data=mail_config,
                discover_providers=True,
            )

        # If no containers existed, still create the service
        if svc is None:
            from .mail.config import MailConfig
            from .mail.service import MailService
            config_obj = MailConfig.from_dict(mail_config)
            svc = MailService(config=config_obj)

        # Install module-level singleton for convenience API
        set_mail_service(svc)
        self._mail_service = svc

        self.logger.info(
            f"📧 Mail configured "
            f"(from={svc.config.default_from!r}, "
            f"providers={len(svc.config.providers)}, "
            f"console={svc.config.console_backend})"
        )

    def _setup_cache(self):
        """
        Initialize cache subsystem from workspace config.

        Reads ``Integration.cache()`` configuration, creates the appropriate
        :class:`CacheBackend` and wraps it in a :class:`CacheService`, then
        registers both in every DI container so controllers / services can
        inject ``CacheService`` or ``CacheBackend``.

        If cache middleware is enabled the ``CacheMiddleware`` layer is pushed
        onto the middleware stack (priority 26, right after templates).

        Actual backend connections (e.g. Redis ``ping``) happen lazily or
        during :meth:`startup` where ``CacheService.initialize()`` is called.
        """
        cache_config = self.config.get_cache_config()
        if not cache_config.get("enabled", False):
            self._cache_service = None
            self.logger.debug("Cache subsystem disabled")
            return

        self.logger.info("🗄️  Initializing cache subsystem...")

        try:
            from .cache.di_providers import (
                build_cache_config,
                create_cache_service,
                register_cache_providers,
            )

            config_obj = build_cache_config(cache_config)
            svc = create_cache_service(config_obj)

            # Register in every DI container
            for container in self.runtime.di_containers.values():
                register_cache_providers(container, svc)

            self._cache_service = svc

            # Optionally add HTTP response-cache middleware
            mw_cfg = cache_config.get("middleware", {})
            if mw_cfg.get("enabled", False):
                from .cache.middleware import CacheMiddleware

                self.middleware_stack.add(
                    CacheMiddleware(
                        cache_service=svc,
                        ttl=mw_cfg.get("ttl", 300),
                        namespace=mw_cfg.get("namespace", "http"),
                    ),
                    scope="global",
                    priority=26,
                    name="cache",
                )
                self.logger.info("🗄️  Cache middleware enabled")

            backend_name = cache_config.get("backend", "memory")
            self.logger.info(
                f"🗄️  Cache configured (backend={backend_name}, "
                f"default_ttl={config_obj.default_ttl}s, "
                f"max_size={config_obj.max_size})"
            )
        except Exception as e:
            self._cache_service = None
            self.logger.error(f"Cache subsystem init failed (non-fatal): {e}", exc_info=True)

    def _resolve_store_from_name(self, store_name: str, **kwargs):
        """
        Resolve a PersistencePolicy.store_name string to an actual SessionStore instance.
        
        This is the canonical mapping from store name labels to concrete store objects.
        Handles all known store types and provides a safe fallback to MemoryStore.
        
        Args:
            store_name: The store name label (e.g., "memory", "default", "file", "redis")
            **kwargs: Additional store-specific configuration (unknown keys are ignored)
            
        Returns:
            A concrete SessionStore instance
        """
        from aquilia.sessions import MemoryStore, FileStore
        
        store_name = (store_name or "memory").lower().strip()
        
        # "default" is an alias for "memory"
        if store_name in ("memory", "default", "mem", "in-memory"):
            max_sessions = kwargs.get("max_sessions", 10000)
            if not isinstance(max_sessions, int):
                max_sessions = 10000
            return MemoryStore(max_sessions=max_sessions)
        elif store_name in ("file", "filesystem", "fs"):
            directory = kwargs.get("directory", "/tmp/aquilia_sessions")
            if not directory:
                directory = "/tmp/aquilia_sessions"
            return FileStore(directory=directory)
        else:
            self.logger.warning(
                f"Unknown session store name '{store_name}', falling back to MemoryStore. "
                f"Valid store names: 'memory', 'default', 'file'"
            )
            return MemoryStore(max_sessions=kwargs.get("max_sessions", 10000) if isinstance(kwargs.get("max_sessions"), int) else 10000)
    
    def _resolve_transport_from_policy(self, transport_policy):
        """
        Resolve a TransportPolicy to an actual SessionTransport instance.
        
        This is the canonical mapping from TransportPolicy.adapter strings to concrete
        transport objects.
        
        Args:
            transport_policy: A TransportPolicy instance with adapter, cookie_*, header_* settings
            
        Returns:
            A concrete SessionTransport instance
        """
        from aquilia.sessions import CookieTransport, HeaderTransport
        
        adapter = getattr(transport_policy, "adapter", "cookie")
        
        if adapter in ("cookie", "cookies"):
            return CookieTransport(transport_policy)
        elif adapter in ("header", "headers"):
            return HeaderTransport(transport_policy)
        elif adapter == "token":
            # Token-based typically uses header transport with the token header
            return HeaderTransport(transport_policy)
        else:
            self.logger.warning(
                f"Unknown transport adapter '{adapter}', falling back to CookieTransport. "
                f"Valid adapters: 'cookie', 'header', 'token'"
            )
            return CookieTransport(transport_policy)
    
    def _create_session_engine(self, session_config: dict):
        """
        Create SessionEngine from configuration.
        
        Handles three configuration formats:
        
        1. Integration.sessions() format — "policy" (singular) key with direct objects:
           {"enabled": True, "policy": <SessionPolicy>, "store": <MemoryStore>, "transport": <CookieTransport>}
           
        2. Workspace.sessions(policies=[...]) format — "policies" (plural) key with a list:
           {"enabled": True, "policies": [<SessionPolicy>, <SessionPolicy>, ...]}
           
        3. Traditional dict format — raw dictionaries for each sub-config:
           {"enabled": True, "policy": {"name": "...", "ttl_days": 7, ...}, "store": {"type": "memory"}, ...}
        
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
        
        # ── Format 1: Integration.sessions() — direct policy object (singular) ──
        if "policy" in session_config and not isinstance(session_config["policy"], dict):
            policy = session_config["policy"]
            store = session_config.get("store")
            transport_config = session_config.get("transport")
            
            # Resolve store: object → keep, dict → build, str → resolve, None → resolve from policy
            if store is None:
                store = self._resolve_store_from_name(
                    policy.persistence.store_name if policy.persistence else "memory"
                )
            elif isinstance(store, str):
                # String store name from YAML config (e.g., "memory") — resolve to object
                store = self._resolve_store_from_name(store)
            elif isinstance(store, dict):
                store = self._resolve_store_from_name(
                    store.get("type", "memory"),
                    **{k: v for k, v in store.items() if k != "type" and v is not None}
                )
            # else: store is already a concrete SessionStore object — use as-is
                
            # Resolve transport: object → keep, dict → build, None → resolve from policy
            if transport_config is None:
                transport = self._resolve_transport_from_policy(policy.transport)
            elif isinstance(transport_config, dict):
                tp = TransportPolicy(**transport_config)
                transport = self._resolve_transport_from_policy(tp)
            else:
                transport = transport_config
            
            self.logger.info(
                f"SessionEngine initialized (Integration format): policy={policy.name}, "
                f"store={type(store).__name__}, transport={type(transport).__name__}"
            )
            return SessionEngine(policy=policy, store=store, transport=transport)
        
        # ── Format 2: Workspace.sessions(policies=[...]) — policy list (plural) ──
        if "policies" in session_config:
            policies_list = session_config["policies"]
            
            if not policies_list:
                self.logger.warning(
                    "Workspace sessions config has empty policies list, "
                    "creating default SessionPolicy"
                )
                policies_list = [SessionPolicy(name="default")]
            
            # Use the first policy as the primary engine policy.
            # In production multi-policy setups, a PolicyRouter would select
            # the appropriate policy per-request; for now we use the first one
            # (typically the "web" policy) as default.
            policy = policies_list[0]
            
            if len(policies_list) > 1:
                self.logger.info(
                    f"Multiple session policies configured: "
                    f"{[p.name for p in policies_list]}. "
                    f"Using '{policy.name}' as primary engine policy."
                )
            
            # Resolve store from PersistencePolicy.store_name
            # The store_name is a label string (e.g., "memory", "default", "redis"),
            # NOT a store object — we must resolve it to a concrete SessionStore.
            store_name = "memory"
            if policy.persistence and hasattr(policy.persistence, "store_name"):
                store_name = policy.persistence.store_name
            
            # Allow extra store kwargs from session_config
            store_kwargs = {}
            if isinstance(session_config.get("store"), dict):
                store_kwargs = {
                    k: v for k, v in session_config["store"].items() if k != "type"
                }
            
            store = self._resolve_store_from_name(store_name, **store_kwargs)
            
            # Resolve transport from TransportPolicy object on the policy
            transport = self._resolve_transport_from_policy(policy.transport)
            
            engine = SessionEngine(policy=policy, store=store, transport=transport)
            
            self.logger.info(
                f"SessionEngine initialized (Workspace format): policy={policy.name}, "
                f"store={type(store).__name__} (from store_name='{store_name}'), "
                f"transport={type(transport).__name__} (adapter='{policy.transport.adapter}')"
            )
            
            return engine
        
        # ── Format 3: Traditional dict format — build everything from dicts ──
        policy_config = session_config.get("policy", {})
        if isinstance(policy_config, dict):
            policy = SessionPolicy(
                name=policy_config.get("name", "user_default"),
                ttl=timedelta(days=policy_config.get("ttl_days", 7)),
                idle_timeout=timedelta(minutes=policy_config.get("idle_timeout_minutes", 30)),
                rotate_on_use=False,
                rotate_on_privilege_change=policy_config.get("rotate_on_privilege_change", True),
                persistence=PersistencePolicy(
                    enabled=True,
                    store_name=policy_config.get("store_name", "default"),
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
        else:
            # Unexpected: policy is neither a dict nor a SessionPolicy object
            # This shouldn't happen, but handle defensively
            self.logger.warning(
                f"Unexpected policy config type: {type(policy_config)}, using defaults"
            )
            policy = SessionPolicy(name="user_default")
        
        # Resolve store using the canonical resolver
        store_config = session_config.get("store", {})
        if isinstance(store_config, dict):
            store_type = store_config.get("type", "memory")
            store_kwargs = {k: v for k, v in store_config.items() if k != "type"}
            store = self._resolve_store_from_name(store_type, **store_kwargs)
        else:
            store = self._resolve_store_from_name("memory")
        
        # Resolve transport using the canonical resolver
        transport = self._resolve_transport_from_policy(policy.transport)
        
        # Create engine
        engine = SessionEngine(
            policy=policy,
            store=store,
            transport=transport,
        )
        
        self.logger.info(
            f"SessionEngine initialized (dict format): policy={policy.name}, "
            f"store={type(store).__name__}, transport={type(transport).__name__}"
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
            
            # Load initial users if configured in auth config
            initial_users = auth_config.get("initial_users", [])
            if initial_users:
                from .auth.core import Identity, IdentityStatus, IdentityType, PasswordCredential
                from .auth.hashing import PasswordHasher
                import uuid
                
                hasher = PasswordHasher()
                for user_cfg in initial_users:
                    try:
                        user_id = user_cfg.get("id", str(uuid.uuid4()))
                        
                        # Build attributes dict from config fields
                        attributes = user_cfg.get("attributes", {})
                        if "email" in user_cfg:
                            attributes.setdefault("email", user_cfg["email"])
                        if "display_name" in user_cfg or "username" in user_cfg:
                            attributes.setdefault("display_name", user_cfg.get("display_name", user_cfg.get("username", "")))
                        if "roles" in user_cfg:
                            attributes.setdefault("roles", list(user_cfg["roles"]))
                        if "scopes" in user_cfg:
                            attributes.setdefault("scopes", list(user_cfg["scopes"]))
                        
                        identity = Identity(
                            id=user_id,
                            type=IdentityType(user_cfg.get("type", "user")),
                            status=IdentityStatus(user_cfg.get("status", "active")),
                            attributes=attributes,
                            tenant_id=user_cfg.get("tenant_id"),
                        )
                        identity_store._identities[user_id] = identity
                        
                        # Hash and store password credential if provided
                        password = user_cfg.get("password")
                        if password:
                            hashed = hasher.hash(password)
                            credential = PasswordCredential(
                                identity_id=user_id,
                                password_hash=hashed,
                            )
                            credential_store._passwords[user_id] = credential
                        
                        self.logger.info(f"Loaded initial user: {attributes.get('email', user_id)}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load initial user: {e}")
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

        # Step 1.2: Initialize WebSocket runtime and load socket controllers
        self.logger.info("Initializing WebSocket runtime...")
        await self.aquila_sockets.initialize()
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
        """Register OpenAPI JSON, Swagger UI, and ReDoc routes."""
        # Build OpenAPIConfig from integration config or fallback to legacy keys
        openapi_integration = self.config.get("integrations", {}).get("openapi", {})
        if openapi_integration and openapi_integration.get("enabled", True):
            openapi_config = OpenAPIConfig.from_dict(openapi_integration)
        else:
            # Legacy fallback for backward compatibility
            openapi_config = OpenAPIConfig(
                title=self.config.get("api_title", "Aquilia API"),
                version=self.config.get("api_version", "1.0.0"),
            )

        generator = OpenAPIGenerator(config=openapi_config)

        # ── Handler: /openapi.json ───────────────────────────────────────
        async def openapi_handler(request, ctx):
            spec = generator.generate(self.controller_router)
            return Response.json(spec)

        # ── Handler: /docs (Swagger UI) ──────────────────────────────────
        swagger_html = generate_swagger_html(openapi_config)

        async def docs_handler(request, ctx):
            return Response.html(swagger_html)

        # ── Handler: /redoc ──────────────────────────────────────────────
        redoc_html = generate_redoc_html(openapi_config)

        async def redoc_handler(request, ctx):
            return Response.html(redoc_html)

        # Register routes via monkeypatched CompiledRoute (same approach as before)
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
                path_template=openapi_config.openapi_json_path,
                full_path=openapi_config.openapi_json_path,
                handler_name="openapi_handler",
            ),
            compiled_pattern=pc.compile(parse_pattern(openapi_config.openapi_json_path)),
            full_path=openapi_config.openapi_json_path,
            http_method="GET",
            specificity=1000,
        )
        route_json.handler = openapi_handler

        # Swagger UI
        route_docs = CompiledRoute(
            controller_class=self.__class__,
            controller_metadata=None,
            route_metadata=RouteMetadata(
                http_method="GET",
                path_template=openapi_config.docs_path,
                full_path=openapi_config.docs_path,
                handler_name="docs_handler",
            ),
            compiled_pattern=pc.compile(parse_pattern(openapi_config.docs_path)),
            full_path=openapi_config.docs_path,
            http_method="GET",
            specificity=1000,
        )
        route_docs.handler = docs_handler

        # ReDoc
        route_redoc = CompiledRoute(
            controller_class=self.__class__,
            controller_metadata=None,
            route_metadata=RouteMetadata(
                http_method="GET",
                path_template=openapi_config.redoc_path,
                full_path=openapi_config.redoc_path,
                handler_name="redoc_handler",
            ),
            compiled_pattern=pc.compile(parse_pattern(openapi_config.redoc_path)),
            full_path=openapi_config.redoc_path,
            http_method="GET",
            specificity=1000,
        )
        route_redoc.handler = redoc_handler

        self.controller_router.routes_by_method.setdefault("GET", []).append(route_json)
        self.controller_router.routes_by_method.setdefault("GET", []).append(route_docs)
        self.controller_router.routes_by_method.setdefault("GET", []).append(route_redoc)
        self.logger.info(
            f"📡 Registered documentation routes: "
            f"{openapi_config.docs_path} (Swagger UI) | "
            f"{openapi_config.redoc_path} (ReDoc) | "
            f"{openapi_config.openapi_json_path} (JSON)"
        )

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
                                # Instantiate guard from method-level @Guard decorator
                                guard_class = h_meta.get("guard_class")
                                guard_kwargs = h_meta.get("guard_kwargs", {})
                                if guard_class:
                                    try:
                                        guard_instance = guard_class(**guard_kwargs)
                                        guards.append(guard_instance)
                                        self.logger.debug(f"Instantiated guard {guard_class.__name__} for {namespace}")
                                    except Exception as ge:
                                        self.logger.warning(f"Failed to instantiate guard {guard_class}: {ge}")
                    
                    # Also instantiate class-level guards from metadata if present
                    if meta.get("guards"):
                        for guard_spec in meta["guards"]:
                            if isinstance(guard_spec, type):
                                try:
                                    guards.append(guard_spec())
                                except Exception as ge:
                                    self.logger.warning(f"Failed to instantiate class guard {guard_spec}: {ge}")
                            elif callable(guard_spec):
                                guards.append(guard_spec)
                    
                    # Use the @Socket path as the pattern (supports Aquilia patterns like /:id)
                    path_pattern = meta.get("path", namespace)
                    
                    route_meta = RouteMetadata(
                        namespace=namespace,
                        path_pattern=path_pattern,
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
                    
                    # Ensure namespace and adapter are injected
                    instance.namespace = namespace
                    instance.adapter = self.aquila_sockets.adapter
                        
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
                    # Skip private files (e.g. _helpers.py) but NOT __init__.py
                    if pyf.name.startswith("_") and pyf.name != "__init__.py":
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

        total_count = len(amdl_files) + len(py_files)
        if total_count > 0:
            self.logger.info(f"Found {total_count} model file(s), registering models...")
        else:
            self.logger.debug("No model files discovered via scan — checking for pre-registered models...")

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
        import time as _time

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
            
            _boot_t0 = _time.monotonic()

            self.logger.info("Starting Aquilia server with Aquilary registry...")
            
            # Log registry information
            self.logger.info(f"Registry fingerprint: {self.aquilary.fingerprint}")
            self.logger.info(f"Mode: {self.mode.value}")
            self.logger.info(f"Apps loaded: {len(self.runtime.meta.app_contexts)}")
            
            # Step 0: Perform runtime auto-discovery
            self.logger.info("Performing runtime auto-discovery...")
            _t0 = _time.monotonic()
            self.runtime.perform_autodiscovery()
            self.trace.journal.record_phase(
                "autodiscovery",
                duration_ms=(_time.monotonic() - _t0) * 1000,
            )
            
            # Step 1: Load and compile controllers
            self.logger.info("Loading controllers from manifests...")
            _t0 = _time.monotonic()
            await self._load_controllers()
            self.trace.journal.record_phase(
                "controllers_loaded",
                duration_ms=(_time.monotonic() - _t0) * 1000,
            )
        
        # Step 2: Compile routes (includes service registration and handler wrapping)
        self.logger.info("Compiling routes with DI integration...")
        _t0 = _time.monotonic()
        self.runtime.compile_routes()
        self.trace.journal.record_phase(
            "routes_compiled",
            duration_ms=(_time.monotonic() - _t0) * 1000,
        )
        
        # Step 3: Start lifecycle (runs app startup hooks in dependency order)
        self.logger.info("Starting app lifecycle hooks...")
        _t0 = _time.monotonic()
        try:
            await self.coordinator.startup()
            self.trace.journal.record_phase(
                "lifecycle_started",
                duration_ms=(_time.monotonic() - _t0) * 1000,
            )
        except Exception as e:
            from .lifecycle import LifecycleError
            self.logger.error(f"Lifecycle startup failed: {e}")
            self.trace.journal.record_phase(
                "lifecycle_started",
                error=str(e),
                duration_ms=(_time.monotonic() - _t0) * 1000,
            )
            raise LifecycleError(f"Startup failed: {e}") from e
        
        # Step 3.1: Register AMDL models from apps (if any .amdl files exist)
        _t0 = _time.monotonic()
        await self._register_amdl_models()
        self.trace.journal.record_phase(
            "models_registered",
            duration_ms=(_time.monotonic() - _t0) * 1000,
        )
        
        # Step 3.2: Start mail subsystem (connect providers)
        if hasattr(self, '_mail_service') and self._mail_service is not None:
            _t0 = _time.monotonic()
            try:
                await self._mail_service.on_startup()
                self.trace.journal.record_phase(
                    "mail_started",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.error(f"Mail startup failed: {e}")
                self.trace.journal.record_phase(
                    "mail_started",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
                # Non-fatal — app can run without mail

        # Step 3.5: Register effects from manifests and initialize providers
        self.logger.info("Registering and initializing effect providers...")
        _t0 = _time.monotonic()
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
            self.trace.journal.record_phase(
                "effects_initialized",
                duration_ms=(_time.monotonic() - _t0) * 1000,
                detail=f"{len(effect_registry.providers)} providers",
            )
        except Exception as e:
            self._effect_registry = None
            self.logger.debug(f"No effect providers to initialize: {e}")
            self.trace.journal.record_phase(
                "effects_initialized",
                duration_ms=(_time.monotonic() - _t0) * 1000,
                detail="none",
            )
        
        # Step 3.6: Initialize cache subsystem (connect backend)
        if hasattr(self, '_cache_service') and self._cache_service is not None:
            _t0 = _time.monotonic()
            try:
                await self._cache_service.initialize()
                self.logger.info("🗄️  Cache backend connected")
                self.trace.journal.record_phase(
                    "cache_started",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.error(f"Cache startup failed: {e}")
                self.trace.journal.record_phase(
                    "cache_started",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
                # Non-fatal — app can run without cache

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

        # Step 5: Trace snapshot — write .aquilia/ directory
        _startup_ms = (_time.monotonic() - _boot_t0) * 1000
        try:
            self.trace.snapshot(self, startup_duration_ms=_startup_ms)
            self.logger.info(f"📋 Trace snapshot written to {self.trace.root}")
        except Exception as e:
            self.logger.warning(f"Trace snapshot failed (non-fatal): {e}")

        self.logger.info(f"✅ Server ready with {len(self.runtime.meta.app_contexts)} apps ({_startup_ms:.0f}ms)")
    
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
        import time as _time

        if not self._startup_complete:
            return  # Nothing to shut down
        
        self.logger.info("Shutting down Aquilia server...")
        
        # Run lifecycle shutdown hooks
        _t0 = _time.monotonic()
        await self.coordinator.shutdown()
        self.trace.journal.record_phase(
            "lifecycle_shutdown",
            duration_ms=(_time.monotonic() - _t0) * 1000,
        )
        
        # Shutdown mail subsystem
        if hasattr(self, '_mail_service') and self._mail_service is not None:
            _t0 = _time.monotonic()
            try:
                await self._mail_service.on_shutdown()
                self.logger.info("Mail subsystem shut down")
                self.trace.journal.record_phase(
                    "mail_shutdown",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.warning(f"Error shutting down mail subsystem: {e}")
                self.trace.journal.record_phase(
                    "mail_shutdown",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )

        # Shutdown cache subsystem
        if hasattr(self, '_cache_service') and self._cache_service is not None:
            _t0 = _time.monotonic()
            try:
                await self._cache_service.shutdown()
                self.logger.info("🗄️  Cache subsystem shut down")
                self.trace.journal.record_phase(
                    "cache_shutdown",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.warning(f"Error shutting down cache subsystem: {e}")
                self.trace.journal.record_phase(
                    "cache_shutdown",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )

        # Cleanup DI containers
        _t0 = _time.monotonic()
        for app_name, container in self.runtime.di_containers.items():
            try:
                await container.shutdown()
                self.logger.debug(f"Cleaned up DI container for app '{app_name}'")
            except Exception as e:
                self.logger.warning(f"Error cleaning up container for '{app_name}': {e}")
                self.trace.journal.record_warning(
                    f"DI cleanup error for '{app_name}': {e}",
                    context="di_cleanup",
                )
        self.trace.journal.record_phase(
            "di_cleanup",
            duration_ms=(_time.monotonic() - _t0) * 1000,
        )
        
        # Finalize effect providers
        if hasattr(self, '_effect_registry') and self._effect_registry:
            _t0 = _time.monotonic()
            try:
                await self._effect_registry.finalize_all()
                self.logger.info("Effect providers finalized")
                self.trace.journal.record_phase(
                    "effects_finalized",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.warning(f"Error finalizing effect providers: {e}")
                self.trace.journal.record_phase(
                    "effects_finalized",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
        
        # Shutdown WebSocket runtime
        if hasattr(self, 'aquila_sockets') and self.aquila_sockets:
            _t0 = _time.monotonic()
            try:
                await self.aquila_sockets.shutdown()
                self.logger.info("WebSocket runtime shut down")
                self.trace.journal.record_phase(
                    "websocket_shutdown",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.warning(f"Error shutting down WebSocket runtime: {e}")
                self.trace.journal.record_phase(
                    "websocket_shutdown",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )

        # Disconnect AMDL database if connected
        if hasattr(self, '_amdl_database') and self._amdl_database:
            _t0 = _time.monotonic()
            try:
                await self._amdl_database.disconnect()
                self.logger.info("AMDL database disconnected")
                self.trace.journal.record_phase(
                    "db_disconnect",
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )
            except Exception as e:
                self.logger.warning(f"Error disconnecting AMDL database: {e}")
                self.trace.journal.record_phase(
                    "db_disconnect",
                    error=str(e),
                    duration_ms=(_time.monotonic() - _t0) * 1000,
                )

        # Trace shutdown snapshot
        if hasattr(self, 'trace'):
            try:
                self.trace.snapshot_shutdown(self)
                self.logger.info("📋 Trace shutdown snapshot written")
            except Exception as e:
                self.logger.warning(f"Trace shutdown snapshot failed (non-fatal): {e}")
        
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
