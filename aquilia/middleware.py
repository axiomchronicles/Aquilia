"""
Middleware system - Composable, async-first middleware with effect awareness.
"""

from __future__ import annotations

from typing import Callable, Awaitable, Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass
import time
import uuid
import traceback
import logging

from .request import Request
from .response import Response, InternalError
from .faults import Fault, FaultDomain

if TYPE_CHECKING:
    from .controller.base import RequestCtx

# Type alias for middleware - use string annotation to avoid circular import
Handler = Callable[[Request, "RequestCtx"], Awaitable[Response]]
Middleware = Callable[[Request, "RequestCtx", Handler], Awaitable[Response]]


@dataclass
class MiddlewareDescriptor:
    """Descriptor for middleware registration."""
    middleware: Middleware
    scope: str  # "global", "app:name", "controller:name", "route:pattern"
    priority: int
    name: str


class MiddlewareStack:
    """
    Manages middleware stack with deterministic ordering.
    Order: Global < App < Controller < Route, then by priority.
    """
    
    def __init__(self):
        self.middlewares: List[MiddlewareDescriptor] = []
        self._sorted = True  # Track if sorting is needed
    
    def add(
        self,
        middleware: Middleware,
        scope: str = "global",
        priority: int = 50,
        name: Optional[str] = None,
    ):
        """Add middleware to stack."""
        if name is None:
            name = middleware.__name__ if hasattr(middleware, "__name__") else "middleware"
        
        descriptor = MiddlewareDescriptor(
            middleware=middleware,
            scope=scope,
            priority=priority,
            name=name,
        )
        
        self.middlewares.append(descriptor)
        self._sorted = False  # Defer sorting until build_handler()
    
    def _sort_middlewares(self):
        """Sort middlewares by scope and priority."""
        scope_order = {"global": 0, "app": 1, "controller": 2, "route": 3}
        
        def sort_key(desc: MiddlewareDescriptor):
            scope_type = desc.scope.split(":")[0]
            scope_rank = scope_order.get(scope_type, 99)
            return (scope_rank, desc.priority)
        
        self.middlewares.sort(key=sort_key)
    
    def build_handler(self, final_handler: Handler) -> Handler:
        """Build middleware chain wrapping the final handler."""
        # Sort only if needed (deferred from add())
        if not self._sorted:
            self._sort_middlewares()
            self._sorted = True
        
        handler = final_handler
        
        # Wrap in reverse order so first middleware is outermost
        for desc in reversed(self.middlewares):
            handler = self._wrap_middleware(desc.middleware, handler)
        
        return handler
    
    def _wrap_middleware(self, middleware: Middleware, next_handler: Handler) -> Handler:
        """Wrap a handler with middleware."""
        async def wrapped(request: Request, ctx: RequestCtx) -> Response:
            return await middleware(request, ctx, next_handler)
        
        return wrapped


# Default middleware implementations

class RequestIdMiddleware:
    """Adds unique request ID to each request.

    Uses os.urandom (16 bytes hex) which is ~4× faster than uuid.uuid4().
    Scans raw ASGI headers directly to avoid triggering full Headers parsing.
    """

    def __init__(self, header_name: str = "X-Request-ID"):
        self.header_name = header_name
        self._header_name_bytes = header_name.lower().encode("latin-1")
        import os
        self._urandom = os.urandom

    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        # Scan raw ASGI headers directly (avoids building Headers object)
        request_id = None
        target = self._header_name_bytes
        for name, value in request.scope.get("headers", ()):
            if name == target:
                request_id = value.decode("latin-1")
                break
        
        if not request_id:
            request_id = self._urandom(16).hex()

        request.state["request_id"] = request_id
        ctx.request_id = request_id

        response = await next(request, ctx)
        response.headers[self.header_name] = request_id
        return response


class ExceptionMiddleware:
    """Catches exceptions and converts them to error responses.

    When ``debug=True`` and the request ``Accept`` header includes
    ``text/html``, renders beautiful React-style debug pages using the
    MongoDB Atlas color palette with dark/light mode support.
    Otherwise, returns structured JSON error responses.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger("aquilia.exceptions")
    
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wants_html(self, request: Request) -> bool:
        """Check if the client prefers an HTML response."""
        try:
            accept = ""
            if hasattr(request, 'headers'):
                h = request.headers
                if hasattr(h, 'get'):
                    accept = h.get("accept", "")
                elif isinstance(h, dict):
                    accept = h.get("accept", "") or h.get("Accept", "")
            return "text/html" in accept
        except Exception:
            return False

    def _html_response(self, body: str, status: int) -> Response:
        """Build an HTML response from rendered page string."""
        return Response(
            content=body.encode("utf-8"),
            status=status,
            headers={"content-type": "text/html; charset=utf-8"},
        )

    def _get_version(self) -> str:
        """Get Aquilia version string."""
        try:
            from aquilia import __version__
            return __version__
        except Exception:
            return ""

    def _render_debug_exception(self, exc: BaseException, request: Request) -> Response:
        """Render a full debug exception page."""
        from .debug.pages import render_debug_exception_page
        html_body = render_debug_exception_page(
            exc, request, aquilia_version=self._get_version(),
        )
        return self._html_response(html_body, 500)

    def _render_debug_http_error(
        self, status: int, message: str, detail: str, request: Request,
    ) -> Response:
        """Render a styled HTTP error page."""
        from .debug.pages import render_http_error_page
        html_body = render_http_error_page(
            status, message, detail, request,
            aquilia_version=self._get_version(),
        )
        return self._html_response(html_body, status)

    # ------------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------------

    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        try:
            return await next(request, ctx)
        
        except ValueError as e:
            # Client error — 400
            self.logger.warning(f"ValueError: {e}")
            if self.debug and self._wants_html(request):
                return self._render_debug_http_error(400, "Bad Request", str(e), request)
            return Response.json(
                {"error": str(e)},
                status=400,
            )
        
        except PermissionError as e:
            # Forbidden — 403
            self.logger.warning(f"PermissionError: {e}")
            if self.debug and self._wants_html(request):
                return self._render_debug_http_error(403, "Forbidden", str(e), request)
            return Response.json(
                {"error": "Forbidden"},
                status=403,
            )

        except Fault as e:
            # Typed Fault
            # Authentication faults (unauthenticated) → 401
            # Authorization faults (authenticated but forbidden) → 403
            _UNAUTHENTICATED_CODES = {
                "AUTH_010",           # AUTH_REQUIRED
                "AUTHENTICATION_REQUIRED",  # AuthenticationRequiredFault / session decorators
                "SESSION_REQUIRED",   # SessionRequiredFault
                "INVALID_CREDENTIALS", # Auth module login failure
            }
            _CONFLICT_CODES = {
                "USER_ALREADY_EXISTS",  # Auth module registration failure
            }
            
            status_map = {
                FaultDomain.ROUTING: 404,
                FaultDomain.SECURITY: 403,
                FaultDomain.IO: 502,
                FaultDomain.EFFECT: 503,
                FaultDomain.MODEL: 404,        # DB Not Found usually
                FaultDomain.SERIALIZATION: 400, # Validation error
                FaultDomain.CACHE: 502,
                FaultDomain.CONFIG: 500,
                FaultDomain.REGISTRY: 500,
                FaultDomain.DI: 500,
                FaultDomain.FLOW: 500,
                FaultDomain.SYSTEM: 500,
            }
            
            code = getattr(e, "code", None)
            if code in _UNAUTHENTICATED_CODES:
                status = 401
            elif code in _CONFLICT_CODES:
                status = 409
            elif code and ("NOT_FOUND" in code or "MISSING" in code):
                status = 404
            elif code and ("VALIDATION" in code or "INVALID" in code):
                status = 400
            elif str(e.domain) == "auth":  # Catch-all for our custom AUTH domain
                status = 401
            else:
                status = status_map.get(e.domain, 500)
            
            message = e.message if (e.public or self.debug) else "Internal server error"
            
            if status >= 500:
                self.logger.error(f"Fault {e.code}: {e.message}")
            else:
                self.logger.warning(f"Fault {e.code}: {e.message}")

            # Debug HTML page for Fault exceptions
            if self.debug and self._wants_html(request):
                if status >= 500:
                    return self._render_debug_exception(e, request)
                else:
                    return self._render_debug_http_error(status, e.code, message, request)
                
            return Response.json(
                {
                    "error": {
                        "code": e.code,
                        "message": message,
                        "domain": e.domain.value,
                    }
                },
                status=status,
            )
        
        except Exception as e:
            # Internal error — 500
            self.logger.error(f"Unhandled exception: {e}", exc_info=True)

            if self.debug and self._wants_html(request):
                return self._render_debug_exception(e, request)
            
            error_data = {"error": "Internal server error"}
            
            if self.debug:
                error_data["detail"] = str(e)
                error_data["traceback"] = traceback.format_exc()
            
            return Response.json(error_data, status=500)


class LoggingMiddleware:
    """Logs request/response with timing.

    Performance (v2):
    - Checks logger.isEnabledFor(INFO) once; skips all work if disabled.
    - Only formats strings when actually logging.
    - Skips per-request 'extra' dict allocation when not needed.
    """

    def __init__(self):
        self.logger = logging.getLogger("aquilia.requests")
        self._log_enabled: bool = True  # Updated lazily

    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        if not self.logger.isEnabledFor(logging.INFO):
            return await next(request, ctx)

        start = time.monotonic()
        response = await next(request, ctx)
        elapsed_ms = (time.monotonic() - start) * 1000.0

        self.logger.info(
            "%s %s - %d (%.1fms)",
            request.method, request.path, response.status, elapsed_ms,
        )

        if elapsed_ms > 1000:
            self.logger.warning(
                "Slow request: %s %s took %.1fms",
                request.method, request.path, elapsed_ms,
            )

        return response


class TimeoutMiddleware:
    """Enforces request timeout."""
    
    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout = timeout_seconds
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        import asyncio
        
        try:
            return await asyncio.wait_for(
                next(request, ctx),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return Response.json(
                {"error": "Request timeout"},
                status=504,
            )


class CORSMiddleware:
    """Handles CORS headers."""
    
    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        max_age: int = 3600,
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        # Handle preflight
        if request.method == "OPTIONS":
            return self._preflight_response(request)
        
        # Process request
        response = await next(request, ctx)
        
        # Add CORS headers
        origin = request.header("origin")
        if origin and self._is_allowed_origin(origin):
            response.headers["access-control-allow-origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["access-control-allow-origin"] = "*"
        
        if self.allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"
        
        return response
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        return "*" in self.allow_origins or origin in self.allow_origins
    
    def _preflight_response(self, request: Request) -> Response:
        """Handle OPTIONS preflight request."""
        headers = {
            "access-control-allow-methods": ", ".join(self.allow_methods),
            "access-control-allow-headers": ", ".join(self.allow_headers),
            "access-control-max-age": str(self.max_age),
        }
        
        origin = request.header("origin")
        if origin and self._is_allowed_origin(origin):
            headers["access-control-allow-origin"] = origin
        elif "*" in self.allow_origins:
            headers["access-control-allow-origin"] = "*"
        
        if self.allow_credentials:
            headers["access-control-allow-credentials"] = "true"
        
        return Response(b"", status=204, headers=headers)


class CompressionMiddleware:
    """Compresses response bodies."""
    
    def __init__(self, minimum_size: int = 500):
        self.minimum_size = minimum_size
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        response = await next(request, ctx)
        
        # Check if client accepts gzip
        accept_encoding = request.header("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Don't compress streaming responses
        if hasattr(response._content, "__aiter__"):
            return response
        
        # Get body
        body = response._encode_body(response._content)
        
        # Only compress if large enough
        if len(body) < self.minimum_size:
            return response
        
        # Compress
        import gzip
        compressed = gzip.compress(body)
        
        # Update response
        response._content = compressed
        response.headers["content-encoding"] = "gzip"
        response.headers["content-length"] = str(len(compressed))
        
        return response
