"""
Aquilia Model Enums — standard enum helpers for model fields.

Provides TextChoices and IntegerChoices similar to Django 3.0+.

Usage:
    from aquilia.models.enums import TextChoices, IntegerChoices

    class Status(TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Priority(IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"

    class Article(Model):
        status = CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
        priority = IntegerField(choices=Priority.choices, default=Priority.LOW)
"""

from __future__ import annotations

from enum import Enum, EnumType
from typing import Any, List, Tuple


__all__ = [
    "TextChoices",
    "IntegerChoices",
    "Choices",
]


class _ChoicesMeta(EnumType):
    """Metaclass that adds .choices / .values / .labels properties to Enum classes."""

    @property
    def choices(cls) -> List[Tuple[Any, str]]:
        return [(m.value, m.label) for m in cls]

    @property
    def values(cls) -> List[Any]:
        return [m.value for m in cls]

    @property
    def names_list(cls) -> List[str]:
        return [m.name for m in cls]

    @property
    def labels(cls) -> List[str]:
        return [m.label for m in cls]


class TextChoices(str, Enum, metaclass=_ChoicesMeta):
    """
    String-valued choices enum.

    Members may be defined as:
        NAME = "value", "Human Label"   → explicit label
        NAME = "value"                  → auto-generated label from name
    """

    def __new__(cls, value: str, label: str | None = None):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._label = label  # may be None; fixed in __init__
        return obj

    def __init__(self, value: str, label: str | None = None):
        # At this point self.name is set by Enum machinery
        if label is not None:
            self._label = label
        else:
            self._label = self.name.replace("_", " ").title()

    @property
    def label(self) -> str:
        return self._label

    def __str__(self) -> str:
        return str(self.value)


class IntegerChoices(int, Enum, metaclass=_ChoicesMeta):
    """
    Integer-valued choices enum.

    Members may be defined as:
        NAME = 1, "Human Label"   → explicit label
        NAME = 1                  → auto-generated label from name
    """

    def __new__(cls, value: int, label: str | None = None):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label = label  # may be None; fixed in __init__
        return obj

    def __init__(self, value: int, label: str | None = None):
        if label is not None:
            self._label = label
        else:
            self._label = self.name.replace("_", " ").title()

    @property
    def label(self) -> str:
        return self._label

    def __str__(self) -> str:
        return str(self.value)


# Alias for backward compat
Choices = TextChoices
