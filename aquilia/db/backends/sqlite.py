"""
Aquilia DB Backend — SQLite adapter via aiosqlite.

This is the default backend. It wraps aiosqlite and implements
the full DatabaseAdapter interface including introspection.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    DatabaseAdapter,
    AdapterCapabilities,
    ColumnInfo,
    TableInfo,
)

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

logger = logging.getLogger("aquilia.db.backends.sqlite")

__all__ = ["SQLiteAdapter"]

# Savepoint name validation — prevent SQL injection
_SP_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class SQLiteAdapter(DatabaseAdapter):
    """
    SQLite adapter using aiosqlite.

    Features:
    - WAL journal mode for concurrent reads
    - Foreign key enforcement
    - Full introspection support
    - Savepoint-based nested transactions
    - SQL injection prevention on savepoint names
    """

    capabilities = AdapterCapabilities(
        supports_returning=False,
        supports_json_type=False,
        supports_arrays=False,
        supports_hstore=False,
        supports_citext=False,
        supports_upsert=True,
        supports_savepoints=True,
        supports_window_functions=True,
        supports_cte=True,
        param_style="qmark",
        null_ordering=False,
        name="sqlite",
    )

    def __init__(self):
        self._connection: Any = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._in_transaction = False

    async def connect(self, url: str, **options) -> None:
        if self._connected:
            return
        if aiosqlite is None:
            raise ImportError(
                "aiosqlite is required for SQLite backend. "
                "Install: pip install aiosqlite"
            )
        async with self._lock:
            if self._connected:
                return
            db_path = self._parse_url(url)
            self._connection = await aiosqlite.connect(db_path)
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.row_factory = aiosqlite.Row
            self._connected = True
            logger.info(f"SQLite connected: {db_path}")

    async def disconnect(self) -> None:
        if not self._connected:
            return
        async with self._lock:
            if self._connection:
                await self._connection.close()
                self._connection = None
            self._connected = False
            logger.info("SQLite disconnected")

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected")
        params = params or []
        cursor = await self._connection.execute(sql, params)
        if not self._in_transaction:
            await self._connection.commit()
        return cursor

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")
        await self._connection.executemany(sql, params_list)
        if not self._in_transaction:
            await self._connection.commit()

    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected")
        params = params or []
        cursor = await self._connection.execute(sql, params)
        rows = await cursor.fetchall()
        if rows and hasattr(rows[0], "keys"):
            return [dict(row) for row in rows]
        if cursor.description and rows:
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        return []

    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected")
        params = params or []
        cursor = await self._connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return dict(row)
        if cursor.description:
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
        return None

    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected")
        params = params or []
        cursor = await self._connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return next(iter(row.values()))
        return row[0]

    # ── Transactions ─────────────────────────────────────────────────

    async def begin(self) -> None:
        await self._connection.execute("BEGIN")
        self._in_transaction = True

    async def commit(self) -> None:
        await self._connection.commit()
        self._in_transaction = False

    async def rollback(self) -> None:
        await self._connection.rollback()
        self._in_transaction = False

    async def savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        await self._connection.execute(f'SAVEPOINT "{name}"')

    async def release_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        await self._connection.execute(f'RELEASE SAVEPOINT "{name}"')

    async def rollback_to_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        await self._connection.execute(f'ROLLBACK TO SAVEPOINT "{name}"')

    # ── Introspection ────────────────────────────────────────────────

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table_name],
        )
        return row is not None

    async def get_tables(self) -> List[str]:
        rows = await self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [r["name"] for r in rows]

    async def get_columns(self, table_name: str) -> List[ColumnInfo]:
        rows = await self.fetch_all(f'PRAGMA table_info("{table_name}")')
        columns = []
        for row in rows:
            columns.append(ColumnInfo(
                name=row["name"],
                data_type=row["type"],
                nullable=not row["notnull"],
                default=row["dflt_value"],
                primary_key=bool(row["pk"]),
            ))
        return columns

    async def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get index info for a table."""
        rows = await self.fetch_all(f'PRAGMA index_list("{table_name}")')
        indexes = []
        for row in rows:
            idx_name = row["name"]
            idx_info = await self.fetch_all(f'PRAGMA index_info("{idx_name}")')
            columns = [i["name"] for i in idx_info]
            indexes.append({
                "name": idx_name,
                "unique": bool(row["unique"]),
                "columns": columns,
            })
        return indexes

    async def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key info for a table."""
        rows = await self.fetch_all(f'PRAGMA foreign_key_list("{table_name}")')
        fks = []
        for row in rows:
            fks.append({
                "from_column": row["from"],
                "to_table": row["table"],
                "to_column": row["to"],
                "on_delete": row.get("on_delete", "NO ACTION"),
                "on_update": row.get("on_update", "NO ACTION"),
            })
        return fks

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def dialect(self) -> str:
        return "sqlite"

    @staticmethod
    def _parse_url(url: str) -> str:
        """Extract file path from sqlite URL."""
        for prefix in ("sqlite:///", "sqlite://"):
            if url.startswith(prefix):
                path = url[len(prefix):]
                return path or ":memory:"
        return url.replace("sqlite:", "").lstrip("/") or ":memory:"
