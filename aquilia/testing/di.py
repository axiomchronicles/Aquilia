"""
Aquilia Testing - DI Container Testing Utilities.

Provides :class:`TestContainer`, :func:`mock_provider`,
:func:`override_provider`, and :func:`spy_provider` for seamless
DI mocking in tests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from aquilia.di.core import Container, Provider, ProviderMeta
from aquilia.di.providers import ValueProvider

T = TypeVar("T")


class _MockProvider:
    """
    Simple mock provider wrapping a value with call tracking.
    """

    def __init__(
        self,
        value: Any,
        token: Type | str,
        scope: str = "singleton",
    ):
        self._value = value
        self._token = token
        self._scope = scope
        self.resolve_count = 0

    @property
    def meta(self) -> ProviderMeta:
        token_str = (
            self._token.__name__
            if isinstance(self._token, type)
            else str(self._token)
        )
        return ProviderMeta(
            name=f"mock:{token_str}",
            token=token_str,
            scope=self._scope,
        )

    async def instantiate(self, ctx: Any = None) -> Any:
        self.resolve_count += 1
        return self._value

    async def shutdown(self) -> None:
        pass


class _FactoryProvider:
    """Provider that calls a factory function on each resolve."""

    def __init__(
        self,
        factory: Callable[..., Any],
        token: Type | str,
        scope: str = "transient",
    ):
        self._factory = factory
        self._token = token
        self._scope = scope
        self.resolve_count = 0

    @property
    def meta(self) -> ProviderMeta:
        token_str = (
            self._token.__name__
            if isinstance(self._token, type)
            else str(self._token)
        )
        return ProviderMeta(
            name=f"factory:{token_str}",
            token=token_str,
            scope=self._scope,
        )

    async def instantiate(self, ctx: Any = None) -> Any:
        self.resolve_count += 1
        result = self._factory()
        if hasattr(result, "__await__"):
            return await result
        return result

    async def shutdown(self) -> None:
        pass


class _SpyProvider:
    """
    Provider that wraps a real provider, delegates to it, and tracks calls.
    """

    def __init__(self, real_provider: Any):
        self._real = real_provider
        self.resolve_count = 0
        self.resolved_values: list[Any] = []

    @property
    def meta(self) -> ProviderMeta:
        return self._real.meta

    async def instantiate(self, ctx: Any = None) -> Any:
        self.resolve_count += 1
        result = await self._real.instantiate(ctx)
        self.resolved_values.append(result)
        return result

    async def shutdown(self) -> None:
        if hasattr(self._real, "shutdown"):
            await self._real.shutdown()


def mock_provider(
    token: Type[T] | str,
    value: T,
    scope: str = "singleton",
) -> _MockProvider:
    """
    Create a mock DI provider that always returns *value*.

    Usage::

        container.register(mock_provider(UserRepo, FakeUserRepo()))
    """
    return _MockProvider(value=value, token=token, scope=scope)


def factory_provider(
    token: Type[T] | str,
    factory: Callable[..., T],
    scope: str = "transient",
) -> _FactoryProvider:
    """
    Create a factory DI provider that calls *factory* on each resolve.

    Usage::

        container.register(factory_provider(UserRepo, lambda: FakeUserRepo()))
    """
    return _FactoryProvider(factory=factory, token=token, scope=scope)


@asynccontextmanager
async def override_provider(
    container: Container,
    token: Type[T] | str,
    mock_value: T,
    *,
    tag: Optional[str] = None,
):
    """
    Temporarily override a provider in a container.

    Restores the original provider on exit.

    Usage::

        async with override_provider(container, UserRepo, FakeRepo()):
            user = await container.resolve_async(UserRepo)
            assert isinstance(user, FakeRepo)
    """
    token_key = container._token_to_key(token)
    cache_key = container._make_cache_key(token_key, tag)

    # Save originals
    original_provider = container._providers.get(cache_key)
    original_cached = container._cache.get(cache_key)

    # Install mock
    mock = _MockProvider(value=mock_value, token=token)
    container._providers[cache_key] = mock
    container._cache.pop(cache_key, None)

    try:
        yield mock
    finally:
        # Restore
        if original_provider is not None:
            container._providers[cache_key] = original_provider
        else:
            container._providers.pop(cache_key, None)

        if original_cached is not None:
            container._cache[cache_key] = original_cached
        else:
            container._cache.pop(cache_key, None)


@asynccontextmanager
async def spy_provider(
    container: Container,
    token: Type[T] | str,
    *,
    tag: Optional[str] = None,
):
    """
    Wrap an existing provider with a spy that tracks calls.

    The real provider's behavior is preserved.

    Usage::

        async with spy_provider(container, UserRepo) as spy:
            user = await container.resolve_async(UserRepo)
            assert spy.resolve_count == 1
    """
    token_key = container._token_to_key(token)
    cache_key = container._make_cache_key(token_key, tag)

    original_provider = container._providers.get(cache_key)
    if original_provider is None:
        raise KeyError(f"No provider registered for {token!r}")

    spy = _SpyProvider(original_provider)
    container._providers[cache_key] = spy
    container._cache.pop(cache_key, None)

    try:
        yield spy
    finally:
        container._providers[cache_key] = original_provider
        container._cache.pop(cache_key, None)


class TestContainer(Container):
    """
    A :class:`Container` subclass tailored for testing.

    Differences from the production container:
    - Relaxed duplicate registration (overwrites instead of raising).
    - Tracks all resolutions for debugging.
    - ``reset()`` clears the cache and resolution log.
    - Shortcut ``register_value`` and ``register_factory`` methods.

    Usage::

        container = TestContainer()
        container.register_value("Database", fake_db)
        db = container.resolve("Database")
    """

    def __init__(self, scope: str = "test", **kw):
        super().__init__(scope=scope, **kw)
        self.resolution_log: list[str] = []

    def register(self, provider: Provider, tag: Optional[str] = None):
        """Register, silently overwriting duplicates."""
        meta = provider.meta
        token = meta.token
        key = self._make_cache_key(token, tag)
        # Allow overwrite (unlike production Container)
        self._providers[key] = provider

    def register_value(
        self,
        token: Type | str,
        value: Any,
        scope: str = "singleton",
        tag: Optional[str] = None,
    ) -> _MockProvider:
        """Shortcut: register a fixed value provider."""
        provider = _MockProvider(value=value, token=token, scope=scope)
        self.register(provider, tag=tag)
        return provider

    def register_factory(
        self,
        token: Type | str,
        factory: Callable[..., Any],
        scope: str = "transient",
        tag: Optional[str] = None,
    ) -> _FactoryProvider:
        """Shortcut: register a factory provider."""
        provider = _FactoryProvider(factory=factory, token=token, scope=scope)
        self.register(provider, tag=tag)
        return provider

    def resolve(self, token, *, tag=None, optional=False):
        token_key = self._token_to_key(token)
        self.resolution_log.append(token_key)
        return super().resolve(token, tag=tag, optional=optional)

    def reset(self):
        """Clear cache and resolution log."""
        self._cache.clear()
        self.resolution_log.clear()
