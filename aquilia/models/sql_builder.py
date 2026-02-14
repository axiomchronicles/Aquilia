"""
Aquilia SQL Builder — safe, parameterized SQL generation.

Provides a fluent builder API that produces parameterized SQL
and bind-parameter lists. All user values are bound as parameters
to prevent SQL injection.

Usage:
    from aquilia.models.sql_builder import SQLBuilder

    sql, params = (
        SQLBuilder()
        .select("id", "name", "email")
        .from_table("users")
        .where("active = ?", True)
        .where("age > ?", 18)
        .order_by("name")
        .limit(10)
        .build()
    )
    # sql = 'SELECT "id", "name", "email" FROM "users" WHERE (active = ?) AND (age > ?) ORDER BY "name" ASC LIMIT 10'
    # params = [True, 18]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


__all__ = [
    "SQLBuilder",
    "InsertBuilder",
    "UpdateBuilder",
    "DeleteBuilder",
    "CreateTableBuilder",
]


class SQLBuilder:
    """
    SELECT query builder with safe parameter binding.
    """

    def __init__(self):
        self._columns: List[str] = []
        self._table: str = ""
        self._table_alias: Optional[str] = None
        self._joins: List[Tuple[str, str, str]] = []  # (type, table, on)
        self._join_params: List[Any] = []
        self._wheres: List[str] = []
        self._params: List[Any] = []
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._having_params: List[Any] = []
        self._order_by: List[str] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._distinct: bool = False

    def select(self, *columns: str) -> SQLBuilder:
        """Set columns to select."""
        self._columns = list(columns)
        return self

    def from_table(self, table: str, alias: Optional[str] = None) -> SQLBuilder:
        """Set the FROM table."""
        self._table = table
        self._table_alias = alias
        return self

    def distinct(self) -> SQLBuilder:
        """Add DISTINCT modifier."""
        self._distinct = True
        return self

    def join(
        self,
        table: str,
        on: str,
        join_type: str = "INNER",
        params: Optional[List[Any]] = None,
    ) -> SQLBuilder:
        """Add a JOIN clause."""
        self._joins.append((join_type, table, on))
        if params:
            self._join_params.extend(params)
        return self

    def left_join(self, table: str, on: str, params: Optional[List[Any]] = None) -> SQLBuilder:
        return self.join(table, on, "LEFT", params)

    def right_join(self, table: str, on: str, params: Optional[List[Any]] = None) -> SQLBuilder:
        return self.join(table, on, "RIGHT", params)

    def where(self, clause: str, *args: Any) -> SQLBuilder:
        """Add a WHERE condition with parameters."""
        self._wheres.append(clause)
        self._params.extend(args)
        return self

    def where_in(self, column: str, values: Sequence[Any]) -> SQLBuilder:
        """Add a WHERE ... IN (...) clause."""
        if not values:
            self._wheres.append("1 = 0")  # Always false
            return self
        placeholders = ", ".join("?" for _ in values)
        self._wheres.append(f'"{column}" IN ({placeholders})')
        self._params.extend(values)
        return self

    def group_by(self, *columns: str) -> SQLBuilder:
        """Add GROUP BY columns."""
        self._group_by.extend(columns)
        return self

    def having(self, clause: str, *args: Any) -> SQLBuilder:
        """Add HAVING condition."""
        self._having.append(clause)
        self._having_params.extend(args)
        return self

    def order_by(self, *fields: str) -> SQLBuilder:
        """
        Add ORDER BY clause.

        Prefix with '-' for DESC: order_by("-created_at", "name")
        """
        for f in fields:
            if f.startswith("-"):
                self._order_by.append(f'"{f[1:]}" DESC')
            else:
                self._order_by.append(f'"{f}" ASC')
        return self

    def limit(self, n: int) -> SQLBuilder:
        self._limit_val = n
        return self

    def offset(self, n: int) -> SQLBuilder:
        self._offset_val = n
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """
        Build the final SQL string and parameter list.

        Returns:
            Tuple of (sql_string, params_list)
        """
        parts: List[str] = []
        params: List[Any] = []

        # SELECT
        distinct = "DISTINCT " if self._distinct else ""
        if self._columns:
            cols = ", ".join(
                f'"{c}"' if not _is_raw(c) else c
                for c in self._columns
            )
        else:
            cols = "*"
        parts.append(f"SELECT {distinct}{cols}")

        # FROM
        table_ref = f'"{self._table}"'
        if self._table_alias:
            table_ref += f' "{self._table_alias}"'
        parts.append(f"FROM {table_ref}")

        # JOINs
        for join_type, join_table, join_on in self._joins:
            parts.append(f'{join_type} JOIN "{join_table}" ON {join_on}')
        params.extend(self._join_params)

        # WHERE
        if self._wheres:
            parts.append("WHERE " + " AND ".join(f"({w})" for w in self._wheres))
            params.extend(self._params)

        # GROUP BY
        if self._group_by:
            cols = ", ".join(f'"{c}"' for c in self._group_by)
            parts.append(f"GROUP BY {cols}")

        # HAVING
        if self._having:
            parts.append("HAVING " + " AND ".join(f"({h})" for h in self._having))
            params.extend(self._having_params)

        # ORDER BY
        if self._order_by:
            parts.append("ORDER BY " + ", ".join(self._order_by))

        # LIMIT / OFFSET
        if self._limit_val is not None:
            parts.append(f"LIMIT {int(self._limit_val)}")
        if self._offset_val is not None:
            parts.append(f"OFFSET {int(self._offset_val)}")

        return " ".join(parts), params

    def build_count(self) -> Tuple[str, List[Any]]:
        """Build a COUNT(*) version of this query."""
        parts: List[str] = ["SELECT COUNT(*)"]
        params: List[Any] = []

        table_ref = f'"{self._table}"'
        if self._table_alias:
            table_ref += f' "{self._table_alias}"'
        parts.append(f"FROM {table_ref}")

        for join_type, join_table, join_on in self._joins:
            parts.append(f'{join_type} JOIN "{join_table}" ON {join_on}')
        params.extend(self._join_params)

        if self._wheres:
            parts.append("WHERE " + " AND ".join(f"({w})" for w in self._wheres))
            params.extend(self._params)

        return " ".join(parts), params


class InsertBuilder:
    """INSERT query builder."""

    def __init__(self, table: str):
        self._table = table
        self._columns: List[str] = []
        self._values: List[Any] = []
        self._returning: Optional[str] = None

    def columns(self, *cols: str) -> InsertBuilder:
        self._columns = list(cols)
        return self

    def values(self, *vals: Any) -> InsertBuilder:
        self._values = list(vals)
        return self

    def from_dict(self, data: Dict[str, Any]) -> InsertBuilder:
        """Set columns and values from a dict."""
        self._columns = list(data.keys())
        self._values = list(data.values())
        return self

    def returning(self, column: str) -> InsertBuilder:
        """Add RETURNING clause (PostgreSQL)."""
        self._returning = column
        return self

    def build(self) -> Tuple[str, List[Any]]:
        col_names = ", ".join(f'"{c}"' for c in self._columns)
        placeholders = ", ".join("?" for _ in self._columns)
        sql = f'INSERT INTO "{self._table}" ({col_names}) VALUES ({placeholders})'
        if self._returning:
            sql += f' RETURNING "{self._returning}"'
        return sql, list(self._values)

    def build_many(self, rows: List[Dict[str, Any]]) -> Tuple[str, List[List[Any]]]:
        """Build INSERT for executemany."""
        if not rows:
            raise ValueError("No rows to insert")
        cols = list(rows[0].keys())
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        sql = f'INSERT INTO "{self._table}" ({col_names}) VALUES ({placeholders})'
        params_list = [[row.get(c) for c in cols] for row in rows]
        return sql, params_list


class UpdateBuilder:
    """UPDATE query builder."""

    def __init__(self, table: str):
        self._table = table
        self._sets: Dict[str, Any] = {}
        self._wheres: List[str] = []
        self._params: List[Any] = []

    def set(self, **kwargs: Any) -> UpdateBuilder:
        self._sets.update(kwargs)
        return self

    def set_dict(self, data: Dict[str, Any]) -> UpdateBuilder:
        self._sets.update(data)
        return self

    def where(self, clause: str, *args: Any) -> UpdateBuilder:
        self._wheres.append(clause)
        self._params.extend(args)
        return self

    def build(self) -> Tuple[str, List[Any]]:
        set_parts = [f'"{k}" = ?' for k in self._sets]
        set_params = list(self._sets.values())
        sql = f'UPDATE "{self._table}" SET {", ".join(set_parts)}'
        params = set_params.copy()
        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)
        return sql, params


class DeleteBuilder:
    """DELETE query builder."""

    def __init__(self, table: str):
        self._table = table
        self._wheres: List[str] = []
        self._params: List[Any] = []

    def where(self, clause: str, *args: Any) -> DeleteBuilder:
        self._wheres.append(clause)
        self._params.extend(args)
        return self

    def build(self) -> Tuple[str, List[Any]]:
        sql = f'DELETE FROM "{self._table}"'
        params = self._params.copy()
        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
        return sql, params


class CreateTableBuilder:
    """CREATE TABLE DDL builder."""

    def __init__(self, table: str, if_not_exists: bool = True):
        self._table = table
        self._if_not_exists = if_not_exists
        self._columns: List[str] = []
        self._constraints: List[str] = []

    def column(self, definition: str) -> CreateTableBuilder:
        self._columns.append(definition)
        return self

    def constraint(self, definition: str) -> CreateTableBuilder:
        self._constraints.append(definition)
        return self

    def build(self) -> str:
        ine = "IF NOT EXISTS " if self._if_not_exists else ""
        body = ",\n  ".join(self._columns + self._constraints)
        return f'CREATE TABLE {ine}"{self._table}" (\n  {body}\n);'


def _is_raw(col: str) -> bool:
    """Check if a column reference is a raw expression (contains parens, *, etc)."""
    return any(c in col for c in ("(", ")", "*", " ", "."))
