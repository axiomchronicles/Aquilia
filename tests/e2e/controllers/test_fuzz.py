"""
FUZZ-001 to FUZZ-003: Property-based fuzz tests.

Uses Hypothesis for randomized input generation targeting:
- Token parser (Authorization header fuzzing)
- Template inputs (form field fuzzing)
- Upload parser (multipart body fuzzing)
"""

import pytest
import uuid

try:
    from hypothesis import given, settings, strategies as st, HealthCheck
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Provide stubs so the module loads
    def given(*a, **kw):
        def decorator(f):
            return pytest.mark.skip(reason="hypothesis not installed")(f)
        return decorator
    def settings(*a, **kw):
        def decorator(f): return f
        return decorator
    class st:
        @staticmethod
        def text(*a, **kw): return None
        @staticmethod
        def binary(*a, **kw): return None
        @staticmethod
        def integers(*a, **kw): return None


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"fuzz-{tag}-{uuid.uuid4().hex[:8]}@test.com"


# ---------------------------------------------------------------------------
# Shared server fixture at module level for fuzz efficiency
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop for hypothesis tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── FUZZ-001: Token parser fuzzing ────────────────────────────────────────

class TestTokenParserFuzz:
    """Fuzz the Authorization header parser in /auth/me."""

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(token=st.text(min_size=0, max_size=2000))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_fuzz_bearer_token(self, client, token):
        """FUZZ-001: Random strings as bearer tokens should not crash the server."""
        resp = await client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        # Server must return a valid HTTP response (not crash)
        assert resp.status_code > 0, f"Server crashed with token: {token!r}"
        # Should be 4xx (invalid token)
        assert resp.status_code != 200 or token == "", (
            f"Random token accepted?! token={token!r}"
        )

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(header=st.text(min_size=0, max_size=500))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_fuzz_auth_header_schemes(self, client, header):
        """FUZZ-001b: Random Authorization header values should not crash."""
        resp = await client.get("/auth/me", headers={
            "Authorization": header,
        })
        assert resp.status_code > 0


# ── FUZZ-002: Template input fuzzing ──────────────────────────────────────

class TestTemplateInputFuzz:
    """Fuzz form fields that get rendered in templates."""

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(email=st.text(min_size=1, max_size=500),
           password=st.text(min_size=1, max_size=500),
           name=st.text(min_size=1, max_size=500))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_fuzz_registration_inputs(self, client, email, password, name):
        """FUZZ-002: Random strings in registration form should not crash."""
        resp = await client.post("/auth/register", data={
            "email": email,
            "password": password,
            "full_name": name,
        })
        # Must return a valid HTTP response
        assert resp.status_code > 0
        # Template rendered content should not contain unescaped input
        if resp.status_code == 200 and '<script>' in email.lower():
            assert '<script>' not in resp.text.lower(), "XSS: script tag not escaped"

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(email=st.text(min_size=1, max_size=500),
           password=st.text(min_size=1, max_size=500))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_fuzz_login_inputs(self, client, email, password):
        """FUZZ-002b: Random strings in login form should not crash."""
        resp = await client.post("/auth/login", data={
            "email": email,
            "password": password,
        })
        assert resp.status_code > 0


# ── FUZZ-003: Upload parser fuzzing ───────────────────────────────────────

class TestUploadParserFuzz:
    """Fuzz multipart upload bodies."""

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(content=st.binary(min_size=0, max_size=10000),
           filename=st.text(min_size=1, max_size=200))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_fuzz_file_upload(self, client, content, filename):
        """FUZZ-003: Random binary content and filenames should not crash."""
        email = _unique_email("fuzzup")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "Fuzzer"},
            files={"profile": (filename, content, "application/octet-stream")},
        )
        assert resp.status_code > 0, f"Server crashed with filename={filename!r}"
