"""
E2E Auth Tests — API Key Authentication

Tests API key generation, authentication, expiration, revocation, and scope checks.
"""

import pytest
from datetime import datetime, timedelta

from aquilia.auth.core import (
    ApiKeyCredential,
    CredentialStatus,
    Identity,
    IdentityType,
    IdentityStatus,
)
from aquilia.auth.faults import (
    AUTH_INVALID_CREDENTIALS,
    AUTH_KEY_EXPIRED,
    AUTH_KEY_REVOKED,
    AUTH_ACCOUNT_SUSPENDED,
    AUTHZ_INSUFFICIENT_SCOPE,
)


class TestApiKeyAuthentication:
    """API key authentication scenarios."""

    async def test_authenticate_valid_api_key(self, auth_manager, seed_api_key):
        """Valid API key returns AuthResult with correct identity."""
        identity, raw_key, credential = seed_api_key
        result = await auth_manager.authenticate_api_key(api_key=raw_key)

        assert result.identity.id == identity.id
        assert result.metadata["auth_method"] == "api_key"
        assert result.metadata["key_id"] == "key-e2e-001"
        assert "read" in result.metadata["scopes"]
        assert "write" in result.metadata["scopes"]

    async def test_invalid_api_key(self, auth_manager, seed_api_key):
        """Invalid API key raises AUTH_INVALID_CREDENTIALS."""
        with pytest.raises(AUTH_INVALID_CREDENTIALS):
            await auth_manager.authenticate_api_key(
                api_key="ak_test_totally_fake_key_that_does_not_exist"
            )

    async def test_short_api_key_rejected(self, auth_manager):
        """API key shorter than 8 chars raises AUTH_INVALID_CREDENTIALS."""
        with pytest.raises(AUTH_INVALID_CREDENTIALS):
            await auth_manager.authenticate_api_key(api_key="short")

    async def test_expired_api_key(
        self, auth_manager, identity_store, credential_store,
    ):
        """Expired API key raises AUTH_KEY_EXPIRED."""
        identity = Identity(
            id="svc-expired",
            type=IdentityType.SERVICE,
            attributes={"name": "Expired Service"},
            status=IdentityStatus.ACTIVE,
        )
        await identity_store.create(identity)

        raw_key = ApiKeyCredential.generate_key(env="test")
        credential = ApiKeyCredential(
            identity_id=identity.id,
            key_id="key-expired",
            key_hash=ApiKeyCredential.hash_key(raw_key),
            prefix=raw_key[:8],
            scopes=["read"],
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Already expired
        )
        await credential_store.save_api_key(credential)

        with pytest.raises(AUTH_KEY_EXPIRED):
            await auth_manager.authenticate_api_key(api_key=raw_key)

    async def test_revoked_api_key(
        self, auth_manager, identity_store, credential_store,
    ):
        """Revoked API key raises AUTH_KEY_REVOKED."""
        identity = Identity(
            id="svc-revoked",
            type=IdentityType.SERVICE,
            attributes={"name": "Revoked Service"},
            status=IdentityStatus.ACTIVE,
        )
        await identity_store.create(identity)

        raw_key = ApiKeyCredential.generate_key(env="test")
        credential = ApiKeyCredential(
            identity_id=identity.id,
            key_id="key-revoked",
            key_hash=ApiKeyCredential.hash_key(raw_key),
            prefix=raw_key[:8],
            scopes=["read"],
            status=CredentialStatus.REVOKED,
        )
        await credential_store.save_api_key(credential)

        with pytest.raises(AUTH_KEY_REVOKED):
            await auth_manager.authenticate_api_key(api_key=raw_key)

    async def test_scope_enforcement(self, auth_manager, seed_api_key):
        """Missing required scopes raises AUTHZ_INSUFFICIENT_SCOPE."""
        _, raw_key, _ = seed_api_key

        with pytest.raises(AUTHZ_INSUFFICIENT_SCOPE):
            await auth_manager.authenticate_api_key(
                api_key=raw_key,
                required_scopes=["admin", "delete"],
            )

    async def test_suspended_identity_via_api_key(
        self, auth_manager, identity_store, credential_store,
    ):
        """API key belonging to suspended identity raises AUTH_ACCOUNT_SUSPENDED."""
        identity = Identity(
            id="svc-suspended",
            type=IdentityType.SERVICE,
            attributes={"name": "Suspended Service"},
            status=IdentityStatus.SUSPENDED,
        )
        await identity_store.create(identity)

        raw_key = ApiKeyCredential.generate_key(env="test")
        credential = ApiKeyCredential(
            identity_id=identity.id,
            key_id="key-suspended-svc",
            key_hash=ApiKeyCredential.hash_key(raw_key),
            prefix=raw_key[:8],
            scopes=["read"],
        )
        await credential_store.save_api_key(credential)

        with pytest.raises(AUTH_ACCOUNT_SUSPENDED):
            await auth_manager.authenticate_api_key(api_key=raw_key)


class TestApiKeyGeneration:
    """API key utility functions."""

    def test_generate_key_format(self):
        """Generated key has correct prefix format."""
        key_live = ApiKeyCredential.generate_key(env="live")
        assert key_live.startswith("ak_live_")

        key_test = ApiKeyCredential.generate_key(env="test")
        assert key_test.startswith("ak_test_")

    def test_hash_key_deterministic(self):
        """Same key always produces the same hash."""
        key = "ak_test_sample_key"
        h1 = ApiKeyCredential.hash_key(key)
        h2 = ApiKeyCredential.hash_key(key)
        assert h1 == h2

    def test_different_keys_different_hashes(self):
        """Different keys produce different hashes."""
        k1 = ApiKeyCredential.generate_key()
        k2 = ApiKeyCredential.generate_key()
        assert ApiKeyCredential.hash_key(k1) != ApiKeyCredential.hash_key(k2)
