"""
Aquilia DB Backends Package — pluggable database adapters.

Provides a common adapter interface and implementations for:
- SQLite (default, via aiosqlite)
- PostgreSQL (via psycopg2 / asyncpg)
- MySQL (via pymysql / aiomysql)
"""

from .base import DatabaseAdapter, AdapterCapabilities, ColumnInfo, TableInfo, IntrospectionResult
from .sqlite import SQLiteAdapter
from .postgres import PostgresAdapter
from .mysql import MySQLAdapter

__all__ = [
    "DatabaseAdapter",
    "AdapterCapabilities",
    "ColumnInfo",
    "TableInfo",
    "IntrospectionResult",
    "SQLiteAdapter",
    "PostgresAdapter",
    "MySQLAdapter",
]
