"""
AquilaSessions - Transport adapters.

Handles session ID extraction and injection across different transports:
- CookieTransport: HTTP cookies (most common)
- HeaderTransport: Custom headers (APIs, mobile apps)
- TokenTransport: Bearer tokens (future)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.response import Response
    from .core import Session, SessionID
    from .policy import TransportPolicy


# ============================================================================
# SessionTransport Protocol
# ============================================================================

class SessionTransport(Protocol):
    """
    Abstract transport interface for session ID delivery.
    
    Transports are responsible for:
    - Extracting session ID from requests
    - Injecting session ID into responses
    - Clearing session ID from responses
    
    Transports do NOT handle:
    - Session validation (that's SessionEngine)
    - Session creation (that's SessionEngine)
    - Session persistence (that's SessionStore)
    """
    
    def extract(self, request: Request) -> str | None:
        """
        Extract session ID from request.
        
        Args:
            request: Incoming request
            
        Returns:
            Session ID string if found, None otherwise
        """
        ...
    
    def inject(self, response: Response, session: Session) -> None:
        """
        Inject session ID into response.
        
        Args:
            response: Outgoing response
            session: Session to inject
        """
        ...
    
    def clear(self, response: Response) -> None:
        """
        Clear session ID from response (logout).
        
        Args:
            response: Outgoing response
        """
        ...


# ============================================================================
# CookieTransport - HTTP Cookies
# ============================================================================

class CookieTransport:
    """
    Cookie-based session transport.
    
    Features:
    - HttpOnly flag (XSS protection)
    - Secure flag (HTTPS only)
    - SameSite policy (CSRF protection)
    - Configurable path and domain
    - Expiry based on session TTL
    
    Example:
        >>> policy = TransportPolicy(
        ...     adapter="cookie",
        ...     cookie_name="aquilia_session",
        ...     cookie_httponly=True,
        ...     cookie_secure=True,
        ...     cookie_samesite="lax"
        ... )
        >>> transport = CookieTransport(policy)
        >>> session_id = transport.extract(request)
    """
    
    def __init__(self, policy: TransportPolicy):
        """
        Initialize cookie transport.
        
        Args:
            policy: Transport policy with cookie settings
        """
        self.policy = policy
        self.cookie_name = policy.cookie_name
    
    def extract(self, request: Request) -> str | None:
        """Extract session ID from cookie."""
        # Get cookies from request
        cookie_header = request.header("cookie")
        if not cookie_header:
            return None
        
        # Parse cookies (simple parser)
        cookies = self._parse_cookies(cookie_header)
        return cookies.get(self.cookie_name)
    
    def inject(self, response: Response, session: Session) -> None:
        """Inject session ID as cookie."""
        session_id = str(session.id)
        
        # Build cookie string
        cookie_parts = [f"{self.cookie_name}={session_id}"]
        
        # Add path
        if self.policy.cookie_path:
            cookie_parts.append(f"Path={self.policy.cookie_path}")
        
        # Add domain
        if self.policy.cookie_domain:
            cookie_parts.append(f"Domain={self.policy.cookie_domain}")
        
        # Add expiry (if session has expiry)
        if session.expires_at:
            # Calculate Max-Age in seconds
            now = datetime.utcnow()
            max_age = int((session.expires_at - now).total_seconds())
            if max_age > 0:
                cookie_parts.append(f"Max-Age={max_age}")
                # Also add Expires for compatibility
                expires_str = session.expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                cookie_parts.append(f"Expires={expires_str}")
        
        # Add security flags
        if self.policy.cookie_httponly:
            cookie_parts.append("HttpOnly")
        
        if self.policy.cookie_secure:
            cookie_parts.append("Secure")
        
        # Add SameSite
        if self.policy.cookie_samesite:
            samesite_value = self.policy.cookie_samesite.capitalize()
            cookie_parts.append(f"SameSite={samesite_value}")
        
        # Build final cookie string
        cookie_str = "; ".join(cookie_parts)
        
        # Add Set-Cookie header
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            max_age=max_age if session.expires_at else None,
            path=self.policy.cookie_path,
            domain=self.policy.cookie_domain,
            secure=self.policy.cookie_secure,
            httponly=self.policy.cookie_httponly,
            samesite=self.policy.cookie_samesite,
        )
    
    def clear(self, response: Response) -> None:
        """Clear session cookie (logout)."""
        # Set cookie with Max-Age=0 to delete
        cookie_parts = [
            f"{self.cookie_name}=deleted",
            "Max-Age=0",
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT",
        ]
        
        if self.policy.cookie_path:
            cookie_parts.append(f"Path={self.policy.cookie_path}")
        
        if self.policy.cookie_domain:
            cookie_parts.append(f"Domain={self.policy.cookie_domain}")
        
        cookie_str = "; ".join(cookie_parts)
        
        # Use response's delete_cookie if available
        if hasattr(response, 'delete_cookie'):
            response.delete_cookie(
                key=self.cookie_name,
                path=self.policy.cookie_path,
                domain=self.policy.cookie_domain,
            )
        else:
            # Fallback: add Set-Cookie header manually
            response.headers["Set-Cookie"] = cookie_str
    
    @staticmethod
    def _parse_cookies(cookie_header: str) -> dict[str, str]:
        """
        Parse cookie header into dict.
        
        Args:
            cookie_header: Cookie header value
            
        Returns:
            Dict of cookie name -> value
        """
        cookies = {}
        
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" in part:
                name, value = part.split("=", 1)
                cookies[name.strip()] = value.strip()
        
        return cookies


# ============================================================================
# HeaderTransport - Custom Header
# ============================================================================

class HeaderTransport:
    """
    Header-based session transport.
    
    Used for:
    - API authentication
    - Mobile app sessions
    - Service-to-service communication
    
    Features:
    - Custom header name (e.g., X-Session-ID, X-API-Token)
    - No cookie limitations
    - Works with CORS
    
    Example:
        >>> policy = TransportPolicy(
        ...     adapter="header",
        ...     header_name="X-Session-ID"
        ... )
        >>> transport = HeaderTransport(policy)
        >>> session_id = transport.extract(request)
    """
    
    def __init__(self, policy: TransportPolicy):
        """
        Initialize header transport.
        
        Args:
            policy: Transport policy with header settings
        """
        self.policy = policy
        self.header_name = policy.header_name
    
    def extract(self, request: Request) -> str | None:
        """Extract session ID from header."""
        return request.header(self.header_name)
    
    def inject(self, response: Response, session: Session) -> None:
        """Inject session ID as header."""
        session_id = str(session.id)
        response.headers[self.header_name] = session_id
    
    def clear(self, response: Response) -> None:
        """Clear session header (remove it)."""
        # Remove header if present
        if self.header_name in response.headers:
            del response.headers[self.header_name]


# ============================================================================
# Transport Factory
# ============================================================================

def create_transport(policy: TransportPolicy) -> CookieTransport | HeaderTransport:
    """
    Create transport adapter from policy.
    
    Args:
        policy: Transport policy
        
    Returns:
        Transport adapter instance
        
    Raises:
        ValueError: If adapter type is unsupported
    """
    if policy.adapter == "cookie":
        return CookieTransport(policy)
    elif policy.adapter == "header":
        return HeaderTransport(policy)
    elif policy.adapter == "token":
        # Future: BearerTokenTransport
        raise NotImplementedError("Token transport not yet implemented")
    else:
        raise ValueError(f"Unsupported transport adapter: {policy.adapter}")
