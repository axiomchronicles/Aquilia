"""
Aquilia DB Backend — MySQL/MariaDB adapter via aiomysql.

Provides full async MySQL support with connection pooling,
proper transaction management, and introspection.

Requires aiomysql:
    pip install aiomysql
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

logger = logging.getLogger("aquilia.db.backends.mysql")

__all__ = ["MySQLAdapter"]

# Try importing async MySQL driver
try:
    import aiomysql
    _HAS_AIOMYSQL = True
except ImportError:
    aiomysql = None  # type: ignore
    _HAS_AIOMYSQL = False

# Savepoint name validation
_SP_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class MySQLAdapter(DatabaseAdapter):
    """
    MySQL / MariaDB adapter using aiomysql with connection pooling.

    Features:
    - Connection pool via aiomysql.create_pool
    - Proper transaction management with a dedicated connection
    - Savepoint support with SQL injection prevention
    - Full introspection via information_schema
    - Automatic ``?`` → ``%s`` placeholder conversion

    Requires:
        pip install aiomysql
    """

    capabilities = AdapterCapabilities(
        supports_returning=False,  # MySQL < 8.0.21 doesn't support RETURNING
        supports_json_type=True,   # MySQL 5.7+
        supports_arrays=False,
        supports_hstore=False,
        supports_citext=False,
        supports_upsert=True,  # ON DUPLICATE KEY UPDATE
        supports_savepoints=True,
        supports_window_functions=True,   # MySQL 8.0+
        supports_cte=True,               # MySQL 8.0+
        param_style="format",            # %s
        null_ordering=False,
        name="mysql",
    )

    def __init__(self):
        self._pool: Any = None
        self._txn_conn: Any = None  # Dedicated connection for active transaction
        self._connected = False
        self._in_transaction = False

    async def connect(self, url: str, **options) -> None:
        if self._connected:
            return

        if not _HAS_AIOMYSQL:
            raise ImportError(
                "aiomysql is required for MySQL support.\n"
                "Install: pip install aiomysql"
            )

        conn_kwargs = _parse_mysql_url(url)
        conn_kwargs.update(options)
        conn_kwargs.setdefault("autocommit", True)
        self._pool = await aiomysql.create_pool(**conn_kwargs)
        self._connected = True
        logger.info(
            f"MySQL connected via aiomysql: "
            f"{conn_kwargs.get('host', '?')}:{conn_kwargs.get('port', 3306)}"
        )

    async def disconnect(self) -> None:
        if not self._connected:
            return
        # Release transaction connection if held
        if self._txn_conn is not None:
            try:
                await self._txn_conn.rollback()
            except Exception:
                pass
            self._txn_conn.close()
            self._txn_conn = None
            self._in_transaction = False
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
        self._connected = False
        logger.info("MySQL disconnected")

    def adapt_sql(self, sql: str) -> str:
        """Convert ``?`` placeholders to ``%s`` for MySQL (string-literal safe)."""
        result: list[str] = []
        in_string = False
        i = 0
        while i < len(sql):
            ch = sql[i]
            if ch == "'" and not in_string:
                in_string = True
                result.append(ch)
            elif ch == "'" and in_string:
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    result.append("''")
                    i += 2
                    continue
                in_string = False
                result.append(ch)
            elif ch == "?" and not in_string:
                result.append("%s")
            else:
                result.append(ch)
            i += 1
        return "".join(result)

    def _get_conn(self) -> Any:
        """Return the transaction connection if in txn, else None."""
        if self._in_transaction and self._txn_conn is not None:
            return self._txn_conn
        return None

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                return cur
        else:
            async with self._pool.acquire() as c:
                async with c.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(adapted_sql, params or ())
                    return cur

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            async with conn.cursor() as cur:
                await cur.executemany(adapted_sql, params_list)
        else:
            async with self._pool.acquire() as c:
                async with c.cursor() as cur:
                    await cur.executemany(adapted_sql, params_list)

    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                rows = await cur.fetchall()
                return list(rows)
        else:
            async with self._pool.acquire() as c:
                async with c.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(adapted_sql, params or ())
                    rows = await cur.fetchall()
                    return list(rows)

    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                row = await cur.fetchone()
                return dict(row) if row else None
        else:
            async with self._pool.acquire() as c:
                async with c.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(adapted_sql, params or ())
                    row = await cur.fetchone()
                    return dict(row) if row else None

    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        conn = self._get_conn()
        if conn is not None:
            async with conn.cursor() as cur:
                await cur.execute(adapted_sql, params or ())
                row = await cur.fetchone()
                return row[0] if row else None
        else:
            async with self._pool.acquire() as c:
                async with c.cursor() as cur:
                    await cur.execute(adapted_sql, params or ())
                    row = await cur.fetchone()
                    return row[0] if row else None

    # ── Transactions ─────────────────────────────────────────────────

    async def begin(self) -> None:
        """Acquire a dedicated connection and start a transaction."""
        if self._in_transaction:
            return
        conn = await self._pool.acquire()
        await conn.autocommit(False)
        await conn.begin()
        self._txn_conn = conn
        self._in_transaction = True

    async def commit(self) -> None:
        """Commit the transaction and release the connection."""
        if not self._in_transaction or self._txn_conn is None:
            return
        try:
            await self._txn_conn.commit()
            await self._txn_conn.autocommit(True)
        finally:
            self._in_transaction = False
            self._pool.release(self._txn_conn)
            self._txn_conn = None

    async def rollback(self) -> None:
        """Rollback the transaction and release the connection."""
        if not self._in_transaction or self._txn_conn is None:
            return
        try:
            await self._txn_conn.rollback()
            await self._txn_conn.autocommit(True)
        finally:
            self._in_transaction = False
            self._pool.release(self._txn_conn)
            self._txn_conn = None

    async def savepoint(self, name: str) -> None:
        """Create a savepoint (must be inside a transaction)."""
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot create savepoint outside a transaction")
        async with conn.cursor() as cur:
            await cur.execute(f'SAVEPOINT `{name}`')

    async def release_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot release savepoint outside a transaction")
        async with conn.cursor() as cur:
            await cur.execute(f'RELEASE SAVEPOINT `{name}`')

    async def rollback_to_savepoint(self, name: str) -> None:
        if not _SP_NAME_RE.match(name):
            raise ValueError(f"Invalid savepoint name: {name!r}")
        conn = self._get_conn()
        if conn is None:
            raise RuntimeError("Cannot rollback savepoint outside a transaction")
        async with conn.cursor() as cur:
            await cur.execute(f'ROLLBACK TO SAVEPOINT `{name}`')

    # ── Introspection ────────────────────────────────────────────────

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetch_one(
            "SELECT COUNT(*) AS cnt FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=?",
            [table_name],
        )
        return bool(row and row.get("cnt", 0) > 0)

    async def get_tables(self) -> List[str]:
        rows = await self.fetch_all(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=DATABASE() ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    async def get_columns(self, table_name: str) -> List[ColumnInfo]:
        rows = await self.fetch_all(
            "SELECT column_name, column_type, is_nullable, column_default, "
            "character_maximum_length "
            "FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=? "
            "ORDER BY ordinal_position",
            [table_name],
        )
        columns = []
        for row in rows:
            columns.append(ColumnInfo(
                name=row["column_name"],
                data_type=row["column_type"],
                nullable=row["is_nullable"] == "YES",
                default=row.get("column_default"),
                max_length=row.get("character_maximum_length"),
            ))
        return columns

    async def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get index info for a MySQL table."""
        rows = await self.fetch_all(
            "SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE "
            "FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? "
            "ORDER BY INDEX_NAME, SEQ_IN_INDEX",
            [table_name],
        )
        # Group by index name
        idx_map: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            name = row["INDEX_NAME"]
            if name not in idx_map:
                idx_map[name] = {
                    "name": name,
                    "unique": not bool(row["NON_UNIQUE"]),
                    "columns": [],
                }
            idx_map[name]["columns"].append(row["COLUMN_NAME"])
        return list(idx_map.values())

    async def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key info for a MySQL table."""
        rows = await self.fetch_all(
            "SELECT kcu.COLUMN_NAME AS from_column, "
            "kcu.REFERENCED_TABLE_NAME AS to_table, "
            "kcu.REFERENCED_COLUMN_NAME AS to_column, "
            "rc.DELETE_RULE AS on_delete, "
            "rc.UPDATE_RULE AS on_update "
            "FROM information_schema.KEY_COLUMN_USAGE kcu "
            "JOIN information_schema.REFERENTIAL_CONSTRAINTS rc "
            "ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME "
            "AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA "
            "WHERE kcu.TABLE_SCHEMA = DATABASE() AND kcu.TABLE_NAME = ? "
            "AND kcu.REFERENCED_TABLE_NAME IS NOT NULL",
            [table_name],
        )
        return [dict(r) for r in rows]

    @property
    def is_connected(self) -> bool:
        return self._connected and self._pool is not None

    @property
    def dialect(self) -> str:
        return "mysql"


# ── URL parsing helper ──────────────────────────────────────────────

def _parse_mysql_url(url: str) -> Dict[str, Any]:
    """
    Parse a mysql:// URL into connection kwargs.

    Expected format:
        mysql://user:password@host:port/dbname
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    kwargs: Dict[str, Any] = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "db": (parsed.path or "/").lstrip("/") or None,
    }
    if parsed.username:
        kwargs["user"] = parsed.username
    if parsed.password:
        kwargs["password"] = parsed.password

    return kwargs
