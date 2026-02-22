"""
DI conftest.py — shared fixtures for DI integration tests.

Provides clean Container / TestContainer instances and helper builders
for dummy services used by DI-01 through DI-13.
"""

import pytest
import pytest_asyncio

from aquilia.di.core import Container, ProviderMeta, ResolveCtx
from aquilia.di.providers import (
    ClassProvider,
    FactoryProvider,
    ValueProvider,
)
from aquilia.di.lifecycle import Lifecycle, LifecycleContext
from aquilia.di.graph import DependencyGraph
from aquilia.di.errors import (
    ProviderNotFoundError,
    DependencyCycleError,
    CircularDependencyError,
)
from aquilia.testing.di import TestContainer, mock_provider, override_provider

from tests.e2e.di.harness import DITestHarness


# ---------------------------------------------------------------------------
# Simple service stubs used across DI tests
# ---------------------------------------------------------------------------

class DummyRepo:
    """Simulates a repository service."""
    def __init__(self):
        self.name = "DummyRepo"

    def get(self, item_id: int) -> dict:
        return {"id": item_id, "name": "item"}


class DummyCache:
    """Simulates a cache service."""
    def __init__(self):
        self.store: dict = {}
        self.name = "DummyCache"

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value):
        self.store[key] = value


class DummyMailer:
    """Simulates a mail service."""
    def __init__(self):
        self.sent: list = []
        self.name = "DummyMailer"

    def send(self, to: str, body: str):
        self.sent.append({"to": to, "body": body})


class TrackedService:
    """Service that tracks init/shutdown for lifecycle tests."""
    instances: list = []  # class-level tracker

    def __init__(self):
        self.initialized = False
        self.shut_down = False
        TrackedService.instances.append(self)

    async def on_startup(self):
        self.initialized = True

    async def on_shutdown(self):
        self.shut_down = True

    @classmethod
    def reset(cls):
        cls.instances.clear()


class AsyncInitService:
    """Service requiring async initialization."""
    def __init__(self):
        self.ready = False
        self.closed = False

    async def async_init(self):
        self.ready = True

    async def shutdown(self):
        self.closed = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_container():
    """Provide a clean app-scoped DI Container."""
    container = Container(scope="app")
    yield container


@pytest_asyncio.fixture
async def app_container_with_shutdown():
    """Provide an app container that is shut down after the test."""
    container = Container(scope="app")
    yield container
    await container.shutdown()


@pytest.fixture
def test_container():
    """Provide a TestContainer (relaxed duplicate registration)."""
    return TestContainer()


@pytest.fixture
def harness(app_container):
    """Provide a DITestHarness wrapping the app_container."""
    return DITestHarness(app_container)


@pytest.fixture
def dummy_repo():
    return DummyRepo()


@pytest.fixture
def dummy_cache():
    return DummyCache()


@pytest.fixture
def dummy_mailer():
    return DummyMailer()
