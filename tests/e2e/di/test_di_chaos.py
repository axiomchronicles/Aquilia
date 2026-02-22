"""
DI Chaos tests — factory intermittent failures, provider init failures,
partial-init detection, concurrent failure injection.
"""

import asyncio
import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ValueProvider
from aquilia.testing.di import TestContainer
from tests.e2e.di.harness import DITestHarness


class TestDIChaosFactoryIntermittentFailure:
    """Factory throws intermittently under concurrent resolution."""

    async def test_intermittent_factory_errors_handled(self):
        container = Container(scope="app")
        counter = {"n": 0}

        class _Intermittent:
            @property
            def meta(self):
                return ProviderMeta(name="flaky", token="flaky", scope="transient")

            async def instantiate(self, ctx=None):
                counter["n"] += 1
                if counter["n"] % 3 == 0:
                    raise RuntimeError(f"Intermittent failure #{counter['n']}")
                return {"ok": True, "call": counter["n"]}

            async def shutdown(self):
                pass

        container.register(_Intermittent())

        successes = 0
        failures = 0

        async def _try_resolve():
            nonlocal successes, failures
            try:
                await container.resolve_async("flaky")
                successes += 1
            except RuntimeError:
                failures += 1

        await asyncio.gather(*[_try_resolve() for _ in range(100)])

        assert successes > 0, "Some calls should succeed"
        assert failures > 0, "Some calls should fail (intermittent)"
        # No crash = test passes


class TestDIChaosProviderInitFailure:
    """Provider init failure leaves no half-open state."""

    async def test_failed_init_cleans_up(self):
        container = Container(scope="app")

        class _Resource:
            opened = []
            closed = []

            @classmethod
            def reset(cls):
                cls.opened.clear()
                cls.closed.clear()

        _Resource.reset()

        class _LeakyProv:
            @property
            def meta(self):
                return ProviderMeta(name="leaky", token="leaky", scope="singleton")

            async def instantiate(self, ctx=None):
                _Resource.opened.append("conn")
                raise ConnectionError("DB down during init")

            async def shutdown(self):
                pass

        container.register(_LeakyProv())

        with pytest.raises(ConnectionError):
            await container.resolve_async("leaky")

        # The instance should NOT be cached
        assert "leaky" not in container._cache

    async def test_container_usable_after_init_crash(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="ok", token="healthy", scope="singleton"))

        class _Crasher:
            @property
            def meta(self):
                return ProviderMeta(name="crash", token="crash", scope="singleton")

            async def instantiate(self, ctx=None):
                raise SystemError("catastrophic")

            async def shutdown(self):
                pass

        container.register(_Crasher())

        # Crash on one provider
        with pytest.raises(SystemError):
            await container.resolve_async("crash")

        # Other provider still works
        result = await container.resolve_async("healthy")
        assert result == "ok"


class TestDIChaosHarnessFailureInjection:
    """Use DI harness to inject failures and verify recovery."""

    async def test_inject_failure_then_restore(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="real", token="svc", scope="singleton"))
        harness = DITestHarness(container)

        # Inject failure
        async with harness.inject_failure("svc", RuntimeError("injected")):
            with pytest.raises(RuntimeError, match="injected"):
                await container.resolve_async("svc")

        # After exit, original restored
        val = await container.resolve_async("svc")
        assert val == "real"

    async def test_concurrent_resolve_during_failure_injection(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="ok", token="target", scope="transient"))
        harness = DITestHarness(container)

        errors = []
        successes = []

        async def _resolver():
            try:
                r = await container.resolve_async("target")
                successes.append(r)
            except RuntimeError:
                errors.append(1)

        # During failure window
        async with harness.inject_failure("target", RuntimeError("down")):
            await asyncio.gather(*[_resolver() for _ in range(50)])

        assert len(errors) == 50, "All should fail during injection"

        # After restore
        val = await container.resolve_async("target")
        assert val == "ok"
