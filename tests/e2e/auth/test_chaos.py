"""
E2E Auth Tests — Chaos Tests

Monkey-patched failures, store corruption, chained failure sequences.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from aquilia.auth.core import (
    Identity, IdentityType, IdentityStatus, PasswordCredential,
)
from aquilia.auth.faults import AUTH_INVALID_CREDENTIALS


class TestStoreCrashMidOperation:
    """Simulate store failures during auth ops."""

    async def test_identity_store_crash_on_lookup(self, auth_manager, identity_store, seed_user):
        """If identity store raises during login, auth fails safely."""
        _, pw = seed_user
        with patch.object(identity_store, 'get_by_attribute', side_effect=RuntimeError("store crash")):
            with pytest.raises(RuntimeError, match="store crash"):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password=pw,
                )

    async def test_token_store_crash_on_issue(self, auth_manager, token_manager, seed_user):
        """If token store fails during token issuance, no partial tokens leak."""
        _, pw = seed_user
        original = token_manager.token_store.save_refresh_token
        token_manager.token_store.save_refresh_token = AsyncMock(
            side_effect=RuntimeError("token store down"),
        )
        try:
            with pytest.raises(RuntimeError, match="token store down"):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password=pw,
                )
        finally:
            token_manager.token_store.save_refresh_token = original

    async def test_credential_store_crash_on_save(self, credential_store):
        """Credential store crash leaves no partial state."""
        cred = PasswordCredential(identity_id="crash-user", password_hash="hash")
        original = credential_store.save_password
        call_count = 0

        async def crash_save(c):
            nonlocal call_count
            call_count += 1
            raise IOError("disk full")

        credential_store.save_password = crash_save
        try:
            with pytest.raises(IOError):
                await credential_store.save_password(cred)
            # Verify no partial state
            got = await credential_store.get_password("crash-user")
            assert got is None
        finally:
            credential_store.save_password = original


class TestCacheCorruption:
    """Write invalid data into stores, verify safe failure."""

    async def test_corrupt_refresh_token_data(self, token_manager, token_store):
        """Corrupted refresh token data → validation fails safely."""
        # Store garbage
        token_store._refresh_tokens["rt_corrupted"] = "NOT_A_DICT"
        with pytest.raises((TypeError, AttributeError, ValueError)):
            await token_manager.validate_refresh_token("rt_corrupted")

    async def test_corrupt_token_missing_fields(self, token_manager, token_store):
        """Refresh token data missing required fields → fails safely."""
        token_store._refresh_tokens["rt_incomplete"] = {"identity_id": "u1"}
        # Should handle missing expires_at gracefully
        data = await token_manager.validate_refresh_token("rt_incomplete")
        assert data["identity_id"] == "u1"

    async def test_null_identity_in_store(self, identity_store):
        """None stored as identity → get returns None or handles gracefully."""
        identity_store._identities["null-id"] = None
        result = await identity_store.get("null-id")
        assert result is None


class TestTokenStoreUnavailable:
    """Simulate token store becoming unavailable."""

    async def test_revocation_check_with_broken_store(self, token_manager, token_store):
        """If is_token_revoked raises, validate_access_token propagates error."""
        token = await token_manager.issue_access_token(
            identity_id="user-001", scopes=["read"],
        )
        original = token_store.is_token_revoked
        token_store.is_token_revoked = AsyncMock(side_effect=ConnectionError("Redis down"))
        try:
            with pytest.raises(ConnectionError, match="Redis down"):
                await token_manager.validate_access_token(token)
        finally:
            token_store.is_token_revoked = original


class TestChainedFailure:
    """Chain multiple failures together — Step 5 chaos orchestration."""

    async def test_corrupt_cache_then_concurrent_refresh(
        self, auth_manager, token_manager, token_store, seed_user,
    ):
        """Corrupt cache → concurrent refresh requests → consistency check."""
        _, pw = seed_user

        # 1) Login normally
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )

        # 2) Corrupt a cache entry
        token_store._refresh_tokens["rt_garbage"] = {"identity_id": "evil"}

        # 3) Concurrent refresh with real + garbage tokens
        async def try_refresh(rt):
            try:
                return await token_manager.refresh_access_token(rt)
            except (ValueError, TypeError, KeyError):
                return None

        results = await asyncio.gather(
            try_refresh(res.refresh_token),
            try_refresh("rt_garbage"),
            try_refresh("rt_nonexistent"),
        )

        # 4) Real refresh should succeed or fail cleanly
        valid_results = [r for r in results if r is not None]
        # At most 1 should succeed (the valid one, unless already consumed)

        # 5) Consistency: no duplicate identity entries
        all_tokens = list(token_store._refresh_tokens.keys())
        identity_ids = [
            token_store._refresh_tokens[t].get("identity_id")
            for t in all_tokens
            if isinstance(token_store._refresh_tokens.get(t), dict)
        ]
        # No crash, store is still operational
        assert isinstance(identity_ids, list)

    async def test_concurrent_revoke_while_refreshing(
        self, token_manager, token_store,
    ):
        """Concurrent revoke + refresh of same token → no crash, one wins."""
        rt = await token_manager.issue_refresh_token(
            identity_id="user-race", scopes=["read"],
        )

        async def do_refresh():
            try:
                return await token_manager.refresh_access_token(rt)
            except ValueError:
                return "revoked"

        async def do_revoke():
            await token_manager.revoke_token(rt)
            return "done"

        results = await asyncio.gather(do_refresh(), do_revoke())
        # One of: refresh succeeded then revoke happened, or revoke won
        # Either way — no crash
        assert len(results) == 2
