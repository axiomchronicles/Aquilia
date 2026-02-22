"""
DI-05: Factory provider errors — throwing factory → descriptive error, no half-init.
DI-06: Missing binding — resolve unregistered token → ProviderNotFoundError.
DI-07: Circular dependency handling — cycle detection or lazy proxy resolution.
"""

import pytest
from aquilia.di.core import Container, ProviderMeta, ResolveCtx
from aquilia.di.providers import FactoryProvider, ClassProvider
from aquilia.di.graph import DependencyGraph
from aquilia.di.errors import (
    ProviderNotFoundError,
    DependencyCycleError,
    CircularDependencyError,
    DIError,
)


# ── DI-05: Factory provider errors ──────────────────────────────────

class TestDI05FactoryProviderErrors:
    """DI-05  risk=high"""

    async def test_factory_that_raises_propagates_error(self):
        container = Container(scope="app")

        class _BadFactory:
            @property
            def meta(self):
                return ProviderMeta(name="bad", token="bad_svc", scope="singleton")

            async def instantiate(self, ctx=None):
                raise ValueError("DB connection refused")

            async def shutdown(self):
                pass

        container.register(_BadFactory())

        with pytest.raises(ValueError, match="DB connection refused"):
            await container.resolve_async("bad_svc")

    async def test_failed_factory_does_not_cache_partial_instance(self):
        container = Container(scope="app")
        call_count = {"n": 0}

        class _Flaky:
            @property
            def meta(self):
                return ProviderMeta(name="flaky", token="flaky_svc", scope="singleton")

            async def instantiate(self, ctx=None):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise RuntimeError("first call fails")
                return {"ok": True}

            async def shutdown(self):
                pass

        container.register(_Flaky())

        # First call fails
        with pytest.raises(RuntimeError):
            await container.resolve_async("flaky_svc")

        # Instance should NOT be cached from the failed attempt
        assert "flaky_svc" not in container._cache

        # Second call succeeds
        result = await container.resolve_async("flaky_svc")
        assert result == {"ok": True}

    async def test_container_recovers_after_factory_error(self):
        container = Container(scope="app")

        # Register a good provider alongside a bad one
        from aquilia.di.providers import ValueProvider
        container.register(ValueProvider(value="good", token="good_svc", scope="singleton"))

        class _Bad:
            @property
            def meta(self):
                return ProviderMeta(name="bad", token="bad_svc2", scope="singleton")

            async def instantiate(self, ctx=None):
                raise TypeError("bad init")

            async def shutdown(self):
                pass

        container.register(_Bad())

        with pytest.raises(TypeError):
            await container.resolve_async("bad_svc2")

        # Good provider should still work fine
        assert await container.resolve_async("good_svc") == "good"


# ── DI-06: Missing binding ──────────────────────────────────────────

class TestDI06MissingBinding:
    """DI-06  risk=medium"""

    async def test_resolve_missing_token_raises(self):
        container = Container(scope="app")

        with pytest.raises(ProviderNotFoundError) as exc_info:
            await container.resolve_async("nonexistent_token")

        assert "nonexistent_token" in str(exc_info.value)

    async def test_resolve_missing_with_optional_returns_none(self):
        container = Container(scope="app")

        result = await container.resolve_async("missing", optional=True)
        assert result is None

    async def test_missing_provider_suggests_candidates(self):
        container = Container(scope="app")
        from aquilia.di.providers import ValueProvider

        container.register(ValueProvider(value="x", token="user_service", scope="singleton"))

        with pytest.raises(ProviderNotFoundError) as exc_info:
            await container.resolve_async("user_service_v2")

        # Should mention the similar token in candidates
        error_msg = str(exc_info.value)
        assert "user_service" in error_msg

    async def test_is_registered_returns_false_for_missing(self):
        container = Container(scope="app")
        assert container.is_registered("anything") is False

    async def test_is_registered_returns_true_for_existing(self):
        container = Container(scope="app")
        from aquilia.di.providers import ValueProvider
        container.register(ValueProvider(value=1, token="exists", scope="singleton"))
        assert container.is_registered("exists") is True


# ── DI-07: Circular dependency handling ─────────────────────────────

class TestDI07CircularDependency:
    """DI-07  risk=high"""

    def test_graph_detects_simple_cycle(self):
        graph = DependencyGraph()

        class _P:
            def __init__(self, token):
                self._meta = ProviderMeta(name=token, token=token, scope="singleton")

            @property
            def meta(self):
                return self._meta

        graph.add_provider(_P("A"), ["B"])
        graph.add_provider(_P("B"), ["A"])

        cycles = graph.detect_cycles()
        assert len(cycles) >= 1, "Should detect A→B→A cycle"

        # Flatten cycle
        flat = [token for cycle in cycles for token in cycle]
        assert "A" in flat
        assert "B" in flat

    def test_graph_detects_three_node_cycle(self):
        graph = DependencyGraph()

        class _P:
            def __init__(self, token):
                self._meta = ProviderMeta(name=token, token=token, scope="singleton")

            @property
            def meta(self):
                return self._meta

        graph.add_provider(_P("X"), ["Y"])
        graph.add_provider(_P("Y"), ["Z"])
        graph.add_provider(_P("Z"), ["X"])

        cycles = graph.detect_cycles()
        assert len(cycles) >= 1

    def test_no_false_cycle_in_acyclic_graph(self):
        graph = DependencyGraph()

        class _P:
            def __init__(self, token):
                self._meta = ProviderMeta(name=token, token=token, scope="singleton")

            @property
            def meta(self):
                return self._meta

        graph.add_provider(_P("root"), ["mid"])
        graph.add_provider(_P("mid"), ["leaf"])
        graph.add_provider(_P("leaf"), [])

        cycles = graph.detect_cycles()
        assert len(cycles) == 0

    def test_topological_sort_raises_on_cycle(self):
        graph = DependencyGraph()

        class _P:
            def __init__(self, token):
                self._meta = ProviderMeta(name=token, token=token, scope="singleton")

            @property
            def meta(self):
                return self._meta

        graph.add_provider(_P("A"), ["B"])
        graph.add_provider(_P("B"), ["A"])

        with pytest.raises(DependencyCycleError):
            graph.get_resolution_order()

    def test_self_loop_detected(self):
        graph = DependencyGraph()

        class _P:
            def __init__(self, token):
                self._meta = ProviderMeta(name=token, token=token, scope="singleton")

            @property
            def meta(self):
                return self._meta

        graph.add_provider(_P("self_ref"), ["self_ref"])

        cycles = graph.detect_cycles()
        assert len(cycles) >= 1

    async def test_resolve_ctx_detects_runtime_cycle(self):
        """ResolveCtx.in_cycle() catches re-entrant resolution."""
        container = Container(scope="app")
        ctx = ResolveCtx(container)
        ctx.push("token_A")
        ctx.push("token_B")

        assert ctx.in_cycle("token_A") is True
        assert ctx.in_cycle("token_B") is True
        assert ctx.in_cycle("token_C") is False

        ctx.pop()
        assert ctx.in_cycle("token_B") is False
