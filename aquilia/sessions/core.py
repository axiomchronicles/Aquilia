"""
AquilaSessions - Core types.

Defines fundamental session data structures:
- Session: Core state container
- SessionID: Opaque cryptographic identifier
- SessionPrincipal: Identity binding
- SessionScope: Lifetime semantics
- SessionFlag: Behavioral markers
"""

from __future__ import annotations

import secrets
import base64
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Literal


# ============================================================================
# SessionID - Opaque Cryptographic Identifier
# ============================================================================

class SessionID:
    """
    Opaque session identifier with cryptographic randomness.
    
    Rules:
    - Never encode meaning (no user ID, no timestamps)
    - Cryptographically random (32 bytes = 256 bits entropy)
    - URL-safe encoding
    - Prefixed for identification (sess_)
    
    Example:
        >>> sid = SessionID()
        >>> str(sid)
        'sess_kJ8...'
        >>> SessionID.from_string(str(sid))
        SessionID(sess_kJ8...)
    """
    
    __slots__ = ("_raw", "_encoded")
    
    def __init__(self, raw: bytes | None = None):
        """
        Create session ID.
        
        Args:
            raw: Raw bytes (32 bytes). If None, generates random bytes.
        """
        if raw is None:
            raw = secrets.token_bytes(32)
        elif len(raw) != 32:
            raise ValueError("Session ID must be exactly 32 bytes")
        
        self._raw = raw
        self._encoded = f"sess_{base64.urlsafe_b64encode(raw).decode().rstrip('=')}"
    
    def __str__(self) -> str:
        """Return encoded session ID string."""
        return self._encoded
    
    def __repr__(self) -> str:
        """Return debug representation."""
        return f"SessionID({self._encoded[:16]}...)"
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on raw bytes."""
        if not isinstance(other, SessionID):
            return False
        return self._raw == other._raw
    
    def __hash__(self) -> int:
        """Hash based on raw bytes."""
        return hash(self._raw)
    
    @classmethod
    def from_string(cls, encoded: str) -> SessionID:
        """
        Parse session ID from encoded string.
        
        Args:
            encoded: Encoded session ID (sess_...)
            
        Returns:
            SessionID instance
            
        Raises:
            ValueError: If format is invalid
        """
        if not encoded.startswith("sess_"):
            raise ValueError("Invalid session ID format: must start with 'sess_'")
        
        raw_b64 = encoded[5:]
        
        # Add padding if needed (base64 requires multiple of 4)
        padding = 4 - (len(raw_b64) % 4)
        if padding != 4:
            raw_b64 += "=" * padding
        
        try:
            raw = base64.urlsafe_b64decode(raw_b64)
        except Exception as e:
            raise ValueError(f"Invalid session ID encoding: {e}")
        
        return cls(raw)
    
    @property
    def raw(self) -> bytes:
        """Get raw bytes (use with caution)."""
        return self._raw


# ============================================================================
# SessionScope - Lifetime Semantics
# ============================================================================

class SessionScope(str, Enum):
    """
    Session lifetime semantics.
    
    Scope determines when and how session state persists:
    - REQUEST: Lives only for single request (no persistence)
    - CONNECTION: WebSocket / long-lived connection
    - USER: Persistent user session (typical web session)
    - DEVICE: Bound to device fingerprint (mobile apps)
    """
    
    REQUEST = "request"
    CONNECTION = "connection"
    USER = "user"
    DEVICE = "device"
    
    def requires_persistence(self) -> bool:
        """Check if this scope requires store persistence."""
        return self in (SessionScope.USER, SessionScope.DEVICE, SessionScope.CONNECTION)
    
    def is_ephemeral(self) -> bool:
        """Check if session is ephemeral (no persistence)."""
        return self == SessionScope.REQUEST


# ============================================================================
# SessionFlag - Behavioral Markers
# ============================================================================

class SessionFlag(str, Enum):
    """
    Flags that modify session behavior.
    
    Flags are additive markers that affect how the session is treated:
    - AUTHENTICATED: Has authenticated principal
    - EPHEMERAL: Never persist to store (override policy)
    - ROTATABLE: ID should rotate on privilege change
    - RENEWABLE: Can extend TTL on use
    - READ_ONLY: Data mutations disallowed
    - LOCKED: Concurrency lock active
    """
    
    AUTHENTICATED = "authenticated"
    EPHEMERAL = "ephemeral"
    ROTATABLE = "rotatable"
    RENEWABLE = "renewable"
    READ_ONLY = "read_only"
    LOCKED = "locked"


# ============================================================================
# SessionPrincipal - Identity Binding
# ============================================================================

@dataclass
class SessionPrincipal:
    """
    Represents who the session belongs to.
    
    A session may exist without a principal (anonymous).
    Principal binding is explicit and auditable.
    
    Attributes:
        kind: Type of principal (user, service, device, anonymous)
        id: Unique identifier within kind
        attributes: Additional claims/metadata
    
    Example:
        >>> principal = SessionPrincipal(
        ...     kind="user",
        ...     id="user_123",
        ...     attributes={"email": "user@example.com", "role": "admin"}
        ... )
        >>> principal.is_user()
        True
        >>> principal.get_attribute("email")
        'user@example.com'
    """
    
    kind: Literal["user", "service", "device", "anonymous"]
    id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    
    def is_user(self) -> bool:
        """Check if principal is a user."""
        return self.kind == "user"
    
    def is_service(self) -> bool:
        """Check if principal is a service."""
        return self.kind == "service"
    
    def is_device(self) -> bool:
        """Check if principal is a device."""
        return self.kind == "device"
    
    def is_anonymous(self) -> bool:
        """Check if principal is anonymous."""
        return self.kind == "anonymous"
    
    def has_attribute(self, key: str) -> bool:
        """Check if attribute exists."""
        return key in self.attributes
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute value with optional default."""
        return self.attributes.get(key, default)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute value."""
        self.attributes[key] = value
    
    def remove_attribute(self, key: str) -> None:
        """Remove attribute."""
        self.attributes.pop(key, None)


# ============================================================================
# Session - Core Data Object
# ============================================================================

@dataclass
class Session:
    """
    Core session object - explicit state container with lifecycle.
    
    Sessions are NOT implicit cookies. They are explicit capabilities
    that grant scoped access to state and identity.
    
    Attributes:
        id: Opaque, cryptographically random identifier
        principal: Who owns this session (optional)
        data: Application state (mutable dictionary)
        created_at: When session was created
        last_accessed_at: When session was last accessed
        expires_at: When session expires (None = no expiry)
        scope: Lifetime semantics
        flags: Behavioral markers
        version: Optimistic concurrency control counter
    
    Internal attributes (prefixed with _):
        _dirty: Has data been modified?
        _policy_name: Which policy governs this session
    
    Example:
        >>> session = Session(
        ...     id=SessionID(),
        ...     scope=SessionScope.USER,
        ...     created_at=datetime.now(timezone.utc),
        ...     last_accessed_at=datetime.now(timezone.utc)
        ... )
        >>> session.data["cart_items"] = 3
        >>> session.is_dirty
        True
        >>> session.mark_authenticated(SessionPrincipal("user", "user_123"))
        >>> session.is_authenticated
        True
    """
    
    id: SessionID
    principal: SessionPrincipal | None = None
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    scope: SessionScope = SessionScope.USER
    flags: set[SessionFlag] = field(default_factory=set)
    version: int = 0
    
    # Internal tracking (not serialized)
    _dirty: bool = field(default=False, repr=False)
    _policy_name: str = field(default="", repr=False)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to track data mutations."""
        super().__setattr__(name, value)
        
        # Mark dirty if data is modified (but not during __init__)
        if hasattr(self, "_dirty") and name == "data":
            object.__setattr__(self, "_dirty", True)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to data."""
        return self.data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like access to data (marks dirty)."""
        self.data[key] = value
        self._dirty = True
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in data."""
        return key in self.data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get data value with default."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set data value (explicit, marks dirty)."""
        self.data[key] = value
        self._dirty = True
    
    def delete(self, key: str) -> None:
        """Delete data key (marks dirty)."""
        if key in self.data:
            del self.data[key]
            self._dirty = True
    
    def clear_data(self) -> None:
        """Clear all session data (marks dirty)."""
        self.data.clear()
        self._dirty = True
    
    # ========================================================================
    # Lifecycle Methods
    # ========================================================================
    
    def is_expired(self, now: datetime | None = None) -> bool:
        """
        Check if session has passed expiry.
        
        Args:
            now: Current time (defaults to utcnow)
            
        Returns:
            True if expired, False otherwise
        """
        if not self.expires_at:
            return False
        
        if now is None:
            now = datetime.now(timezone.utc)
        
        return now >= self.expires_at
    
    def idle_duration(self, now: datetime | None = None) -> timedelta:
        """
        Calculate how long session has been idle.
        
        Args:
            now: Current time (defaults to utcnow)
            
        Returns:
            Timedelta since last access
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        return now - self.last_accessed_at
    
    def touch(self, now: datetime | None = None) -> None:
        """
        Mark session as accessed (updates last_accessed_at).
        
        Args:
            now: Current time (defaults to utcnow)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        self.last_accessed_at = now
        self._dirty = True
    
    def extend_expiry(self, ttl: timedelta, now: datetime | None = None) -> None:
        """
        Extend session expiry by TTL.
        
        Args:
            ttl: Time to live to add
            now: Current time (defaults to utcnow)
        """
        if now is None:
            now = datetime.utcnow()
        
        self.expires_at = now + ttl
        self._dirty = True
    
    # ========================================================================
    # Authentication Methods
    # ========================================================================
    
    def mark_authenticated(self, principal: SessionPrincipal) -> None:
        """
        Bind principal and mark as authenticated.
        
        Args:
            principal: Principal to bind
        """
        self.principal = principal
        self.flags.add(SessionFlag.AUTHENTICATED)
        self.flags.add(SessionFlag.ROTATABLE)  # Should rotate on privilege change
        self._dirty = True
    
    def clear_authentication(self) -> None:
        """Remove authentication and principal."""
        self.principal = None
        self.flags.discard(SessionFlag.AUTHENTICATED)
        self.flags.discard(SessionFlag.ROTATABLE)
        self._dirty = True
    
    @property
    def is_authenticated(self) -> bool:
        """Check if session has authenticated principal."""
        return SessionFlag.AUTHENTICATED in self.flags and self.principal is not None
    
    @property
    def is_anonymous(self) -> bool:
        """Check if session is anonymous (no principal or anonymous principal)."""
        return not self.is_authenticated
    
    # ========================================================================
    # State Management
    # ========================================================================
    
    @property
    def is_dirty(self) -> bool:
        """Check if session needs persistence."""
        return self._dirty
    
    def mark_clean(self) -> None:
        """Mark session as clean (after persistence)."""
        self._dirty = False
    
    def mark_dirty(self) -> None:
        """Explicitly mark session as dirty."""
        self._dirty = True
    
    @property
    def is_ephemeral(self) -> bool:
        """Check if session should never persist."""
        return (
            SessionFlag.EPHEMERAL in self.flags
            or self.scope.is_ephemeral()
        )
    
    @property
    def is_read_only(self) -> bool:
        """Check if data mutations are disallowed."""
        return SessionFlag.READ_ONLY in self.flags
    
    @property
    def is_locked(self) -> bool:
        """Check if concurrency lock is active."""
        return SessionFlag.LOCKED in self.flags
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize session to dictionary (for storage).
        
        Returns:
            Dictionary representation
        """
        return {
            "id": str(self.id),
            "principal": (
                {
                    "kind": self.principal.kind,
                    "id": self.principal.id,
                    "attributes": self.principal.attributes,
                }
                if self.principal
                else None
            ),
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope.value,
            "flags": [f.value for f in self.flags],
            "version": self.version,
            "_policy_name": self._policy_name,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """
        Deserialize session from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Session instance
        """
        # Parse session ID
        session_id = SessionID.from_string(data["id"])
        
        # Parse principal
        principal = None
        if data.get("principal"):
            principal = SessionPrincipal(
                kind=data["principal"]["kind"],
                id=data["principal"]["id"],
                attributes=data["principal"]["attributes"],
            )
        
        # Parse dates
        created_at = datetime.fromisoformat(data["created_at"])
        last_accessed_at = datetime.fromisoformat(data["last_accessed_at"])
        expires_at = (
            datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None
        )
        
        # Parse scope and flags
        scope = SessionScope(data["scope"])
        flags = {SessionFlag(f) for f in data.get("flags", [])}
        
        # Create session
        session = cls(
            id=session_id,
            principal=principal,
            data=data.get("data", {}),
            created_at=created_at,
            last_accessed_at=last_accessed_at,
            expires_at=expires_at,
            scope=scope,
            flags=flags,
            version=data.get("version", 0),
        )
        
        session._policy_name = data.get("_policy_name", "")
        session._dirty = False  # Just loaded, not dirty
        
        return session
