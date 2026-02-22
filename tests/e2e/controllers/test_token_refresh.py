"""
TOKEN-001 to TOKEN-003: Token refresh controller tests.

Exercises: AuthController.refresh, TokenManager rotation, token store side-effects.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"refresh-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _get_tokens(client, tag=""):
    """Register + login, return (user_data, tokens_dict)."""
    email = _unique_email(tag)
    user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Refresh {tag}"}
    reg = await client.post("/auth/register", json=user)
    assert reg.status_code == 201
    login = await client.post("/auth/login", json={"email": email, "password": user["password"]})
    assert login.status_code == 200
    return user, login.json()


# ── TOKEN-001: Refresh success ────────────────────────────────────────────

class TestTokenRefresh:
    """Token refresh endpoint."""

    async def test_refresh_returns_new_tokens(self, client):
        """TOKEN-001: Valid refresh token returns new access + refresh tokens."""
        _, tokens = await _get_tokens(client, "ok")

        resp = await client.post("/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200, f"Refresh failed: {resp.status_code} {resp.text}"

        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        # New tokens should differ from the originals
        assert body["access_token"] != tokens["access_token"], "Access token should rotate"

    async def test_refreshed_token_works(self, client):
        """TOKEN-001b: The new access token should be usable for /auth/me."""
        _, tokens = await _get_tokens(client, "works")

        refresh_resp = await client.post("/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()

        # Use the new access token
        client.set_bearer_token(new_tokens["access_token"])
        me_resp = await client.get("/auth/me")
        assert me_resp.status_code == 200, f"/me failed with new token: {me_resp.status_code}"
        client.clear_auth()


# ── TOKEN-002: Old refresh token reuse ────────────────────────────────────

class TestRefreshTokenReuse:
    """Reuse of old refresh token after rotation."""

    async def test_old_refresh_token_rejected(self, client):
        """TOKEN-002: Using old refresh token after rotation should fail."""
        _, tokens = await _get_tokens(client, "reuse")
        old_refresh = tokens["refresh_token"]

        # Rotate
        resp1 = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert resp1.status_code == 200

        # Reuse old token — should be rejected
        resp2 = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert 400 <= resp2.status_code < 500, (
            f"Old refresh token should be rejected, got {resp2.status_code}"
        )


# ── TOKEN-003: Missing refresh_token ──────────────────────────────────────

class TestRefreshMissingField:
    """Missing or invalid refresh_token field."""

    async def test_missing_refresh_token_400(self, client):
        """TOKEN-003: Missing refresh_token field returns 400."""
        resp = await client.post("/auth/refresh", json={})
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body or "errors" in body

    async def test_empty_refresh_token_400(self, client):
        """TOKEN-003b: Empty refresh_token string returns 400."""
        resp = await client.post("/auth/refresh", json={"refresh_token": ""})
        assert resp.status_code == 400

    async def test_invalid_refresh_token(self, client):
        """TOKEN-003c: Garbage refresh token returns error."""
        resp = await client.post("/auth/refresh", json={
            "refresh_token": "not-a-valid-token",
        })
        assert 400 <= resp.status_code < 500
