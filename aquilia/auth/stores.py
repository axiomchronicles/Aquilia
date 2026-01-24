"""
AquilAuth - Credential and Token Stores

In-memory and Redis-backed storage implementations for identities,
credentials, OAuth clients, and tokens.

Stores:
- MemoryIdentityStore: Dev/testing identity storage
- MemoryCredentialStore: Dev/testing credential storage
- MemoryOAuthClientStore: Dev/testing OAuth client storage
- MemoryTokenStore: Dev/testing token storage
- RedisTokenStore: Production token revocation with bloom filter
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Protocol

from .core import (
    ApiKeyCredential,
    Identity,
    IdentityStatus,
    MFACredential,
    OAuthClient,
    PasswordCredential,
)


# ============================================================================
# Memory Stores (for development and testing)
# ============================================================================


class MemoryIdentityStore:
    """In-memory identity storage for development/testing."""

    def __init__(self):
        self._identities: dict[str, Identity] = {}
        self._by_attribute: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._lock = asyncio.Lock()

    async def create(self, identity: Identity) -> Identity:
        """Create new identity."""
        async with self._lock:
            if identity.id in self._identities:
                raise ValueError(f"Identity {identity.id} already exists")

            self._identities[identity.id] = identity

            # Index attributes for fast lookup
            for key, value in identity.attributes.items():
                if isinstance(value, (str, int, bool)):
                    self._by_attribute[key][str(value)].add(identity.id)

            return identity

    async def get(self, identity_id: str) -> Identity | None:
        """Get identity by ID."""
        return self._identities.get(identity_id)

    async def get_by_attribute(
        self, attribute: str, value: Any
    ) -> Identity | None:
        """Get identity by attribute value."""
        identity_ids = self._by_attribute[attribute].get(str(value), set())
        if identity_ids:
            return self._identities.get(next(iter(identity_ids)))
        return None

    async def update(self, identity: Identity) -> Identity:
        """Update existing identity."""
        async with self._lock:
            if identity.id not in self._identities:
                raise ValueError(f"Identity {identity.id} not found")

            old_identity = self._identities[identity.id]

            # Update attribute indices
            for key, value in old_identity.attributes.items():
                if isinstance(value, (str, int, bool)):
                    self._by_attribute[key][str(value)].discard(identity.id)

            for key, value in identity.attributes.items():
                if isinstance(value, (str, int, bool)):
                    self._by_attribute[key][str(value)].add(identity.id)

            self._identities[identity.id] = identity
            return identity

    async def delete(self, identity_id: str) -> bool:
        """Delete identity (soft delete by setting status)."""
        async with self._lock:
            identity = self._identities.get(identity_id)
            if not identity:
                return False

            # Create new identity with DELETED status
            deleted_identity = Identity(
                id=identity.id,
                type=identity.type,
                attributes=identity.attributes,
                status=IdentityStatus.DELETED,
                tenant_id=identity.tenant_id,
                created_at=identity.created_at,
                updated_at=datetime.utcnow(),
            )

            self._identities[identity_id] = deleted_identity
            return True

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[Identity]:
        """List identities by tenant."""
        identities = [
            i
            for i in self._identities.values()
            if i.tenant_id == tenant_id and i.status != IdentityStatus.DELETED
        ]
        return identities[offset : offset + limit]


class MemoryCredentialStore:
    """In-memory credential storage for development/testing."""

    def __init__(self):
        self._passwords: dict[str, PasswordCredential] = {}
        self._api_keys: dict[str, ApiKeyCredential] = {}
        self._mfa: dict[str, list[MFACredential]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # Password credentials
    async def save_password(self, credential: PasswordCredential) -> None:
        """Save password credential."""
        async with self._lock:
            self._passwords[credential.identity_id] = credential

    async def get_password(
        self, identity_id: str
    ) -> PasswordCredential | None:
        """Get password credential."""
        return self._passwords.get(identity_id)

    async def delete_password(self, identity_id: str) -> bool:
        """Delete password credential."""
        async with self._lock:
            if identity_id in self._passwords:
                del self._passwords[identity_id]
                return True
            return False

    # API key credentials
    async def save_api_key(self, credential: ApiKeyCredential) -> None:
        """Save API key credential."""
        async with self._lock:
            self._api_keys[credential.key_id] = credential

    async def get_api_key(self, key_id: str) -> ApiKeyCredential | None:
        """Get API key credential."""
        return self._api_keys.get(key_id)

    async def get_api_key_by_prefix(
        self, prefix: str
    ) -> ApiKeyCredential | None:
        """Get API key by prefix (first 8 chars)."""
        for credential in self._api_keys.values():
            if credential.prefix == prefix:
                return credential
        return None

    async def list_api_keys(self, identity_id: str) -> list[ApiKeyCredential]:
        """List all API keys for identity."""
        return [
            c
            for c in self._api_keys.values()
            if c.identity_id == identity_id
        ]

    async def delete_api_key(self, key_id: str) -> bool:
        """Delete API key credential."""
        async with self._lock:
            if key_id in self._api_keys:
                del self._api_keys[key_id]
                return True
            return False

    # MFA credentials
    async def save_mfa(self, credential: MFACredential) -> None:
        """Save MFA credential."""
        async with self._lock:
            credentials = self._mfa[credential.identity_id]
            # Remove existing credential of same type
            self._mfa[credential.identity_id] = [
                c for c in credentials if c.mfa_type != credential.mfa_type
            ]
            self._mfa[credential.identity_id].append(credential)

    async def get_mfa(
        self, identity_id: str, mfa_type: str | None = None
    ) -> list[MFACredential]:
        """Get MFA credentials for identity."""
        credentials = self._mfa.get(identity_id, [])
        if mfa_type:
            return [c for c in credentials if c.mfa_type == mfa_type]
        return credentials

    async def delete_mfa(
        self, identity_id: str, mfa_type: str | None = None
    ) -> bool:
        """Delete MFA credentials."""
        async with self._lock:
            if identity_id not in self._mfa:
                return False

            if mfa_type:
                original_len = len(self._mfa[identity_id])
                self._mfa[identity_id] = [
                    c
                    for c in self._mfa[identity_id]
                    if c.mfa_type != mfa_type
                ]
                return len(self._mfa[identity_id]) < original_len
            else:
                del self._mfa[identity_id]
                return True


class MemoryOAuthClientStore:
    """In-memory OAuth client storage for development/testing."""

    def __init__(self):
        self._clients: dict[str, OAuthClient] = {}
        self._lock = asyncio.Lock()

    async def create(self, client: OAuthClient) -> OAuthClient:
        """Create OAuth client."""
        async with self._lock:
            if client.client_id in self._clients:
                raise ValueError(f"Client {client.client_id} already exists")
            self._clients[client.client_id] = client
            return client

    async def get(self, client_id: str) -> OAuthClient | None:
        """Get OAuth client by ID."""
        return self._clients.get(client_id)

    async def update(self, client: OAuthClient) -> OAuthClient:
        """Update OAuth client."""
        async with self._lock:
            if client.client_id not in self._clients:
                raise ValueError(f"Client {client.client_id} not found")
            self._clients[client.client_id] = client
            return client

    async def delete(self, client_id: str) -> bool:
        """Delete OAuth client."""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                return True
            return False

    async def list(
        self, owner_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[OAuthClient]:
        """List OAuth clients."""
        clients = list(self._clients.values())
        if owner_id:
            clients = [c for c in clients if c.owner_id == owner_id]
        return clients[offset : offset + limit]


class MemoryTokenStore:
    """In-memory token storage for development/testing."""

    def __init__(self):
        self._refresh_tokens: dict[str, dict[str, Any]] = {}
        self._revoked_tokens: set[str] = set()
        self._revoked_by_identity: dict[str, set[str]] = defaultdict(set)
        self._revoked_by_session: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def save_refresh_token(
        self,
        token_id: str,
        identity_id: str,
        scopes: list[str],
        expires_at: datetime,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save refresh token."""
        async with self._lock:
            self._refresh_tokens[token_id] = {
                "identity_id": identity_id,
                "scopes": scopes,
                "expires_at": expires_at.isoformat(),
                "session_id": session_id,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            if session_id:
                self._revoked_by_session[session_id].add(token_id)

    async def get_refresh_token(self, token_id: str) -> dict[str, Any] | None:
        """Get refresh token data."""
        return self._refresh_tokens.get(token_id)

    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke single refresh token."""
        async with self._lock:
            self._revoked_tokens.add(token_id)

            # Track by identity and session for bulk revocation
            if token_id in self._refresh_tokens:
                data = self._refresh_tokens[token_id]
                self._revoked_by_identity[data["identity_id"]].add(token_id)

    async def revoke_tokens_by_identity(self, identity_id: str) -> None:
        """Revoke all tokens for identity."""
        async with self._lock:
            for token_id, data in self._refresh_tokens.items():
                if data["identity_id"] == identity_id:
                    self._revoked_tokens.add(token_id)
                    self._revoked_by_identity[identity_id].add(token_id)

    async def revoke_tokens_by_session(self, session_id: str) -> None:
        """Revoke all tokens for session."""
        async with self._lock:
            token_ids = self._revoked_by_session.get(session_id, set())
            self._revoked_tokens.update(token_ids)

    async def is_token_revoked(self, token_id: str) -> bool:
        """Check if token is revoked."""
        return token_id in self._revoked_tokens

    async def cleanup_expired(self) -> int:
        """Remove expired tokens (returns count removed)."""
        async with self._lock:
            now = datetime.utcnow()
            expired = []

            for token_id, data in self._refresh_tokens.items():
                expires_at = datetime.fromisoformat(data["expires_at"])
                if expires_at < now:
                    expired.append(token_id)

            for token_id in expired:
                del self._refresh_tokens[token_id]
                self._revoked_tokens.discard(token_id)

            return len(expired)


# ============================================================================
# Redis Token Store (for production)
# ============================================================================


class RedisTokenStore:
    """
    Redis-backed token store with bloom filter for fast revocation checks.

    Uses:
    - Sorted sets for refresh tokens (with expiration as score)
    - Bloom filter for revoked tokens (probabilistic, fast)
    - Sets for identity/session token tracking
    """

    def __init__(self, redis_client: Any, key_prefix: str = "aquilauth:"):
        """
        Initialize Redis token store.

        Args:
            redis_client: Redis async client (e.g., aioredis)
            key_prefix: Prefix for all Redis keys
        """
        self.redis = redis_client
        self.prefix = key_prefix

    def _key(self, *parts: str) -> str:
        """Build Redis key."""
        return self.prefix + ":".join(parts)

    async def save_refresh_token(
        self,
        token_id: str,
        identity_id: str,
        scopes: list[str],
        expires_at: datetime,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save refresh token to Redis."""
        data = {
            "identity_id": identity_id,
            "scopes": json.dumps(scopes),
            "expires_at": expires_at.isoformat(),
            "session_id": session_id or "",
            "metadata": json.dumps(metadata or {}),
        }

        # Store token data as hash
        await self.redis.hset(
            self._key("token", token_id),
            mapping=data,
        )

        # Set expiration (Redis auto-cleanup)
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        await self.redis.expire(self._key("token", token_id), ttl)

        # Track by identity
        await self.redis.sadd(
            self._key("identity", identity_id, "tokens"), token_id
        )
        await self.redis.expire(
            self._key("identity", identity_id, "tokens"),
            ttl + 86400,  # Extra day for cleanup
        )

        # Track by session
        if session_id:
            await self.redis.sadd(
                self._key("session", session_id, "tokens"), token_id
            )
            await self.redis.expire(
                self._key("session", session_id, "tokens"),
                ttl + 86400,
            )

    async def get_refresh_token(self, token_id: str) -> dict[str, Any] | None:
        """Get refresh token data from Redis."""
        data = await self.redis.hgetall(self._key("token", token_id))
        if not data:
            return None

        return {
            "identity_id": data[b"identity_id"].decode(),
            "scopes": json.loads(data[b"scopes"].decode()),
            "expires_at": data[b"expires_at"].decode(),
            "session_id": data[b"session_id"].decode() or None,
            "metadata": json.loads(data[b"metadata"].decode()),
        }

    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke single refresh token."""
        # Add to revoked set (bloom filter alternative)
        await self.redis.sadd(self._key("revoked"), token_id)

        # Set expiration on revoked set (cleanup after 30 days)
        await self.redis.expire(self._key("revoked"), 30 * 86400)

    async def revoke_tokens_by_identity(self, identity_id: str) -> None:
        """Revoke all tokens for identity."""
        token_ids = await self.redis.smembers(
            self._key("identity", identity_id, "tokens")
        )

        if token_ids:
            # Add all to revoked set
            await self.redis.sadd(
                self._key("revoked"), *[t.decode() for t in token_ids]
            )

    async def revoke_tokens_by_session(self, session_id: str) -> None:
        """Revoke all tokens for session."""
        token_ids = await self.redis.smembers(
            self._key("session", session_id, "tokens")
        )

        if token_ids:
            await self.redis.sadd(
                self._key("revoked"), *[t.decode() for t in token_ids]
            )

    async def is_token_revoked(self, token_id: str) -> bool:
        """Check if token is revoked (fast check using Redis set)."""
        return await self.redis.sismember(self._key("revoked"), token_id)

    async def cleanup_expired(self) -> int:
        """Redis handles expiration automatically, return 0."""
        return 0


# ============================================================================
# Authorization Code Store (for OAuth2)
# ============================================================================


class MemoryAuthorizationCodeStore:
    """In-memory authorization code storage for OAuth2 flows."""

    def __init__(self):
        self._codes: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def save_code(
        self,
        code: str,
        client_id: str,
        identity_id: str,
        redirect_uri: str,
        scopes: list[str],
        expires_at: datetime,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> None:
        """Save authorization code."""
        async with self._lock:
            self._codes[code] = {
                "client_id": client_id,
                "identity_id": identity_id,
                "redirect_uri": redirect_uri,
                "scopes": scopes,
                "expires_at": expires_at.isoformat(),
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "used": False,
            }

    async def get_code(self, code: str) -> dict[str, Any] | None:
        """Get authorization code data."""
        return self._codes.get(code)

    async def consume_code(self, code: str) -> bool:
        """Mark code as used (one-time use)."""
        async with self._lock:
            if code in self._codes and not self._codes[code]["used"]:
                self._codes[code]["used"] = True
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired codes."""
        async with self._lock:
            now = datetime.utcnow()
            expired = []

            for code, data in self._codes.items():
                expires_at = datetime.fromisoformat(data["expires_at"])
                if expires_at < now or data["used"]:
                    expired.append(code)

            for code in expired:
                del self._codes[code]

            return len(expired)


# ============================================================================
# Device Code Store (for device flow)
# ============================================================================


class MemoryDeviceCodeStore:
    """In-memory device code storage for device authorization flow."""

    def __init__(self):
        self._codes: dict[str, dict[str, Any]] = {}
        self._user_codes: dict[str, str] = {}  # user_code -> device_code
        self._lock = asyncio.Lock()

    async def save_device_code(
        self,
        device_code: str,
        user_code: str,
        client_id: str,
        scopes: list[str],
        expires_at: datetime,
    ) -> None:
        """Save device code."""
        async with self._lock:
            self._codes[device_code] = {
                "user_code": user_code,
                "client_id": client_id,
                "scopes": scopes,
                "expires_at": expires_at.isoformat(),
                "identity_id": None,  # Set when user authorizes
                "status": "pending",  # pending, authorized, denied
            }
            self._user_codes[user_code] = device_code

    async def get_by_device_code(
        self, device_code: str
    ) -> dict[str, Any] | None:
        """Get device code data."""
        return self._codes.get(device_code)

    async def get_by_user_code(self, user_code: str) -> dict[str, Any] | None:
        """Get device code data by user code."""
        device_code = self._user_codes.get(user_code)
        if device_code:
            return self._codes.get(device_code)
        return None

    async def authorize_device_code(
        self, user_code: str, identity_id: str
    ) -> bool:
        """Authorize device code (user approved)."""
        async with self._lock:
            device_code = self._user_codes.get(user_code)
            if device_code and device_code in self._codes:
                self._codes[device_code]["identity_id"] = identity_id
                self._codes[device_code]["status"] = "authorized"
                return True
            return False

    async def deny_device_code(self, user_code: str) -> bool:
        """Deny device code (user rejected)."""
        async with self._lock:
            device_code = self._user_codes.get(user_code)
            if device_code and device_code in self._codes:
                self._codes[device_code]["status"] = "denied"
                return True
            return False
