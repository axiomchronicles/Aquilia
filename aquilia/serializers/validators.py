"""
Aquilia Serializer Validators — Reusable validation callables.

Validators can be attached to individual fields or to the serializer
itself (via ``Meta.validators``).

Every validator is a callable ``(value) -> None`` that raises
``ValueError`` on failure.  Async validators are supported via
the ``AsyncValidator`` protocol.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Callable, Optional, Protocol, Sequence, runtime_checkable


# ============================================================================
# Validator Protocol
# ============================================================================

@runtime_checkable
class Validator(Protocol):
    """Synchronous validator protocol."""

    def __call__(self, value: Any) -> None:
        """Raise ``ValueError`` if *value* is invalid."""
        ...


@runtime_checkable
class AsyncValidator(Protocol):
    """Async validator that may hit the database."""

    async def __call__(self, value: Any) -> None:  # type: ignore[override]
        ...


# ============================================================================
# Value Validators
# ============================================================================

class MaxLengthValidator:
    """Reject values whose ``len()`` exceeds *limit*."""

    __slots__ = ("limit", "message")

    def __init__(self, limit: int, message: str | None = None):
        self.limit = limit
        self.message = message or f"Ensure this value has at most {limit} characters."

    def __call__(self, value: Any) -> None:
        if hasattr(value, "__len__") and len(value) > self.limit:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"MaxLengthValidator({self.limit})"


class MinLengthValidator:
    """Reject values whose ``len()`` is below *limit*."""

    __slots__ = ("limit", "message")

    def __init__(self, limit: int, message: str | None = None):
        self.limit = limit
        self.message = message or f"Ensure this value has at least {limit} characters."

    def __call__(self, value: Any) -> None:
        if hasattr(value, "__len__") and len(value) < self.limit:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"MinLengthValidator({self.limit})"


class MaxValueValidator:
    """Reject numeric values above *limit*."""

    __slots__ = ("limit", "message")

    def __init__(self, limit: float | int | Decimal, message: str | None = None):
        self.limit = limit
        self.message = message or f"Ensure this value is at most {limit}."

    def __call__(self, value: Any) -> None:
        if value is not None and value > self.limit:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"MaxValueValidator({self.limit})"


class MinValueValidator:
    """Reject numeric values below *limit*."""

    __slots__ = ("limit", "message")

    def __init__(self, limit: float | int | Decimal, message: str | None = None):
        self.limit = limit
        self.message = message or f"Ensure this value is at least {limit}."

    def __call__(self, value: Any) -> None:
        if value is not None and value < self.limit:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"MinValueValidator({self.limit})"


class RegexValidator:
    """Reject values that do not match *pattern*."""

    __slots__ = ("regex", "message", "inverse_match")

    def __init__(
        self,
        pattern: str,
        message: str | None = None,
        *,
        inverse_match: bool = False,
        flags: int = 0,
    ):
        self.regex = re.compile(pattern, flags)
        self.message = message or f"Value does not match pattern '{pattern}'."
        self.inverse_match = inverse_match

    def __call__(self, value: Any) -> None:
        if value is None:
            return
        val_str = str(value)
        matched = bool(self.regex.search(val_str))
        if self.inverse_match:
            matched = not matched
        if not matched:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"RegexValidator({self.regex.pattern!r})"


# ============================================================================
# Database-aware Validators (async)
# ============================================================================

class UniqueValidator:
    """
    Validate that a field value is unique in the database.

    Designed for use with ``ModelSerializer``.  Requires the model
    class to be set at validation time (the serializer wires this up).

    Usage::

        email = EmailField(validators=[UniqueValidator()])
    """

    __slots__ = ("message", "queryset", "lookup", "_model", "_field_name")

    def __init__(
        self,
        queryset: Any | None = None,
        lookup: str = "exact",
        message: str | None = None,
    ):
        self.queryset = queryset
        self.lookup = lookup
        self.message = message or "This field must be unique."
        self._model: Any = None
        self._field_name: str = ""

    def set_context(self, field_name: str, model: Any) -> None:
        """Called by ModelSerializer to wire up model/field context."""
        self._field_name = field_name
        self._model = model

    async def __call__(self, value: Any) -> None:
        if self._model is None:
            return  # No model context — skip (standalone Serializer)
        lookup_kwarg = f"{self._field_name}__{self.lookup}" if self.lookup != "exact" else self._field_name
        qs = self.queryset or self._model.objects.filter(**{lookup_kwarg: value})
        if not self.queryset:
            qs = self._model.objects.filter(**{lookup_kwarg: value})
        count = await qs.count()
        if count > 0:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"UniqueValidator(lookup={self.lookup!r})"


class UniqueTogetherValidator:
    """
    Validate that a combination of fields is unique together.

    Attach to ``Meta.validators``::

        class Meta:
            model = Order
            fields = "__all__"
            validators = [
                UniqueTogetherValidator(fields=["user_id", "product_id"]),
            ]
    """

    __slots__ = ("fields_list", "message", "_model")

    def __init__(
        self,
        fields: Sequence[str],
        message: str | None = None,
    ):
        self.fields_list = list(fields)
        self.message = message or f"The fields {', '.join(fields)} must be unique together."
        self._model: Any = None

    def set_context(self, model: Any) -> None:
        """Called by ModelSerializer to wire up model context."""
        self._model = model

    async def __call__(self, data: dict[str, Any]) -> None:
        if self._model is None:
            return
        lookup = {f: data.get(f) for f in self.fields_list if f in data}
        if len(lookup) != len(self.fields_list):
            return  # Not all fields present — skip
        count = await self._model.objects.filter(**lookup).count()
        if count > 0:
            raise ValueError(self.message)

    def __repr__(self) -> str:
        return f"UniqueTogetherValidator(fields={self.fields_list!r})"
