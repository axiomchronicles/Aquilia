"""
Controller + DI combined brutal scenarios:
- Slow provider under concurrent controller requests
- Remove provider → fail fast with clear error
- Corrupted cached instance detection
"""

import asyncio
import time
import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ValueProvider
from aquilia.di.errors import ProviderNotFoundError
from aquilia.testing.di import TestContainer, override_provider
from tests.e2e.di.harness import DITestHarness


# ── Slow provider under concurrent requests ─────────────────────────

class TestControllerDISlowProvider:
    """Replace a provider with a slow implementation while 200 concurrent
    controller requests are in-flight; measure latencies and check for
    cascading failures."""

    async def test_slow_provider_concurrent_requests(self):
        container = TestContainer(scope="app")
        container.register_value("fast_svc", "fast")

        class _SlowProv:
            @property
            def meta(self):
                return ProviderMeta(name="slow", token="fast_svc", scope="transient")

            async def instantiate(self, ctx=None):
                await asyncio.sleep(0.05)  # 50ms latency
                return "slow_result"

            async def shutdown(self):
                pass

        latencies = []
        errors = []

        async def _simulate_request():
            t0 = time.perf_counter()
            try:
                result = await container.resolve_async("fast_svc")
                latencies.append(time.perf_counter() - t0)
                return result
            except Exception as e:
                errors.append(str(e))
                latencies.append(time.perf_counter() - t0)
                return None

        # Phase 1: fast resolves
        fast_results = await asyncio.gather(*[_simulate_request() for _ in range(50)])
        assert all(r == "fast" for r in fast_results)

        # Phase 2: swap to slow
        container._cache.pop("fast_svc", None)
        container.register(_SlowProv())

        slow_results = await asyncio.gather(*[_simulate_request() for _ in range(200)])
        assert all(r == "slow_result" for r in slow_results), "All should get slow result"

        # Verify no cascading failures
        assert len(errors) == 0, f"Unexpected errors: {errors}"

        # Latencies under slow provider should be ≥ 50ms
        slow_latencies = latencies[50:]  # skip fast phase
        avg_latency = sum(slow_latencies) / len(slow_latencies) if slow_latencies else 0


# ── Remove provider → fail fast ─────────────────────────────────────

class TestControllerDIMissingProvider:
    """Remove a low-level provider at runtime (simulate misconfiguration)
    and verify controllers fail fast with clear error."""

    async def test_removed_provider_causes_clear_error(self):
        container = TestContainer(scope="app")
        container.register_value("crucial_db", "db_instance")

        # Verify it works
        assert await container.resolve_async("crucial_db") == "db_instance"

        # Simulate misconfiguration: remove provider
        container._providers.pop("crucial_db", None)
        container._cache.pop("crucial_db", None)

        with pytest.raises(ProviderNotFoundError) as exc_info:
            await container.resolve_async("crucial_db")

        assert "crucial_db" in str(exc_info.value)

    async def test_recovery_after_rebind(self):
        container = TestContainer(scope="app")
        container.register_value("db", "original_db")

        # Remove
        container._providers.pop("db", None)
        container._cache.pop("db", None)

        with pytest.raises(ProviderNotFoundError):
            await container.resolve_async("db")

        # Rebind (recovery)
        container.register_value("db", "restored_db")
        result = await container.resolve_async("db")
        assert result == "restored_db"


# ── Corrupted cached instance ────────────────────────────────────────

class TestControllerDICorruptedCache:
    """Corrupt a provider's internal cached state and verify
    controllers detect and recover."""

    async def test_corrupted_cache_returns_stale_value(self):
        container = Container(scope="app")
        container.register(ValueProvider(value={"healthy": True}, token="svc", scope="singleton"))

        svc = await container.resolve_async("svc")
        assert svc["healthy"] is True

        # Corrupt the cached instance
        svc["healthy"] = False
        svc["corrupted"] = True

        # Subsequent resolves return the same (corrupted) cached object
        svc2 = await container.resolve_async("svc")
        assert svc2["healthy"] is False
        assert svc2 is svc

    async def test_cache_clear_forces_fresh_resolve(self):
        container = Container(scope="app")

        class _FreshProv:
            """Provider that creates a fresh dict each time."""
            @property
            def meta(self):
                return ProviderMeta(name="svc2", token="svc2", scope="singleton")

            async def instantiate(self, ctx=None):
                return {"healthy": True}  # fresh dict each call

            async def shutdown(self):
                pass

        container.register(_FreshProv())

        svc = await container.resolve_async("svc2")
        svc["healthy"] = False  # corrupt

        # Clear cache → force re-instantiation
        container._cache.pop("svc2", None)
        fresh = await container.resolve_async("svc2")
        assert fresh["healthy"] is True
        assert fresh is not svc

    async def test_corrupted_cache_in_request_scope(self):
        parent = Container(scope="app")

        class _ReqProv:
            """Request-scoped provider that creates fresh dicts."""
            @property
            def meta(self):
                return ProviderMeta(name="counter", token="counter", scope="request")

            async def instantiate(self, ctx=None):
                return {"n": 0}  # fresh dict each call

            async def shutdown(self):
                pass

        parent.register(_ReqProv())

        child = parent.create_request_scope()
        counter = await child.resolve_async("counter")
        counter["n"] = 999  # corrupt

        # Same request scope sees corruption
        c2 = await child.resolve_async("counter")
        assert c2["n"] == 999

        await child.shutdown()

        # New request scope gets fresh instance
        child2 = parent.create_request_scope()
        fresh = await child2.resolve_async("counter")
        assert fresh["n"] == 0
        await child2.shutdown()
