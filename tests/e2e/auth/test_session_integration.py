"""
E2E Auth Tests — Session Integration

Tests identity/credential store CRUD and session-token binding.
"""

import pytest
from aquilia.auth.core import (
    Identity, IdentityType, IdentityStatus,
    PasswordCredential, ApiKeyCredential,
)


class TestIdentityStoreCRUD:
    async def test_create_and_get(self, identity_store):
        i = Identity(id="u1", type=IdentityType.USER, attributes={"email": "u1@t.com"})
        await identity_store.create(i)
        got = await identity_store.get(i.id)
        assert got.id == "u1"
        assert got.attributes["email"] == "u1@t.com"

    async def test_get_nonexistent(self, identity_store):
        assert await identity_store.get("nope") is None

    async def test_get_by_attribute(self, identity_store):
        i = Identity(id="u2", type=IdentityType.USER, attributes={"email": "find@t.com"})
        await identity_store.create(i)
        found = await identity_store.get_by_attribute("email", "find@t.com")
        assert found is not None and found.id == "u2"

    async def test_update(self, identity_store):
        i = Identity(id="u3", type=IdentityType.USER, attributes={"name": "old"})
        await identity_store.create(i)
        updated = Identity(id="u3", type=IdentityType.USER, attributes={"name": "new"})
        await identity_store.update(updated)
        got = await identity_store.get("u3")
        assert got.attributes["name"] == "new"

    async def test_delete_soft_deletes(self, identity_store):
        """delete() soft-deletes by marking status as DELETED."""
        i = Identity(id="u4", type=IdentityType.USER, attributes={})
        await identity_store.create(i)
        await identity_store.delete("u4")
        got = await identity_store.get("u4")
        assert got.status == IdentityStatus.DELETED


class TestCredentialStoreCRUD:
    async def test_password_save_and_get(self, credential_store):
        cred = PasswordCredential(identity_id="u1", password_hash="$hash$")
        await credential_store.save_password(cred)
        got = await credential_store.get_password("u1")
        assert got.password_hash == "$hash$"

    async def test_api_key_save_and_get(self, credential_store):
        cred = ApiKeyCredential(
            identity_id="s1", key_id="k1",
            key_hash="hash", prefix="ak_test_", scopes=["r"],
        )
        await credential_store.save_api_key(cred)
        got = await credential_store.get_api_key_by_prefix("ak_test_")
        assert got is not None and got.key_id == "k1"


class TestSessionTokenBinding:
    async def test_login_creates_session(self, auth_manager, seed_user):
        _, pw = seed_user
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        assert res.session_id is not None

    async def test_token_claims_contain_sid(self, auth_manager, seed_user):
        _, pw = seed_user
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        claims = await auth_manager.verify_token(res.access_token)
        assert claims.sid == res.session_id

    async def test_refresh_token_tracks_session(self, token_manager):
        rt = await token_manager.issue_refresh_token(
            identity_id="u1", scopes=["r"], session_id="sess-123",
        )
        data = await token_manager.validate_refresh_token(rt)
        assert data["session_id"] == "sess-123"

    async def test_logout_revokes_session_tokens(self, token_manager, token_store):
        rt1 = await token_manager.issue_refresh_token(
            identity_id="u1", scopes=["a"], session_id="sess-kill",
        )
        rt2 = await token_manager.issue_refresh_token(
            identity_id="u1", scopes=["b"], session_id="sess-kill",
        )
        await token_manager.revoke_tokens_by_session("sess-kill")
        assert await token_store.is_token_revoked(rt1)
        assert await token_store.is_token_revoked(rt2)
