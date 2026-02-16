"""
Aquilia DB Backend — PostgreSQL adapter via asyncpg.

Provides full async PostgreSQL support with connection pooling,
proper transaction management, and introspection.

Requires asyncpg:
    pip install asyncpg
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    DatabaseAdapter,
    AdapterCapabilities,
    ColumnInfo,
)

logger = logging.getLogger("aquilia.db.backends.postgres")

__all__ = ["PostgresAdapter"]

# Try importing async postgres driver
try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    asyncpg = None  # type: ignore
    _HAS_ASYNCPG = False

# Savepoint name validation
_SP_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL adapter using asyncpg with connection pooling.

    Features:
    - Connection pool via asyncpg.create_pool
    - Proper transaction management with a dedicated connection
    - Savepoint support with SQL injection prevention
    - Full introspection via information_schema
    - Automatic ``?`` → ``$N`` placeholder conversion (string-literal safe)

    Requires:
        pip install asyncpg
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
        self._txn_conn: Any = None  # Dedicated connection for active transaction
        self._txn_obj: Any = None   # asyncpg Transaction object
        self._connected = False
        self._in_transaction = False

    async def connect(self, url: str, **options) -> None:
        if self._connected:
            return

        if not _HAS_ASYNCPG:
            raise ImportError(
                "asyncpg is required for PostgreSQL support.\n"
                "Install: pip install asyncpg"
            )

        min_size = options.pop("pool_min_size", 2)
        max_size = options.pop("pool_max_size", 10)
        self._pool = await asyncpg.create_pool(
            url, min_size=min_size, max_size=max_size, **options
        )
        self._connected = True
        logger.info(f"PostgreSQL connected via asyncpg: {_mask_url(url)}")

    async def disconnect(self) -> None:
        if not self._connected:
            return
        # Release transaction connection if held
        if self._txn_conn is not None:
            try:
                if self._txn_obj is not None:
                    await self._txn_obj.rollback()
            except Exception:
                pass
            try:
                await self._txn_conn.close()
            except Exception:
                pass
            self._txn_conn = None
            self._txn_obj = None
            self._in_transaction = False
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._connected = False
        logger.info("PostgreSQL disconnected")

    def adapt_sql(self, sql: str) -> str:
        """
        Convert ``?`` placeholders to ``$1, $2, ...`` for asyncpg.

        String-literal safe — skips ``?`` inside single-quoted strings.
        """
        result: list[str] = []
        param_idx = 0
        in_string = False
        i = 0
        while i < len(sql):
            ch = sql[i]
            if ch == "'" and not in_string:
                in_string = True
                result.append(ch)
            elif ch == "'" and in_string:
                # Check for escaped quote ''
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    result.append("''")
                    i += 2
                    continue
                in_string = False
                result.append(ch)
            elif ch == "?" and not in_string:
                param_idx += 1
                result.append(f"${param_idx}")
            else:
                result.append(ch)
            i += 1
        return "".join(result)

    def _get_conn(self) -> Any:
        """Return the transaction connection if in txn, else raise."""
        if self._in_transaction and self._txn_conn is not None:
            return self._txn_conn
        return None

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            return await conn.execute(adapted_sql, *(params or []))
        async with self._pool.acquire() as c:
            return await c.execute(adapted_sql, *(params or []))

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            await conn.executemany(adapted_sql, params_list)
        else:
            async with self._pool.acquire() as c:
                await c.executemany(adapted_sql, params_list)

    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            rows = await conn.fetch(adapted_sql, *(params or []))
        else:
            async with self._pool.acquire() as c:
                rows = await c.fetch(adapted_sql, *(params or []))
        return [dict(row) for row in rows]

    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            row = await conn.fetchrow(adapted_sql, *(params or []))
        else:
            async with self._pool.acquire() as c:
                row = await c.fetchrow(adapted_sql, *(params or []))
        if row is None:
            return None
        return dict(row)

    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            return await conn.fetchval(adapted_sql, *(params or []))
        async with self._pool.acquire() as c:
            return await c.fetchval(adapted_sql, *(params or []))

    # ── Transactions ─────────────────────────────────────────────────

    async def begin(self) -> None:
        """Acquire a dedicated connection and start a transaction."""
        if self._in_transaction:
            return
        self._txn_conn = await self._pool.acquire()
        self._txn_obj = self._txn_conn.transaction()
        await self._txn_obj.start()
        self._in_transaction = True

    async def commit(self) -> None:
        """Commit the transaction and release the connection."""
        if not self._in_transaction or self._txn_obj is None:
            return
        try:
            await self._txn_obj.commit()
        finally:
            self._in_transaction = False
            await self._pool.release(self._txn_conn)
            self._txn_conn = None
            self._txn_obj = None

    async def rollback(self) -> None:
        """Rollback the transaction and release the connection."""
        if not self._in_transaction or self._txn_obj is None:
            return
        try:
            await self._txn_obj.rollback()
        finally:
            self._in_transaction = False
            await self._pool.release(self._txn_conn)
            self._txn_conn = None
            self._txn_obj = None

    async def savepoint(self, name: str) -> None:
        """Create a savepoint (must be inside a transaction)."""
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot create savepoint outside a transaction")
        await conn.execute(f'SAVEPOINT "{name}"')

    async def release_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot release savepoint outside a transaction")
        await conn.execute(f'RELEASE SAVEPOINT "{name}"')

    async def rollback_to_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot rollback savepoint outside a transaction")
        await conn.execute(f'ROLLBACK TO SAVEPOINT "{name}"')

    # ── Introspection ────────────────────────────────────────────────

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetch_one(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=?) AS e",
            [table_name],
        )
        return bool(row and row.get("e"))

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

    async def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get index info for a PostgreSQL table."""
        rows = await self.fetch_all(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = ?",
            [table_name],
        )
        indexes = []
        for row in rows:
            indexes.append({
                "name": row["indexname"],
                "definition": row["indexdef"],
                "unique": "UNIQUE" in row.get("indexdef", "").upper(),
            })
        return indexes

    async def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key info for a PostgreSQL table."""
        rows = await self.fetch_all(
            "SELECT kcu.column_name AS from_column, "
            "ccu.table_name AS to_table, "
            "ccu.column_name AS to_column, "
            "rc.delete_rule AS on_delete, "
            "rc.update_rule AS on_update "
            "FROM information_schema.key_column_usage kcu "
            "JOIN information_schema.referential_constraints rc "
            "ON kcu.constraint_name = rc.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu "
            "ON rc.unique_constraint_name = ccu.constraint_name "
            "WHERE kcu.table_schema = 'public' AND kcu.table_name = ?",
            [table_name],
        )
        return [dict(r) for r in rows]

    @property
    def is_connected(self) -> bool:
        return self._connected and self._pool is not None

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
