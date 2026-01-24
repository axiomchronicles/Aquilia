"""
AquilAuth - Aquilia Sessions Integration

Deep integration between AquilAuth and Aquilia Sessions.
Replaces the standalone AuthSession with native Aquilia Sessions.

This module provides:
- AuthPrincipal: Identity binding for sessions
- AuthSessionPolicy: Preconfigured policies for auth workflows
- SessionAuthManager: AuthManager that works with SessionEngine
- Session extension for auth data
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from aquilia.sessions import (
    Session,
    SessionEngine,
    SessionID,
    SessionPolicy,
    SessionPrincipal,
    SessionScope,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
)

if TYPE_CHECKING:
    from ..core import Identity
    from ..tokens import TokenClaims


# ============================================================================
# Auth Principal Extension
# ============================================================================


class AuthPrincipal(SessionPrincipal):
    """
    Authentication principal for Aquilia Sessions.
    
    Extends SessionPrincipal with auth-specific data.
    """
    
    def __init__(
        self,
        identity_id: str,
        tenant_id: str | None = None,
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        mfa_verified: bool = False,
    ):
        """
        Initialize auth principal.
        
        Args:
            identity_id: Identity ID
            tenant_id: Optional tenant ID
            roles: User roles
            scopes: OAuth scopes
            mfa_verified: Whether MFA was verified
        """
        super().__init__(
            kind="user",
            id=identity_id,
            attributes={
                "tenant_id": tenant_id,
                "roles": roles or [],
                "scopes": scopes or [],
                "mfa_verified": mfa_verified,
            }
        )
        self.tenant_id = tenant_id
        self.roles = roles or []
        self.scopes = scopes or []
        self.mfa_verified = mfa_verified
    
    @classmethod
    def from_identity(cls, identity: Identity) -> AuthPrincipal:
        """Create AuthPrincipal from Identity."""
        return cls(
            identity_id=identity.id,
            tenant_id=identity.tenant_id,
            roles=identity.get_attribute("roles", []),
            scopes=identity.get_attribute("scopes", []),
            mfa_verified=False,  # Set by MFA flow
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        data = super().to_dict()
        data.update({
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "scopes": self.scopes,
            "mfa_verified": self.mfa_verified,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthPrincipal:
        """Deserialize from dictionary."""
        return cls(
            identity_id=data["principal_id"],
            tenant_id=data.get("tenant_id"),
            roles=data.get("roles", []),
            scopes=data.get("scopes", []),
            mfa_verified=data.get("mfa_verified", False),
        )


# ============================================================================
# Session Extensions for Auth Data
# ============================================================================


def bind_identity(session: Session, identity: Identity) -> None:
    """
    Bind identity to session.
    
    Args:
        session: Aquilia session
        identity: Auth identity
    """
    # Set principal
    session.principal = AuthPrincipal.from_identity(identity)
    
    # Store identity data in session state
    session.state["identity_id"] = identity.identity_id
    session.state["tenant_id"] = identity.tenant_id
    session.state["roles"] = identity.roles
    session.state["scopes"] = identity.scopes
    session.state["status"] = identity.status.value
    session.state["attributes"] = identity.attributes


def bind_token_claims(session: Session, claims: TokenClaims) -> None:
    """
    Bind token claims to session.
    
    Args:
        session: Aquilia session
        claims: Token claims
    """
    session.state["token_claims"] = {
        "sub": claims.sub,
        "iss": claims.iss,
        "iat": claims.iat.isoformat() if claims.iat else None,
        "exp": claims.exp.isoformat() if claims.exp else None,
        "scopes": claims.scopes,
        "tenant_id": claims.tenant_id,
    }


def get_identity_id(session: Session) -> str | None:
    """Get identity ID from session."""
    return session.state.get("identity_id")


def get_tenant_id(session: Session) -> str | None:
    """Get tenant ID from session."""
    return session.state.get("tenant_id")


def get_roles(session: Session) -> list[str]:
    """Get roles from session."""
    return session.state.get("roles", [])


def get_scopes(session: Session) -> list[str]:
    """Get scopes from session."""
    return session.state.get("scopes", [])


def is_mfa_verified(session: Session) -> bool:
    """Check if MFA was verified for this session."""
    if session.principal and isinstance(session.principal, AuthPrincipal):
        return session.principal.mfa_verified
    return False


def set_mfa_verified(session: Session) -> None:
    """Mark session as MFA verified."""
    if session.principal and isinstance(session.principal, AuthPrincipal):
        session.principal.mfa_verified = True
    session.state["mfa_verified"] = True


# ============================================================================
# Preconfigured Auth Policies
# ============================================================================


def user_session_policy(
    ttl: timedelta = timedelta(days=7),
    idle_timeout: timedelta = timedelta(hours=1),
    max_sessions: int | None = 5,
    store_name: str = "redis",
) -> SessionPolicy:
    """
    Create policy for user web sessions.
    
    Args:
        ttl: Total session lifetime
        idle_timeout: Max idle time
        max_sessions: Max concurrent sessions per user
        store_name: SessionStore name
        
    Returns:
        Configured SessionPolicy
    """
    return SessionPolicy(
        name="auth_user",
        ttl=ttl,
        idle_timeout=idle_timeout,
        rotate_on_use=False,
        rotate_on_privilege_change=True,  # Rotate on MFA verification
        persistence=PersistencePolicy(
            enabled=True,
            store_name=store_name,
            write_through=True,
            compress=False,
        ),
        concurrency=ConcurrencyPolicy(
            max_sessions_per_principal=max_sessions,
            behavior_on_limit="evict_oldest",
        ),
        transport=TransportPolicy(
            adapter="cookie",
            cookie_name="aquilia_auth",
            cookie_httponly=True,
            cookie_secure=True,
            cookie_samesite="lax",
            cookie_path="/",
        ),
        scope="user",
    )


def api_session_policy(
    ttl: timedelta = timedelta(hours=1),
    max_sessions: int | None = None,
) -> SessionPolicy:
    """
    Create policy for API token sessions.
    
    Args:
        ttl: Token lifetime
        max_sessions: Max concurrent sessions (None for unlimited)
        
    Returns:
        Configured SessionPolicy
    """
    return SessionPolicy(
        name="auth_api",
        ttl=ttl,
        idle_timeout=None,  # No idle timeout for API tokens
        rotate_on_use=False,
        rotate_on_privilege_change=False,
        persistence=PersistencePolicy(
            enabled=True,
            store_name="redis",
            write_through=True,
            compress=False,
        ),
        concurrency=ConcurrencyPolicy(
            max_sessions_per_principal=max_sessions,
            behavior_on_limit="reject",  # Don't allow new API sessions
        ),
        transport=TransportPolicy(
            adapter="header",
            header_name="Authorization",  # Bearer token
        ),
        scope="user",
    )


def device_session_policy(
    ttl: timedelta = timedelta(days=90),
    idle_timeout: timedelta = timedelta(days=30),
) -> SessionPolicy:
    """
    Create policy for device (mobile app) sessions.
    
    Args:
        ttl: Total session lifetime
        idle_timeout: Max idle time
        
    Returns:
        Configured SessionPolicy
    """
    return SessionPolicy(
        name="auth_device",
        ttl=ttl,
        idle_timeout=idle_timeout,
        rotate_on_use=False,
        rotate_on_privilege_change=True,
        persistence=PersistencePolicy(
            enabled=True,
            store_name="redis",
            write_through=True,
            compress=False,
        ),
        concurrency=ConcurrencyPolicy(
            max_sessions_per_principal=10,  # Multiple devices
            behavior_on_limit="evict_oldest",
        ),
        transport=TransportPolicy(
            adapter="header",
            header_name="X-Device-Session",
        ),
        scope="device",
    )


# ============================================================================
# Session-Aware Auth Manager Helper
# ============================================================================


class SessionAuthBridge:
    """
    Bridge between AuthManager and SessionEngine.
    
    Coordinates authentication with session management.
    """
    
    def __init__(
        self,
        session_engine: SessionEngine,
    ):
        """
        Initialize session-auth bridge.
        
        Args:
            session_engine: Aquilia SessionEngine
        """
        self.session_engine = session_engine
    
    async def create_auth_session(
        self,
        identity: Identity,
        request: Any,
        token_claims: TokenClaims | None = None,
    ) -> Session:
        """
        Create authenticated session.
        
        Args:
            identity: Authenticated identity
            request: Request object
            token_claims: Optional token claims
            
        Returns:
            Created session with auth data bound
        """
        # Resolve session (will create new one)
        session = await self.session_engine.resolve(request)
        
        # Bind identity
        bind_identity(session, identity)
        
        # Bind token claims if provided
        if token_claims:
            bind_token_claims(session, token_claims)
        
        return session
    
    async def rotate_on_privilege_escalation(
        self,
        session: Session,
        response: Any,
    ) -> Session:
        """
        Rotate session ID after privilege escalation (e.g., MFA).
        
        Args:
            session: Current session
            response: Response object
            
        Returns:
            New session with rotated ID
        """
        # Rotate session ID
        new_session = await self.session_engine.rotate(session)
        
        # Emit to response
        await self.session_engine.commit(new_session, response)
        
        return new_session
    
    async def verify_and_extend(
        self,
        session: Session,
    ) -> bool:
        """
        Verify session is valid and extend if needed.
        
        Args:
            session: Session to verify
            
        Returns:
            True if valid, False otherwise
        """
        # SessionEngine already validated in resolve()
        # Just check if identity is bound
        identity_id = get_identity_id(session)
        return identity_id is not None
    
    async def logout(
        self,
        session: Session,
        response: Any,
    ) -> None:
        """
        Logout - destroy session.
        
        Args:
            session: Session to destroy
            response: Response object
        """
        await self.session_engine.destroy(session, response)
    
    async def logout_all_devices(
        self,
        identity_id: str,
    ) -> None:
        """
        Logout from all devices - destroy all sessions for identity.
        
        Args:
            identity_id: Identity ID
        """
        # List all sessions for this principal
        sessions = await self.session_engine.store.list_by_principal(identity_id)
        
        # Delete all sessions
        for session in sessions:
            await self.session_engine.store.delete(session.id)


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    "AuthPrincipal",
    "bind_identity",
    "bind_token_claims",
    "get_identity_id",
    "get_tenant_id",
    "get_roles",
    "get_scopes",
    "is_mfa_verified",
    "set_mfa_verified",
    "user_session_policy",
    "api_session_policy",
    "device_session_policy",
    "SessionAuthBridge",
]
