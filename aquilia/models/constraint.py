"""
Aquilia Model Constraints — CheckConstraint, ExclusionConstraint.

Extends the existing Index / UniqueConstraint from fields_module with
additional constraint types for advanced database constraints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "CheckConstraint",
    "ExclusionConstraint",
    "Deferrable",
]


class Deferrable:
    """Constraint deferral modes for PostgreSQL."""
    DEFERRED = "DEFERRABLE INITIALLY DEFERRED"
    IMMEDIATE = "DEFERRABLE INITIALLY IMMEDIATE"


class CheckConstraint:
    """
    SQL CHECK constraint.

    Usage in Meta:
        class Meta:
            constraints = [
                CheckConstraint(
                    check="age >= 0 AND age <= 200",
                    name="valid_age",
                ),
                CheckConstraint(
                    check="price > 0",
                    name="positive_price",
                ),
            ]
    """

    def __init__(
        self,
        *,
        check: str,
        name: str,
        violation_error_message: Optional[str] = None,
    ):
        self.check = check
        self.name = name
        self.violation_error_message = violation_error_message or f"Constraint {name!r} violated"

    def sql(self, table_name: str, dialect: str = "sqlite") -> str:
        """Generate the constraint SQL for CREATE TABLE body."""
        return f'CONSTRAINT "{self.name}" CHECK ({self.check})'

    def sql_alter_add(self, table_name: str, dialect: str = "sqlite") -> str:
        """Generate ALTER TABLE ADD CONSTRAINT SQL."""
        return (
            f'ALTER TABLE "{table_name}" '
            f'ADD CONSTRAINT "{self.name}" CHECK ({self.check});'
        )

    def sql_alter_drop(self, table_name: str, dialect: str = "sqlite") -> str:
        """Generate ALTER TABLE DROP CONSTRAINT SQL."""
        if dialect == "sqlite":
            # SQLite doesn't support ALTER TABLE DROP CONSTRAINT
            return f"-- SQLite: Cannot drop CHECK constraint '{self.name}' via ALTER TABLE"
        return f'ALTER TABLE "{table_name}" DROP CONSTRAINT "{self.name}";'

    def deconstruct(self) -> Dict[str, Any]:
        return {
            "type": "CheckConstraint",
            "check": self.check,
            "name": self.name,
        }

    def __repr__(self) -> str:
        return f"CheckConstraint(name={self.name!r}, check={self.check!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CheckConstraint):
            return NotImplemented
        return self.name == other.name and self.check == other.check

    def __hash__(self) -> int:
        return hash(("CheckConstraint", self.name))


class ExclusionConstraint:
    """
    PostgreSQL EXCLUDE constraint.

    Usage in Meta:
        class Meta:
            constraints = [
                ExclusionConstraint(
                    name="no_overlapping_reservations",
                    expressions=[
                        ("room_id", "="),
                        ("during", "&&"),
                    ],
                    index_type="GIST",
                ),
            ]

    Note: Only supported on PostgreSQL with appropriate extensions.
    """

    def __init__(
        self,
        *,
        name: str,
        expressions: Sequence[Tuple[str, str]],
        index_type: str = "GIST",
        condition: Optional[str] = None,
        deferrable: Optional[str] = None,
        violation_error_message: Optional[str] = None,
    ):
        self.name = name
        self.expressions = list(expressions)
        self.index_type = index_type
        self.condition = condition
        self.deferrable = deferrable
        self.violation_error_message = (
            violation_error_message or f"Exclusion constraint {name!r} violated"
        )

    def sql(self, table_name: str, dialect: str = "sqlite") -> str:
        """Generate constraint SQL (PostgreSQL only)."""
        if dialect == "sqlite":
            return f"-- EXCLUDE constraints not supported on SQLite ({self.name})"

        expr_parts = ", ".join(
            f'"{col}" WITH {op}' for col, op in self.expressions
        )
        sql = f'CONSTRAINT "{self.name}" EXCLUDE USING {self.index_type} ({expr_parts})'
        if self.condition:
            sql += f" WHERE ({self.condition})"
        if self.deferrable:
            sql += f" {self.deferrable}"
        return sql

    def sql_alter_add(self, table_name: str, dialect: str = "sqlite") -> str:
        if dialect == "sqlite":
            return f"-- EXCLUDE constraints not supported on SQLite ({self.name})"
        constraint_body = self.sql(table_name, dialect)
        return f'ALTER TABLE "{table_name}" ADD {constraint_body};'

    def sql_alter_drop(self, table_name: str, dialect: str = "sqlite") -> str:
        if dialect == "sqlite":
            return f"-- Cannot drop EXCLUDE constraint on SQLite ({self.name})"
        return f'ALTER TABLE "{table_name}" DROP CONSTRAINT "{self.name}";'

    def deconstruct(self) -> Dict[str, Any]:
        return {
            "type": "ExclusionConstraint",
            "name": self.name,
            "expressions": self.expressions,
            "index_type": self.index_type,
            "condition": self.condition,
        }

    def __repr__(self) -> str:
        return f"ExclusionConstraint(name={self.name!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ExclusionConstraint):
            return NotImplemented
        return self.name == other.name and self.expressions == other.expressions

    def __hash__(self) -> int:
        return hash(("ExclusionConstraint", self.name))
