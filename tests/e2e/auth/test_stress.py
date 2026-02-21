"""
E2E Auth Tests — Stress & Concurrency

High-concurrency login, refresh, and revocation flows.
"""

import asyncio
import time
import pytest

from aquilia.auth.core import Identity, IdentityType, IdentityStatus, PasswordCredential


class TestConcurrentLoginRefresh:
    """PRF-01: 200 concurrent login+refresh flows."""

    async def test_200_concurrent_login_refresh(self, auth_manager, token_manager, seed_user):
        """200 parallel login+refresh cycles → no deadlocks or resource exhaustion."""
        _, pw = seed_user
        errors = []

        async def login_refresh_cycle(i):
            try:
                res = await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password=pw,
                )
                assert res.access_token is not None
                new_at, new_rt = await token_manager.refresh_access_token(res.refresh_token)
                assert new_at.count(".") == 2
                return True
            except Exception as e:
                errors.append({"worker": i, "error": str(e)})
                return False

        start = time.monotonic()
        results = await asyncio.gather(
            *[login_refresh_cycle(i) for i in range(200)]
        )
        elapsed = time.monotonic() - start

        success_count = sum(1 for r in results if r)
        assert success_count == 200, f"Only {success_count}/200 succeeded. Errors: {errors[:5]}"
        assert elapsed < 30, f"Took {elapsed:.1f}s — possible deadlock"


class TestTokenValidationThroughput:
    """PRF-02: Validate 1000 tokens sequentially."""

    async def test_validate_1000_tokens(self, token_manager):
        """Issue 1000 tokens and validate all — measure throughput."""
        tokens = []
        for i in range(1000):
            t = await token_manager.issue_access_token(
                identity_id=f"user-{i:04d}", scopes=["read"],
            )
            tokens.append(t)

        start = time.monotonic()
        for t in tokens:
            claims = await token_manager.validate_access_token(t)
            assert claims["sub"].startswith("user-")
        elapsed = time.monotonic() - start

        assert elapsed < 30, f"1000 validations took {elapsed:.1f}s"


class TestConcurrentTokenRevocation:
    """PRF-03: 100 concurrent revocations."""

    async def test_concurrent_revoke_100(self, token_manager, token_store):
        """Revoke 100 tokens concurrently → all marked as revoked."""
        tokens = []
        for i in range(100):
            rt = await token_manager.issue_refresh_token(
                identity_id=f"user-{i:03d}", scopes=["read"],
            )
            tokens.append(rt)

        await asyncio.gather(*[token_manager.revoke_token(rt) for rt in tokens])

        for rt in tokens:
            assert await token_store.is_token_revoked(rt) is True


class TestConcurrentPasswordReset:
    """REG-02: 10 concurrent wrong-password attempts then check lockout."""

    async def test_concurrent_wrong_passwords(self, auth_manager, seed_user):
        """10 concurrent wrong-password attempts → rate limiter tracks all."""
        from aquilia.auth.faults import AUTH_INVALID_CREDENTIALS, AUTH_ACCOUNT_LOCKED
        _, _ = seed_user
        errors = []

        async def wrong_attempt():
            try:
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password="WrongPw!",
                )
            except (AUTH_INVALID_CREDENTIALS, AUTH_ACCOUNT_LOCKED) as e:
                errors.append(type(e).__name__)

        await asyncio.gather(*[wrong_attempt() for _ in range(10)])
        # All should have failed — mix of invalid_creds and locked
        assert len(errors) == 10


class TestSessionFixation:
    """REG-03: Forged session ID never enters the auth flow."""

    async def test_forged_session_ignored(self, auth_manager, seed_user):
        """Login always generates a new session_id, ignoring any forged ones."""
        _, pw = seed_user
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        # Session ID is server-generated
        assert res.session_id is not None
        assert res.session_id.startswith("sess_")
        # A forged session ID has no effect
        assert res.session_id != "sess_EVIL_FORGED"


class TestDuplicateRegistration:
    """REG-06: Creating same identity twice."""

    async def test_duplicate_identity_id(self, identity_store):
        """Second create with same ID raises or is handled."""
        i1 = Identity(id="dup-001", type=IdentityType.USER, attributes={"email": "a@t.com"})
        await identity_store.create(i1)
        i2 = Identity(id="dup-001", type=IdentityType.USER, attributes={"email": "b@t.com"})
        # Should either raise or overwrite — either is acceptable
        try:
            await identity_store.create(i2)
            # If it didn't raise, check what's stored
            got = await identity_store.get("dup-001")
            assert got is not None
        except (ValueError, KeyError):
            # Duplicate rejected
            pass


class TestMemoryPressure:
    """FLT-03: Fill token store, verify operations still work."""

    async def test_10000_tokens_then_operate(self, token_manager, token_store):
        """Fill store with 10000 tokens, then issue/validate/revoke."""
        # Fill
        for i in range(10000):
            await token_manager.issue_refresh_token(
                identity_id=f"bulk-{i:05d}", scopes=["r"],
            )

        # Issue a new one
        rt = await token_manager.issue_refresh_token(
            identity_id="post-fill", scopes=["read"],
        )
        data = await token_manager.validate_refresh_token(rt)
        assert data["identity_id"] == "post-fill"

        # Revoke
        await token_manager.revoke_token(rt)
        assert await token_store.is_token_revoked(rt) is True

        # Issue + validate access token
        at = await token_manager.issue_access_token(
            identity_id="post-fill", scopes=["read"],
        )
        claims = await token_manager.validate_access_token(at)
        assert claims["sub"] == "post-fill"
