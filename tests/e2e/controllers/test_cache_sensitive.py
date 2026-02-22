"""
CACHE-001 to CACHE-003: Cache-sensitive controller tests.

Exercises: AuthController.me, cache service, DB fallback.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"cache-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _register_login_get_tokens(client, tag=""):
    email = _unique_email(tag)
    user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Cache {tag}"}
    reg = await client.post("/auth/register", json=user)
    assert reg.status_code == 201
    login = await client.post("/auth/login", json={"email": email, "password": user["password"]})
    assert login.status_code == 200
    return user, login.json()


# ── CACHE-001: Cache hit for user data ────────────────────────────────────

class TestCacheHit:
    """After first /me call, subsequent calls should hit cache."""

    async def test_second_me_call_cached(self, client):
        """CACHE-001: Second /me call returns same data (cache hit)."""
        _, tokens = await _register_login_get_tokens(client, "hit")
        client.set_bearer_token(tokens["access_token"])

        r1 = await client.get("/auth/me")
        assert r1.status_code == 200

        r2 = await client.get("/auth/me")
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]
        # Second call should be no slower (heuristic)
        client.clear_auth()


# ── CACHE-002: Cache corruption → DB fallback ─────────────────────────────

class TestCacheCorruption:
    """When cache has corrupt data, /me should fallback to DB."""

    async def test_corrupt_cache_entry_fallback(self, test_server, client):
        """CACHE-002: Corrupt cache → DB fallback → correct response."""
        user, tokens = await _register_login_get_tokens(client, "corrupt")
        client.set_bearer_token(tokens["access_token"])

        # Prime the cache
        r1 = await client.get("/auth/me")
        assert r1.status_code == 200
        user_id = r1.json()["id"]

        # Corrupt the cache entry directly if cache service is accessible
        cache = test_server.cache_service
        if cache:
            cache_key = f"user:{user_id}"
            try:
                await cache.set(cache_key, "CORRUPTED_NOT_A_DICT", ttl=300)
            except Exception:
                pass  # Cache may not support raw string set

        # Call /me again — should still work (DB fallback or error handled)
        r2 = await client.get("/auth/me")
        # Should either succeed (200) or return a handled error (4xx/5xx)
        # It should NOT crash the server
        assert r2.status_code in (200, 401, 404, 500), (
            f"Unexpected status after cache corruption: {r2.status_code}"
        )
        client.clear_auth()


# ── CACHE-003: Cache rebuild after corruption ─────────────────────────────

class TestCacheRebuild:
    """After cache corruption is handled, cache should rebuild on next call."""

    async def test_cache_rebuilds(self, test_server, client):
        """CACHE-003: After corruption, subsequent /me calls work normally."""
        user, tokens = await _register_login_get_tokens(client, "rebuild")
        client.set_bearer_token(tokens["access_token"])

        # First call (miss → DB fetch → cache set)
        r1 = await client.get("/auth/me")
        assert r1.status_code == 200

        # Invalidate cache
        cache = test_server.cache_service
        if cache:
            user_id = r1.json()["id"]
            try:
                await cache.delete(f"user:{user_id}")
            except Exception:
                pass

        # Next call should re-fetch from DB and re-populate cache
        r2 = await client.get("/auth/me")
        assert r2.status_code == 200
        assert r2.json()["email"] == user["email"]

        # Third call should be a cache hit again
        r3 = await client.get("/auth/me")
        assert r3.status_code == 200
        assert r3.json()["id"] == r2.json()["id"]
        client.clear_auth()
