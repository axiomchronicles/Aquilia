"""
E2E Auth Tests — OAuth2 Flows

Tests authorization code flow (with PKCE), client credentials, and device flow.
"""

import pytest
from datetime import datetime, timedelta

from aquilia.auth.oauth import PKCEVerifier
from aquilia.auth.core import OAuthClient
from aquilia.auth.faults import (
    AUTH_CLIENT_INVALID,
    AUTH_GRANT_INVALID,
    AUTH_PKCE_INVALID,
    AUTH_REDIRECT_URI_MISMATCH,
    AUTH_SCOPE_INVALID,
    AUTH_DEVICE_CODE_PENDING,
    AUTH_DEVICE_CODE_EXPIRED,
)


class TestAuthorizationCodeFlow:
    """Full authorization code flow with PKCE."""

    async def test_full_auth_code_flow(self, oauth2_manager, seed_oauth_client):
        """Authorize → grant code → exchange for tokens."""
        client, client_secret = seed_oauth_client

        # Step 1: Generate PKCE
        code_verifier = PKCEVerifier.generate_code_verifier()
        code_challenge = PKCEVerifier.generate_code_challenge(code_verifier)

        # Step 2: Authorize (returns authorization request data)
        auth_data = await oauth2_manager.authorize(
            client_id=client.client_id,
            redirect_uri="https://test.aquilia.dev/callback",
            scope="profile email",
            state="random-state",
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        assert auth_data["client_id"] == client.client_id
        assert "profile" in auth_data["scope"]
        assert "email" in auth_data["scope"]

        # Step 3: Grant authorization code (after user consent)
        code = await oauth2_manager.grant_authorization_code(
            client_id=client.client_id,
            identity_id="user-e2e-001",
            redirect_uri="https://test.aquilia.dev/callback",
            scopes=["profile", "email"],
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        assert code.startswith("ac_")

        # Step 4: Exchange code for tokens
        token_response = await oauth2_manager.exchange_authorization_code(
            code=code,
            client_id=client.client_id,
            client_secret=client_secret,
            redirect_uri="https://test.aquilia.dev/callback",
            code_verifier=code_verifier,
        )
        assert "access_token" in token_response
        assert "refresh_token" in token_response
        assert token_response["token_type"] == "Bearer"
        assert token_response["expires_in"] == 300

    async def test_pkce_verification_failure(self, oauth2_manager, seed_oauth_client):
        """Wrong PKCE verifier raises AUTH_PKCE_INVALID."""
        client, client_secret = seed_oauth_client

        code_verifier = PKCEVerifier.generate_code_verifier()
        code_challenge = PKCEVerifier.generate_code_challenge(code_verifier)

        code = await oauth2_manager.grant_authorization_code(
            client_id=client.client_id,
            identity_id="user-001",
            redirect_uri="https://test.aquilia.dev/callback",
            scopes=["profile"],
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        with pytest.raises(AUTH_PKCE_INVALID):
            await oauth2_manager.exchange_authorization_code(
                code=code,
                client_id=client.client_id,
                client_secret=client_secret,
                redirect_uri="https://test.aquilia.dev/callback",
                code_verifier="wrong_verifier_that_does_not_match_the_challenge",
            )

    async def test_authorization_code_reuse(self, oauth2_manager, seed_oauth_client):
        """Second exchange of same code raises AUTH_GRANT_INVALID."""
        client, client_secret = seed_oauth_client

        code = await oauth2_manager.grant_authorization_code(
            client_id=client.client_id,
            identity_id="user-001",
            redirect_uri="https://test.aquilia.dev/callback",
            scopes=["profile"],
        )

        # First exchange succeeds
        await oauth2_manager.exchange_authorization_code(
            code=code,
            client_id=client.client_id,
            client_secret=client_secret,
            redirect_uri="https://test.aquilia.dev/callback",
        )

        # Second exchange fails (one-time use)
        with pytest.raises(AUTH_GRANT_INVALID):
            await oauth2_manager.exchange_authorization_code(
                code=code,
                client_id=client.client_id,
                client_secret=client_secret,
                redirect_uri="https://test.aquilia.dev/callback",
            )

    async def test_redirect_uri_mismatch(self, oauth2_manager, seed_oauth_client):
        """Wrong redirect URI raises AUTH_REDIRECT_URI_MISMATCH."""
        client, _ = seed_oauth_client

        with pytest.raises(AUTH_REDIRECT_URI_MISMATCH):
            await oauth2_manager.authorize(
                client_id=client.client_id,
                redirect_uri="https://evil.com/callback",
                scope="profile",
            )

    async def test_invalid_scope_request(self, oauth2_manager, seed_oauth_client):
        """Requesting a scope not registered raises AUTH_SCOPE_INVALID."""
        client, _ = seed_oauth_client

        verifier = PKCEVerifier.generate_code_verifier()
        challenge = PKCEVerifier.generate_code_challenge(verifier)

        with pytest.raises(AUTH_SCOPE_INVALID):
            await oauth2_manager.authorize(
                client_id=client.client_id,
                redirect_uri="https://test.aquilia.dev/callback",
                scope="profile admin superpower",
                code_challenge=challenge,
            )


class TestClientCredentialsGrant:
    """Machine-to-machine authentication."""

    async def test_client_credentials_grant(self, oauth2_manager, oauth_client_store, password_hasher):
        """Client credentials grant issues access token (no refresh)."""
        raw_secret = OAuthClient.generate_client_secret()
        secret_hash = password_hasher.hash(raw_secret)

        client = OAuthClient(
            client_id="m2m-service",
            client_secret_hash=secret_hash,
            name="M2M Service",
            grant_types=["client_credentials"],
            redirect_uris=[],
            scopes=["api.read", "api.write"],
            require_pkce=False,
        )
        await oauth_client_store.create(client)

        result = await oauth2_manager.client_credentials_grant(
            client_id="m2m-service",
            client_secret=raw_secret,
            scope="api.read api.write",
        )
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert "refresh_token" not in result  # No refresh for client_credentials


class TestDeviceFlow:
    """Device authorization flow (TV/CLI devices)."""

    async def test_device_authorization_flow(
        self, oauth2_manager, oauth_client_store, device_code_store,
    ):
        """Full device flow: request code → user authorizes → poll for token."""
        client = OAuthClient(
            client_id="cli-device",
            client_secret_hash=None,
            name="CLI Tool",
            grant_types=["urn:ietf:params:oauth:grant-type:device_code"],
            redirect_uris=[],
            scopes=["profile", "read"],
            require_pkce=False,
        )
        await oauth_client_store.create(client)

        # Step 1: Request device authorization
        device_resp = await oauth2_manager.device_authorization(
            client_id="cli-device",
            scope="profile read",
        )
        assert "device_code" in device_resp
        assert "user_code" in device_resp
        assert device_resp["expires_in"] == 900

        device_code = device_resp["device_code"]
        user_code = device_resp["user_code"]

        # Step 2: Poll before user authorizes → pending
        with pytest.raises(AUTH_DEVICE_CODE_PENDING):
            await oauth2_manager.device_token(
                device_code=device_code,
                client_id="cli-device",
            )

        # Step 3: User authorizes via user_code
        await device_code_store.authorize_device_code(user_code, "user-e2e-001")

        # Step 4: Poll again → token issued
        token_resp = await oauth2_manager.device_token(
            device_code=device_code,
            client_id="cli-device",
        )
        assert "access_token" in token_resp
        assert "refresh_token" in token_resp


class TestPKCEUtilities:
    """PKCE (Proof Key for Code Exchange) utility tests."""

    def test_code_verifier_length(self):
        """Code verifier length is within RFC spec."""
        verifier = PKCEVerifier.generate_code_verifier(128)
        assert 43 <= len(verifier) <= 128

    def test_code_challenge_s256(self):
        """S256 challenge is SHA256 hash of verifier."""
        verifier = PKCEVerifier.generate_code_verifier()
        challenge = PKCEVerifier.generate_code_challenge(verifier, "S256")
        assert challenge != verifier  # S256 transforms the value

    def test_pkce_roundtrip_verification(self):
        """Verifier matches its own challenge."""
        verifier = PKCEVerifier.generate_code_verifier()
        challenge = PKCEVerifier.generate_code_challenge(verifier)
        assert PKCEVerifier.verify_code_challenge(verifier, challenge) is True

    def test_pkce_wrong_verifier_fails(self):
        """Wrong verifier does not match challenge."""
        verifier = PKCEVerifier.generate_code_verifier()
        challenge = PKCEVerifier.generate_code_challenge(verifier)
        assert PKCEVerifier.verify_code_challenge("wrong_verifier", challenge) is False
