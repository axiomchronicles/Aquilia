"""
AquilAuth - Session Integration

Integration with Aquilia Sessions for auth state management.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from ..core import Identity


# ============================================================================
# Auth Session
# ============================================================================


class AuthSession:
    """
    Authentication session.

    Binds tokens to sessions and manages session lifecycle.
    """

    def __init__(
        self,
        session_id: str,
        identity_id: str,
        created_at: datetime,
        expires_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        self.identity_id = identity_id
        self.created_at = created_at
        self.expires_at = expires_at
        self.last_activity = created_at
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "identity_id": self.identity_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthSession:
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            identity_id=data["identity_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# Session Store
# ============================================================================


class MemorySessionStore:
    """In-memory session store for development/testing."""

    def __init__(self):
        self._sessions: dict[str, AuthSession] = {}

    async def create_session(
        self,
        identity_id: str,
        ttl_seconds: int = 3600,
        metadata: dict[str, Any] | None = None,
    ) -> AuthSession:
        """
        Create new session.

        Args:
            identity_id: Identity ID
            ttl_seconds: Session lifetime in seconds
            metadata: Session metadata

        Returns:
            Created session
        """
        session_id = f"sess_{secrets.token_urlsafe(32)}"
        now = datetime.utcnow()

        session = AuthSession(
            session_id=session_id,
            identity_id=identity_id,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            metadata=metadata,
        )

        self._sessions[session_id] = session
        return session

    async def get_session(self, session_id: str) -> AuthSession | None:
        """Get session by ID."""
        session = self._sessions.get(session_id)

        if session and session.is_expired():
            # Clean up expired session
            del self._sessions[session_id]
            return None

        return session

    async def update_session(self, session: AuthSession) -> None:
        """Update session."""
        self._sessions[session.session_id] = session

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_sessions(
        self, identity_id: str
    ) -> list[AuthSession]:
        """List all active sessions for identity."""
        return [
            s
            for s in self._sessions.values()
            if s.identity_id == identity_id and not s.is_expired()
        ]

    async def delete_all_sessions(self, identity_id: str) -> int:
        """Delete all sessions for identity."""
        sessions_to_delete = [
            sid
            for sid, s in self._sessions.items()
            if s.identity_id == identity_id
        ]

        for sid in sessions_to_delete:
            del self._sessions[sid]

        return len(sessions_to_delete)


# ============================================================================
# Session Manager
# ============================================================================


class SessionManager:
    """
    Session manager for authentication.

    Creates sessions on login, rotates on privilege escalation.
    """

    def __init__(
        self,
        session_store: MemorySessionStore,
        default_ttl: int = 3600,
        max_sessions_per_user: int = 10,
    ):
        """
        Initialize session manager.

        Args:
            session_store: Session storage backend
            default_ttl: Default session TTL in seconds
            max_sessions_per_user: Max concurrent sessions per user
        """
        self.session_store = session_store
        self.default_ttl = default_ttl
        self.max_sessions_per_user = max_sessions_per_user

    async def create_session(
        self,
        identity: Identity,
        metadata: dict[str, Any] | None = None,
    ) -> AuthSession:
        """
        Create new session for identity.

        Args:
            identity: Identity
            metadata: Session metadata (IP, user agent, etc.)

        Returns:
            Created session
        """
        # Check session limit
        existing = await self.session_store.list_sessions(identity.id)
        if len(existing) >= self.max_sessions_per_user:
            # Delete oldest session
            oldest = min(existing, key=lambda s: s.created_at)
            await self.session_store.delete_session(oldest.session_id)

        # Create session
        return await self.session_store.create_session(
            identity_id=identity.id,
            ttl_seconds=self.default_ttl,
            metadata=metadata,
        )

    async def get_session(self, session_id: str) -> AuthSession | None:
        """Get session and update activity."""
        session = await self.session_store.get_session(session_id)

        if session:
            session.update_activity()
            await self.session_store.update_session(session)

        return session

    async def extend_session(
        self, session_id: str, additional_seconds: int = 3600
    ) -> bool:
        """
        Extend session expiration.

        Args:
            session_id: Session ID
            additional_seconds: Seconds to add to expiration

        Returns:
            True if extended
        """
        session = await self.session_store.get_session(session_id)
        if not session:
            return False

        session.expires_at += timedelta(seconds=additional_seconds)
        await self.session_store.update_session(session)
        return True

    async def rotate_session(
        self, old_session_id: str
    ) -> AuthSession | None:
        """
        Rotate session ID (privilege escalation).

        Creates new session with same data, deletes old one.

        Args:
            old_session_id: Old session ID

        Returns:
            New session
        """
        old_session = await self.session_store.get_session(old_session_id)
        if not old_session:
            return None

        # Create new session with same data
        new_session = await self.session_store.create_session(
            identity_id=old_session.identity_id,
            ttl_seconds=int(
                (old_session.expires_at - datetime.utcnow()).total_seconds()
            ),
            metadata=old_session.metadata,
        )

        # Delete old session
        await self.session_store.delete_session(old_session_id)

        return new_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete session (logout)."""
        return await self.session_store.delete_session(session_id)

    async def delete_all_sessions(self, identity_id: str) -> int:
        """Delete all sessions for identity (logout all devices)."""
        return await self.session_store.delete_all_sessions(identity_id)


# ============================================================================
# Auth Session Middleware
# ============================================================================


class AuthSessionMiddleware:
    """
    Middleware for session-based authentication.

    Integrates with Aquilia middleware pipeline.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        cookie_name: str = "aquilia_session",
        cookie_secure: bool = True,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ):
        """
        Initialize session middleware.

        Args:
            session_manager: Session manager
            cookie_name: Session cookie name
            cookie_secure: Require HTTPS
            cookie_httponly: HttpOnly flag
            cookie_samesite: SameSite policy
        """
        self.session_manager = session_manager
        self.cookie_name = cookie_name
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite

    async def __call__(self, request: Any, next_handler: Any) -> Any:
        """
        Process request with session.

        Args:
            request: HTTP request
            next_handler: Next middleware/handler

        Returns:
            Response
        """
        # Get session ID from cookie
        session_id = request.cookies.get(self.cookie_name)

        session = None
        if session_id:
            # Load session
            session = await self.session_manager.get_session(session_id)

        # Attach session to request
        request.session = session

        # Call next handler
        response = await next_handler(request)

        # Set session cookie if session was created
        if hasattr(request, "_new_session_id"):
            self._set_session_cookie(response, request._new_session_id)

        return response

    def _set_session_cookie(self, response: Any, session_id: str) -> None:
        """Set session cookie on response."""
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
