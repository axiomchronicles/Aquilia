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

logger = logging.getLogger("aquilia.models.migrations")

MIGRATION_TABLE = "aquilia_migrations"


# ── Migration Operations ────────────────────────────────────────────────────


class MigrationOps:
    """
    Migration operation builder — used inside migration scripts.

    Usage in generated migration files:
        from aquilia.models.migrations import op

        def upgrade(conn):
            op.create_table("aq_user", [...])

        def downgrade(conn):
            op.drop_table("aq_user")
    """

    def __init__(self) -> None:
        self._statements: List[str] = []

    def create_table(self, name: str, columns: List[str]) -> None:
        """Generate CREATE TABLE statement."""
        body = ",\n  ".join(columns)
        self._statements.append(f'CREATE TABLE IF NOT EXISTS "{name}" (\n  {body}\n);')

    def drop_table(self, name: str) -> None:
        """Generate DROP TABLE statement."""
        self._statements.append(f'DROP TABLE IF EXISTS "{name}";')

    def add_column(self, table: str, column_def: str) -> None:
        """Generate ALTER TABLE ADD COLUMN."""
        self._statements.append(f'ALTER TABLE "{table}" ADD COLUMN {column_def};')

    def create_index(self, name: str, table: str, columns: List[str], unique: bool = False) -> None:
        """Generate CREATE INDEX."""
        u = "UNIQUE " if unique else ""
        cols = ", ".join(f'"{c}"' for c in columns)
        self._statements.append(
            f'CREATE {u}INDEX IF NOT EXISTS "{name}" ON "{table}" ({cols});'
        )

    def drop_index(self, name: str) -> None:
        """Generate DROP INDEX."""
        self._statements.append(f'DROP INDEX IF EXISTS "{name}";')

    def execute_sql(self, sql: str) -> None:
        """Add raw SQL."""
        self._statements.append(sql)

    # ── Column type helpers ──────────────────────────────────────────

    @staticmethod
    def pk(name: str = "id") -> str:
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
    def boolean(name: str, nullable: bool = False, default: Optional[bool] = None) -> str:
        parts = [f'"{name}"', "INTEGER"]
        if not nullable:
            parts.append("NOT NULL")
        if default is not None:
            parts.append(f"DEFAULT {1 if default else 0}")
        return " ".join(parts)

    @staticmethod
    def timestamp(name: str, nullable: bool = False, default: Optional[str] = None) -> str:
        parts = [f'"{name}"', "TIMESTAMP"]
        if not nullable:
            parts.append("NOT NULL")
        if default:
            parts.append(f"DEFAULT {default}")
        return " ".join(parts)

    @staticmethod
    def real(name: str, nullable: bool = False) -> str:
        parts = [f'"{name}"', "REAL"]
        if not nullable:
            parts.append("NOT NULL")
        return " ".join(parts)

    def get_statements(self) -> List[str]:
        """Return accumulated SQL statements."""
        return self._statements.copy()

    def clear(self) -> None:
        """Reset accumulated statements."""
        self._statements.clear()


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
    """

    def __init__(self, db: AquiliaDatabase, migrations_dir: str | Path = "migrations"):
        self.db = db
        self.migrations_dir = Path(migrations_dir)

    async def ensure_tracking_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        sql = f"""
        CREATE TABLE IF NOT EXISTS "{MIGRATION_TABLE}" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "revision" VARCHAR(50) NOT NULL UNIQUE,
            "slug" VARCHAR(200) NOT NULL,
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
            # Extract revision from filename: YYYYMMDD_HHMMSS_slug.py
            parts = path.stem.split("_", 2)
            if len(parts) >= 2:
                rev = f"{parts[0]}_{parts[1]}"
                if rev not in applied:
                    pending.append(path)

        return pending

    async def apply_migration(self, path: Path) -> None:
        """Apply a single migration file."""
        import importlib.util

        # Extract revision
        parts = path.stem.split("_", 2)
        rev = f"{parts[0]}_{parts[1]}"
        slug = parts[2] if len(parts) > 2 else path.stem

        # Load module
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

        # Record migration
        await self.db.execute(
            f'INSERT INTO "{MIGRATION_TABLE}" ("revision", "slug") VALUES (?, ?)',
            [rev, slug],
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

        for path in pending:
            await self.apply_migration(path)
            parts = path.stem.split("_", 2)
            rev = f"{parts[0]}_{parts[1]}"
            applied.append(rev)

        return applied

    async def _rollback_to(self, target: str) -> List[str]:
        """Rollback to a specific revision."""
        import importlib.util

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
                continue

            path = migration_files[0]
            spec = importlib.util.spec_from_file_location(f"migration_{rev}", path)
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                raise MigrationFault(
                    migration=rev,
                    reason=f"Failed to load migration for rollback: {exc}",
                ) from exc

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
