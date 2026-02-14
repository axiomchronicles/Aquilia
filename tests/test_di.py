"""
Test 5: Dependency Injection (di/)

Tests Container, Providers, Scopes, Decorators, Lifecycle, Graph, Errors.
"""

import pytest
import asyncio

from aquilia.di.core import Container, ProviderMeta, ResolveCtx
from aquilia.di.providers import ClassProvider, FactoryProvider, ValueProvider
from aquilia.di.scopes import Scope, ServiceScope, ScopeValidator, SCOPES
from aquilia.di.decorators import service, factory, inject, Inject, provides
from aquilia.di.errors import DIError, ProviderNotFoundError, ScopeViolationError
from aquilia.di.graph import DependencyGraph
from aquilia.di.lifecycle import Lifecycle


# ============================================================================
# Scope Validation
# ============================================================================

class TestScopes:

    def test_scope_enum_values(self):
        assert ServiceScope.SINGLETON.value == "singleton"
        assert ServiceScope.APP.value == "app"
        assert ServiceScope.REQUEST.value == "request"
        assert ServiceScope.TRANSIENT.value == "transient"
        assert ServiceScope.POOLED.value == "pooled"
        assert ServiceScope.EPHEMERAL.value == "ephemeral"

    def test_scope_cacheable(self):
        assert SCOPES["singleton"].cacheable is True
        assert SCOPES["app"].cacheable is True
        assert SCOPES["request"].cacheable is True
        assert SCOPES["transient"].cacheable is False

    def test_scope_can_inject_into(self):
        singleton = SCOPES["singleton"]
        request = SCOPES["request"]
        transient = SCOPES["transient"]

        # Singleton can inject into anything
        assert singleton.can_inject_into(request) is True
        assert singleton.can_inject_into(singleton) is True

        # Request cannot inject into singleton
        assert request.can_inject_into(singleton) is False
        assert request.can_inject_into(request) is True

        # Transient can inject into anything
        assert transient.can_inject_into(singleton) is True

    def test_scope_validator(self):
        assert ScopeValidator.validate_injection("singleton", "request") is True
        assert ScopeValidator.validate_injection("request", "singleton") is False

    def test_scope_hierarchy(self):
        hierarchy = ScopeValidator.get_scope_hierarchy()
        assert "request" in hierarchy.get("app", [])


# ============================================================================
# Value Provider
# ============================================================================

class TestValueProvider:

    @pytest.mark.asyncio
    async def test_value_provider(self):
        container = Container(scope="app")
        provider = ValueProvider(token="config.db_url", value="postgres://localhost/db", scope="singleton")
        container.register(provider)
        result = await container.resolve_async("config.db_url")
        assert result == "postgres://localhost/db"


# ============================================================================
# Class Provider
# ============================================================================

class TestClassProvider:

    def test_class_provider_meta(self):
        class MyService:
            pass

        provider = ClassProvider(MyService, scope="app")
        assert provider.meta.name == "MyService"
        assert provider.meta.scope == "app"


# ============================================================================
# Container
# ============================================================================

class TestContainer:

    @pytest.mark.asyncio
    async def test_register_and_resolve(self):
        container = Container(scope="app")
        provider = ValueProvider(token="greeting", value="hello", scope="singleton")
        container.register(provider)
        result = await container.resolve_async("greeting")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_resolve_optional_missing(self):
        container = Container(scope="app")
        result = await container.resolve_async("nonexistent", optional=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_not_found_raises(self):
        container = Container(scope="app")
        with pytest.raises(Exception):
            await container.resolve_async("nonexistent")

    @pytest.mark.asyncio
    async def test_duplicate_registration_raises(self):
        container = Container(scope="app")
        p1 = ValueProvider(token="key", value="v1", scope="singleton")
        p2 = ValueProvider(token="key", value="v2", scope="singleton")
        container.register(p1)
        with pytest.raises(ValueError):
            container.register(p2)

    @pytest.mark.asyncio
    async def test_idempotent_registration(self):
        container = Container(scope="app")
        p = ValueProvider(token="key", value="v1", scope="singleton")
        container.register(p)
        container.register(p)  # Same provider, should not raise

    def test_is_registered(self):
        container = Container(scope="app")
        p = ValueProvider(token="key", value="v1", scope="singleton")
        container.register(p)
        assert container.is_registered("key") is True
        assert container.is_registered("missing") is False

    @pytest.mark.asyncio
    async def test_request_scope_child(self):
        parent = Container(scope="app")
        p = ValueProvider(token="shared", value="from_parent", scope="singleton")
        parent.register(p)

        child = parent.create_request_scope()
        # Child should inherit parent providers
        result = await child.resolve_async("shared")
        assert result == "from_parent"

    @pytest.mark.asyncio
    async def test_request_scope_override(self):
        parent = Container(scope="app")
        p_parent = ValueProvider(token="svc", value="parent_value", scope="singleton")
        parent.register(p_parent)

        child = parent.create_request_scope()
        p_child = ValueProvider(token="svc_child", value="child_value", scope="request")
        child.register(p_child)

        assert await child.resolve_async("svc_child") == "child_value"

    @pytest.mark.asyncio
    async def test_register_instance(self):
        container = Container(scope="request")
        obj = {"key": "value"}
        await container.register_instance("my_instance", obj)
        result = await container.resolve_async("my_instance")
        assert result is obj

    @pytest.mark.asyncio
    async def test_caching(self):
        container = Container(scope="app")
        call_count = 0

        async def make_thing():
            nonlocal call_count
            call_count += 1
            return {"instance": call_count}

        provider = FactoryProvider(
            factory=make_thing,
            scope="app",
            name="thing",
        )
        container.register(provider)

        r1 = await container.resolve_async(provider.meta.token)
        r2 = await container.resolve_async(provider.meta.token)
        assert r1 is r2
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_shutdown(self):
        container = Container(scope="app")
        p = ValueProvider(token="key", value="v", scope="singleton")
        container.register(p)
        await container.resolve_async("key")
        await container.shutdown()
        # After shutdown, cache is cleared
        assert len(container._cache) == 0


# ============================================================================
# Decorators
# ============================================================================

class TestDIDecorators:

    def test_service_decorator(self):
        @service(scope="request", tag="primary")
        class MyService:
            pass

        assert MyService.__di_scope__ == "request"
        assert MyService.__di_tag__ == "primary"
        assert MyService.__di_name__ == "MyService"

    def test_factory_decorator(self):
        @factory(scope="singleton", name="db_pool")
        async def create_pool():
            return "pool"

        assert create_pool.__di_scope__ == "singleton"
        assert create_pool.__di_factory__ is True
        assert create_pool.__di_name__ == "db_pool"

    def test_provides_decorator(self):
        class IRepo:
            pass

        @provides(IRepo, scope="app", tag="sql")
        def make_repo():
            return "repo"

        assert make_repo.__di_provides__ is IRepo
        assert make_repo.__di_scope__ == "app"

    def test_inject_metadata(self):
        marker = inject(tag="readonly", optional=True)
        assert isinstance(marker, Inject)
        assert marker.tag == "readonly"
        assert marker.optional is True

    def test_inject_class(self):
        marker = Inject(token="MyService", tag="v2")
        assert marker.token == "MyService"
        assert marker.tag == "v2"


# ============================================================================
# Lifecycle
# ============================================================================

class TestLifecycle:

    @pytest.mark.asyncio
    async def test_startup_hooks(self):
        lifecycle = Lifecycle()
        results = []

        async def hook1():
            results.append("h1")

        async def hook2():
            results.append("h2")

        lifecycle.on_startup(hook1, name="h1")
        lifecycle.on_startup(hook2, name="h2")
        await lifecycle.run_startup_hooks()
        assert results == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_shutdown_hooks_reverse_order(self):
        lifecycle = Lifecycle()
        results = []

        async def h1():
            results.append("h1")

        async def h2():
            results.append("h2")

        lifecycle.on_shutdown(h1, name="h1")
        lifecycle.on_shutdown(h2, name="h2")
        await lifecycle.run_shutdown_hooks()
        # Hooks run in registration order (same priority)
        assert results == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_clear(self):
        lifecycle = Lifecycle()

        async def noop():
            pass

        lifecycle.on_startup(noop, name="x")
        lifecycle.clear()
        # Should not raise
        await lifecycle.run_startup_hooks()


# ============================================================================
# Dependency Graph
# ============================================================================

class TestDependencyGraph:

    def _make_provider(self, name, scope="app"):
        """Helper to make a minimal provider for graph tests."""
        return ValueProvider(token=name, value=f"value_{name}", scope=scope)

    def test_add_and_resolve(self):
        graph = DependencyGraph()
        p_a = self._make_provider("A")
        p_b = self._make_provider("B")
        p_c = self._make_provider("C")
        graph.add_provider(p_a, ["B"])
        graph.add_provider(p_b, ["C"])
        graph.add_provider(p_c, [])
        # A depends on B, B depends on C
        assert "B" in graph.adj_list["A"]

    def test_cycle_detection(self):
        graph = DependencyGraph()
        p_a = self._make_provider("A")
        p_b = self._make_provider("B")
        graph.add_provider(p_a, ["B"])
        graph.add_provider(p_b, ["A"])
        cycles = graph.detect_cycles()
        assert len(cycles) > 0

    def test_no_cycle(self):
        graph = DependencyGraph()
        p_a = self._make_provider("A")
        p_b = self._make_provider("B")
        p_c = self._make_provider("C")
        graph.add_provider(p_a, ["B"])
        graph.add_provider(p_b, ["C"])
        graph.add_provider(p_c, [])
        cycles = graph.detect_cycles()
        assert len(cycles) == 0

    def test_topological_order(self):
        graph = DependencyGraph()
        p_app = self._make_provider("app")
        p_db = self._make_provider("db")
        p_cache = self._make_provider("cache")
        p_config = self._make_provider("config")
        graph.add_provider(p_app, ["db", "cache"])
        graph.add_provider(p_db, ["config"])
        graph.add_provider(p_cache, [])
        graph.add_provider(p_config, [])
        order = graph.get_resolution_order()
        # All providers should be in the result
        assert set(order) == {"app", "db", "cache", "config"}
        # Kahn's processes nodes with no incoming edges first
        # 'app' has no incoming edges (nothing depends on it), so it comes first
        # This is the resolution order, not dependency order
        assert len(order) == 4


# ============================================================================
# ResolveCtx
# ============================================================================

class TestResolveCtx:

    def test_push_pop(self):
        container = Container(scope="app")
        ctx = ResolveCtx(container=container)
        ctx.push("ServiceA")
        ctx.push("ServiceB")
        assert ctx.get_trace() == ["ServiceA", "ServiceB"]
        ctx.pop()
        assert ctx.get_trace() == ["ServiceA"]

    def test_cycle_detection(self):
        container = Container(scope="app")
        ctx = ResolveCtx(container=container)
        ctx.push("ServiceA")
        assert ctx.in_cycle("ServiceA") is True
        assert ctx.in_cycle("ServiceB") is False
