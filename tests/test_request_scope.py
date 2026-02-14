"""
Tests for PR-Fix-C01: Request-scope DI isolation.

Validates that each request gets its own DI child container,
preventing cross-request state leakage.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class FakeContainer:
    """Minimal container stub for testing scope isolation."""

    def __init__(self, scope="app", parent=None):
        self._scope = scope
        self._parent = parent
        self._local: dict = {}
        self._shutdown_called = False

    def create_request_scope(self):
        child = FakeContainer(scope="request", parent=self)
        return child

    async def shutdown(self):
        self._shutdown_called = True

    def set(self, key, value):
        self._local[key] = value

    def get(self, key, default=None):
        return self._local.get(key, default)


class FakeRuntime:
    def __init__(self, container):
        self.di_containers = {"default": container}


# ---------------------------------------------------------------------------
# Tests for the ASGI-level RequestScopeMiddleware
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_scope_creates_child_container():
    """Each request MUST get a child container, not the app container."""
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware

    app_container = FakeContainer(scope="app")
    runtime = FakeRuntime(app_container)

    captured_containers = []

    async def fake_app(scope, receive, send):
        captured_containers.append(scope["state"]["di_container"])

    mw = RequestScopeMiddleware(fake_app, runtime)
    scope = {"type": "http", "app_name": "default"}
    await mw(scope, AsyncMock(), AsyncMock())

    assert len(captured_containers) == 1
    req_container = captured_containers[0]
    # Must be a DIFFERENT object from the app container
    assert req_container is not app_container
    assert req_container._scope == "request"
    assert req_container._parent is app_container


@pytest.mark.asyncio
async def test_request_scope_child_is_shutdown_after_request():
    """Request-scoped container must be shut down after the request."""
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware

    app_container = FakeContainer(scope="app")
    runtime = FakeRuntime(app_container)
    captured = []

    async def fake_app(scope, receive, send):
        captured.append(scope["state"]["di_container"])

    mw = RequestScopeMiddleware(fake_app, runtime)
    scope = {"type": "http", "app_name": "default"}
    await mw(scope, AsyncMock(), AsyncMock())

    assert captured[0]._shutdown_called is True
    # App container must NOT be shut down
    assert app_container._shutdown_called is False


@pytest.mark.asyncio
async def test_concurrent_requests_get_isolated_containers():
    """Two concurrent requests must NOT share the same container."""
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware

    app_container = FakeContainer(scope="app")
    runtime = FakeRuntime(app_container)
    captured = []
    barrier = asyncio.Barrier(2)

    async def fake_app(scope, receive, send):
        container = scope["state"]["di_container"]
        container.set("identity", scope.get("test_user"))
        await barrier.wait()  # force both requests to overlap
        captured.append((scope.get("test_user"), container.get("identity")))

    mw = RequestScopeMiddleware(fake_app, runtime)

    async def make_request(user):
        scope = {"type": "http", "app_name": "default", "test_user": user}
        await mw(scope, AsyncMock(), AsyncMock())

    await asyncio.gather(make_request("alice"), make_request("bob"))

    # Each request must see only its own identity
    for user, identity in captured:
        assert user == identity, f"User {user} saw identity {identity} — cross-request leak!"


@pytest.mark.asyncio
async def test_non_http_scope_passes_through():
    """Non-HTTP scopes (lifespan, ws) should pass through without DI."""
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware

    app_container = FakeContainer(scope="app")
    runtime = FakeRuntime(app_container)
    called = False

    async def fake_app(scope, receive, send):
        nonlocal called
        called = True

    mw = RequestScopeMiddleware(fake_app, runtime)
    scope = {"type": "lifespan"}
    await mw(scope, AsyncMock(), AsyncMock())
    assert called


@pytest.mark.asyncio
async def test_no_container_passes_through():
    """If no DI container registered for the app, pass through."""
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware

    runtime = FakeRuntime(None)
    runtime.di_containers = {}  # empty
    called = False

    async def fake_app(scope, receive, send):
        nonlocal called
        called = True

    mw = RequestScopeMiddleware(fake_app, runtime)
    scope = {"type": "http", "app_name": "unknown"}
    await mw(scope, AsyncMock(), AsyncMock())
    assert called


# ---------------------------------------------------------------------------
# Tests for SimplifiedRequestScopeMiddleware
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simplified_middleware_creates_child():
    """SimplifiedRequestScopeMiddleware must also create a child container."""
    from aquilia.middleware_ext.request_scope import SimplifiedRequestScopeMiddleware

    app_container = FakeContainer(scope="app")
    runtime = FakeRuntime(app_container)

    class FakeRequest:
        class state:
            app_name = "default"
            di_container = None
            app_container = None
            runtime = None

    request = FakeRequest()

    async def call_next(req):
        return "ok"

    mw = SimplifiedRequestScopeMiddleware(runtime)
    result = await mw(request, call_next)

    assert result == "ok"
    assert request.state.di_container is not app_container
