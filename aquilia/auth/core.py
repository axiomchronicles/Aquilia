"""
AquilAuth - Core Types

Identity, credentials, and foundational data structures.
"""

from __future__ import annotations

from typing import Literal, Any, Protocol
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import secrets
import hashlib


# ============================================================================
# Identity Model
# ============================================================================

class IdentityType(str, Enum):
    """Type of authenticated principal."""
    USER = "user"
    SERVICE = "service"
    DEVICE = "device"
    ANONYMOUS = "anonymous"


class IdentityStatus(str, Enum):
    """Identity status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING = "pending"  # Awaiting verification


@dataclass(frozen=True)
class Identity:
    """
    Authenticated principal (user or service).
    
    Immutable once created. Stored in DI request scope.
    
    Design:
    - Stable ID that never changes
    - Type discrimination for policy decisions
    - Flexible attributes for ABAC
    - Status for soft delete and suspension
    - Multi-tenant support via tenant_id
    """
    id: str
    type: IdentityType
    attributes: dict[str, Any]  # email, name, roles, dept, clearance, etc.
    status: IdentityStatus = IdentityStatus.ACTIVE
    tenant_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute value with default."""
        return self.attributes.get(key, default)
    
    def has_role(self, role: str) -> bool:
        """Check if identity has role."""
        roles = self.get_attribute("roles", [])
        return role in roles
    
    def has_scope(self, scope: str) -> bool:
        """Check if identity has scope."""
        scopes = self.get_attribute("scopes", [])
        return scope in scopes or "*" in scopes
    
    def is_active(self) -> bool:
        """Check if identity is active."""
        return self.status == IdentityStatus.ACTIVE
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "type": self.type.value,
            "attributes": self.attributes,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Identity:
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            type=IdentityType(data["type"]),
            attributes=data["attributes"],
            status=IdentityStatus(data["status"]),
            tenant_id=data.get("tenant_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


# ============================================================================
# Credential Types
# ============================================================================

class CredentialStatus(str, Enum):
    """Credential status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class Credential(Protocol):
    """
    Base protocol for credentials.
    
    All credential types must implement this protocol.
    """
    identity_id: str
    status: CredentialStatus
    created_at: datetime
    last_used_at: datetime | None


@dataclass
class PasswordCredential:
    """
    Password-based credential.
    
    Uses Argon2id for hashing (memory-hard, GPU-resistant).
    """
    identity_id: str
    password_hash: str          # Argon2id hash
    algorithm: str = "argon2id"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_changed_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    must_change: bool = False   # Force password change on next login
    status: CredentialStatus = CredentialStatus.ACTIVE
    
    def should_rotate(self, max_age_days: int = 90) -> bool:
        """Check if password should be rotated."""
        age = datetime.utcnow() - self.last_changed_at
        return age > timedelta(days=max_age_days)
    
    def touch(self) -> None:
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "identity_id": self.identity_id,
            "password_hash": self.password_hash,
            "algorithm": self.algorithm,
            "created_at": self.created_at.isoformat(),
            "last_changed_at": self.last_changed_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "must_change": self.must_change,
            "status": self.status.value,
        }


@dataclass
class ApiKeyCredential:
    """
    API key credential (long-lived).
    
    Key format: ak_<env>_<random>
    Example: ak_live_1234567890abcdef
    
    Security:
    - Keys are hashed before storage (SHA256)
    - Prefix stored for identification
    - Scoped permissions
    - Rate limiting per key
    """
    identity_id: str
    key_id: str                 # Unique identifier
    key_hash: str               # SHA256(key_secret)
    prefix: str                 # First 8 chars (e.g., "ak_live_")
    scopes: list[str]
    rate_limit: int | None = None  # Requests per minute
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    status: CredentialStatus = CredentialStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
    
    @staticmethod
    def generate_key(env: Literal["test", "live"] = "live") -> str:
        """
        Generate new API key.
        
        Format: ak_<env>_<32_random_bytes>
        """
        random_part = secrets.token_urlsafe(32)
        return f"ak_{env}_{random_part}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash API key with SHA256."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "identity_id": self.identity_id,
            "key_id": self.key_id,
            "key_hash": self.key_hash,
            "prefix": self.prefix,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "status": self.status.value,
            "metadata": self.metadata,
        }


@dataclass
class OAuthClient:
    """
    OAuth2/OIDC client.
    
    Supports multiple grant types:
    - authorization_code: Standard OAuth2 flow
    - client_credentials: Machine-to-machine
    - refresh_token: Token refresh
    - device_code: Device flow (TV, CLI)
    """
    client_id: str
    client_secret_hash: str | None  # None for public clients
    name: str
    grant_types: list[Literal["authorization_code", "client_credentials", "refresh_token", "device_code"]]
    redirect_uris: list[str]
    scopes: list[str]
    require_pkce: bool = True
    require_consent: bool = True
    token_endpoint_auth_method: Literal["client_secret_basic", "client_secret_post", "none"] = "client_secret_post"
    access_token_ttl: int = 3600      # 1 hour
    refresh_token_ttl: int = 2592000  # 30 days
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: CredentialStatus = CredentialStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def is_public_client(self) -> bool:
        """Check if client is public (no secret)."""
        return self.client_secret_hash is None
    
    def supports_grant_type(self, grant_type: str) -> bool:
        """Check if client supports grant type."""
        return grant_type in self.grant_types
    
    def is_redirect_uri_valid(self, redirect_uri: str) -> bool:
        """Check if redirect URI is allowed."""
        return redirect_uri in self.redirect_uris
    
    @staticmethod
    def generate_client_id(prefix: str = "app") -> str:
        """Generate client ID."""
        random_part = secrets.token_urlsafe(16)
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def generate_client_secret() -> str:
        """Generate client secret."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_client_secret(secret: str) -> str:
        """Hash client secret with SHA256."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "client_id": self.client_id,
            "client_secret_hash": self.client_secret_hash,
            "name": self.name,
            "grant_types": self.grant_types,
            "redirect_uris": self.redirect_uris,
            "scopes": self.scopes,
            "require_pkce": self.require_pkce,
            "require_consent": self.require_consent,
            "token_endpoint_auth_method": self.token_endpoint_auth_method,
            "access_token_ttl": self.access_token_ttl,
            "refresh_token_ttl": self.refresh_token_ttl,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata,
        }


@dataclass
class MFACredential:
    """
    Multi-factor authentication credential.
    
    Supports:
    - TOTP: Time-based one-time passwords (Google Authenticator)
    - WebAuthn: FIDO2 hardware keys
    - SMS/Email: OTP via message (requires external provider)
    """
    identity_id: str
    mfa_type: Literal["totp", "webauthn", "sms", "email"]
    mfa_secret: str | None = None       # TOTP shared secret (base32)
    backup_codes: list[str] = field(default_factory=list)  # Hashed backup codes
    webauthn_credentials: list[dict[str, Any]] = field(default_factory=list)  # Public keys
    phone_number: str | None = None     # For SMS
    email: str | None = None            # For email OTP
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified_at: datetime | None = None
    last_used_at: datetime | None = None
    status: CredentialStatus = CredentialStatus.ACTIVE
    
    def is_verified(self) -> bool:
        """Check if MFA is verified."""
        return self.verified_at is not None
    
    def touch(self) -> None:
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.utcnow()
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate TOTP secret (base32)."""
        import base64
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode().rstrip("=")
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate backup codes (8-character alphanumeric)."""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "identity_id": self.identity_id,
            "mfa_type": self.mfa_type,
            "mfa_secret": self.mfa_secret,
            "backup_codes": self.backup_codes,
            "webauthn_credentials": self.webauthn_credentials,
            "phone_number": self.phone_number,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "status": self.status.value,
        }


# ============================================================================
# Token Claims
# ============================================================================

@dataclass
class TokenClaims:
    """
    Access token claims (JWT payload).
    
    Standard claims:
    - iss: Issuer
    - sub: Subject (identity ID)
    - aud: Audience
    - exp: Expiration time
    - iat: Issued at
    - nbf: Not before
    - jti: JWT ID (unique token identifier)
    
    Custom claims:
    - scopes: Permitted scopes
    - sid: Session ID
    - roles: User roles
    - tenant_id: Multi-tenant ID
    """
    iss: str                    # Issuer
    sub: str                    # Subject (identity ID)
    aud: list[str]              # Audience
    exp: int                    # Expiration (Unix timestamp)
    iat: int                    # Issued at (Unix timestamp)
    nbf: int                    # Not before (Unix timestamp)
    jti: str                    # Token ID
    scopes: list[str]           # Scopes
    sid: str | None = None      # Session ID
    roles: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        import time
        return time.time() > self.exp
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has scope."""
        return scope in self.scopes or "*" in self.scopes
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (JWT payload)."""
        return {
            "iss": self.iss,
            "sub": self.sub,
            "aud": self.aud,
            "exp": self.exp,
            "iat": self.iat,
            "nbf": self.nbf,
            "jti": self.jti,
            "scopes": self.scopes,
            "sid": self.sid,
            "roles": self.roles,
            "tenant_id": self.tenant_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenClaims:
        """Deserialize from dict (JWT payload)."""
        return cls(
            iss=data["iss"],
            sub=data["sub"],
            aud=data["aud"],
            exp=data["exp"],
            iat=data["iat"],
            nbf=data["nbf"],
            jti=data["jti"],
            scopes=data.get("scopes", []),
            sid=data.get("sid"),
            roles=data.get("roles", []),
            tenant_id=data.get("tenant_id"),
        )


# ============================================================================
# Authentication Result
# ============================================================================

@dataclass
class AuthResult:
    """
    Result of authentication operation.
    
    Contains:
    - Authenticated identity
    - Access token (for API requests)
    - Refresh token (for token renewal)
    - Session handle (if session-based auth)
    - Metadata (auth method, MFA used, etc.)
    """
    identity: Identity
    access_token: str | None = None
    refresh_token: str | None = None
    session_id: str | None = None
    expires_in: int | None = None  # Access token TTL in seconds
    token_type: str = "Bearer"
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (token response)."""
        result = {
            "access_token": self.access_token,
            "token_type": self.token_type,
        }
        
        if self.expires_in is not None:
            result["expires_in"] = self.expires_in
        
        if self.refresh_token:
            result["refresh_token"] = self.refresh_token
        
        if self.scopes:
            result["scope"] = " ".join(self.scopes)
        
        return result


# ============================================================================
# Store Protocols
# ============================================================================

class IdentityStore(Protocol):
    """Protocol for identity storage."""
    
    async def create(self, identity: Identity) -> None:
        """Create new identity."""
        ...
    
    async def get(self, identity_id: str) -> Identity | None:
        """Get identity by ID."""
        ...
    
    async def get_by_attribute(self, key: str, value: Any) -> Identity | None:
        """Get identity by attribute (e.g., email)."""
        ...
    
    async def update(self, identity: Identity) -> None:
        """Update identity."""
        ...
    
    async def delete(self, identity_id: str) -> None:
        """Delete identity (soft delete)."""
        ...
    
    async def list_by_tenant(self, tenant_id: str) -> list[Identity]:
        """List identities by tenant."""
        ...


class CredentialStore(Protocol):
    """Protocol for credential storage."""
    
    async def create_password(self, credential: PasswordCredential) -> None:
        """Create password credential."""
        ...
    
    async def get_password(self, identity_id: str) -> PasswordCredential | None:
        """Get password credential."""
        ...
    
    async def update_password(self, credential: PasswordCredential) -> None:
        """Update password credential."""
        ...
    
    async def create_api_key(self, credential: ApiKeyCredential) -> None:
        """Create API key credential."""
        ...
    
    async def get_api_key(self, key_id: str) -> ApiKeyCredential | None:
        """Get API key by ID."""
        ...
    
    async def get_api_key_by_hash(self, key_hash: str) -> ApiKeyCredential | None:
        """Get API key by hash."""
        ...
    
    async def list_api_keys(self, identity_id: str) -> list[ApiKeyCredential]:
        """List API keys for identity."""
        ...
    
    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke API key."""
        ...
    
    async def create_mfa(self, credential: MFACredential) -> None:
        """Create MFA credential."""
        ...
    
    async def get_mfa(self, identity_id: str) -> list[MFACredential]:
        """Get MFA credentials for identity."""
        ...
    
    async def update_mfa(self, credential: MFACredential) -> None:
        """Update MFA credential."""
        ...


class OAuthClientStore(Protocol):
    """Protocol for OAuth client storage."""
    
    async def create(self, client: OAuthClient) -> None:
        """Create OAuth client."""
        ...
    
    async def get(self, client_id: str) -> OAuthClient | None:
        """Get client by ID."""
        ...
    
    async def update(self, client: OAuthClient) -> None:
        """Update client."""
        ...
    
    async def delete(self, client_id: str) -> None:
        """Delete client."""
        ...
    
    async def list_all(self) -> list[OAuthClient]:
        """List all clients."""
        ...
