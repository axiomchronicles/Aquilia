"""
Aquilia Model Deletion — on_delete behaviors for ForeignKey fields.

Provides constants and handler functions for CASCADE, SET_NULL,
PROTECT, SET_DEFAULT, SET(), DO_NOTHING behaviors.

Usage:
    from aquilia.models.deletion import CASCADE, SET_NULL, PROTECT

    class Post(Model):
        author = ForeignKey(User, on_delete=CASCADE)
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
]


# String constants matching SQL behavior (for backward compat with
# existing ForeignKey(on_delete="CASCADE") usage)
CASCADE = "CASCADE"
SET_NULL = "SET NULL"
PROTECT = "PROTECT"
SET_DEFAULT = "SET DEFAULT"
DO_NOTHING = "DO NOTHING"
RESTRICT = "RESTRICT"


class OnDeleteHandler:
    """
    Callable that implements on_delete behavior at the application level.

    While the SQL-level REFERENCES ... ON DELETE handles database-level
    cascading, this class supports application-level pre/post processing.
    """

    def __init__(self, action: str, value: Any = None):
        self.action = action
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

        elif self.action == PROTECT:
            # Check if there are referencing rows
            row = await db.fetch_one(
                f'SELECT COUNT(*) as cnt FROM "{table}" '
                f'WHERE "{target_field_name}" = ?',
                [pk_value],
            )
            if row and row.get("cnt", 0) > 0:
                raise ProtectedError(
                    f"Cannot delete: {row['cnt']} {source_model.__name__} "
                    f"record(s) reference this object"
                )
            return 0

        elif self.action == RESTRICT:
            # Similar to PROTECT but checked at DB level
            row = await db.fetch_one(
                f'SELECT COUNT(*) as cnt FROM "{table}" '
                f'WHERE "{target_field_name}" = ?',
                [pk_value],
            )
            if row and row.get("cnt", 0) > 0:
                raise RestrictedError(
                    f"Cannot delete: {source_model.__name__} records "
                    f"reference this object (RESTRICT)"
                )
            return 0

        else:
            # DO_NOTHING
            return 0


class SET:
    """
    Factory for SET(value) on_delete behavior.

    Usage:
        author = ForeignKey(User, on_delete=SET(0))
        author = ForeignKey(User, on_delete=SET(lambda: get_sentinel_user()))
    """

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"SET({self.value!r})"


class ProtectedError(Exception):
    """Raised when trying to delete a protected object."""
    pass


class RestrictedError(Exception):
    """Raised when trying to delete a restricted object."""
    pass
