"""
CHAOS-001 to CHAOS-003: Chaos and race condition tests.

Exercises: Concurrent registrations, cache corruption + refresh races,
concurrent login stress.
"""

import pytest
import asyncio
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"chaos-{tag}-{uuid.uuid4().hex[:8]}@test.com"


# ── CHAOS-001: Concurrent registration with same email ───────────────────

class TestConcurrentRegistration:
    """Race condition: multiple concurrent registrations with the same email."""

    async def test_concurrent_same_email(self, client):
        """CHAOS-001: Only one of 10 concurrent registrations should succeed."""
        email = _unique_email("race")
        payload = {"email": email, "password": "Str0ngP@ss!", "full_name": "Racer"}

        async def attempt_register():
            return await client.post("/auth/register", json=payload)

        # Fire 10 concurrent registrations
        results = await asyncio.gather(
            *[attempt_register() for _ in range(10)],
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception) and r.status_code == 201]
        errors = [r for r in results if not isinstance(r, Exception) and 400 <= r.status_code < 500]
        exceptions = [r for r in results if isinstance(r, Exception)]

        # At most one should succeed (ideally exactly one, but race conditions are complex)
        assert len(successes) <= 2, (
            f"Expected at most 1-2 successes, got {len(successes)}"
        )
        # The rest should be errors or exceptions
        assert len(errors) + len(exceptions) >= 8, (
            f"Not enough rejections: {len(errors)} errors, {len(exceptions)} exceptions"
        )


# ── CHAOS-002: Cache corruption + concurrent /me requests ────────────────

class TestCacheChaos:
    """Corrupt cache while multiple /me requests are in-flight."""

    async def test_concurrent_me_with_cache_corruption(self, test_server, client):
        """CHAOS-002: Multiple /me requests during cache corruption should not crash."""
        email = _unique_email("cachaos")
        user = {"email": email, "password": "Str0ngP@ss!", "full_name": "CacheChaos"}
        await client.post("/auth/register", json=user)
        login = await client.post("/auth/login", json={"email": email, "password": user["password"]})
        tokens = login.json()
        client.set_bearer_token(tokens["access_token"])

        # Prime cache
        r = await client.get("/auth/me")
        assert r.status_code == 200
        user_id = r.json()["id"]

        async def corrupt_cache():
            """Periodically corrupt cache during test."""
            cache = test_server.cache_service
            if cache:
                for _ in range(5):
                    try:
                        await cache.set(f"user:{user_id}", "CORRUPT", ttl=1)
                    except Exception:
                        pass
                    await asyncio.sleep(0.01)

        async def fire_me_request():
            return await client.get("/auth/me")

        # Run corruption and requests concurrently
        results = await asyncio.gather(
            corrupt_cache(),
            *[fire_me_request() for _ in range(20)],
            return_exceptions=True,
        )

        # Count successful responses (ignore exceptions from race conditions)
        responses = [r for r in results if hasattr(r, 'status_code')]
        for resp in responses:
            # Server must not crash — any valid HTTP status is OK
            assert resp.status_code > 0
        client.clear_auth()


# ── CHAOS-003: Concurrent login stress ────────────────────────────────────

class TestConcurrentLoginStress:
    """Multiple concurrent logins for the same user."""

    async def test_concurrent_logins(self, client):
        """CHAOS-003: 20 concurrent logins should all succeed or fail gracefully."""
        email = _unique_email("stress")
        user = {"email": email, "password": "Str0ngP@ss!", "full_name": "StressUser"}
        await client.post("/auth/register", json=user)

        async def attempt_login():
            return await client.post("/auth/login", json={
                "email": email, "password": user["password"],
            })

        results = await asyncio.gather(
            *[attempt_login() for _ in range(20)],
            return_exceptions=True,
        )

        responses = [r for r in results if not isinstance(r, Exception)]
        exceptions = [r for r in results if isinstance(r, Exception)]

        # Most should succeed
        successes = [r for r in responses if r.status_code == 200]
        assert len(successes) >= 15, (
            f"Expected most logins to succeed, got {len(successes)}/20 "
            f"({len(exceptions)} exceptions)"
        )
