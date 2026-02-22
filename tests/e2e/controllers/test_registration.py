"""
REG-001 to REG-004: Registration controller tests.

Exercises: AuthController.register, serializers, ORM, file uploads, faults.
"""

import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────

def _unique_email(tag: str = "") -> str:
    import uuid
    return f"reg-{tag}-{uuid.uuid4().hex[:8]}@test.com"


# ── REG-001: Registration success (JSON) ─────────────────────────────────

class TestRegistrationJSON:
    """Registration via JSON payload."""

    async def test_register_success(self, client):
        """REG-001: Valid JSON registration returns 201 with user data."""
        payload = {
            "email": _unique_email("json"),
            "password": "Str0ngP@ss!",
            "full_name": "JSON Tester",
        }
        resp = await client.post("/auth/register", json=payload)

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["email"] == payload["email"]
        assert body["full_name"] == payload["full_name"]
        assert "id" in body
        assert "created_at" in body
        # Password hash must NOT be exposed
        assert "password" not in body
        assert "password_hash" not in body

    async def test_register_returns_id(self, client):
        """Registered user ID should be a positive integer."""
        payload = {
            "email": _unique_email("id"),
            "password": "Str0ngP@ss!",
            "full_name": "ID Check",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        assert isinstance(resp.json()["id"], int)
        assert resp.json()["id"] > 0


# ── REG-002: Registration success (form) ─────────────────────────────────

class TestRegistrationForm:
    """Registration via url-encoded form (browser flow)."""

    async def test_register_form_redirect(self, client):
        """REG-002: Form registration redirects to login page."""
        payload = {
            "email": _unique_email("form"),
            "password": "Str0ngP@ss!",
            "full_name": "Form Tester",
        }
        resp = await client.post("/auth/register", data=payload)

        # Should redirect (302) to /auth/login
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
        assert "/auth/login" in (resp.location or "")


# ── REG-003: Duplicate email ─────────────────────────────────────────────

class TestDuplicateRegistration:
    """Attempting to register with an existing email."""

    async def test_duplicate_email_rejected(self, client):
        """REG-003: Second registration with same email raises fault."""
        email = _unique_email("dup")
        payload = {"email": email, "password": "Str0ngP@ss!", "full_name": "First"}

        resp1 = await client.post("/auth/register", json=payload)
        assert resp1.status_code == 201

        # Attempt duplicate
        resp2 = await client.post("/auth/register", json=payload)
        # Should return an error status (4xx)
        assert 400 <= resp2.status_code < 500, (
            f"Duplicate email should be rejected, got {resp2.status_code}"
        )


# ── REG-004: Validation errors ───────────────────────────────────────────

class TestRegistrationValidation:
    """Serializer and input validation for registration."""

    async def test_missing_email(self, client):
        """Missing email field should return 400."""
        resp = await client.post("/auth/register", json={
            "password": "Str0ngP@ss!",
            "full_name": "No Email",
        })
        assert 400 <= resp.status_code < 500

    async def test_missing_password(self, client):
        """Missing password field should return 400."""
        resp = await client.post("/auth/register", json={
            "email": _unique_email("nopw"),
            "full_name": "No Password",
        })
        assert 400 <= resp.status_code < 500

    async def test_empty_body(self, client):
        """Empty JSON body should return 400."""
        resp = await client.post("/auth/register", json={})
        assert 400 <= resp.status_code < 500

    async def test_invalid_json(self, client):
        """Malformed body should return 400."""
        resp = await client.post(
            "/auth/register",
            body=b"not json at all",
            headers={"content-type": "application/json"},
        )
        assert 400 <= resp.status_code < 500
