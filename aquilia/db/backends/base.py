"""
Aquilia DB Backend — Base Adapter Interface.

All database backends must implement this interface. The ``AquiliaDatabase``
engine delegates to the appropriate adapter based on the connection URL.

This interface abstracts differences between SQLite, PostgreSQL, and MySQL:
- Parameter placeholder style (?, %s, $1)
- Transaction semantics
- Introspection queries
- RETURNING clause support
- JSON column type
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple, Type

logger = logging.getLogger("aquilia.db.backends")

__all__ = [
    "DatabaseAdapter",
    "AdapterCapabilities",
    "IntrospectionResult",
    "ColumnInfo",
    "TableInfo",
]


@dataclass
class AdapterCapabilities:
    """Describes what a specific backend supports."""

    supports_returning: bool = False
    supports_json_type: bool = False
    supports_arrays: bool = False
    supports_hstore: bool = False
    supports_citext: bool = False
    supports_upsert: bool = True
    supports_savepoints: bool = True
    supports_window_functions: bool = True
    supports_cte: bool = True
    param_style: str = "qmark"  # qmark (?) | format (%s) | numeric ($1)
    null_ordering: bool = False  # NULLS FIRST / NULLS LAST
    name: str = "base"


@dataclass
class ColumnInfo:
    """Introspection result for a single column."""

    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    unique: bool = False
    max_length: Optional[int] = None


@dataclass
class TableInfo:
    """Introspection result for a table."""

    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IntrospectionResult:
    """Full database introspection result."""

    tables: List[TableInfo] = field(default_factory=list)


class DatabaseAdapter(ABC):
    """
    Abstract database adapter interface.

    All backends must implement these methods. The ``AquiliaDatabase``
    engine uses this interface to execute queries, manage transactions,
    and introspect schemas.
    """

    capabilities: AdapterCapabilities = AdapterCapabilities()

    @abstractmethod
    async def connect(self, url: str, **options) -> None:
        """Open a connection to the database."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection."""
        ...

    @abstractmethod
    async def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        """Execute a SQL statement. Returns a cursor-like object."""
        ...

    @abstractmethod
    async def execute_many(self, sql: str, params_list: Sequence[Sequence[Any]]) -> None:
        """Execute a SQL statement with multiple parameter sets."""
        ...

    @abstractmethod
    async def fetch_all(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """Execute and return all rows as dicts."""
        ...

    @abstractmethod
    async def fetch_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute and return one row as dict, or None."""
        ...

    @abstractmethod
    async def fetch_val(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        """Execute and return a scalar value."""
        ...

    # ── Transaction management ───────────────────────────────────────

    @abstractmethod
    async def begin(self) -> None:
        """Start a transaction."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    @abstractmethod
    async def savepoint(self, name: str) -> None:
        """Create a savepoint."""
        ...

    @abstractmethod
    async def release_savepoint(self, name: str) -> None:
        """Release (commit) a savepoint."""
        ...

    @abstractmethod
    async def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a savepoint."""
        ...

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Context manager for transactions."""
        await self.begin()
        try:
            yield
            await self.commit()
        except Exception:
            await self.rollback()
            raise

    # ── Introspection ────────────────────────────────────────────────

    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        ...

    @abstractmethod
    async def get_tables(self) -> List[str]:
        """List all table names."""
        ...

    @abstractmethod
    async def get_columns(self, table_name: str) -> List[ColumnInfo]:
        """Get column info for a table."""
        ...

    async def introspect(self) -> IntrospectionResult:
        """Full database introspection."""
        tables = await self.get_tables()
        result = IntrospectionResult()
        for table_name in tables:
            columns = await self.get_columns(table_name)
            result.tables.append(TableInfo(name=table_name, columns=columns))
        return result

    # ── SQL adaptation ───────────────────────────────────────────────

    def adapt_sql(self, sql: str) -> str:
        """
        Adapt SQL placeholders from qmark (?) to the backend's param style.

        Override this in backends that use a different param style.
        """
        return sql

    def last_insert_id(self, cursor: Any) -> Optional[int]:
        """Extract last inserted ID from cursor."""
        if hasattr(cursor, "lastrowid"):
            return cursor.lastrowid
        return None

    @property
    def is_connected(self) -> bool:
        """Check if the adapter is connected."""
        return False

    @property
    def dialect(self) -> str:
        """Return the SQL dialect name."""
        return self.capabilities.name
