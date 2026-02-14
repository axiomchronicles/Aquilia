"""
Test: ASGI Middleware Integration

Verifies that the middleware chain is executed for ALL requests —
including those that do NOT match any controller route.

This is critical for middleware like StaticMiddleware, CORSMiddleware
(preflight), rate limiting, etc. that must be able to intercept and
respond to requests independently of the controller router.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field as dc_field
from typing import Optional, Dict, Any, List

import pytest

from aquilia.request import Request
from aquilia.response import Response
from aquilia.middleware import MiddlewareStack
from aquilia.asgi import ASGIAdapter
from aquilia.controller.router import ControllerRouter


# ── Helpers ──────────────────────────────────────────────────────────────────


def make_scope(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[List[tuple]] = None,
    scheme: str = "http",
) -> dict:
    """Build a minimal ASGI HTTP scope."""
    raw_headers = []
    if headers:
        for name, value in headers:
            raw_headers.append(
                (
                    name.encode("latin-1") if isinstance(name, str) else name,
                    value.encode("latin-1") if isinstance(value, str) else value,
                )
            )
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": (
            query_string.encode("utf-8")
            if isinstance(query_string, str)
            else query_string
        ),
        "headers": raw_headers,
        "scheme": scheme,
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 12345),
        "root_path": "",
    }


def make_receive(body: bytes = b""):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return receive


class ResponseCapture:
    """Captures what gets sent through ASGI ``send``."""

    def __init__(self):
        self.messages: list = []
        self.status: Optional[int] = None
        self.headers: Dict[str, str] = {}
        self.body = b""

    async def __call__(self, message: dict):
        self.messages.append(message)
        if message["type"] == "http.response.start":
            self.status = message["status"]
            for name, value in message.get("headers", []):
                key = name.decode("latin-1") if isinstance(name, bytes) else name
                val = value.decode("latin-1") if isinstance(value, bytes) else value
                self.headers[key.lower()] = val
        elif message["type"] == "http.response.body":
            self.body += message.get("body", b"")


def _make_adapter(middleware_stack=None, controller_router=None, server=None):
    """Build a minimal ASGIAdapter wired for testing."""
    router = controller_router or ControllerRouter()
    stack = middleware_stack or MiddlewareStack()
    engine = MagicMock()
    adapter = ASGIAdapter(
        controller_router=router,
        controller_engine=engine,
        middleware_stack=stack,
        server=server,
    )
    return adapter


# ═════════════════════════════════════════════════════════════════════════════
#  Core fix: middleware chain runs even when no controller route matches
# ═════════════════════════════════════════════════════════════════════════════


class TestMiddlewareRunsWithoutRouteMatch:
    """Middleware must execute even when no controller route is matched."""

    @pytest.mark.asyncio
    async def test_middleware_called_on_unmatched_path(self):
        """A custom middleware should be invoked for a path with no controller."""
        calls = []

        async def tracking_middleware(request, ctx, next_handler):
            calls.append("middleware_before")
            resp = await next_handler(request, ctx)
            calls.append("middleware_after")
            return resp

        stack = MiddlewareStack()
        stack.add(tracking_middleware, priority=50, name="tracker")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/no-such-route")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        # The middleware must have been invoked
        assert "middleware_before" in calls
        assert "middleware_after" in calls
        # The final response should be 404 (no controller)
        assert send.status == 404

    @pytest.mark.asyncio
    async def test_middleware_can_intercept_and_respond(self):
        """A middleware should be able to short-circuit and return its own
        response for paths that don't match any controller (e.g. static files)."""

        async def interceptor(request, ctx, next_handler):
            if request.path == "/intercepted":
                return Response(b"INTERCEPTED", status=200)
            return await next_handler(request, ctx)

        stack = MiddlewareStack()
        stack.add(interceptor, priority=5, name="interceptor")

        adapter = _make_adapter(middleware_stack=stack)

        # Request the intercepted path (no controller for it)
        scope = make_scope(path="/intercepted")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 200
        assert send.body == b"INTERCEPTED"

    @pytest.mark.asyncio
    async def test_unintercepted_path_returns_404(self):
        """When no middleware intercepts and no controller matches → 404."""
        stack = MiddlewareStack()
        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/totally-unknown")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 404


# ═════════════════════════════════════════════════════════════════════════════
#  Static middleware integration via ASGI pipeline
# ═════════════════════════════════════════════════════════════════════════════


class TestStaticMiddlewareViaPipeline:
    """Verify that StaticMiddleware actually serves files through the
    full ASGI adapter pipeline."""

    @pytest.fixture
    def static_dir(self, tmp_path):
        css_dir = tmp_path / "css"
        css_dir.mkdir()
        (css_dir / "app.css").write_text("body { color: red; }")
        (tmp_path / "hello.txt").write_text("hello world")
        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "chat.js").write_text("console.log('chat');")
        return tmp_path

    @pytest.mark.asyncio
    async def test_static_file_served_via_asgi(self, static_dir):
        """GET /static/css/app.css should return the CSS file content."""
        from aquilia.middleware_ext.static import StaticMiddleware

        static_mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )

        stack = MiddlewareStack()
        stack.add(static_mw, priority=6, name="static_files")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/static/css/app.css")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 200
        assert b"body { color: red; }" in send.body
        assert "text/css" in send.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_static_js_served_via_asgi(self, static_dir):
        """GET /static/js/chat.js should return JS content."""
        from aquilia.middleware_ext.static import StaticMiddleware

        static_mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )

        stack = MiddlewareStack()
        stack.add(static_mw, priority=6, name="static_files")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/static/js/chat.js")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 200
        assert b"console.log('chat');" in send.body

    @pytest.mark.asyncio
    async def test_non_static_path_falls_through_to_404(self, static_dir):
        """GET /api/users should NOT be served by static middleware."""
        from aquilia.middleware_ext.static import StaticMiddleware

        static_mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )

        stack = MiddlewareStack()
        stack.add(static_mw, priority=6, name="static_files")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/api/users")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 404

    @pytest.mark.asyncio
    async def test_missing_static_file_returns_404(self, static_dir):
        """GET /static/no-such-file.txt should 404."""
        from aquilia.middleware_ext.static import StaticMiddleware

        static_mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )

        stack = MiddlewareStack()
        stack.add(static_mw, priority=6, name="static_files")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/static/no-such-file.txt")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 404

    @pytest.mark.asyncio
    async def test_post_to_static_falls_through(self, static_dir):
        """POST /static/hello.txt should fall through (static only handles GET/HEAD)."""
        from aquilia.middleware_ext.static import StaticMiddleware

        static_mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )

        stack = MiddlewareStack()
        stack.add(static_mw, priority=6, name="static_files")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(method="POST", path="/static/hello.txt")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert send.status == 404


# ═════════════════════════════════════════════════════════════════════════════
#  Multiple middleware co-operation (e.g. static + CORS on same request)
# ═════════════════════════════════════════════════════════════════════════════


class TestMultipleMiddlewareOrder:
    """Middleware should compose correctly even for non-controller paths."""

    @pytest.mark.asyncio
    async def test_cors_preflight_without_controller(self):
        """OPTIONS /api/foo should be handled by CORS middleware
        even if no controller is registered for that path."""
        from aquilia.middleware import CORSMiddleware

        cors = CORSMiddleware(allow_origins=["*"])

        stack = MiddlewareStack()
        stack.add(cors, priority=11, name="cors")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(
            method="OPTIONS",
            path="/api/foo",
            headers=[("origin", "http://localhost:3000")],
        )
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        # CORS middleware should handle preflight → 204
        assert send.status == 204
        assert "access-control-allow-origin" in send.headers

    @pytest.mark.asyncio
    async def test_middleware_chain_ordering_preserved(self):
        """Middleware should execute in priority order."""
        execution_order = []

        async def mw_first(request, ctx, next_handler):
            execution_order.append("first")
            return await next_handler(request, ctx)

        async def mw_second(request, ctx, next_handler):
            execution_order.append("second")
            return await next_handler(request, ctx)

        async def mw_third(request, ctx, next_handler):
            execution_order.append("third")
            return await next_handler(request, ctx)

        stack = MiddlewareStack()
        stack.add(mw_third, priority=30, name="third")
        stack.add(mw_first, priority=10, name="first")
        stack.add(mw_second, priority=20, name="second")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/any-path")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert execution_order == ["first", "second", "third"]


# ═════════════════════════════════════════════════════════════════════════════
#  Request state is populated even without a controller match
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestStateSafety:
    """Ensure request.state is safely initialised for non-controller paths."""

    @pytest.mark.asyncio
    async def test_request_state_has_defaults_on_no_match(self):
        """request.state should have app_name, route_pattern, path_params
        even when no controller matched."""
        captured_state = {}

        async def state_inspector(request, ctx, next_handler):
            captured_state.update(request.state)
            return await next_handler(request, ctx)

        stack = MiddlewareStack()
        stack.add(state_inspector, priority=5, name="inspector")

        adapter = _make_adapter(middleware_stack=stack)

        scope = make_scope(path="/no-controller")
        send = ResponseCapture()
        await adapter(scope, make_receive(), send)

        assert "app_name" in captured_state
        assert "route_pattern" in captured_state
        assert "path_params" in captured_state
        assert captured_state["app_name"] is None
        assert captured_state["path_params"] == {}
