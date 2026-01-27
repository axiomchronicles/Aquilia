"""
WebSocket Middleware - Per-message processing pipeline

Similar to HTTP middleware but for WebSocket messages.
"""

from __future__ import annotations

from typing import Callable, Awaitable, Optional, TYPE_CHECKING, Any
import logging

if TYPE_CHECKING:
    from .connection import Connection
    from .envelope import MessageEnvelope

logger = logging.getLogger("aquilia.sockets.middleware")


# Type aliases (using Any to avoid runtime circular import)
MessageHandler = Callable[[Any, Any], Awaitable[Optional[dict]]]
SocketMiddleware = Callable[[Any, Any, MessageHandler], Awaitable[Optional[dict]]]


class MessageValidationMiddleware:
    """
    Message validation middleware.
    
    Validates message format and size.
    """
    
    def __init__(
        self,
        max_message_size: int = 65536,  # 64KB
        max_payload_size: int = 32768,  # 32KB
    ):
        """
        Initialize validation middleware.
        
        Args:
            max_message_size: Max total message size (bytes)
            max_payload_size: Max payload size (bytes)
        """
        self.max_message_size = max_message_size
        self.max_payload_size = max_payload_size
    
    async def __call__(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
        next: MessageHandler,
    ) -> Optional[dict]:
        """Validate message."""
        from .faults import WS_PAYLOAD_TOO_LARGE, WS_MESSAGE_INVALID
        import json
        
        # Validate envelope structure
        if not envelope.event:
            raise WS_MESSAGE_INVALID("Missing event name")
        
        # Check payload size
        payload_str = json.dumps(envelope.payload)
        payload_size = len(payload_str.encode("utf-8"))
        
        if payload_size > self.max_payload_size:
            raise WS_PAYLOAD_TOO_LARGE(payload_size, self.max_payload_size)
        
        # Call next handler
        return await next(conn, envelope)


class RateLimitMiddleware:
    """
    Rate limiting middleware.
    
    Tracks message rate per connection.
    """
    
    def __init__(
        self,
        messages_per_second: int = 10,
        burst: int = 20,
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            messages_per_second: Sustained rate limit
            burst: Burst allowance
        """
        self.messages_per_second = messages_per_second
        self.burst = burst
        self._tokens = {}
        self._last_refill = {}
    
    async def __call__(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
        next: MessageHandler,
    ) -> Optional[dict]:
        """Check rate limit."""
        from .faults import WS_RATE_LIMIT_EXCEEDED
        import time
        
        now = time.time()
        conn_id = conn.connection_id
        
        # Initialize token bucket
        if conn_id not in self._tokens:
            self._tokens[conn_id] = self.burst
            self._last_refill[conn_id] = now
        
        # Refill tokens
        elapsed = now - self._last_refill[conn_id]
        refill = elapsed * self.messages_per_second
        self._tokens[conn_id] = min(self.burst, self._tokens[conn_id] + refill)
        self._last_refill[conn_id] = now
        
        # Check tokens
        if self._tokens[conn_id] < 1:
            raise WS_RATE_LIMIT_EXCEEDED(self.messages_per_second)
        
        # Consume token
        self._tokens[conn_id] -= 1
        
        # Call next handler
        return await next(conn, envelope)


class LoggingMiddleware:
    """
    Logging middleware.
    
    Logs all messages for debugging.
    """
    
    def __init__(self, log_payloads: bool = False):
        """
        Initialize logging middleware.
        
        Args:
            log_payloads: Include payloads in logs
        """
        self.log_payloads = log_payloads
    
    async def __call__(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
        next: MessageHandler,
    ) -> Optional[dict]:
        """Log message."""
        identity_id = conn.identity.id if conn.identity else "anonymous"
        
        if self.log_payloads:
            logger.debug(
                f"Message from {identity_id} ({conn.connection_id}): "
                f"event={envelope.event} payload={envelope.payload}"
            )
        else:
            logger.debug(
                f"Message from {identity_id} ({conn.connection_id}): "
                f"event={envelope.event}"
            )
        
        # Call next handler
        result = await next(conn, envelope)
        
        return result


class MetricsMiddleware:
    """
    Metrics collection middleware.
    
    Records message metrics.
    """
    
    def __init__(self):
        """Initialize metrics middleware."""
        self.message_count = 0
        self.error_count = 0
        self.event_counts = {}
    
    async def __call__(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
        next: MessageHandler,
    ) -> Optional[dict]:
        """Record metrics."""
        import time
        
        self.message_count += 1
        self.event_counts[envelope.event] = self.event_counts.get(envelope.event, 0) + 1
        
        start = time.time()
        
        try:
            result = await next(conn, envelope)
            return result
        except Exception:
            self.error_count += 1
            raise
        finally:
            elapsed = time.time() - start
            logger.debug(f"Message {envelope.event} took {elapsed*1000:.2f}ms")


class MiddlewareChain:
    """
    Middleware chain builder.
    
    Composes multiple middleware into a single handler.
    """
    
    def __init__(self):
        """Initialize middleware chain."""
        self.middlewares: list[SocketMiddleware] = []
    
    def add(self, middleware: SocketMiddleware):
        """Add middleware to chain."""
        self.middlewares.append(middleware)
    
    def build(self, final_handler: MessageHandler) -> MessageHandler:
        """Build middleware chain."""
        handler = final_handler
        
        # Wrap in reverse order
        for middleware in reversed(self.middlewares):
            handler = self._wrap(middleware, handler)
        
        return handler
    
    def _wrap(
        self,
        middleware: SocketMiddleware,
        next_handler: MessageHandler,
    ) -> MessageHandler:
        """Wrap handler with middleware."""
        async def wrapped(conn: Connection, envelope: MessageEnvelope):
            return await middleware(conn, envelope, next_handler)
        
        return wrapped
