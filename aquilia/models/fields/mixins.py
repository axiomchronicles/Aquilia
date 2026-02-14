"""
Aquilia Field Mixins — reusable behaviors for model fields.

These mixins can be composed with Field subclasses to add
standard behaviors without duplicating code:

    class NullableCharField(NullableMixin, CharField):
        pass

Or applied at runtime via ``Field.with_mixin(NullableMixin)``.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import warnings
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..fields_module import Field


__all__ = [
    "NullableMixin",
    "UniqueMixin",
    "IndexedMixin",
    "AutoNowMixin",
    "ChoiceMixin",
    "EncryptedMixin",
]


class NullableMixin:
    """
    Mixin that makes a field nullable with sensible defaults.

    Usage:
        class NullableChar(NullableMixin, CharField):
            pass

        name = NullableChar(max_length=100)
        # Equivalent to CharField(max_length=100, null=True, blank=True)
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)


class UniqueMixin:
    """
    Mixin that enforces uniqueness on a field.

    Usage:
        class UniqueEmail(UniqueMixin, EmailField):
            pass
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("unique", True)
        super().__init__(*args, **kwargs)


class IndexedMixin:
    """
    Mixin that auto-adds a database index to a field.

    Usage:
        class IndexedChar(IndexedMixin, CharField):
            pass
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_index", True)
        super().__init__(*args, **kwargs)


class AutoNowMixin:
    """
    Mixin for fields that auto-update on save (like updated_at).

    Applies to DateField, TimeField, DateTimeField.
    Sets auto_now=True by default.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_now", True)
        super().__init__(*args, **kwargs)


class ChoiceMixin:
    """
    Mixin that enforces validation of choices with display values.

    Provides helper methods to get display values from stored values.

    Usage:
        class StatusField(ChoiceMixin, CharField):
            STATUS_CHOICES = [
                ("active", "Active"),
                ("inactive", "Inactive"),
                ("pending", "Pending Review"),
            ]

            def __init__(self, **kwargs):
                kwargs.setdefault("choices", self.STATUS_CHOICES)
                super().__init__(**kwargs)
    """

    def get_display(self, value: Any) -> str:
        """Return the human-readable display value for a stored value."""
        if not hasattr(self, "choices") or not self.choices:
            return str(value)
        for choice_val, display in self.choices:
            if choice_val == value:
                return display
        return str(value)

    @property
    def choice_values(self) -> list:
        """Return list of valid stored values."""
        if not hasattr(self, "choices") or not self.choices:
            return []
        return [c[0] for c in self.choices]


class EncryptedMixin:
    """
    Placeholder mixin for encrypted field storage.

    When a concrete encryption backend is configured, this mixin
    encrypts values before writing to the database and decrypts
    on read. Without a backend, it stores values as base64-encoded
    strings and emits a deprecation warning.

    WARNING: The default base64 encoding is NOT secure encryption.
    Configure a real encryption backend for production use.

    Usage:
        class SecureTextField(EncryptedMixin, TextField):
            pass

        secret = SecureTextField()
    """

    _encryption_backend: Optional[Callable] = None
    _decryption_backend: Optional[Callable] = None

    @classmethod
    def configure_encryption(
        cls,
        encrypt: Callable[[str], str],
        decrypt: Callable[[str], str],
    ) -> None:
        """
        Configure encryption/decryption functions.

        Args:
            encrypt: Function that takes plaintext and returns ciphertext
            decrypt: Function that takes ciphertext and returns plaintext
        """
        cls._encryption_backend = encrypt
        cls._decryption_backend = decrypt

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        str_value = str(value)
        if self._encryption_backend:
            return self._encryption_backend(str_value)
        # Fallback: base64 (NOT secure — placeholder only)
        warnings.warn(
            "EncryptedMixin is using base64 encoding (NOT encryption). "
            "Configure a real encryption backend with "
            "EncryptedMixin.configure_encryption(encrypt_fn, decrypt_fn).",
            UserWarning,
            stacklevel=2,
        )
        return base64.b64encode(str_value.encode("utf-8")).decode("ascii")

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            if self._decryption_backend:
                return self._decryption_backend(value)
            # Fallback: base64 decode
            try:
                return base64.b64decode(value.encode("ascii")).decode("utf-8")
            except Exception:
                return value
        return value
