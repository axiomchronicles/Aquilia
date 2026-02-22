"""
DI-04: Lifecycle hooks — startup/shutdown order, finalizer LIFO.
DI-11: Async provider init/teardown — async_init completes, no hung tasks.
"""

import asyncio
import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.lifecycle import Lifecycle, LifecycleContext, DisposalStrategy


# ── DI-04: Lifecycle hooks ──────────────────────────────────────────

class TestDI04LifecycleHooks:
    """DI-04  risk=medium"""

    async def test_startup_hooks_run_in_priority_order(self):
        lc = Lifecycle()
        order = []

        lc.on_startup(lambda: _append(order, "low"), name="low", priority=1)
        lc.on_startup(lambda: _append(order, "high"), name="high", priority=10)
        lc.on_startup(lambda: _append(order, "mid"), name="mid", priority=5)

        await lc.run_startup_hooks()
        assert order == ["high", "mid", "low"], f"Expected priority order, got {order}"

    async def test_shutdown_hooks_run_in_priority_order(self):
        lc = Lifecycle()
        order = []

        lc.on_shutdown(lambda: _append(order, "low"), name="low", priority=1)
        lc.on_shutdown(lambda: _append(order, "high"), name="high", priority=10)

        await lc.run_shutdown_hooks()
        assert order == ["high", "low"]

    async def test_finalizers_run_lifo(self):
        lc = Lifecycle(disposal_strategy=DisposalStrategy.LIFO)
        order = []

        lc.register_finalizer(lambda: _append(order, "first"))
        lc.register_finalizer(lambda: _append(order, "second"))
        lc.register_finalizer(lambda: _append(order, "third"))

        await lc.run_finalizers()
        assert order == ["third", "second", "first"], f"Expected LIFO, got {order}"

    async def test_finalizers_run_fifo(self):
        lc = Lifecycle(disposal_strategy=DisposalStrategy.FIFO)
        order = []

        lc.register_finalizer(lambda: _append(order, "first"))
        lc.register_finalizer(lambda: _append(order, "second"))

        await lc.run_finalizers()
        assert order == ["first", "second"], f"Expected FIFO, got {order}"

    async def test_finalizers_run_parallel(self):
        lc = Lifecycle(disposal_strategy=DisposalStrategy.PARALLEL)
        results = []

        lc.register_finalizer(lambda: _append(results, "a"))
        lc.register_finalizer(lambda: _append(results, "b"))

        await lc.run_finalizers()
        assert set(results) == {"a", "b"}

    async def test_shutdown_hook_failure_does_not_block_others(self):
        lc = Lifecycle()
        order = []

        async def failing():
            raise RuntimeError("boom")

        lc.on_shutdown(failing, name="fail")
        lc.on_shutdown(lambda: _append(order, "ok"), name="ok", priority=-1)

        # Should not raise; failing hook is swallowed
        await lc.run_shutdown_hooks()
        assert "ok" in order

    async def test_lifecycle_context_manager(self):
        lc = Lifecycle()
        started = []
        stopped = []

        lc.on_startup(lambda: _append(started, True), name="s")
        lc.on_shutdown(lambda: _append(stopped, True), name="s")

        async with LifecycleContext(lc):
            assert started == [True]
            assert stopped == []

        assert stopped == [True]

    async def test_container_lifecycle_integration(self):
        """Verify Container.startup / Container.shutdown drive lifecycle hooks."""
        container = Container(scope="app")
        order = []

        container._lifecycle.on_startup(lambda: _append(order, "start"), name="st")
        container._lifecycle.on_shutdown(lambda: _append(order, "stop"), name="sp")
        container._lifecycle.register_finalizer(lambda: _append(order, "finalize"))

        await container.startup()
        assert "start" in order

        await container.shutdown()
        assert "stop" in order
        assert "finalize" in order

    async def test_clear_removes_all_hooks(self):
        lc = Lifecycle()
        lc.on_startup(lambda: None, name="x")
        lc.on_shutdown(lambda: None, name="y")
        lc.register_finalizer(lambda: None)

        lc.clear()
        assert len(lc._startup_hooks) == 0
        assert len(lc._shutdown_hooks) == 0
        assert len(lc._finalizers) == 0


# ── DI-11: Async provider init/teardown ─────────────────────────────

class TestDI11AsyncProviderInitTeardown:
    """DI-11  risk=high"""

    async def test_async_init_service_completes(self):
        """Provider requiring async init finishes without hung tasks."""
        container = Container(scope="app")

        class AsyncService:
            def __init__(self):
                self.ready = False
                self.closed = False

            async def async_init(self):
                await asyncio.sleep(0.01)
                self.ready = True

            async def shutdown(self):
                self.closed = True

        class _AsyncProv:
            @property
            def meta(self):
                return ProviderMeta(name="async_svc", token="async_svc", scope="singleton")

            async def instantiate(self, ctx=None):
                svc = AsyncService()
                await svc.async_init()
                return svc

            async def shutdown(self):
                pass

        container.register(_AsyncProv())
        svc = await container.resolve_async("async_svc")
        assert svc.ready is True

        await container.shutdown()

    async def test_no_hung_tasks_after_container_shutdown(self):
        """Verify no pending tasks leak from async provider init."""
        container = Container(scope="app")

        async def _factory_fn():
            await asyncio.sleep(0.005)
            return {"status": "ok"}

        class _P:
            @property
            def meta(self):
                return ProviderMeta(name="task_svc", token="task_svc", scope="singleton")

            async def instantiate(self, ctx=None):
                return await _factory_fn()

            async def shutdown(self):
                pass

        container.register(_P())
        result = await container.resolve_async("task_svc")
        assert result["status"] == "ok"

        await container.shutdown()

        # Snapshot active tasks — none should be from our provider
        pending = [t for t in asyncio.all_tasks() if not t.done() and "task_svc" in str(t)]
        assert len(pending) == 0, f"Leaked tasks: {pending}"


# ── helper ──────────────────────────────────────────────────────────

async def _append(lst, val):
    lst.append(val)
