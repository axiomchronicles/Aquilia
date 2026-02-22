"""
TPL-001 to TPL-003: Template rendering controller tests.

Exercises: AuthController views (register, login), Jinja2 template rendering,
XSS prevention, template injection.
"""

import pytest


pytestmark = pytest.mark.asyncio


# ── TPL-003: View pages render correctly ──────────────────────────────────

class TestTemplateRendering:
    """Basic template rendering tests for auth views."""

    async def test_register_page_renders(self, client):
        """TPL-003: GET /auth/register returns HTML."""
        resp = await client.get("/auth/register")
        assert resp.status_code == 200
        assert "text/html" in resp.content_type

    async def test_login_page_renders(self, client):
        """TPL-003b: GET /auth/login returns HTML."""
        resp = await client.get("/auth/login")
        assert resp.status_code == 200
        assert "text/html" in resp.content_type


# ── TPL-001: Template injection ───────────────────────────────────────────

class TestTemplateInjection:
    """Ensure Jinja2 template injection is not possible through user input."""

    INJECTION_PAYLOADS = [
        "{{ 7*7 }}",
        "{% import os %}{{ os.popen('id').read() }}",
        "${7*7}",
        "#{7*7}",
        "{{config}}",
        "{{self.__class__.__mro__[2].__subclasses__()}}",
    ]

    async def test_template_injection_in_register(self, client):
        """TPL-001: Template injection payloads in registration should be
        escaped or rejected, never executed."""
        for payload in self.INJECTION_PAYLOADS:
            resp = await client.post("/auth/register", data={
                "email": payload,
                "password": "test1234",
                "full_name": payload,
            })
            # Should either reject (4xx) or render with escaped output
            if resp.status_code == 200 or resp.status_code == 302:
                # If rendered, check that the payload is NOT evaluated
                body_text = resp.text
                assert "49" not in body_text, (
                    f"Template injection executed! Payload: {payload}"
                )
                assert "config" not in body_text.lower() or "{{config}}" in body_text, (
                    f"Config leaked via template injection! Payload: {payload}"
                )


# ── TPL-002: XSS payloads ────────────────────────────────────────────────

class TestXSSPrevention:
    """Ensure XSS payloads are escaped when rendered in templates."""

    XSS_PAYLOADS = [
        '<script>alert("xss")</script>',
        '<img src=x onerror=alert(1)>',
        '"><script>alert(document.cookie)</script>',
        "';alert(String.fromCharCode(88,83,83))//",
        '<svg/onload=alert(1)>',
        'javascript:alert(1)',
    ]

    async def test_xss_in_registration_error(self, client):
        """TPL-002: XSS payloads in form fields should be HTML-escaped."""
        for payload in self.XSS_PAYLOADS:
            resp = await client.post("/auth/register", data={
                "email": payload,
                "password": "test1234",
                "full_name": payload,
            })
            if resp.status_code == 200:
                body = resp.text
                # Unescaped script tag should NOT appear
                assert '<script>' not in body.lower(), (
                    f"XSS vulnerability: unescaped script tag! Payload: {payload}"
                )
                assert 'onerror=' not in body.lower(), (
                    f"XSS vulnerability: unescaped event handler! Payload: {payload}"
                )
                assert '<svg/onload' not in body.lower(), (
                    f"XSS vulnerability: unescaped SVG handler! Payload: {payload}"
                )

    async def test_xss_in_login_error(self, client):
        """TPL-002b: XSS payloads in login form should be escaped."""
        for payload in self.XSS_PAYLOADS:
            resp = await client.post("/auth/login", data={
                "email": payload,
                "password": payload,
            })
            if resp.status_code == 200:
                body = resp.text
                assert '<script>' not in body.lower(), (
                    f"XSS in login: unescaped script! Payload: {payload}"
                )
