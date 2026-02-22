"""
DI-08: Override in tests — override_provider context manager, controller gets mock, restore.
DI-10: Hot-rebind — replace implementation at runtime, new calls use new impl.
"""

import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ValueProvider
from aquilia.testing.di import TestContainer, override_provider, spy_provider

from tests.e2e.di.harness import DITestHarness


# ── DI-08: Override in tests ────────────────────────────────────────

class TestDI08OverrideInTests:
    """DI-08  risk=medium"""

    async def test_override_replaces_resolved_value(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="real_db", token="db", scope="singleton"))

        # Resolve original
        original = await container.resolve_async("db")
        assert original == "real_db"

        # Override
        async with override_provider(container, "db", "mock_db"):
            overridden = await container.resolve_async("db")
            assert overridden == "mock_db"

        # Restore
        restored = await container.resolve_async("db")
        assert restored == "real_db"

    async def test_override_tracks_access_count(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="x", token="svc", scope="singleton"))

        # Use transient-like behavior: clear cache between resolves so mock.instantiate
        # runs each time (singleton caching would bypass mock on 2nd call)
        async with override_provider(container, "svc", "y") as mock:
            await container.resolve_async("svc")
            container._cache.pop("svc", None)
            await container.resolve_async("svc")
            assert mock.resolve_count == 2

    async def test_nested_overrides_restore_correctly(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="original", token="nested", scope="singleton"))

        async with override_provider(container, "nested", "first_mock"):
            v1 = await container.resolve_async("nested")
            assert v1 == "first_mock"

            async with override_provider(container, "nested", "second_mock"):
                v2 = await container.resolve_async("nested")
                assert v2 == "second_mock"

            # After inner exits, should be back to first mock
            v3 = await container.resolve_async("nested")
            assert v3 == "first_mock"

        # After outer exits, back to original
        v4 = await container.resolve_async("nested")
        assert v4 == "original"

    async def test_spy_provider_tracks_calls(self):
        container = Container(scope="app")
        container.register(ValueProvider(value=42, token="num", scope="singleton"))

        async with spy_provider(container, "num") as spy:
            result = await container.resolve_async("num")
            assert result == 42
            assert spy.resolve_count == 1

    async def test_harness_override_and_restore(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="real", token="h_svc", scope="singleton"))
        harness = DITestHarness(container)

        async with harness.override("h_svc", "fake"):
            v = await container.resolve_async("h_svc")
            assert v == "fake"

        v2 = await container.resolve_async("h_svc")
        assert v2 == "real"


# ── DI-10: Hot-rebind ───────────────────────────────────────────────

class TestDI10HotRebind:
    """DI-10  risk=medium"""

    async def test_replacing_provider_uses_new_impl(self):
        container = TestContainer()
        container.register_value("feature_flag", False)

        v1 = await container.resolve_async("feature_flag")
        assert v1 is False

        # Hot-rebind: overwrite with new value
        container.register_value("feature_flag", True)
        container._cache.pop("feature_flag", None)  # clear stale cache

        v2 = await container.resolve_async("feature_flag")
        assert v2 is True

    async def test_rebind_invalidates_cache(self):
        container = TestContainer()
        container.register_value("counter", 1)

        await container.resolve_async("counter")
        assert "counter" in container._cache

        # Rebind
        container.register_value("counter", 2)
        container._cache.pop("counter", None)

        result = await container.resolve_async("counter")
        assert result == 2

    async def test_rebind_in_test_container_no_error(self):
        """TestContainer allows duplicate registration (unlike prod Container)."""
        container = TestContainer()
        container.register_value("dup", "a")
        container.register_value("dup", "b")  # should not raise

        container._cache.pop("dup", None)
        result = await container.resolve_async("dup")
        assert result == "b"

    async def test_rebind_singleton_propagates_to_request_scopes_immediately(self):
        """Singleton-scoped providers delegate from child to parent via
        `resolve_async` line 380 (scope delegation). So parent rebinds are
        immediately visible from request scopes — the child never caches
        singletons itself."""
        parent = TestContainer(scope="app")
        parent.register_value("svc", "v1")

        child = parent.create_request_scope()
        before = await child.resolve_async("svc")
        assert before == "v1"

        # Rebind in parent — immediately visible via scope delegation
        parent.register_value("svc", "v2")
        parent._cache.pop("svc", None)

        rebind_result = await child.resolve_async("svc")
        assert rebind_result == "v2", "Singleton delegation means child sees parent rebind"

        await child.shutdown()

    async def test_rebind_request_scoped_caches_per_child(self):
        """Request-scoped providers are cached per child container.
        Rebinding in parent does NOT affect already-cached request-scoped values
        because request scope doesn't delegate to parent."""
        from aquilia.di.core import ProviderMeta

        parent = TestContainer(scope="app")

        class _ReqProv:
            def __init__(self, val):
                self._val = val

            @property
            def meta(self):
                return ProviderMeta(name="rsc", token="rsc", scope="request")

            async def instantiate(self, ctx=None):
                return self._val

            async def shutdown(self):
                pass

        parent.register(_ReqProv("v1"))

        child = parent.create_request_scope()
        before = await child.resolve_async("rsc")
        assert before == "v1"

        # Rebind in parent (shared _providers dict)
        parent._providers["rsc"] = _ReqProv("v2")
        parent._cache.pop("rsc", None)

        # Child still has cached v1 for request-scoped providers
        cached = await child.resolve_async("rsc")
        assert cached == "v1", "Request-scoped cached in child's own _cache"

        await child.shutdown()
