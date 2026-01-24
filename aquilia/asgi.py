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
    ):
        """
        Initialize ASGI adapter.
        
        Args:
            controller_router: Controller router for request matching
            controller_engine: ControllerEngine for controller execution
            middleware_stack: Middleware stack
            server: AquiliaServer instance for lifecycle management
        """
        self.controller_router = controller_router
        self.controller_engine = controller_engine
        self.middleware_stack = middleware_stack
        self.server = server
        self.logger = logging.getLogger("aquilia.asgi")
    
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
            # 404 Not Found
            response = Response.json(
                {"error": "Not found"},
                status=404,
            )
            await response.send_asgi(send)
            return
        
        # Get DI container from server runtime registry
        di_container = None
        
        if self.server and hasattr(self.server, 'runtime'):
            # Get the first app's container (or create request scope from it)
            if self.server.runtime.di_containers:
                # Get first app container
                app_container = next(iter(self.server.runtime.di_containers.values()))
                # Create request-scoped child container
                di_container = app_container.create_request_scope()
        
        if not di_container:
            # Fallback: create minimal container
            from .di import Container
            di_container = Container(scope="request")
        
        # Store path params in request state
        request.state["path_params"] = controller_match.params
        
        try:
            # Execute controller
            response = await self.controller_engine.execute(
                controller_match.route,
                request,
                controller_match.params,
                di_container,
            )
        except Exception as e:
            self.logger.error(f"Error executing controller: {e}", exc_info=True)
            response = Response.json(
                {"error": "Internal server error"},
                status=500,
            )
        
        await response.send_asgi(send)
    
    async def handle_websocket(self, scope: dict, receive: callable, send: callable):
        """Handle WebSocket connection."""
        # WebSocket support - basic accept/close for now
        await send({"type": "websocket.accept"})
        
        while True:
            message = await receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            elif message["type"] == "websocket.receive":
                # Echo back for now
                text = message.get("text")
                if text:
                    await send({
                        "type": "websocket.send",
                        "text": text,
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
