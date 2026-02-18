"""
Aquilia Migration DSL — declarative, human-readable migration operations.

Provides a clean, Aquilia-native DSL for expressing schema changes as
composable Python objects. Each operation knows how to compile itself
to SQL for any supported backend (SQLite, PostgreSQL, MySQL).

DSL Primitives:
    CreateModel      — Create a new table with columns
    DropModel        — Drop a table
    RenameModel      — Rename a table
    AddField         — Add a column to a table
    RemoveField      — Remove a column from a table
    AlterField       — Change column type/constraints
    RenameField      — Rename a column
    CreateIndex      — Create an index
    DropIndex        — Drop an index
    AddConstraint    — Add a constraint
    RemoveConstraint — Drop a constraint
    RunSQL           — Execute raw SQL (forward + reverse)
    RunPython        — Execute a Python callable

Usage in migration files:

    from aquilia.models.migration_dsl import (
        Migration, CreateModel, AddField, CreateIndex, RunSQL,
        columns as C,
    )

    class Meta:
        revision = "20260217_210454"
        slug = "order_orderevent_orderitem_and_7_more"
        models = ["Order", "OrderEvent", "OrderItem", ...]

    operations = [
        CreateModel(
            name="User",
            table="users",
            fields=[
                C.auto("id"),
                C.uuid("uuid", unique=True),
                C.varchar("email", 255, unique=True),
                C.varchar("username", 150, unique=True),
                C.varchar("password_hash", 255),
                C.varchar("first_name", 100, default=""),
                C.varchar("last_name", 100, default=""),
                C.varchar("role", 20, default="customer"),
                C.boolean("is_active", default=True),
                C.boolean("is_verified", default=False),
                C.varchar("avatar_url", 500, null=True),
                C.text("bio", null=True),
                C.varchar("phone", 20, null=True),
                C.text("preferences", default=""),
                C.timestamp("last_login_at", null=True),
                C.integer("login_count", default=0),
                C.timestamp("created_at"),
                C.timestamp("updated_at"),
            ],
        ),
        CreateIndex("idx_users_email", "users", ["email"]),
        CreateIndex("idx_users_username", "users", ["username"]),
        CreateIndex("idx_users_role_is_active", "users", ["role", "is_active"]),
    ]
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


# ── Sentinel for distinguishing 'no default' from None ──────────────────────


class _SentinelType:
    """Sentinel to distinguish 'no default' from None."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<NO_DEFAULT>"

    def __bool__(self):
        return False


_SENTINEL = _SentinelType()


def _format_default(value: Any, dialect: str = "sqlite") -> str:
    """Format a Python value as a SQL DEFAULT literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        if dialect == "postgresql":
            return "TRUE" if value else "FALSE"
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return repr(value)


# ── Column Definition Helper ────────────────────────────────────────────────


@dataclass
class ColumnDef:
    """
    A column definition in the DSL.

    Encapsulates the full definition of a database column including
    type, constraints, references, and defaults.
    """

    name: str
    col_type: str  # e.g. "VARCHAR(255)", "INTEGER", "TIMESTAMP"
    primary_key: bool = False
    autoincrement: bool = False
    unique: bool = False
    nullable: bool = False
    default: Any = _SENTINEL  # sentinel to distinguish from None
    references: Optional[Tuple[str, str]] = None  # (table, column)
    on_delete: str = "CASCADE"
    on_update: str = "CASCADE"

    def to_sql(self, dialect: str = "sqlite") -> str:
        """Compile this column to a SQL column definition."""
        parts = [f'"{self.name}"', self._resolve_type(dialect)]

        if self.unique and not self.primary_key:
            parts.append("UNIQUE")
        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                if dialect == "postgresql":
                    # Type is already SERIAL
                    parts.pop()  # remove PRIMARY KEY, it's in type
                    parts.append("PRIMARY KEY")
                elif dialect == "mysql":
                    parts.append("AUTO_INCREMENT")
                else:
                    parts.append("AUTOINCREMENT")
        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")
        if self.default is not _SENTINEL:
            parts.append(f"DEFAULT {_format_default(self.default, dialect)}")
        if self.references:
            ref_table, ref_col = self.references
            parts.append(f'REFERENCES "{ref_table}"("{ref_col}")')
            parts.append(f"ON DELETE {self.on_delete}")
            parts.append(f"ON UPDATE {self.on_update}")

        return " ".join(parts)

    def _resolve_type(self, dialect: str) -> str:
        """Resolve the SQL type for the given dialect."""
        t = self.col_type
        if self.autoincrement and self.primary_key:
            if dialect == "postgresql":
                return "SERIAL" if "BIG" not in t.upper() else "BIGSERIAL"
            elif dialect == "mysql":
                return "INTEGER" if "BIG" not in t.upper() else "BIGINT"
        return t

    def to_snapshot(self) -> Dict[str, Any]:
        """Serialize this column to a snapshot-compatible dict."""
        d: Dict[str, Any] = {
            "name": self.name,
            "type": self.col_type,
        }
        if self.primary_key:
            d["primary_key"] = True
        if self.autoincrement:
            d["autoincrement"] = True
        if self.unique:
            d["unique"] = True
        if self.nullable:
            d["nullable"] = True
        if self.default is not _SENTINEL:
            d["default"] = self.default
        if self.references:
            d["references"] = {"table": self.references[0], "column": self.references[1]}
            d["on_delete"] = self.on_delete
            d["on_update"] = self.on_update
        return d

    @classmethod
    def from_snapshot(cls, data: Dict[str, Any]) -> ColumnDef:
        """Deserialize from snapshot dict."""
        ref = data.get("references")
        return cls(
            name=data["name"],
            col_type=data["type"],
            primary_key=data.get("primary_key", False),
            autoincrement=data.get("autoincrement", False),
            unique=data.get("unique", False),
            nullable=data.get("nullable", False),
            default=data.get("default", _SENTINEL),
            references=(ref["table"], ref["column"]) if ref else None,
            on_delete=data.get("on_delete", "CASCADE"),
            on_update=data.get("on_update", "CASCADE"),
        )


# ── Column Builder (C namespace) ────────────────────────────────────────────


class _ColumnBuilder:
    """
    Fluent column builder — the ``columns`` (aliased as ``C``) namespace.

    Usage:
        from aquilia.models.migration_dsl import columns as C

        C.auto("id")
        C.varchar("email", 255, unique=True)
        C.integer("age", null=True)
        C.foreign_key("user_id", "users", "id", on_delete="CASCADE")
    """

    @staticmethod
    def auto(name: str = "id") -> ColumnDef:
        return ColumnDef(name=name, col_type="INTEGER", primary_key=True, autoincrement=True)

    @staticmethod
    def bigauto(name: str = "id") -> ColumnDef:
        return ColumnDef(name=name, col_type="INTEGER", primary_key=True, autoincrement=True)

    @staticmethod
    def integer(name: str, *, null: bool = False, unique: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="INTEGER", nullable=null, unique=unique, default=default)

    @staticmethod
    def biginteger(name: str, *, null: bool = False, unique: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="INTEGER", nullable=null, unique=unique, default=default)

    @staticmethod
    def varchar(name: str, length: int = 255, *, null: bool = False, unique: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type=f"VARCHAR({length})", nullable=null, unique=unique, default=default)

    @staticmethod
    def text(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="TEXT", nullable=null, default=default)

    @staticmethod
    def boolean(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="INTEGER", nullable=null, default=default)

    @staticmethod
    def real(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="REAL", nullable=null, default=default)

    @staticmethod
    def decimal(name: str, max_digits: int = 10, decimal_places: int = 2, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type=f"DECIMAL({max_digits},{decimal_places})", nullable=null, default=default)

    @staticmethod
    def timestamp(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="TIMESTAMP", nullable=null, default=default)

    @staticmethod
    def date(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="DATE", nullable=null, default=default)

    @staticmethod
    def time(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="TIME", nullable=null, default=default)

    @staticmethod
    def uuid(name: str, *, null: bool = False, unique: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="VARCHAR(36)", nullable=null, unique=unique, default=default)

    @staticmethod
    def blob(name: str, *, null: bool = False) -> ColumnDef:
        return ColumnDef(name=name, col_type="BLOB", nullable=null)

    @staticmethod
    def json(name: str, *, null: bool = False, default: Any = _SENTINEL) -> ColumnDef:
        return ColumnDef(name=name, col_type="TEXT", nullable=null, default=default)

    @staticmethod
    def foreign_key(
        name: str,
        ref_table: str,
        ref_column: str = "id",
        *,
        null: bool = False,
        on_delete: str = "CASCADE",
        on_update: str = "CASCADE",
    ) -> ColumnDef:
        return ColumnDef(
            name=name,
            col_type="INTEGER",
            nullable=null,
            references=(ref_table, ref_column),
            on_delete=on_delete,
            on_update=on_update,
        )


columns = _ColumnBuilder()
C = columns  # Short alias


# ── Operation Base ──────────────────────────────────────────────────────────


class Operation:
    """Base class for all migration operations."""

    reversible: bool = True

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        """Compile this operation to SQL statement(s)."""
        raise NotImplementedError

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        """Compile the reverse of this operation to SQL."""
        raise NotImplementedError(f"{type(self).__name__} is not reversible")

    def describe(self) -> str:
        """Human-readable description."""
        return type(self).__name__

    def to_snapshot_delta(self) -> Dict[str, Any]:
        """Describe the snapshot change this operation implies."""
        return {}


# ── CreateModel ─────────────────────────────────────────────────────────────


@dataclass
class CreateModel(Operation):
    """
    Create a new database table.

    Usage:
        CreateModel(
            name="User",
            table="users",
            fields=[
                C.auto("id"),
                C.varchar("email", 255, unique=True),
                C.boolean("is_active", default=True),
            ],
        )
    """

    name: str  # Model/class name
    table: str  # Database table name
    fields: List[ColumnDef] = field(default_factory=list)

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        col_defs = ",\n  ".join(f.to_sql(dialect) for f in self.fields)
        return [f'CREATE TABLE IF NOT EXISTS "{self.table}" (\n  {col_defs}\n);']

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'DROP TABLE IF EXISTS "{self.table}";']

    def describe(self) -> str:
        return f"CreateModel({self.name}, table={self.table}, {len(self.fields)} fields)"


# ── DropModel ───────────────────────────────────────────────────────────────


@dataclass
class DropModel(Operation):
    """Drop a table."""

    name: str
    table: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'DROP TABLE IF EXISTS "{self.table}";']

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        raise NotImplementedError("DropModel is not auto-reversible — provide a CreateModel")

    def describe(self) -> str:
        return f"DropModel({self.name}, table={self.table})"


# ── RenameModel ─────────────────────────────────────────────────────────────


@dataclass
class RenameModel(Operation):
    """Rename a table (preserves data)."""

    old_name: str
    new_name: str
    old_table: str
    new_table: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.old_table}" RENAME TO "{self.new_table}";']

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.new_table}" RENAME TO "{self.old_table}";']

    def describe(self) -> str:
        return f"RenameModel({self.old_name} → {self.new_name})"


# ── AddField ────────────────────────────────────────────────────────────────


@dataclass
class AddField(Operation):
    """Add a column to an existing table."""

    model_name: str
    table: str
    column: ColumnDef = field(default_factory=lambda: ColumnDef(name="", col_type=""))

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.table}" ADD COLUMN {self.column.to_sql(dialect)};']

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.table}" DROP COLUMN "{self.column.name}";']

    def describe(self) -> str:
        return f"AddField({self.model_name}.{self.column.name})"


# ── RemoveField ─────────────────────────────────────────────────────────────


@dataclass
class RemoveField(Operation):
    """Remove a column from an existing table."""

    model_name: str
    table: str
    column_name: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.table}" DROP COLUMN "{self.column_name}";']

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        raise NotImplementedError("RemoveField is not auto-reversible")

    def describe(self) -> str:
        return f"RemoveField({self.model_name}.{self.column_name})"


# ── AlterField ──────────────────────────────────────────────────────────────


@dataclass
class AlterField(Operation):
    """
    Alter a column's type, constraints, or default.

    Note: SQLite < 3.35 does not support ALTER COLUMN. For SQLite,
    this generates a comment indicating a table rebuild is needed.
    """

    model_name: str
    table: str
    column_name: str
    new_type: Optional[str] = None
    nullable: Optional[bool] = None
    new_default: Any = _SENTINEL
    drop_default: bool = False

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        stmts: List[str] = []
        if dialect == "sqlite":
            stmts.append(
                f'-- SQLite: ALTER COLUMN not supported for '
                f'"{self.table}"."{self.column_name}". Requires table rebuild.'
            )
            return stmts

        if dialect == "postgresql":
            if self.new_type:
                stmts.append(
                    f'ALTER TABLE "{self.table}" ALTER COLUMN '
                    f'"{self.column_name}" TYPE {self.new_type};'
                )
            if self.nullable is True:
                stmts.append(
                    f'ALTER TABLE "{self.table}" ALTER COLUMN '
                    f'"{self.column_name}" DROP NOT NULL;'
                )
            elif self.nullable is False:
                stmts.append(
                    f'ALTER TABLE "{self.table}" ALTER COLUMN '
                    f'"{self.column_name}" SET NOT NULL;'
                )
            if self.drop_default:
                stmts.append(
                    f'ALTER TABLE "{self.table}" ALTER COLUMN '
                    f'"{self.column_name}" DROP DEFAULT;'
                )
            elif self.new_default is not _SENTINEL:
                stmts.append(
                    f'ALTER TABLE "{self.table}" ALTER COLUMN '
                    f'"{self.column_name}" SET DEFAULT '
                    f'{_format_default(self.new_default, dialect)};'
                )
        return stmts

    def describe(self) -> str:
        return f"AlterField({self.model_name}.{self.column_name})"


# ── RenameField ─────────────────────────────────────────────────────────────


@dataclass
class RenameField(Operation):
    """Rename a column (preserves data)."""

    model_name: str
    table: str
    old_name: str
    new_name: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [
            f'ALTER TABLE "{self.table}" RENAME COLUMN '
            f'"{self.old_name}" TO "{self.new_name}";'
        ]

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return [
            f'ALTER TABLE "{self.table}" RENAME COLUMN '
            f'"{self.new_name}" TO "{self.old_name}";'
        ]

    def describe(self) -> str:
        return f"RenameField({self.model_name}.{self.old_name} → {self.new_name})"


# ── CreateIndex ─────────────────────────────────────────────────────────────


@dataclass
class CreateIndex(Operation):
    """Create a database index."""

    name: str
    table: str
    columns: List[str] = field(default_factory=list)
    unique: bool = False
    condition: Optional[str] = None  # Partial index WHERE clause

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        u = "UNIQUE " if self.unique else ""
        cols = ", ".join(f'"{c}"' for c in self.columns)
        sql = f'CREATE {u}INDEX IF NOT EXISTS "{self.name}" ON "{self.table}" ({cols})'
        if self.condition and dialect != "mysql":
            sql += f" WHERE ({self.condition})"
        return [sql + ";"]

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'DROP INDEX IF EXISTS "{self.name}";']

    def describe(self) -> str:
        return f"CreateIndex({self.name}, {self.table}, {self.columns})"


# ── DropIndex ───────────────────────────────────────────────────────────────


@dataclass
class DropIndex(Operation):
    """Drop a database index."""

    name: str
    table: Optional[str] = None  # Required for MySQL

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        if dialect == "mysql" and self.table:
            return [f'DROP INDEX "{self.name}" ON "{self.table}";']
        return [f'DROP INDEX IF EXISTS "{self.name}";']

    def describe(self) -> str:
        return f"DropIndex({self.name})"


# ── AddConstraint ───────────────────────────────────────────────────────────


@dataclass
class AddConstraint(Operation):
    """Add a constraint to a table."""

    table: str
    constraint_sql: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return [f'ALTER TABLE "{self.table}" ADD {self.constraint_sql};']

    def describe(self) -> str:
        return f"AddConstraint({self.table})"


# ── RemoveConstraint ────────────────────────────────────────────────────────


@dataclass
class RemoveConstraint(Operation):
    """Remove a constraint from a table."""

    table: str
    name: str

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        if dialect == "sqlite":
            return [f'-- SQLite: Cannot drop constraint "{self.name}" via ALTER TABLE;']
        return [f'ALTER TABLE "{self.table}" DROP CONSTRAINT "{self.name}";']

    def describe(self) -> str:
        return f"RemoveConstraint({self.table}.{self.name})"


# ── RunSQL ──────────────────────────────────────────────────────────────────


@dataclass
class RunSQL(Operation):
    """
    Execute raw SQL statements (forward and optionally reverse).

    Usage:
        RunSQL(
            sql="INSERT INTO config (key, val) VALUES ('version', '1.0');",
            reverse_sql="DELETE FROM config WHERE key = 'version';",
        )

        RunSQL(
            sql=[
                "CREATE VIEW active_users AS SELECT * FROM users WHERE is_active=1;",
                "CREATE VIEW admin_users AS SELECT * FROM users WHERE role='admin';",
            ],
        )
    """

    sql: Union[str, List[str]] = ""
    reverse: Union[str, List[str]] = ""

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        if isinstance(self.sql, list):
            return self.sql
        return [self.sql] if self.sql else []

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        if isinstance(self.reverse, list):
            return self.reverse
        return [self.reverse] if self.reverse else []

    def describe(self) -> str:
        preview = (self.sql if isinstance(self.sql, str) else self.sql[0]) if self.sql else "(empty)"
        return f"RunSQL({preview[:60]}...)"


# ── RunPython ───────────────────────────────────────────────────────────────


@dataclass
class RunPython(Operation):
    """
    Execute a Python callable as a data migration step.

    The callable receives (conn) as argument — the AquiliaDatabase instance.
    """

    forward: Optional[Callable] = None
    reverse: Optional[Callable] = None

    reversible = True

    def to_sql(self, dialect: str = "sqlite") -> List[str]:
        return []  # Not SQL — handled by runner

    def reverse_sql(self, dialect: str = "sqlite") -> List[str]:
        return []

    def describe(self) -> str:
        name = self.forward.__name__ if self.forward else "(none)"
        return f"RunPython({name})"


# ── Migration Container ────────────────────────────────────────────────────


@dataclass
class Migration:
    """
    Container for a set of migration operations with metadata.

    This is the top-level object in a DSL migration file.

    Usage:
        migration = Migration(
            revision="20260217_210454",
            slug="initial_schema",
            models=["User", "Order", "Product"],
            operations=[
                CreateModel(...),
                CreateIndex(...),
            ],
        )
    """

    revision: str
    slug: str
    models: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    operations: List[Operation] = field(default_factory=list)

    def compile_upgrade(self, dialect: str = "sqlite") -> List[str]:
        """Compile all operations to forward SQL."""
        stmts: List[str] = []
        for op in self.operations:
            stmts.extend(op.to_sql(dialect))
        return stmts

    def compile_downgrade(self, dialect: str = "sqlite") -> List[str]:
        """Compile all operations (reversed) to rollback SQL."""
        stmts: List[str] = []
        for op in reversed(self.operations):
            try:
                stmts.extend(op.reverse_sql(dialect))
            except NotImplementedError:
                stmts.append(f"-- {op.describe()} is not auto-reversible")
        return stmts

    def get_python_ops(self) -> List[RunPython]:
        """Get all RunPython operations (for the runner)."""
        return [op for op in self.operations if isinstance(op, RunPython)]

    def describe(self) -> str:
        lines = [
            f"Migration {self.revision} ({self.slug})",
            f"  Models: {', '.join(self.models)}",
            f"  Operations ({len(self.operations)}):",
        ]
        for op in self.operations:
            lines.append(f"    - {op.describe()}")
        return "\n".join(lines)


# ── Utility: Convert raw-SQL migration to DSL ──────────────────────────────


def raw_sql_to_operations(upgrade_sql: str, downgrade_sql: str = "") -> List[Operation]:
    """
    Convert raw SQL strings into a list of RunSQL operations.

    This is a compatibility helper for existing raw-SQL migration files.
    """
    ops: List[Operation] = []
    if upgrade_sql.strip():
        ops.append(RunSQL(sql=upgrade_sql.strip(), reverse=downgrade_sql.strip()))
    return ops
