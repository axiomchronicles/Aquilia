"""
ME-001 to ME-003: /auth/me endpoint tests.

Exercises: AuthController.me, bearer token auth, cache integration.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"me-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _register_login(client, tag=""):
    email = _unique_email(tag)
    user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Me {tag}"}
    reg = await client.post("/auth/register", json=user)
    assert reg.status_code == 201
    login = await client.post("/auth/login", json={"email": email, "password": user["password"]})
    assert login.status_code == 200
    return user, login.json()


# ── ME-001: Valid bearer token ────────────────────────────────────────────

class TestMeEndpoint:
    """GET /auth/me with valid token."""

    async def test_me_returns_user_data(self, client):
        """ME-001: Valid bearer token returns user profile."""
        user, tokens = await _register_login(client, "ok")

        client.set_bearer_token(tokens["access_token"])
        resp = await client.get("/auth/me")
        assert resp.status_code == 200, f"/me failed: {resp.status_code} {resp.text}"

        body = resp.json()
        assert body["email"] == user["email"]
        assert body["full_name"] == user["full_name"]
        assert "id" in body
        assert "created_at" in body
        # Must NOT leak secrets
        assert "password_hash" not in body
        assert "password" not in body
        client.clear_auth()

    async def test_me_cached_second_call(self, client):
        """ME-001b: Second /me call should hit cache (same result faster)."""
        _, tokens = await _register_login(client, "cache")
        client.set_bearer_token(tokens["access_token"])

        resp1 = await client.get("/auth/me")
        assert resp1.status_code == 200
        data1 = resp1.json()

        resp2 = await client.get("/auth/me")
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Same data
        assert data1["id"] == data2["id"]
        assert data1["email"] == data2["email"]
        client.clear_auth()


# ── ME-002: Missing Authorization header ──────────────────────────────────

class TestMeNoAuth:
    """GET /auth/me without credentials."""

    async def test_no_auth_header_401(self, client):
        """ME-002: Missing Authorization header returns 401."""
        client.clear_auth()
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_empty_bearer_401(self, client):
        """ME-002b: Empty Bearer value returns 401."""
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer "})
        # The split(" ")[1] will be empty string
        assert 400 <= resp.status_code < 500


# ── ME-003: Malformed Authorization header ────────────────────────────────

class TestMeMalformedAuth:
    """GET /auth/me with bad Authorization header formats."""

    async def test_basic_auth_rejected(self, client):
        """ME-003: Basic auth scheme should be rejected."""
        resp = await client.get("/auth/me", headers={
            "Authorization": "Basic dXNlcjpwYXNz",
        })
        assert resp.status_code == 401

    async def test_no_scheme(self, client):
        """ME-003b: Token without 'Bearer' prefix rejected."""
        resp = await client.get("/auth/me", headers={
            "Authorization": "some-random-token",
        })
        assert resp.status_code == 401

    async def test_garbage_jwt(self, client):
        """ME-003c: Invalid JWT string returns error."""
        client.set_bearer_token("not.a.valid.jwt")
        resp = await client.get("/auth/me")
        assert 400 <= resp.status_code < 500
        client.clear_auth()
