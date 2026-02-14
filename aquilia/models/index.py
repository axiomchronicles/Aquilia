"""
Aquilia Model Indexes — standalone index rendering.

Re-exports Index and UniqueConstraint from fields_module and adds
additional index types: GinIndex, GistIndex, BrinIndex, HashIndex,
and FunctionalIndex.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

# Re-export originals from fields_module
from ..models.fields_module import Index, UniqueConstraint

__all__ = [
    # Re-exported
    "Index",
    "UniqueConstraint",
    # New
    "GinIndex",
    "GistIndex",
    "BrinIndex",
    "HashIndex",
    "FunctionalIndex",
]


class _PostgresOnlyIndex:
    """Base class for PostgreSQL-specific index types."""

    _index_type: str = ""

    def __init__(
        self,
        *,
        fields: Sequence[str] = (),
        name: Optional[str] = None,
        condition: Optional[str] = None,
        opclasses: Sequence[str] = (),
    ):
        self.fields = list(fields)
        self.name = name
        self.condition = condition
        self.opclasses = list(opclasses)

    def sql(self, table_name: str, dialect: str = "sqlite") -> str:
        """Generate CREATE INDEX statement."""
        if dialect == "sqlite":
            # Fall back to B-tree on SQLite
            return self._btree_fallback(table_name)

        idx_name = self.name or f"idx_{table_name}_{'_'.join(self.fields)}"
        cols_with_opclass = []
        for i, field in enumerate(self.fields):
            col_str = f'"{field}"'
            if i < len(self.opclasses) and self.opclasses[i]:
                col_str += f" {self.opclasses[i]}"
            cols_with_opclass.append(col_str)

        col_list = ", ".join(cols_with_opclass)
        sql = (
            f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
            f'ON "{table_name}" USING {self._index_type} ({col_list})'
        )
        if self.condition:
            sql += f" WHERE ({self.condition})"
        sql += ";"
        return sql

    def _btree_fallback(self, table_name: str) -> str:
        """Fallback to B-tree index on non-PostgreSQL databases."""
        idx_name = self.name or f"idx_{table_name}_{'_'.join(self.fields)}"
        col_list = ", ".join(f'"{f}"' for f in self.fields)
        return (
            f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
            f'ON "{table_name}" ({col_list});'
        )

    def deconstruct(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "fields": self.fields,
            "name": self.name,
            "condition": self.condition,
            "opclasses": self.opclasses if self.opclasses else None,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(fields={self.fields!r}, name={self.name!r})"


class GinIndex(_PostgresOnlyIndex):
    """PostgreSQL GIN index — useful for full-text search, JSONB, arrays."""
    _index_type = "GIN"


class GistIndex(_PostgresOnlyIndex):
    """PostgreSQL GiST index — useful for geometric, range types, exclusion constraints."""
    _index_type = "GIST"


class BrinIndex(_PostgresOnlyIndex):
    """PostgreSQL BRIN index — useful for very large tables with natural ordering."""
    _index_type = "BRIN"


class HashIndex(_PostgresOnlyIndex):
    """PostgreSQL Hash index — useful for equality lookups only."""
    _index_type = "HASH"


class FunctionalIndex:
    """
    Index on an expression or function call.

    Usage:
        FunctionalIndex(
            expression='LOWER("email")',
            name="idx_users_email_lower",
        )
    """

    def __init__(
        self,
        *,
        expression: str,
        name: str,
        index_type: Optional[str] = None,
        condition: Optional[str] = None,
    ):
        self.expression = expression
        self.name = name
        self.index_type = index_type  # e.g., "GIN", "GIST", None for B-tree
        self.condition = condition

    def sql(self, table_name: str, dialect: str = "sqlite") -> str:
        using = f" USING {self.index_type}" if self.index_type and dialect != "sqlite" else ""
        sql = (
            f'CREATE INDEX IF NOT EXISTS "{self.name}" '
            f'ON "{table_name}"{using} ({self.expression})'
        )
        if self.condition:
            sql += f" WHERE ({self.condition})"
        sql += ";"
        return sql

    def deconstruct(self) -> Dict[str, Any]:
        return {
            "type": "FunctionalIndex",
            "expression": self.expression,
            "name": self.name,
            "index_type": self.index_type,
            "condition": self.condition,
        }

    def __repr__(self) -> str:
        return f"FunctionalIndex(name={self.name!r}, expression={self.expression!r})"
