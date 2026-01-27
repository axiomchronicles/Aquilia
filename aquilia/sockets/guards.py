"""
WebSocket Guards - Security and validation guards

Guards run at handshake and/or per-message.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .connection import Connection, ConnectionScope
    from .envelope import MessageEnvelope
    from aquilia.auth.core import Identity
    from aquilia.sessions.core import Session

from .faults import WS_AUTH_REQUIRED, WS_FORBIDDEN, WS_ORIGIN_NOT_ALLOWED

logger = logging.getLogger("aquilia.sockets.guards")


class SocketGuard:
    """
    Base class for WebSocket guards.
    
    Guards can run at:
    - Handshake (before connection established)
    - Per-message (before handler execution)
    """
    
    async def check_handshake(
        self,
        scope: ConnectionScope,
        identity: Optional[Identity],
        session: Optional[Session],
    ) -> bool:
        """
        Check handshake authorization.
        
        Args:
            scope: Connection scope (path, headers, etc.)
            identity: Authenticated identity (if any)
            session: Session (if any)
            
        Returns:
            True to allow, False to reject
            
        Raises:
            SocketFault to reject with specific error
        """
        return True
    
    async def check_message(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
    ) -> bool:
        """
        Check message authorization.
        
        Args:
            conn: Active connection
            envelope: Incoming message
            
        Returns:
            True to allow, False to reject
            
        Raises:
            SocketFault to reject with specific error
        """
        return True


class HandshakeAuthGuard(SocketGuard):
    """
    Handshake authentication guard.
    
    Requires valid authentication at handshake time.
    Supports:
    - Authorization header (Bearer token)
    - Session cookie
    - Query string token (?token=...)
    """
    
    def __init__(
        self,
        *,
        require_identity: bool = True,
        require_session: bool = False,
        allowed_identity_types: Optional[list[str]] = None,
    ):
        """
        Initialize handshake auth guard.
        
        Args:
            require_identity: Require authenticated identity
            require_session: Require active session
            allowed_identity_types: Whitelist of identity types
        """
        self.require_identity = require_identity
        self.require_session = require_session
        self.allowed_identity_types = allowed_identity_types
    
    async def check_handshake(
        self,
        scope: ConnectionScope,
        identity: Optional[Identity],
        session: Optional[Session],
    ) -> bool:
        """Check handshake authentication."""
        # Check identity requirement
        if self.require_identity and not identity:
            raise WS_AUTH_REQUIRED()
        
        # Check session requirement
        if self.require_session and not session:
            raise WS_FORBIDDEN("Session required")
        
        # Check identity type
        if identity and self.allowed_identity_types:
            if identity.type.value not in self.allowed_identity_types:
                raise WS_FORBIDDEN(f"Identity type {identity.type.value} not allowed")
        
        # Check identity status
        if identity and not identity.is_active():
            raise WS_FORBIDDEN("Identity is not active")
        
        return True


class OriginGuard(SocketGuard):
    """
    Origin validation guard.
    
    Checks Origin header against whitelist.
    """
    
    def __init__(self, allowed_origins: list[str]):
        """
        Initialize origin guard.
        
        Args:
            allowed_origins: List of allowed origins (with wildcards)
                Example: ["https://example.com", "https://*.example.com"]
        """
        self.allowed_origins = allowed_origins
    
    async def check_handshake(
        self,
        scope: ConnectionScope,
        identity: Optional[Identity],
        session: Optional[Session],
    ) -> bool:
        """Check origin header."""
        origin = scope.headers.get("origin", "")
        
        if not origin:
            # No origin header - allow (same-origin or non-browser)
            return True
        
        # Check against whitelist
        if not self._is_origin_allowed(origin):
            raise WS_ORIGIN_NOT_ALLOWED(origin)
        
        return True
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin matches whitelist."""
        for allowed in self.allowed_origins:
            if allowed == "*":
                return True
            
            if allowed.startswith("*."):
                # Wildcard subdomain
                domain = allowed[2:]
                if origin.endswith(domain):
                    return True
            else:
                # Exact match
                if origin == allowed:
                    return True
        
        return False


class MessageAuthGuard(SocketGuard):
    """
    Per-message authentication guard.
    
    Validates authentication for each message.
    Useful for long-lived connections.
    """
    
    def __init__(self, *, check_interval: int = 300):
        """
        Initialize message auth guard.
        
        Args:
            check_interval: Seconds between auth checks
        """
        self.check_interval = check_interval
        self._last_check = {}
    
    async def check_message(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
    ) -> bool:
        """Check message authentication."""
        import time
        
        now = time.time()
        last = self._last_check.get(conn.connection_id, 0)
        
        # Check periodically
        if now - last > self.check_interval:
            if not conn.identity:
                raise WS_AUTH_REQUIRED()
            
            if not conn.identity.is_active():
                raise WS_FORBIDDEN("Identity is not active")
            
            self._last_check[conn.connection_id] = now
        
        return True


class RateLimitGuard(SocketGuard):
    """
    Rate limiting guard.
    
    Limits messages per second per connection.
    """
    
    def __init__(self, messages_per_second: int = 10):
        """
        Initialize rate limit guard.
        
        Args:
            messages_per_second: Max messages per second
        """
        self.messages_per_second = messages_per_second
        self._message_counts = {}
        self._window_start = {}
    
    async def check_message(
        self,
        conn: Connection,
        envelope: MessageEnvelope,
    ) -> bool:
        """Check rate limit."""
        from .faults import WS_RATE_LIMIT_EXCEEDED
        import time
        
        now = time.time()
        conn_id = conn.connection_id
        
        # Initialize or reset window
        if conn_id not in self._window_start or now - self._window_start[conn_id] >= 1.0:
            self._window_start[conn_id] = now
            self._message_counts[conn_id] = 0
        
        # Increment count
        self._message_counts[conn_id] += 1
        
        # Check limit
        if self._message_counts[conn_id] > self.messages_per_second:
            raise WS_RATE_LIMIT_EXCEEDED(self.messages_per_second)
        
        return True
