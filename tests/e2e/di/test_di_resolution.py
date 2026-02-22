"""
DI-01: Provider resolution — token A → concrete impl X, methods work.
DI-02: Singleton vs transient — same id vs different id.
DI-03: Request-scoped providers — unique per request scope, cleaned after.
"""

import asyncio
import pytest
from aquilia.di.core import Container, ProviderMeta, ResolveCtx
from aquilia.di.providers import ValueProvider, ClassProvider, FactoryProvider
from aquilia.testing.di import TestContainer, mock_provider


# ── helpers ──────────────────────────────────────────────────────────

class SimpleService:
    counter = 0
    def __init__(self):
        SimpleService.counter += 1
        self.instance_id = SimpleService.counter

    def greet(self) -> str:
        return f"hello from instance {self.instance_id}"


class RequestScopedService:
    def __init__(self):
        self.calls = 0

    def tick(self):
        self.calls += 1
        return self.calls


# ── DI-01: Provider resolution ──────────────────────────────────────

class TestDI01ProviderResolution:
    """DI-01  risk=low"""

    async def test_value_provider_resolves_to_correct_instance(self, app_container):
        sentinel = object()
        prov = ValueProvider(value=sentinel, token="sentinel_token", scope="singleton")
        app_container.register(prov)

        result = await app_container.resolve_async("sentinel_token")
        assert result is sentinel

    async def test_value_provider_method_works(self, app_container, dummy_repo):
        prov = ValueProvider(value=dummy_repo, token="repo", scope="singleton")
        app_container.register(prov)

        repo = await app_container.resolve_async("repo")
        data = repo.get(42)
        assert data == {"id": 42, "name": "item"}

    async def test_class_provider_creates_instance(self):
        container = Container(scope="app")
        prov = ClassProvider(cls=SimpleService, scope="singleton")
        container.register(prov)

        token = prov.meta.token
        instance = await container.resolve_async(token)
        assert isinstance(instance, SimpleService)
        assert instance.greet().startswith("hello from instance")

    async def test_mock_provider_resolves(self, app_container):
        mp = mock_provider("my_mock", value={"key": "value"})
        app_container.register(mp)

        result = await app_container.resolve_async("my_mock")
        assert result == {"key": "value"}


# ── DI-02: Singleton vs transient ────────────────────────────────────

class TestDI02SingletonVsTransient:
    """DI-02  risk=medium"""

    async def test_singleton_returns_same_instance(self):
        container = Container(scope="app")
        prov = ValueProvider(value=SimpleService(), token="svc", scope="singleton")
        container.register(prov)

        a = await container.resolve_async("svc")
        b = await container.resolve_async("svc")
        assert a is b, "Singleton must return identical instance"

    async def test_transient_returns_different_instances(self):
        container = Container(scope="app")
        call_count = 0

        class TransientThing:
            def __init__(self):
                nonlocal call_count
                call_count += 1
                self.n = call_count

        async def _factory(ctx=None):
            return TransientThing()

        from aquilia.di.core import ProviderMeta as PM

        class _TransientProv:
            @property
            def meta(self):
                return PM(name="transient_thing", token="transient_thing", scope="transient")

            async def instantiate(self, ctx=None):
                return TransientThing()

            async def shutdown(self):
                pass

        container.register(_TransientProv())

        a = await container.resolve_async("transient_thing")
        b = await container.resolve_async("transient_thing")
        assert a is not b, "Transient must create new instance each time"
        assert a.n != b.n

    async def test_singleton_same_across_request_scopes(self):
        parent = Container(scope="app")
        prov = ValueProvider(value=SimpleService(), token="shared", scope="singleton")
        parent.register(prov)

        child1 = parent.create_request_scope()
        child2 = parent.create_request_scope()

        a = await child1.resolve_async("shared")
        b = await child2.resolve_async("shared")
        assert a is b, "Singleton must be shared across request scopes"

        await child1.shutdown()
        await child2.shutdown()


# ── DI-03: Request-scoped providers ──────────────────────────────────

class TestDI03RequestScoped:
    """DI-03  risk=high"""

    async def test_request_scope_unique_per_request(self):
        parent = Container(scope="app")

        class _ReqProv:
            @property
            def meta(self):
                return ProviderMeta(name="req_svc", token="req_svc", scope="request")

            async def instantiate(self, ctx=None):
                return RequestScopedService()

            async def shutdown(self):
                pass

        parent.register(_ReqProv())

        child1 = parent.create_request_scope()
        child2 = parent.create_request_scope()

        svc1 = await child1.resolve_async("req_svc")
        svc2 = await child2.resolve_async("req_svc")

        assert svc1 is not svc2, "Request-scoped must be unique per scope"

        # Same within one request
        svc1_again = await child1.resolve_async("req_svc")
        assert svc1 is svc1_again, "Request-scoped must cache within a request"

        await child1.shutdown()
        await child2.shutdown()

    async def test_request_scope_cleaned_on_shutdown(self):
        parent = Container(scope="app")
        prov = ValueProvider(value=RequestScopedService(), token="rsc", scope="request")
        parent.register(prov)

        child = parent.create_request_scope()
        svc = await child.resolve_async("rsc")
        assert svc is not None

        await child.shutdown()
        # Cache is cleared after shutdown
        assert len(child._cache) == 0

    async def test_concurrent_request_scopes_isolated(self):
        parent = Container(scope="app")

        counter = {"n": 0}

        class _CountingProv:
            @property
            def meta(self):
                return ProviderMeta(name="counting", token="counting", scope="request")

            async def instantiate(self, ctx=None):
                counter["n"] += 1
                return {"request_number": counter["n"]}

            async def shutdown(self):
                pass

        parent.register(_CountingProv())

        async def _simulate_request():
            child = parent.create_request_scope()
            val = await child.resolve_async("counting")
            await asyncio.sleep(0.01)  # simulate work
            await child.shutdown()
            return val

        results = await asyncio.gather(*[_simulate_request() for _ in range(10)])
        request_numbers = [r["request_number"] for r in results]
        # All unique
        assert len(set(request_numbers)) == 10
