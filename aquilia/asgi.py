"""
ASGI adapter - Bridges ASGI protocol to Aquilia's request/response system.
Supports HTTP, WebSocket, and Controllers.

Performance (v2):
- Middleware chain is built ONCE after startup and cached.
- Route matching uses sync O(1)/O(k) hot path.
- Per-request allocations minimized.
- Query string parsed once (lazy, inside Request).
- DI container lookup uses cached app container reference.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, Callable, Awaitable
import logging
import sys
import platform

from .request import Request
from .response import Response
from .middleware import MiddlewareStack, Handler
from .controller.router import ControllerRouter
from .controller.base import RequestCtx


class ASGIAdapter:
    """
    ASGI application adapter.
    Converts ASGI events to Aquilia Request/Response.
    Uses controller-based routing exclusively.
    """

    __slots__ = (
        'controller_router', 'controller_engine', 'middleware_stack',
        'server', 'socket_runtime', 'logger',
        '_cached_middleware_chain', '_default_container',
        '_debug', '_has_routes_cache', '_server_runtime',
    )

    def __init__(
        self,
        controller_router: ControllerRouter,
        controller_engine: Any,
        middleware_stack: MiddlewareStack,
        server: Optional[Any] = None,
        socket_runtime: Optional[Any] = None,
    ):
        self.controller_router = controller_router
        self.controller_engine = controller_engine
        self.middleware_stack = middleware_stack
        self.server = server
        self.socket_runtime = socket_runtime
        self.logger = logging.getLogger("aquilia.asgi")
        self._cached_middleware_chain: Optional[Handler] = None
        self._default_container = None
        self._debug: Optional[bool] = None
        self._has_routes_cache: Optional[bool] = None
        self._server_runtime = None  # Cached after startup

        if self.socket_runtime and self.server:
            self._setup_socket_di()

    def _setup_socket_di(self):
        """Setup DI container factory for WebSockets."""
        server = self.server

        async def container_factory(request=None):
            if not server or not hasattr(server, 'runtime'):
                from .di import Container
                return Container(scope="request")
            if server.runtime.di_containers:
                app_container = next(iter(server.runtime.di_containers.values()))
                return app_container.create_request_scope()
            from .di import Container
            return Container(scope="request")

        self.socket_runtime.container_factory = container_factory

    # ------------------------------------------------------------------
    # Cached helpers
    # ------------------------------------------------------------------

    def _is_debug(self) -> bool:
        if self._debug is None:
            if self.server and hasattr(self.server, '_is_debug'):
                self._debug = self.server._is_debug()
            else:
                self._debug = False
        return self._debug

    def _get_default_container(self):
        """Get or create the default app container (cached)."""
        if self._default_container is None:
            if self.server and hasattr(self.server, 'runtime') and self.server.runtime.di_containers:
                self._default_container = next(iter(self.server.runtime.di_containers.values()))
            else:
                from .di import Container
                self._default_container = Container(scope="app")
        return self._default_container

    def _has_routes(self) -> bool:
        if self._has_routes_cache is None:
            try:
                if hasattr(self.controller_router, 'routes_by_method'):
                    self._has_routes_cache = any(
                        len(routes) > 0
                        for routes in self.controller_router.routes_by_method.values()
                    )
                else:
                    self._has_routes_cache = True
            except Exception:
                self._has_routes_cache = True
        return self._has_routes_cache

    # ------------------------------------------------------------------
    # Middleware chain building (cached)
    # ------------------------------------------------------------------

    def _build_cached_chain(self):
        """Build the middleware chain once. The final handler dispatches
        to the matched controller stored in request.state."""
        if self._cached_middleware_chain is not None:
            return

        async def _final_handler(request: Request, ctx) -> Response:
            """Final handler that dispatches to matched controller."""
            controller_match = request.state.get("_controller_match")

            if controller_match:
                return await self.controller_engine.execute(
                    controller_match.route,
                    request,
                    controller_match.params,
                    ctx.container,
                )

            # No controller matched — 404
            if self._is_debug():
                accept = self._get_accept_from_request(request)
                if "text/html" in accept:
                    from .debug.pages import render_http_error_page, render_welcome_page
                    version = self._get_version()
                    path = request.path
                    method = request.method
                    if path == "/" and not self._has_routes():
                        # Gather System Info
                        system_info = {
                            "python_version": platform.python_version(),
                            "platform": sys.platform,
                            "debug": self._is_debug(),
                        }
                        # Try to get config features if server is available
                        if self.server and hasattr(self.server, 'config'):
                            cfg = self.server.config
                            system_info['auth'] = cfg.get_auth_config().get("enabled", False)
                            system_info['sessions'] = cfg.get_session_config().get("enabled", False)
                        
                        html_body = render_welcome_page(aquilia_version=version, system_info=system_info)
                        return Response(
                            content=html_body.encode("utf-8"),
                            status=200,
                            headers={"content-type": "text/html; charset=utf-8"},
                        )
                    html_body = render_http_error_page(
                        404, "Not Found",
                        f"No route matches {method} {path}",
                        request,
                        aquilia_version=version,
                    )
                    return Response(
                        content=html_body.encode("utf-8"),
                        status=404,
                        headers={"content-type": "text/html; charset=utf-8"},
                    )

            return Response.json({"error": "Not found"}, status=404)

        self._cached_middleware_chain = self.middleware_stack.build_handler(_final_handler)

    @staticmethod
    def _get_accept_from_request(request: Request) -> str:
        try:
            return request.header("accept") or ""
        except Exception:
            return ""

    def _get_version(self) -> str:
        try:
            from aquilia import __version__
            return __version__
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # ASGI entry point
    # ------------------------------------------------------------------

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        scope_type = scope["type"]
        if scope_type == "http":
            await self.handle_http(scope, receive, send)
        elif scope_type == "websocket":
            await self.handle_websocket(scope, receive, send)
        elif scope_type == "lifespan":
            await self.handle_lifespan(scope, receive, send)

    async def handle_http(self, scope: dict, receive: Callable, send: Callable):
        """Handle HTTP request with optimized hot path."""

        # ── Build middleware chain once (idempotent) ──
        if self._cached_middleware_chain is None:
            self._build_cached_chain()

        # ── Create lean Request object ──
        request = Request(scope, receive)

        # ── Sync route matching (O(1) for static, O(k) for dynamic) ──
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        controller_match = self.controller_router.match_sync(path, method)

        # ── Resolve DI container ──
        app_container = None
        runtime = self._server_runtime
        if runtime is None and self.server and hasattr(self.server, 'runtime'):
            runtime = self.server.runtime
            self._server_runtime = runtime

        if controller_match and runtime:
            app_name = getattr(controller_match.route, 'app_name', None)
            if app_name:
                app_container = runtime.di_containers.get(app_name)
            if app_container is None and runtime.di_containers:
                app_container = self._get_default_container()
        else:
            app_container = self._get_default_container()

        di_container = app_container.create_request_scope() if app_container else None
        if di_container is None:
            from .di import Container
            di_container = Container(scope="request")

        # ── Build RequestCtx ──
        ctx = RequestCtx(
            request=request,
            identity=None,
            session=None,
            container=di_container,
        )

        # Store controller match in request state for the final handler
        if controller_match:
            request.state["_controller_match"] = controller_match
            request.state["app_name"] = getattr(controller_match.route, 'app_name', None)
            request.state["route_pattern"] = getattr(controller_match.route, 'full_path', None)
            request.state["path_params"] = controller_match.params
        else:
            request.state["app_name"] = None
            request.state["route_pattern"] = None
            request.state["path_params"] = {}

        # ── Execute cached middleware chain ──
        try:
            response = await self._cached_middleware_chain(request, ctx)
        except Exception as e:
            self.logger.error(f"Critical error in request pipeline: {e}", exc_info=True)
            if self._is_debug():
                accept = self._get_accept_from_request(request)
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

    async def handle_websocket(self, scope: dict, receive: Callable, send: Callable):
        """Handle WebSocket connection."""
        if self.socket_runtime:
            await self.socket_runtime.handle_websocket(scope, receive, send)
        else:
            self.logger.warning("WebSocket connection attempt but sockets are disabled")
            await send({"type": "websocket.close", "code": 1003})

    async def handle_lifespan(self, scope: dict, receive: Callable, send: Callable):
        """Handle ASGI lifespan events."""
        while True:
            message = await receive()

            if message["type"] == "lifespan.startup":
                try:
                    if self.server:
                        await self.server.startup()
                        # Invalidate caches after startup
                        self._cached_middleware_chain = None
                        self._default_container = None
                        self._has_routes_cache = None
                        self._debug = None
                        self._server_runtime = None
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
                    if self.server:
                        await self.server.shutdown()
                        self.logger.debug("Server shutdown complete")
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception as e:
                    self.logger.error(f"Shutdown error: {e}", exc_info=True)
                    await send({"type": "lifespan.shutdown.failed", "message": str(e)})
                break
