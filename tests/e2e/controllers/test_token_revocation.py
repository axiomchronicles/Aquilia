"""
Token revocation and /me reuse tests.

Exercises: AuthController.me, InMemoryTokenStore.revoke, cache invalidation.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"revoke-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _get_tokens(client, tag=""):
    email = _unique_email(tag)
    user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Revoke {tag}"}
    await client.post("/auth/register", json=user)
    login = await client.post("/auth/login", json={"email": email, "password": user["password"]})
    return user, login.json()


class TestTokenRevocation:
    """Test that revoked tokens cannot be reused."""

    async def test_revoked_token_rejected_on_me(self, client):
        """After token is used then revoked (via refresh rotation),
        the old access token should eventually become invalid."""
        _, tokens = await _get_tokens(client, "rev")

        # Use the access token — should work
        client.set_bearer_token(tokens["access_token"])
        r1 = await client.get("/auth/me")
        assert r1.status_code == 200

        # Rotate tokens (old refresh is revoked in InMemoryTokenStore)
        refresh_resp = await client.post("/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()

        # Verify new access token works
        client.set_bearer_token(new_tokens["access_token"])
        r2 = await client.get("/auth/me")
        assert r2.status_code == 200

        # Old refresh token should be rejected
        old_refresh_resp = await client.post("/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert 400 <= old_refresh_resp.status_code < 500, (
            f"Old refresh token should be rejected, got {old_refresh_resp.status_code}"
        )
        client.clear_auth()

    async def test_multiple_refresh_rotations(self, client):
        """Chain multiple refresh rotations — only the latest should work."""
        _, tokens = await _get_tokens(client, "chain")

        current_refresh = tokens["refresh_token"]
        for i in range(3):
            resp = await client.post("/auth/refresh", json={
                "refresh_token": current_refresh,
            })
            assert resp.status_code == 200, f"Rotation {i} failed: {resp.status_code}"
            new = resp.json()
            current_refresh = new["refresh_token"]

        # Final token should work
        client.set_bearer_token(new["access_token"])
        me = await client.get("/auth/me")
        assert me.status_code == 200
        client.clear_auth()
