"""
Aquilia Testing - Effect System Testing Utilities.

Provides :class:`MockEffectRegistry` and :class:`MockEffectProvider`
for stubbing side-effects (DB, Cache, Queue, HTTP) in tests.
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from aquilia.effects import EffectProvider, EffectRegistry


@dataclass
class EffectCall:
    """Record of an acquire or release call on a MockEffectProvider."""
    action: str  # "acquire" or "release"
    mode: Optional[str] = None
    resource: Any = None
    success: Optional[bool] = None
    timestamp: float = 0.0


class MockEffectProvider(EffectProvider):
    """
    Stub provider that returns configurable values.

    Tracks acquire/release calls for assertions.
    Supports sequential return values for multi-call scenarios.

    Usage::

        mock = MockEffectProvider(return_value={"user": "alice"})
        resource = await mock.acquire(mode="read")
        assert resource == {"user": "alice"}
        assert mock.acquire_count == 1

        # Sequential returns:
        mock = MockEffectProvider(return_sequence=["a", "b", "c"])
        assert await mock.acquire() == "a"
        assert await mock.acquire() == "b"
        assert await mock.acquire() == "c"
        assert await mock.acquire() == "c"  # last value repeats
    """

    def __init__(
        self,
        return_value: Any = None,
        *,
        return_sequence: Optional[Sequence[Any]] = None,
        acquire_side_effect: Optional[Exception] = None,
    ):
        self.return_value = return_value
        self._return_sequence = list(return_sequence) if return_sequence else None
        self._sequence_idx = 0
        self.acquire_side_effect = acquire_side_effect
        self.acquire_count = 0
        self.release_count = 0
        self.acquired_modes: List[Optional[str]] = []
        self.released_resources: List[Any] = []
        self._initialized = False
        self._finalized = False
        self.call_history: List[EffectCall] = []

    async def initialize(self):
        self._initialized = True

    async def acquire(self, mode: Optional[str] = None) -> Any:
        self.acquire_count += 1
        self.acquired_modes.append(mode)
        self.call_history.append(EffectCall(
            action="acquire", mode=mode, timestamp=_time.monotonic(),
        ))
        if self.acquire_side_effect:
            raise self.acquire_side_effect

        # Sequential return values
        if self._return_sequence is not None:
            idx = min(self._sequence_idx, len(self._return_sequence) - 1)
            self._sequence_idx += 1
            return self._return_sequence[idx]
        return self.return_value

    async def release(self, resource: Any, success: bool = True):
        self.release_count += 1
        self.released_resources.append((resource, success))
        self.call_history.append(EffectCall(
            action="release", resource=resource, success=success,
            timestamp=_time.monotonic(),
        ))

    async def finalize(self):
        self._finalized = True

    @property
    def last_acquired_mode(self) -> Optional[str]:
        """Return the mode from the last acquire call."""
        return self.acquired_modes[-1] if self.acquired_modes else None

    def reset(self):
        """Reset all tracking counters."""
        self.acquire_count = 0
        self.release_count = 0
        self.acquired_modes.clear()
        self.released_resources.clear()
        self.call_history.clear()
        self._sequence_idx = 0


class MockEffectRegistry(EffectRegistry):
    """
    Test-friendly :class:`EffectRegistry` that auto-stubs missing effects.

    If ``acquire`` is called for an unregistered effect, a
    :class:`MockEffectProvider` is created automatically and returned.

    Usage::

        registry = MockEffectRegistry()
        registry.register_mock("DBTx", return_value=fake_conn)

        provider = registry.get_provider("DBTx")
        resource = await provider.acquire("read")
    """

    def __init__(self):
        super().__init__()
        self._mocks: Dict[str, MockEffectProvider] = {}

    def register_mock(
        self,
        effect_name: str,
        return_value: Any = None,
        **kw,
    ) -> MockEffectProvider:
        """Register a mock provider for the given effect name."""
        mock = MockEffectProvider(return_value=return_value, **kw)
        self._mocks[effect_name] = mock
        self.register(effect_name, mock)
        return mock

    def get_provider(self, effect_name: str) -> EffectProvider:
        """
        Return the provider – auto-creating a mock if not registered.
        """
        if effect_name not in self.providers:
            return self.register_mock(effect_name)
        return super().get_provider(effect_name)

    def get_mock(self, effect_name: str) -> Optional[MockEffectProvider]:
        """Retrieve the underlying mock (or ``None``)."""
        return self._mocks.get(effect_name)

    def reset_all(self):
        """Reset tracking on all mock providers."""
        for mock in self._mocks.values():
            mock.reset()
