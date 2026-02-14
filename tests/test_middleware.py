"""
Test 8: Middleware System (middleware.py)

Tests MiddlewareStack, RequestIdMiddleware, ExceptionMiddleware,
LoggingMiddleware, TimeoutMiddleware, CORSMiddleware, CompressionMiddleware.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aquilia.middleware import (
    MiddlewareStack,
    RequestIdMiddleware,
    ExceptionMiddleware,
    LoggingMiddleware,
    TimeoutMiddleware,
    CORSMiddleware,
    CompressionMiddleware,
)


# ============================================================================
# MiddlewareStack
# ============================================================================

class TestMiddlewareStack:

    def test_init(self):
        stack = MiddlewareStack()
        assert len(stack.middlewares) == 0

    def test_add_middleware(self):
        stack = MiddlewareStack()

        async def mw(request, ctx, next_handler):
            return await next_handler(request, ctx)

        stack.add(mw)
        assert len(stack.middlewares) == 1

    def test_add_with_priority(self):
        stack = MiddlewareStack()

        async def mw1(request, ctx, next_handler):
            return await next_handler(request, ctx)

        async def mw2(request, ctx, next_handler):
            return await next_handler(request, ctx)

        stack.add(mw1, priority=10)
        stack.add(mw2, priority=1)
        assert len(stack.middlewares) == 2

    @pytest.mark.asyncio
    async def test_build_handler_basic(self):
        stack = MiddlewareStack()
        calls = []

        async def mw(request, ctx, next_handler):
            calls.append("mw_before")
            resp = await next_handler(request, ctx)
            calls.append("mw_after")
            return resp

        async def handler(request, ctx):
            calls.append("handler")
            return "ok"

        stack.add(mw)
        composed = stack.build_handler(handler)
        result = await composed(MagicMock(), MagicMock())
        assert result == "ok"
        assert calls == ["mw_before", "handler", "mw_after"]

    @pytest.mark.asyncio
    async def test_build_handler_order(self):
        stack = MiddlewareStack()
        calls = []

        async def mw1(request, ctx, next_handler):
            calls.append("mw1")
            return await next_handler(request, ctx)

        async def mw2(request, ctx, next_handler):
            calls.append("mw2")
            return await next_handler(request, ctx)

        async def handler(request, ctx):
            calls.append("handler")
            return "ok"

        stack.add(mw1, priority=10)
        stack.add(mw2, priority=20)
        composed = stack.build_handler(handler)
        await composed(MagicMock(), MagicMock())
        assert "mw1" in calls
        assert "mw2" in calls
        assert "handler" in calls


# ============================================================================
# RequestIdMiddleware
# ============================================================================

class TestRequestIdMiddleware:

    def test_create(self):
        mw = RequestIdMiddleware()
        assert mw is not None

    @pytest.mark.asyncio
    async def test_adds_request_id(self):
        mw = RequestIdMiddleware()
        request = MagicMock()
        request.state = {}
        request.header = MagicMock(return_value=None)
        ctx = MagicMock()

        async def next_handler(req, c):
            resp = MagicMock()
            resp.headers = {}
            return resp

        resp = await mw(request, ctx, next_handler)
        assert "request_id" in request.state


# ============================================================================
# ExceptionMiddleware
# ============================================================================

class TestExceptionMiddleware:

    def test_create(self):
        mw = ExceptionMiddleware()
        assert mw is not None

    @pytest.mark.asyncio
    async def test_catches_exception(self):
        mw = ExceptionMiddleware()
        request = MagicMock()
        request.state = {}
        ctx = MagicMock()

        async def next_handler(req, c):
            raise ValueError("test error")

        resp = await mw(request, ctx, next_handler)
        assert resp is not None


# ============================================================================
# CORSMiddleware
# ============================================================================

class TestCORSMiddleware:

    def test_create_defaults(self):
        mw = CORSMiddleware()
        assert mw is not None
        assert mw.allow_origins is not None

    def test_create_custom(self):
        mw = CORSMiddleware(
            allow_origins=["http://localhost:3000"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization"],
            allow_credentials=True,
            max_age=3600,
        )
        assert "http://localhost:3000" in mw.allow_origins
        assert mw.allow_credentials is True


# ============================================================================
# TimeoutMiddleware
# ============================================================================

class TestTimeoutMiddleware:

    def test_create(self):
        mw = TimeoutMiddleware(timeout_seconds=5.0)
        assert mw.timeout == 5.0

    @pytest.mark.asyncio
    async def test_passes_through_fast_request(self):
        mw = TimeoutMiddleware(timeout_seconds=5.0)
        request = MagicMock()
        request.state = {}
        ctx = MagicMock()

        async def next_handler(req, c):
            return "fast"

        resp = await mw(request, ctx, next_handler)
        assert resp == "fast"


# ============================================================================
# LoggingMiddleware
# ============================================================================

class TestLoggingMiddleware:

    def test_create(self):
        mw = LoggingMiddleware()
        assert mw is not None

    @pytest.mark.asyncio
    async def test_logs_request(self):
        mw = LoggingMiddleware()
        request = MagicMock()
        request.state = {}
        request.method = "GET"
        request.path = "/test"
        ctx = MagicMock()

        async def next_handler(req, c):
            resp = MagicMock()
            resp.status = 200
            return resp

        resp = await mw(request, ctx, next_handler)
        assert resp is not None
