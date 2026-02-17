"""
Aquilia Blueprint Facets — the field-level primitives of a Blueprint.

A Facet is a single aspect of a model exposed through a Blueprint.
Facets auto-derive from Model fields but can be overridden, composed,
or created standalone.

Naming:
    - "Facet" because each one represents a *facet* of the model
      visible to the outside world.
    - Replaces the "SerializerField" abstraction with Blueprint-native
      semantics: cast (inbound), mold (outbound), seal (validate).
"""

from __future__ import annotations

import re
import uuid
import inspect
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TYPE_CHECKING,
)

from .exceptions import CastFault

if TYPE_CHECKING:
    from .core import Blueprint


__all__ = [
    "Facet",
    "TextFacet",
    "IntFacet",
    "FloatFacet",
    "DecimalFacet",
    "BoolFacet",
    "DateFacet",
    "TimeFacet",
    "DateTimeFacet",
    "DurationFacet",
    "UUIDFacet",
    "EmailFacet",
    "URLFacet",
    "SlugFacet",
    "IPFacet",
    "ListFacet",
    "DictFacet",
    "JSONFacet",
    "FileFacet",
    "ChoiceFacet",
    "Computed",
    "Constant",
    "WriteOnly",
    "ReadOnly",
    "Hidden",
    "Inject",
    "UNSET",
]


# ── Sentinel ─────────────────────────────────────────────────────────────

class _Unset:
    """Sentinel for 'no value provided'."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<UNSET>"

    def __bool__(self) -> bool:
        return False


UNSET = _Unset()


# ── Facet Base ───────────────────────────────────────────────────────────

class Facet:
    """
    Base facet — a single data point in a Blueprint.

    Lifecycle::

        inbound:   raw_value → cast() → seal() → validated_value
        outbound:  model_attr → mold() → output_value

    Attributes:
        source:       Model attribute name (defaults to facet name)
        required:     Must be present in input (default True)
        read_only:    Only appears in output, never accepted as input
        write_only:   Only accepted as input, never in output
        default:      Default value if not provided
        allow_null:   Accept None as a valid value
        allow_blank:  Accept empty string (text facets)
        label:        Human-readable label
        help_text:    Documentation string
        validators:   Extra validator callables
    """

    # Class-level ordering counter for stable field ordering
    _creation_order: int = 0

    # Override in subclasses for schema generation
    _type_name: str = "any"

    def __init__(
        self,
        *,
        source: str | None = None,
        required: bool | None = None,
        read_only: bool = False,
        write_only: bool = False,
        default: Any = UNSET,
        allow_null: bool = False,
        allow_blank: bool = False,
        label: str | None = None,
        help_text: str | None = None,
        validators: Sequence[Callable] | None = None,
    ):
        self.source = source
        self._required = required  # None = auto-detect from model field
        self.read_only = read_only
        self.write_only = write_only
        self.default = default
        self.allow_null = allow_null
        self.allow_blank = allow_blank
        self.label = label
        self.help_text = help_text
        self.validators: list[Callable] = list(validators) if validators else []

        # Set during bind()
        self.name: str | None = None
        self.blueprint: Blueprint | None = None
        self._bound = False

        # Auto-increment creation order for stable ordering
        Facet._creation_order += 1
        self._order = Facet._creation_order

    @property
    def required(self) -> bool:
        if self._required is not None:
            return self._required
        if self.read_only:
            return False
        if self.default is not UNSET:
            return False
        if self.allow_null:
            return False
        return True

    @required.setter
    def required(self, value: bool) -> None:
        self._required = value

    def bind(self, name: str, blueprint: Blueprint) -> None:
        """Attach this facet to a Blueprint with a field name."""
        self.name = name
        self.blueprint = blueprint
        if self.source is None:
            self.source = name
        self._bound = True

    def clone(self) -> Facet:
        """Create a shallow copy for Blueprint inheritance."""
        import copy
        new = copy.copy(self)
        new.validators = list(self.validators)
        new._bound = False
        new.name = None
        new.blueprint = None
        return new

    # ── Inbound: Cast ────────────────────────────────────────────────

    def cast(self, value: Any) -> Any:
        """
        Cast an incoming value to the internal Python type.

        Override in subclasses for type-specific coercion.
        Raise ``CastFault`` on failure.
        """
        return value

    # ── Outbound: Mold ───────────────────────────────────────────────

    def mold(self, value: Any) -> Any:
        """
        Shape an outgoing value for the response.

        Override in subclasses for type-specific formatting.
        """
        return value

    # ── Validation: Seal ─────────────────────────────────────────────

    def seal(self, value: Any) -> Any:
        """
        Run all field-level validators on a cast value.

        Returns the (possibly transformed) value.
        """
        for validator in self.validators:
            try:
                validator(value)
            except (ValueError, TypeError) as exc:
                raise CastFault(
                    self.name or "<unbound>",
                    str(exc),
                ) from exc
        return value

    # ── Attribute Access ─────────────────────────────────────────────

    def extract(self, instance: Any) -> Any:
        """
        Extract this facet's value from a model instance.

        Handles dotted sources like "category.name".
        """
        if self.source == "*":
            return instance

        parts = self.source.split(".") if self.source else []
        obj = instance
        for part in parts:
            if obj is None:
                return None
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
        return obj

    # ── Schema ───────────────────────────────────────────────────────

    def to_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema for this facet."""
        schema: Dict[str, Any] = {"type": self._type_name}
        if self.label:
            schema["title"] = self.label
        if self.help_text:
            schema["description"] = self.help_text
        if self.default is not UNSET:
            schema["default"] = self.default
        if self.read_only:
            schema["readOnly"] = True
        if self.write_only:
            schema["writeOnly"] = True
        return schema

    # ── Factories ────────────────────────────────────────────────────

    @classmethod
    def write_only(cls, **kwargs) -> Facet:
        """Factory: create a write-only facet."""
        kwargs["write_only"] = True
        return cls(**kwargs)

    @classmethod
    def read_only(cls, **kwargs) -> Facet:
        """Factory: create a read-only facet."""
        kwargs["read_only"] = True
        return cls(**kwargs)

    def __repr__(self) -> str:
        name = self.name or "<unbound>"
        return f"<{type(self).__name__} '{name}'>"


# ── Text Facets ──────────────────────────────────────────────────────────

class TextFacet(Facet):
    """Text/string facet with length constraints."""

    _type_name = "string"

    def __init__(
        self,
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        trim: bool = True,
        pattern: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.trim = trim
        self.pattern = re.compile(pattern) if pattern else None

    def cast(self, value: Any) -> str:
        if not isinstance(value, str):
            try:
                value = str(value)
            except (ValueError, TypeError) as exc:
                raise CastFault(self.name or "<unbound>", f"Expected string, got {type(value).__name__}") from exc
        if self.trim:
            value = value.strip()
        return value

    def seal(self, value: Any) -> str:
        if not self.allow_blank and isinstance(value, str) and value == "":
            raise CastFault(self.name or "<unbound>", "This field may not be blank")
        if self.min_length is not None and len(value) < self.min_length:
            raise CastFault(self.name or "<unbound>", f"Must be at least {self.min_length} characters")
        if self.max_length is not None and len(value) > self.max_length:
            raise CastFault(self.name or "<unbound>", f"Must be at most {self.max_length} characters")
        if self.pattern and not self.pattern.search(value):
            raise CastFault(self.name or "<unbound>", f"Does not match required pattern")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            schema["pattern"] = self.pattern.pattern
        return schema


class EmailFacet(TextFacet):
    """Email address facet with format validation."""

    _EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def cast(self, value: Any) -> str:
        value = super().cast(value)
        return value.lower()

    def seal(self, value: Any) -> str:
        if not self._EMAIL_RE.match(value):
            raise CastFault(self.name or "<unbound>", "Invalid email address")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "email"
        return schema


class URLFacet(TextFacet):
    """URL facet with format validation."""

    _URL_RE = re.compile(
        r"^https?://"
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
        r"[a-zA-Z]{2,}"
        r"(?::\d+)?"
        r"(?:/[^\s]*)?$"
    )

    def seal(self, value: Any) -> str:
        if not self._URL_RE.match(value):
            raise CastFault(self.name or "<unbound>", "Invalid URL")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "uri"
        return schema


class SlugFacet(TextFacet):
    """URL slug facet (lowercase alphanumeric + hyphens)."""

    _SLUG_RE = re.compile(r"^[-a-zA-Z0-9_]+$")

    def cast(self, value: Any) -> str:
        value = super().cast(value)
        return value.lower()

    def seal(self, value: Any) -> str:
        if not self._SLUG_RE.match(value):
            raise CastFault(self.name or "<unbound>", "Invalid slug (use letters, numbers, hyphens, underscores)")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["pattern"] = self._SLUG_RE.pattern
        return schema


class IPFacet(TextFacet):
    """IP address facet (v4 or v6)."""

    def seal(self, value: Any) -> str:
        import ipaddress
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise CastFault(self.name or "<unbound>", "Invalid IP address")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "ip-address"
        return schema


# ── Numeric Facets ───────────────────────────────────────────────────────

class IntFacet(Facet):
    """Integer facet with range constraints."""

    _type_name = "integer"

    def __init__(
        self,
        *,
        min_value: int | None = None,
        max_value: int | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def cast(self, value: Any) -> int:
        if isinstance(value, bool):
            raise CastFault(self.name or "<unbound>", "Boolean is not a valid integer")
        try:
            return int(value)
        except (ValueError, TypeError) as exc:
            raise CastFault(self.name or "<unbound>", f"Expected integer, got {type(value).__name__}") from exc

    def seal(self, value: Any) -> int:
        if self.min_value is not None and value < self.min_value:
            raise CastFault(self.name or "<unbound>", f"Must be at least {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise CastFault(self.name or "<unbound>", f"Must be at most {self.max_value}")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


class FloatFacet(Facet):
    """Floating-point facet."""

    _type_name = "number"

    def __init__(
        self,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def cast(self, value: Any) -> float:
        try:
            return float(value)
        except (ValueError, TypeError) as exc:
            raise CastFault(self.name or "<unbound>", f"Expected number, got {type(value).__name__}") from exc

    def seal(self, value: Any) -> float:
        if self.min_value is not None and value < self.min_value:
            raise CastFault(self.name or "<unbound>", f"Must be at least {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise CastFault(self.name or "<unbound>", f"Must be at most {self.max_value}")
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


class DecimalFacet(Facet):
    """Decimal facet with precision constraints."""

    _type_name = "string"  # JSON doesn't have decimal, use string

    def __init__(
        self,
        *,
        max_digits: int | None = None,
        decimal_places: int | None = None,
        min_value: Decimal | float | None = None,
        max_value: Decimal | float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.min_value = Decimal(str(min_value)) if min_value is not None else None
        self.max_value = Decimal(str(max_value)) if max_value is not None else None

    def cast(self, value: Any) -> Decimal:
        if isinstance(value, float):
            value = str(value)
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise CastFault(self.name or "<unbound>", f"Invalid decimal value") from exc

    def seal(self, value: Decimal) -> Decimal:
        if self.min_value is not None and value < self.min_value:
            raise CastFault(self.name or "<unbound>", f"Must be at least {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise CastFault(self.name or "<unbound>", f"Must be at most {self.max_value}")
        if self.max_digits is not None:
            sign, digits, exp = value.as_tuple()
            total_digits = len(digits)
            if total_digits > self.max_digits:
                raise CastFault(self.name or "<unbound>", f"Must have at most {self.max_digits} digits")
        if self.decimal_places is not None:
            sign, digits, exp = value.as_tuple()
            actual_places = -exp if exp < 0 else 0
            if actual_places > self.decimal_places:
                raise CastFault(self.name or "<unbound>", f"Must have at most {self.decimal_places} decimal places")
        return super().seal(value)

    def mold(self, value: Any) -> str:
        """Decimals are molded to strings for JSON precision."""
        if value is None:
            return None
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "decimal"
        return schema


# ── Boolean Facet ────────────────────────────────────────────────────────

class BoolFacet(Facet):
    """Boolean facet with truthy/falsy coercion."""

    _type_name = "boolean"

    _TRUE_VALUES = {"true", "1", "yes", "on", "t", "y"}
    _FALSE_VALUES = {"false", "0", "no", "off", "f", "n"}

    def cast(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in self._TRUE_VALUES:
                return True
            if lower in self._FALSE_VALUES:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        raise CastFault(self.name or "<unbound>", f"Expected boolean, got {type(value).__name__}")


# ── Date/Time Facets ─────────────────────────────────────────────────────

class DateFacet(Facet):
    """Date facet (ISO 8601)."""

    _type_name = "string"

    def cast(self, value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        raise CastFault(self.name or "<unbound>", "Expected ISO 8601 date (YYYY-MM-DD)")

    def mold(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "date"
        return schema


class TimeFacet(Facet):
    """Time facet (ISO 8601)."""

    _type_name = "string"

    def cast(self, value: Any) -> time:
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            try:
                return time.fromisoformat(value)
            except ValueError:
                pass
        raise CastFault(self.name or "<unbound>", "Expected ISO 8601 time (HH:MM:SS)")

    def mold(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, time):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "time"
        return schema


class DateTimeFacet(Facet):
    """DateTime facet (ISO 8601)."""

    _type_name = "string"

    def cast(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        raise CastFault(self.name or "<unbound>", "Expected ISO 8601 datetime")

    def mold(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "date-time"
        return schema


class DurationFacet(Facet):
    """Duration/timedelta facet."""

    _type_name = "string"

    def cast(self, value: Any) -> timedelta:
        if isinstance(value, timedelta):
            return value
        if isinstance(value, (int, float)):
            return timedelta(seconds=value)
        if isinstance(value, str):
            # Parse "HH:MM:SS" or total seconds
            try:
                return timedelta(seconds=float(value))
            except ValueError:
                pass
            parts = value.split(":")
            if len(parts) == 3:
                try:
                    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                    return timedelta(hours=h, minutes=m, seconds=s)
                except (ValueError, TypeError):
                    pass
        raise CastFault(self.name or "<unbound>", "Expected duration (seconds or HH:MM:SS)")

    def mold(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, timedelta):
            return value.total_seconds()
        return value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "duration"
        return schema


class UUIDFacet(Facet):
    """UUID facet."""

    _type_name = "string"

    def cast(self, value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError) as exc:
            raise CastFault(self.name or "<unbound>", "Invalid UUID") from exc

    def mold(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "uuid"
        return schema


# ── Structured Facets ────────────────────────────────────────────────────

class ListFacet(Facet):
    """List/array facet with optional child facet."""

    _type_name = "array"

    def __init__(
        self,
        *,
        child: Facet | None = None,
        min_items: int | None = None,
        max_items: int | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.child = child
        self.min_items = min_items
        self.max_items = max_items

    def cast(self, value: Any) -> list:
        if not isinstance(value, (list, tuple)):
            raise CastFault(self.name or "<unbound>", f"Expected list, got {type(value).__name__}")
        result = list(value)
        if self.child is not None:
            cast_items = []
            for i, item in enumerate(result):
                try:
                    cast_items.append(self.child.cast(item))
                except CastFault as exc:
                    raise CastFault(
                        f"{self.name or '<unbound>'}[{i}]",
                        str(exc),
                    ) from exc
            result = cast_items
        return result

    def seal(self, value: list) -> list:
        if self.min_items is not None and len(value) < self.min_items:
            raise CastFault(self.name or "<unbound>", f"Must have at least {self.min_items} items")
        if self.max_items is not None and len(value) > self.max_items:
            raise CastFault(self.name or "<unbound>", f"Must have at most {self.max_items} items")
        if self.child is not None:
            for i, item in enumerate(value):
                try:
                    self.child.seal(item)
                except CastFault as exc:
                    raise CastFault(f"{self.name or '<unbound>'}[{i}]", str(exc)) from exc
        return super().seal(value)

    def mold(self, value: Any) -> list | None:
        if value is None:
            return None
        if self.child is not None:
            return [self.child.mold(item) for item in value]
        return list(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.child is not None:
            schema["items"] = self.child.to_schema()
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        return schema


class DictFacet(Facet):
    """Dictionary/object facet."""

    _type_name = "object"

    def cast(self, value: Any) -> dict:
        if not isinstance(value, dict):
            raise CastFault(self.name or "<unbound>", f"Expected object, got {type(value).__name__}")
        return dict(value)

    def mold(self, value: Any) -> dict | None:
        if value is None:
            return None
        return dict(value) if isinstance(value, dict) else value


class JSONFacet(Facet):
    """Arbitrary JSON facet (any JSON-serializable value)."""

    _type_name = "object"

    def cast(self, value: Any) -> Any:
        # Accept any JSON-serializable value
        return value


# ── File Facet ───────────────────────────────────────────────────────────

class FileFacet(Facet):
    """File reference facet — stores path/URL string."""

    _type_name = "string"

    def __init__(self, *, allowed_types: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.allowed_types = allowed_types

    def mold(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "binary"
        return schema


# ── Choice Facet ─────────────────────────────────────────────────────────

class ChoiceFacet(Facet):
    """Facet with a fixed set of allowed values."""

    _type_name = "string"

    def __init__(self, *, choices: Sequence, **kwargs):
        super().__init__(**kwargs)
        if isinstance(choices, dict):
            self.choices = choices
            self._valid_values = set(choices.keys())
        elif choices and isinstance(choices[0], (list, tuple)):
            self.choices = {k: v for k, v in choices}
            self._valid_values = {k for k, v in choices}
        else:
            self.choices = {c: c for c in choices}
            self._valid_values = set(choices)

    def cast(self, value: Any) -> Any:
        return value

    def seal(self, value: Any) -> Any:
        if value not in self._valid_values:
            raise CastFault(
                self.name or "<unbound>",
                f"Invalid choice '{value}'. Valid: {sorted(str(v) for v in self._valid_values)}",
            )
        return super().seal(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["enum"] = sorted(str(v) for v in self._valid_values)
        return schema


# ── Special Facets ───────────────────────────────────────────────────────

class Computed(Facet):
    """
    A facet whose value is computed at output time — never accepted as input.

    Usage::

        full_name = Computed(lambda user: f"{user.first_name} {user.last_name}")
        item_count = Computed("get_item_count")  # calls method on model/blueprint
    """

    def __init__(self, compute: Callable | str, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)
        self._compute = compute

    def extract(self, instance: Any) -> Any:
        """Compute the value from the instance."""
        if isinstance(self._compute, str):
            # Method name on the blueprint
            if self.blueprint is not None:
                method = getattr(self.blueprint, self._compute, None)
                if method is not None:
                    return method(instance)
            # Method name on the instance
            method = getattr(instance, self._compute, None)
            if method is not None:
                result = method()
                return result
            return None
        # Callable
        return self._compute(instance)

    def mold(self, value: Any) -> Any:
        return value


class Constant(Facet):
    """
    A facet that always returns a fixed value — useful for type
    discriminators, API versioning, etc.

    Usage::

        api_version = Constant("v2")
        type = Constant("user")
    """

    def __init__(self, value: Any, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)
        self._constant = value

    def extract(self, instance: Any) -> Any:
        return self._constant

    def mold(self, value: Any) -> Any:
        return self._constant

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["const"] = self._constant
        return schema


class WriteOnly(TextFacet):
    """
    Convenience: a text facet that is write-only (e.g., passwords).

    Usage::

        password = WriteOnly(min_length=8)
    """

    def __init__(self, **kwargs):
        kwargs["write_only"] = True
        super().__init__(**kwargs)


class ReadOnly(Facet):
    """
    A pass-through read-only facet.

    Usage::

        created_at = ReadOnly()
    """

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def mold(self, value: Any) -> Any:
        # Auto-serialize common types
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, timedelta):
            return value.total_seconds()
        return value


class Hidden(Facet):
    """
    A hidden facet — populated from default/DI, never in input or output.

    Usage::

        class AuditBlueprint(Blueprint):
            created_by = Hidden(default=CurrentUserDefault())
    """

    def __init__(self, **kwargs):
        kwargs["write_only"] = True
        super().__init__(**kwargs)


# ── DI Injection Facet ───────────────────────────────────────────────────

class Inject(Facet):
    """
    A facet that resolves its value from the DI container at validation time.

    This is Aquilia's native approach to computed defaults — the value
    comes from a registered service rather than from user input.

    Usage::

        class OrderBlueprint(Blueprint):
            total = Inject(PricingService, via="calculate")
            audit_user = Inject("identity", attr="id")

    Args:
        token: DI token (type or string) to resolve.
        via: Method to call on the resolved service (result becomes the value).
        attr: Attribute to read from the resolved service.
    """

    def __init__(
        self,
        token: Any,
        *,
        via: str | None = None,
        attr: str | None = None,
        **kwargs,
    ):
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)
        self.token = token
        self.via = via
        self.attr = attr

    def resolve_from_context(self, context: Dict[str, Any]) -> Any:
        """Resolve value from DI container in Blueprint context."""
        container = context.get("container")
        if container is None:
            return UNSET

        try:
            service = container.resolve(self.token, optional=True)
        except Exception:
            return UNSET

        if service is None:
            return UNSET
        if self.via:
            method = getattr(service, self.via, None)
            if method and callable(method):
                return method()
            return UNSET
        if self.attr:
            return getattr(service, self.attr, UNSET)
        return service


# ── Model Field → Facet Mapping ──────────────────────────────────────────

# Maps model field class names to facet classes for auto-derivation
MODEL_FIELD_TO_FACET: Dict[str, Type[Facet]] = {
    # Text
    "CharField": TextFacet,
    "TextField": TextFacet,
    "SlugField": SlugFacet,
    "EmailField": EmailFacet,
    "URLField": URLFacet,
    "UUIDField": UUIDFacet,
    "FilePathField": TextFacet,
    # Numeric
    "IntegerField": IntFacet,
    "BigIntegerField": IntFacet,
    "SmallIntegerField": IntFacet,
    "PositiveIntegerField": IntFacet,
    "PositiveSmallIntegerField": IntFacet,
    "FloatField": FloatFacet,
    "DecimalField": DecimalFacet,
    "AutoField": IntFacet,
    "BigAutoField": IntFacet,
    # Boolean
    "BooleanField": BoolFacet,
    # Date/Time
    "DateField": DateFacet,
    "TimeField": TimeFacet,
    "DateTimeField": DateTimeFacet,
    "DurationField": DurationFacet,
    # Structured
    "JSONField": JSONFacet,
    "ArrayField": ListFacet,
    "HStoreField": DictFacet,
    # IP
    "GenericIPAddressField": IPFacet,
    "InetAddressField": IPFacet,
    # Files
    "FileField": FileFacet,
    "ImageField": FileFacet,
    # Binary
    "BinaryField": TextFacet,
    # Generated
    "GeneratedField": ReadOnly,
    # Range (PostgreSQL)
    "RangeField": TextFacet,
}


def derive_facet(model_field: Any) -> Facet:
    """
    Derive a Facet instance from an Aquilia Model field.

    Reads the model field's type, constraints, and defaults to
    produce a correctly configured Facet.
    """
    field_cls_name = type(model_field).__name__
    facet_cls = MODEL_FIELD_TO_FACET.get(field_cls_name, Facet)

    kwargs: Dict[str, Any] = {}

    # Null/blank
    if getattr(model_field, "null", False):
        kwargs["allow_null"] = True
    if getattr(model_field, "blank", False):
        kwargs["allow_blank"] = True

    # Help text
    if getattr(model_field, "help_text", ""):
        kwargs["help_text"] = model_field.help_text

    # Default value
    try:
        from ..models.fields_module import UNSET as MODEL_UNSET
    except ImportError:
        MODEL_UNSET = None

    field_default = getattr(model_field, "default", UNSET)
    if field_default is not MODEL_UNSET and field_default is not UNSET:
        kwargs["default"] = field_default

    # Read-only detection
    if getattr(model_field, "primary_key", False):
        kwargs["read_only"] = True
    if not getattr(model_field, "editable", True):
        kwargs["read_only"] = True
    if getattr(model_field, "auto_now", False) or getattr(model_field, "auto_now_add", False):
        kwargs["read_only"] = True

    # Required detection
    if not kwargs.get("read_only", False):
        has_default = getattr(model_field, "has_default", lambda: False)
        if callable(has_default):
            has_default = has_default()
        if getattr(model_field, "null", False) or getattr(model_field, "blank", False) or has_default:
            kwargs["required"] = False

    # Choices → ChoiceFacet
    if getattr(model_field, "choices", None):
        return ChoiceFacet(choices=model_field.choices, **kwargs)

    # Type-specific kwargs
    if facet_cls in (TextFacet, SlugFacet, EmailFacet, URLFacet):
        if hasattr(model_field, "max_length") and model_field.max_length:
            kwargs["max_length"] = model_field.max_length

    if facet_cls is DecimalFacet:
        if hasattr(model_field, "max_digits") and model_field.max_digits:
            kwargs["max_digits"] = model_field.max_digits
        if hasattr(model_field, "decimal_places") and model_field.decimal_places is not None:
            kwargs["decimal_places"] = model_field.decimal_places

    if facet_cls in (IntFacet, FloatFacet):
        if hasattr(model_field, "min_value") and model_field.min_value is not None:
            kwargs["min_value"] = model_field.min_value
        if hasattr(model_field, "max_value") and model_field.max_value is not None:
            kwargs["max_value"] = model_field.max_value

    return facet_cls(**kwargs)
