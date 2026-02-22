"""
AquilAuth - Token Management

JWT-like token generation, validation, and key ring management.
"""

from __future__ import annotations

from typing import Literal, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import base64
import secrets
import hashlib
import time


# ============================================================================
# Key Management
# ============================================================================

class KeyAlgorithm(str):
    """Supported signing algorithms."""
    RS256 = "RS256"  # RSA with SHA-256
    ES256 = "ES256"  # ECDSA with SHA-256
    EdDSA = "EdDSA"  # Ed25519


class KeyStatus(str):
    """Key status in lifecycle."""
    ACTIVE = "active"        # Current signing key
    ROTATING = "rotating"    # Being promoted
    RETIRED = "retired"      # No longer signs, but verifies
    REVOKED = "revoked"      # Invalid for all operations


@dataclass
class KeyDescriptor:
    """
    Cryptographic key metadata.
    
    Keys are identified by 'kid' (key ID) in JWT headers.
    """
    kid: str                           # Key ID (e.g., "key_001")
    algorithm: str                     # Algorithm (RS256, ES256, EdDSA)
    public_key_pem: str                # PEM-encoded public key
    private_key_pem: str | None = None # PEM-encoded private key (signing only)
    status: str = KeyStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retire_after: datetime | None = None
    revoked_at: datetime | None = None
    
    def is_active(self) -> bool:
        """Check if key can be used for signing."""
        return self.status == KeyStatus.ACTIVE
    
    def can_verify(self) -> bool:
        """Check if key can be used for verification."""
        return self.status in (KeyStatus.ACTIVE, KeyStatus.ROTATING, KeyStatus.RETIRED)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        res = {
            "kid": self.kid,
            "algorithm": self.algorithm,
            "public_key": self.public_key_pem,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "retire_after": self.retire_after.isoformat() if self.retire_after else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
        if self.private_key_pem:
            res["private_key"] = self.private_key_pem
        return res
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KeyDescriptor:
        """Deserialize from dict."""
        return cls(
            kid=data["kid"],
            algorithm=data["algorithm"],
            public_key_pem=data["public_key"],
            private_key_pem=data.get("private_key"),
            status=data.get("status", KeyStatus.ACTIVE),
            created_at=datetime.fromisoformat(data["created_at"]),
            retire_after=datetime.fromisoformat(data["retire_after"]) if data.get("retire_after") else None,
            revoked_at=datetime.fromisoformat(data["revoked_at"]) if data.get("revoked_at") else None,
        )
    
    @classmethod
    def generate(cls, kid: str, algorithm: str = KeyAlgorithm.RS256) -> KeyDescriptor:
        """
        Generate new key pair.
        
        Requires cryptography library.
        """
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        if algorithm == KeyAlgorithm.RS256:
            # Generate RSA key pair (2048-bit)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )
        elif algorithm == KeyAlgorithm.ES256:
            # Generate ECDSA key pair (P-256 curve)
            private_key = ec.generate_private_key(
                ec.SECP256R1(),
                backend=default_backend(),
            )
        elif algorithm == KeyAlgorithm.EdDSA:
            # Generate Ed25519 key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        
        return cls(
            kid=kid,
            algorithm=algorithm,
            public_key_pem=public_pem,
            private_key_pem=private_pem,
        )


class KeyRing:
    """
    Key ring for JWT signing and verification.
    
    Manages multiple keys with lifecycle:
    - Current signing key (kid)
    - Historical keys for verification
    - Rotation support
    """
    
    def __init__(self, keys: list[KeyDescriptor]):
        self.keys: dict[str, KeyDescriptor] = {k.kid: k for k in keys}
        
        # Find active signing key
        active_keys = [k for k in keys if k.is_active()]
        if not active_keys:
            raise ValueError("No active signing key in key ring")
        
        self.current_kid = active_keys[0].kid
    
    def get_signing_key(self) -> KeyDescriptor:
        """Get current signing key."""
        key = self.keys.get(self.current_kid)
        
        if not key or not key.is_active():
            raise ValueError(f"No active signing key: {self.current_kid}")
        
        return key
    
    def get_verification_key(self, kid: str) -> KeyDescriptor | None:
        """Get verification key by kid."""
        key = self.keys.get(kid)
        
        if key and key.can_verify():
            return key
        
        return None
    
    def add_key(self, key: KeyDescriptor) -> None:
        """Add key to ring."""
        self.keys[key.kid] = key
    
    def promote_key(self, kid: str) -> None:
        """Promote key to active (retire current)."""
        new_key = self.keys.get(kid)
        
        if not new_key:
            raise ValueError(f"Key not found: {kid}")
        
        # Retire current key
        if self.current_kid in self.keys:
            old_key = self.keys[self.current_kid]
            old_key.status = KeyStatus.RETIRED
            old_key.retire_after = datetime.now(timezone.utc)
        
        # Promote new key
        new_key.status = KeyStatus.ACTIVE
        self.current_kid = kid
    
    def revoke_key(self, kid: str) -> None:
        """Revoke key (invalid for all operations)."""
        key = self.keys.get(kid)
        
        if key:
            key.status = KeyStatus.REVOKED
            key.revoked_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "current_kid": self.current_kid,
            "keys": [k.to_dict() for k in self.keys.values()],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KeyRing:
        """Deserialize from dict."""
        keys = [KeyDescriptor.from_dict(k) for k in data["keys"]]
        ring = cls(keys)
        ring.current_kid = data["current_kid"]
        return ring
    
    @classmethod
    def from_file(cls, path: Path) -> KeyRing:
        """Load from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_file(self, path: Path) -> None:
        """Save to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# ============================================================================
# Token Manager
# ============================================================================

@dataclass
class TokenConfig:
    """Token manager configuration."""
    issuer: str = "aquilia"
    audience: list[str] = field(default_factory=lambda: ["api"])
    access_token_ttl: int = 3600        # 1 hour
    refresh_token_ttl: int = 2592000    # 30 days
    algorithm: str = KeyAlgorithm.RS256


class TokenStore(Protocol):
    """Protocol for token storage (opaque tokens, revocation)."""
    
    async def save_refresh_token(
        self,
        token_id: str,
        identity_id: str,
        scopes: list[str],
        expires_at: datetime,
        session_id: str | None = None,
    ) -> None:
        """Save refresh token."""
        ...
    
    async def get_refresh_token(self, token_id: str) -> dict[str, Any] | None:
        """Get refresh token data."""
        ...
    
    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke refresh token."""
        ...
    
    async def revoke_tokens_by_identity(self, identity_id: str) -> None:
        """Revoke all tokens for identity."""
        ...
    
    async def revoke_tokens_by_session(self, session_id: str) -> None:
        """Revoke all tokens for session."""
        ...
    
    async def is_token_revoked(self, token_id: str) -> bool:
        """Check if token is revoked."""
        ...


class TokenManager:
    """
    Token lifecycle manager.
    
    Responsibilities:
    - Issue signed access tokens (JWT-like)
    - Issue opaque refresh tokens
    - Validate token signatures and claims
    - Manage token revocation
    """
    
    def __init__(
        self,
        key_ring: KeyRing,
        token_store: TokenStore,
        config: TokenConfig | None = None,
    ):
        self.key_ring = key_ring
        self.token_store = token_store
        self.config = config or TokenConfig()
    
    async def issue_access_token(
        self,
        identity_id: str,
        scopes: list[str],
        roles: list[str] | None = None,
        session_id: str | None = None,
        tenant_id: str | None = None,
        ttl: int | None = None,
    ) -> str:
        """
        Issue signed access token.
        
        Format: header.payload.signature
        - header: {"alg": "RS256", "kid": "key_001", "typ": "JWT"}
        - payload: {"iss": "aquilia", "sub": "user_123", ...}
        - signature: RS256(header + payload, private_key)
        """
        now = int(time.time())
        ttl = ttl or self.config.access_token_ttl
        
        # Generate token ID
        token_id = f"at_{secrets.token_urlsafe(16)}"
        
        # Build payload
        payload = {
            "iss": self.config.issuer,
            "sub": identity_id,
            "aud": self.config.audience,
            "exp": now + ttl,
            "iat": now,
            "nbf": now,
            "jti": token_id,
            "scopes": scopes,
        }
        
        if roles:
            payload["roles"] = roles
        
        if session_id:
            payload["sid"] = session_id
        
        if tenant_id:
            payload["tenant_id"] = tenant_id
        
        # Sign token
        return self._sign_token(payload)
    
    async def issue_refresh_token(
        self,
        identity_id: str,
        scopes: list[str],
        session_id: str | None = None,
    ) -> str:
        """
        Issue opaque refresh token.
        
        Refresh tokens are stored in token_store (stateful).
        Format: rt_<random>
        """
        token_id = f"rt_{secrets.token_urlsafe(32)}"
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.config.refresh_token_ttl)
        
        await self.token_store.save_refresh_token(
            token_id=token_id,
            identity_id=identity_id,
            scopes=scopes,
            expires_at=expires_at,
            session_id=session_id,
        )
        
        return token_id
    
    async def validate_access_token(self, token: str) -> dict[str, Any]:
        """
        Validate and decode access token.
        
        Checks:
        1. Format (3 parts)
        2. Header (alg, kid)
        3. Signature
        4. Expiration
        5. Not revoked
        
        Raises:
            ValueError: Invalid token
        """
        # Parse token
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError:
            raise ValueError("Malformed token: expected 3 parts")
        
        # Decode header
        header = self._base64_decode_json(header_b64)
        kid = header.get("kid")
        
        if not kid:
            raise ValueError("Missing kid in header")
        
        # Get verification key
        key = self.key_ring.get_verification_key(kid)
        
        if not key:
            raise ValueError(f"Unknown kid: {kid}")
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}".encode()
        signature = self._base64_decode(signature_b64)
        
        if not self._verify_signature(message, signature, key):
            raise ValueError("Invalid signature")
        
        # Decode payload
        payload = self._base64_decode_json(payload_b64)
        
        # Check expiration
        now = int(time.time())
        exp = payload.get("exp")
        
        if not exp or exp < now:
            raise ValueError("Token expired")
        
        # Check not before
        nbf = payload.get("nbf", 0)
        if nbf > now:
            raise ValueError("Token not yet valid")
        
        # Check revocation
        jti = payload.get("jti")
        if jti and await self.token_store.is_token_revoked(jti):
            raise ValueError("Token revoked")
        
        return payload
    
    async def validate_refresh_token(self, token: str) -> dict[str, Any]:
        """
        Validate refresh token.
        
        Refresh tokens are opaque and stored in token_store.
        """
        data = await self.token_store.get_refresh_token(token)
        
        if not data:
            raise ValueError("Invalid refresh token")
        
        # Check expiration
        expires_at = data.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            raise ValueError("Refresh token expired")
        
        return data
    
    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Exchange refresh token for new access + refresh tokens.
        
        Implements refresh token rotation (security best practice).
        """
        # Validate refresh token
        data = await self.validate_refresh_token(refresh_token)
        
        # Revoke old refresh token
        await self.token_store.revoke_refresh_token(refresh_token)
        
        # Issue new tokens
        access_token = await self.issue_access_token(
            identity_id=data["identity_id"],
            scopes=data["scopes"],
            session_id=data.get("session_id"),
        )
        
        new_refresh_token = await self.issue_refresh_token(
            identity_id=data["identity_id"],
            scopes=data["scopes"],
            session_id=data.get("session_id"),
        )
        
        return (access_token, new_refresh_token)
    
    async def revoke_token(self, token_id: str) -> None:
        """Revoke token by ID."""
        await self.token_store.revoke_refresh_token(token_id)
    
    async def revoke_tokens_by_identity(self, identity_id: str) -> None:
        """Revoke all tokens for identity."""
        await self.token_store.revoke_tokens_by_identity(identity_id)
    
    async def revoke_tokens_by_session(self, session_id: str) -> None:
        """Revoke all tokens for session."""
        await self.token_store.revoke_tokens_by_session(session_id)
    
    def _sign_token(self, payload: dict[str, Any]) -> str:
        """Sign JWT token."""
        key = self.key_ring.get_signing_key()
        
        # Build header
        header = {
            "alg": key.algorithm,
            "kid": key.kid,
            "typ": "JWT",
        }
        
        # Encode parts
        header_b64 = self._base64_encode_json(header)
        payload_b64 = self._base64_encode_json(payload)
        
        # Sign
        message = f"{header_b64}.{payload_b64}".encode()
        signature = self._create_signature(message, key)
        signature_b64 = self._base64_encode(signature)
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _create_signature(self, message: bytes, key: KeyDescriptor) -> bytes:
        """Create signature for message."""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, padding
        from cryptography.hazmat.backends import default_backend
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            key.private_key_pem.encode(),
            password=None,
            backend=default_backend(),
        )
        
        if key.algorithm == KeyAlgorithm.RS256:
            signature = private_key.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        elif key.algorithm == KeyAlgorithm.ES256:
            signature = private_key.sign(
                message,
                ec.ECDSA(hashes.SHA256()),
            )
        elif key.algorithm == KeyAlgorithm.EdDSA:
            signature = private_key.sign(message)
        else:
            raise ValueError(f"Unsupported algorithm: {key.algorithm}")
        
        return signature
    
    def _verify_signature(self, message: bytes, signature: bytes, key: KeyDescriptor) -> bool:
        """Verify signature."""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, padding
        from cryptography.hazmat.backends import default_backend
        from cryptography.exceptions import InvalidSignature
        
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                key.public_key_pem.encode(),
                backend=default_backend(),
            )
            
            if key.algorithm == KeyAlgorithm.RS256:
                public_key.verify(
                    signature,
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
            elif key.algorithm == KeyAlgorithm.ES256:
                public_key.verify(
                    signature,
                    message,
                    ec.ECDSA(hashes.SHA256()),
                )
            elif key.algorithm == KeyAlgorithm.EdDSA:
                public_key.verify(signature, message)
            else:
                return False
            
            return True
        
        except InvalidSignature:
            return False
    
    def _base64_encode(self, data: bytes) -> str:
        """URL-safe base64 encode."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    
    def _base64_decode(self, data: str) -> bytes:
        """URL-safe base64 decode."""
        # Add padding
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += "=" * padding
        
        return base64.urlsafe_b64decode(data)
    
    def _base64_encode_json(self, data: dict) -> str:
        """Encode JSON as URL-safe base64."""
        json_bytes = json.dumps(data, separators=(",", ":")).encode()
        return self._base64_encode(json_bytes)
    
    def _base64_decode_json(self, data: str) -> dict:
        """Decode URL-safe base64 as JSON."""
        json_bytes = self._base64_decode(data)
        return json.loads(json_bytes)
