"""
Aquilia DB Backend — PostgreSQL adapter.

Uses psycopg2 (sync) or asyncpg (async) for PostgreSQL connections.
Falls back gracefully if drivers are not installed.

This is a placeholder/stub implementation — the interface is complete
but actual connections require psycopg2 or asyncpg to be installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    DatabaseAdapter,
    AdapterCapabilities,
    ColumnInfo,
)

logger = logging.getLogger("aquilia.db.backends.postgres")

__all__ = ["PostgresAdapter"]

# Try importing async postgres drivers
try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    asyncpg = None  # type: ignore
    _HAS_ASYNCPG = False

try:
    import psycopg2
    _HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None  # type: ignore
    _HAS_PSYCOPG2 = False


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL adapter.

    Requires asyncpg or psycopg2 to be installed:
        pip install asyncpg
        # or
        pip install psycopg2-binary
    """

    capabilities = AdapterCapabilities(
        supports_returning=True,
        supports_json_type=True,
        supports_arrays=True,
        supports_hstore=True,
        supports_citext=True,
        supports_upsert=True,
        supports_savepoints=True,
        supports_window_functions=True,
        supports_cte=True,
        param_style="numeric",  # $1, $2, ...
        null_ordering=True,
        name="postgresql",
    )

    def __init__(self):
        self._pool: Any = None
        self._connection: Any = None
        self._connected = False

    async def connect(self, url: str, **options) -> None:
        if self._connected:
            return

        if _HAS_ASYNCPG:
            self._pool = await asyncpg.create_pool(url, **options)
            self._connected = True
            logger.info(f"PostgreSQL connected via asyncpg: {_mask_url(url)}")
        elif _HAS_PSYCOPG2:
            raise NotImplementedError(
                "Sync psycopg2 adapter not yet implemented. "
                "Install asyncpg for async PostgreSQL support: pip install asyncpg"
            )
        else:
            raise ImportError(
                "No PostgreSQL driver available. Install one:\n"
                "  pip install asyncpg        (recommended, async)\n"
                "  pip install psycopg2-binary (sync fallback)"
            )

    async def disconnect(self) -> None:
        if not self._connected:
            return
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._connected = False
        logger.info("PostgreSQL disconnected")

    def adapt_sql(self, sql: str) -> str:
        """Convert ? placeholders to $1, $2, ... for PostgreSQL."""
        result = []
        param_idx = 0
        for char in sql:
            if char == "?":
                param_idx += 1
                result.append(f"${param_idx}")
            else:
                result.append(char)
        return "".join(result)

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            return await conn.execute(adapted_sql, *(params or []))

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            await conn.executemany(adapted_sql, params_list)

    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(adapted_sql, *(params or []))
            return [dict(row) for row in rows]

    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(adapted_sql, *(params or []))
            if row is None:
                return None
            return dict(row)

    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            return await conn.fetchval(adapted_sql, *(params or []))

    # ── Transactions ─────────────────────────────────────────────────

    async def begin(self) -> None:
        pass  # asyncpg uses connection.transaction()

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def savepoint(self, name: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"SAVEPOINT {name}")

    async def release_savepoint(self, name: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"RELEASE SAVEPOINT {name}")

    async def rollback_to_savepoint(self, name: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"ROLLBACK TO SAVEPOINT {name}")

    # ── Introspection ────────────────────────────────────────────────

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetch_one(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=?)",
            [table_name],
        )
        return bool(row and next(iter(row.values())))

    async def get_tables(self) -> List[str]:
        rows = await self.fetch_all(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    async def get_columns(self, table_name: str) -> List[ColumnInfo]:
        rows = await self.fetch_all(
            "SELECT column_name, data_type, is_nullable, column_default, "
            "character_maximum_length "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=? "
            "ORDER BY ordinal_position",
            [table_name],
        )
        columns = []
        for row in rows:
            columns.append(ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                nullable=row["is_nullable"] == "YES",
                default=row.get("column_default"),
                max_length=row.get("character_maximum_length"),
            ))
        return columns

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def dialect(self) -> str:
        return "postgresql"


def _mask_url(url: str) -> str:
    """Mask password in URL for logging."""
    if "@" in url:
        parts = url.split("@", 1)
        pre = parts[0]
        if ":" in pre:
            scheme_user = pre.rsplit(":", 1)[0]
            return f"{scheme_user}:***@{parts[1]}"
    return url
