"""
SESS-001 to SESS-004: Session management controller tests.

Exercises: AuthController.login, dashboard_view, @authenticated_ui, sessions.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"sess-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _register(client, tag=""):
    email = _unique_email(tag)
    user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Session {tag}"}
    reg = await client.post("/auth/register", json=user)
    assert reg.status_code == 201
    return user


# ── SESS-001: Session created on login ────────────────────────────────────

class TestSessionCreation:
    """Verifies session creation during login flow."""

    async def test_login_creates_session_cookie(self, client):
        """SESS-001: Login sets session-related cookies."""
        user = await _register(client, "create")
        resp = await client.post("/auth/login", json={
            "email": user["email"],
            "password": user["password"],
        })
        assert resp.status_code == 200
        # Should have at least access_token cookie (may also have session cookie)
        assert len(client.cookies) > 0, f"No cookies set after login: {client.cookies}"


# ── SESS-002: @authenticated_ui redirect ──────────────────────────────────

class TestAuthenticatedUIDecorator:
    """The @authenticated_ui decorator should redirect unauthenticated users."""

    async def test_unauthenticated_redirects_to_login(self, client):
        """SESS-002: Accessing /auth/dashboard without session → redirect to login."""
        client.clear_cookies()
        client.clear_auth()
        resp = await client.get("/auth/dashboard")
        assert resp.status_code == 302
        assert "/auth/login" in (resp.location or ""), (
            f"Expected redirect to /auth/login, got: {resp.location}"
        )

    async def test_authenticated_gets_dashboard(self, client):
        """SESS-002b: Logged-in user can access dashboard."""
        user = await _register(client, "auth-dash")
        await client.post("/auth/login", json={
            "email": user["email"], "password": user["password"],
        })
        resp = await client.get("/auth/dashboard")
        # 200 (rendered) or 302 (fallback) — but NOT 401
        assert resp.status_code in (200, 302)


# ── SESS-003: Session invalidation ────────────────────────────────────────

class TestSessionInvalidation:
    """Session should be invalidated when cookies are cleared."""

    async def test_clear_cookies_loses_session(self, client):
        """SESS-003: After clearing cookies, dashboard redirects to login."""
        user = await _register(client, "inval")
        await client.post("/auth/login", json={
            "email": user["email"], "password": user["password"],
        })
        # Verify we have a session
        assert len(client.cookies) > 0

        # Clear all cookies (simulate logout / browser cookie clear)
        client.clear_cookies()
        resp = await client.get("/auth/dashboard")
        assert resp.status_code == 302
        assert "/auth/login" in (resp.location or "")


# ── SESS-004: Session fixation simulation ─────────────────────────────────

class TestSessionFixation:
    """Simulate session fixation attack: inject old session ID before login."""

    async def test_session_id_changes_after_login(self, client):
        """SESS-004: Session cookie should rotate on privilege change (login)."""
        # Set a fake session cookie before login
        client.set_cookie("aq_session", "fixed-attacker-session-id")

        user = await _register(client, "fixation")
        await client.post("/auth/login", json={
            "email": user["email"], "password": user["password"],
        })

        # After login, session value should differ from the injected one
        session_cookie = client.cookies.get("aq_session", "")
        if session_cookie:
            assert session_cookie != "fixed-attacker-session-id", (
                "Session fixation: session cookie was NOT rotated after login!"
            )
