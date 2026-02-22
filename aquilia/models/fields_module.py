"""
Aquilia Model Fields — Pure Python, Django-grade field system.

Every field is production-ready with full validation, SQL generation,
and serialization. Aquilia fields use a unique descriptive API:

    class User(Model):
        table = "users"
        
        name = Char(max_length=150)
        email = Email(max_length=255, unique=True)
        age = Integer(null=True)
        bio = Text(blank=True)
        joined = DateTime(auto_now_add=True)

No $ prefixes, no AMDL — just clean, expressive Python.
"""

from __future__ import annotations

import copy
import datetime
import decimal
import ipaddress
import json
import os
import re
import uuid
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from .base import Model

__all__: list[str] = []


# ── Field Errors ─────────────────────────────────────────────────────────────


class FieldValidationError(ValueError):
    """Raised when field validation fails."""

    def __init__(self, field_name: str, message: str, value: Any = None):
        self.field_name = field_name
        self.value = value
        super().__init__(f"Field '{field_name}': {message}")


# ── Sentinel ─────────────────────────────────────────────────────────────────

class _Unset:
    """Sentinel for distinguishing 'not set' from None."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<UNSET>"

    def __bool__(self):
        return False

UNSET = _Unset()


# ── Base Field ───────────────────────────────────────────────────────────────


class Field:
    """
    Base field descriptor — all Aquilia fields inherit from this.

    Core parameters (shared by every field):
        null        – Allow NULL in database (default False)
        blank       – Allow empty string in validation (default False)
        default     – Default value or callable
        unique      – Add UNIQUE constraint
        primary_key – Mark as primary key
        db_index    – Create database index
        db_column   – Override column name
        choices     – Restrict to enumerated values
        validators  – List of validation callables
        help_text   – Documentation string
        editable    – Whether field is editable (default True)
        verbose_name – Human-readable field label
    """

    # Subclass-specific
    _field_type: str = "FIELD"
    _python_type: type = object

    # Counter for field ordering
    _creation_counter = 0

    def __init__(
        self,
        *,
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None,
    ):
        self.null = null
        self.blank = blank
        self.default = default
        self.unique = unique
        self.primary_key = primary_key
        self.db_index = db_index
        self.db_column = db_column
        self.choices = choices
        self.validators = validators or []
        self.help_text = help_text
        self.editable = editable
        self.verbose_name = verbose_name

        # Set by metaclass
        self.name: str = ""
        self.attr_name: str = ""
        self.model: Optional[Type[Model]] = None

        # Ordering
        self._order = Field._creation_counter
        Field._creation_counter += 1

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = self.db_column or name
        self.attr_name = name
        if self.verbose_name is None:
            self.verbose_name = name.replace("_", " ").title()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"

    @property
    def column_name(self) -> str:
        """Database column name."""
        return self.db_column or self.name

    def has_default(self) -> bool:
        """Check if field has a default value."""
        return self.default is not UNSET

    def get_default(self) -> Any:
        """Get default value, calling it if callable."""
        if self.default is UNSET:
            return None
        if callable(self.default):
            return self.default()
        return copy.deepcopy(self.default)

    def validate(self, value: Any) -> Any:
        """
        Validate and coerce value. Returns cleaned value.
        Override in subclasses for type-specific validation.
        """
        if value is None:
            # blank=True means field can be empty (validated before save)
            # null=True means field can be NULL in database
            # If blank=True, allow None during validation (will be set by auto_now/default)
            if not self.blank and not self.null:
                raise FieldValidationError(self.name, "Cannot be null")
            return None

        if self.choices:
            valid_values = [c[0] for c in self.choices]
            if value not in valid_values:
                raise FieldValidationError(
                    self.name,
                    f"Invalid choice '{value}'. Must be one of: {valid_values}",
                    value,
                )

        for validator in self.validators:
            validator(value)

        return value

    def to_python(self, value: Any) -> Any:
        """Convert database value to Python object."""
        if value is None:
            return None
        return value

    def to_db(self, value: Any) -> Any:
        """Convert Python value to database-ready value."""
        if value is None:
            return None
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        """Return SQL type string for this field."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement sql_type()"
        )

    def sql_column_def(self, dialect: str = "sqlite") -> str:
        """Generate full SQL column definition."""
        parts = [f'"{self.column_name}"', self.sql_type(dialect)]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if isinstance(self, (AutoField, BigAutoField)):
                parts.append("AUTOINCREMENT")
        if self.unique and not self.primary_key:
            parts.append("UNIQUE")
        if not self.null and not self.primary_key:
            parts.append("NOT NULL")
        if self.has_default():
            sql_default = self._sql_default(dialect)
            if sql_default is not None:
                parts.append(f"DEFAULT {sql_default}")

        return " ".join(parts)

    def _sql_default(self, dialect: str = "sqlite") -> Optional[str]:
        """Get SQL DEFAULT clause value."""
        if self.default is UNSET or callable(self.default):
            return None
        if isinstance(self.default, bool):
            return "1" if self.default else "0"
        if isinstance(self.default, (int, float)):
            return str(self.default)
        if isinstance(self.default, str):
            return f"'{self.default}'"
        return None

    def deconstruct(self) -> Dict[str, Any]:
        """Serialize field definition for migrations."""
        data: Dict[str, Any] = {
            "type": self.__class__.__name__,
            "null": self.null,
            "unique": self.unique,
            "primary_key": self.primary_key,
            "db_index": self.db_index,
        }
        if self.db_column:
            data["db_column"] = self.db_column
        if self.has_default() and not callable(self.default):
            data["default"] = self.default
        return data

    def clone(self) -> Field:
        """Create a deep copy of this field."""
        return copy.deepcopy(self)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔢 NUMERIC FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class AutoField(Field):
    """Auto-incrementing integer primary key (32-bit)."""

    _field_type = "AUTO"
    _python_type = int

    def __init__(self, *,
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        kwargs.setdefault("primary_key", True)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        if value is None:
            return None  # Auto-generated
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "INTEGER"


class BigAutoField(Field):
    """Auto-incrementing 64-bit integer primary key (Django 3.2+ default)."""

    _field_type = "BIGAUTO"
    _python_type = int

    def __init__(self, *,
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        kwargs.setdefault("primary_key", True)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "BIGSERIAL"
        return "INTEGER"


class SmallAutoField(AutoField):
    """Auto-incrementing 16-bit integer primary key."""

    _field_type = "SMALLAUTO"
    _python_type = int

    def validate(self, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if not (-32768 <= value <= 32767):
            raise FieldValidationError(self.name, f"Value {value} out of 16-bit integer range")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "SMALLSERIAL"
        return "INTEGER"



class IntegerField(Field):
    """Standard 32-bit integer field."""

    _field_type = "INTEGER"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if not (-2_147_483_648 <= value <= 2_147_483_647):
            raise FieldValidationError(self.name, f"Value {value} out of 32-bit integer range")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "INTEGER"


class BigIntegerField(Field):
    """64-bit integer field."""

    _field_type = "BIGINT"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "BIGINT"
        return "INTEGER"


class SmallIntegerField(Field):
    """16-bit integer field (-32768 to 32767)."""

    _field_type = "SMALLINT"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if not (-32_768 <= value <= 32_767):
            raise FieldValidationError(self.name, f"Value {value} out of 16-bit integer range")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "SMALLINT"
        return "INTEGER"


class PositiveIntegerField(Field):
    """Positive 32-bit integer field (0 to 2147483647)."""

    _field_type = "POSINT"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if value < 0:
            raise FieldValidationError(self.name, f"Value must be >= 0, got {value}")
        if value > 2_147_483_647:
            raise FieldValidationError(self.name, f"Value {value} exceeds maximum (2147483647)")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "INTEGER"


class PositiveSmallIntegerField(Field):
    """Positive 16-bit integer field (0 to 32767)."""

    _field_type = "POSSMALLINT"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if value < 0:
            raise FieldValidationError(self.name, f"Value must be >= 0, got {value}")
        if value > 32_767:
            raise FieldValidationError(self.name, f"Value {value} exceeds maximum (32767)")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "SMALLINT"
        return "INTEGER"


class PositiveBigIntegerField(Field):
    """Positive 64-bit integer field (0 to 9223372036854775807)."""

    _field_type = "POSBIGINT"
    _python_type = int

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer, got {type(value).__name__}")
        if value < 0:
            raise FieldValidationError(self.name, f"Value must be >= 0, got {value}")
        if value > 9_223_372_036_854_775_807:
            raise FieldValidationError(self.name, f"Value {value} exceeds maximum (9223372036854775807)")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "BIGINT"
        return "INTEGER"


class FloatField(Field):
    """Double-precision floating-point field."""

    _field_type = "FLOAT"
    _python_type = float

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected number, got {type(value).__name__}")
        return float(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "DOUBLE PRECISION"
        return "REAL"


class DecimalField(Field):
    """Fixed-precision decimal field."""

    _field_type = "DECIMAL"
    _python_type = decimal.Decimal

    def __init__(self, *, max_digits: int = 10, decimal_places: int = 2, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, decimal.Decimal):
            try:
                value = decimal.Decimal(str(value))
            except (TypeError, ValueError, decimal.InvalidOperation):
                raise FieldValidationError(self.name, f"Expected decimal, got {type(value).__name__}")

        # Check digits — correctly count whole and decimal parts
        sign, digits, exponent = value.as_tuple()
        if exponent >= 0:
            # No decimal places — e.g. Decimal('123') has exponent=0, digits=(1,2,3)
            whole_digits = len(digits) + exponent
            dec_digits = 0
        else:
            # Negative exponent — e.g. Decimal('12.34') has exponent=-2
            dec_digits = abs(exponent)
            whole_digits = max(0, len(digits) - dec_digits)

        if whole_digits > (self.max_digits - self.decimal_places):
            raise FieldValidationError(
                self.name,
                f"Ensure that there are no more than "
                f"{self.max_digits - self.decimal_places} digits before the decimal point "
                f"({whole_digits} found)",
            )
        if dec_digits > self.decimal_places:
            raise FieldValidationError(
                self.name,
                f"Ensure that there are no more than "
                f"{self.decimal_places} decimal places ({dec_digits} found)",
            )
        if len(digits) > self.max_digits:
            raise FieldValidationError(
                self.name,
                f"Ensure that there are no more than "
                f"{self.max_digits} digits in total ({len(digits)} found)",
            )
        return value

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        return decimal.Decimal(str(value))

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return str(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        return f"DECIMAL({self.max_digits},{self.decimal_places})"

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["max_digits"] = self.max_digits
        d["decimal_places"] = self.decimal_places
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# 🔤 TEXT / STRING FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class CharField(Field):
    """Short text field — requires max_length."""

    _field_type = "CHAR"
    _python_type = str

    def __init__(self, *, max_length: int = 255, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.max_length = max_length
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        # blank=True allows empty/whitespace-only strings;
        # blank=False rejects them (like Django)
        if not value.strip() and not self.blank:
            raise FieldValidationError(self.name, "Cannot be blank")
        if len(value) > self.max_length:
            raise FieldValidationError(
                self.name,
                f"Max length is {self.max_length}, got {len(value)} characters"
            )
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return f"VARCHAR({self.max_length})"

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["max_length"] = self.max_length
        return d


class VarcharField(CharField):
    """Explicit alias for CharField, representing a variable-length string."""
    _field_type = "VARCHAR"




class TextField(Field):
    """Long text field — no length restriction."""

    _field_type = "TEXT"
    _python_type = str

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        if not value.strip() and not self.blank:
            raise FieldValidationError(self.name, "Cannot be blank")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "TEXT"


class SlugField(CharField):
    """URL-friendly slug field."""

    _field_type = "SLUG"
    _SLUG_RE = re.compile(r'^[-a-zA-Z0-9_]+$')

    def __init__(self, *, max_length: int = 50, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        super().__init__(max_length=max_length, **kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not self._SLUG_RE.match(value):
            raise FieldValidationError(
                self.name,
                f"Invalid slug '{value}'. Only letters, numbers, hyphens, and underscores allowed."
            )
        return value


class EmailField(CharField):
    """Email address field with validation."""

    _field_type = "EMAIL"
    _EMAIL_RE = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )

    def __init__(self, *, max_length: int = 254, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        super().__init__(max_length=max_length, **kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not self._EMAIL_RE.match(value):
            raise FieldValidationError(self.name, f"Invalid email address: '{value}'")
        return value.lower()


class URLField(CharField):
    """URL field with validation."""

    _field_type = "URL"
    _URL_RE = re.compile(
        r'^https?://'
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?::\d+)?'
        r'(?:/[^\s]*)?$'
    )

    def __init__(self, *, max_length: int = 200, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        super().__init__(max_length=max_length, **kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not self._URL_RE.match(value):
            raise FieldValidationError(self.name, f"Invalid URL: '{value}'")
        return value


class UUIDField(Field):
    """UUID field — stored as VARCHAR(36) in database."""

    _field_type = "UUID"
    _python_type = uuid.UUID

    def __init__(self, *, auto: bool = False, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.auto = auto
        if auto:
            kwargs.setdefault("default", uuid.uuid4)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                raise FieldValidationError(self.name, f"Invalid UUID: '{value}'")
        raise FieldValidationError(self.name, f"Expected UUID, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return str(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "UUID"
        return "VARCHAR(36)"


class FilePathField(CharField):
    """File system path field."""

    _field_type = "FILEPATH"

    def __init__(
        self,
        *,
        path: str = "",
        match: Optional[str] = None,
        recursive: bool = False,
        allow_files: bool = True,
        allow_folders: bool = False,
        max_length: int = 100,
        **kwargs,
    ):
        self.path = path
        self.match = match
        self.recursive = recursive
        self.allow_files = allow_files
        self.allow_folders = allow_folders
        super().__init__(max_length=max_length, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# 📅 DATE & TIME FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class DateField(Field):
    """Date field (year, month, day)."""

    _field_type = "DATE"
    _python_type = datetime.date

    def __init__(self, *, auto_now: bool = False, auto_now_add: bool = False, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        # auto_now and auto_now_add fields should be blank=True (auto-populated)
        if auto_now or auto_now_add:
            kwargs.setdefault("blank", True)
        if auto_now_add:
            kwargs.setdefault("default", datetime.date.today)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                raise FieldValidationError(self.name, f"Invalid date format: '{value}'")
        raise FieldValidationError(self.name, f"Expected date, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "DATE"

    def pre_save(self, instance: Any, is_create: bool) -> Any:
        """Auto-set value before save."""
        if self.auto_now:
            return datetime.date.today()
        if self.auto_now_add and is_create:
            return datetime.date.today()
        return getattr(instance, self.attr_name, None)


class TimeField(Field):
    """Time field (hour, minute, second, microsecond)."""

    _field_type = "TIME"
    _python_type = datetime.time

    def __init__(self, *, auto_now: bool = False, auto_now_add: bool = False, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        # auto_now and auto_now_add fields should be blank=True (auto-populated)
        if auto_now or auto_now_add:
            kwargs.setdefault("blank", True)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, str):
            try:
                return datetime.time.fromisoformat(value)
            except ValueError:
                raise FieldValidationError(self.name, f"Invalid time format: '{value}'")
        raise FieldValidationError(self.name, f"Expected time, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, str):
            return datetime.time.fromisoformat(value)
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value.isoformat()
        return str(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "TIME"

    def pre_save(self, instance: Any, is_create: bool) -> Any:
        """Auto-set time value before save."""
        if self.auto_now:
            return datetime.datetime.now(datetime.timezone.utc).time()
        if self.auto_now_add and is_create:
            return datetime.datetime.now(datetime.timezone.utc).time()
        return getattr(instance, self.attr_name, None)


class DateTimeField(Field):
    """DateTime field with timezone support."""

    _field_type = "DATETIME"
    _python_type = datetime.datetime

    def __init__(self, *, auto_now: bool = False, auto_now_add: bool = False, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        # auto_now and auto_now_add fields should be blank=True (auto-populated)
        if auto_now or auto_now_add:
            kwargs.setdefault("blank", True)
        if auto_now_add:
            kwargs.setdefault("default", lambda: datetime.datetime.now(datetime.timezone.utc))
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.datetime.fromisoformat(value)
            except ValueError:
                raise FieldValidationError(self.name, f"Invalid datetime format: '{value}'")
        raise FieldValidationError(self.name, f"Expected datetime, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return str(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "TIMESTAMP WITH TIME ZONE"
        return "TIMESTAMP"

    def pre_save(self, instance: Any, is_create: bool) -> Any:
        """Auto-set value before save."""
        if self.auto_now:
            return datetime.datetime.now(datetime.timezone.utc)
        if self.auto_now_add and is_create:
            return datetime.datetime.now(datetime.timezone.utc)
        return getattr(instance, self.attr_name, None)


class DurationField(Field):
    """Stores timedelta — as microseconds in database."""

    _field_type = "DURATION"
    _python_type = datetime.timedelta

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        if isinstance(value, (int, float)):
            return datetime.timedelta(seconds=value)
        raise FieldValidationError(self.name, f"Expected timedelta, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        if isinstance(value, (int, float)):
            return datetime.timedelta(microseconds=value)
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return int(value.total_seconds() * 1_000_000)
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "INTERVAL"
        return "INTEGER"  # microseconds


# ═══════════════════════════════════════════════════════════════════════════════
# ✅ BOOLEAN FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class BooleanField(Field):
    """Boolean field — stored as INTEGER 0/1 in SQLite."""

    _field_type = "BOOL"
    _python_type = bool

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.null:
                return None
            raise FieldValidationError(self.name, "Cannot be null")
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                return True
            if value.lower() in ("false", "0", "no"):
                return False
        raise FieldValidationError(self.name, f"Expected boolean, got {type(value).__name__}")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        return bool(value)

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return 1 if value else 0

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "BOOLEAN"
        return "INTEGER"


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 BINARY / SPECIAL DATA FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class BinaryField(Field):
    """Binary data field — stored as BLOB."""

    _field_type = "BINARY"
    _python_type = bytes

    def __init__(self, *, max_length: Optional[int] = None, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.max_length = max_length
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise FieldValidationError(self.name, f"Expected bytes, got {type(value).__name__}")
        if self.max_length and len(value) > self.max_length:
            raise FieldValidationError(self.name, f"Max length is {self.max_length} bytes")
        return bytes(value)

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, memoryview):
            return bytes(value)
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "BLOB"


class JSONField(Field):
    """JSON data field — native on PostgreSQL, TEXT elsewhere."""

    _field_type = "JSON"
    _python_type = dict

    def __init__(self, *, encoder: Optional[type] = None, decoder: Optional[Callable] = None, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.encoder = encoder
        self.decoder = decoder
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        # Must be JSON-serializable
        try:
            json.dumps(value, cls=self.encoder)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(self.name, f"Value is not JSON serializable: {e}")
        return value

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, cls=self.encoder)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "JSONB"
        return "TEXT"


# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 RELATIONSHIP FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class RelationField(Field):
    """Base class for relationship fields."""

    def __init__(self, to: Union[str, Type[Model]], *, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.to = to
        self._related_model: Optional[Type[Model]] = None
        super().__init__(**kwargs)

    @property
    def related_model(self) -> Optional[Type[Model]]:
        """Resolve the related model (handles forward references)."""
        if self._related_model is not None:
            return self._related_model
        if isinstance(self.to, type):
            self._related_model = self.to
        return self._related_model

    def resolve_model(self, registry: Dict[str, Type[Model]]) -> None:
        """Resolve string-based model reference."""
        if isinstance(self.to, str):
            self._related_model = registry.get(self.to)


class ForeignKey(RelationField):
    """
    Many-to-one relationship field.

    Usage:
        class Post(Model):
            author = ForeignKey("User", related_name="posts")
    """

    _field_type = "FK"
    _python_type = int

    def __init__(
        self,
        to: Union[str, Type[Model]],
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        on_update: str = "CASCADE",
        db_constraint: bool = True,
        **kwargs,
    ):
        self.related_name = related_name
        self.on_delete = on_delete.upper()
        self.on_update = on_update.upper()
        self.db_constraint = db_constraint
        super().__init__(to=to, **kwargs)

    def __set_name__(self, owner: type, name: str) -> None:
        # FK column name gets _id suffix unless db_column is explicit
        if not self.db_column:
            self.db_column = f"{name}_id"
        super().__set_name__(owner, name)
        self.name = self.db_column

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.null:
                return None
            raise FieldValidationError(self.name, "Cannot be null")
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise FieldValidationError(self.name, f"Expected integer FK, got {type(value).__name__}")
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        return "INTEGER"

    def sql_column_def(self, dialect: str = "sqlite") -> str:
        base = super().sql_column_def(dialect)
        if self.db_constraint and self.related_model:
            table = getattr(self.related_model, '_table_name', self.related_model.__name__.lower())
            pk = getattr(self.related_model, '_pk_name', 'id')
            base += f' REFERENCES "{table}"("{pk}")'
            base += f" ON DELETE {self.on_delete}"
            base += f" ON UPDATE {self.on_update}"
        return base

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["to"] = self.to if isinstance(self.to, str) else self.to.__name__
        d["on_delete"] = self.on_delete
        d["related_name"] = self.related_name
        return d


class OneToOneField(ForeignKey):
    """
    One-to-one relationship field.

    Usage:
        class Profile(Model):
            user = OneToOneField("User", related_name="profile")
    """

    _field_type = "O2O"

    def __init__(self, to: Union[str, Type[Model]], *, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        kwargs.setdefault("unique", True)
        super().__init__(to=to, **kwargs)


class ManyToManyField(RelationField):
    """
    Many-to-many relationship field.

    Creates a junction table automatically. Not a real column — virtual.

    Usage:
        class Post(Model):
            tags = ManyToManyField("Tag", related_name="posts")
    """

    _field_type = "M2M"

    def __init__(
        self,
        to: Union[str, Type[Model]],
        *,
        related_name: Optional[str] = None,
        through: Optional[Union[str, Type[Model]]] = None,
        through_fields: Optional[Tuple[str, str]] = None,
        db_table: Optional[str] = None,
        **kwargs,
    ):
        self.related_name = related_name
        self.through = through
        self.through_fields = through_fields
        self.db_table = db_table
        # M2M is never an actual column
        kwargs.pop("null", None)
        kwargs.pop("unique", None)
        kwargs.pop("db_index", None)
        super().__init__(to=to, **kwargs)

    def junction_table_name(self, source_model: Type[Model]) -> str:
        """Generate junction table name."""
        if self.db_table:
            return self.db_table
        source = getattr(source_model, '_table_name', source_model.__name__.lower())
        target = self.to if isinstance(self.to, str) else self.to.__name__
        target = target.lower()
        return f"{source}_{self.attr_name}"

    def junction_columns(self, source_model: Type[Model]) -> Tuple[str, str]:
        """Return (source_fk_col, target_fk_col) for junction table."""
        if self.through_fields:
            return self.through_fields
        source_name = source_model.__name__.lower()
        target_name = self.to if isinstance(self.to, str) else self.to.__name__
        target_name = target_name.lower()
        return (f"{source_name}_id", f"{target_name}_id")

    def sql_type(self, dialect: str = "sqlite") -> str:
        return ""  # Not a real column

    def sql_column_def(self, dialect: str = "sqlite") -> str:
        return ""  # Not a real column

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["to"] = self.to if isinstance(self.to, str) else self.to.__name__
        d["related_name"] = self.related_name
        if self.through:
            d["through"] = self.through if isinstance(self.through, str) else self.through.__name__
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# 📍 IP & NETWORK FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class GenericIPAddressField(Field):
    """IPv4 or IPv6 address field."""

    _field_type = "IP"
    _python_type = str

    def __init__(self, *, protocol: str = "both", unpack_ipv4: bool = False, 
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        self.protocol = protocol.lower()
        self.unpack_ipv4 = unpack_ipv4
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        try:
            addr = ipaddress.ip_address(value)
            if self.protocol == "ipv4" and not isinstance(addr, ipaddress.IPv4Address):
                raise FieldValidationError(self.name, "Expected IPv4 address")
            if self.protocol == "ipv6" and not isinstance(addr, ipaddress.IPv6Address):
                raise FieldValidationError(self.name, "Expected IPv6 address")
            return str(addr)
        except ValueError:
            raise FieldValidationError(self.name, f"Invalid IP address: '{value}'")

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "INET"
        return "VARCHAR(39)"


# ═══════════════════════════════════════════════════════════════════════════════
# 📁 FILE & MEDIA FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class FileField(CharField):
    """File path/URL field — stores the path to the uploaded file."""

    _field_type = "FILE"

    def __init__(
        self,
        *,
        upload_to: Union[str, Callable] = "",
        max_length: int = 100,
        **kwargs,
    ):
        self.upload_to = upload_to
        super().__init__(max_length=max_length, **kwargs)


class ImageField(FileField):
    """Image file field — extends FileField with image validation."""

    _field_type = "IMAGE"

    def __init__(
        self,
        *,
        width_field: Optional[str] = None,
        height_field: Optional[str] = None,
        **kwargs,
    ):
        self.width_field = width_field
        self.height_field = height_field
        super().__init__(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# 🧬 ADVANCED / POSTGRESQL-SPECIFIC FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class ArrayField(Field):
    """PostgreSQL array field."""

    _field_type = "ARRAY"

    def __init__(self, base_field: Field, *, size: Optional[int] = None, **kwargs):
        self.base_field = base_field
        self.size = size
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, (list, tuple)):
            raise FieldValidationError(self.name, f"Expected list, got {type(value).__name__}")
        if self.size and len(value) > self.size:
            raise FieldValidationError(self.name, f"Max {self.size} elements, got {len(value)}")
        return [self.base_field.validate(item) for item in value]

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return list(value)

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        # SQLite: store as JSON
        return json.dumps(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return f"{self.base_field.sql_type(dialect)}[]"
        return "TEXT"  # JSON fallback


class HStoreField(Field):
    """PostgreSQL hstore field (key-value pairs)."""

    _field_type = "HSTORE"

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise FieldValidationError(self.name, f"Expected dict, got {type(value).__name__}")
        for k, v in value.items():
            if not isinstance(k, str):
                raise FieldValidationError(self.name, "All keys must be strings")
            if not isinstance(v, (str, type(None))):
                raise FieldValidationError(self.name, "All values must be strings or None")
        return value

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return json.dumps(value)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "HSTORE"
        return "TEXT"


class RangeField(Field):
    """Base class for PostgreSQL range fields."""

    _field_type = "RANGE"

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise FieldValidationError(self.name, "Range must be a 2-element [lower, upper]")
        return list(value)

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return list(value)

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return json.dumps(value)


class IntegerRangeField(RangeField):
    _field_type = "INT4RANGE"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "INT4RANGE"
        return "TEXT"


class BigIntegerRangeField(RangeField):
    _field_type = "INT8RANGE"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "INT8RANGE"
        return "TEXT"


class DecimalRangeField(RangeField):
    _field_type = "NUMRANGE"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "NUMRANGE"
        return "TEXT"


class DateRangeField(RangeField):
    _field_type = "DATERANGE"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "DATERANGE"
        return "TEXT"


class DateTimeRangeField(RangeField):
    _field_type = "TSTZRANGE"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "TSTZRANGE"
        return "TEXT"


# Case-insensitive text fields (PostgreSQL CITEXT)

class CICharField(CharField):
    """Case-insensitive CharField (PostgreSQL CITEXT)."""
    _field_type = "CICHAR"

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is not None:
            value = value.lower()
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "CITEXT"
        return f"VARCHAR({self.max_length})"


class CIEmailField(EmailField):
    """Case-insensitive EmailField (PostgreSQL CITEXT)."""
    _field_type = "CIEMAIL"

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "CITEXT"
        return f"VARCHAR({self.max_length})"


class CITextField(TextField):
    """Case-insensitive TextField (PostgreSQL CITEXT)."""
    _field_type = "CITEXT"

    def validate(self, value: Any) -> Any:
        value = super().validate(value)
        if value is not None:
            value = value.lower()
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if dialect == "postgresql":
            return "CITEXT"
        return "TEXT"


class InetAddressField(GenericIPAddressField):
    """PostgreSQL INET field — stores IP address with optional netmask."""
    _field_type = "INET"


# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 META / SPECIAL-PURPOSE FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class GeneratedField(Field):
    """
    Database-computed generated field (Django 5+).

    The value is computed from an expression and stored (STORED)
    or computed on read (VIRTUAL).
    """

    _field_type = "GENERATED"

    def __init__(
        self,
        *,
        expression: str,
        output_field: Optional[Field] = None,
        db_persist: bool = True,
        **kwargs,
    ):
        self.expression = expression
        self.output_field = output_field
        self.db_persist = db_persist
        kwargs["editable"] = False
        super().__init__(**kwargs)

    def sql_type(self, dialect: str = "sqlite") -> str:
        if self.output_field:
            return self.output_field.sql_type(dialect)
        return "TEXT"

    def sql_column_def(self, dialect: str = "sqlite") -> str:
        col_type = self.sql_type(dialect)
        mode = "STORED" if self.db_persist else "VIRTUAL"
        return f'"{self.column_name}" {col_type} GENERATED ALWAYS AS ({self.expression}) {mode}'


class OrderWrt(IntegerField):
    """Internal ordering helper field."""

    _field_type = "ORDERWRT"

    def __init__(self, *,
        null: bool = False,
        blank: bool = False,
        default: Any = UNSET,
        unique: bool = False,
        primary_key: bool = False,
        db_index: bool = False,
        db_column: Optional[str] = None,
        choices: Optional[Sequence[Tuple[Any, str]]] = None,
        validators: Optional[List[Callable]] = None,
        help_text: str = "",
        editable: bool = True,
        verbose_name: Optional[str] = None):
        kwargs = {
            'null': null,
            'blank': blank,
            'default': default,
            'unique': unique,
            'primary_key': primary_key,
            'db_index': db_index,
            'db_column': db_column,
            'choices': choices,
            'validators': validators,
            'help_text': help_text,
            'editable': editable,
            'verbose_name': verbose_name,
        }
        kwargs.setdefault("default", 0)
        kwargs.setdefault("db_index", True)
        super().__init__(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX / CONSTRAINT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


class Index:
    """
    Composite index declaration.

    Usage in Meta:
        class Meta:
            indexes = [
                Index(fields=["email", "username"], unique=True),
                Index(fields=["created_at"], name="idx_created"),
            ]
    """

    def __init__(
        self,
        *,
        fields: List[str],
        name: Optional[str] = None,
        unique: bool = False,
    ):
        self.fields = fields
        self.name = name
        self.unique = unique

    def sql(self, table_name: str) -> str:
        idx_name = self.name or f"idx_{table_name}_{'_'.join(self.fields)}"
        u = "UNIQUE " if self.unique else ""
        cols = ", ".join(f'"{f}"' for f in self.fields)
        return f'CREATE {u}INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ({cols});'


class UniqueConstraint:
    """
    Unique constraint declaration.

    Usage in Meta:
        class Meta:
            constraints = [
                UniqueConstraint(fields=["email", "tenant_id"], name="uq_email_tenant"),
            ]
    """

    def __init__(self, *, fields: List[str], name: Optional[str] = None):
        self.fields = fields
        self.name = name
