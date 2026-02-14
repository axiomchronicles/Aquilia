"""
Aquilia Field Validators — reusable validation callables.

Provides a library of production-grade validators that can be
attached to any field via the ``validators=[...]`` parameter.

Usage:
    from aquilia.models.fields.validators import (
        MinValueValidator, MaxValueValidator, MinLengthValidator,
        RegexValidator, EmailValidator, URLValidator,
    )

    class Product(Model):
        price = DecimalField(validators=[MinValueValidator(0)])
        sku = CharField(max_length=20, validators=[
            RegexValidator(r'^[A-Z]{2}-\\d{4}$', "Invalid SKU format"),
        ])
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Callable, Optional, Sequence, Union


__all__ = [
    "BaseValidator",
    "MinValueValidator",
    "MaxValueValidator",
    "MinLengthValidator",
    "MaxLengthValidator",
    "RegexValidator",
    "EmailValidator",
    "URLValidator",
    "SlugValidator",
    "ProhibitNullCharactersValidator",
    "DecimalValidator",
    "FileExtensionValidator",
    "StepValueValidator",
    "RangeValidator",
    "UniqueForDateValidator",
]


class ValidationError(ValueError):
    """Raised by validators when a value fails validation."""

    def __init__(self, message: str, code: str = "invalid", params: Optional[dict] = None):
        self.message = message
        self.code = code
        self.params = params or {}
        super().__init__(message)


class BaseValidator:
    """Base class for all validators."""

    message: str = "Invalid value."
    code: str = "invalid"

    def __call__(self, value: Any) -> None:
        if not self.is_valid(value):
            raise ValidationError(
                self.get_message(value), code=self.code
            )

    def is_valid(self, value: Any) -> bool:
        """Override in subclasses. Return True if value is valid."""
        return True

    def get_message(self, value: Any) -> str:
        return self.message

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__) and
            self.__dict__ == other.__dict__
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class MinValueValidator(BaseValidator):
    """Ensure value >= limit."""

    code = "min_value"

    def __init__(self, limit_value: Union[int, float, Decimal], message: Optional[str] = None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return value >= self.limit_value

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value is greater than or equal to {self.limit_value}."
        )

    def __repr__(self) -> str:
        return f"MinValueValidator({self.limit_value})"


class MaxValueValidator(BaseValidator):
    """Ensure value <= limit."""

    code = "max_value"

    def __init__(self, limit_value: Union[int, float, Decimal], message: Optional[str] = None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return value <= self.limit_value

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value is less than or equal to {self.limit_value}."
        )

    def __repr__(self) -> str:
        return f"MaxValueValidator({self.limit_value})"


class MinLengthValidator(BaseValidator):
    """Ensure string length >= limit."""

    code = "min_length"

    def __init__(self, limit_value: int, message: Optional[str] = None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return len(value) >= self.limit_value

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value has at least {self.limit_value} character(s) "
            f"(it has {len(value) if value else 0})."
        )

    def __repr__(self) -> str:
        return f"MinLengthValidator({self.limit_value})"


class MaxLengthValidator(BaseValidator):
    """Ensure string length <= limit."""

    code = "max_length"

    def __init__(self, limit_value: int, message: Optional[str] = None):
        self.limit_value = limit_value
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return len(value) <= self.limit_value

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value has at most {self.limit_value} character(s) "
            f"(it has {len(value) if value else 0})."
        )


class RegexValidator(BaseValidator):
    """Validate against a regex pattern."""

    code = "invalid"

    def __init__(
        self,
        regex: str,
        message: Optional[str] = None,
        code: Optional[str] = None,
        inverse_match: bool = False,
        flags: int = 0,
    ):
        self.regex = regex
        self._compiled = re.compile(regex, flags)
        self.inverse_match = inverse_match
        if message:
            self.message = message
        if code:
            self.code = code

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        value = str(value)
        matched = bool(self._compiled.search(value))
        return not matched if self.inverse_match else matched

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Enter a valid value."
        )

    def __repr__(self) -> str:
        return f"RegexValidator({self.regex!r})"


class EmailValidator(RegexValidator):
    """Validate email address format."""

    _EMAIL_RE = (
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            self._EMAIL_RE,
            message=message or "Enter a valid email address.",
            code="invalid_email",
        )


class URLValidator(RegexValidator):
    """Validate URL format."""

    _URL_RE = (
        r'^https?://'
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?::\d+)?'
        r'(?:/[^\s]*)?$'
    )

    def __init__(self, message: Optional[str] = None, schemes: Optional[Sequence[str]] = None):
        self.schemes = schemes or ["http", "https"]
        super().__init__(
            self._URL_RE,
            message=message or "Enter a valid URL.",
            code="invalid_url",
        )


class SlugValidator(RegexValidator):
    """Validate slug format (letters, numbers, hyphens, underscores)."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            r'^[-a-zA-Z0-9_]+$',
            message=message or "Enter a valid slug (letters, numbers, hyphens, underscores).",
            code="invalid_slug",
        )


class ProhibitNullCharactersValidator(BaseValidator):
    """Reject strings containing null characters."""

    code = "null_characters_not_allowed"
    message = "Null characters are not allowed."

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return "\x00" not in str(value)


class DecimalValidator(BaseValidator):
    """Validate decimal precision and scale."""

    code = "invalid_decimal"

    def __init__(self, max_digits: int, decimal_places: int, message: Optional[str] = None):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        try:
            d = Decimal(str(value))
        except Exception:
            return False
        sign, digits, exponent = d.as_tuple()
        num_digits = len(digits)
        decimals = -exponent if exponent < 0 else 0
        whole_digits = num_digits - decimals
        return (
            whole_digits <= (self.max_digits - self.decimal_places)
            and decimals <= self.decimal_places
        )

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure there are no more than {self.max_digits} digits total "
            f"and {self.decimal_places} decimal places."
        )


class FileExtensionValidator(BaseValidator):
    """Validate file extension against an allowed list."""

    code = "invalid_extension"

    def __init__(
        self,
        allowed_extensions: Sequence[str],
        message: Optional[str] = None,
    ):
        self.allowed_extensions = [ext.lower().lstrip(".") for ext in allowed_extensions]
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        ext = str(value).rsplit(".", 1)[-1].lower() if "." in str(value) else ""
        return ext in self.allowed_extensions

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"File extension not allowed. Allowed: {', '.join(self.allowed_extensions)}."
        )


class StepValueValidator(BaseValidator):
    """Ensure value is a multiple of step (from offset)."""

    code = "invalid_step"

    def __init__(
        self,
        step: Union[int, float, Decimal],
        offset: Union[int, float, Decimal] = 0,
        message: Optional[str] = None,
    ):
        self.step = step
        self.offset = offset
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        return (Decimal(str(value)) - Decimal(str(self.offset))) % Decimal(str(self.step)) == 0

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value is a multiple of {self.step}."
        )


class RangeValidator(BaseValidator):
    """Ensure value falls within [min_val, max_val] range."""

    code = "out_of_range"

    def __init__(
        self,
        min_val: Optional[Union[int, float, Decimal]] = None,
        max_val: Optional[Union[int, float, Decimal]] = None,
        message: Optional[str] = None,
    ):
        self.min_val = min_val
        self.max_val = max_val
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        return True

    def get_message(self, value: Any) -> str:
        return self.message if hasattr(self, 'message') and self.message != "Invalid value." else (
            f"Ensure this value is between {self.min_val} and {self.max_val}."
        )


class UniqueForDateValidator(BaseValidator):
    """
    Validate uniqueness for a date-based scope.

    This is a placeholder — actual enforcement requires DB-level checks.
    """

    code = "unique_for_date"

    def __init__(self, date_field: str, message: Optional[str] = None):
        self.date_field = date_field
        if message:
            self.message = message

    def is_valid(self, value: Any) -> bool:
        # Placeholder — real uniqueness check happens at the DB level
        return True
