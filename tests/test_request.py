"""
Test 2: Request (request.py)

Tests Request object: properties, query params, headers, cookies, URL building,
client IP, body reading, JSON parsing, form parsing, identity/session/DI integration.
"""

import pytest
import json

from aquilia.request import (
    Request, BadRequest, PayloadTooLarge, InvalidJSON, ClientDisconnect,
)
from aquilia._datastructures import MultiDict, Headers, URL
from tests.conftest import make_request, make_scope, make_receive


# ============================================================================
# Basic Properties
# ============================================================================

class TestRequestBasicProperties:

    def test_method(self):
        req = make_request(method="POST")
        assert req.method == "POST"

    def test_path(self):
        req = make_request(path="/users/42")
        assert req.path == "/users/42"

    def test_http_version(self):
        req = make_request()
        assert req.http_version == "1.1"

    def test_raw_path(self):
        req = make_request(path="/hello")
        assert req.raw_path == b"/hello"

    def test_client(self):
        req = make_request(client=("10.0.0.1", 9999))
        assert req.client == ("10.0.0.1", 9999)

    def test_scheme(self):
        req = make_request(scheme="https")
        assert req.scope["scheme"] == "https"


# ============================================================================
# Query Parameters
# ============================================================================

class TestRequestQueryParams:

    def test_query_params(self):
        req = make_request(query_string="a=1&b=2")
        params = req.query_params()
        assert params.get("a") == "1"
        assert params.get("b") == "2"

    def test_query_param(self):
        req = make_request(query_string="page=5")
        assert req.query_param("page") == "5"
        assert req.query_param("missing") is None
        assert req.query_param("missing", "default") == "default"

    def test_repeated_params(self):
        req = make_request(query_string="tag=a&tag=b&tag=c")
        params = req.query_params()
        assert params.get_all("tag") == ["a", "b", "c"]

    def test_empty_query(self):
        req = make_request(query_string="")
        params = req.query_params()
        assert len(params) == 0


# ============================================================================
# Headers
# ============================================================================

class TestRequestHeaders:

    def test_headers(self):
        req = make_request(headers=[("Content-Type", "application/json"), ("X-Custom", "val")])
        assert req.header("content-type") == "application/json"
        assert req.header("x-custom") == "val"

    def test_has_header(self):
        req = make_request(headers=[("Authorization", "Bearer tok")])
        assert req.has_header("authorization") is True
        assert req.has_header("missing") is False

    def test_header_default(self):
        req = make_request()
        assert req.header("missing") is None
        assert req.header("missing", "fallback") == "fallback"


# ============================================================================
# Cookies
# ============================================================================

class TestRequestCookies:

    def test_cookies(self):
        req = make_request(headers=[("Cookie", "sid=abc123; theme=dark")])
        cookies = req.cookies()
        assert cookies["sid"] == "abc123"
        assert cookies["theme"] == "dark"

    def test_cookie(self):
        req = make_request(headers=[("Cookie", "token=xyz")])
        assert req.cookie("token") == "xyz"
        assert req.cookie("missing") is None
        assert req.cookie("missing", "fallback") == "fallback"

    def test_no_cookies(self):
        req = make_request()
        cookies = req.cookies()
        assert len(cookies) == 0


# ============================================================================
# URL Building
# ============================================================================

class TestRequestURL:

    def test_url(self):
        req = make_request(
            path="/api/users",
            query_string="page=1",
            headers=[("Host", "example.com:8080")],
        )
        url = req.url()
        assert url.host == "example.com"
        assert url.port == 8080
        assert url.path == "/api/users"
        assert url.query == "page=1"

    def test_url_caching(self):
        req = make_request(headers=[("Host", "a.com")])
        u1 = req.url()
        u2 = req.url()
        assert u1 is u2  # Same object returned


# ============================================================================
# Client IP
# ============================================================================

class TestRequestClientIP:

    def test_direct_client_ip(self):
        req = make_request(client=("192.168.1.1", 1234))
        assert req.client_ip() == "192.168.1.1"

    def test_proxied_ip(self):
        req = make_request(
            headers=[("X-Forwarded-For", "1.2.3.4, 10.0.0.1")],
            trust_proxy=True,
        )
        assert req.client_ip() == "1.2.3.4"

    def test_no_trust_proxy(self):
        req = make_request(
            headers=[("X-Forwarded-For", "1.2.3.4")],
            client=("10.0.0.1", 80),
            trust_proxy=False,
        )
        assert req.client_ip() == "10.0.0.1"


# ============================================================================
# Content Helpers
# ============================================================================

class TestRequestContentHelpers:

    def test_content_type(self):
        req = make_request(headers=[("Content-Type", "application/json")])
        assert req.content_type() == "application/json"

    def test_content_length(self):
        req = make_request(headers=[("Content-Length", "42")])
        assert req.content_length() == 42

    def test_is_json(self):
        req = make_request(headers=[("Content-Type", "application/json")])
        assert req.is_json() is True

    def test_is_not_json(self):
        req = make_request(headers=[("Content-Type", "text/html")])
        assert req.is_json() is False

    def test_accepts(self):
        req = make_request(headers=[("Accept", "application/json, text/html")])
        assert req.accepts("application/json") is True
        assert req.accepts("text/html") is True

    def test_accepts_wildcard(self):
        req = make_request(headers=[("Accept", "*/*")])
        assert req.accepts("anything/here") is True


# ============================================================================
# Authorization Helpers
# ============================================================================

class TestRequestAuthHelpers:

    def test_auth_scheme(self):
        req = make_request(headers=[("Authorization", "Bearer tokenxyz")])
        assert req.auth_scheme() == "Bearer"

    def test_auth_credentials(self):
        req = make_request(headers=[("Authorization", "Bearer tokenxyz")])
        assert req.auth_credentials() == "tokenxyz"

    def test_no_auth(self):
        req = make_request()
        assert req.auth_scheme() is None
        assert req.auth_credentials() is None


# ============================================================================
# Body Reading
# ============================================================================

class TestRequestBody:

    @pytest.mark.asyncio
    async def test_body(self):
        req = make_request(body=b"hello world")
        body = await req.body()
        assert body == b"hello world"

    @pytest.mark.asyncio
    async def test_body_idempotent(self):
        req = make_request(body=b"test")
        b1 = await req.body()
        b2 = await req.body()
        assert b1 == b2 == b"test"

    @pytest.mark.asyncio
    async def test_text(self):
        req = make_request(body=b"hello")
        text = await req.text()
        assert text == "hello"

    @pytest.mark.asyncio
    async def test_iter_bytes(self):
        req = make_request(body=b"abcdefghij")
        chunks = []
        async for chunk in req.iter_bytes():
            chunks.append(chunk)
        assert b"".join(chunks) == b"abcdefghij"

    @pytest.mark.asyncio
    async def test_body_size_limit(self):
        req = make_request(body=b"x" * 100, max_body_size=50)
        with pytest.raises(PayloadTooLarge):
            await req.body()


# ============================================================================
# JSON Parsing
# ============================================================================

class TestRequestJSON:

    @pytest.mark.asyncio
    async def test_json(self):
        data = {"key": "value", "num": 42}
        req = make_request(
            body=json.dumps(data).encode(),
            headers=[("Content-Type", "application/json")],
        )
        result = await req.json()
        assert result == data

    @pytest.mark.asyncio
    async def test_json_idempotent(self):
        req = make_request(body=b'{"a": 1}')
        r1 = await req.json()
        r2 = await req.json()
        assert r1 == r2

    @pytest.mark.asyncio
    async def test_json_invalid(self):
        req = make_request(body=b"not json{{{")
        with pytest.raises(InvalidJSON):
            await req.json()


# ============================================================================
# Identity / Session / State Integration
# ============================================================================

class TestRequestStateIntegration:

    def test_identity_from_state(self):
        from tests.conftest import make_identity
        identity = make_identity()
        req = make_request()
        req.state["identity"] = identity
        assert req.identity is identity

    def test_authenticated(self):
        from tests.conftest import make_identity
        req = make_request()
        assert req.authenticated is False
        req.state["identity"] = make_identity()
        req.state["authenticated"] = True
        assert req.authenticated is True

    def test_session_from_state(self):
        from tests.conftest import make_session
        sess = make_session()
        req = make_request()
        req.state["session"] = sess
        assert req.session is sess

    def test_state_dict(self):
        req = make_request()
        req.state["custom"] = "value"
        assert req.state["custom"] == "value"

    def test_trace_id_from_header(self):
        req = make_request(headers=[("X-Trace-Id", "trace-abc")])
        assert req.trace_id == "trace-abc"

    def test_request_id_from_state(self):
        req = make_request()
        req.state["request_id"] = "req-123"
        assert req.request_id == "req-123"


# ============================================================================
# Template Context Integration
# ============================================================================

class TestRequestTemplateContext:

    def test_template_context_auto_injected(self):
        req = make_request(path="/test")
        ctx = req.template_context
        assert ctx["request"] is req
        assert ctx["path"] == "/test"
        assert ctx["method"] == "GET"

    def test_add_template_context(self):
        req = make_request()
        req.add_template_context(title="Home", user="bob")
        ctx = req.template_context
        assert ctx["title"] == "Home"
        assert ctx["user"] == "bob"


# ============================================================================
# Fault Context
# ============================================================================

class TestRequestFaultContext:

    def test_fault_context(self):
        req = make_request(
            method="POST",
            path="/api/users",
            headers=[("User-Agent", "TestAgent/1.0")],
            client=("10.0.0.1", 9999),
        )
        req.state["request_id"] = "req-456"
        fc = req.fault_context()
        assert fc["method"] == "POST"
        assert fc["path"] == "/api/users"
        assert fc["client_ip"] == "10.0.0.1"
        assert fc["request_id"] == "req-456"


# ============================================================================
# Cleanup
# ============================================================================

class TestRequestCleanup:

    @pytest.mark.asyncio
    async def test_cleanup_no_error(self):
        req = make_request()
        await req.cleanup()  # Should not raise
