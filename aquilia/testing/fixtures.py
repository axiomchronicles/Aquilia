"""
Aquilia Testing - Pytest Fixtures.

Provides ready-to-use pytest fixtures for common Aquilia testing
patterns.  Import ``aquilia_fixtures`` in your ``conftest.py`` to
register all fixtures at once, or import individual fixtures.

Usage in conftest.py::

    from aquilia.testing.fixtures import aquilia_fixtures
    aquilia_fixtures()  # registers all fixtures

Or use the plugin entry point (automatic via pip install).
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

import pytest

from .client import TestClient, WebSocketTestClient
from .config import TestConfig, override_settings, set_active_config
from .server import TestServer
from .faults import MockFaultEngine
from .effects import MockEffectRegistry, MockEffectProvider
from .cache import MockCacheBackend
from .auth import TestIdentityFactory
from .mail import clear_outbox, get_outbox
from .di import TestContainer
from .utils import make_test_request, make_test_scope


def aquilia_fixtures():
    """
    Register Aquilia pytest fixtures.

    Call this function in your ``conftest.py`` to make all fixtures
    available::

        # conftest.py
        from aquilia.testing.fixtures import aquilia_fixtures
        aquilia_fixtures()

    This is a no-op — the fixtures are registered by the module being
    imported.  The function exists as a documentation anchor and to
    ensure the module's side-effects run.
    """
    pass  # Side-effect of import registers the fixtures below


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def test_config():
    """A blank :class:`TestConfig` for unit tests."""
    from aquilia.config import ConfigLoader
    loader = ConfigLoader()
    loader.config_data = {"debug": True, "runtime": {"mode": "test"}}
    cfg = TestConfig(loader)
    set_active_config(cfg)
    yield cfg


@pytest.fixture
def fault_engine():
    """A :class:`MockFaultEngine` for capturing faults."""
    engine = MockFaultEngine()
    yield engine
    engine.reset()


@pytest.fixture
def effect_registry():
    """A :class:`MockEffectRegistry` for stubbing effects."""
    registry = MockEffectRegistry()
    yield registry
    registry.reset_all()


@pytest.fixture
def cache_backend():
    """A :class:`MockCacheBackend` (in-memory, zero-config)."""
    backend = MockCacheBackend()
    yield backend
    backend.reset()


@pytest.fixture
def di_container():
    """A :class:`TestContainer` with relaxed validation."""
    container = TestContainer()
    yield container
    container.reset()


@pytest.fixture
def identity_factory():
    """A :class:`TestIdentityFactory` for creating test identities."""
    return TestIdentityFactory()


@pytest.fixture
def mail_outbox():
    """
    Clear the mail outbox before the test and return it.

    Use ``assert len(mail_outbox) == 1`` to verify mail was sent.
    """
    clear_outbox()
    yield get_outbox()
    clear_outbox()


@pytest.fixture
def test_request():
    """
    Factory fixture — call with kwargs to create test requests.

    Usage::

        def test_something(test_request):
            req = test_request(method="POST", path="/api", json={"a": 1})
    """
    return make_test_request


@pytest.fixture
def test_scope():
    """
    Factory fixture — call with kwargs to create ASGI scopes.

    Usage::

        def test_scope_stuff(test_scope):
            scope = test_scope(method="GET", path="/health")
    """
    return make_test_scope


# -----------------------------------------------------------------------
# Async fixtures (require pytest-asyncio)
# -----------------------------------------------------------------------

@pytest.fixture
async def test_server():
    """
    Async fixture providing a booted :class:`TestServer`.

    Shuts down automatically after the test.

    Usage::

        async def test_api(test_server):
            client = TestClient(test_server)
            resp = await client.get("/")
            assert resp.status_code == 200
    """
    server = TestServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def test_client(test_server):
    """
    Async fixture providing a :class:`TestClient` wired to a :class:`TestServer`.

    Usage::

        async def test_index(test_client):
            resp = await test_client.get("/")
    """
    return TestClient(test_server)


@pytest.fixture
async def ws_client(test_server):
    """
    Async fixture providing a :class:`WebSocketTestClient` wired to a :class:`TestServer`.

    Usage::

        async def test_websocket(ws_client):
            await ws_client.connect("/ws")
            await ws_client.send_text("hello")
            msg = await ws_client.receive_text()
            await ws_client.close()
    """
    client = WebSocketTestClient(test_server)
    yield client
    if client.is_connected:
        await client.close()


@pytest.fixture
def settings_override():
    """
    Fixture factory for overriding settings.

    Usage::

        def test_debug(settings_override):
            with settings_override(DEBUG=True):
                # config is overridden
                pass
    """
    return override_settings
