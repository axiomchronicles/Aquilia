"""
Aquilia DB Backend — MySQL adapter.

Uses pymysql (sync) or aiomysql (async) for MySQL/MariaDB connections.
Falls back gracefully if drivers are not installed.

This is a placeholder/stub implementation — the interface is complete
but actual connections require pymysql or aiomysql to be installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    DatabaseAdapter,
    AdapterCapabilities,
    ColumnInfo,
)

logger = logging.getLogger("aquilia.db.backends.mysql")

__all__ = ["MySQLAdapter"]

# Try importing async MySQL drivers
try:
    import aiomysql
    _HAS_AIOMYSQL = True
except ImportError:
    aiomysql = None  # type: ignore
    _HAS_AIOMYSQL = False

try:
    import pymysql
    _HAS_PYMYSQL = True
except ImportError:
    pymysql = None  # type: ignore
    _HAS_PYMYSQL = False


class MySQLAdapter(DatabaseAdapter):
    """
    MySQL / MariaDB adapter.

    Requires aiomysql or pymysql to be installed:
        pip install aiomysql
        # or
        pip install pymysql
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
        self._connected = False

    async def connect(self, url: str, **options) -> None:
        if self._connected:
            return

        if _HAS_AIOMYSQL:
            conn_kwargs = _parse_mysql_url(url)
            conn_kwargs.update(options)
            self._pool = await aiomysql.create_pool(**conn_kwargs)
            self._connected = True
            logger.info(f"MySQL connected via aiomysql: {conn_kwargs.get('host', '?')}:{conn_kwargs.get('port', 3306)}")
        elif _HAS_PYMYSQL:
            raise NotImplementedError(
                "Sync pymysql adapter not yet implemented. "
                "Install aiomysql for async MySQL support: pip install aiomysql"
            )
        else:
            raise ImportError(
                "No MySQL driver available. Install one:\n"
                "  pip install aiomysql  (recommended, async)\n"
                "  pip install pymysql   (sync fallback)"
            )

    async def disconnect(self) -> None:
        if not self._connected:
            return
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
        self._connected = False
        logger.info("MySQL disconnected")

    def adapt_sql(self, sql: str) -> str:
        """Convert ? placeholders to %s for MySQL."""
        return sql.replace("?", "%s")

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                await conn.commit()
                return cur.lastrowid

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(adapted_sql, params_list)
                await conn.commit()

    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                rows = await cur.fetchall()
                return list(rows)

    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(adapted_sql, params or ())
                row = await cur.fetchone()
                return dict(row) if row else None

    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        if not self._connected:
            raise RuntimeError("Not connected to MySQL")
        adapted_sql = self.adapt_sql(sql)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(adapted_sql, params or ())
                row = await cur.fetchone()
                return row[0] if row else None

    # ── Transactions ─────────────────────────────────────────────────

    async def begin(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.begin()

    async def commit(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.commit()

    async def rollback(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.rollback()

    async def savepoint(self, name: str) -> None:
        await self.execute(f"SAVEPOINT {name}")

    async def release_savepoint(self, name: str) -> None:
        await self.execute(f"RELEASE SAVEPOINT {name}")

    async def rollback_to_savepoint(self, name: str) -> None:
        await self.execute(f"ROLLBACK TO SAVEPOINT {name}")

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

    @property
    def is_connected(self) -> bool:
        return self._connected

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
