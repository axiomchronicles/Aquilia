"""
Tests for PR-Fix-C03: LazyProxy run_until_complete crash fix.

Validates that:
- LazyProxy raises a clear RuntimeError inside an async context.
- LazyProxy resolves correctly from synchronous (non-async) code.
"""
import asyncio
import pytest


class FakeContainer:
    """Minimal container mock for LazyProxy testing."""

    async def resolve_async(self, token, tag=None):
        return f"resolved:{token}"


def _make_lazy_proxy():
    """Create a LazyProxy instance via the provider's factory."""
    from aquilia.di.providers import LazyProxyProvider
    from aquilia.di.core import ProviderMeta, ResolveCtx

    provider = LazyProxyProvider(
        token="TestService",
        target_token="TestService",
        name="test_lazy",
    )

    container = FakeContainer()
    proxy_class = provider._create_proxy_class()
    proxy = proxy_class(container, "TestService", None)
    return proxy


@pytest.mark.asyncio
async def test_lazy_proxy_raises_in_async_context():
    """LazyProxy._resolve() must raise RuntimeError inside a running event loop."""
    proxy = _make_lazy_proxy()
    with pytest.raises(RuntimeError, match="Cannot lazily resolve"):
        proxy._resolve()


def test_lazy_proxy_resolves_in_sync_context():
    """LazyProxy._resolve() must work when no event loop is running."""
    proxy = _make_lazy_proxy()
    result = proxy._resolve()
    assert result == "resolved:TestService"


def test_lazy_proxy_getattr_in_sync_context():
    """Attribute access on LazyProxy triggers resolution."""
    proxy = _make_lazy_proxy()
    # str has .upper(), so resolved "resolved:TestService".upper() works
    assert proxy.upper() == "RESOLVED:TESTSERVICE"


@pytest.mark.asyncio
async def test_lazy_proxy_getattr_raises_in_async():
    """Attribute access inside async must give clear error."""
    proxy = _make_lazy_proxy()
    with pytest.raises(RuntimeError, match="Cannot lazily resolve"):
        _ = proxy.upper()
