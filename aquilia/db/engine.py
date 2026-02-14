"""
Aquilia Database Engine — async-first, SQLite-by-default.

Provides:
- AquiliaDatabase: async connection manager with transaction support
- SQLite driver via aiosqlite
- Full integration with AquilaFaults and DI container
- Lifecycle hooks for startup/shutdown
- Planned: Postgres (asyncpg), MySQL (aiomysql)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple

from ..faults.domains import (
    DatabaseConnectionFault,
    QueryFault,
    SchemaFault,
)
from ..di.decorators import service

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

logger = logging.getLogger("aquilia.db")


# ── Backward-compatible alias ────────────────────────────────────────────────
# Legacy code that catches ``DatabaseError`` will still work because
# ``DatabaseConnectionFault`` is a ``Fault`` (and thus an ``Exception``).
DatabaseError = DatabaseConnectionFault


@service(scope="app", name="AquiliaDatabase")
class AquiliaDatabase:
    """
    Async database engine for Aquilia.

    SQLite-first implementation using aiosqlite.
    All operations are async and use parameterized queries.

    Integrates with:
    - **AquilaFaults**: raises ``DatabaseConnectionFault``, ``QueryFault``,
      ``SchemaFault`` instead of bare exceptions.
    - **DI**: decorated with ``@service(scope="app")``; resolvable from
      Aquilia's dependency-injection container.
    - **Lifecycle**: exposes ``on_startup`` / ``on_shutdown`` hooks for the
      ``LifecycleCoordinator``.

    Usage:
        db = AquiliaDatabase("sqlite:///app.db")
        await db.connect()
        rows = await db.fetch_all("SELECT * FROM users WHERE active = ?", [True])
        await db.disconnect()
    """

    __slots__ = (
        "_url",
        "_driver",
        "_connection",
        "_connected",
        "_lock",
        "_options",
        "_in_transaction",
    )

    def __init__(self, url: str = "sqlite:///db.sqlite3", **options: Any):
        """
        Initialize database.

        Args:
            url: Database URL. Supported schemes:
                 - sqlite:///path/to/db.sqlite3
                 - sqlite:///:memory:
                 - (future) postgresql://user:pass@host/db
                 - (future) mysql://user:pass@host/db
            **options: Driver-specific options
        """
        self._url = url
        self._driver = self._detect_driver(url)
        self._connection: Any = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._options = options
        self._in_transaction = False

    @staticmethod
    def _detect_driver(url: str) -> str:
        """Detect database driver from URL scheme."""
        if url.startswith("sqlite"):
            return "sqlite"
        elif url.startswith("postgresql") or url.startswith("postgres"):
            return "postgresql"
        elif url.startswith("mysql"):
            return "mysql"
        else:
            raise DatabaseConnectionFault(
                url=url,
                reason=f"Unsupported database URL scheme: {url}",
            )

    def _parse_sqlite_path(self) -> str:
        """Extract file path from sqlite URL."""
        # sqlite:///path → path
        # sqlite:///:memory: → :memory:
        prefix = "sqlite:///"
        if self._url.startswith(prefix):
            return self._url[len(prefix):]
        prefix2 = "sqlite://"
        if self._url.startswith(prefix2):
            path = self._url[len(prefix2):]
            return path if path else ":memory:"
        return self._url.replace("sqlite:", "").lstrip("/")

    # ── Lifecycle hooks ──────────────────────────────────────────────

    async def on_startup(self) -> None:
        """Lifecycle hook — called by ``LifecycleCoordinator`` at app start."""
        await self.connect()

    async def on_shutdown(self) -> None:
        """Lifecycle hook — called by ``LifecycleCoordinator`` at app stop."""
        await self.disconnect()

    # ── Connection management ────────────────────────────────────────

    async def connect(self) -> None:
        """Open database connection."""
        if self._connected:
            return

        async with self._lock:
            if self._connected:
                return

            try:
                if self._driver == "sqlite":
                    if aiosqlite is None:
                        raise DatabaseConnectionFault(
                            url=self._url,
                            reason=(
                                "aiosqlite is required for SQLite support. "
                                "Install it: pip install aiosqlite"
                            ),
                        )
                    db_path = self._parse_sqlite_path()
                    self._connection = await aiosqlite.connect(db_path)
                    # Enable WAL mode for better concurrent read performance
                    await self._connection.execute("PRAGMA journal_mode=WAL")
                    # Enable foreign keys
                    await self._connection.execute("PRAGMA foreign_keys=ON")
                    self._connection.row_factory = aiosqlite.Row
                    logger.info(f"Connected to SQLite: {db_path}")

                elif self._driver == "postgresql":
                    raise DatabaseConnectionFault(
                        url=self._url,
                        reason=(
                            "PostgreSQL support planned but not yet implemented. "
                            "Use SQLite for now."
                        ),
                    )
                elif self._driver == "mysql":
                    raise DatabaseConnectionFault(
                        url=self._url,
                        reason=(
                            "MySQL support planned but not yet implemented. "
                            "Use SQLite for now."
                        ),
                    )

                self._connected = True
            except DatabaseConnectionFault:
                raise
            except Exception as exc:
                raise DatabaseConnectionFault(
                    url=self._url,
                    reason=str(exc),
                ) from exc

    async def disconnect(self) -> None:
        """Close database connection."""
        if not self._connected:
            return
        async with self._lock:
            if not self._connected:
                return
            try:
                if self._connection:
                    await self._connection.close()
                    self._connection = None
                self._connected = False
                logger.info("Database disconnected")
            except Exception as exc:
                raise DatabaseConnectionFault(
                    url=self._url,
                    reason=f"Disconnect failed: {exc}",
                ) from exc

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """
        Async context manager for transactions.

        Usage:
            async with db.transaction():
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")
        """
        if not self._connected:
            await self.connect()

        if self._driver == "sqlite":
            # SQLite: use BEGIN/COMMIT/ROLLBACK
            await self._connection.execute("BEGIN")
            self._in_transaction = True
            try:
                yield
                await self._connection.commit()
            except Exception:
                await self._connection.rollback()
                raise
            finally:
                self._in_transaction = False
        else:
            # Future: PostgreSQL/MySQL transaction
            yield

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        """
        Execute a SQL statement.

        Args:
            sql: SQL query with ? placeholders
            params: Parameter values

        Returns:
            Cursor for INSERT/UPDATE/DELETE (exposes lastrowid, rowcount)

        Raises:
            QueryFault: When query execution fails
        """
        if not self._connected:
            await self.connect()

        if params is None:
            params = []
        try:
            cursor = await self._connection.execute(sql, params)
            if not self._in_transaction:
                await self._connection.commit()
            return cursor
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="execute",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        """Execute a SQL statement with multiple parameter sets."""
        if not self._connected:
            await self.connect()
        try:
            await self._connection.executemany(sql, params_list)
            if not self._in_transaction:
                await self._connection.commit()
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="execute_many",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    async def fetch_all(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return all rows as dicts.

        Args:
            sql: SELECT query
            params: Parameter values

        Returns:
            List of row dicts

        Raises:
            QueryFault: When query execution fails
        """
        if not self._connected:
            await self.connect()

        if params is None:
            params = []
        try:
            cursor = await self._connection.execute(sql, params)
            rows = await cursor.fetchall()
            if rows and hasattr(rows[0], "keys"):
                return [dict(row) for row in rows]
            # Fallback: use cursor.description
            if cursor.description and rows:
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row)) for row in rows]
            return []
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="fetch_all",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    async def fetch_one(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return first row as dict, or None.

        Raises:
            QueryFault: When query execution fails
        """
        if not self._connected:
            await self.connect()

        if params is None:
            params = []
        try:
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
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="fetch_one",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    async def fetch_val(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> Any:
        """
        Execute query and return scalar value from first row, first column.

        Raises:
            QueryFault: When query execution fails
        """
        if not self._connected:
            await self.connect()

        if params is None:
            params = []
        try:
            cursor = await self._connection.execute(sql, params)
            row = await cursor.fetchone()
            if row is None:
                return None
            if isinstance(row, dict):
                return next(iter(row.values()))
            return row[0]
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="fetch_val",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        if self._driver == "sqlite":
            row = await self.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [table_name],
            )
            return row is not None
        return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def url(self) -> str:
        return self._url

    @property
    def driver(self) -> str:
        return self._driver


# ── Module-level singleton accessor ─────────────────────────────────────────

_default_database: Optional[AquiliaDatabase] = None


def get_database() -> AquiliaDatabase:
    """Get the default database instance."""
    global _default_database
    if _default_database is None:
        raise DatabaseConnectionFault(
            url="<not configured>",
            reason=(
                "No database configured. Call configure_database() first "
                "or set database URL in aquilia config."
            ),
        )
    return _default_database


def configure_database(url: str = "sqlite:///db.sqlite3", **options: Any) -> AquiliaDatabase:
    """
    Configure and return the default database.

    Args:
        url: Database connection URL
        **options: Driver-specific options

    Returns:
        AquiliaDatabase instance
    """
    global _default_database
    _default_database = AquiliaDatabase(url, **options)
    return _default_database


def set_database(db: AquiliaDatabase) -> None:
    """Set an externally-created database as the default."""
    global _default_database
    _default_database = db
