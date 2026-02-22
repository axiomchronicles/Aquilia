"""
DI Test Harness — introspection, instrumentation, overrides, and failure injection.

Usage:
    harness = DITestHarness(container)
    harness.list_providers()
    harness.count_resolutions("MyToken")
    async with harness.override("MyToken", mock_val):
        ...
    async with harness.inject_failure("MyToken", RuntimeError("boom")):
        ...
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Type, TypeVar

from aquilia.di.core import Container, Provider, ProviderMeta, ResolveCtx

T = TypeVar("T")


class _FailingProvider:
    """Provider that always raises on instantiate."""

    def __init__(self, token: str, error: Exception, scope: str = "singleton"):
        self._token = token
        self._error = error
        self._scope = scope

    @property
    def meta(self) -> ProviderMeta:
        return ProviderMeta(name=f"failing:{self._token}", token=self._token, scope=self._scope)

    async def instantiate(self, ctx: Any = None) -> Any:
        raise self._error

    async def shutdown(self) -> None:
        pass


class _InstrumentedProvider:
    """Wraps an existing provider with timing and call-count tracking."""

    def __init__(self, inner: Provider):
        self._inner = inner
        self.call_count = 0
        self.total_time = 0.0
        self.errors: list[Exception] = []

    @property
    def meta(self) -> ProviderMeta:
        return self._inner.meta

    async def instantiate(self, ctx: Any = None) -> Any:
        self.call_count += 1
        t0 = time.perf_counter()
        try:
            return await self._inner.instantiate(ctx)
        except Exception as exc:
            self.errors.append(exc)
            raise
        finally:
            self.total_time += time.perf_counter() - t0

    async def shutdown(self) -> None:
        await self._inner.shutdown()


class DITestHarness:
    """Full-featured test harness for a DI Container."""

    def __init__(self, container: Container):
        self.container = container
        self._instruments: Dict[str, _InstrumentedProvider] = {}

    # ── Introspection ──────────────────────────────────────────────

    def list_providers(self) -> List[Dict[str, Any]]:
        """Return a list of {key, name, token, scope, tags} for every registered provider."""
        result = []
        for key, prov in self.container._providers.items():
            m = prov.meta
            result.append({"key": key, "name": m.name, "token": m.token, "scope": m.scope, "tags": m.tags})
        return result

    def list_cached(self) -> Dict[str, Any]:
        """Return {cache_key: instance} for all cached instances."""
        return dict(self.container._cache)

    def provider_count(self) -> int:
        return len(self.container._providers)

    # ── Instrumentation ────────────────────────────────────────────

    def instrument(self, token: str, *, tag: Optional[str] = None) -> _InstrumentedProvider:
        """Replace provider with an instrumented wrapper; returns the wrapper."""
        cache_key = self.container._make_cache_key(token, tag)
        original = self.container._providers.get(cache_key)
        if original is None:
            raise KeyError(f"No provider for {token}")
        instr = _InstrumentedProvider(original)
        self.container._providers[cache_key] = instr
        self.container._cache.pop(cache_key, None)
        self._instruments[cache_key] = instr
        return instr

    def count_resolutions(self, token: str, *, tag: Optional[str] = None) -> int:
        cache_key = self.container._make_cache_key(token, tag)
        instr = self._instruments.get(cache_key)
        return instr.call_count if instr else 0

    # ── Overrides ──────────────────────────────────────────────────

    @asynccontextmanager
    async def override(self, token: Type | str, mock_value: Any, *, tag: Optional[str] = None):
        """Temporarily replace a provider; restore on exit."""
        from aquilia.testing.di import _MockProvider

        token_key = self.container._token_to_key(token)
        cache_key = self.container._make_cache_key(token_key, tag)
        original_prov = self.container._providers.get(cache_key)
        original_cached = self.container._cache.get(cache_key)

        mock = _MockProvider(value=mock_value, token=token, scope="singleton")
        self.container._providers[cache_key] = mock
        self.container._cache.pop(cache_key, None)
        try:
            yield mock
        finally:
            if original_prov is not None:
                self.container._providers[cache_key] = original_prov
            else:
                self.container._providers.pop(cache_key, None)
            if original_cached is not None:
                self.container._cache[cache_key] = original_cached
            else:
                self.container._cache.pop(cache_key, None)

    # ── Failure injection ──────────────────────────────────────────

    @asynccontextmanager
    async def inject_failure(self, token: str, error: Exception, *, tag: Optional[str] = None):
        """Replace provider with one that always raises *error*; restore on exit."""
        cache_key = self.container._make_cache_key(token, tag)
        original_prov = self.container._providers.get(cache_key)
        original_cached = self.container._cache.get(cache_key)

        failing = _FailingProvider(token, error)
        self.container._providers[cache_key] = failing
        self.container._cache.pop(cache_key, None)
        try:
            yield
        finally:
            if original_prov is not None:
                self.container._providers[cache_key] = original_prov
            else:
                self.container._providers.pop(cache_key, None)
            if original_cached is not None:
                self.container._cache[cache_key] = original_cached
            else:
                self.container._cache.pop(cache_key, None)

    # ── Cleanup ────────────────────────────────────────────────────

    def restore_all(self):
        """Remove any instrumented wrappers (best-effort)."""
        for key, instr in self._instruments.items():
            self.container._providers[key] = instr._inner
            self.container._cache.pop(key, None)
        self._instruments.clear()
