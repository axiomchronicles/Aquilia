"""
E2E Auth Tests — Rate Limiting

Tests rate limiter lockout, reset, and expiration behaviour.
"""

import asyncio
import pytest
from aquilia.auth.faults import AUTH_ACCOUNT_LOCKED, AUTH_INVALID_CREDENTIALS


class TestRateLimiting:
    async def test_lockout_after_max_attempts(self, auth_manager, seed_user):
        _, _ = seed_user
        for _ in range(3):
            with pytest.raises(AUTH_INVALID_CREDENTIALS):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password="wrong",
                )
        with pytest.raises(AUTH_ACCOUNT_LOCKED):
            await auth_manager.authenticate_password(
                username="testuser@aquilia.dev", password="wrong",
            )

    async def test_reset_on_success(self, auth_manager, seed_user):
        _, pw = seed_user
        for _ in range(2):
            with pytest.raises(AUTH_INVALID_CREDENTIALS):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password="wrong",
                )
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        assert res.identity is not None
        for _ in range(2):
            with pytest.raises(AUTH_INVALID_CREDENTIALS):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password="wrong",
                )
        res2 = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        assert res2.identity is not None

    def test_remaining_attempts_decrement(self, rate_limiter):
        """Counter decrements with each record_attempt call."""
        key = "test-user-decrement"
        assert rate_limiter.get_remaining_attempts(key) == 3  # max_attempts=3
        rate_limiter.record_attempt(key)
        assert rate_limiter.get_remaining_attempts(key) == 2
        rate_limiter.record_attempt(key)
        assert rate_limiter.get_remaining_attempts(key) == 1

    def test_is_locked_out(self, rate_limiter):
        """After max_attempts, is_locked_out returns True."""
        key = "test-lockout-check"
        for _ in range(3):
            rate_limiter.record_attempt(key)
        assert rate_limiter.is_locked_out(key) is True

    async def test_lockout_expiration(self, auth_manager, seed_user):
        _, pw = seed_user
        for _ in range(3):
            with pytest.raises(AUTH_INVALID_CREDENTIALS):
                await auth_manager.authenticate_password(
                    username="testuser@aquilia.dev", password="wrong",
                )
        with pytest.raises(AUTH_ACCOUNT_LOCKED):
            await auth_manager.authenticate_password(
                username="testuser@aquilia.dev", password="wrong",
            )
        # Wait for lockout to expire (5s configured in fixture)
        await asyncio.sleep(6)
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        assert res.identity is not None
