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
        """Handle HTTP request.

        The middleware chain is **always** executed so that middleware such as
        ``StaticMiddleware``, ``CORSMiddleware`` (preflight), etc. can
        intercept and respond to requests that do not match any controller
        route.  The controller match is performed inside the *final handler*
        of the middleware chain – if no route matches, a 404 is returned from
        there, but only after every middleware has had a chance to act.
        """
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

        # Pre-match the controller route so we can set up the DI container
        # and RequestCtx, but do NOT short-circuit on a miss – we need the
        # middleware chain to run regardless.
        controller_match = await self.controller_router.match(path, method, query_params)

        # Get DI container from server runtime registry
        di_container = None

        if controller_match and self.server and hasattr(self.server, 'runtime'):
            # Get app name from route metadata
            app_name = getattr(controller_match.route, 'app_name', None)

            if app_name and self.server.runtime.di_containers.get(app_name):
                app_container = self.server.runtime.di_containers[app_name]
                di_container = app_container.create_request_scope()
            elif self.server.runtime.di_containers:
                app_container = next(iter(self.server.runtime.di_containers.values()))
                di_container = app_container.create_request_scope()

        if not di_container:
            # Fallback: try to get any available container, or create minimal one
            if self.server and hasattr(self.server, 'runtime') and self.server.runtime.di_containers:
                app_container = next(iter(self.server.runtime.di_containers.values()))
                di_container = app_container.create_request_scope()
            else:
                from .di import Container
                di_container = Container(scope="request")

        # Create RequestCtx with proper initialization
        from .controller.base import RequestCtx
        ctx = RequestCtx(
            request=request,
            identity=None,
            session=None,
            container=di_container,
        )

        # Store metadata in request state for middleware access
        if controller_match:
            app_name = getattr(controller_match.route, 'app_name', None)
            request.state["app_name"] = app_name
            request.state["route_pattern"] = getattr(controller_match.route, 'full_path', None)
            request.state["path_params"] = controller_match.params
        else:
            request.state["app_name"] = None
            request.state["route_pattern"] = None
            request.state["path_params"] = {}

        # Define final handler: execute the matched controller or return 404.
        # Middleware earlier in the chain (e.g. StaticMiddleware) may return
        # a response before this handler is ever reached.
        async def final_handler(req: Request, context: RequestCtx) -> Response:
            if controller_match:
                return await self.controller_engine.execute(
                    controller_match.route,
                    req,
                    controller_match.params,
                    context.container,
                )

            # No controller matched – 404
            if self._is_debug():
                accept = self._get_accept(scope)
                if "text/html" in accept:
                    from .debug.pages import render_http_error_page, render_welcome_page
                    version = self._get_version()
                    if path == "/" and not self._has_routes():
                        html_body = render_welcome_page(aquilia_version=version)
                        return Response(
                            content=html_body.encode("utf-8"),
                            status=200,
                            headers={"content-type": "text/html; charset=utf-8"},
                        )
                    html_body = render_http_error_page(
                        404, "Not Found",
                        f"No route matches {method} {path}",
                        req,
                        aquilia_version=version,
                    )
                    return Response(
                        content=html_body.encode("utf-8"),
                        status=404,
                        headers={"content-type": "text/html; charset=utf-8"},
                    )

            return Response.json({"error": "Not found"}, status=404)

        # Build middleware chain (wraps final_handler with all registered middleware)
        chain = self.middleware_stack.build_handler(final_handler)

        try:
            # Execute the full chain (Middleware -> Controller or 404)
            response = await chain(request, ctx)
        except Exception as e:
            # Fallback if middleware itself crashes
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
