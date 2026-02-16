"""
Aquilia Model Signals — pre/post save, delete, init hooks.

Provides a lightweight signal/event system for model lifecycle events,
with support for weak references, priority ordering, sender filtering,
and temporary connections.

Usage:
    from aquilia.models.signals import pre_save, post_save, pre_delete, post_delete

    @pre_save.connect
    async def hash_password(sender, instance, **kwargs):
        if sender.__name__ == "User" and instance.password_changed:
            instance.password = hash(instance.password)

    @post_save.connect
    async def send_welcome_email(sender, instance, created, **kwargs):
        if created and sender.__name__ == "User":
            await send_email(instance.email, "Welcome!")
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import weakref
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("aquilia.models.signals")

__all__ = [
    "Signal",
    "pre_save",
    "post_save",
    "pre_delete",
    "post_delete",
    "pre_init",
    "post_init",
    "m2m_changed",
    "receiver",
    "class_prepared",
    "pre_migrate",
    "post_migrate",
]


class _DeadRef:
    """Sentinel indicating a weak reference that has been garbage-collected."""
    pass


class Signal:
    """
    A signal that can be connected to receiver functions.

    Receivers can be sync or async callables. They receive:
        sender   — the Model class
        instance — the model instance (if applicable)
        **kwargs — signal-specific keyword arguments

    Features:
        - Sender-based filtering
        - Priority ordering (lower runs first)
        - Weak references (auto-disconnect when receiver is GC'd)
        - Temporary connections via context manager

    Usage:
        my_signal = Signal("my_signal")

        @my_signal.connect
        async def handler(sender, instance, **kwargs):
            print(f"Signal fired for {sender.__name__}")

        # Or connect without decorator
        my_signal.connect(handler)

        # Disconnect
        my_signal.disconnect(handler)

        # Fire
        await my_signal.send(MyModel, instance=obj, created=True)

        # Temporary connection
        async with my_signal.connected(handler):
            await my_signal.send(MyModel, instance=obj)
        # handler is automatically disconnected here
    """

    def __init__(self, name: str):
        self.name = name
        # Each entry: (receiver_or_weakref, sender_filter, priority)
        self._receivers: List[tuple] = []

    def connect(
        self,
        receiver: Callable = None,
        *,
        sender: Optional[Type] = None,
        weak: bool = False,
        priority: int = 100,
    ):
        """
        Connect a receiver function. Can be used as a decorator.

        Args:
            receiver: Callable to invoke when signal fires
            sender: Optional sender class to filter on
            weak: If True, store a weak reference (auto-cleanup on GC)
            priority: Lower values run first (default: 100)
        """
        def _decorator(fn: Callable) -> Callable:
            self._add_receiver(fn, sender, weak, priority)
            return fn

        if receiver is not None:
            # Called as @signal.connect (without parentheses)
            if callable(receiver):
                self._add_receiver(receiver, sender, weak, priority)
                return receiver
            # Called as @signal.connect(sender=MyModel)
            return _decorator
        return _decorator

    def _add_receiver(
        self,
        fn: Callable,
        sender: Optional[Type],
        weak: bool,
        priority: int,
    ) -> None:
        """Internal: add a receiver with deduplication."""
        # Store weak reference if requested
        if weak:
            try:
                ref = weakref.ref(fn, self._make_cleanup(fn, sender))
            except TypeError:
                # Built-in functions can't be weakly referenced
                ref = fn
        else:
            ref = fn

        # Check for duplicates (by identity)
        for existing_ref, existing_sender, _ in self._receivers:
            resolved = self._resolve_ref(existing_ref)
            if resolved is fn and existing_sender is sender:
                return  # Already connected

        self._receivers.append((ref, sender, priority))
        # Sort by priority (stable sort preserves insertion order for ties)
        self._receivers.sort(key=lambda x: x[2])

    def _make_cleanup(self, fn: Callable, sender: Optional[Type]) -> Callable:
        """Create a weak-reference finalizer that removes dead entries."""
        def cleanup(ref):
            self._receivers = [
                (r, s, p) for r, s, p in self._receivers
                if self._resolve_ref(r) is not _DeadRef
            ]
        return cleanup

    @staticmethod
    def _resolve_ref(ref: Any) -> Any:
        """Resolve a receiver — dereference weakrefs."""
        if isinstance(ref, weakref.ref):
            obj = ref()
            if obj is None:
                return _DeadRef
            return obj
        return ref

    def disconnect(self, receiver: Callable, *, sender: Optional[Type] = None) -> bool:
        """
        Disconnect a receiver.

        Returns True if the receiver was found and removed.
        """
        for i, (ref, s, p) in enumerate(self._receivers):
            resolved = self._resolve_ref(ref)
            if resolved is receiver and s is sender:
                self._receivers.pop(i)
                return True
        # Try removing without sender filter
        for i, (ref, s, p) in enumerate(self._receivers):
            resolved = self._resolve_ref(ref)
            if resolved is receiver:
                self._receivers.pop(i)
                return True
        return False

    async def send(self, sender: Type, **kwargs) -> List[Any]:
        """
        Fire the signal, calling all connected receivers.

        Args:
            sender: The Model class sending the signal
            **kwargs: Signal-specific arguments

        Returns:
            List of return values from receivers
        """
        results = []
        for ref, filter_sender, _ in self._receivers:
            receiver = self._resolve_ref(ref)
            if receiver is _DeadRef:
                continue
            # Skip if sender filter doesn't match
            if filter_sender is not None and sender is not filter_sender:
                continue
            try:
                if inspect.iscoroutinefunction(receiver):
                    result = await receiver(sender=sender, **kwargs)
                else:
                    result = receiver(sender=sender, **kwargs)
                results.append(result)
            except Exception as exc:
                logger.error(
                    f"Signal '{self.name}' receiver {receiver.__name__} "
                    f"raised {exc.__class__.__name__}: {exc}"
                )
                results.append(exc)
        return results

    def send_sync(self, sender: Type, **kwargs) -> List[Any]:
        """
        Fire the signal synchronously (for sync receivers only).
        """
        results = []
        for ref, filter_sender, _ in self._receivers:
            receiver = self._resolve_ref(ref)
            if receiver is _DeadRef:
                continue
            if filter_sender is not None and sender is not filter_sender:
                continue
            if inspect.iscoroutinefunction(receiver):
                logger.warning(
                    f"Signal '{self.name}': async receiver {receiver.__name__} "
                    f"skipped in sync send"
                )
                continue
            try:
                result = receiver(sender=sender, **kwargs)
                results.append(result)
            except Exception as exc:
                logger.error(
                    f"Signal '{self.name}' receiver {receiver.__name__} "
                    f"raised {exc.__class__.__name__}: {exc}"
                )
                results.append(exc)
        return results

    async def robust_send(self, sender: Type, **kwargs) -> List[Any]:
        """
        Fire the signal, catching exceptions from each receiver.

        Unlike send(), this does NOT stop on exceptions — every receiver
        runs regardless. Returns list of (receiver, response_or_exception).

        Like Django's Signal.send_robust().
        """
        results = []
        for ref, filter_sender, _ in self._receivers:
            receiver = self._resolve_ref(ref)
            if receiver is _DeadRef:
                continue
            if filter_sender is not None and sender is not filter_sender:
                continue
            try:
                if inspect.iscoroutinefunction(receiver):
                    result = await receiver(sender=sender, **kwargs)
                else:
                    result = receiver(sender=sender, **kwargs)
                results.append((receiver, result))
            except Exception as exc:
                logger.error(
                    f"Signal '{self.name}' receiver {receiver.__name__} "
                    f"raised {exc.__class__.__name__}: {exc}"
                )
                results.append((receiver, exc))
        return results

    @property
    def receivers(self) -> List[Callable]:
        """List of connected receiver functions (resolved, alive only)."""
        result = []
        for ref, _, _ in self._receivers:
            resolved = self._resolve_ref(ref)
            if resolved is not _DeadRef:
                result.append(resolved)
        return result

    def has_listeners(self, sender: Optional[Type] = None) -> bool:
        """Check if any receivers are connected (optionally for a sender)."""
        if sender is None:
            return any(
                self._resolve_ref(ref) is not _DeadRef
                for ref, _, _ in self._receivers
            )
        return any(
            self._resolve_ref(ref) is not _DeadRef
            and (s is None or s is sender)
            for ref, s, _ in self._receivers
        )

    @contextlib.contextmanager
    def connected(self, fn: Callable, *, sender: Optional[Type] = None, priority: int = 100):
        """
        Context manager for temporary signal connection.

        The receiver is automatically disconnected on exit.

        Usage:
            with pre_save.connected(my_handler, sender=User):
                await user.save()
            # my_handler is disconnected here
        """
        self._add_receiver(fn, sender, weak=False, priority=priority)
        try:
            yield
        finally:
            self.disconnect(fn, sender=sender)

    def clear(self) -> None:
        """Remove all receivers (useful for testing)."""
        self._receivers.clear()

    def __repr__(self) -> str:
        alive = sum(1 for ref, _, _ in self._receivers if self._resolve_ref(ref) is not _DeadRef)
        return f"<Signal '{self.name}' receivers={alive}>"


# ── Built-in signals ─────────────────────────────────────────────────────────

pre_save = Signal("pre_save")
post_save = Signal("post_save")
pre_delete = Signal("pre_delete")
post_delete = Signal("post_delete")
pre_init = Signal("pre_init")
post_init = Signal("post_init")
m2m_changed = Signal("m2m_changed")
class_prepared = Signal("class_prepared")
pre_migrate = Signal("pre_migrate")
post_migrate = Signal("post_migrate")


# ── receiver() shorthand decorator ──────────────────────────────────────────


def receiver(signal: Signal, *, sender: Optional[Type] = None):
    """
    Shorthand decorator to connect a function to a signal.

    Usage:
        from aquilia.models.signals import receiver, pre_save

        @receiver(pre_save, sender=User)
        async def hash_password(sender, instance, **kwargs):
            if instance.password_changed:
                instance.password = hash(instance.password)

        # Multiple signals:
        @receiver(pre_save)
        @receiver(post_save)
        async def log_save(sender, instance, **kwargs):
            print(f"Saving {sender.__name__}")
    """
    def _decorator(fn: Callable) -> Callable:
        signal.connect(fn, sender=sender)
        return fn
    return _decorator
