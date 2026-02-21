"""
E2E Auth Tests — Token Lifecycle

Tests token issuance, validation, refresh, revocation, and key rotation.
"""

import time
import pytest

from aquilia.auth.tokens import KeyDescriptor, KeyAlgorithm, KeyRing, KeyStatus


class TestTokenIssuance:
    async def test_issue_and_validate_access_token(self, token_manager):
        token = await token_manager.issue_access_token(
            identity_id="user-001", scopes=["read", "write"],
            roles=["admin"], session_id="sess-001", tenant_id="tenant-001",
        )
        assert token.count(".") == 2
        claims = await token_manager.validate_access_token(token)
        assert claims["sub"] == "user-001"
        assert claims["iss"] == "aquilia-test"
        assert "read" in claims["scopes"]
        assert "admin" in claims["roles"]
        assert claims["sid"] == "sess-001"
        assert claims["tenant_id"] == "tenant-001"

    async def test_access_token_expiration(self, token_manager):
        token = await token_manager.issue_access_token(
            identity_id="user-001", scopes=["read"], ttl=-1,
        )
        with pytest.raises(ValueError, match="Token expired"):
            await token_manager.validate_access_token(token)

    async def test_malformed_token_rejected(self, token_manager):
        with pytest.raises(ValueError, match="Malformed token"):
            await token_manager.validate_access_token("not.a.valid.token.format")
        with pytest.raises(ValueError, match="Malformed token"):
            await token_manager.validate_access_token("single-segment")


class TestRefreshTokenLifecycle:
    async def test_refresh_token_roundtrip(self, token_manager):
        refresh = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["profile"], session_id="sess-001",
        )
        assert refresh.startswith("rt_")
        data = await token_manager.validate_refresh_token(refresh)
        assert data["identity_id"] == "user-001"
        assert data["scopes"] == ["profile"]
        assert data["session_id"] == "sess-001"

    async def test_refresh_token_rotation(self, token_manager):
        """refresh_access_token revokes old token and issues new pair."""
        old_refresh = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["read"],
        )
        new_access, new_refresh = await token_manager.refresh_access_token(old_refresh)
        assert new_access.count(".") == 2
        assert new_refresh.startswith("rt_")
        # Old refresh token is now revoked — validation must fail
        with pytest.raises(ValueError, match="revoked"):
            await token_manager.validate_refresh_token(old_refresh)

    async def test_invalid_refresh_token(self, token_manager):
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await token_manager.validate_refresh_token("rt_nonexistent_token")


class TestTokenRevocation:
    async def test_revoke_refresh_token(self, token_manager):
        """Revoked refresh token raises ValueError on validation."""
        refresh = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["read"],
        )
        await token_manager.revoke_token(refresh)
        with pytest.raises(ValueError, match="revoked"):
            await token_manager.validate_refresh_token(refresh)

    async def test_revoked_refresh_cannot_be_used(self, token_manager):
        """Attempting to refresh with a revoked token raises ValueError."""
        refresh = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["read"],
        )
        await token_manager.revoke_token(refresh)
        with pytest.raises(ValueError):
            await token_manager.refresh_access_token(refresh)

    async def test_revoke_tokens_by_identity(self, token_manager, token_store):
        rt1 = await token_manager.issue_refresh_token(identity_id="user-revoke", scopes=["a"])
        rt2 = await token_manager.issue_refresh_token(identity_id="user-revoke", scopes=["b"])
        await token_manager.revoke_tokens_by_identity("user-revoke")
        assert await token_store.is_token_revoked(rt1) is True
        assert await token_store.is_token_revoked(rt2) is True

    async def test_revoke_tokens_by_session(self, token_manager, token_store):
        rt1 = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["a"], session_id="sess-to-revoke",
        )
        rt2 = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["b"], session_id="sess-to-revoke",
        )
        rt3 = await token_manager.issue_refresh_token(
            identity_id="user-001", scopes=["c"], session_id="sess-keep",
        )
        await token_manager.revoke_tokens_by_session("sess-to-revoke")
        assert await token_store.is_token_revoked(rt1) is True
        assert await token_store.is_token_revoked(rt2) is True
        assert await token_store.is_token_revoked(rt3) is False


class TestKeyRotation:
    async def test_key_rotation_old_tokens_still_verify(self, token_store):
        old_key = KeyDescriptor.generate("key_old", KeyAlgorithm.RS256)
        ring = KeyRing([old_key])
        mgr = _make_token_manager(ring, token_store)
        token_old = await mgr.issue_access_token(identity_id="user-001", scopes=["read"])
        new_key = KeyDescriptor.generate("key_new", KeyAlgorithm.RS256)
        ring.add_key(new_key)
        ring.promote_key("key_new")
        claims = await mgr.validate_access_token(token_old)
        assert claims["sub"] == "user-001"
        token_new = await mgr.issue_access_token(identity_id="user-002", scopes=["write"])
        claims_new = await mgr.validate_access_token(token_new)
        assert claims_new["sub"] == "user-002"

    async def test_revoked_key_rejects_token(self, token_store):
        key = KeyDescriptor.generate("key_to_revoke", KeyAlgorithm.RS256)
        ring = KeyRing([key])
        mgr = _make_token_manager(ring, token_store)
        token = await mgr.issue_access_token(identity_id="user-001", scopes=["read"])
        new_key = KeyDescriptor.generate("key_replacement", KeyAlgorithm.RS256)
        ring.add_key(new_key)
        ring.promote_key("key_replacement")
        ring.revoke_key("key_to_revoke")
        with pytest.raises(ValueError, match="Unknown kid"):
            await mgr.validate_access_token(token)


def _make_token_manager(key_ring, token_store):
    from aquilia.auth.tokens import TokenConfig, TokenManager, KeyAlgorithm
    config = TokenConfig(
        issuer="aquilia-test", audience=["test-api"],
        access_token_ttl=300, refresh_token_ttl=3600, algorithm=KeyAlgorithm.RS256,
    )
    return TokenManager(key_ring, token_store, config)
