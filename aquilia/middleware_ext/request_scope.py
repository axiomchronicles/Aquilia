"""
Request Scope Middleware - Creates request-scoped DI container per request.

This middleware is critical for the integration between DI and request handling.
It creates a child container with request scope for each incoming request,
enabling request-scoped services and proper lifecycle management.
"""

from typing import Any, Callable, Awaitable, Optional
from aquilia.di import Container


class RequestScopeMiddleware:
    """
    ASGI middleware that creates request-scoped DI container.
    
    For each request:
    1. Gets app-scoped container from runtime registry
    2. Creates child container with request scope
    3. Stores in request.state.di_container
    4. Executes request handler
    5. Disposes request container
    
    Usage:
        app.add_middleware(RequestScopeMiddleware, runtime=runtime)
    """
    
    def __init__(self, app: Callable, runtime: Any):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application callable
            runtime: RuntimeRegistry instance with di_containers
        """
        self.app = app
        self.runtime = runtime
    
    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """
        ASGI middleware entrypoint.
        
        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            # Only handle HTTP requests
            await self.app(scope, receive, send)
            return
        
        # Get app name from scope (set by router or app selector)
        app_name = scope.get("app_name", "default")
        
        # Get app-scoped container
        app_container = self.runtime.di_containers.get(app_name)
        
        if app_container is None:
            # No DI container for this app, proceed without DI
            await self.app(scope, receive, send)
            return
        
        # Create request-scoped child container for proper isolation
        request_container = app_container.create_request_scope()
        
        # Store in scope for handler access
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["di_container"] = request_container
        scope["state"]["app_container"] = app_container
        scope["state"]["runtime"] = self.runtime
        
        try:
            # Execute request
            await self.app(scope, receive, send)
        finally:
            # Cleanup request-scoped container
            # This ensures proper disposal of request-scoped services
            if request_container is not app_container:
                if hasattr(request_container, "shutdown"):
                    await request_container.shutdown()
                elif hasattr(request_container, "dispose"):
                    request_container.dispose()


class SimplifiedRequestScopeMiddleware:
    """
    Simplified middleware for frameworks with request objects.
    
    This is a higher-level version that works with frameworks
    providing request/response objects instead of raw ASGI.
    
    Usage:
        @app.middleware("http")
        async def add_di(request, call_next):
            return await SimplifiedRequestScopeMiddleware(runtime)(request, call_next)
    """
    
    def __init__(self, runtime: Any):
        """
        Initialize simplified middleware.
        
        Args:
            runtime: RuntimeRegistry instance
        """
        self.runtime = runtime
    
    async def __call__(
        self,
        request: Any,
        call_next: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """
        Middleware handler for request/response pattern.
        
        Args:
            request: Request object with .state attribute
            call_next: Next middleware/handler callable
            
        Returns:
            Response object
        """
        # Get app name from request
        app_name = getattr(request.state, "app_name", "default")
        
        # Get app-scoped container
        app_container = self.runtime.di_containers.get(app_name)
        
        if app_container is None:
            # No DI, proceed without container
            return await call_next(request)
        
        # Create request-scoped child container for proper isolation
        request_container = app_container.create_request_scope()
        
        # Store in request state
        request.state.di_container = request_container
        request.state.app_container = app_container
        request.state.runtime = self.runtime
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup request-scoped container
            if request_container is not app_container:
                if hasattr(request_container, "shutdown"):
                    await request_container.shutdown()
                elif hasattr(request_container, "dispose"):
                    request_container.dispose()


def create_request_scope_middleware(runtime: Any) -> Callable:
    """
    Factory function to create request scope middleware.
    
    Args:
        runtime: RuntimeRegistry instance
        
    Returns:
        Middleware callable
        
    Example:
        middleware = create_request_scope_middleware(runtime)
        app.add_middleware(middleware)
    """
    async def middleware(request, call_next):
        return await SimplifiedRequestScopeMiddleware(runtime)(request, call_next)
    
    return middleware
