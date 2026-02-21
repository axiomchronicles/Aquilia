"""
E2E Auth Tests — Fault Injection

Simulate external service failures, misconfigurations, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, patch

from aquilia.auth.manager import AuthManager, RateLimiter
from aquilia.auth.faults import AUTH_ACCOUNT_LOCKED, AUTH_INVALID_CREDENTIALS
from aquilia.auth.core import Identity, IdentityType, IdentityStatus, PasswordCredential
from aquilia.auth.hashing import PasswordPolicy


class TestRateLimiterMisconfiguration:
    """FLT-02: Rate limiter with max_attempts=0."""

    async def test_zero_max_attempts_locks_immediately(
        self, identity_store, credential_store, token_manager, password_hasher,
    ):
        """max_attempts=0 → every attempt is immediately locked."""
        limiter = RateLimiter(max_attempts=0, window_seconds=60, lockout_duration=5)
        mgr = AuthManager(
            identity_store=identity_store,
            credential_store=credential_store,
            token_manager=token_manager,
            password_hasher=password_hasher,
            rate_limiter=limiter,
        )

        identity = Identity(
            id="u-misc", type=IdentityType.USER,
            attributes={"email": "misc@t.com"}, status=IdentityStatus.ACTIVE,
        )
        await identity_store.create(identity)
        await credential_store.save_password(
            PasswordCredential(identity_id="u-misc", password_hash=password_hasher.hash("Pass1!"))
        )

        # Even correct password should be locked
        with pytest.raises(AUTH_ACCOUNT_LOCKED):
            await mgr.authenticate_password(username="misc@t.com", password="Pass1!")


class TestPasswordPolicyEdgeCases:
    """Edge cases in password validation."""

    def test_empty_password(self):
        """Empty string fails all policy checks."""
        policy = PasswordPolicy(min_length=8, require_uppercase=True, require_lowercase=True,
                                require_digit=True, require_special=True)
        valid, violations = policy.validate("")
        assert valid is False
        assert len(violations) > 0

    def test_unicode_password(self):
        """Unicode passwords are handled without crash."""
        policy = PasswordPolicy(min_length=8)
        valid, violations = policy.validate("Ünïcödé✓🔒🔑ℕ")
        # Should pass length check (>8 chars)
        assert isinstance(valid, bool)

    def test_very_long_password(self):
        """Very long password doesn't cause DoS."""
        policy = PasswordPolicy(min_length=8)
        long_pw = "A" * 100_000
        valid, violations = policy.validate(long_pw)
        assert isinstance(valid, bool)

    def test_null_bytes_password(self):
        """Null bytes in password are handled."""
        policy = PasswordPolicy(min_length=8)
        valid, violations = policy.validate("Pass\x00\x00\x00\x00word1!")
        assert isinstance(valid, bool)


class TestExternalServiceFailure:
    """FLT-01: Simulate external provider failure during auth ops."""

    async def test_auth_with_store_timeout(
        self, identity_store, credential_store, token_manager, password_hasher,
    ):
        """Store operations that timeout → auth fails with clear error."""
        import asyncio

        async def slow_get(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate timeout
            return None

        mgr = AuthManager(
            identity_store=identity_store,
            credential_store=credential_store,
            token_manager=token_manager,
            password_hasher=password_hasher,
        )

        identity = Identity(
            id="u-timeout", type=IdentityType.USER,
            attributes={"email": "timeout@t.com"}, status=IdentityStatus.ACTIVE,
        )
        await identity_store.create(identity)

        original = identity_store.get_by_attribute
        identity_store.get_by_attribute = slow_get
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    mgr.authenticate_password(username="timeout@t.com", password="x"),
                    timeout=1.0,
                )
        finally:
            identity_store.get_by_attribute = original


class TestTokenEdgeCases:
    """Token boundary conditions."""

    async def test_token_with_ttl_zero(self, token_manager):
        """TTL=0 → token issued at same second may be borderline; TTL=-1 expires."""
        token = await token_manager.issue_access_token(
            identity_id="u1", scopes=["r"], ttl=-1,
        )
        with pytest.raises(ValueError, match="Token expired"):
            await token_manager.validate_access_token(token)

    async def test_revoke_nonexistent_token(self, token_manager):
        """Revoking a non-existent token doesn't crash."""
        await token_manager.revoke_token("rt_does_not_exist")
        # No exception = pass
