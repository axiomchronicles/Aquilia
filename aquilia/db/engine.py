"""
Aquilia Database Engine — async-first, multi-backend, production-ready.

Provides:
- AquiliaDatabase: async connection manager delegating to backend adapters
- SQLite (aiosqlite), PostgreSQL (asyncpg), MySQL (aiomysql) backends
- Full integration with AquilaFaults and DI container
- Lifecycle hooks for startup/shutdown
- Connection health checks and reconnection
- Multi-database routing support
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple, Type

from ..faults.domains import (
    DatabaseConnectionFault,
    QueryFault,
    SchemaFault,
)
from ..di.decorators import service
from .backends.base import DatabaseAdapter, AdapterCapabilities, ColumnInfo, TableInfo

logger = logging.getLogger("aquilia.db")


# ── Backward-compatible alias ────────────────────────────────────────────────
DatabaseError = DatabaseConnectionFault

# Sanitize savepoint names to prevent SQL injection
_SP_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _sanitize_savepoint(name: str) -> str:
    """Validate savepoint names — only alphanumeric + underscore allowed."""
    if not _SP_NAME_RE.match(name):
        raise QueryFault(
            model="<transaction>",
            operation="savepoint",
            reason=f"Invalid savepoint name: {name!r}. Use alphanumeric + underscore only.",
        )
    return name


def _create_adapter(driver: str) -> DatabaseAdapter:
    """Factory — instantiate the correct backend adapter."""
    if driver == "sqlite":
        from .backends.sqlite import SQLiteAdapter
        return SQLiteAdapter()
    elif driver == "postgresql":
        from .backends.postgres import PostgresAdapter
        return PostgresAdapter()
    elif driver == "mysql":
        from .backends.mysql import MySQLAdapter
        return MySQLAdapter()
    else:
        raise DatabaseConnectionFault(
            url=f"<{driver}>",
            reason=f"No adapter registered for driver: {driver}",
        )


@service(scope="app", name="AquiliaDatabase")
class AquiliaDatabase:
    """
    Async database engine for Aquilia.

    Delegates all operations to the appropriate backend adapter
    (SQLite, PostgreSQL, or MySQL). All operations are async and
    use parameterized queries with ``?`` placeholders — the adapter
    translates to the backend's native param style automatically.

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

        # PostgreSQL:
        db = AquiliaDatabase("postgresql://user:pass@localhost/mydb")
        await db.connect()

        # MySQL:
        db = AquiliaDatabase("mysql://user:pass@localhost/mydb")
        await db.connect()
    """

    __slots__ = (
        "_url",
        "_driver",
        "_adapter",
        "_connected",
        "_lock",
        "_options",
        "_in_transaction",
        "_last_activity",
        "_connect_retries",
        "_connect_retry_delay",
    )

    def __init__(self, url: str = "sqlite:///db.sqlite3", **options: Any):
        """
        Initialize database engine.

        Args:
            url: Database URL. Supported schemes:
                 - sqlite:///path/to/db.sqlite3
                 - sqlite:///:memory:
                 - postgresql://user:pass@host/db
                 - mysql://user:pass@host/db
            **options: Driver-specific options passed to the backend adapter.
                connect_retries (int): Number of connection retries (default 3).
                connect_retry_delay (float): Seconds between retries (default 0.5).
        """
        self._url = url
        self._driver = self._detect_driver(url)
        self._adapter: DatabaseAdapter = _create_adapter(self._driver)
        self._connected = False
        self._lock = asyncio.Lock()
        self._options = options
        self._in_transaction = False
        self._last_activity: float = 0.0
        self._connect_retries = int(options.pop("connect_retries", 3))
        self._connect_retry_delay = float(options.pop("connect_retry_delay", 0.5))

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

    # ── Lifecycle hooks ──────────────────────────────────────────────

    async def on_startup(self) -> None:
        """Lifecycle hook — called by ``LifecycleCoordinator`` at app start."""
        await self.connect()

    async def on_shutdown(self) -> None:
        """Lifecycle hook — called by ``LifecycleCoordinator`` at app stop."""
        await self.disconnect()

    # ── Connection management ────────────────────────────────────────

    async def connect(self) -> None:
        """Open database connection with retry logic."""
        if self._connected:
            return

        async with self._lock:
            if self._connected:
                return

            last_exc: Optional[Exception] = None
            for attempt in range(1, self._connect_retries + 1):
                try:
                    await self._adapter.connect(self._url, **self._options)
                    self._connected = True
                    self._last_activity = time.monotonic()
                    logger.info(f"Database connected ({self._driver}), attempt {attempt}")
                    return
                except (DatabaseConnectionFault, ImportError):
                    raise
                except Exception as exc:
                    last_exc = exc
                    if attempt < self._connect_retries:
                        logger.warning(
                            f"Connection attempt {attempt} failed: {exc}, "
                            f"retrying in {self._connect_retry_delay}s..."
                        )
                        await asyncio.sleep(self._connect_retry_delay)

            raise DatabaseConnectionFault(
                url=self._url,
                reason=f"Failed after {self._connect_retries} attempts: {last_exc}",
            )

    async def disconnect(self) -> None:
        """Close database connection."""
        if not self._connected:
            return
        async with self._lock:
            if not self._connected:
                return
            try:
                await self._adapter.disconnect()
                self._connected = False
                logger.info("Database disconnected")
            except Exception as exc:
                self._connected = False
                raise DatabaseConnectionFault(
                    url=self._url,
                    reason=f"Disconnect failed: {exc}",
                ) from exc

    async def ensure_connected(self) -> None:
        """Ensure a live connection exists, reconnecting if needed."""
        if not self._connected:
            await self.connect()
        elif not self._adapter.is_connected:
            self._connected = False
            await self.connect()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """
        Async context manager for transactions.

        Delegates to the backend adapter's transaction management.

        Usage:
            async with db.transaction():
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")
        """
        await self.ensure_connected()

        await self._adapter.begin()
        self._in_transaction = True
        try:
            yield
            await self._adapter.commit()
        except Exception:
            await self._adapter.rollback()
            raise
        finally:
            self._in_transaction = False

    async def savepoint(self, name: str) -> None:
        """Create a named savepoint within a transaction."""
        name = _sanitize_savepoint(name)
        await self.ensure_connected()
        await self._adapter.savepoint(name)

    async def release_savepoint(self, name: str) -> None:
        """Release (commit) a named savepoint."""
        name = _sanitize_savepoint(name)
        await self.ensure_connected()
        await self._adapter.release_savepoint(name)

    async def rollback_to_savepoint(self, name: str) -> None:
        """Roll back to a named savepoint."""
        name = _sanitize_savepoint(name)
        await self.ensure_connected()
        await self._adapter.rollback_to_savepoint(name)

    # ── Query execution ──────────────────────────────────────────────

    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        """
        Execute a SQL statement.

        Args:
            sql: SQL query with ? placeholders (auto-adapted per backend)
            params: Parameter values

        Returns:
            Cursor-like object (exposes lastrowid, rowcount)

        Raises:
            QueryFault: When query execution fails
        """
        await self.ensure_connected()

        if params is None:
            params = []
        try:
            self._last_activity = time.monotonic()
            result = await self._adapter.execute(sql, params)
            return result
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
        await self.ensure_connected()
        try:
            self._last_activity = time.monotonic()
            await self._adapter.execute_many(sql, params_list)
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
            sql: SELECT query with ? placeholders
            params: Parameter values

        Returns:
            List of row dicts

        Raises:
            QueryFault: When query execution fails
        """
        await self.ensure_connected()

        if params is None:
            params = []
        try:
            self._last_activity = time.monotonic()
            return await self._adapter.fetch_all(sql, params)
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
        await self.ensure_connected()

        if params is None:
            params = []
        try:
            self._last_activity = time.monotonic()
            return await self._adapter.fetch_one(sql, params)
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
        await self.ensure_connected()

        if params is None:
            params = []
        try:
            self._last_activity = time.monotonic()
            return await self._adapter.fetch_val(sql, params)
        except (DatabaseConnectionFault, QueryFault, SchemaFault):
            raise
        except Exception as exc:
            raise QueryFault(
                model="<raw>",
                operation="fetch_val",
                reason=str(exc),
                metadata={"sql": sql[:200]},
            ) from exc

    # ── Introspection (delegated to adapter) ─────────────────────────

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        await self.ensure_connected()
        return await self._adapter.table_exists(table_name)

    async def get_tables(self) -> List[str]:
        """List all table names in the database."""
        await self.ensure_connected()
        return await self._adapter.get_tables()

    async def get_columns(self, table_name: str) -> List[ColumnInfo]:
        """Get column metadata for a table."""
        await self.ensure_connected()
        return await self._adapter.get_columns(table_name)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected and self._adapter.is_connected

    @property
    def url(self) -> str:
        return self._url

    @property
    def driver(self) -> str:
        return self._driver

    @property
    def dialect(self) -> str:
        """Return the SQL dialect name (sqlite, postgresql, mysql)."""
        return self._adapter.dialect

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Return backend capabilities."""
        return self._adapter.capabilities

    @property
    def adapter(self) -> DatabaseAdapter:
        """Direct access to the underlying adapter (advanced use)."""
        return self._adapter

    @property
    def in_transaction(self) -> bool:
        return self._in_transaction


# ── Module-level singleton accessor ─────────────────────────────────────────

_default_database: Optional[AquiliaDatabase] = None
_database_registry: Dict[str, AquiliaDatabase] = {}


def get_database(alias: Optional[str] = None) -> AquiliaDatabase:
    """
    Get a database instance by alias, or the default.

    Args:
        alias: Optional database alias for multi-database setups.
               Use "default" or None for the primary database.

    Raises:
        DatabaseConnectionFault: If no database is configured.
    """
    if alias and alias != "default":
        db = _database_registry.get(alias)
        if db is None:
            raise DatabaseConnectionFault(
                url=f"<alias:{alias}>",
                reason=f"No database configured with alias '{alias}'. "
                       f"Available: {list(_database_registry.keys())}",
            )
        return db

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


def configure_database(
    url: str = "sqlite:///db.sqlite3",
    *,
    alias: str = "default",
    **options: Any,
) -> AquiliaDatabase:
    """
    Configure and return a database instance.

    Args:
        url: Database connection URL
        alias: Database alias for multi-database setups (default "default")
        **options: Driver-specific options

    Returns:
        AquiliaDatabase instance
    """
    db = AquiliaDatabase(url, **options)
    _database_registry[alias] = db

    if alias == "default":
        global _default_database
        _default_database = db

    return db


def set_database(db: AquiliaDatabase, *, alias: str = "default") -> None:
    """Set an externally-created database as the default or by alias."""
    _database_registry[alias] = db
    if alias == "default":
        global _default_database
        _default_database = db


def get_all_databases() -> Dict[str, AquiliaDatabase]:
    """Return all configured database instances."""
    return dict(_database_registry)
