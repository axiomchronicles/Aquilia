"""
Tests for the aquilia.testing module.

Validates every component of the Django-style testing framework:
- TestClient & TestResponse
- WebSocketTestClient
- TestServer lifecycle
- override_settings context manager / decorator
- TestConfig
- MockFaultEngine & CapturedFault
- MockEffectRegistry & MockEffectProvider
- MockCacheBackend & CacheTestMixin
- TestIdentityFactory & AuthTestMixin
- MailTestMixin & CapturedMail outbox
- TestContainer, mock_provider, override_provider
- AquiliaAssertions mixin
- Pytest fixtures
- SimpleTestCase, AquiliaTestCase (base behaviour only)
- CLI test command helpers
"""

from __future__ import annotations

import asyncio
import json
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ============================================================================
# Imports under test
# ============================================================================

from aquilia.testing.utils import (
    make_test_scope,
    make_test_receive,
    make_test_request,
    make_test_response,
)
from aquilia.testing.config import (
    override_settings,
    TestConfig,
    set_active_config,
    get_active_config,
)
from aquilia.testing.client import TestClient, TestResponse, WebSocketTestClient
from aquilia.testing.faults import MockFaultEngine, CapturedFault
from aquilia.testing.effects import MockEffectRegistry, MockEffectProvider, EffectCall
from aquilia.testing.cache import MockCacheBackend, CacheTestMixin
from aquilia.testing.auth import TestIdentityFactory, AuthTestMixin, IdentityBuilder
from aquilia.testing.mail import (
    MailTestMixin,
    CapturedMail,
    capture_mail,
    get_outbox,
    clear_outbox,
)
from aquilia.testing.di import (
    TestContainer, mock_provider, override_provider,
    factory_provider, spy_provider,
)
from aquilia.testing.assertions import AquiliaAssertions
from aquilia.testing.cases import SimpleTestCase
from aquilia.testing.utils import make_test_ws_scope, make_upload_file

from aquilia.config import ConfigLoader
from aquilia.faults.core import Fault, FaultDomain, Severity
from aquilia.auth.core import Identity, IdentityType, IdentityStatus


# ============================================================================
# 1. Utils – make_test_scope
# ============================================================================


class TestMakeTestScope:
    """Tests for make_test_scope factory."""

    def test_defaults(self):
        scope = make_test_scope()
        assert scope["type"] == "http"
        assert scope["method"] == "GET"
        assert scope["path"] == "/"
        assert scope["scheme"] == "http"
        assert scope["http_version"] == "1.1"
        assert scope["query_string"] == b""
        assert scope["headers"] == []
        assert scope["server"] == ("127.0.0.1", 8000)
        assert scope["client"] == ("127.0.0.1", 12345)

    def test_custom_method_and_path(self):
        scope = make_test_scope(method="POST", path="/api/users")
        assert scope["method"] == "POST"
        assert scope["path"] == "/api/users"
        assert scope["raw_path"] == b"/api/users"

    def test_query_string(self):
        scope = make_test_scope(query_string="page=1&limit=10")
        assert scope["query_string"] == b"page=1&limit=10"

    def test_headers_as_strings(self):
        scope = make_test_scope(headers=[
            ("content-type", "application/json"),
            ("authorization", "Bearer tok"),
        ])
        assert len(scope["headers"]) == 2
        assert scope["headers"][0] == (b"content-type", b"application/json")
        assert scope["headers"][1] == (b"authorization", b"Bearer tok")

    def test_headers_as_bytes(self):
        scope = make_test_scope(headers=[
            (b"x-custom", b"value"),
        ])
        assert scope["headers"][0] == (b"x-custom", b"value")

    def test_custom_client_server(self):
        scope = make_test_scope(
            client=("192.168.1.1", 9999),
            server=("0.0.0.0", 443),
        )
        assert scope["client"] == ("192.168.1.1", 9999)
        assert scope["server"] == ("0.0.0.0", 443)

    def test_https_scheme(self):
        scope = make_test_scope(scheme="https")
        assert scope["scheme"] == "https"

    def test_websocket_scope_type(self):
        scope = make_test_scope(scope_type="websocket")
        assert scope["type"] == "websocket"


# ============================================================================
# 2. Utils – make_test_receive
# ============================================================================


class TestMakeTestReceive:
    """Tests for make_test_receive callable builder."""

    async def test_empty_body(self):
        receive = make_test_receive()
        msg = await receive()
        assert msg["type"] == "http.request"
        assert msg["body"] == b""
        assert msg["more_body"] is False

    async def test_body_bytes(self):
        receive = make_test_receive(b"hello world")
        msg = await receive()
        assert msg["body"] == b"hello world"
        assert msg["more_body"] is False

    async def test_disconnect_after_body(self):
        receive = make_test_receive(b"x")
        await receive()  # body
        disconnect = await receive()
        assert disconnect["type"] == "http.disconnect"

    async def test_chunked_body(self):
        receive = make_test_receive(chunks=[b"chunk1", b"chunk2", b"chunk3"])
        msg1 = await receive()
        assert msg1["body"] == b"chunk1"
        assert msg1["more_body"] is True

        msg2 = await receive()
        assert msg2["body"] == b"chunk2"
        assert msg2["more_body"] is True

        msg3 = await receive()
        assert msg3["body"] == b"chunk3"
        assert msg3["more_body"] is False

        disconnect = await receive()
        assert disconnect["type"] == "http.disconnect"


# ============================================================================
# 3. Utils – make_test_request
# ============================================================================


class TestMakeTestRequest:
    """Tests for make_test_request factory."""

    def test_default_request(self):
        req = make_test_request()
        assert req.method == "GET"
        assert req.path == "/"

    def test_post_with_json(self):
        req = make_test_request(
            method="POST",
            path="/api/data",
            json={"key": "value"},
        )
        assert req.method == "POST"
        assert req.path == "/api/data"

    def test_with_headers(self):
        req = make_test_request(
            headers=[("x-custom", "val")],
        )
        # Headers should be set on the scope
        assert req.scope["headers"]

    def test_form_data(self):
        req = make_test_request(
            method="POST",
            form_data={"username": "alice", "password": "secret"},
        )
        assert req.method == "POST"

    def test_query_string(self):
        req = make_test_request(query_string="foo=bar")
        assert req.query_string == "foo=bar"


# ============================================================================
# 4. Utils – make_test_response
# ============================================================================


class TestMakeTestResponse:
    """Tests for make_test_response factory."""

    def test_default_response(self):
        resp = make_test_response()
        assert resp is not None

    def test_custom_status_and_body(self):
        resp = make_test_response(status=201, content=b"created")
        assert resp.status == 201


# ============================================================================
# 5. TestResponse
# ============================================================================


class TestTestResponse:
    """Tests for the TestResponse wrapper."""

    def _make(self, status=200, headers=None, body=b""):
        return TestResponse(
            status_code=status,
            headers=headers or {},
            body=body,
        )

    def test_status_code(self):
        r = self._make(200)
        assert r.status_code == 200

    def test_is_success(self):
        assert self._make(200).is_success
        assert self._make(201).is_success
        assert self._make(299).is_success
        assert not self._make(300).is_success
        assert not self._make(404).is_success

    def test_is_redirect(self):
        assert self._make(301).is_redirect
        assert self._make(302).is_redirect
        assert not self._make(200).is_redirect

    def test_is_client_error(self):
        assert self._make(400).is_client_error
        assert self._make(404).is_client_error
        assert self._make(499).is_client_error
        assert not self._make(500).is_client_error

    def test_is_server_error(self):
        assert self._make(500).is_server_error
        assert self._make(503).is_server_error
        assert not self._make(200).is_server_error

    def test_text(self):
        r = self._make(body=b"hello world")
        assert r.text == "hello world"

    def test_json(self):
        data = {"status": "ok", "count": 42}
        r = self._make(
            headers={"content-type": "application/json"},
            body=json.dumps(data).encode(),
        )
        assert r.json() == data

    def test_json_cached(self):
        r = self._make(body=b'{"a": 1}')
        first = r.json()
        second = r.json()
        assert first is second  # cached

    def test_content_type(self):
        r = self._make(headers={"content-type": "text/html; charset=utf-8"})
        assert r.content_type == "text/html"
        assert r.charset == "utf-8"

    def test_header_accessor(self):
        r = self._make(headers={"x-request-id": "abc123"})
        assert r.header("X-Request-Id") == "abc123"
        assert r.header("missing") is None
        assert r.header("missing", "default") == "default"

    def test_repr(self):
        r = self._make(200, {"content-type": "application/json"}, b'{"ok":true}')
        assert "200" in repr(r)


# ============================================================================
# 6. TestClient
# ============================================================================


class TestTestClient:
    """Tests for the in-process TestClient."""

    @staticmethod
    async def _echo_app(scope, receive, send):
        """Simple ASGI echo app for testing."""
        body_msg = await receive()
        body = body_msg.get("body", b"")

        response_body = json.dumps({
            "method": scope["method"],
            "path": scope["path"],
            "query": scope["query_string"].decode(),
            "body": body.decode() if body else "",
            "headers": {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in scope["headers"]
            },
        }).encode()

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(response_body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": response_body,
        })

    async def test_get(self):
        client = TestClient(self._echo_app)
        resp = await client.get("/hello")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "GET"
        assert data["path"] == "/hello"

    async def test_post_json(self):
        client = TestClient(self._echo_app)
        resp = await client.post("/api", json={"key": "val"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "POST"
        assert '"key"' in data["body"]
        assert data["headers"]["content-type"] == "application/json"

    async def test_post_form_data(self):
        client = TestClient(self._echo_app)
        resp = await client.post("/form", data={"name": "alice"})
        data = resp.json()
        assert "name=alice" in data["body"]
        assert "urlencoded" in data["headers"]["content-type"]

    async def test_put(self):
        client = TestClient(self._echo_app)
        resp = await client.put("/item/1", json={"name": "updated"})
        data = resp.json()
        assert data["method"] == "PUT"

    async def test_patch(self):
        client = TestClient(self._echo_app)
        resp = await client.patch("/item/1", json={"name": "patched"})
        data = resp.json()
        assert data["method"] == "PATCH"

    async def test_delete(self):
        client = TestClient(self._echo_app)
        resp = await client.delete("/item/1")
        data = resp.json()
        assert data["method"] == "DELETE"

    async def test_head(self):
        client = TestClient(self._echo_app)
        resp = await client.head("/")
        data = resp.json()
        assert data["method"] == "HEAD"

    async def test_options(self):
        client = TestClient(self._echo_app)
        resp = await client.options("/")
        data = resp.json()
        assert data["method"] == "OPTIONS"

    async def test_default_headers(self):
        client = TestClient(
            self._echo_app,
            default_headers={"x-api-key": "secret"},
        )
        resp = await client.get("/")
        data = resp.json()
        assert data["headers"]["x-api-key"] == "secret"

    async def test_custom_headers_per_request(self):
        client = TestClient(self._echo_app)
        resp = await client.get("/", headers={"x-trace": "abc"})
        data = resp.json()
        assert data["headers"]["x-trace"] == "abc"

    async def test_query_string(self):
        client = TestClient(self._echo_app)
        resp = await client.get("/search", query_string="q=test&page=1")
        data = resp.json()
        assert data["query"] == "q=test&page=1"

    async def test_cookie_management(self):
        client = TestClient(self._echo_app)
        client.set_cookie("session", "abc123")
        resp = await client.get("/")
        data = resp.json()
        assert "session=abc123" in data["headers"].get("cookie", "")

    async def test_clear_cookies(self):
        client = TestClient(self._echo_app)
        client.set_cookie("a", "1")
        client.clear_cookies()
        resp = await client.get("/")
        data = resp.json()
        assert "cookie" not in data["headers"]

    async def test_cookie_jar_from_set_cookie(self):
        async def cookie_app(scope, receive, send):
            await receive()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"set-cookie", b"token=xyz; Path=/"),
                ],
            })
            await send({"type": "http.response.body", "body": b""})

        client = TestClient(cookie_app)
        await client.get("/login")
        assert client._cookies.get("token") == "xyz"

    async def test_raise_server_exceptions(self):
        async def failing_app(scope, receive, send):
            raise ValueError("boom")

        client = TestClient(failing_app, raise_server_exceptions=True)
        with pytest.raises(ValueError, match="boom"):
            await client.get("/")

    async def test_suppress_server_exceptions(self):
        async def failing_app(scope, receive, send):
            raise ValueError("boom")

        client = TestClient(failing_app, raise_server_exceptions=False)
        resp = await client.get("/")
        # Response should be default (200) since no response was sent
        assert resp.status_code == 200


# ============================================================================
# 7. TestConfig
# ============================================================================


class TestTestConfig:
    """Tests for TestConfig wrapper."""

    def test_get_with_overrides(self):
        loader = ConfigLoader()
        loader.config_data = {"debug": False, "database": {"url": "sqlite:///test.db"}}
        cfg = TestConfig(loader, debug=True)
        assert cfg.get("debug") is True  # overridden
        assert cfg.get("database.url") == "sqlite:///test.db"  # from base

    def test_get_fallback_to_base(self):
        loader = ConfigLoader()
        loader.config_data = {"name": "myapp"}
        cfg = TestConfig(loader)
        assert cfg.get("name") == "myapp"

    def test_get_default(self):
        cfg = TestConfig()
        assert cfg.get("missing", "fallback") == "fallback"

    def test_to_dict_merges(self):
        loader = ConfigLoader()
        loader.config_data = {"a": 1, "b": {"c": 2}}
        cfg = TestConfig(loader, b={"c": 99, "d": 3})
        d = cfg.to_dict()
        assert d["a"] == 1
        assert d["b"]["c"] == 99
        assert d["b"]["d"] == 3

    def test_to_dict_cached(self):
        cfg = TestConfig(debug=True)
        d1 = cfg.to_dict()
        d2 = cfg.to_dict()
        assert d1 is d2

    def test_proxy_accessors(self):
        loader = ConfigLoader()
        loader.config_data = {
            "integrations": {
                "cache": {"backend": "memory"},
                "sessions": {"ttl": 3600},
                "auth": {"secret": "s"},
                "mail": {"provider": "smtp"},
                "templates": {"dir": "templates/"},
            },
        }
        cfg = TestConfig(loader)
        assert cfg.get_cache_config()["backend"] == "memory"
        assert cfg.get_session_config()["ttl"] == 3600
        assert cfg.get_auth_config()["secret"] == "s"
        assert cfg.get_mail_config()["provider"] == "smtp"
        assert cfg.get_template_config()["dir"] == "templates/"


# ============================================================================
# 8. override_settings
# ============================================================================


class TestOverrideSettings:
    """Tests for the override_settings context manager / decorator."""

    def _setup_active_config(self) -> ConfigLoader:
        loader = ConfigLoader()
        loader.config_data = {"debug": False, "cache": {"backend": "redis"}}
        set_active_config(loader)
        return loader

    def test_context_manager_sync(self):
        loader = self._setup_active_config()
        assert loader.get("debug") is False

        with override_settings(DEBUG=True):
            assert loader.get("debug") is True

        assert loader.get("debug") is False

    def test_context_manager_nested_key(self):
        loader = self._setup_active_config()
        assert loader.get("cache.backend") == "redis"

        with override_settings(CACHE__BACKEND="memory"):
            assert loader.get("cache.backend") == "memory"

        assert loader.get("cache.backend") == "redis"

    async def test_async_context_manager(self):
        loader = self._setup_active_config()
        async with override_settings(DEBUG=True):
            assert loader.get("debug") is True
        assert loader.get("debug") is False

    def test_decorator_sync(self):
        loader = self._setup_active_config()

        @override_settings(DEBUG=True)
        def check():
            return loader.get("debug")

        assert check() is True
        assert loader.get("debug") is False

    async def test_decorator_async(self):
        loader = self._setup_active_config()

        @override_settings(DEBUG=True)
        async def check():
            return loader.get("debug")

        result = await check()
        assert result is True
        assert loader.get("debug") is False


# ============================================================================
# 9. MockFaultEngine
# ============================================================================


class TestMockFaultEngine:
    """Tests for MockFaultEngine."""

    def _make_fault(self, code="TEST_ERR"):
        return Fault(
            code=code,
            message="test fault",
            domain=FaultDomain.SYSTEM,
            severity=Severity.ERROR,
        )

    def test_emit_captures(self):
        engine = MockFaultEngine()
        f = self._make_fault()
        engine.emit(f, app_name="myapp")
        assert len(engine.captured) == 1
        assert engine.captured[0].fault is f
        assert engine.captured[0].app_name == "myapp"
        assert engine.captured[0].timestamp > 0

    def test_has_fault(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("ERR_A"))
        engine.emit(self._make_fault("ERR_B"))
        assert engine.has_fault("ERR_A")
        assert engine.has_fault("ERR_B")
        assert not engine.has_fault("ERR_C")

    def test_get_faults_by_code(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("ERR_A"))
        engine.emit(self._make_fault("ERR_B"))
        engine.emit(self._make_fault("ERR_A"))
        results = engine.get_faults(code="ERR_A")
        assert len(results) == 2

    def test_get_faults_by_domain(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault())
        results = engine.get_faults(domain=str(FaultDomain.SYSTEM))
        assert len(results) == 1

    def test_fault_codes(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("A"))
        engine.emit(self._make_fault("B"))
        assert engine.fault_codes == ["A", "B"]

    def test_fault_count(self):
        engine = MockFaultEngine()
        assert engine.fault_count == 0
        engine.emit(self._make_fault())
        assert engine.fault_count == 1

    def test_reset(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault())
        engine.reset()
        assert engine.fault_count == 0
        assert engine.captured == []

    def test_raise_fault(self):
        engine = MockFaultEngine()
        f = self._make_fault("RAISED")
        with pytest.raises(Fault):
            engine.raise_fault(f)
        assert engine.has_fault("RAISED")

    def test_context_manager_resets(self):
        engine = MockFaultEngine()
        with engine:
            engine.emit(self._make_fault())
            assert engine.fault_count == 1
        assert engine.fault_count == 0  # reset on exit

    def test_register_app(self):
        engine = MockFaultEngine()
        handler = MagicMock()
        engine.register_app("myapp", handler)
        assert "myapp" in engine._handlers

    def test_register_handler(self):
        engine = MockFaultEngine()
        handler = MagicMock()
        engine.register_handler("SYSTEM", handler)
        assert "SYSTEM" in engine._handlers


# ============================================================================
# 10. CapturedFault
# ============================================================================


class TestCapturedFault:
    """Tests for CapturedFault dataclass."""

    def test_properties(self):
        f = Fault(
            code="MY_ERR",
            message="broken",
            domain=FaultDomain.CONFIG,
            severity=Severity.WARN,
        )
        captured = CapturedFault(
            fault=f,
            domain="CONFIG",
            app_name="testapp",
            timestamp=100.0,
        )
        assert captured.code == "MY_ERR"
        assert captured.message  # non-empty
        assert captured.severity == Severity.WARN
        assert "MY_ERR" in repr(captured)
        assert "CONFIG" in repr(captured)


# ============================================================================
# 11. MockEffectProvider
# ============================================================================


class TestMockEffectProvider:
    """Tests for MockEffectProvider."""

    async def test_acquire_returns_value(self):
        p = MockEffectProvider(return_value={"db": "conn"})
        result = await p.acquire(mode="read")
        assert result == {"db": "conn"}
        assert p.acquire_count == 1
        assert p.acquired_modes == ["read"]

    async def test_release_tracks(self):
        p = MockEffectProvider(return_value="resource")
        r = await p.acquire()
        await p.release(r, success=True)
        assert p.release_count == 1
        assert p.released_resources == [("resource", True)]

    async def test_acquire_side_effect(self):
        p = MockEffectProvider(acquire_side_effect=ConnectionError("fail"))
        with pytest.raises(ConnectionError, match="fail"):
            await p.acquire()
        assert p.acquire_count == 1

    async def test_initialize_and_finalize(self):
        p = MockEffectProvider()
        await p.initialize()
        assert p._initialized
        await p.finalize()
        assert p._finalized

    def test_reset(self):
        p = MockEffectProvider()
        p.acquire_count = 5
        p.release_count = 3
        p.acquired_modes.extend(["a", "b"])
        p.released_resources.append(("x", True))
        p.reset()
        assert p.acquire_count == 0
        assert p.release_count == 0
        assert p.acquired_modes == []
        assert p.released_resources == []


# ============================================================================
# 12. MockEffectRegistry
# ============================================================================


class TestMockEffectRegistry:
    """Tests for MockEffectRegistry."""

    def test_register_mock(self):
        reg = MockEffectRegistry()
        mock = reg.register_mock("DBTx", return_value="fake_conn")
        assert isinstance(mock, MockEffectProvider)
        assert reg.has_effect("DBTx")

    async def test_get_provider_auto_stubs(self):
        reg = MockEffectRegistry()
        provider = reg.get_provider("UnknownEffect")
        assert isinstance(provider, MockEffectProvider)
        resource = await provider.acquire()
        assert resource is None  # default return_value

    def test_get_mock(self):
        reg = MockEffectRegistry()
        reg.register_mock("Cache", return_value="cache_conn")
        mock = reg.get_mock("Cache")
        assert mock is not None
        assert mock.return_value == "cache_conn"

    def test_get_mock_none(self):
        reg = MockEffectRegistry()
        assert reg.get_mock("Nonexistent") is None

    def test_reset_all(self):
        reg = MockEffectRegistry()
        m1 = reg.register_mock("A")
        m2 = reg.register_mock("B")
        m1.acquire_count = 5
        m2.release_count = 3
        reg.reset_all()
        assert m1.acquire_count == 0
        assert m2.release_count == 0


# ============================================================================
# 13. MockCacheBackend
# ============================================================================


class TestMockCacheBackend:
    """Tests for MockCacheBackend."""

    async def test_set_and_get(self):
        cache = MockCacheBackend()
        await cache.set("key1", "value1", ttl=60)
        result = await cache.get("key1")
        assert result == "value1"
        assert cache.set_count == 1
        assert cache.get_count == 1

    async def test_get_missing(self):
        cache = MockCacheBackend()
        result = await cache.get("missing")
        assert result is None

    async def test_delete(self):
        cache = MockCacheBackend()
        await cache.set("key", "val")
        deleted = await cache.delete("key")
        assert deleted is True
        assert await cache.get("key") is None
        assert cache.delete_count == 1

    async def test_delete_missing(self):
        cache = MockCacheBackend()
        deleted = await cache.delete("nope")
        assert deleted is False

    async def test_exists(self):
        cache = MockCacheBackend()
        await cache.set("present", "yes")
        assert await cache.exists("present") is True
        assert await cache.exists("absent") is False

    async def test_clear(self):
        cache = MockCacheBackend()
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.clear()
        assert await cache.get("a") is None
        assert cache.clear_count == 1

    async def test_keys_all(self):
        cache = MockCacheBackend()
        await cache.set("user:1", "alice")
        await cache.set("user:2", "bob")
        await cache.set("session:1", "data")
        keys = await cache.keys()
        assert sorted(keys) == ["session:1", "user:1", "user:2"]

    async def test_keys_pattern(self):
        cache = MockCacheBackend()
        await cache.set("user:1", "alice")
        await cache.set("user:2", "bob")
        await cache.set("session:1", "data")
        keys = await cache.keys("user:*")
        assert sorted(keys) == ["user:1", "user:2"]

    async def test_connect_disconnect(self):
        cache = MockCacheBackend()
        await cache.connect()
        assert cache._connected is True
        await cache.disconnect()
        assert cache._connected is False

    async def test_health_check(self):
        cache = MockCacheBackend()
        assert await cache.health_check() is True

    def test_store_direct_access(self):
        cache = MockCacheBackend()
        cache._store["direct"] = "access"
        assert cache.store["direct"] == "access"

    def test_reset(self):
        cache = MockCacheBackend()
        cache._store["k"] = "v"
        cache.get_count = 10
        cache.set_count = 5
        cache.reset()
        assert cache._store == {}
        assert cache.get_count == 0
        assert cache.set_count == 0


# ============================================================================
# 14. CacheTestMixin
# ============================================================================


class TestCacheTestMixin:
    """Tests for CacheTestMixin helper methods."""

    async def test_assert_cached(self):
        cache = MockCacheBackend()
        await cache.set("present", "yes")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.assert_cached("present")

        with pytest.raises(AssertionError):
            await case.assert_cached("missing")

    async def test_assert_not_cached(self):
        cache = MockCacheBackend()
        await cache.set("present", "yes")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.assert_not_cached("absent")

        with pytest.raises(AssertionError):
            await case.assert_not_cached("present")

    async def test_populate_cache(self):
        cache = MockCacheBackend()

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.populate_cache({"a": 1, "b": 2})
        assert await cache.get("a") == 1
        assert await cache.get("b") == 2

    async def test_flush_cache(self):
        cache = MockCacheBackend()
        await cache.set("x", "y")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.flush_cache()
        assert await cache.get("x") is None


# ============================================================================
# 15. TestIdentityFactory
# ============================================================================


class TestTestIdentityFactory:
    """Tests for TestIdentityFactory."""

    def test_user(self):
        identity = TestIdentityFactory.user(id="u1", email="u1@test.com")
        assert identity.id == "u1"
        assert identity.type == IdentityType.USER
        assert identity.status == IdentityStatus.ACTIVE
        assert identity.attributes["email"] == "u1@test.com"
        assert "user" in identity.attributes["roles"]

    def test_admin(self):
        identity = TestIdentityFactory.admin(id="admin-1")
        assert identity.id == "admin-1"
        assert "admin" in identity.attributes["roles"]
        assert "*" in identity.attributes["scopes"]

    def test_service(self):
        identity = TestIdentityFactory.service(
            id="svc-1",
            scopes=["read:users", "write:users"],
        )
        assert identity.type == IdentityType.SERVICE
        assert "read:users" in identity.attributes["scopes"]

    def test_anonymous(self):
        identity = TestIdentityFactory.anonymous()
        assert identity.id == "anonymous"
        assert identity.attributes["roles"] == []

    def test_user_auto_id(self):
        i1 = TestIdentityFactory.user()
        i2 = TestIdentityFactory.user()
        assert i1.id != i2.id  # unique auto-generated IDs

    def test_user_custom_roles(self):
        identity = TestIdentityFactory.user(roles=["editor", "reviewer"])
        assert identity.attributes["roles"] == ["editor", "reviewer"]

    def test_user_with_tenant(self):
        identity = TestIdentityFactory.user(tenant_id="org-1")
        assert identity.tenant_id == "org-1"

    def test_user_extra_attrs(self):
        identity = TestIdentityFactory.user(department="engineering")
        assert identity.attributes["department"] == "engineering"


# ============================================================================
# 16. AuthTestMixin
# ============================================================================


class TestAuthTestMixin:
    """Tests for AuthTestMixin."""

    def test_force_login(self):
        identity = TestIdentityFactory.user(id="test-user")

        class FakeClient:
            _default_headers: dict = {}

        class FakeCase(AuthTestMixin):
            client = FakeClient()

        case = FakeCase()
        case.force_login(identity)
        assert case.client._default_headers["X-Test-Identity-Id"] == "test-user"

    def test_force_logout(self):
        class FakeClient:
            _default_headers: dict = {"X-Test-Identity-Id": "u1"}

        class FakeCase(AuthTestMixin):
            client = FakeClient()

        case = FakeCase()
        case.force_logout()
        assert "X-Test-Identity-Id" not in case.client._default_headers


# ============================================================================
# 17. Mail – CapturedMail & outbox
# ============================================================================


class TestMailOutbox:
    """Tests for mail outbox and CapturedMail."""

    def setup_method(self):
        clear_outbox()

    def test_capture_mail(self):
        msg = capture_mail(
            to=["alice@test.com"],
            subject="Welcome",
            body="Hello Alice",
        )
        assert isinstance(msg, CapturedMail)
        assert msg.to == ["alice@test.com"]
        assert msg.subject == "Welcome"
        assert msg.body == "Hello Alice"

    def test_outbox_collects(self):
        capture_mail(to=["a@t.com"], subject="One")
        capture_mail(to=["b@t.com"], subject="Two")
        assert len(get_outbox()) == 2

    def test_clear_outbox(self):
        capture_mail(to=["a@t.com"], subject="Test")
        clear_outbox()
        assert len(get_outbox()) == 0

    def test_captured_mail_repr(self):
        msg = CapturedMail(to=["user@test.com"], subject="Hi")
        assert "user@test.com" in repr(msg)
        assert "Hi" in repr(msg)

    def test_captured_mail_defaults(self):
        msg = CapturedMail(to=["x@y.com"], subject="S")
        assert msg.body == ""
        assert msg.html_body == ""
        assert msg.cc == []
        assert msg.bcc == []
        assert msg.attachments == []
        assert msg.headers == {}
        assert msg.template_name is None


# ============================================================================
# 18. MailTestMixin
# ============================================================================


class TestMailTestMixin:
    """Tests for MailTestMixin."""

    def setup_method(self):
        clear_outbox()

    def test_assert_mail_sent(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test")
        mixin.assert_mail_sent()

    def test_assert_mail_sent_to(self):
        mixin = MailTestMixin()
        capture_mail(to=["alice@example.com"], subject="Hello")
        mixin.assert_mail_sent(to="alice@example.com")

    def test_assert_mail_sent_count(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="1")
        capture_mail(to=["b@t.com"], subject="2")
        mixin.assert_mail_sent(count=2)

    def test_assert_mail_sent_fails(self):
        mixin = MailTestMixin()
        with pytest.raises(AssertionError):
            mixin.assert_mail_sent()

    def test_assert_no_mail_sent(self):
        mixin = MailTestMixin()
        mixin.assert_no_mail_sent()

    def test_assert_no_mail_sent_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Oops")
        with pytest.raises(AssertionError):
            mixin.assert_no_mail_sent()

    def test_assert_mail_subject_contains(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Welcome to Aquilia")
        mixin.assert_mail_subject_contains("Welcome")

    def test_assert_mail_subject_contains_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Hello World")
        with pytest.raises(AssertionError):
            mixin.assert_mail_subject_contains("Goodbye")

    def test_assert_mail_body_contains(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="X", body="Click here to verify")
        mixin.assert_mail_body_contains("verify")

    def test_assert_mail_body_contains_html(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="X", html_body="<b>Important</b>")
        mixin.assert_mail_body_contains("Important")


# ============================================================================
# 19. TestContainer
# ============================================================================


class TestTestContainer:
    """Tests for TestContainer (DI)."""

    def test_register_overwrites(self):
        """TestContainer should allow duplicate registration (overwrite)."""
        from aquilia.di.providers import ValueProvider

        container = TestContainer()
        p1 = ValueProvider(token="MyService", value="v1", scope="singleton")
        p2 = ValueProvider(token="MyService", value="v2", scope="singleton")
        container.register(p1)
        container.register(p2)  # should NOT raise

    def test_resolution_log(self):
        from aquilia.di.providers import ValueProvider

        container = TestContainer()
        container.register(ValueProvider(token="Svc", value=42, scope="singleton"))
        container.resolve("Svc")
        assert "Svc" in container.resolution_log

    def test_reset_clears(self):
        container = TestContainer()
        container.resolution_log.append("Svc")
        container._cache["key"] = "val"
        container.reset()
        assert container.resolution_log == []
        assert container._cache == {}


# ============================================================================
# 20. mock_provider
# ============================================================================


class TestMockProvider:
    """Tests for mock_provider factory."""

    async def test_mock_provider_resolves(self):
        mp = mock_provider("UserRepo", value={"users": []})
        result = await mp.instantiate(None)
        assert result == {"users": []}
        assert mp.resolve_count == 1

    def test_mock_provider_meta(self):
        mp = mock_provider("UserRepo", value="fake")
        assert "mock:" in mp.meta.name
        assert mp.meta.scope == "singleton"

    async def test_mock_provider_shutdown(self):
        mp = mock_provider("Svc", value="x")
        await mp.shutdown()  # should not raise


# ============================================================================
# 21. override_provider
# ============================================================================


class TestOverrideProvider:
    """Tests for override_provider context manager."""

    async def test_override_and_restore(self):
        from aquilia.di.providers import ValueProvider

        container = TestContainer()
        original_provider = ValueProvider(token="Svc", value="original", scope="singleton")
        container.register(original_provider)
        cache_key = container._make_cache_key("Svc", None)

        async with override_provider(container, "Svc", "mocked") as mock:
            # Mock provider should be installed
            assert container._providers[cache_key] is mock

        # After exit, original provider should be restored
        assert container._providers[cache_key] is original_provider


# ============================================================================
# 22. AquiliaAssertions
# ============================================================================


class TestAquiliaAssertions:
    """Tests for assertion mixin methods."""

    def _response(self, status=200, headers=None, body=b""):
        return TestResponse(status, headers or {}, body)

    def setup_method(self):
        self.a = AquiliaAssertions()

    # -- Status assertions --

    def test_assert_status_pass(self):
        self.a.assert_status(self._response(200), 200)

    def test_assert_status_fail(self):
        with pytest.raises(AssertionError, match="Expected status 404"):
            self.a.assert_status(self._response(200), 404)

    def test_assert_success(self):
        self.a.assert_success(self._response(200))
        self.a.assert_success(self._response(201))

    def test_assert_success_fail(self):
        with pytest.raises(AssertionError, match="Expected 2xx"):
            self.a.assert_success(self._response(404))

    def test_assert_redirect(self):
        r = self._response(302, headers={"location": "/dashboard"})
        self.a.assert_redirect(r)
        self.a.assert_redirect(r, location="/dashboard")

    def test_assert_redirect_wrong_location(self):
        r = self._response(302, headers={"location": "/other"})
        with pytest.raises(AssertionError):
            self.a.assert_redirect(r, location="/dashboard")

    def test_assert_not_found(self):
        self.a.assert_not_found(self._response(404))

    def test_assert_forbidden(self):
        self.a.assert_forbidden(self._response(403))

    def test_assert_unauthorized(self):
        self.a.assert_unauthorized(self._response(401))

    def test_assert_bad_request(self):
        self.a.assert_bad_request(self._response(400))

    # -- JSON assertions --

    def test_assert_json(self):
        r = self._response(
            200,
            headers={"content-type": "application/json"},
            body=b'{"ok": true}',
        )
        self.a.assert_json(r)
        self.a.assert_json(r, expected={"ok": True})

    def test_assert_json_wrong_content_type(self):
        r = self._response(200, headers={"content-type": "text/html"})
        with pytest.raises(AssertionError, match="Expected JSON"):
            self.a.assert_json(r)

    def test_assert_json_contains(self):
        r = self._response(
            200,
            headers={"content-type": "application/json"},
            body=json.dumps({"name": "Alice", "age": 30}).encode(),
        )
        self.a.assert_json_contains(r, {"name": "Alice"})

    def test_assert_json_contains_missing_key(self):
        r = self._response(body=json.dumps({"a": 1}).encode())
        with pytest.raises(AssertionError, match="Missing key"):
            self.a.assert_json_contains(r, {"b": 2})

    def test_assert_json_key(self):
        r = self._response(body=json.dumps({"token": "abc"}).encode())
        self.a.assert_json_key(r, "token")

    def test_assert_json_key_missing(self):
        r = self._response(body=json.dumps({"a": 1}).encode())
        with pytest.raises(AssertionError, match="not found"):
            self.a.assert_json_key(r, "missing")

    # -- HTML assertions --

    def test_assert_html(self):
        r = self._response(200, headers={"content-type": "text/html"})
        self.a.assert_html(r)

    def test_assert_html_fail(self):
        r = self._response(200, headers={"content-type": "application/json"})
        with pytest.raises(AssertionError, match="Expected HTML"):
            self.a.assert_html(r)

    # -- Header assertions --

    def test_assert_header(self):
        r = self._response(200, headers={"x-request-id": "abc"})
        self.a.assert_header(r, "x-request-id")
        self.a.assert_header(r, "x-request-id", "abc")

    def test_assert_header_wrong_value(self):
        r = self._response(200, headers={"x-request-id": "abc"})
        with pytest.raises(AssertionError):
            self.a.assert_header(r, "x-request-id", "xyz")

    def test_assert_no_header(self):
        r = self._response(200)
        self.a.assert_no_header(r, "x-missing")

    def test_assert_no_header_fails(self):
        r = self._response(200, headers={"x-present": "yes"})
        with pytest.raises(AssertionError, match="unexpectedly present"):
            self.a.assert_no_header(r, "x-present")

    # -- Cookie assertion --

    def test_assert_cookie(self):
        r = self._response(200, headers={"set-cookie": "session=abc; Path=/"})
        self.a.assert_cookie(r, "session")

    def test_assert_cookie_missing(self):
        r = self._response(200)
        with pytest.raises(AssertionError):
            self.a.assert_cookie(r, "session")

    # -- Body assertion --

    def test_assert_body_contains(self):
        r = self._response(200, body=b"Welcome to Aquilia")
        self.a.assert_body_contains(r, "Aquilia")

    def test_assert_body_contains_fail(self):
        r = self._response(200, body=b"Hello World")
        with pytest.raises(AssertionError, match="not found"):
            self.a.assert_body_contains(r, "Aquilia")

    # -- Fault assertions --

    def test_assert_fault_raised(self):
        engine = MockFaultEngine()
        f = Fault(code="ERR", message="x", domain=FaultDomain.SYSTEM, severity=Severity.ERROR)
        engine.emit(f)
        self.a.assert_fault_raised(engine, code="ERR")

    def test_assert_fault_raised_fails(self):
        engine = MockFaultEngine()
        with pytest.raises(AssertionError, match="No fault"):
            self.a.assert_fault_raised(engine, code="MISSING")

    def test_assert_no_faults(self):
        engine = MockFaultEngine()
        self.a.assert_no_faults(engine)

    def test_assert_no_faults_fails(self):
        engine = MockFaultEngine()
        engine.emit(Fault(code="X", message="x", domain=FaultDomain.SYSTEM, severity=Severity.ERROR))
        with pytest.raises(AssertionError, match="Expected no faults"):
            self.a.assert_no_faults(engine)

    # -- DI assertions --

    def test_assert_registered(self):
        from aquilia.di.providers import ValueProvider
        container = TestContainer()
        container.register(ValueProvider(token="Svc", value=42, scope="singleton"))
        self.a.assert_registered(container, "Svc")

    def test_assert_registered_fails(self):
        container = TestContainer()
        with pytest.raises(AssertionError, match="not registered"):
            self.a.assert_registered(container, "Missing")

    def test_assert_resolves(self):
        from aquilia.di.providers import ValueProvider
        container = TestContainer()
        container.register(ValueProvider(token="Svc", value=99, scope="singleton"))
        self.a.assert_resolves(container, "Svc")


# ============================================================================
# 23. SimpleTestCase
# ============================================================================


class TestSimpleTestCase:
    """Tests for SimpleTestCase base class."""

    def test_has_assertion_mixin(self):
        assert issubclass(SimpleTestCase, AquiliaAssertions)

    def test_is_test_case(self):
        import unittest
        assert issubclass(SimpleTestCase, unittest.TestCase)


# ============================================================================
# 24. Pytest Fixtures (module-level)
# ============================================================================


class TestFixtures:
    """Tests for pytest fixtures provided by aquilia.testing.fixtures."""

    def test_test_config_fixture(self, test_config):
        assert isinstance(test_config, TestConfig)
        assert test_config.get("debug") is True
        assert test_config.get("runtime.mode") == "test"

    def test_fault_engine_fixture(self, fault_engine):
        assert isinstance(fault_engine, MockFaultEngine)
        assert fault_engine.fault_count == 0

    def test_effect_registry_fixture(self, effect_registry):
        assert isinstance(effect_registry, MockEffectRegistry)

    def test_cache_backend_fixture(self, cache_backend):
        assert isinstance(cache_backend, MockCacheBackend)
        assert cache_backend.get_count == 0

    def test_di_container_fixture(self, di_container):
        assert isinstance(di_container, TestContainer)

    def test_identity_factory_fixture(self, identity_factory):
        assert isinstance(identity_factory, TestIdentityFactory)
        user = identity_factory.user(id="fix-1")
        assert user.id == "fix-1"

    def test_mail_outbox_fixture(self, mail_outbox):
        assert isinstance(mail_outbox, list)
        assert len(mail_outbox) == 0

    def test_test_request_fixture(self, test_request):
        """test_request is a factory callable."""
        req = test_request(method="POST", path="/api")
        assert req.method == "POST"

    def test_test_scope_fixture(self, test_scope):
        """test_scope is a factory callable."""
        scope = test_scope(method="DELETE", path="/item/1")
        assert scope["method"] == "DELETE"
        assert scope["path"] == "/item/1"


# ============================================================================
# 25. CLI test command
# ============================================================================


class TestCLITestCommand:
    """Tests for CLI test command helpers."""

    def test_discover_test_dirs(self):
        from aquilia.cli.commands.test import _discover_test_dirs
        dirs = _discover_test_dirs()
        # Should return at least the tests/ directory if CWD has one
        assert isinstance(dirs, list)

    def test_run_tests_returns_int(self):
        """run_tests should return an integer exit code."""
        from aquilia.cli.commands.test import run_tests
        # Run with a nonexistent path so it exits quickly
        code = run_tests(paths=["__nonexistent_test_dir__"], extra_args=["--co", "-q"])
        assert isinstance(code, int)


# ============================================================================
# 26. Integration: Fixtures + Assertions together
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple testing components."""

    def test_fault_engine_with_assertions(self, fault_engine):
        a = AquiliaAssertions()
        a.assert_no_faults(fault_engine)

        f = Fault(code="INT_ERR", message="test", domain=FaultDomain.IO, severity=Severity.ERROR)
        fault_engine.emit(f)
        a.assert_fault_raised(fault_engine, code="INT_ERR")

    async def test_cache_backend_flow(self, cache_backend):
        await cache_backend.set("user:1", {"name": "Alice"})
        await cache_backend.set("user:2", {"name": "Bob"})

        assert await cache_backend.exists("user:1")
        assert not await cache_backend.exists("user:3")

        keys = await cache_backend.keys("user:*")
        assert len(keys) == 2

        await cache_backend.delete("user:1")
        assert not await cache_backend.exists("user:1")

    async def test_effect_registry_flow(self, effect_registry):
        mock = effect_registry.register_mock("DBTx", return_value="db_conn")
        provider = effect_registry.get_provider("DBTx")
        resource = await provider.acquire(mode="write")
        assert resource == "db_conn"
        assert mock.acquire_count == 1
        await provider.release(resource, success=True)
        assert mock.release_count == 1

    def test_identity_in_auth_mixin(self, identity_factory):
        admin = identity_factory.admin(id="admin-x")

        class FakeClient:
            _default_headers: dict = {}

        class Case(AuthTestMixin):
            client = FakeClient()

        case = Case()
        case.force_login(admin)
        assert case.client._default_headers["X-Test-Identity-Id"] == "admin-x"
        case.force_logout()
        assert "X-Test-Identity-Id" not in case.client._default_headers

    def test_di_container_with_mock_provider(self, di_container):
        mp = mock_provider("CacheService", value="fake_cache")
        di_container.register(mp)
        result = di_container.resolve("CacheService")
        assert result is not None  # resolve returns from cache or provider
        assert "CacheService" in di_container.resolution_log

    def test_mail_workflow(self, mail_outbox):
        mixin = MailTestMixin()
        mixin.assert_no_mail_sent()
        capture_mail(to=["user@test.com"], subject="Activation", body="Click link")
        mixin.assert_mail_sent(to="user@test.com")
        mixin.assert_mail_subject_contains("Activation")
        mixin.assert_mail_body_contains("Click link")
        assert len(mail_outbox) == 1

    async def test_client_with_echo_app(self):
        """Full integration: TestClient → ASGI app → assertions."""
        async def api_app(scope, receive, send):
            await receive()
            body = json.dumps({"status": "ok"}).encode()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"application/json"),
                ],
            })
            await send({"type": "http.response.body", "body": body})

        client = TestClient(api_app)
        resp = await client.get("/health")

        a = AquiliaAssertions()
        a.assert_status(resp, 200)
        a.assert_success(resp)
        a.assert_json(resp, expected={"status": "ok"})
        a.assert_json_contains(resp, {"status": "ok"})
        a.assert_json_key(resp, "status")
        a.assert_header(resp, "content-type")
        a.assert_body_contains(resp, "ok")


# ============================================================================
# 28. Enhanced TestResponse features
# ============================================================================


class TestTestResponseEnhancements:
    """Tests for enhanced TestResponse features."""

    def _make(self, status=200, headers=None, body=b"", **kw):
        return TestResponse(status_code=status, headers=headers or {}, body=body, **kw)

    def test_elapsed_time(self):
        r = self._make(elapsed=12.5)
        assert r.elapsed == 12.5

    def test_request_method_and_path(self):
        r = self._make(request_method="POST", request_path="/api/users")
        assert r.request_method == "POST"
        assert r.request_path == "/api/users"

    def test_content_length_present(self):
        r = self._make(headers={"content-length": "42"})
        assert r.content_length == 42

    def test_content_length_absent(self):
        r = self._make()
        assert r.content_length is None

    def test_location_present(self):
        r = self._make(302, headers={"location": "/dashboard"})
        assert r.location == "/dashboard"

    def test_location_absent(self):
        r = self._make(200)
        assert r.location is None

    def test_has_header_true(self):
        r = self._make(headers={"x-request-id": "abc"})
        assert r.has_header("x-request-id")
        assert r.has_header("X-Request-Id")

    def test_has_header_false(self):
        r = self._make()
        assert not r.has_header("x-missing")

    def test_repr_includes_elapsed(self):
        r = self._make(200, elapsed=5.3)
        assert "5.3ms" in repr(r)


# ============================================================================
# 29. Enhanced TestClient features
# ============================================================================


class TestTestClientEnhancements:
    """Tests for enhanced TestClient features."""

    @staticmethod
    async def _echo_app(scope, receive, send):
        body_msg = await receive()
        body = body_msg.get("body", b"")
        response_body = json.dumps({
            "method": scope["method"],
            "path": scope["path"],
            "query": scope["query_string"].decode(),
            "body": body.decode() if body else "",
            "headers": {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in scope["headers"]
            },
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(response_body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": response_body})

    async def test_set_bearer_token(self):
        client = TestClient(self._echo_app)
        client.set_bearer_token("my-jwt-token")
        resp = await client.get("/protected")
        data = resp.json()
        assert data["headers"]["authorization"] == "Bearer my-jwt-token"

    async def test_clear_auth(self):
        client = TestClient(self._echo_app)
        client.set_bearer_token("tok")
        client.clear_auth()
        resp = await client.get("/")
        data = resp.json()
        assert "authorization" not in data["headers"]

    async def test_delete_cookie(self):
        client = TestClient(self._echo_app)
        client.set_cookie("a", "1")
        client.set_cookie("b", "2")
        client.delete_cookie("a")
        resp = await client.get("/")
        data = resp.json()
        cookie_header = data["headers"].get("cookie", "")
        assert "a=1" not in cookie_header
        assert "b=2" in cookie_header

    async def test_cookies_property(self):
        client = TestClient(self._echo_app)
        client.set_cookie("session", "abc")
        client.set_cookie("lang", "en")
        cookies = client.cookies
        assert cookies == {"session": "abc", "lang": "en"}
        # Should be a copy
        cookies["new"] = "val"
        assert "new" not in client.cookies

    async def test_follow_redirects(self):
        """Test automatic redirect following."""
        redirect_count = 0

        async def redirect_app(scope, receive, send):
            nonlocal redirect_count
            await receive()
            path = scope["path"]
            if path == "/start":
                redirect_count += 1
                await send({
                    "type": "http.response.start",
                    "status": 302,
                    "headers": [(b"location", b"/end")],
                })
                await send({"type": "http.response.body", "body": b""})
            else:
                body = b'{"done": true}'
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({"type": "http.response.body", "body": body})

        client = TestClient(redirect_app, follow_redirects=True)
        resp = await client.get("/start")
        assert resp.status_code == 200
        assert resp.json() == {"done": True}
        assert len(client.history) == 1
        assert client.history[0].status_code == 302

    async def test_response_elapsed_is_set(self):
        """Responses should have elapsed time set."""
        client = TestClient(self._echo_app)
        resp = await client.get("/")
        assert resp.elapsed >= 0.0

    async def test_response_request_method_and_path(self):
        client = TestClient(self._echo_app)
        resp = await client.post("/api/data", json={"x": 1})
        assert resp.request_method == "POST"
        assert resp.request_path == "/api/data"

    async def test_multipart_upload(self):
        """Test file upload via multipart/form-data."""
        client = TestClient(self._echo_app)
        files = {"avatar": ("notes.txt", b"hello world", "text/plain")}
        resp = await client.post("/upload", files=files, data={"name": "alice"})
        data = resp.json()
        assert "multipart/form-data" in data["headers"]["content-type"]
        assert "notes.txt" in data["body"]
        assert "alice" in data["body"]


# ============================================================================
# 30. Enhanced TestConfig features
# ============================================================================


class TestTestConfigEnhancements:
    """Tests for enhanced TestConfig dict-like interface."""

    def test_set_simple(self):
        cfg = TestConfig(debug=False)
        cfg.set("debug", True)
        assert cfg.get("debug") is True

    def test_set_dotted(self):
        cfg = TestConfig(database={"url": "sqlite:///old.db"})
        cfg.set("database.url", "sqlite:///new.db")
        assert cfg.get("database.url") == "sqlite:///new.db"

    def test_set_invalidates_cache(self):
        cfg = TestConfig(name="old")
        _ = cfg.to_dict()  # prime cache
        cfg.set("name", "new")
        assert cfg.to_dict()["name"] == "new"

    def test_has(self):
        cfg = TestConfig(debug=True, nested={"key": "val"})
        assert cfg.has("debug")
        assert cfg.has("nested.key")
        assert not cfg.has("missing")

    def test_keys(self):
        cfg = TestConfig(a=1, b=2, c=3)
        assert sorted(cfg.keys()) == ["a", "b", "c"]

    def test_config_data_property(self):
        cfg = TestConfig(debug=True, name="test")
        data = cfg.config_data
        assert data["debug"] is True
        assert data["name"] == "test"

    def test_contains(self):
        cfg = TestConfig(debug=True)
        assert "debug" in cfg
        assert "missing" not in cfg

    def test_getitem(self):
        cfg = TestConfig(debug=True)
        assert cfg["debug"] is True

    def test_getitem_missing_raises(self):
        cfg = TestConfig()
        with pytest.raises(KeyError):
            _ = cfg["nonexistent"]

    def test_repr(self):
        cfg = TestConfig(debug=True)
        r = repr(cfg)
        assert "TestConfig" in r


# ============================================================================
# 31. Enhanced MockCacheBackend features
# ============================================================================


class TestMockCacheBackendEnhancements:
    """Tests for enhanced MockCacheBackend: TTL tracking, increment, mget/mset."""

    async def test_ttl_tracking(self):
        cache = MockCacheBackend()
        await cache.set("key", "val", ttl=60)
        remaining = cache.get_ttl("key")
        assert remaining is not None
        assert remaining > 0

    async def test_ttl_none_for_missing(self):
        cache = MockCacheBackend()
        assert cache.get_ttl("missing") is None

    async def test_get_or_set_existing(self):
        cache = MockCacheBackend()
        await cache.set("existing", "val")
        result = await cache.get_or_set("existing", "new_val", ttl=60)
        assert result == "val"  # existing value returned

    async def test_get_or_set_missing(self):
        cache = MockCacheBackend()
        result = await cache.get_or_set("missing", "new_val", ttl=60)
        assert result == "new_val"
        assert await cache.get("missing") == "new_val"

    async def test_increment(self):
        cache = MockCacheBackend()
        await cache.set("counter", 10)
        result = await cache.increment("counter")
        assert result == 11
        assert await cache.get("counter") == 11

    async def test_increment_delta(self):
        cache = MockCacheBackend()
        await cache.set("counter", 5)
        result = await cache.increment("counter", delta=3)
        assert result == 8

    async def test_increment_missing_starts_at_zero(self):
        cache = MockCacheBackend()
        result = await cache.increment("new_counter")
        assert result == 1

    async def test_decrement(self):
        cache = MockCacheBackend()
        await cache.set("counter", 10)
        result = await cache.decrement("counter")
        assert result == 9

    async def test_decrement_delta(self):
        cache = MockCacheBackend()
        await cache.set("counter", 10)
        result = await cache.decrement("counter", delta=5)
        assert result == 5

    async def test_mget(self):
        cache = MockCacheBackend()
        await cache.set("a", 1)
        await cache.set("b", 2)
        results = await cache.mget("a", "b", "c")
        assert results == [1, 2, None]

    async def test_mset(self):
        cache = MockCacheBackend()
        await cache.mset({"x": 10, "y": 20}, ttl=300)
        assert await cache.get("x") == 10
        assert await cache.get("y") == 20

    async def test_size_property(self):
        cache = MockCacheBackend()
        assert cache.size == 0
        await cache.set("a", 1)
        await cache.set("b", 2)
        assert cache.size == 2

    async def test_clear_clears_ttls(self):
        cache = MockCacheBackend()
        await cache.set("a", 1, ttl=60)
        await cache.clear()
        assert cache.get_ttl("a") is None

    async def test_reset_clears_ttls(self):
        cache = MockCacheBackend()
        await cache.set("a", 1, ttl=60)
        cache.reset()
        assert cache._ttls == {}


# ============================================================================
# 32. Enhanced CacheTestMixin features
# ============================================================================


class TestCacheTestMixinEnhancements:
    """Tests for enhanced CacheTestMixin: assert_cache_value, assert_cache_count."""

    async def test_assert_cache_value(self):
        cache = MockCacheBackend()
        await cache.set("key", "expected")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.assert_cache_value("key", "expected")

    async def test_assert_cache_value_fails(self):
        cache = MockCacheBackend()
        await cache.set("key", "actual")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        with pytest.raises(AssertionError):
            await case.assert_cache_value("key", "wrong")

    async def test_assert_cache_count(self):
        cache = MockCacheBackend()
        await cache.set("user:1", "a")
        await cache.set("user:2", "b")
        await cache.set("session:1", "c")

        class FakeCase(CacheTestMixin):
            cache_backend = cache

        case = FakeCase()
        await case.assert_cache_count(3)
        await case.assert_cache_count(2, pattern="user:*")


# ============================================================================
# 33. Enhanced MockFaultEngine features
# ============================================================================


class TestMockFaultEngineEnhancements:
    """Tests for enhanced MockFaultEngine: severity filter, last_fault, async ctx."""

    def _make_fault(self, code="ERR", severity=Severity.ERROR):
        return Fault(
            code=code, message="test", domain=FaultDomain.SYSTEM, severity=severity,
        )

    def test_get_faults_by_severity(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("A", Severity.ERROR))
        engine.emit(self._make_fault("B", Severity.WARN))
        engine.emit(self._make_fault("C", Severity.ERROR))
        errors = engine.get_faults(severity=Severity.ERROR)
        assert len(errors) == 2

    def test_last_fault(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("FIRST"))
        engine.emit(self._make_fault("SECOND"))
        assert engine.last_fault is not None
        assert engine.last_fault.code == "SECOND"

    def test_last_fault_empty(self):
        engine = MockFaultEngine()
        assert engine.last_fault is None

    def test_last_fault_code(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("MY_CODE"))
        assert engine.last_fault_code == "MY_CODE"

    def test_last_fault_code_empty(self):
        engine = MockFaultEngine()
        assert engine.last_fault_code is None

    def test_has_fault_with_severity(self):
        engine = MockFaultEngine()
        engine.emit(self._make_fault("A", Severity.WARN))
        assert engine.has_fault_with_severity(Severity.WARN)
        assert not engine.has_fault_with_severity(Severity.ERROR)

    async def test_async_context_manager(self):
        engine = MockFaultEngine()
        async with engine:
            engine.emit(self._make_fault())
            assert engine.fault_count == 1
        assert engine.fault_count == 0


# ============================================================================
# 34. Enhanced MockEffectProvider features
# ============================================================================


class TestMockEffectProviderEnhancements:
    """Tests for enhanced MockEffectProvider: call_history, return_sequence."""

    async def test_return_sequence(self):
        p = MockEffectProvider(return_sequence=["a", "b", "c"])
        assert await p.acquire() == "a"
        assert await p.acquire() == "b"
        assert await p.acquire() == "c"
        assert await p.acquire() == "c"  # last value repeats

    async def test_call_history_acquire(self):
        p = MockEffectProvider(return_value="x")
        await p.acquire(mode="read")
        assert len(p.call_history) == 1
        call = p.call_history[0]
        assert isinstance(call, EffectCall)
        assert call.action == "acquire"
        assert call.mode == "read"
        assert call.timestamp > 0

    async def test_call_history_release(self):
        p = MockEffectProvider(return_value="x")
        r = await p.acquire()
        await p.release(r, success=True)
        assert len(p.call_history) == 2
        release_call = p.call_history[1]
        assert release_call.action == "release"
        assert release_call.resource == "x"
        assert release_call.success is True

    async def test_last_acquired_mode(self):
        p = MockEffectProvider(return_value="x")
        assert p.last_acquired_mode is None
        await p.acquire(mode="write")
        assert p.last_acquired_mode == "write"

    async def test_reset_clears_history(self):
        p = MockEffectProvider(return_sequence=["a", "b"])
        await p.acquire()
        await p.acquire()
        p.reset()
        assert p.call_history == []
        assert p._sequence_idx == 0
        # After reset, sequence restarts
        assert await p.acquire() == "a"


# ============================================================================
# 35. Enhanced TestIdentityFactory & IdentityBuilder
# ============================================================================


class TestIdentityBuilderEnhancements:
    """Tests for IdentityBuilder fluent API."""

    def test_build_basic(self):
        identity = TestIdentityFactory.build("u-1").create()
        assert identity.id == "u-1"
        assert identity.type == IdentityType.USER
        assert identity.status == IdentityStatus.ACTIVE

    def test_build_with_roles_and_scopes(self):
        identity = (
            TestIdentityFactory.build("u-2")
            .with_roles("admin", "editor")
            .with_scopes("read:*", "write:*")
            .create()
        )
        assert identity.attributes["roles"] == ["admin", "editor"]
        assert identity.attributes["scopes"] == ["read:*", "write:*"]

    def test_build_with_email_and_name(self):
        identity = (
            TestIdentityFactory.build("u-3")
            .with_email("alice@test.com")
            .with_name("Alice Wonderland")
            .create()
        )
        assert identity.attributes["email"] == "alice@test.com"
        assert identity.attributes["display_name"] == "Alice Wonderland"

    def test_build_with_tenant(self):
        identity = TestIdentityFactory.build("u-4").with_tenant("org-1").create()
        assert identity.tenant_id == "org-1"

    def test_build_as_service(self):
        identity = TestIdentityFactory.build("svc-1").as_service().create()
        assert identity.type == IdentityType.SERVICE

    def test_build_as_suspended(self):
        identity = TestIdentityFactory.build("u-5").as_suspended().create()
        assert identity.status == IdentityStatus.SUSPENDED

    def test_build_with_attr(self):
        identity = (
            TestIdentityFactory.build("u-6")
            .with_attr("department", "engineering")
            .create()
        )
        assert identity.attributes["department"] == "engineering"

    def test_build_with_status_and_type(self):
        identity = (
            TestIdentityFactory.build("u-7")
            .with_status(IdentityStatus.SUSPENDED)
            .with_type(IdentityType.SERVICE)
            .create()
        )
        assert identity.status == IdentityStatus.SUSPENDED
        assert identity.type == IdentityType.SERVICE

    def test_suspended_factory(self):
        identity = TestIdentityFactory.suspended(id="sus-1")
        assert identity.status == IdentityStatus.SUSPENDED
        assert identity.type == IdentityType.USER

    def test_builder_chaining(self):
        """Builder methods should return self for chaining."""
        builder = IdentityBuilder("x")
        result = builder.with_roles("a").with_scopes("b").with_email("e@t.com")
        assert result is builder


# ============================================================================
# 36. Enhanced AuthTestMixin features
# ============================================================================


class TestAuthTestMixinEnhancements:
    """Tests for enhanced AuthTestMixin: current_identity, login_as_admin/user."""

    def _make_case(self):
        class FakeClient:
            _default_headers: dict = {}

        class Case(AuthTestMixin):
            client = FakeClient()

        return Case()

    def test_current_identity(self):
        case = self._make_case()
        assert case.current_identity is None
        identity = TestIdentityFactory.user(id="u-1")
        case.force_login(identity)
        assert case.current_identity is not None
        assert case.current_identity.id == "u-1"

    def test_is_authenticated(self):
        case = self._make_case()
        assert not case.is_authenticated
        case.force_login(TestIdentityFactory.user(id="u-2"))
        assert case.is_authenticated
        case.force_logout()
        assert not case.is_authenticated

    def test_login_as_admin(self):
        case = self._make_case()
        identity = case.login_as_admin(id="admin-99")
        assert identity.id == "admin-99"
        assert "admin" in identity.attributes["roles"]
        assert case.is_authenticated

    def test_login_as_user(self):
        case = self._make_case()
        identity = case.login_as_user(id="user-88")
        assert identity.id == "user-88"
        assert "user" in identity.attributes["roles"]
        assert case.is_authenticated


# ============================================================================
# 37. Enhanced DI features: factory_provider, spy_provider, register shortcuts
# ============================================================================


class TestDIEnhancements:
    """Tests for factory_provider, spy_provider, and TestContainer shortcuts."""

    async def test_factory_provider_creates_new_each_time(self):
        call_count = 0

        def make_service():
            nonlocal call_count
            call_count += 1
            return {"instance": call_count}

        fp = factory_provider("MySvc", make_service)
        result1 = await fp.instantiate()
        result2 = await fp.instantiate()
        assert result1 == {"instance": 1}
        assert result2 == {"instance": 2}
        assert fp.resolve_count == 2

    async def test_factory_provider_meta(self):
        fp = factory_provider("MySvc", lambda: "x", scope="transient")
        assert "factory:" in fp.meta.name
        assert fp.meta.scope == "transient"

    async def test_spy_provider(self):
        from aquilia.di.providers import ValueProvider

        container = TestContainer()
        container.register(ValueProvider(token="Svc", value=42, scope="singleton"))

        async with spy_provider(container, "Svc") as spy:
            result = await container.resolve_async("Svc")
            assert spy.resolve_count == 1
            assert spy.resolved_values == [42]

    async def test_spy_provider_missing_raises(self):
        container = TestContainer()
        with pytest.raises(KeyError):
            async with spy_provider(container, "NonExistent") as spy:
                pass

    def test_register_value_shortcut(self):
        container = TestContainer()
        provider = container.register_value("MyToken", "my_value")
        assert provider is not None
        result = container.resolve("MyToken")
        assert result is not None
        assert "MyToken" in container.resolution_log

    def test_register_factory_shortcut(self):
        container = TestContainer()
        call_count = 0

        def make():
            nonlocal call_count
            call_count += 1
            return call_count

        provider = container.register_factory("Counter", make)
        assert provider is not None


# ============================================================================
# 38. Enhanced MailTestMixin features
# ============================================================================


class TestMailTestMixinEnhancements:
    """Tests for enhanced MailTestMixin methods."""

    def setup_method(self):
        clear_outbox()

    def test_latest_mail(self):
        mixin = MailTestMixin()
        assert mixin.latest_mail is None
        capture_mail(to=["a@t.com"], subject="First")
        capture_mail(to=["b@t.com"], subject="Second")
        assert mixin.latest_mail.subject == "Second"

    def test_get_mail_for(self):
        mixin = MailTestMixin()
        capture_mail(to=["alice@t.com"], subject="For Alice")
        capture_mail(to=["bob@t.com"], subject="For Bob")
        capture_mail(to=["alice@t.com"], subject="Another for Alice")
        alice_mail = mixin.get_mail_for("alice@t.com")
        assert len(alice_mail) == 2

    def test_assert_mail_count(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="One")
        capture_mail(to=["b@t.com"], subject="Two")
        mixin.assert_mail_count(2)

    def test_assert_mail_count_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="One")
        with pytest.raises(AssertionError, match="Expected 5"):
            mixin.assert_mail_count(5)

    def test_assert_mail_to(self):
        mixin = MailTestMixin()
        capture_mail(to=["target@t.com"], subject="Test")
        mixin.assert_mail_to("target@t.com")

    def test_assert_mail_to_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["other@t.com"], subject="Test")
        with pytest.raises(AssertionError, match="No mail sent to"):
            mixin.assert_mail_to("missing@t.com")

    def test_assert_mail_from(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", from_email="noreply@app.com")
        mixin.assert_mail_from("noreply@app.com")

    def test_assert_mail_from_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", from_email="other@app.com")
        with pytest.raises(AssertionError, match="No mail from"):
            mixin.assert_mail_from("noreply@app.com")

    def test_assert_mail_has_attachment(self):
        mixin = MailTestMixin()
        capture_mail(
            to=["a@t.com"], subject="Test",
            attachments=[{"filename": "report.pdf", "data": b"..."}],
        )
        mixin.assert_mail_has_attachment()
        mixin.assert_mail_has_attachment(filename="report.pdf")

    def test_assert_mail_has_attachment_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test")
        with pytest.raises(AssertionError, match="No mail with attachments"):
            mixin.assert_mail_has_attachment()

    def test_assert_mail_has_attachment_wrong_name(self):
        mixin = MailTestMixin()
        capture_mail(
            to=["a@t.com"], subject="Test",
            attachments=[{"filename": "report.pdf"}],
        )
        with pytest.raises(AssertionError, match="No mail with attachment"):
            mixin.assert_mail_has_attachment(filename="invoice.pdf")

    def test_assert_mail_cc(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", cc=["cc@t.com"])
        mixin.assert_mail_cc("cc@t.com")

    def test_assert_mail_cc_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", cc=[])
        with pytest.raises(AssertionError, match="No mail with CC"):
            mixin.assert_mail_cc("missing@t.com")

    def test_assert_mail_bcc(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", bcc=["bcc@t.com"])
        mixin.assert_mail_bcc("bcc@t.com")

    def test_assert_mail_bcc_fails(self):
        mixin = MailTestMixin()
        capture_mail(to=["a@t.com"], subject="Test", bcc=[])
        with pytest.raises(AssertionError, match="No mail with BCC"):
            mixin.assert_mail_bcc("missing@t.com")


# ============================================================================
# 39. Enhanced assertions
# ============================================================================


class TestAssertionsEnhancements:
    """Tests for the enhanced assertion methods."""

    def _response(self, status=200, headers=None, body=b""):
        return TestResponse(status, headers or {}, body)

    def setup_method(self):
        self.a = AquiliaAssertions()

    # -- New status assertions --

    def test_assert_status_in_range(self):
        self.a.assert_status_in_range(self._response(201), 200, 299)

    def test_assert_status_in_range_fails(self):
        with pytest.raises(AssertionError):
            self.a.assert_status_in_range(self._response(404), 200, 299)

    def test_assert_created(self):
        self.a.assert_created(self._response(201))

    def test_assert_created_fails(self):
        with pytest.raises(AssertionError):
            self.a.assert_created(self._response(200))

    def test_assert_accepted(self):
        self.a.assert_accepted(self._response(202))

    def test_assert_no_content(self):
        self.a.assert_no_content(self._response(204))

    def test_assert_method_not_allowed(self):
        self.a.assert_method_not_allowed(self._response(405))

    def test_assert_conflict(self):
        self.a.assert_conflict(self._response(409))

    def test_assert_gone(self):
        self.a.assert_gone(self._response(410))

    def test_assert_unprocessable(self):
        self.a.assert_unprocessable(self._response(422))

    def test_assert_too_many_requests(self):
        self.a.assert_too_many_requests(self._response(429))

    def test_assert_server_error(self):
        self.a.assert_server_error(self._response(500))

    def test_assert_service_unavailable(self):
        self.a.assert_service_unavailable(self._response(503))

    # -- New JSON assertions --

    def test_assert_json_path(self):
        data = {"user": {"name": "Alice", "address": {"city": "Paris"}}}
        r = self._response(body=json.dumps(data).encode())
        self.a.assert_json_path(r, "user.name", "Alice")
        self.a.assert_json_path(r, "user.address.city", "Paris")

    def test_assert_json_path_exists_only(self):
        data = {"key": "val"}
        r = self._response(body=json.dumps(data).encode())
        self.a.assert_json_path(r, "key")  # no expected value = just check existence

    def test_assert_json_path_missing(self):
        data = {"a": 1}
        r = self._response(body=json.dumps(data).encode())
        with pytest.raises(AssertionError):
            self.a.assert_json_path(r, "b.c.d")

    def test_assert_json_list(self):
        r = self._response(body=json.dumps([1, 2, 3]).encode())
        self.a.assert_json_list(r)

    def test_assert_json_list_fails_on_dict(self):
        r = self._response(body=json.dumps({"a": 1}).encode())
        with pytest.raises(AssertionError):
            self.a.assert_json_list(r)

    def test_assert_json_length(self):
        r = self._response(body=json.dumps([1, 2, 3]).encode())
        self.a.assert_json_length(r, 3)

    def test_assert_json_length_dict(self):
        r = self._response(body=json.dumps({"a": 1, "b": 2}).encode())
        self.a.assert_json_length(r, 2)

    def test_assert_json_not_empty(self):
        r = self._response(body=json.dumps([1]).encode())
        self.a.assert_json_not_empty(r)

    def test_assert_json_not_empty_fails(self):
        r = self._response(body=json.dumps([]).encode())
        with pytest.raises(AssertionError):
            self.a.assert_json_not_empty(r)

    # -- New content assertions --

    def test_assert_content_type(self):
        r = self._response(headers={"content-type": "application/json"})
        self.a.assert_content_type(r, "application/json")

    def test_assert_content_length(self):
        r = self._response(headers={"content-length": "42"}, body=b"x" * 42)
        self.a.assert_content_length(r, 42)

    # -- New header assertions --

    def test_assert_header_contains(self):
        r = self._response(headers={"x-custom": "hello world"})
        self.a.assert_header_contains(r, "x-custom", "world")

    def test_assert_header_contains_fails(self):
        r = self._response(headers={"x-custom": "hello world"})
        with pytest.raises(AssertionError):
            self.a.assert_header_contains(r, "x-custom", "missing")

    # -- New cookie assertions --

    def test_assert_cookie_value(self):
        r = self._response(headers={"set-cookie": "session=abc123; Path=/"})
        self.a.assert_cookie_value(r, "session", "abc123")

    def test_assert_no_cookie(self):
        r = self._response(headers={})
        self.a.assert_no_cookie(r, "session")

    def test_assert_no_cookie_fails(self):
        r = self._response(headers={"set-cookie": "session=abc123"})
        with pytest.raises(AssertionError):
            self.a.assert_no_cookie(r, "session")

    # -- New body assertions --

    def test_assert_body_not_contains(self):
        r = self._response(body=b"Hello World")
        self.a.assert_body_not_contains(r, "Secret")

    def test_assert_body_not_contains_fails(self):
        r = self._response(body=b"Hello World")
        with pytest.raises(AssertionError):
            self.a.assert_body_not_contains(r, "World")

    def test_assert_body_empty(self):
        r = self._response(body=b"")
        self.a.assert_body_empty(r)

    def test_assert_body_empty_fails(self):
        r = self._response(body=b"content")
        with pytest.raises(AssertionError):
            self.a.assert_body_empty(r)

    # -- New fault assertions --

    def test_assert_fault_count(self):
        engine = MockFaultEngine()
        f = Fault(code="E", message="x", domain=FaultDomain.SYSTEM, severity=Severity.ERROR)
        engine.emit(f)
        engine.emit(f)
        self.a.assert_fault_count(engine, 2)

    def test_assert_fault_count_fails(self):
        engine = MockFaultEngine()
        with pytest.raises(AssertionError):
            self.a.assert_fault_count(engine, 1)

    def test_assert_fault_severity(self):
        engine = MockFaultEngine()
        f = Fault(code="E", message="x", domain=FaultDomain.SYSTEM, severity=Severity.ERROR)
        engine.emit(f)
        self.a.assert_fault_severity(engine, Severity.ERROR)

    # -- New DI assertions --

    def test_assert_not_registered(self):
        container = TestContainer()
        self.a.assert_not_registered(container, "MissingService")

    def test_assert_not_registered_fails(self):
        from aquilia.di.providers import ValueProvider
        container = TestContainer()
        container.register(ValueProvider(token="Svc", value=1, scope="singleton"))
        with pytest.raises(AssertionError):
            self.a.assert_not_registered(container, "Svc")


# ============================================================================
# 40. Enhanced Utils: make_test_ws_scope, make_upload_file
# ============================================================================


class TestUtilsEnhancements:
    """Tests for make_test_ws_scope and make_upload_file."""

    def test_make_test_ws_scope_defaults(self):
        scope = make_test_ws_scope()
        assert scope["type"] == "websocket"
        assert scope["path"] == "/ws"
        assert scope["scheme"] == "ws"
        assert scope["subprotocols"] == []

    def test_make_test_ws_scope_custom(self):
        scope = make_test_ws_scope(
            path="/chat",
            subprotocols=["graphql-ws"],
            query_string="token=abc",
        )
        assert scope["path"] == "/chat"
        assert scope["subprotocols"] == ["graphql-ws"]
        assert scope["query_string"] == b"token=abc"

    def test_make_test_ws_scope_headers(self):
        scope = make_test_ws_scope(
            headers=[("x-custom", "val")],
        )
        assert scope["headers"][0] == (b"x-custom", b"val")

    def test_make_test_ws_scope_client_server(self):
        scope = make_test_ws_scope(
            client=("10.0.0.1", 5555),
            server=("0.0.0.0", 443),
        )
        assert scope["client"] == ("10.0.0.1", 5555)
        assert scope["server"] == ("0.0.0.0", 443)

    def test_make_upload_file_bytes(self):
        result = make_upload_file("doc.pdf", b"%PDF-1.4", "application/pdf")
        assert result == ("doc.pdf", b"%PDF-1.4", "application/pdf")

    def test_make_upload_file_string(self):
        result = make_upload_file("readme.txt", "Hello World", "text/plain")
        assert result == ("readme.txt", b"Hello World", "text/plain")

    def test_make_upload_file_default_content_type(self):
        result = make_upload_file("data.bin", b"\x00\x01")
        assert result[2] == "application/octet-stream"


# ============================================================================
# 41. Enhanced CLI test command
# ============================================================================


class TestCLITestCommandEnhancements:
    """Tests for enhanced CLI test command: --parallel, --last-failed."""

    def test_run_tests_accepts_parallel(self):
        from aquilia.cli.commands.test import run_tests
        # Should not crash with parallel=True
        code = run_tests(
            paths=["__nonexistent__"],
            parallel=True,
            extra_args=["--co", "-q"],
        )
        assert isinstance(code, int)

    def test_run_tests_accepts_last_failed(self):
        from aquilia.cli.commands.test import run_tests
        code = run_tests(
            paths=["__nonexistent__"],
            last_failed=True,
            extra_args=["--co", "-q"],
        )
        assert isinstance(code, int)

    def test_run_tests_accepts_no_header(self):
        from aquilia.cli.commands.test import run_tests
        code = run_tests(
            paths=["__nonexistent__"],
            no_header=True,
            extra_args=["--co", "-q"],
        )
        assert isinstance(code, int)


# ============================================================================
# 42. Updated package-level imports
# ============================================================================


class TestPackageLevelImports:
    """Verify all public symbols are importable from aquilia.testing."""

    def test_all_exports(self):
        import aquilia.testing as t
        expected = [
            "TestClient", "WebSocketTestClient",
            "AquiliaTestCase", "TransactionTestCase", "LiveServerTestCase", "SimpleTestCase",
            "TestServer", "create_test_server",
            "override_settings", "TestConfig",
            "MockFaultEngine", "CapturedFault",
            "MockEffectRegistry", "MockEffectProvider", "EffectCall",
            "CacheTestMixin", "MockCacheBackend",
            "AuthTestMixin", "TestIdentityFactory", "IdentityBuilder",
            "MailTestMixin", "CapturedMail",
            "TestContainer", "mock_provider", "override_provider",
            "factory_provider", "spy_provider",
            "AquiliaAssertions",
            "aquilia_fixtures",
            "make_test_scope", "make_test_request", "make_test_receive", "make_test_response",
            "make_test_ws_scope", "make_upload_file",
        ]
        for name in expected:
            assert hasattr(t, name), f"Missing export: {name}"

    def test_main_package_exports(self):
        import aquilia
        expected_from_testing = [
            "TestClient", "TestServer", "AquiliaTestCase",
            "SimpleTestCase", "TransactionTestCase", "LiveServerTestCase",
            "override_settings", "create_test_server",
        ]
        for name in expected_from_testing:
            assert hasattr(aquilia, name), f"Missing from aquilia: {name}"
