"""
Aquilia EnumField — store Python enums with database mapping.

Usage:
    from enum import Enum
    from aquilia.models.fields import EnumField

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    class Item(Model):
        color = EnumField(enum_class=Color, default=Color.RED)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Type

from ..fields_module import Field, CharField, FieldValidationError, UNSET


__all__ = ["EnumField"]


class EnumField(Field):
    """
    Stores a Python Enum value in the database.

    By default, stores the enum *value* (not name) as a VARCHAR.
    Supports both string-valued and integer-valued enums.

    Args:
        enum_class: The Enum class to use
        max_length: Maximum length for string storage (default 50)
        store_name: If True, store the enum *name* instead of value
    """

    _field_type = "ENUM"

    def __init__(
        self,
        *,
        enum_class: Type[Enum],
        max_length: int = 50,
        store_name: bool = False,
        **kwargs,
    ):
        self.enum_class = enum_class
        self.max_length = max_length
        self.store_name = store_name

        # Auto-generate choices from enum
        choices = [(m.value, m.name) for m in enum_class]
        kwargs.setdefault("choices", choices)

        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.null:
                return None
            raise FieldValidationError(self.name, "Cannot be null")

        # Accept enum member directly
        if isinstance(value, self.enum_class):
            return value

        # Accept raw value
        try:
            return self.enum_class(value)
        except ValueError:
            pass

        # Accept name
        if isinstance(value, str) and value in self.enum_class.__members__:
            return self.enum_class[value]

        raise FieldValidationError(
            self.name,
            f"Invalid value '{value}' for {self.enum_class.__name__}. "
            f"Valid: {[m.value for m in self.enum_class]}",
            value,
        )

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value
        # Try by value first
        try:
            return self.enum_class(value)
        except (ValueError, KeyError):
            pass
        # Try by name
        if isinstance(value, str) and value in self.enum_class.__members__:
            return self.enum_class[value]
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.name if self.store_name else value.value
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        # Check if all values are integers
        all_int = all(isinstance(m.value, int) for m in self.enum_class)
        if all_int:
            return "INTEGER"
        return f"VARCHAR({self.max_length})"

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["enum_class"] = f"{self.enum_class.__module__}.{self.enum_class.__qualname__}"
        d["max_length"] = self.max_length
        d["store_name"] = self.store_name
        return d
