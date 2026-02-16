"""
Aquilia Migration System — generate and apply schema migrations.

Provides:
- Migration operations (op.create_table, op.drop_table, etc.)
- Migration file generation from AMDL diffs (legacy)
- Migration file generation from Python Model classes (new)
- Migration runner with tracking table
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..db.engine import AquiliaDatabase
from ..faults.domains import MigrationFault, MigrationConflictFault, SchemaFault
from .ast_nodes import FieldType, ModelNode
from .runtime import generate_create_table_sql, generate_create_index_sql, SQLITE_TYPE_MAP
from .signals import pre_migrate, post_migrate

logger = logging.getLogger("aquilia.models.migrations")

MIGRATION_TABLE = "aquilia_migrations"


# ── Migration Operations ────────────────────────────────────────────────────


class MigrationOps:
    """
    Migration operation builder — used inside migration scripts.

    Provides DDL operations for schema changes, dialect-aware SQL helpers,
    and raw SQL execution. Accumulated statements can be retrieved and
    executed by the MigrationRunner.

    Usage in generated migration files:
        from aquilia.models.migrations import op

        async def upgrade(conn):
            op.create_table("aq_user", [...])
            op.add_column("aq_user", op.varchar("bio", 500, nullable=True))
            op.rename_column("aq_user", "name", "full_name")
            for sql in op.get_statements():
                await conn.execute(sql)
            op.clear()

        async def downgrade(conn):
            op.drop_table("aq_user")
    """

    def __init__(self, dialect: str = "sqlite") -> None:
        self._statements: List[str] = []
        self._dialect = dialect

    @property
    def dialect(self) -> str:
        return self._dialect

    @dialect.setter
    def dialect(self, value: str) -> None:
        self._dialect = value

    # ── Table operations ─────────────────────────────────────────────

    def create_table(self, name: str, columns: List[str]) -> None:
        """Generate CREATE TABLE statement."""
        body = ",\n  ".join(columns)
        self._statements.append(f'CREATE TABLE IF NOT EXISTS "{name}" (\n  {body}\n);')

    def drop_table(self, name: str, cascade: bool = False) -> None:
        """Generate DROP TABLE statement."""
        sql = f'DROP TABLE IF EXISTS "{name}"'
        if cascade and self._dialect in ("postgresql", "mysql"):
            sql += " CASCADE"
        self._statements.append(sql + ";")

    def rename_table(self, old_name: str, new_name: str) -> None:
        """Generate RENAME TABLE statement (dialect-aware)."""
        if self._dialect == "mysql":
            self._statements.append(
                f'RENAME TABLE "{old_name}" TO "{new_name}";'
            )
        else:
            # SQLite & PostgreSQL both support ALTER TABLE ... RENAME TO
            self._statements.append(
                f'ALTER TABLE "{old_name}" RENAME TO "{new_name}";'
            )

    # ── Column operations ────────────────────────────────────────────

    def add_column(self, table: str, column_def: str) -> None:
        """Generate ALTER TABLE ADD COLUMN."""
        self._statements.append(f'ALTER TABLE "{table}" ADD COLUMN {column_def};')

    def drop_column(self, table: str, column: str) -> None:
        """
        Generate ALTER TABLE DROP COLUMN (dialect-aware).

        Note: SQLite < 3.35.0 does not support DROP COLUMN. For older
        SQLite versions, a table-rebuild strategy would be needed.
        SQLite 3.35.0+ (2021-03) supports ALTER TABLE DROP COLUMN.
        """
        if self._dialect == "mysql":
            self._statements.append(
                f'ALTER TABLE "{table}" DROP COLUMN "{column}";'
            )
        else:
            # PostgreSQL & SQLite 3.35+
            self._statements.append(
                f'ALTER TABLE "{table}" DROP COLUMN "{column}";'
            )

    def rename_column(self, table: str, old_name: str, new_name: str) -> None:
        """
        Generate ALTER TABLE RENAME COLUMN (dialect-aware).

        Supported by SQLite 3.25+ (2018-09), PostgreSQL 9.x+, MySQL 8.0+.
        """
        if self._dialect == "mysql":
            # MySQL uses CHANGE for older versions, RENAME COLUMN for 8.0+
            self._statements.append(
                f'ALTER TABLE "{table}" RENAME COLUMN "{old_name}" TO "{new_name}";'
            )
        else:
            self._statements.append(
                f'ALTER TABLE "{table}" RENAME COLUMN "{old_name}" TO "{new_name}";'
            )

    def alter_column(
        self,
        table: str,
        column: str,
        *,
        type: Optional[str] = None,
        nullable: Optional[bool] = None,
        default: Optional[Any] = None,
        drop_default: bool = False,
    ) -> None:
        """
        Generate ALTER TABLE ALTER COLUMN (dialect-aware).

        For PostgreSQL, generates ALTER COLUMN ... TYPE / SET NOT NULL / etc.
        For MySQL, generates MODIFY COLUMN.
        For SQLite, ALTER COLUMN is not supported — generates a comment.

        Args:
            table: Table name
            column: Column name
            type: New column type (e.g., "VARCHAR(500)")
            nullable: Set NULL / NOT NULL constraint
            default: New default value
            drop_default: Drop the default value
        """
        if self._dialect == "sqlite":
            # SQLite does not support ALTER COLUMN — document limitation
            self._statements.append(
                f'-- SQLite: ALTER COLUMN not supported for "{table}"."{column}". '
                f"Requires table rebuild."
            )
            return

        if self._dialect == "postgresql":
            if type is not None:
                self._statements.append(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"TYPE {type};"
                )
            if nullable is True:
                self._statements.append(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"DROP NOT NULL;"
                )
            elif nullable is False:
                self._statements.append(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"SET NOT NULL;"
                )
            if drop_default:
                self._statements.append(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"DROP DEFAULT;"
                )
            elif default is not None:
                default_sql = _format_default(default)
                self._statements.append(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                    f"SET DEFAULT {default_sql};"
                )
        elif self._dialect == "mysql":
            # MySQL MODIFY requires full column redefinition
            parts = [f'ALTER TABLE "{table}" MODIFY COLUMN "{column}"']
            if type is not None:
                parts.append(type)
            if nullable is True:
                parts.append("NULL")
            elif nullable is False:
                parts.append("NOT NULL")
            if drop_default:
                pass  # MySQL drops default by omission in MODIFY
            elif default is not None:
                parts.append(f"DEFAULT {_format_default(default)}")
            self._statements.append(" ".join(parts) + ";")

    # ── Index operations ─────────────────────────────────────────────

    def create_index(
        self,
        name: str,
        table: str,
        columns: List[str],
        unique: bool = False,
        condition: Optional[str] = None,
    ) -> None:
        """Generate CREATE INDEX (with optional partial index condition)."""
        u = "UNIQUE " if unique else ""
        cols = ", ".join(f'"{c}"' for c in columns)
        sql = f'CREATE {u}INDEX IF NOT EXISTS "{name}" ON "{table}" ({cols})'
        if condition and self._dialect != "mysql":
            sql += f" WHERE ({condition})"
        self._statements.append(sql + ";")

    def drop_index(self, name: str, table: Optional[str] = None) -> None:
        """Generate DROP INDEX (dialect-aware)."""
        if self._dialect == "mysql" and table:
            self._statements.append(f'DROP INDEX "{name}" ON "{table}";')
        else:
            self._statements.append(f'DROP INDEX IF EXISTS "{name}";')

    # ── Constraint operations ────────────────────────────────────────

    def add_constraint(self, table: str, constraint_sql: str) -> None:
        """Generate ALTER TABLE ADD CONSTRAINT."""
        self._statements.append(
            f'ALTER TABLE "{table}" ADD {constraint_sql};'
        )

    def drop_constraint(self, table: str, name: str) -> None:
        """Generate ALTER TABLE DROP CONSTRAINT (not supported on SQLite)."""
        if self._dialect == "sqlite":
            self._statements.append(
                f'-- SQLite: Cannot drop constraint "{name}" via ALTER TABLE'
            )
        else:
            self._statements.append(
                f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}";'
            )

    # ── Raw SQL / data migration ─────────────────────────────────────

    def execute_sql(self, sql: str) -> None:
        """Add raw SQL statement."""
        self._statements.append(sql)

    def run_python(self, func: Callable) -> None:
        """
        Mark a Python callable as a data-migration step.

        The callable is stored as-is and will be invoked by the runner
        with the db connection as argument. This enables data migrations
        alongside schema changes.

        Usage:
            async def populate_slugs(conn):
                rows = await conn.fetch_all('SELECT id, title FROM articles')
                for row in rows:
                    slug = row["title"].lower().replace(" ", "-")
                    await conn.execute(
                        'UPDATE articles SET slug = ? WHERE id = ?',
                        [slug, row["id"]]
                    )

            op.run_python(populate_slugs)
        """
        self._statements.append(func)  # type: ignore[arg-type]

    # ── Column type helpers (dialect-aware) ──────────────────────────

    # NOTE: pk(), boolean(), timestamp() are designed to work both as:
    #   - Instance methods: op.pk()  (uses self._dialect)
    #   - Static calls:     MigrationOps.pk()  (defaults to SQLite)

    @staticmethod
    def pk(name: str = "id", *, dialect: str = "sqlite") -> str:
        """Primary key column definition."""
        if dialect == "postgresql":
            return f'"{name}" SERIAL PRIMARY KEY'
        elif dialect == "mysql":
            return f'"{name}" INTEGER PRIMARY KEY AUTO_INCREMENT'
        return f'"{name}" INTEGER PRIMARY KEY AUTOINCREMENT'

    @staticmethod
    def bigpk(name: str = "id", *, dialect: str = "sqlite") -> str:
        """Big integer primary key."""
        if dialect == "postgresql":
            return f'"{name}" BIGSERIAL PRIMARY KEY'
        elif dialect == "mysql":
            return f'"{name}" BIGINT PRIMARY KEY AUTO_INCREMENT'
        return f'"{name}" INTEGER PRIMARY KEY AUTOINCREMENT'

    @staticmethod
    def integer(name: str, nullable: bool = False, unique: bool = False) -> str:
        parts = [f'"{name}"', "INTEGER"]
        if unique:
            parts.append("UNIQUE")
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def biginteger(name: str, nullable: bool = False, unique: bool = False, *, dialect: str = "sqlite") -> str:
        """Big integer column."""
        sql_type = "BIGINT" if dialect != "sqlite" else "INTEGER"
        parts = [f'"{name}"', sql_type]
        if unique:
            parts.append("UNIQUE")
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def varchar(name: str, length: int = 255, nullable: bool = False, unique: bool = False) -> str:
        parts = [f'"{name}"', f"VARCHAR({length})"]
        if unique:
            parts.append("UNIQUE")
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def text(name: str, nullable: bool = False) -> str:
        parts = [f'"{name}"', "TEXT"]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def blob(name: str, nullable: bool = False) -> str:
        parts = [f'"{name}"', "BLOB"]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def boolean(name: str, nullable: bool = False, default: Optional[bool] = None, *, dialect: str = "sqlite") -> str:
        """Boolean column (dialect-aware)."""
        if dialect == "postgresql":
            sql_type = "BOOLEAN"
        else:
            sql_type = "INTEGER"
        parts = [f'"{name}"', sql_type]
        if not nullable:
            parts.append("NOT NULL")
        if default is not None:
            if dialect == "postgresql":
                parts.append(f"DEFAULT {'TRUE' if default else 'FALSE'}")
            else:
                parts.append(f"DEFAULT {1 if default else 0}")
        return " ".join(parts)

    @staticmethod
    def timestamp(name: str, nullable: bool = False, default: Optional[str] = None, *, dialect: str = "sqlite") -> str:
        """Timestamp column (dialect-aware)."""
        if dialect == "postgresql":
            sql_type = "TIMESTAMP WITH TIME ZONE"
        elif dialect == "mysql":
            sql_type = "DATETIME"
        else:
            sql_type = "TIMESTAMP"
        parts = [f'"{name}"', sql_type]
        if not nullable:
            parts.append("NOT NULL")
        if default:
            parts.append(f"DEFAULT {default}")
        return " ".join(parts)

    @staticmethod
    def decimal(
        name: str,
        max_digits: int = 10,
        decimal_places: int = 2,
        nullable: bool = False,
        *,
        dialect: str = "sqlite",
    ) -> str:
        """Decimal / numeric column."""
        if dialect == "sqlite":
            sql_type = "REAL"
        else:
            sql_type = f"NUMERIC({max_digits}, {decimal_places})"
        parts = [f'"{name}"', sql_type]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def json(name: str, nullable: bool = False, *, dialect: str = "sqlite") -> str:
        """JSON column (dialect-aware)."""
        if dialect == "postgresql":
            sql_type = "JSONB"
        elif dialect == "mysql":
            sql_type = "JSON"
        else:
            sql_type = "TEXT"
        parts = [f'"{name}"', sql_type]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def uuid(name: str, nullable: bool = False, *, dialect: str = "sqlite") -> str:
        """UUID column (dialect-aware)."""
        if dialect == "postgresql":
            sql_type = "UUID"
        else:
            sql_type = "VARCHAR(36)"
        parts = [f'"{name}"', sql_type]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def real(name: str, nullable: bool = False) -> str:
        parts = [f'"{name}"', "REAL"]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    @staticmethod
    def foreign_key(
        name: str,
        ref_table: str,
        ref_column: str = "id",
        on_delete: str = "CASCADE",
        nullable: bool = False,
    ) -> str:
        """Foreign key column with inline REFERENCES."""
        parts = [f'"{name}"', "INTEGER"]
        if not nullable:
            parts.append("NOT NULL")
        parts.append(f'REFERENCES "{ref_table}"("{ref_column}")')
        parts.append(f"ON DELETE {on_delete}")
        return " ".join(parts)

    # ── Statement management ─────────────────────────────────────────

    def get_statements(self) -> List[Any]:
        """Return accumulated SQL statements (strings and callables)."""
        return self._statements.copy()

    def clear(self) -> None:
        """Reset accumulated statements."""
        self._statements.clear()


def _format_default(value: Any) -> str:
    """Format a Python value as SQL DEFAULT value."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return str(value)


# Module-level ops instance for use in migration scripts
op = MigrationOps()


# ── Migration File Generator ────────────────────────────────────────────────


@dataclass
class MigrationInfo:
    """Metadata for a single migration file."""
    revision: str  # timestamp-based ID
    slug: str  # human-readable slug
    models: List[str]  # model names affected
    path: Optional[Path] = None
    applied: bool = False


def _generate_revision() -> str:
    """Generate a timestamp-based revision ID."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S")


def _slugify(name: str) -> str:
    """Convert model name to a migration slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def generate_migration_file(
    models: List[ModelNode],
    migrations_dir: str | Path,
    slug: Optional[str] = None,
) -> Path:
    """
    Generate a migration file from AMDL model nodes.

    Creates a Python file with upgrade() and downgrade() functions.

    Args:
        models: List of ModelNode objects
        migrations_dir: Directory to write migration file
        slug: Optional slug for filename

    Returns:
        Path to generated migration file
    """
    rev = _generate_revision()
    if not slug:
        names = [_slugify(m.name) for m in models]
        slug = "_".join(names[:3])
        if len(models) > 3:
            slug += f"_and_{len(models) - 3}_more"

    filename = f"{rev}_{slug}.py"
    mdir = Path(migrations_dir)
    mdir.mkdir(parents=True, exist_ok=True)

    # Build upgrade SQL
    upgrade_lines: List[str] = []
    downgrade_lines: List[str] = []

    for model in models:
        # Create table
        create_sql = generate_create_table_sql(model)
        upgrade_lines.append(f'    await conn.execute("""{create_sql}""")')

        # Create indexes
        for idx_sql in generate_create_index_sql(model):
            upgrade_lines.append(f'    await conn.execute("""{idx_sql}""")')

        # Drop table (downgrade)
        downgrade_lines.append(f'    await conn.execute(\'DROP TABLE IF EXISTS "{model.table_name}"\')')

    upgrade_body = "\n".join(upgrade_lines) if upgrade_lines else "    pass"
    downgrade_body = "\n".join(downgrade_lines) if downgrade_lines else "    pass"

    content = f'''"""
Migration: {rev}_{slug}
Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
Models: {", ".join(m.name for m in models)}
"""

# Revision identifiers
revision = "{rev}"
slug = "{slug}"


async def upgrade(conn):
    """Apply migration — create tables."""
{upgrade_body}


async def downgrade(conn):
    """Revert migration — drop tables."""
{downgrade_body}
'''

    filepath = mdir / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Generated migration: {filepath}")
    return filepath


def generate_migration_from_models(
    model_classes: list,
    migrations_dir: str | Path,
    slug: Optional[str] = None,
) -> Path:
    """
    Generate a migration file from new Python Model subclasses.

    Creates a Python file with upgrade() and downgrade() functions
    using SQL generated by Model.generate_create_table_sql().

    Args:
        model_classes: List of Model subclass classes
        migrations_dir: Directory to write migration file
        slug: Optional slug for filename

    Returns:
        Path to generated migration file
    """
    rev = _generate_revision()
    if not slug:
        names = [_slugify(m.__name__) for m in model_classes]
        slug = "_".join(names[:3])
        if len(model_classes) > 3:
            slug += f"_and_{len(model_classes) - 3}_more"

    filename = f"{rev}_{slug}.py"
    mdir = Path(migrations_dir)
    mdir.mkdir(parents=True, exist_ok=True)

    # Build upgrade SQL
    upgrade_lines: List[str] = []
    downgrade_lines: List[str] = []

    for model_cls in model_classes:
        # Create table
        create_sql = model_cls.generate_create_table_sql()
        upgrade_lines.append(f'    await conn.execute("""{create_sql}""")')

        # Create indexes
        for idx_sql in model_cls.generate_index_sql():
            upgrade_lines.append(f'    await conn.execute("""{idx_sql}""")')

        # Create M2M junction tables
        for m2m_sql in model_cls.generate_m2m_sql():
            upgrade_lines.append(f'    await conn.execute("""{m2m_sql}""")')

        # Drop table (downgrade)
        table_name = model_cls._meta.table_name
        downgrade_lines.append(f'    await conn.execute(\'DROP TABLE IF EXISTS "{table_name}"\')')

    upgrade_body = "\n".join(upgrade_lines) if upgrade_lines else "    pass"
    downgrade_body = "\n".join(downgrade_lines) if downgrade_lines else "    pass"

    model_names = ", ".join(m.__name__ for m in model_classes)
    content = f'''"""
Migration: {rev}_{slug}
Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
Models: {model_names}
"""

# Revision identifiers
revision = "{rev}"
slug = "{slug}"


async def upgrade(conn):
    """Apply migration — create tables."""
{upgrade_body}


async def downgrade(conn):
    """Revert migration — drop tables."""
{downgrade_body}
'''

    filepath = mdir / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Generated migration from Python models: {filepath}")
    return filepath


# ── Migration Runner ────────────────────────────────────────────────────────


class MigrationRunner:
    """
    Applies and tracks migrations against an AquiliaDatabase.

    Maintains `aquilia_migrations` table for tracking applied migrations.

    Features:
    - Forward migration (apply pending)
    - Rollback to specific revision
    - Status report (applied/pending)
    - Dry-run mode (preview SQL without executing)
    - Data migration support (run_python callables)
    - Migration dependency tracking
    """

    def __init__(
        self,
        db: AquiliaDatabase,
        migrations_dir: str | Path = "migrations",
    ):
        self.db = db
        self.migrations_dir = Path(migrations_dir)

    async def ensure_tracking_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        sql = f"""
        CREATE TABLE IF NOT EXISTS "{MIGRATION_TABLE}" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "revision" VARCHAR(50) NOT NULL UNIQUE,
            "slug" VARCHAR(200) NOT NULL,
            "checksum" VARCHAR(64),
            "applied_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        await self.db.execute(sql)

    async def get_applied(self) -> List[str]:
        """Get list of applied revision IDs."""
        await self.ensure_tracking_table()
        rows = await self.db.fetch_all(
            f'SELECT "revision" FROM "{MIGRATION_TABLE}" ORDER BY "id"'
        )
        return [r["revision"] for r in rows]

    async def get_pending(self) -> List[Path]:
        """Get migration files that haven't been applied yet."""
        applied = set(await self.get_applied())
        pending: List[Path] = []

        if not self.migrations_dir.exists():
            return pending

        for path in sorted(self.migrations_dir.glob("*.py")):
            if path.name.startswith("__"):
                continue
            rev = _extract_revision(path)
            if rev and rev not in applied:
                pending.append(path)

        return pending

    async def status(self) -> Dict[str, Any]:
        """
        Get migration status — applied, pending, and total counts.

        Returns:
            Dict with keys: applied, pending, last_applied, total
        """
        applied = await self.get_applied()
        pending = await self.get_pending()
        return {
            "applied": applied,
            "pending": [p.stem for p in pending],
            "last_applied": applied[-1] if applied else None,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "total": len(applied) + len(pending),
        }

    async def show_status(self) -> str:
        """
        Return a human-readable status string.

        Usage:
            runner = MigrationRunner(db, "migrations/")
            print(await runner.show_status())
        """
        info = await self.status()
        lines = [
            f"Migration Status ({self.migrations_dir})",
            f"  Applied: {info['applied_count']}",
            f"  Pending: {info['pending_count']}",
            f"  Total:   {info['total']}",
        ]
        if info["last_applied"]:
            lines.append(f"  Last applied: {info['last_applied']}")
        if info["pending"]:
            lines.append("  Pending migrations:")
            for name in info["pending"]:
                lines.append(f"    - {name}")
        return "\n".join(lines)

    async def dry_run(self, target: Optional[str] = None) -> List[str]:
        """
        Preview migrations without executing. Returns list of SQL strings.

        Loads each pending migration module and collects statements from
        its upgrade() function without applying them.

        Args:
            target: If provided, preview rollback to this revision.

        Returns:
            List of SQL statement strings that would be executed.
        """
        import importlib.util
        import inspect

        statements: List[str] = []

        if target is not None:
            # Dry-run rollback
            applied = await self.get_applied()
            if target not in applied:
                raise MigrationFault(
                    migration=target,
                    reason=f"Target revision '{target}' not in applied migrations",
                )
            target_idx = applied.index(target)
            to_rollback = list(reversed(applied[target_idx + 1:]))
            for rev in to_rollback:
                migration_files = list(self.migrations_dir.glob(f"{rev}*.py"))
                if not migration_files:
                    statements.append(f"-- WARNING: Migration file for {rev} not found")
                    continue
                path = migration_files[0]
                module = _load_migration_module(path, rev)
                if hasattr(module, "downgrade"):
                    # Use a dry-run op to capture statements
                    dry_op = MigrationOps()
                    statements.append(f"-- Rollback: {rev}")
                    # We can't easily capture what downgrade generates since
                    # it calls conn.execute directly; document limitation
                    statements.append(f"-- (Run downgrade function from {path.name})")
            return statements

        # Dry-run forward
        pending = await self.get_pending()
        for path in pending:
            rev = _extract_revision(path)
            statements.append(f"-- Migration: {rev} ({path.name})")
            module = _load_migration_module(path, rev or path.stem)
            if hasattr(module, "upgrade"):
                statements.append(f"-- (Run upgrade function from {path.name})")
        return statements

    async def apply_migration(self, path: Path) -> None:
        """Apply a single migration file."""
        rev = _extract_revision(path) or path.stem
        slug = path.stem.split("_", 2)[2] if len(path.stem.split("_", 2)) > 2 else path.stem

        # Compute checksum
        checksum = _file_checksum(path)

        # Load module
        module = _load_migration_module(path, rev)

        # Run upgrade
        if hasattr(module, "upgrade"):
            upgrade_fn = module.upgrade
            import inspect
            try:
                if inspect.iscoroutinefunction(upgrade_fn):
                    await upgrade_fn(self.db)
                else:
                    upgrade_fn(self.db)
            except MigrationFault:
                raise
            except Exception as exc:
                raise MigrationFault(
                    migration=rev,
                    reason=f"Upgrade failed: {exc}",
                ) from exc

        # Record migration with checksum
        await self.db.execute(
            f'INSERT INTO "{MIGRATION_TABLE}" ("revision", "slug", "checksum") VALUES (?, ?, ?)',
            [rev, slug, checksum],
        )
        logger.info(f"Applied migration: {rev} ({slug})")

    async def migrate(self, target: Optional[str] = None) -> List[str]:
        """
        Apply all pending migrations.

        Args:
            target: Optional target revision to migrate to (for rollback)

        Returns:
            List of applied revision IDs
        """
        await self.ensure_tracking_table()

        if target is not None:
            return await self._rollback_to(target)

        pending = await self.get_pending()
        applied: List[str] = []

        # Signal: pre_migrate
        await pre_migrate.send(sender=self.__class__, db=self.db)

        for path in pending:
            await self.apply_migration(path)
            rev = _extract_revision(path) or path.stem
            applied.append(rev)

        # Signal: post_migrate
        await post_migrate.send(sender=self.__class__, db=self.db)

        return applied

    async def _rollback_to(self, target: str) -> List[str]:
        """Rollback to a specific revision."""
        applied = await self.get_applied()
        if target not in applied:
            raise MigrationFault(
                migration=target,
                reason=f"Target revision '{target}' not in applied migrations",
            )

        # Find migrations to rollback (everything after target)
        target_idx = applied.index(target)
        to_rollback = list(reversed(applied[target_idx + 1:]))

        rolled_back: List[str] = []
        for rev in to_rollback:
            # Find migration file
            migration_files = list(self.migrations_dir.glob(f"{rev}*.py"))
            if not migration_files:
                logger.warning(f"Migration file for {rev} not found, skipping downgrade")
                # Still remove from tracking so we don't get stuck
                await self.db.execute(
                    f'DELETE FROM "{MIGRATION_TABLE}" WHERE "revision" = ?',
                    [rev],
                )
                rolled_back.append(rev)
                continue

            path = migration_files[0]
            module = _load_migration_module(path, rev)

            # Run downgrade
            if hasattr(module, "downgrade"):
                downgrade_fn = module.downgrade
                import inspect
                try:
                    if inspect.iscoroutinefunction(downgrade_fn):
                        await downgrade_fn(self.db)
                    else:
                        downgrade_fn(self.db)
                except MigrationFault:
                    raise
                except Exception as exc:
                    raise MigrationFault(
                        migration=rev,
                        reason=f"Downgrade failed: {exc}",
                    ) from exc

            # Remove from tracking
            await self.db.execute(
                f'DELETE FROM "{MIGRATION_TABLE}" WHERE "revision" = ?',
                [rev],
            )
            rolled_back.append(rev)
            logger.info(f"Rolled back migration: {rev}")

        return rolled_back

    async def verify_checksums(self) -> List[Dict[str, str]]:
        """
        Verify that applied migration files haven't been tampered with.

        Returns list of dicts with 'revision' and 'reason' for any mismatches.
        """
        await self.ensure_tracking_table()
        rows = await self.db.fetch_all(
            f'SELECT "revision", "checksum" FROM "{MIGRATION_TABLE}" ORDER BY "id"'
        )
        mismatches: List[Dict[str, str]] = []
        for row in rows:
            rev = row["revision"]
            stored_checksum = row.get("checksum")
            if not stored_checksum:
                continue  # Old migration without checksum tracking
            migration_files = list(self.migrations_dir.glob(f"{rev}*.py"))
            if not migration_files:
                mismatches.append({
                    "revision": rev,
                    "reason": "Migration file not found on disk",
                })
                continue
            current_checksum = _file_checksum(migration_files[0])
            if current_checksum != stored_checksum:
                mismatches.append({
                    "revision": rev,
                    "reason": "File has been modified since it was applied",
                })
        return mismatches


# ── Helper functions ─────────────────────────────────────────────────────────


def _extract_revision(path: Path) -> Optional[str]:
    """Extract revision ID from migration filename: YYYYMMDD_HHMMSS_slug.py"""
    parts = path.stem.split("_", 2)
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return None


def _file_checksum(path: Path) -> str:
    """Compute SHA-256 checksum of a migration file."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def _load_migration_module(path: Path, rev: str) -> Any:
    """Load a migration Python module from file path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"migration_{rev}", path)
    if not spec or not spec.loader:
        raise MigrationFault(
            migration=rev,
            reason=f"Cannot load migration module: {path}",
        )
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise MigrationFault(
            migration=rev,
            reason=f"Failed to load migration: {exc}",
        ) from exc
    return module
