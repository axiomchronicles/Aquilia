"""
DI-09: Concurrency stress on DI resolution — 500 concurrent resolves,
correct scopes, no data races, no crashes.
"""

import asyncio
import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ValueProvider


class _ThreadSafeCounter:
    """Non-atomic counter to detect data races."""
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1


class TestDI09ConcurrencyStress:
    """DI-09  risk=high"""

    async def test_500_concurrent_singleton_resolves_same_instance(self):
        container = Container(scope="app")
        sentinel = object()
        container.register(ValueProvider(value=sentinel, token="shared", scope="singleton"))

        results = await asyncio.gather(
            *[container.resolve_async("shared") for _ in range(500)]
        )
        assert all(r is sentinel for r in results), "Singleton diverged under concurrency"

    async def test_concurrent_request_scopes_isolated(self):
        parent = Container(scope="app")
        counter = _ThreadSafeCounter()

        class _ReqProv:
            @property
            def meta(self):
                return ProviderMeta(name="req", token="req_item", scope="request")

            async def instantiate(self, ctx=None):
                counter.increment()
                return {"n": counter.value}

            async def shutdown(self):
                pass

        parent.register(_ReqProv())

        async def _request():
            child = parent.create_request_scope()
            val = await child.resolve_async("req_item")
            await child.shutdown()
            return val

        results = await asyncio.gather(*[_request() for _ in range(200)])
        numbers = [r["n"] for r in results]
        assert len(set(numbers)) == 200, "Request-scoped instances must be unique"

    async def test_mixed_singleton_and_transient_under_load(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="shared", token="shared", scope="singleton"))

        call_count = {"n": 0}

        class _TransProv:
            @property
            def meta(self):
                return ProviderMeta(name="trans", token="trans", scope="transient")

            async def instantiate(self, ctx=None):
                call_count["n"] += 1
                return {"call": call_count["n"]}

            async def shutdown(self):
                pass

        container.register(_TransProv())

        async def _resolve_both():
            s = await container.resolve_async("shared")
            t = await container.resolve_async("trans")
            return s, t

        results = await asyncio.gather(*[_resolve_both() for _ in range(300)])

        singletons = [r[0] for r in results]
        transients = [r[1] for r in results]

        assert all(s == "shared" for s in singletons)
        assert len(set(id(t) for t in transients)) > 1, "Transient should create multiple instances"

    async def test_concurrent_register_and_resolve(self):
        """Register new providers while resolving existing ones concurrently."""
        from aquilia.testing.di import TestContainer

        container = TestContainer(scope="app")
        container.register_value("base", "base_val")

        async def _resolver():
            for _ in range(50):
                await container.resolve_async("base")
                await asyncio.sleep(0)

        async def _registrar():
            for i in range(50):
                container.register_value(f"dyn_{i}", f"val_{i}")
                await asyncio.sleep(0)

        await asyncio.gather(_resolver(), _registrar())

        # All dynamic should be resolvable
        for i in range(50):
            container._cache.pop(f"dyn_{i}", None)
            val = await container.resolve_async(f"dyn_{i}")
            assert val == f"val_{i}"

    async def test_concurrent_shutdown_does_not_crash(self):
        """Shutting down multiple request containers concurrently."""
        parent = Container(scope="app")
        parent.register(ValueProvider(value="x", token="x", scope="request"))

        children = [parent.create_request_scope() for _ in range(100)]
        for c in children:
            await c.resolve_async("x")

        await asyncio.gather(*[c.shutdown() for c in children])
        # No exception = success
