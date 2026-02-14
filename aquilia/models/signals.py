"""
Aquilia Model Signals — pre/post save, delete, init hooks.

Provides a lightweight signal/event system for model lifecycle events.

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
import inspect
import logging
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


class Signal:
    """
    A signal that can be connected to receiver functions.

    Receivers can be sync or async callables. They receive:
        sender   — the Model class
        instance — the model instance (if applicable)
        **kwargs — signal-specific keyword arguments

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
    """

    def __init__(self, name: str):
        self.name = name
        self._receivers: List[Callable] = []

    def connect(self, receiver: Callable = None, *, sender: Optional[Type] = None):
        """
        Connect a receiver function. Can be used as a decorator.

        Args:
            receiver: Callable to invoke when signal fires
            sender: Optional sender class to filter on
        """
        def _decorator(fn: Callable) -> Callable:
            entry = (fn, sender)
            if entry not in self._receivers:
                self._receivers.append(entry)
            return fn

        if receiver is not None:
            # Called as @signal.connect (without parentheses)
            if callable(receiver):
                entry = (receiver, sender)
                if entry not in self._receivers:
                    self._receivers.append(entry)
                return receiver
            # Called as @signal.connect(sender=MyModel)
            return _decorator
        return _decorator

    def disconnect(self, receiver: Callable, *, sender: Optional[Type] = None) -> bool:
        """
        Disconnect a receiver.

        Returns True if the receiver was found and removed.
        """
        entry = (receiver, sender)
        try:
            self._receivers.remove(entry)
            return True
        except ValueError:
            # Try removing without sender filter
            for i, (fn, s) in enumerate(self._receivers):
                if fn is receiver:
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
        for receiver, filter_sender in self._receivers:
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
        for receiver, filter_sender in self._receivers:
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

    @property
    def receivers(self) -> List[Callable]:
        """List of connected receiver functions."""
        return [fn for fn, _ in self._receivers]

    def has_listeners(self, sender: Optional[Type] = None) -> bool:
        """Check if any receivers are connected."""
        if sender is None:
            return len(self._receivers) > 0
        return any(
            s is None or s is sender
            for _, s in self._receivers
        )

    def clear(self) -> None:
        """Remove all receivers (useful for testing)."""
        self._receivers.clear()

    def __repr__(self) -> str:
        return f"<Signal '{self.name}' receivers={len(self._receivers)}>"


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
