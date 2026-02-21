"""
AquilAuth - OAuth2/OIDC Flows

Implementation of OAuth 2.0 and OpenID Connect flows:
- Authorization Code Flow (with PKCE)
- Client Credentials Flow
- Device Authorization Flow
- Refresh Token Flow
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Any

from .core import OAuthClient
from .faults import (
    AUTH_CLIENT_INVALID,
    AUTH_DEVICE_CODE_EXPIRED,
    AUTH_DEVICE_CODE_PENDING,
    AUTH_GRANT_INVALID,
    AUTH_PKCE_INVALID,
    AUTH_REDIRECT_URI_MISMATCH,
    AUTH_SCOPE_INVALID,
    AUTH_SLOW_DOWN,
)
from .stores import (
    MemoryAuthorizationCodeStore,
    MemoryDeviceCodeStore,
    MemoryOAuthClientStore,
)
from .tokens import TokenManager


# ============================================================================
# PKCE Utilities
# ============================================================================


class PKCEVerifier:
    """PKCE (Proof Key for Code Exchange) utilities."""

    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """
        Generate code verifier for PKCE.

        Args:
            length: Length of verifier (43-128 chars)

        Returns:
            URL-safe random string
        """
        if not 43 <= length <= 128:
            length = 128

        # Generate random bytes and encode as URL-safe base64
        random_bytes = secrets.token_bytes(length)
        verifier = (
            base64.urlsafe_b64encode(random_bytes)
            .decode("utf-8")
            .rstrip("=")[:length]
        )
        return verifier

    @staticmethod
    def generate_code_challenge(
        verifier: str, method: str = "S256"
    ) -> str:
        """
        Generate code challenge from verifier.

        Args:
            verifier: Code verifier
            method: Challenge method (S256 or plain)

        Returns:
            Code challenge
        """
        if method == "S256":
            # SHA256 hash of verifier
            digest = hashlib.sha256(verifier.encode("utf-8")).digest()
            challenge = (
                base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
            )
            return challenge
        elif method == "plain":
            return verifier
        else:
            raise ValueError(f"Unknown PKCE method: {method}")

    @staticmethod
    def verify_code_challenge(
        verifier: str, challenge: str, method: str = "S256"
    ) -> bool:
        """
        Verify code verifier against challenge.

        Args:
            verifier: Code verifier from client
            challenge: Stored code challenge
            method: Challenge method

        Returns:
            True if verifier matches challenge
        """
        expected = PKCEVerifier.generate_code_challenge(verifier, method)
        return secrets.compare_digest(expected, challenge)


# ============================================================================
# OAuth2 Manager
# ============================================================================


class OAuth2Manager:
    """
    OAuth 2.0 / OIDC authorization server.

    Implements:
    - Authorization Code Flow (with PKCE)
    - Client Credentials Flow
    - Device Authorization Flow
    - Token refresh
    """

    def __init__(
        self,
        client_store: MemoryOAuthClientStore,
        code_store: MemoryAuthorizationCodeStore,
        device_store: MemoryDeviceCodeStore,
        token_manager: TokenManager,
        issuer: str,
    ):
        self.client_store = client_store
        self.code_store = code_store
        self.device_store = device_store
        self.token_manager = token_manager
        self.issuer = issuer

    async def validate_client(
        self, client_id: str, client_secret: str | None = None
    ) -> OAuthClient:
        """
        Validate OAuth client credentials.

        Args:
            client_id: Client ID
            client_secret: Client secret (required for confidential clients)

        Returns:
            OAuth client

        Raises:
            AUTH_CLIENT_INVALID: Invalid client credentials
        """
        client = await self.client_store.get(client_id)
        if not client:
            raise AUTH_CLIENT_INVALID(client_id=client_id)

        # Verify client secret if provided
        if client_secret:
            from .hashing import PasswordHasher

            hasher = PasswordHasher()
            if not hasher.verify(client.client_secret_hash, client_secret):
                raise AUTH_CLIENT_INVALID(client_id=client_id)

        return client

    async def authorize(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str | None = None,
        response_type: str = "code",
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
    ) -> dict[str, Any]:
        """
        Authorization endpoint - initiate authorization flow.

        Args:
            client_id: OAuth client ID
            redirect_uri: Redirect URI
            scope: Space-separated scopes
            state: Client state parameter
            response_type: Response type (code)
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE method (S256, plain)

        Returns:
            Authorization data (requires user consent)

        Raises:
            AUTH_CLIENT_INVALID: Invalid client
            AUTH_REDIRECT_URI_MISMATCH: Invalid redirect URI
            AUTH_SCOPE_INVALID: Invalid scope
        """
        # Validate client
        client = await self.validate_client(client_id)

        # Validate redirect URI
        if redirect_uri not in client.redirect_uris:
            raise AUTH_REDIRECT_URI_MISMATCH(
                redirect_uri=redirect_uri,
                allowed_uris=client.redirect_uris,
            )

        # Parse and validate scopes
        requested_scopes = scope.split()
        invalid_scopes = set(requested_scopes) - set(client.scopes)
        if invalid_scopes:
            raise AUTH_SCOPE_INVALID(
                requested_scopes=requested_scopes,
                allowed_scopes=client.scopes,
            )

        # Check PKCE requirement
        if client.require_pkce and not code_challenge:
            raise AUTH_PKCE_INVALID(
                reason="PKCE required but no code_challenge provided"
            )

        # Return authorization request (requires user consent UI)
        return {
            "client_id": client_id,
            "client_name": client.name,
            "redirect_uri": redirect_uri,
            "scope": requested_scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "require_consent": client.require_consent,
        }

    async def grant_authorization_code(
        self,
        client_id: str,
        identity_id: str,
        redirect_uri: str,
        scopes: list[str],
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
    ) -> str:
        """
        Grant authorization code after user consent.

        Args:
            client_id: OAuth client ID
            identity_id: User who granted consent
            redirect_uri: Redirect URI
            scopes: Approved scopes
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE method

        Returns:
            Authorization code
        """
        # Generate authorization code
        code = f"ac_{secrets.token_urlsafe(32)}"

        # Store code (expires in 10 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        await self.code_store.save_code(
            code=code,
            client_id=client_id,
            identity_id=identity_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            expires_at=expires_at,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        return code

    async def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict[str, Any]:
        """
        Token endpoint - exchange authorization code for tokens.

        Args:
            code: Authorization code
            client_id: OAuth client ID
            client_secret: Client secret
            redirect_uri: Redirect URI (must match)
            code_verifier: PKCE code verifier

        Returns:
            Token response with access_token, refresh_token, etc.

        Raises:
            AUTH_GRANT_INVALID: Invalid or expired code
            AUTH_REDIRECT_URI_MISMATCH: Redirect URI mismatch
            AUTH_PKCE_INVALID: PKCE verification failed
        """
        # Validate client
        client = await self.validate_client(client_id, client_secret)

        # Get authorization code
        code_data = await self.code_store.get_code(code)
        if not code_data:
            raise AUTH_GRANT_INVALID(grant_type="authorization_code")

        # Check expiration
        expires_at = datetime.fromisoformat(code_data["expires_at"])
        if datetime.utcnow() > expires_at:
            raise AUTH_GRANT_INVALID(
                grant_type="authorization_code", reason="Code expired"
            )

        # Verify one-time use
        if not await self.code_store.consume_code(code):
            raise AUTH_GRANT_INVALID(
                grant_type="authorization_code", reason="Code already used"
            )

        # Verify redirect URI
        if redirect_uri != code_data["redirect_uri"]:
            raise AUTH_REDIRECT_URI_MISMATCH(
                redirect_uri=redirect_uri,
                allowed_uris=[code_data["redirect_uri"]],
            )

        # Verify PKCE if present
        if code_data["code_challenge"]:
            if not code_verifier:
                raise AUTH_PKCE_INVALID(
                    reason="Code verifier required but not provided"
                )

            if not PKCEVerifier.verify_code_challenge(
                code_verifier,
                code_data["code_challenge"],
                code_data["code_challenge_method"],
            ):
                raise AUTH_PKCE_INVALID(reason="Code verifier verification failed")

        # Issue tokens
        identity_id = code_data["identity_id"]
        scopes = code_data["scopes"]

        access_token = await self.token_manager.issue_access_token(
            identity_id=identity_id,
            scopes=scopes,
        )

        refresh_token = await self.token_manager.issue_refresh_token(
            identity_id=identity_id,
            scopes=scopes,
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_manager.config.access_token_ttl,
            "refresh_token": refresh_token,
            "scope": " ".join(scopes),
        }

    async def client_credentials_grant(
        self, client_id: str, client_secret: str, scope: str | None = None
    ) -> dict[str, Any]:
        """
        Client Credentials grant - machine-to-machine auth.

        Args:
            client_id: OAuth client ID
            client_secret: Client secret
            scope: Requested scopes

        Returns:
            Token response with access_token

        Raises:
            AUTH_CLIENT_INVALID: Invalid client
            AUTH_SCOPE_INVALID: Invalid scope
        """
        # Validate client
        client = await self.validate_client(client_id, client_secret)

        # Verify grant type allowed
        if "client_credentials" not in client.grant_types:
            raise AUTH_CLIENT_INVALID(
                client_id=client_id,
                reason="client_credentials grant not allowed",
            )

        # Parse scopes
        requested_scopes = scope.split() if scope else client.scopes
        invalid_scopes = set(requested_scopes) - set(client.scopes)
        if invalid_scopes:
            raise AUTH_SCOPE_INVALID(
                requested_scopes=requested_scopes,
                allowed_scopes=client.scopes,
            )

        # Issue access token (no refresh token for client credentials)
        access_token = await self.token_manager.issue_access_token(
            identity_id=client_id,  # Client is the identity
            scopes=requested_scopes,
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_manager.config.access_token_ttl,
            "scope": " ".join(requested_scopes),
        }

    async def device_authorization(
        self, client_id: str, scope: str | None = None
    ) -> dict[str, Any]:
        """
        Device Authorization - initiate device flow.

        Args:
            client_id: OAuth client ID
            scope: Requested scopes

        Returns:
            Device code response with device_code, user_code, verification_uri

        Raises:
            AUTH_CLIENT_INVALID: Invalid client
        """
        # Validate client
        client = await self.validate_client(client_id)

        # Verify grant type allowed
        if "urn:ietf:params:oauth:grant-type:device_code" not in client.grant_types:
            raise AUTH_CLIENT_INVALID(
                client_id=client_id,
                reason="device_code grant not allowed",
            )

        # Parse scopes
        requested_scopes = scope.split() if scope else client.scopes

        # Generate device code and user code
        device_code = f"dc_{secrets.token_urlsafe(32)}"
        user_code = self._generate_user_code()

        # Store device code (expires in 15 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        await self.device_store.save_device_code(
            device_code=device_code,
            user_code=user_code,
            client_id=client_id,
            scopes=requested_scopes,
            expires_at=expires_at,
        )

        return {
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": f"{self.issuer}/device",
            "verification_uri_complete": f"{self.issuer}/device?user_code={user_code}",
            "expires_in": 900,  # 15 minutes
            "interval": 5,  # Poll every 5 seconds
        }

    async def device_token(
        self, device_code: str, client_id: str
    ) -> dict[str, Any]:
        """
        Device Token - poll for authorization.

        Args:
            device_code: Device code
            client_id: OAuth client ID

        Returns:
            Token response if authorized

        Raises:
            AUTH_DEVICE_CODE_PENDING: User hasn't authorized yet
            AUTH_DEVICE_CODE_EXPIRED: Device code expired
            AUTH_GRANT_INVALID: Invalid device code
        """
        # Get device code data
        code_data = await self.device_store.get_by_device_code(device_code)
        if not code_data:
            raise AUTH_GRANT_INVALID(grant_type="device_code")

        # Verify client
        if code_data["client_id"] != client_id:
            raise AUTH_CLIENT_INVALID(client_id=client_id)

        # Check expiration
        expires_at = datetime.fromisoformat(code_data["expires_at"])
        if datetime.utcnow() > expires_at:
            raise AUTH_DEVICE_CODE_EXPIRED()

        # Check status
        if code_data["status"] == "pending":
            raise AUTH_DEVICE_CODE_PENDING()

        if code_data["status"] == "denied":
            raise AUTH_GRANT_INVALID(
                grant_type="device_code", reason="User denied authorization"
            )

        # Authorized - issue tokens
        identity_id = code_data["identity_id"]
        scopes = code_data["scopes"]

        access_token = await self.token_manager.issue_access_token(
            identity_id=identity_id,
            scopes=scopes,
        )

        refresh_token = await self.token_manager.issue_refresh_token(
            identity_id=identity_id,
            scopes=scopes,
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_manager.config.access_token_ttl,
            "refresh_token": refresh_token,
            "scope": " ".join(scopes),
        }

    def _generate_user_code(self, length: int = 8) -> str:
        """
        Generate user-friendly code for device flow.

        Returns:
            Code like "WDJB-MJHT" (8 chars, grouped)
        """
        # Use uppercase letters and numbers (excluding similar chars: 0,O,1,I)
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = "".join(secrets.choice(alphabet) for _ in range(length))

        # Format as XXXX-XXXX for readability
        return f"{code[:4]}-{code[4:]}"
