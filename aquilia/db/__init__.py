"""
Aquilia Database — async-first database layer.

Provides:
- AquiliaDatabase: Connection manager with transaction support
- SQLite driver (default), Postgres/MySQL planned
- Module-level accessors for DI integration
- Structured faults via AquilaFaults (DatabaseConnectionFault, QueryFault, SchemaFault)
"""

from .engine import (
    AquiliaDatabase,
    DatabaseError,
    get_database,
    configure_database,
    set_database,
)

# Re-export fault types for convenience
from ..faults.domains import (
    DatabaseConnectionFault,
    QueryFault,
    SchemaFault,
)

__all__ = [
    "AquiliaDatabase",
    "DatabaseError",
    "DatabaseConnectionFault",
    "QueryFault",
    "SchemaFault",
    "get_database",
    "configure_database",
    "set_database",
]
