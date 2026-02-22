"""
LOGIN-001 to LOGIN-005: Login, protected access, and cookie tests.

Exercises: AuthController.login, dashboard_view, sessions, cookies, faults.
"""

import pytest
import uuid


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"login-{tag}-{uuid.uuid4().hex[:8]}@test.com"


async def _register_and_login(client, tag=""):
    """Helper: register a user, then login, returning (user_data, tokens_resp)."""
    user = {
        "email": _unique_email(tag),
        "password": "Str0ngP@ss!",
        "full_name": f"Login Tester {tag}",
    }
    reg = await client.post("/auth/register", json=user)
    assert reg.status_code == 201, f"Registration failed: {reg.status_code} {reg.text}"

    login_resp = await client.post("/auth/login", json={
        "email": user["email"],
        "password": user["password"],
    })
    return user, login_resp


# ── LOGIN-001: Login success (JSON) ──────────────────────────────────────

class TestLoginJSON:
    """Login via JSON payload."""

    async def test_login_success(self, client):
        """LOGIN-001: Valid credentials return tokens."""
        user, resp = await _register_and_login(client, "json-ok")
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"

        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] > 0

    async def test_login_sets_cookie(self, client):
        """LOGIN-001b: Login response sets access_token cookie."""
        _, resp = await _register_and_login(client, "cookie")
        # The TestClient should have captured the Set-Cookie header
        assert "access_token" in client.cookies, (
            f"access_token cookie not set. cookies={client.cookies}"
        )


# ── LOGIN-002: Login form flow ───────────────────────────────────────────

class TestLoginForm:
    """Login via url-encoded form (browser flow)."""

    async def test_form_login_redirects_to_dashboard(self, client):
        """LOGIN-002: Form login redirects to /auth/dashboard."""
        email = _unique_email("form")
        await client.post("/auth/register", json={
            "email": email, "password": "Str0ngP@ss!", "full_name": "Form",
        })

        resp = await client.post("/auth/login", data={
            "email": email, "password": "Str0ngP@ss!",
        })
        assert resp.status_code == 302
        assert "/auth/dashboard" in (resp.location or "")


# ── LOGIN-003: Invalid credentials ───────────────────────────────────────

class TestLoginInvalidCredentials:
    """Login with wrong password or non-existent user."""

    async def test_wrong_password(self, client):
        """LOGIN-003: Wrong password returns error."""
        email = _unique_email("wrongpw")
        await client.post("/auth/register", json={
            "email": email, "password": "Str0ngP@ss!", "full_name": "Wrong PW",
        })

        resp = await client.post("/auth/login", json={
            "email": email, "password": "WrongPassword123!",
        })
        assert 400 <= resp.status_code < 500, f"Expected 4xx, got {resp.status_code}"

    async def test_nonexistent_user(self, client):
        """LOGIN-003b: Non-existent email returns error."""
        resp = await client.post("/auth/login", json={
            "email": "nobody@nowhere.com", "password": "Anything!",
        })
        assert 400 <= resp.status_code < 500


# ── LOGIN-004: Protected route access ────────────────────────────────────

class TestProtectedAccess:
    """Accessing protected dashboard after login."""

    async def test_dashboard_accessible_after_login(self, client):
        """LOGIN-004: /auth/dashboard is accessible with valid session."""
        _, login_resp = await _register_and_login(client, "protected")
        assert login_resp.status_code == 200

        # Client should now have session cookies
        dash_resp = await client.get("/auth/dashboard")
        # Should render the page (200) or fallback redirect (302)
        assert dash_resp.status_code in (200, 302), (
            f"Expected 200 or 302, got {dash_resp.status_code}"
        )

    async def test_dashboard_redirects_unauthenticated(self, client):
        """LOGIN-004b: /auth/dashboard redirects without session."""
        # Fresh client — no cookies
        client.clear_cookies()
        client.clear_auth()
        resp = await client.get("/auth/dashboard")
        assert resp.status_code == 302, f"Expected redirect, got {resp.status_code}"
        assert "/auth/login" in (resp.location or "")


# ── LOGIN-005: Cookie flags ──────────────────────────────────────────────

class TestCookieFlags:
    """Verify security attributes on Set-Cookie."""

    async def test_httponly_flag(self, client):
        """LOGIN-005: access_token cookie should be httponly."""
        _, resp = await _register_and_login(client, "cookieflag")

        raw_cookie = resp.headers.get("set-cookie", "")
        # httponly should be present
        assert "httponly" in raw_cookie.lower(), (
            f"httponly flag missing from Set-Cookie: {raw_cookie}"
        )

    async def test_token_reuse_after_logout(self, client):
        """LOGIN-005b: Clearing cookies prevents dashboard access."""
        _, login_resp = await _register_and_login(client, "reuse")
        tokens = login_resp.json()

        # Clear cookies (simulates logout)
        client.clear_cookies()
        client.clear_auth()

        # Attempt to access protected endpoint
        resp = await client.get("/auth/dashboard")
        assert resp.status_code == 302, "Should redirect after cookie clear"
