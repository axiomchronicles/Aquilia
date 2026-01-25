"""
AquilaSessions - Policy types.

Defines session policies that govern behavior:
- SessionPolicy: Master policy contract
- PersistencePolicy: How sessions persist
- ConcurrencyPolicy: Concurrent session limits
- TransportPolicy: How sessions travel
"""

from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Session, SessionPrincipal, SessionScope


# ============================================================================
# Sub-Policies
# ============================================================================

@dataclass
class PersistencePolicy:
    """
    Controls how sessions persist to storage.
    
    Attributes:
        enabled: Whether persistence is enabled
        store_name: Which SessionStore to use
        write_through: Immediate vs eventual consistency
        compress: Compress session data before storage
    
    Example:
        >>> policy = PersistencePolicy(
        ...     enabled=True,
        ...     store_name="redis",
        ...     write_through=True,
        ...     compress=False
        ... )
    """
    
    enabled: bool = True
    store_name: str = "default"
    write_through: bool = True  # vs write-behind (eventual)
    compress: bool = False


@dataclass
class ConcurrencyPolicy:
    """
    Controls concurrent session limits per principal.
    
    Attributes:
        max_sessions_per_principal: Maximum concurrent sessions (None = unlimited)
        behavior_on_limit: What to do when limit is reached
            - "reject": Reject new session creation
            - "evict_oldest": Evict oldest session
            - "evict_all": Evict all existing sessions
    
    Example:
        >>> policy = ConcurrencyPolicy(
        ...     max_sessions_per_principal=5,
        ...     behavior_on_limit="evict_oldest"
        ... )
        >>> policy.violated(principal, active_count=6)
        True
    """
    
    max_sessions_per_principal: int | None = None
    behavior_on_limit: Literal["reject", "evict_oldest", "evict_all"] = "evict_oldest"
    
    def violated(self, principal: SessionPrincipal, active_count: int) -> bool:
        """
        Check if concurrency limit is violated.
        
        Args:
            principal: Principal to check
            active_count: Number of active sessions for this principal
            
        Returns:
            True if limit is violated, False otherwise
        """
        if self.max_sessions_per_principal is None:
            return False
        
        return active_count > self.max_sessions_per_principal
    
    def should_reject(self) -> bool:
        """Check if policy rejects new sessions on limit."""
        return self.behavior_on_limit == "reject"
    
    def should_evict_oldest(self) -> bool:
        """Check if policy evicts oldest session on limit."""
        return self.behavior_on_limit == "evict_oldest"
    
    def should_evict_all(self) -> bool:
        """Check if policy evicts all sessions on limit."""
        return self.behavior_on_limit == "evict_all"


@dataclass
class TransportPolicy:
    """
    Controls how sessions travel across network.
    
    Attributes:
        adapter: Transport adapter type
        cookie_name: Name of session cookie (if adapter=cookie)
        cookie_httponly: HttpOnly flag (prevents XSS)
        cookie_secure: Secure flag (HTTPS only)
        cookie_samesite: SameSite policy (CSRF protection)
        cookie_path: Cookie path
        cookie_domain: Cookie domain
        header_name: Header name (if adapter=header)
    
    Example:
        >>> policy = TransportPolicy(
        ...     adapter="cookie",
        ...     cookie_name="aquilia_session",
        ...     cookie_httponly=True,
        ...     cookie_secure=True,
        ...     cookie_samesite="lax"
        ... )
    """
    
    adapter: Literal["cookie", "header", "token"] = "cookie"
    
    # Cookie options
    cookie_name: str = "aquilia_session"
    cookie_httponly: bool = True
    cookie_secure: bool = True
    cookie_samesite: Literal["strict", "lax", "none"] = "lax"
    cookie_path: str = "/"
    cookie_domain: str | None = None
    
    # Header options
    header_name: str = "X-Session-ID"


# ============================================================================
# Master Policy
# ============================================================================

@dataclass
class SessionPolicy:
    """
    Master policy that defines how sessions behave.
    
    Policies are the source of truth for:
    - Lifetime management (TTL, idle timeout)
    - Rotation rules (when to rotate IDs)
    - Persistence strategy
    - Concurrency limits
    - Transport mechanism
    
    Attributes:
        name: Policy identifier (e.g., "user_default", "api_token")
        ttl: Total session lifetime (None = no expiry)
        idle_timeout: Max idle time before expiry
        rotate_on_use: Rotate ID on each request
        rotate_on_privilege_change: Rotate ID when authentication changes
        persistence: Persistence sub-policy
        concurrency: Concurrency sub-policy
        transport: Transport sub-policy
        scope: Default session scope
    
    Example:
        >>> policy = SessionPolicy(
        ...     name="user_default",
        ...     ttl=timedelta(days=7),
        ...     idle_timeout=timedelta(minutes=30),
        ...     rotate_on_use=False,
        ...     rotate_on_privilege_change=True,
        ...     persistence=PersistencePolicy(enabled=True, store_name="redis"),
        ...     concurrency=ConcurrencyPolicy(max_sessions_per_principal=5),
        ...     transport=TransportPolicy(adapter="cookie"),
        ... )
    """
    
    name: str
    ttl: timedelta | None = None
    idle_timeout: timedelta | None = None
    rotate_on_use: bool = False
    rotate_on_privilege_change: bool = True
    persistence: PersistencePolicy = None  # type: ignore
    concurrency: ConcurrencyPolicy = None  # type: ignore
    transport: TransportPolicy = None  # type: ignore
    scope: str = "user"  # Will be converted to SessionScope
    
    def __post_init__(self):
        """Initialize sub-policies with defaults if not provided."""
        if self.persistence is None:
            self.persistence = PersistencePolicy()
        
        if self.concurrency is None:
            self.concurrency = ConcurrencyPolicy()
        
        if self.transport is None:
            self.transport = TransportPolicy()
    
    def should_rotate(self, session: Session, privilege_changed: bool = False) -> bool:
        """
        Determine if session ID should rotate.
        
        Args:
            session: Session to check
            privilege_changed: Whether authentication changed
            
        Returns:
            True if rotation should happen, False otherwise
        """
        # Always rotate on privilege change if policy says so
        if privilege_changed and self.rotate_on_privilege_change:
            return True
        
        # Rotate on every use if policy says so
        if self.rotate_on_use:
            return True
        
        return False
    
    def calculate_expiry(self, now: datetime | None = None) -> datetime | None:
        """
        Calculate session expiry time based on TTL.
        
        Args:
            now: Current time (defaults to utcnow)
            
        Returns:
            Expiry datetime or None if no TTL
        """
        if not self.ttl:
            return None
        
        if now is None:
            now = datetime.utcnow()
        
        return now + self.ttl
    
    def is_valid(self, session: Session, now: datetime | None = None) -> tuple[bool, str]:
        """
        Validate session against policy.
        
        Args:
            session: Session to validate
            now: Current time (defaults to utcnow)
            
        Returns:
            Tuple of (is_valid, reason)
            - (True, "valid") if valid
            - (False, "expired") if expired
            - (False, "idle_timeout") if idle timeout exceeded
        """
        if now is None:
            now = datetime.utcnow()
        
        # Check expiry
        if session.is_expired(now):
            return False, "expired"
        
        # Check idle timeout
        if self.idle_timeout:
            idle_duration = session.idle_duration(now)
            if idle_duration >= self.idle_timeout:
                return False, "idle_timeout"
        
        return True, "valid"
    
    def should_persist(self, session: Session) -> bool:
        """
        Determine if session should be persisted.
        
        Args:
            session: Session to check
            
        Returns:
            True if should persist, False otherwise
        """
        # Never persist if persistence disabled
        if not self.persistence.enabled:
            return False
        
        # Never persist ephemeral sessions
        if session.is_ephemeral:
            return False
        
        # Only persist if scope requires it
        if not session.scope.requires_persistence():
            return False
        
        return True
    
    def requires_store(self) -> bool:
        """Check if policy requires a session store."""
        return self.persistence.enabled
    
    @classmethod
    def from_dict(cls, name: str, config: dict) -> SessionPolicy:
        """
        Create policy from configuration dictionary.
        
        Args:
            name: Policy name
            config: Configuration dict
            
        Returns:
            SessionPolicy instance
        """
        from .core import SessionScope
        
        # Parse TTL (seconds to timedelta)
        ttl = None
        if config.get("ttl"):
            ttl = timedelta(seconds=config["ttl"])
        
        # Parse idle timeout
        idle_timeout = None
        if config.get("idle_timeout"):
            idle_timeout = timedelta(seconds=config["idle_timeout"])
        
        # Parse persistence policy
        persistence_config = config.get("persistence", {})
        persistence = PersistencePolicy(
            enabled=persistence_config.get("enabled", True),
            store_name=persistence_config.get("store_name", "default"),
            write_through=persistence_config.get("write_through", True),
            compress=persistence_config.get("compress", False),
        )
        
        # Parse concurrency policy
        concurrency_config = config.get("concurrency", {})
        concurrency = ConcurrencyPolicy(
            max_sessions_per_principal=concurrency_config.get("max_sessions_per_principal"),
            behavior_on_limit=concurrency_config.get("behavior_on_limit", "evict_oldest"),
        )
        
        # Parse transport policy
        transport_config = config.get("transport", {})
        transport = TransportPolicy(
            adapter=transport_config.get("adapter", "cookie"),
            cookie_name=transport_config.get("cookie_name", "aquilia_session"),
            cookie_httponly=transport_config.get("cookie_httponly", True),
            cookie_secure=transport_config.get("cookie_secure", True),
            cookie_samesite=transport_config.get("cookie_samesite", "lax"),
            cookie_path=transport_config.get("cookie_path", "/"),
            cookie_domain=transport_config.get("cookie_domain"),
            header_name=transport_config.get("header_name", "X-Session-ID"),
        )
        
        # Parse scope
        scope_str = config.get("scope", "user")
        
        return cls(
            name=name,
            ttl=ttl,
            idle_timeout=idle_timeout,
            rotate_on_use=config.get("rotate_on_use", False),
            rotate_on_privilege_change=config.get("rotate_on_privilege_change", True),
            persistence=persistence,
            concurrency=concurrency,
            transport=transport,
            scope=scope_str,
        )
    
    # ========================================================================
    # Unique Aquilia Fluent Builders
    # ========================================================================
    
    @classmethod
    def for_web_users(cls) -> "SessionPolicyBuilder":
        """Create policy optimized for web users."""
        return SessionPolicyBuilder().web_defaults()
    
    @classmethod
    def for_api_tokens(cls) -> "SessionPolicyBuilder":
        """Create policy optimized for API tokens."""
        return SessionPolicyBuilder().api_defaults()
    
    @classmethod
    def for_mobile_users(cls) -> "SessionPolicyBuilder":
        """Create policy optimized for mobile users."""
        return SessionPolicyBuilder().mobile_defaults()
    
    @classmethod
    def for_admin_users(cls) -> "SessionPolicyBuilder":
        """Create policy with enhanced security for admin users."""
        return SessionPolicyBuilder().admin_defaults()


# ============================================================================
# Unique Aquilia Session Policy Builder
# ============================================================================

class SessionPolicyBuilder:
    """Fluent builder for SessionPolicy with unique Aquilia syntax."""
    
    def __init__(self):
        self._name = "aquilia_session"
        self._ttl = timedelta(days=7)
        self._idle_timeout = timedelta(hours=1)
        self._rotate_on_use = False
        self._rotate_on_privilege_change = True
        self._scope = "user"
        self._transport = TransportPolicy(
            adapter="cookie",
            cookie_name="aquilia_session",
            cookie_secure=True,
            cookie_httponly=True,
            cookie_samesite="lax"
        )
        self._persistence = PersistencePolicy(enabled=True, store_name="default")
        self._concurrency = ConcurrencyPolicy(max_sessions_per_principal=5)
    
    def named(self, name: str) -> "SessionPolicyBuilder":
        """Set policy name."""
        self._name = name
        return self
    
    def lasting(self, days: int = None, hours: int = None, minutes: int = None) -> "SessionPolicyBuilder":
        """Set session duration with natural syntax."""
        if days: self._ttl = timedelta(days=days)
        elif hours: self._ttl = timedelta(hours=hours) 
        elif minutes: self._ttl = timedelta(minutes=minutes)
        return self
    
    def idle_timeout(self, hours: int = None, minutes: int = None, days: int = None) -> "SessionPolicyBuilder":
        """Set idle timeout with natural syntax."""
        if days: self._idle_timeout = timedelta(days=days)
        elif hours: self._idle_timeout = timedelta(hours=hours)
        elif minutes: self._idle_timeout = timedelta(minutes=minutes)
        return self
    
    def no_idle_timeout(self) -> "SessionPolicyBuilder":
        """Disable idle timeout."""
        self._idle_timeout = None
        return self
    
    def rotating_on_auth(self) -> "SessionPolicyBuilder":
        """Enable session rotation on privilege changes."""
        self._rotate_on_privilege_change = True
        return self
    
    def rotating_on_use(self) -> "SessionPolicyBuilder":
        """Enable session rotation on each use."""
        self._rotate_on_use = True
        return self
    
    def scoped_to(self, scope: str) -> "SessionPolicyBuilder":
        """Set session scope (user, tenant, global)."""
        self._scope = scope
        return self
    
    def max_concurrent(self, limit: int) -> "SessionPolicyBuilder":
        """Set maximum concurrent sessions per principal."""
        self._concurrency = ConcurrencyPolicy(
            max_sessions_per_principal=limit,
            behavior_on_limit="evict_oldest"
        )
        return self
    
    def unlimited_concurrent(self) -> "SessionPolicyBuilder":
        """Allow unlimited concurrent sessions."""
        self._concurrency = ConcurrencyPolicy(
            max_sessions_per_principal=None,
            behavior_on_limit="allow"
        )
        return self
    
    def with_smart_defaults(self) -> "SessionPolicyBuilder":
        """Apply smart defaults based on environment."""
        # Auto-detect environment and apply appropriate settings
        import os
        if os.getenv("AQUILIA_ENV") == "production":
            return self.lasting(days=1).idle_timeout(minutes=30)
        else:
            return self.lasting(days=7).idle_timeout(hours=2)
    
    def web_defaults(self) -> "SessionPolicyBuilder":
        """Apply defaults optimized for web applications."""
        return (self.named("web_session")
                   .lasting(days=7)
                   .idle_timeout(hours=2)
                   .rotating_on_auth()
                   .max_concurrent(5))
    
    def api_defaults(self) -> "SessionPolicyBuilder":
        """Apply defaults optimized for API services."""
        return (self.named("api_session")
                   .lasting(hours=1)
                   .no_idle_timeout()
                   .unlimited_concurrent())
    
    def mobile_defaults(self) -> "SessionPolicyBuilder":
        """Apply defaults optimized for mobile applications."""
        return (self.named("mobile_session")
                   .lasting(days=90)
                   .idle_timeout(days=30)
                   .max_concurrent(3))
    
    def admin_defaults(self) -> "SessionPolicyBuilder":
        """Apply enhanced security defaults for admin users."""
        return (self.named("admin_session")
                   .lasting(hours=8)
                   .idle_timeout(minutes=15)
                   .rotating_on_use()
                   .max_concurrent(1))
    
    def build(self) -> SessionPolicy:
        """Build the final SessionPolicy."""
        return SessionPolicy(
            name=self._name,
            ttl=self._ttl,
            idle_timeout=self._idle_timeout,
            rotate_on_use=self._rotate_on_use,
            rotate_on_privilege_change=self._rotate_on_privilege_change,
            persistence=self._persistence,
            concurrency=self._concurrency,
            transport=self._transport,
            scope=self._scope,
        )
    
    def __call__(self) -> SessionPolicy:
        """Allow direct calling to build policy."""
        return self.build()


# ============================================================================
# Built-in Policies
# ============================================================================

# Default user session policy (7 days, 30 min idle timeout)
DEFAULT_USER_POLICY = SessionPolicy(
    name="user_default",
    ttl=timedelta(days=7),
    idle_timeout=timedelta(minutes=30),
    rotate_on_use=False,
    rotate_on_privilege_change=True,
    persistence=PersistencePolicy(enabled=True, store_name="default"),
    concurrency=ConcurrencyPolicy(max_sessions_per_principal=5, behavior_on_limit="evict_oldest"),
    transport=TransportPolicy(adapter="cookie"),
    scope="user",
)

# API token policy (1 hour, no idle timeout, header transport)
API_TOKEN_POLICY = SessionPolicy(
    name="api_token",
    ttl=timedelta(hours=1),
    idle_timeout=None,
    rotate_on_use=False,
    rotate_on_privilege_change=False,
    persistence=PersistencePolicy(enabled=True, store_name="default"),
    concurrency=ConcurrencyPolicy(max_sessions_per_principal=None),
    transport=TransportPolicy(adapter="header", header_name="X-API-Token"),
    scope="user",
)

# Ephemeral request-scoped policy (no persistence)
EPHEMERAL_POLICY = SessionPolicy(
    name="ephemeral",
    ttl=None,
    idle_timeout=None,
    rotate_on_use=False,
    rotate_on_privilege_change=False,
    persistence=PersistencePolicy(enabled=False),
    concurrency=ConcurrencyPolicy(max_sessions_per_principal=None),
    transport=TransportPolicy(adapter="cookie"),
    scope="request",
)
