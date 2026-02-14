"""
Test 14: Lifecycle System (lifecycle.py)

Tests LifecycleCoordinator, LifecyclePhase, LifecycleEvent,
LifecycleManager, LifecycleError.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Any, Optional, List

from aquilia.lifecycle import (
    LifecycleCoordinator,
    LifecyclePhase,
    LifecycleEvent,
    LifecycleError,
    LifecycleManager,
    create_lifecycle_coordinator,
)


# ============================================================================
# Helpers
# ============================================================================

@dataclass
class FakeAppContext:
    name: str
    on_startup: Any = None
    on_shutdown: Any = None
    config_namespace: Optional[dict] = None


class FakeRuntimeMeta:
    def __init__(self, app_contexts=None):
        self.app_contexts = app_contexts or []


class FakeRuntime:
    def __init__(self, app_contexts=None):
        self.meta = FakeRuntimeMeta(app_contexts)
        self.di_containers = {}


# ============================================================================
# LifecyclePhase
# ============================================================================

class TestLifecyclePhase:

    def test_values(self):
        assert LifecyclePhase.INIT.value == "init"
        assert LifecyclePhase.STARTING.value == "starting"
        assert LifecyclePhase.READY.value == "ready"
        assert LifecyclePhase.STOPPING.value == "stopping"
        assert LifecyclePhase.STOPPED.value == "stopped"
        assert LifecyclePhase.ERROR.value == "error"


# ============================================================================
# LifecycleEvent
# ============================================================================

class TestLifecycleEvent:

    def test_create(self):
        event = LifecycleEvent(phase=LifecyclePhase.INIT)
        assert event.phase == LifecyclePhase.INIT
        assert event.app_name is None
        assert event.error is None

    def test_create_with_app(self):
        event = LifecycleEvent(
            phase=LifecyclePhase.STARTING,
            app_name="users",
            message="Starting users",
        )
        assert event.app_name == "users"
        assert event.message == "Starting users"


# ============================================================================
# LifecycleCoordinator
# ============================================================================

class TestLifecycleCoordinator:

    def test_init(self):
        runtime = FakeRuntime()
        coord = LifecycleCoordinator(runtime)
        assert coord.phase == LifecyclePhase.INIT
        assert coord.started_apps == []

    @pytest.mark.asyncio
    async def test_startup_no_apps(self):
        runtime = FakeRuntime([])
        coord = LifecycleCoordinator(runtime)
        await coord.startup()
        assert coord.phase == LifecyclePhase.READY

    @pytest.mark.asyncio
    async def test_startup_with_app(self):
        started = []

        async def on_start(config_ns, container):
            started.append("app1")

        ctx = FakeAppContext(name="app1", on_startup=on_start)
        runtime = FakeRuntime([ctx])
        coord = LifecycleCoordinator(runtime)
        await coord.startup()
        assert "app1" in started
        assert coord.phase == LifecyclePhase.READY
        assert "app1" in coord.started_apps

    @pytest.mark.asyncio
    async def test_shutdown(self):
        stopped = []

        async def on_stop(config_ns, container):
            stopped.append("app1")

        ctx = FakeAppContext(name="app1", on_shutdown=on_stop)
        runtime = FakeRuntime([ctx])
        coord = LifecycleCoordinator(runtime)
        coord.started_apps = ["app1"]
        coord.phase = LifecyclePhase.READY
        await coord.shutdown()
        assert "app1" in stopped
        assert coord.phase == LifecyclePhase.STOPPED

    @pytest.mark.asyncio
    async def test_startup_twice_raises(self):
        runtime = FakeRuntime([])
        coord = LifecycleCoordinator(runtime)
        await coord.startup()
        with pytest.raises(LifecycleError, match="Cannot start"):
            await coord.startup()

    @pytest.mark.asyncio
    async def test_on_event(self):
        events = []

        def handler(event):
            events.append(event.phase)

        runtime = FakeRuntime([])
        coord = LifecycleCoordinator(runtime)
        coord.on_event(handler)
        await coord.startup()
        assert LifecyclePhase.STARTING in events
        assert LifecyclePhase.READY in events

    def test_get_status(self):
        runtime = FakeRuntime([FakeAppContext(name="a")])
        coord = LifecycleCoordinator(runtime)
        status = coord.get_status()
        assert status["phase"] == "init"
        assert status["total_apps"] == 1

    @pytest.mark.asyncio
    async def test_startup_failure_rolls_back(self):
        stopped = []

        async def on_start_ok(config_ns, container):
            pass

        async def on_stop_ok(config_ns, container):
            stopped.append("ok_app")

        async def on_start_fail(config_ns, container):
            raise RuntimeError("startup failed")

        ok_ctx = FakeAppContext(name="ok_app", on_startup=on_start_ok, on_shutdown=on_stop_ok)
        bad_ctx = FakeAppContext(name="bad_app", on_startup=on_start_fail)
        runtime = FakeRuntime([ok_ctx, bad_ctx])
        coord = LifecycleCoordinator(runtime)

        with pytest.raises(LifecycleError, match="Startup failed"):
            await coord.startup()
        # ok_app should be rolled back
        assert "ok_app" in stopped


# ============================================================================
# LifecycleManager (context manager)
# ============================================================================

class TestLifecycleManager:

    @pytest.mark.asyncio
    async def test_context_manager(self):
        runtime = FakeRuntime([])
        manager = LifecycleManager(runtime)
        async with manager as coord:
            assert coord.phase == LifecyclePhase.READY
        assert coord.phase == LifecyclePhase.STOPPED


# ============================================================================
# Factory Function
# ============================================================================

class TestCreateLifecycleCoordinator:

    def test_factory(self):
        runtime = FakeRuntime()
        coord = create_lifecycle_coordinator(runtime)
        assert isinstance(coord, LifecycleCoordinator)
