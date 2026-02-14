"""
ASGI adapter - Bridges ASGI protocol to Aquilia's request/response system.
Supports HTTP, WebSocket, and Controllers.
"""

from typing import Dict, Any, Optional
import logging

from .request import Request
from .response import Response
from .middleware import MiddlewareStack, Handler
from .controller.router import ControllerRouter


class ASGIAdapter:
    """
    ASGI application adapter.
    Converts ASGI events to Aquilia Request/Response.
    Uses controller-based routing exclusively.
    """
    
    def __init__(
        self,
        controller_router: ControllerRouter,
        controller_engine: Any,
        middleware_stack: MiddlewareStack,
        server: Optional[Any] = None,
        socket_runtime: Optional[Any] = None,
    ):
        """
        Initialize ASGI adapter.
        
        Args:
            controller_router: Controller router for request matching
            controller_engine: ControllerEngine for controller execution
            middleware_stack: Middleware stack
            server: AquiliaServer instance for lifecycle management
            socket_runtime: AquilaSockets runtime
        """
        self.controller_router = controller_router
        self.controller_engine = controller_engine
        self.middleware_stack = middleware_stack
        self.server = server
        self.socket_runtime = socket_runtime
        self.logger = logging.getLogger("aquilia.asgi")
        
        # Configure socket runtime with DI factory if server is available
        if self.socket_runtime and self.server:
            self._setup_socket_di()
            
    def _setup_socket_di(self):
        """Setup DI container factory for WebSockets."""
        async def container_factory(request=None):
            if not self.server or not hasattr(self.server, 'runtime'):
                from .di import Container
                return Container(scope="request")
            
            # Try to find a container
            # For now, we take the first available app container
            # In the future, we could map socket namespaces to apps
            if self.server.runtime.di_containers:
                app_container = next(iter(self.server.runtime.di_containers.values()))
                return app_container.create_request_scope()
            
            # Fallback
            from .di import Container
            return Container(scope="request")
            
        self.socket_runtime.container_factory = container_factory

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def _is_debug(self) -> bool:
        """Check if the server is running in debug mode."""
        if self.server and hasattr(self.server, '_is_debug'):
            return self.server._is_debug()
        return False

    def _get_accept(self, scope: dict) -> str:
        """Extract the Accept header from ASGI scope."""
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"accept":
                return header_value.decode("utf-8", errors="replace")
        return ""

    def _get_version(self) -> str:
        """Get Aquilia version."""
        try:
            from aquilia import __version__
            return __version__
        except Exception:
            return ""

    def _has_routes(self) -> bool:
        """Check if any controller routes are registered."""
        try:
            if hasattr(self.controller_router, 'routes_by_method'):
                return any(
                    len(routes) > 0
                    for routes in self.controller_router.routes_by_method.values()
                )
            if hasattr(self.controller_router, 'compiled_controllers'):
                return len(self.controller_router.compiled_controllers) > 0
            return True  # Assume routes exist if we can't check
        except Exception:
            return True
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI entry point."""
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        elif scope["type"] == "lifespan":
            await self.handle_lifespan(scope, receive, send)
        else:
            self.logger.warning(f"Unknown ASGI scope type: {scope['type']}")
    
    async def handle_http(self, scope: dict, receive: callable, send: callable):
        """Handle HTTP request."""
        # Create Request object
        request = Request(scope, receive)
        
        # Match route
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        
        # Extract query params for controller matching
        query_params = {}
        if scope.get("query_string"):
            from urllib.parse import parse_qs
            query_string = scope.get("query_string", b"").decode("utf-8")
            parsed = parse_qs(query_string)
            query_params = {k: v[0] for k, v in parsed.items()}
        
        # Match controller route
        controller_match = await self.controller_router.match(path, method, query_params)
        
        if not controller_match:
            # 404 Not Found — show debug page if enabled
            if self._is_debug():
                accept = self._get_accept(scope)
                if "text/html" in accept:
                    from .debug.pages import render_http_error_page, render_welcome_page
                    version = self._get_version()
                    # Show welcome page on root path with no routes
                    if path == "/" and not self._has_routes():
                        html_body = render_welcome_page(aquilia_version=version)
                    else:
                        html_body = render_http_error_page(
                            404, "Not Found",
                            f"No route matches {method} {path}",
                            request,
                            aquilia_version=version,
                        )
                    response = Response(
                        content=html_body.encode("utf-8"),
                        status=404 if not (path == "/" and not self._has_routes()) else 200,
                        headers={"content-type": "text/html; charset=utf-8"},
                    )
                    await response.send_asgi(send)
                    return

            response = Response.json(
                {"error": "Not found"},
                status=404,
            )
            await response.send_asgi(send)
            return
        
        # Get DI container from server runtime registry
        di_container = None
        
        if self.server and hasattr(self.server, 'runtime'):
            # Get app name from route metadata
            app_name = getattr(controller_match.route, 'app_name', None)
            
            if app_name and self.server.runtime.di_containers.get(app_name):
                # Get specific app container
                app_container = self.server.runtime.di_containers[app_name]
                # Create request-scoped child container
                di_container = app_container.create_request_scope()
            elif self.server.runtime.di_containers:
                 # Fallback: Get first app container (or global if we had one)
                app_container = next(iter(self.server.runtime.di_containers.values()))
                di_container = app_container.create_request_scope()
        
        if not di_container:
            # Fallback: create minimal container
            from .di import Container
            di_container = Container(scope="request")
        
        # Create RequestCtx with proper initialization
        from .controller.base import RequestCtx
        ctx = RequestCtx(
            request=request,
            identity=None,  # Will be set by auth middleware if needed
            session=None,   # Will be set by session middleware if needed
            container=di_container,
        )
        
        # Store metadata in request state for middleware access
        app_name = getattr(controller_match.route, 'app_name', None)
        request.state["app_name"] = app_name
        request.state["route_pattern"] = getattr(controller_match.route, 'full_path', None)
        request.state["path_params"] = controller_match.params
        
        # Define final handler that executes the controller
        async def final_handler(req: Request, context: RequestCtx) -> Response:
            return await self.controller_engine.execute(
                controller_match.route,
                req,
                controller_match.params,
                context.container,
            )
            
        # Build middleware chain (wraps final_handler with all registered middleware)
        chain = self.middleware_stack.build_handler(final_handler)
        
        try:
            # Execute the full chain (Middleware -> Controller)
            response = await chain(request, ctx)
        except Exception as e:
            # Fallback if middleware itself crashes (e.g. ExceptionMiddleware missing or failed)
            self.logger.error(f"Critical error in request pipeline: {e}", exc_info=True)
            if self._is_debug():
                accept = self._get_accept(scope)
                if "text/html" in accept:
                    from .debug.pages import render_debug_exception_page
                    html_body = render_debug_exception_page(
                        e, request, aquilia_version=self._get_version(),
                    )
                    response = Response(
                        content=html_body.encode("utf-8"),
                        status=500,
                        headers={"content-type": "text/html; charset=utf-8"},
                    )
                    await response.send_asgi(send)
                    return
            response = Response.json(
                {"error": "Internal server error"},
                status=500,
            )
        
        await response.send_asgi(send)
    
    async def handle_websocket(self, scope: dict, receive: callable, send: callable):
        """Handle WebSocket connection."""
        if self.socket_runtime:
            await self.socket_runtime.handle_websocket(scope, receive, send)
        else:
            # Reject if no socket runtime
            self.logger.warning("WebSocket connection attempt but sockets are disabled")
            await send({
                "type": "websocket.close",
                "code": 1003,
            })
    
    async def handle_lifespan(self, scope: dict, receive: callable, send: callable):
        """
        Handle ASGI lifespan events.
        
        Integrates with AquiliaServer lifecycle management to ensure
        controllers are loaded and all startup/shutdown hooks are executed.
        """
        while True:
            message = await receive()
            
            if message["type"] == "lifespan.startup":
                try:
                    # Call server startup to load controllers and initialize
                    if self.server:
                        await self.server.startup()
                        self.logger.debug("Server startup complete")
                    else:
                        self.logger.warning("No server instance - controllers may not be loaded")
                    
                    await send({"type": "lifespan.startup.complete"})
                except Exception as e:
                    self.logger.error(f"Startup error: {e}", exc_info=True)
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
                    raise
            
            elif message["type"] == "lifespan.shutdown":
                try:
                    # Call server shutdown to cleanup resources
                    if self.server:
                        await self.server.shutdown()
                        self.logger.debug("Server shutdown complete")
                    
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception as e:
                    self.logger.error(f"Shutdown error: {e}", exc_info=True)
                    await send({"type": "lifespan.shutdown.failed", "message": str(e)})
                break
