"""
Aquilia Model Deletion — on_delete behaviors for ForeignKey fields.

Provides constants and handler functions for CASCADE, SET_NULL,
PROTECT, SET_DEFAULT, SET(), DO_NOTHING, RESTRICT behaviors.

Usage:
    from aquilia.models.deletion import CASCADE, SET_NULL, PROTECT, SET

    class Post(Model):
        author = ForeignKey(User, on_delete=CASCADE)

    class Comment(Model):
        author = ForeignKey(User, on_delete=SET(get_sentinel_user))
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

from .sql_builder import DeleteBuilder, UpdateBuilder

if TYPE_CHECKING:
    from .base import Model

logger = logging.getLogger("aquilia.models.deletion")

__all__ = [
    "CASCADE",
    "SET_NULL",
    "PROTECT",
    "SET_DEFAULT",
    "SET",
    "DO_NOTHING",
    "RESTRICT",
    "OnDeleteHandler",
    "ProtectedError",
    "RestrictedError",
    "normalize_on_delete",
]


# String constants matching SQL behavior (for backward compat with
# existing ForeignKey(on_delete="CASCADE") usage)
CASCADE = "CASCADE"
SET_NULL = "SET NULL"
PROTECT = "PROTECT"
SET_DEFAULT = "SET DEFAULT"
DO_NOTHING = "DO NOTHING"
RESTRICT = "RESTRICT"

# Normalization map for flexible on_delete string matching
_ON_DELETE_ALIASES = {
    "CASCADE": CASCADE,
    "SET_NULL": SET_NULL,
    "SET NULL": SET_NULL,
    "SETNULL": SET_NULL,
    "PROTECT": PROTECT,
    "SET_DEFAULT": SET_DEFAULT,
    "SET DEFAULT": SET_DEFAULT,
    "SETDEFAULT": SET_DEFAULT,
    "DO_NOTHING": DO_NOTHING,
    "DO NOTHING": DO_NOTHING,
    "DONOTHING": DO_NOTHING,
    "RESTRICT": RESTRICT,
}


def normalize_on_delete(action: Any) -> Any:
    """
    Normalize an on_delete value to its canonical constant.

    Handles string variations ("SET_NULL" / "SET NULL") and returns
    SET instances unchanged.
    """
    if isinstance(action, SET):
        return action
    if isinstance(action, str):
        upper = action.upper().strip()
        return _ON_DELETE_ALIASES.get(upper, action)
    return action


class OnDeleteHandler:
    """
    Callable that implements on_delete behavior at the application level.

    While the SQL-level REFERENCES ... ON DELETE handles database-level
    cascading, this class supports application-level pre/post processing.

    Supports string constants (CASCADE, SET_NULL, etc.) and SET instances.
    """

    def __init__(self, action: Any, value: Any = None):
        if isinstance(action, SET):
            self._set_instance = action
            self.action = "_SET_CALLABLE"
            self.value = None
        else:
            self._set_instance = None
            self.action = normalize_on_delete(action)
            self.value = value

    async def handle(
        self,
        db,
        source_model,
        target_field_name: str,
        pk_value: Any,
    ) -> int:
        """
        Execute the on_delete action.

        Args:
            db: Database instance
            source_model: The Model class with the FK
            target_field_name: Column name of the FK
            pk_value: PK value being deleted

        Returns:
            Number of affected rows
        """
        table = source_model._table_name

        if self.action == CASCADE:
            builder = DeleteBuilder(table)
            builder.where(f'"{target_field_name}" = ?', pk_value)
            sql, params = builder.build()
            cursor = await db.execute(sql, params)
            return cursor.rowcount

        elif self.action == SET_NULL:
            builder = UpdateBuilder(table)
            builder.set_dict({target_field_name: None})
            builder.where(f'"{target_field_name}" = ?', pk_value)
            sql, params = builder.build()
            cursor = await db.execute(sql, params)
            return cursor.rowcount

        elif self.action == SET_DEFAULT:
            default_val = self.value
            builder = UpdateBuilder(table)
            builder.set_dict({target_field_name: default_val})
            builder.where(f'"{target_field_name}" = ?', pk_value)
            sql, params = builder.build()
            cursor = await db.execute(sql, params)
            return cursor.rowcount

        elif self.action == "_SET_CALLABLE":
            # SET(value) or SET(callable)
            set_value = self._set_instance.resolve()
            builder = UpdateBuilder(table)
            builder.set_dict({target_field_name: set_value})
            builder.where(f'"{target_field_name}" = ?', pk_value)
            sql, params = builder.build()
            cursor = await db.execute(sql, params)
            return cursor.rowcount

        elif self.action == PROTECT:
            # Check if there are referencing rows
            row = await db.fetch_one(
                f'SELECT COUNT(*) as cnt FROM "{table}" '
                f'WHERE "{target_field_name}" = ?',
                [pk_value],
            )
            count = row.get("cnt", 0) if row else 0
            if count > 0:
                raise ProtectedError(
                    f"Cannot delete: {count} {source_model.__name__} "
                    f"record(s) reference this object",
                    protected_objects=count,
                )
            return 0

        elif self.action == RESTRICT:
            # Similar to PROTECT but semantically different — RESTRICT
            # is meant to mirror SQL RESTRICT (checked at DB level too)
            row = await db.fetch_one(
                f'SELECT COUNT(*) as cnt FROM "{table}" '
                f'WHERE "{target_field_name}" = ?',
                [pk_value],
            )
            count = row.get("cnt", 0) if row else 0
            if count > 0:
                raise RestrictedError(
                    f"Cannot delete: {source_model.__name__} records "
                    f"reference this object (RESTRICT)",
                    restricted_objects=count,
                )
            return 0

        else:
            # DO_NOTHING or unrecognized — no application-level action
            return 0

    @classmethod
    def for_action(cls, action: Any) -> OnDeleteHandler:
        """
        Factory method — create an OnDeleteHandler from any on_delete value.

        Handles string constants and SET instances uniformly.
        """
        if isinstance(action, SET):
            return cls(action)
        return cls(normalize_on_delete(action))


class SET:
    """
    Factory for SET(value) / SET(callable) on_delete behavior.

    When the referenced object is deleted, set the FK column to the
    given value — or call the given callable to compute the value.

    Usage:
        # Static value
        author = ForeignKey(User, on_delete=SET(0))

        # Callable (invoked at delete time)
        def get_sentinel_user():
            return 1  # sentinel user PK

        author = ForeignKey(User, on_delete=SET(get_sentinel_user))
    """

    def __init__(self, value: Any):
        self._value = value

    @property
    def value(self) -> Any:
        """The raw value or callable (for backward compatibility)."""
        return self._value

    def resolve(self) -> Any:
        """Resolve the SET value — call it if it's a callable."""
        if callable(self._value):
            return self._value()
        return self._value

    def __repr__(self) -> str:
        return f"SET({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SET):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        try:
            return hash(("SET", self._value))
        except TypeError:
            return hash(("SET", id(self._value)))


class ProtectedError(Exception):
    """Raised when trying to delete a protected object."""

    def __init__(self, message: str, protected_objects: int = 0):
        super().__init__(message)
        self.protected_objects = protected_objects


class RestrictedError(Exception):
    """Raised when trying to delete a restricted object."""

    def __init__(self, message: str, restricted_objects: int = 0):
        super().__init__(message)
        self.restricted_objects = restricted_objects
