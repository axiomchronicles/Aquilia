"""
Aquilia Serializer Fields — Complete field library for serialization.

Every field handles:
- ``to_representation(value)``: Python object → JSON-safe output
- ``to_internal_value(data)``: Raw input → validated Python object
- ``validate(value)``: Custom validation after coercion
- ``run_validators(value)``: Run all attached validators

Field options:
- ``required`` (bool): Must be present in input (default True)
- ``default``: Default value or callable
- ``allow_null`` (bool): Accept None
- ``allow_blank`` (bool): Accept empty string (CharField only)
- ``read_only`` (bool): Include in output only
- ``write_only`` (bool): Accept in input only
- ``source`` (str): Attribute name on the source object (dot-path supported)
- ``label`` (str): Human label for OpenAPI
- ``help_text`` (str): Description for OpenAPI
- ``validators`` (list): Extra validator callables
- ``error_messages`` (dict): Custom error messages
"""

from __future__ import annotations

import copy
import datetime
import decimal
import ipaddress
import json
import re
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)


# ============================================================================
# Sentinel
# ============================================================================

class _Empty:
    """Sentinel for 'no value provided'."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<empty>"

    def __bool__(self):
        return False

empty = _Empty()


# ============================================================================
# Base Field
# ============================================================================

class SerializerField:
    """
    Base serializer field.

    All Aquilia serializer fields inherit from this class.
    Follows a descriptor-like pattern: the owning ``Serializer``
    metaclass calls ``bind(field_name, parent)`` at class-creation time.
    """

    _creation_counter: int = 0

    # Subclass may set these
    _type_label: str = "field"
    _python_type: type = object

    default_error_messages: Dict[str, str] = {
        "required": "This field is required.",
        "null": "This field may not be null.",
        "invalid": "Invalid value.",
    }

    def __init__(
        self,
        *,
        required: bool | None = None,
        default: Any = empty,
        allow_null: bool = False,
        allow_blank: bool = False,
        read_only: bool = False,
        write_only: bool = False,
        source: str | None = None,
        label: str | None = None,
        help_text: str = "",
        validators: list[Callable] | None = None,
        error_messages: dict[str, str] | None = None,
    ):
        # Auto-derive required: False if default is set or read_only
        if required is None:
            required = (default is empty) and (not read_only)

        self.required = required
        self.default = default
        self.allow_null = allow_null
        self.allow_blank = allow_blank
        self.read_only = read_only
        self.write_only = write_only
        self.source = source
        self.label = label
        self.help_text = help_text
        self.validators = list(validators or [])

        # Merge error messages
        self.error_messages = {**self.default_error_messages}
        if error_messages:
            self.error_messages.update(error_messages)

        # Set by Serializer metaclass
        self.field_name: str = ""
        self.parent: Any = None  # The owning Serializer instance

        # Ordering
        self._order = SerializerField._creation_counter
        SerializerField._creation_counter += 1

    # ── Binding ──────────────────────────────────────────────────────────

    def bind(self, field_name: str, parent: Any) -> None:
        """
        Called by the serializer to attach this field.

        Args:
            field_name: Name in the serializer's declared fields
            parent: The owning Serializer instance
        """
        self.field_name = field_name
        self.parent = parent
        if self.source is None:
            self.source = field_name
        if self.label is None:
            self.label = field_name.replace("_", " ").title()
        # Pre-split source for fast attribute access (avoids split per call)
        self._source_parts: tuple[str, ...] = tuple(self.source.split("."))
        self._simple_source: bool = len(self._source_parts) == 1

    # ── Core API ─────────────────────────────────────────────────────────

    def to_representation(self, value: Any) -> Any:
        """
        Convert a Python value to a JSON-serializable output.

        Override in subclasses for custom rendering.
        """
        return value

    def to_internal_value(self, data: Any) -> Any:
        """
        Convert raw input data to a validated Python value.

        Override in subclasses for custom parsing/coercion.
        Raise ``ValueError`` on invalid data.
        """
        return data

    def validate(self, value: Any) -> Any:
        """
        Per-field custom validation hook.

        Called AFTER ``to_internal_value``.  Return the (possibly
        modified) value, or raise ``ValueError``.
        """
        return value

    def run_validators(self, value: Any) -> None:
        """Run all attached validators."""
        errors: list[str] = []
        for validator in self.validators:
            try:
                validator(value)
            except (ValueError, TypeError) as exc:
                errors.append(str(exc))
        if errors:
            raise ValueError("; ".join(errors))

    def get_default(self) -> Any:
        """Return default value (call if callable).

        When ``required=False`` and no explicit default is set, returns
        ``None`` so that optional fields with no default are silently
        omitted rather than raising a spurious "required" error.
        """
        if self.default is empty:
            if self.required:
                raise ValueError(self.error_messages["required"])
            # Optional field with no explicit default → omit / None
            return None
        if callable(self.default):
            return self.default()
        return copy.deepcopy(self.default)

    def get_attribute(self, instance: Any) -> Any:
        """
        Extract the source attribute from *instance*.

        Supports dot-path sources like ``"user.email"``.
        Uses pre-split source parts (computed at bind time) to avoid
        string splitting on every call.
        """
        # Fast path: simple (non-dotted) source — most common case
        if self._simple_source:
            attr = self._source_parts[0]
            if isinstance(instance, Mapping):
                return instance.get(attr)
            return getattr(instance, attr, None)
        # Dotted path: traverse
        obj = instance
        for attr in self._source_parts:
            if isinstance(obj, Mapping):
                obj = obj.get(attr)
            elif obj is not None:
                obj = getattr(obj, attr, None)
            else:
                return None
        return obj

    # ── Introspection ────────────────────────────────────────────────────

    def to_schema(self) -> Dict[str, Any]:
        """Generate OpenAPI JSON-Schema fragment for this field."""
        schema: Dict[str, Any] = {}
        if self.help_text:
            schema["description"] = self.help_text
        if self.label:
            schema["title"] = self.label
        if self.allow_null:
            schema["nullable"] = True
        if self.default is not empty and not callable(self.default):
            schema["default"] = self.default
        return schema

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        bound = f", bound={self.field_name!r}" if self.field_name else ""
        return f"<{cls}{bound}>"


# ============================================================================
# Boolean Fields
# ============================================================================

class BooleanField(SerializerField):
    """Boolean field — coerces truthy/falsy strings."""

    _type_label = "boolean"
    _python_type = bool

    TRUE_VALUES = {"true", "True", "TRUE", "1", "yes", "Yes", "on", "On", True, 1}
    FALSE_VALUES = {"false", "False", "FALSE", "0", "no", "No", "off", "Off", False, 0}

    def to_internal_value(self, data: Any) -> bool:
        if data in self.TRUE_VALUES:
            return True
        if data in self.FALSE_VALUES:
            return False
        raise ValueError("Must be a valid boolean.")

    def to_representation(self, value: Any) -> bool:
        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False
        return bool(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "boolean"
        return schema


class NullBooleanField(BooleanField):
    """Tri-state boolean (True / False / None)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> bool | None:
        if data is None or data == "" or data == "null":
            return None
        return super().to_internal_value(data)

    def to_representation(self, value: Any) -> bool | None:
        if value is None:
            return None
        return super().to_representation(value)


# ============================================================================
# String Fields
# ============================================================================

class CharField(SerializerField):
    """String field with optional length constraints."""

    _type_label = "string"
    _python_type = str

    def __init__(
        self,
        *,
        max_length: int | None = None,
        min_length: int | None = None,
        trim_whitespace: bool = True,
        **kwargs,
    ):
        self.max_length = max_length
        self.min_length = min_length
        self.trim_whitespace = trim_whitespace
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        if not isinstance(data, (str, int, float)):
            raise ValueError("Not a valid string.")
        value = str(data)
        if self.trim_whitespace:
            value = value.strip()
        if not self.allow_blank and value == "":
            raise ValueError("This field may not be blank.")
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"Ensure this field has no more than {self.max_length} characters.")
        if self.min_length is not None and len(value) < self.min_length:
            raise ValueError(f"Ensure this field has at least {self.min_length} characters.")
        return value

    def to_representation(self, value: Any) -> str:
        return str(value) if value is not None else ""

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        return schema


class EmailField(CharField):
    """Email field with format validation."""

    _type_label = "email"

    _EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        if value and not self._EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value.lower() if value else value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "email"
        return schema


class SlugField(CharField):
    """Slug field (letters, numbers, hyphens, underscores)."""

    _type_label = "slug"
    _SLUG_RE = re.compile(r"^[-a-zA-Z0-9_]+$")

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        if value and not self._SLUG_RE.match(value):
            raise ValueError("Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.")
        return value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["pattern"] = r"^[-a-zA-Z0-9_]+$"
        return schema


class URLField(CharField):
    """URL field with basic validation."""

    _type_label = "url"
    _URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        if value and not self._URL_RE.match(value):
            raise ValueError("Enter a valid URL.")
        return value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["format"] = "uri"
        return schema


class UUIDField(SerializerField):
    """UUID field — accepts string or UUID objects."""

    _type_label = "uuid"
    _python_type = uuid.UUID

    def __init__(self, *, format: str = "hex_verbose", **kwargs):
        self.uuid_format = format  # "hex_verbose" (default), "hex", "int", "urn"
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> uuid.UUID:
        if isinstance(data, uuid.UUID):
            return data
        try:
            return uuid.UUID(str(data))
        except (ValueError, AttributeError):
            raise ValueError("Must be a valid UUID.")

    def to_representation(self, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "uuid"
        return schema


class IPAddressField(SerializerField):
    """IP address field (v4 or v6)."""

    _type_label = "ip"

    def __init__(self, *, protocol: str = "both", **kwargs):
        self.protocol = protocol  # "ipv4", "ipv6", "both"
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        try:
            if self.protocol == "ipv4":
                return str(ipaddress.IPv4Address(data))
            elif self.protocol == "ipv6":
                return str(ipaddress.IPv6Address(data))
            else:
                return str(ipaddress.ip_address(data))
        except (ValueError, TypeError):
            raise ValueError("Enter a valid IP address.")

    def to_representation(self, value: Any) -> str:
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        if self.protocol == "ipv4":
            schema["format"] = "ipv4"
        elif self.protocol == "ipv6":
            schema["format"] = "ipv6"
        else:
            schema["format"] = "ip-address"
        return schema


# ============================================================================
# Numeric Fields
# ============================================================================

class IntegerField(SerializerField):
    """Integer field with optional min/max."""

    _type_label = "integer"
    _python_type = int

    def __init__(
        self,
        *,
        min_value: int | None = None,
        max_value: int | None = None,
        **kwargs,
    ):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> int:
        if isinstance(data, bool):
            raise ValueError("A valid integer is required.")
        try:
            value = int(data)
        except (ValueError, TypeError):
            raise ValueError("A valid integer is required.")
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Ensure this value is greater than or equal to {self.min_value}.")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Ensure this value is less than or equal to {self.max_value}.")
        return value

    def to_representation(self, value: Any) -> int:
        return int(value) if value is not None else 0

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "integer"
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


class FloatField(SerializerField):
    """Float field with optional min/max."""

    _type_label = "float"
    _python_type = float

    def __init__(
        self,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        **kwargs,
    ):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> float:
        try:
            value = float(data)
        except (ValueError, TypeError):
            raise ValueError("A valid number is required.")
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Ensure this value is greater than or equal to {self.min_value}.")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Ensure this value is less than or equal to {self.max_value}.")
        return value

    def to_representation(self, value: Any) -> float:
        return float(value) if value is not None else 0.0

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "number"
        schema["format"] = "double"
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


class DecimalField(SerializerField):
    """Decimal field with precision control."""

    _type_label = "decimal"
    _python_type = decimal.Decimal

    def __init__(
        self,
        *,
        max_digits: int | None = None,
        decimal_places: int | None = None,
        min_value: decimal.Decimal | float | None = None,
        max_value: decimal.Decimal | float | None = None,
        coerce_to_string: bool = True,
        **kwargs,
    ):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.min_value = min_value
        self.max_value = max_value
        self.coerce_to_string = coerce_to_string
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> decimal.Decimal:
        try:
            value = decimal.Decimal(str(data))
        except (decimal.InvalidOperation, TypeError, ValueError):
            raise ValueError("A valid decimal number is required.")

        if value.is_nan() or value.is_infinite():
            raise ValueError("A valid decimal number is required.")

        # Check digit constraints
        sign, digits, exponent = value.as_tuple()
        whole_digits = len(digits) + exponent if exponent < 0 else len(digits)
        dec_places = abs(exponent) if exponent < 0 else 0

        if self.max_digits is not None and whole_digits > self.max_digits:
            raise ValueError(f"Ensure that there are no more than {self.max_digits} digits in total.")
        if self.decimal_places is not None and dec_places > self.decimal_places:
            raise ValueError(f"Ensure that there are no more than {self.decimal_places} decimal places.")

        if self.min_value is not None and value < decimal.Decimal(str(self.min_value)):
            raise ValueError(f"Ensure this value is greater than or equal to {self.min_value}.")
        if self.max_value is not None and value > decimal.Decimal(str(self.max_value)):
            raise ValueError(f"Ensure this value is less than or equal to {self.max_value}.")

        return value

    def to_representation(self, value: Any) -> str | float:
        if value is None:
            return None  # type: ignore
        d = decimal.Decimal(str(value))
        if self.decimal_places is not None:
            d = d.quantize(decimal.Decimal(10) ** -self.decimal_places)
        if self.coerce_to_string:
            return str(d)
        return float(d)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "decimal"
        return schema


# ============================================================================
# Date / Time Fields
# ============================================================================

class DateField(SerializerField):
    """Date field — ISO 8601 string ↔ datetime.date."""

    _type_label = "date"
    _python_type = datetime.date

    def __init__(self, *, format: str = "iso-8601", **kwargs):
        self.date_format = format
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> datetime.date:
        if isinstance(data, datetime.datetime):
            return data.date()
        if isinstance(data, datetime.date):
            return data
        if isinstance(data, str):
            try:
                return datetime.date.fromisoformat(data)
            except ValueError:
                pass
        raise ValueError("Date has wrong format. Use ISO 8601: YYYY-MM-DD.")

    def to_representation(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            value = value.date()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "date"
        return schema


class TimeField(SerializerField):
    """Time field — ISO 8601 string ↔ datetime.time."""

    _type_label = "time"
    _python_type = datetime.time

    def to_internal_value(self, data: Any) -> datetime.time:
        if isinstance(data, datetime.time):
            return data
        if isinstance(data, str):
            try:
                return datetime.time.fromisoformat(data)
            except ValueError:
                pass
        raise ValueError("Time has wrong format. Use ISO 8601: HH:MM[:SS[.ffffff]].")

    def to_representation(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "time"
        return schema


class DateTimeField(SerializerField):
    """DateTime field — ISO 8601 string ↔ datetime.datetime."""

    _type_label = "datetime"
    _python_type = datetime.datetime

    def to_internal_value(self, data: Any) -> datetime.datetime:
        if isinstance(data, datetime.datetime):
            return data
        if isinstance(data, datetime.date):
            return datetime.datetime(data.year, data.month, data.day)
        if isinstance(data, str):
            try:
                return datetime.datetime.fromisoformat(data)
            except ValueError:
                pass
        raise ValueError("Datetime has wrong format. Use ISO 8601: YYYY-MM-DDTHH:MM[:SS[.ffffff]][Z].")

    def to_representation(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "date-time"
        return schema


class DurationField(SerializerField):
    """Duration field — seconds or ISO 8601 duration string ↔ timedelta."""

    _type_label = "duration"
    _python_type = datetime.timedelta

    def to_internal_value(self, data: Any) -> datetime.timedelta:
        if isinstance(data, datetime.timedelta):
            return data
        if isinstance(data, (int, float)):
            return datetime.timedelta(seconds=data)
        if isinstance(data, str):
            try:
                return datetime.timedelta(seconds=float(data))
            except ValueError:
                pass
        raise ValueError("Duration has wrong format. Use seconds (number) or ISO 8601 duration.")

    def to_representation(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return value.total_seconds()
        return float(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "number"
        schema["description"] = schema.get("description", "") + " Duration in seconds."
        return schema


# ============================================================================
# Composite Fields
# ============================================================================

class ListField(SerializerField):
    """
    List field — validates each item with a child field.

    Usage::

        tags = ListField(child=CharField(max_length=50))
    """

    _type_label = "list"

    def __init__(
        self,
        *,
        child: SerializerField | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        **kwargs,
    ):
        self.child = child
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(**kwargs)

    def bind(self, field_name: str, parent: Any) -> None:
        super().bind(field_name, parent)
        if self.child:
            self.child.bind(f"{field_name}[]", parent)

    def to_internal_value(self, data: Any) -> list:
        if not isinstance(data, (list, tuple)):
            raise ValueError("Expected a list of items.")

        if self.min_length is not None and len(data) < self.min_length:
            raise ValueError(f"Ensure this list has at least {self.min_length} items.")
        if self.max_length is not None and len(data) > self.max_length:
            raise ValueError(f"Ensure this list has no more than {self.max_length} items.")

        if self.child:
            result = []
            errors: list[str] = []
            for idx, item in enumerate(data):
                try:
                    result.append(self.child.to_internal_value(item))
                except ValueError as e:
                    errors.append(f"Item {idx}: {e}")
            if errors:
                raise ValueError("; ".join(errors))
            return result
        return list(data)

    def to_representation(self, value: Any) -> list:
        if value is None:
            return []
        if self.child:
            return [self.child.to_representation(item) for item in value]
        return list(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "array"
        if self.child:
            schema["items"] = self.child.to_schema()
        if self.min_length is not None:
            schema["minItems"] = self.min_length
        if self.max_length is not None:
            schema["maxItems"] = self.max_length
        return schema


class DictField(SerializerField):
    """
    Dict field — validates values with an optional child field.

    Usage::

        metadata = DictField(child=CharField())
    """

    _type_label = "dict"

    def __init__(self, *, child: SerializerField | None = None, **kwargs):
        self.child = child
        super().__init__(**kwargs)

    def bind(self, field_name: str, parent: Any) -> None:
        super().bind(field_name, parent)
        if self.child:
            self.child.bind(f"{field_name}[*]", parent)

    def to_internal_value(self, data: Any) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Expected a dictionary.")
        if self.child:
            result = {}
            errors: list[str] = []
            for key, val in data.items():
                try:
                    result[str(key)] = self.child.to_internal_value(val)
                except ValueError as e:
                    errors.append(f"Key '{key}': {e}")
            if errors:
                raise ValueError("; ".join(errors))
            return result
        return dict(data)

    def to_representation(self, value: Any) -> dict:
        if value is None:
            return {}
        if self.child:
            return {k: self.child.to_representation(v) for k, v in value.items()}
        return dict(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "object"
        if self.child:
            schema["additionalProperties"] = self.child.to_schema()
        return schema


class JSONField(SerializerField):
    """
    JSON field — accepts any JSON-compatible value.

    If the input is a string, it is parsed as JSON.
    """

    _type_label = "json"

    def __init__(self, *, binary: bool = False, **kwargs):
        self.binary = binary
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise ValueError("Value must be valid JSON.")
        if isinstance(data, bytes):
            try:
                return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError("Value must be valid JSON.")
        # Already a Python object (dict, list, etc.)
        return data

    def to_representation(self, value: Any) -> Any:
        return value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        # JSON can be any type
        return schema


# ============================================================================
# Special Fields
# ============================================================================

class ReadOnlyField(SerializerField):
    """
    Read-only field that simply returns the source attribute.

    Used internally by ``ModelSerializer`` for fields like ``id``.
    """

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> Any:
        return value


class HiddenField(SerializerField):
    """
    Hidden field — not shown in representation, provides a default.

    Useful for injecting request context::

        owner = HiddenField(default=CurrentUserDefault())
    """

    def __init__(self, *, default: Any, **kwargs):
        kwargs["write_only"] = True
        super().__init__(default=default, **kwargs)

    def to_internal_value(self, data: Any) -> Any:
        return self.get_default()


class SerializerMethodField(SerializerField):
    """
    Read-only field whose value comes from a serializer method.

    Usage::

        class UserSerializer(Serializer):
            full_name = SerializerMethodField()

            def get_full_name(self, obj):
                return f"{obj.first_name} {obj.last_name}"
    """

    def __init__(self, *, method_name: str | None = None, **kwargs):
        kwargs["read_only"] = True
        kwargs.setdefault("source", "*")
        self.method_name = method_name
        super().__init__(**kwargs)

    def bind(self, field_name: str, parent: Any) -> None:
        if self.method_name is None:
            self.method_name = f"get_{field_name}"
        super().bind(field_name, parent)

    def to_representation(self, value: Any) -> Any:
        method = getattr(self.parent, self.method_name)
        return method(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        # Cannot determine type without running method
        return schema


class ChoiceField(SerializerField):
    """Field restricted to a fixed set of choices."""

    _type_label = "choice"

    def __init__(
        self,
        choices: Sequence[Any] | Sequence[Tuple[Any, str]],
        **kwargs,
    ):
        # Normalize choices to list of (value, label)
        normalized: list[tuple[Any, str]] = []
        for c in choices:
            if isinstance(c, (list, tuple)):
                normalized.append((c[0], str(c[1])))
            else:
                normalized.append((c, str(c)))
        self.choices = normalized
        self._valid_values = {c[0] for c in normalized}
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> Any:
        if data not in self._valid_values:
            valid = ", ".join(repr(v) for v in self._valid_values)
            raise ValueError(f"Invalid choice '{data}'. Valid choices: {valid}")
        return data

    def to_representation(self, value: Any) -> Any:
        return value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["enum"] = [c[0] for c in self.choices]
        return schema


class MultipleChoiceField(ChoiceField):
    """Field accepting a list of choices."""

    _type_label = "multiple_choice"

    def to_internal_value(self, data: Any) -> list:
        if not isinstance(data, (list, tuple, set)):
            raise ValueError("Expected a list of items.")
        result = []
        for item in data:
            if item not in self._valid_values:
                valid = ", ".join(repr(v) for v in self._valid_values)
                raise ValueError(f"Invalid choice '{item}'. Valid choices: {valid}")
            result.append(item)
        return result

    def to_representation(self, value: Any) -> list:
        if value is None:
            return []
        return list(value)

    def to_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {}
        schema["type"] = "array"
        schema["items"] = {"enum": [c[0] for c in self.choices]}
        if self.help_text:
            schema["description"] = self.help_text
        return schema


class FileField(SerializerField):
    """File upload field."""

    _type_label = "file"

    def __init__(
        self,
        *,
        max_size: int | None = None,
        allowed_types: list[str] | None = None,
        **kwargs,
    ):
        self.max_size = max_size
        self.allowed_types = allowed_types
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> Any:
        # Accept file-like objects or UploadFile instances
        if hasattr(data, "read"):
            return data
        raise ValueError("Expected a file upload.")

    def to_representation(self, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "url"):
            return value.url
        if hasattr(value, "name"):
            return value.name
        return str(value)

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["type"] = "string"
        schema["format"] = "binary"
        return schema


class ImageField(FileField):
    """Image upload field with format validation."""

    _type_label = "image"

    def __init__(self, **kwargs):
        kwargs.setdefault("allowed_types", ["image/jpeg", "image/png", "image/gif", "image/webp"])
        super().__init__(**kwargs)


class ConstantField(SerializerField):
    """
    Field that always returns a constant value.

    Useful for API versioning or type discriminators::

        type = ConstantField(value="user")
    """

    def __init__(self, *, value: Any, **kwargs):
        kwargs["read_only"] = True
        self._constant_value = value
        super().__init__(**kwargs)

    def to_representation(self, _value: Any) -> Any:
        return self._constant_value

    def get_attribute(self, instance: Any) -> Any:
        return self._constant_value

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        schema["const"] = self._constant_value
        return schema


# ============================================================================
# DI-Aware Defaults — Like FastAPI Depends() for serializer fields
# ============================================================================

class _DIAwareDefault:
    """Marker base for defaults that resolve from the DI container."""

    _is_di_default: bool = True

    def __call__(self) -> Any:  # pragma: no cover — resolved via DI path
        raise RuntimeError(
            f"{self.__class__.__name__} must be resolved through the DI "
            f"container.  Pass `context={{'container': container}}` to "
            f"the serializer."
        )


class CurrentUserDefault(_DIAwareDefault):
    """
    Inject the currently authenticated user from request context.

    Looks up ``context["request"].state["identity"]`` or resolves
    the ``Identity`` type from the DI container.

    Usage::

        class CommentSerializer(Serializer):
            author_id = HiddenField(default=CurrentUserDefault())
            body = CharField()

    At validation time the field is automatically populated with
    ``identity.id`` (or the full identity if ``use_id=False``).
    """

    __slots__ = ("use_id", "attr")

    def __init__(self, *, use_id: bool = True, attr: str = "id"):
        self.use_id = use_id
        self.attr = attr

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve current user from serializer context."""
        # 1. Check context["request"]
        request = context.get("request")
        if request is not None:
            state = getattr(request, "state", None)
            if state is not None:
                identity = state.get("identity") if isinstance(state, dict) else getattr(state, "identity", None)
                if identity is not None:
                    return getattr(identity, self.attr, identity) if self.use_id else identity

        # 2. Check context["identity"]
        identity = context.get("identity")
        if identity is not None:
            return getattr(identity, self.attr, identity) if self.use_id else identity

        # 3. Check DI container
        container = context.get("container")
        if container is not None:
            try:
                identity = container.resolve("identity", optional=True)
                if identity is not None:
                    return getattr(identity, self.attr, identity) if self.use_id else identity
            except Exception:
                pass

        return None

    def __repr__(self) -> str:
        return f"CurrentUserDefault(use_id={self.use_id}, attr={self.attr!r})"


class CurrentRequestDefault(_DIAwareDefault):
    """
    Inject the current request object (or an attribute of it).

    Usage::

        class AuditSerializer(Serializer):
            ip_address = HiddenField(default=CurrentRequestDefault(attr="client_ip"))
    """

    __slots__ = ("attr",)

    def __init__(self, *, attr: str | None = None):
        self.attr = attr

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve from serializer context."""
        request = context.get("request")
        if request is None:
            return None
        if self.attr:
            return getattr(request, self.attr, None)
        return request

    def __repr__(self) -> str:
        return f"CurrentRequestDefault(attr={self.attr!r})"


class InjectDefault(_DIAwareDefault):
    """
    Inject any service from the DI container at validation time.

    This is Aquilia's equivalent of FastAPI's ``Depends()``.

    Usage::

        class OrderSerializer(Serializer):
            total = HiddenField(default=InjectDefault(PricingService, method="calculate"))

    Or simply resolve the service and use it::

        class OrderSerializer(Serializer):
            pricing = HiddenField(default=InjectDefault(PricingService))

    Args:
        token: The DI token (type or string) to resolve.
        method: Optional method to call on the resolved service.
        tag: Optional DI tag for disambiguation.
    """

    __slots__ = ("token", "method", "tag")

    def __init__(
        self,
        token: Any,
        *,
        method: str | None = None,
        tag: str | None = None,
    ):
        self.token = token
        self.method = method
        self.tag = tag

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve service from DI container in serializer context."""
        container = context.get("container")
        if container is None:
            raise RuntimeError(
                f"InjectDefault({self.token}) requires a DI container in "
                f"serializer context.  Pass context={{'container': container}}."
            )

        try:
            if hasattr(container, "resolve"):
                service = container.resolve(self.token, tag=self.tag, optional=False)
            else:
                raise RuntimeError("Container does not support .resolve()")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to resolve {self.token} from DI container: {exc}"
            ) from exc

        if self.method:
            return getattr(service, self.method)
        return service

    def __repr__(self) -> str:
        return f"InjectDefault(token={self.token!r}, method={self.method!r})"


def is_di_default(default: Any) -> bool:
    """Check if a default value is DI-aware and needs container resolution."""
    return isinstance(default, _DIAwareDefault)
