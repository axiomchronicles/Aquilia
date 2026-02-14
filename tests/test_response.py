"""
Test 3: Response (response.py)

Tests Response object: factory methods, headers, cookies, JSON, HTML, redirect,
streaming, SSE, file, background tasks, cookie signing, status helpers.
"""

import pytest
import json

from aquilia.response import (
    Response, ServerSentEvent, CookieSigner,
    CallableBackgroundTask,
)


# ============================================================================
# Response Construction
# ============================================================================

class TestResponseConstruction:

    def test_default(self):
        r = Response()
        assert r.status == 200

    def test_with_string_content(self):
        r = Response("Hello", status=200)
        assert r._content == "Hello"
        assert r.status == 200

    def test_with_bytes_content(self):
        r = Response(b"raw bytes", status=201)
        assert r._content == b"raw bytes"
        assert r.status == 201

    def test_with_custom_headers(self):
        r = Response(b"", headers={"x-custom": "val"})
        assert r.headers["x-custom"] == "val"

    def test_media_type_override(self):
        r = Response("text", media_type="text/xml")
        assert r.headers["content-type"] == "text/xml"

    def test_auto_detect_json_media(self):
        r = Response({"key": "value"})
        assert "application/json" in r.headers["content-type"]

    def test_auto_detect_text_media(self):
        r = Response("plain text")
        assert "text/plain" in r.headers["content-type"]


# ============================================================================
# Factory Methods
# ============================================================================

class TestResponseFactories:

    def test_json(self):
        r = Response.json({"a": 1, "b": [2, 3]})
        assert r.status == 200
        assert "application/json" in r.headers["content-type"]

    def test_json_custom_status(self):
        r = Response.json({"error": "not found"}, status=404)
        assert r.status == 404

    def test_json_serializes_sets(self):
        r = Response.json({"items": {1, 2, 3}})
        # Should not raise - sets serialized as lists

    def test_html(self):
        r = Response.html("<h1>Hello</h1>")
        assert r.status == 200
        assert "text/html" in r.headers["content-type"]

    def test_text(self):
        r = Response.text("plain text")
        assert "text/plain" in r.headers["content-type"]

    def test_redirect(self):
        r = Response.redirect("/login")
        assert r.status == 307
        assert r.headers["location"] == "/login"

    def test_redirect_301(self):
        r = Response.redirect("/new-url", status=301)
        assert r.status == 301
        assert r.headers["location"] == "/new-url"


# ============================================================================
# Server-Sent Events
# ============================================================================

class TestSSE:

    def test_sse_encode_basic(self):
        event = ServerSentEvent(data="hello")
        encoded = event.encode()
        assert b"data: hello" in encoded
        assert encoded.endswith(b"\n\n")

    def test_sse_encode_with_id(self):
        event = ServerSentEvent(data="msg", id="42")
        encoded = event.encode()
        assert b"id: 42" in encoded
        assert b"data: msg" in encoded

    def test_sse_encode_with_event_type(self):
        event = ServerSentEvent(data="payload", event="update")
        encoded = event.encode()
        assert b"event: update" in encoded

    def test_sse_encode_with_retry(self):
        event = ServerSentEvent(data="msg", retry=3000)
        encoded = event.encode()
        assert b"retry: 3000" in encoded

    def test_sse_multiline_data(self):
        event = ServerSentEvent(data="line1\nline2\nline3")
        encoded = event.encode()
        assert encoded.count(b"data:") == 3


# ============================================================================
# Cookie Signer
# ============================================================================

class TestCookieSigner:

    def test_sign_unsign_roundtrip(self):
        signer = CookieSigner("secret-key-123")
        signed = signer.sign("my-value")
        assert signer.unsign(signed) == "my-value"

    def test_unsign_tampered(self):
        signer = CookieSigner("secret")
        signed = signer.sign("original")
        # Tamper with the signed value
        tampered = signed[:-3] + "xxx"
        assert signer.unsign(tampered) is None

    def test_unsign_different_key(self):
        signer1 = CookieSigner("key1")
        signer2 = CookieSigner("key2")
        signed = signer1.sign("value")
        assert signer2.unsign(signed) is None

    def test_sign_unsign_special_chars(self):
        signer = CookieSigner("secret")
        signed = signer.sign("user@example.com|admin")
        assert signer.unsign(signed) == "user@example.com|admin"

    def test_unsign_invalid_format(self):
        signer = CookieSigner("secret")
        assert signer.unsign("no-dot-here") is None


# ============================================================================
# Background Tasks
# ============================================================================

class TestBackgroundTasks:

    def test_no_background_tasks(self):
        r = Response("ok")
        assert r._background_tasks == []

    @pytest.mark.asyncio
    async def test_callable_background_task(self):
        results = []

        async def task():
            results.append("executed")

        bg = CallableBackgroundTask(func=task)
        await bg.run()
        assert results == ["executed"]

    def test_single_background_task(self):
        async def noop():
            pass
        bg = CallableBackgroundTask(func=noop)
        r = Response("ok", background=bg)
        assert len(r._background_tasks) == 1

    def test_multiple_background_tasks(self):
        async def noop():
            pass
        tasks = [CallableBackgroundTask(func=noop) for _ in range(3)]
        r = Response("ok", background=tasks)
        assert len(r._background_tasks) == 3


# ============================================================================
# Headers Management
# ============================================================================

class TestResponseHeaders:

    def test_set_header(self):
        r = Response("ok")
        r.headers["x-custom"] = "value"
        assert r.headers["x-custom"] == "value"

    def test_multi_value_headers(self):
        r = Response("ok", headers={"set-cookie": ["a=1", "b=2"]})
        assert r.headers["set-cookie"] == ["a=1", "b=2"]
