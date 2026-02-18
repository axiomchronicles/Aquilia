"""
Aquilia Migration Runner — executes DSL and raw-SQL migrations.

Compiles DSL operations to backend SQL, runs migrations transactionally
where possible, and records applied migrations in ``aquilia_migrations``.

Features:
- DSL migration support (operations list)
- Legacy raw-SQL migration support (upgrade/downgrade functions)
- Transactional execution (per-migration)
- --fake flag (mark as applied without running)
- --plan flag (dry-run SQL preview)
- Safe SQLite probing (no WAL/SHM creation)
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import inspect
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..db.engine import AquiliaDatabase
from ..faults.domains import MigrationFault, MigrationConflictFault, SchemaFault
from .migration_dsl import Migration, Operation, RunPython, RunSQL

logger = logging.getLogger("aquilia.models.migration_runner")

MIGRATION_TABLE = "aquilia_migrations"


@dataclass
class MigrationRecord:
    """A record in the aquilia_migrations tracking table."""
    revision: str
    slug: str
    checksum: str
    applied_at: Optional[str] = None


class MigrationRunner:
    """
    Applies and tracks migrations against an AquiliaDatabase.

    Supports both new DSL migrations (with ``operations`` list)
    and legacy raw-SQL migrations (with ``upgrade``/``downgrade`` functions).

    Usage:
        runner = MigrationRunner(db, "migrations/")
        await runner.migrate()              # Apply all pending
        await runner.migrate(fake=True)     # Mark applied without executing
        stmts = await runner.plan()         # Preview SQL
        await runner.migrate(target="rev")  # Rollback to revision
    """

    def __init__(
        self,
        db: AquiliaDatabase,
        migrations_dir: str | Path = "migrations",
        *,
        dialect: str = "sqlite",
    ):
        self.db = db
        self.migrations_dir = Path(migrations_dir)
        self.dialect = dialect

    async def ensure_tracking_table(self) -> None:
        """Create the aquilia_migrations tracking table if it doesn't exist."""
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
        """Get list of applied revision IDs, ordered by application time."""
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
        """Get migration status — applied, pending, totals."""
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
        """Return a human-readable status string."""
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

    async def plan(self, target: Optional[str] = None) -> List[str]:
        """
        Preview migrations without executing (--plan / dry-run).

        Returns list of SQL statements that would be executed.
        """
        statements: List[str] = []
        pending = await self.get_pending()

        for path in pending:
            rev = _extract_revision(path) or path.stem
            statements.append(f"-- Migration: {rev} ({path.name})")
            module = _load_migration_module(path, rev)

            # Check for DSL migration
            if hasattr(module, "operations"):
                migration_obj = _build_migration_from_module(module)
                for sql in migration_obj.compile_upgrade(self.dialect):
                    statements.append(sql)
            elif hasattr(module, "upgrade"):
                statements.append(f"-- (Legacy: runs upgrade() from {path.name})")

        return statements

    async def sqlmigrate(self, revision: str) -> List[str]:
        """
        Get the SQL for a specific migration (aq db sqlmigrate).
        """
        path = self._find_migration_file(revision)
        if not path:
            raise MigrationFault(
                migration=revision,
                reason=f"Migration file not found for revision '{revision}'",
            )

        module = _load_migration_module(path, revision)

        if hasattr(module, "operations"):
            migration_obj = _build_migration_from_module(module)
            return migration_obj.compile_upgrade(self.dialect)
        else:
            # Legacy — try to extract SQL from source
            return _extract_sql_from_source(path)

    async def migrate(
        self,
        *,
        target: Optional[str] = None,
        fake: bool = False,
        database: Optional[str] = None,
    ) -> List[str]:
        """
        Apply all pending migrations.

        Args:
            target: Target revision for rollback (None = forward all)
            fake: If True, mark as applied without executing SQL
            database: Database alias (for multi-db, currently unused)

        Returns:
            List of applied revision IDs
        """
        from .signals import pre_migrate, post_migrate

        await self.ensure_tracking_table()

        if target is not None:
            return await self._rollback_to(target, fake=fake)

        pending = await self.get_pending()
        applied: List[str] = []

        # Signal: pre_migrate
        await pre_migrate.send(sender=self.__class__, db=self.db)

        for path in pending:
            await self._apply_migration(path, fake=fake)
            rev = _extract_revision(path) or path.stem
            applied.append(rev)

        # Signal: post_migrate
        await post_migrate.send(sender=self.__class__, db=self.db)

        return applied

    async def _apply_migration(self, path: Path, *, fake: bool = False) -> None:
        """Apply a single migration file."""
        rev = _extract_revision(path) or path.stem
        slug = _extract_slug(path)
        checksum = _file_checksum(path)

        module = _load_migration_module(path, rev)

        if not fake:
            if hasattr(module, "operations"):
                # DSL migration
                migration_obj = _build_migration_from_module(module)
                await self._execute_dsl_migration(migration_obj)
            elif hasattr(module, "upgrade"):
                # Legacy raw-SQL migration
                upgrade_fn = module.upgrade
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
            else:
                logger.warning(f"Migration {rev} has no operations or upgrade(): skipping execution")

        # Record migration
        await self.db.execute(
            f'INSERT INTO "{MIGRATION_TABLE}" ("revision", "slug", "checksum") VALUES (?, ?, ?)',
            [rev, slug, checksum],
        )
        action = "Faked" if fake else "Applied"
        logger.info(f"{action} migration: {rev} ({slug})")

    async def _execute_dsl_migration(self, migration: Migration) -> None:
        """Execute a DSL migration transactionally."""
        stmts = migration.compile_upgrade(self.dialect)
        python_ops = migration.get_python_ops()

        try:
            async with self.db.transaction():
                for sql in stmts:
                    if sql.startswith("--"):
                        continue  # Skip comments
                    await self.db.execute(sql)

                for py_op in python_ops:
                    if py_op.forward:
                        if inspect.iscoroutinefunction(py_op.forward):
                            await py_op.forward(self.db)
                        else:
                            py_op.forward(self.db)
        except MigrationFault:
            raise
        except Exception as exc:
            raise MigrationFault(
                migration=migration.revision,
                reason=f"DSL migration failed: {exc}",
            ) from exc

    async def _rollback_to(self, target: str, *, fake: bool = False) -> List[str]:
        """Rollback to a specific revision."""
        applied = await self.get_applied()
        if target not in applied:
            raise MigrationFault(
                migration=target,
                reason=f"Target revision '{target}' not in applied migrations",
            )

        target_idx = applied.index(target)
        to_rollback = list(reversed(applied[target_idx + 1:]))

        rolled_back: List[str] = []
        for rev in to_rollback:
            path = self._find_migration_file(rev)

            if not fake and path:
                module = _load_migration_module(path, rev)
                if hasattr(module, "operations"):
                    migration_obj = _build_migration_from_module(module)
                    stmts = migration_obj.compile_downgrade(self.dialect)
                    try:
                        async with self.db.transaction():
                            for sql in stmts:
                                if sql.startswith("--"):
                                    continue
                                await self.db.execute(sql)
                    except Exception as exc:
                        raise MigrationFault(migration=rev, reason=f"Rollback failed: {exc}") from exc
                elif hasattr(module, "downgrade"):
                    downgrade_fn = module.downgrade
                    try:
                        if inspect.iscoroutinefunction(downgrade_fn):
                            await downgrade_fn(self.db)
                        else:
                            downgrade_fn(self.db)
                    except Exception as exc:
                        raise MigrationFault(migration=rev, reason=f"Rollback failed: {exc}") from exc

            # Remove from tracking
            await self.db.execute(
                f'DELETE FROM "{MIGRATION_TABLE}" WHERE "revision" = ?', [rev],
            )
            rolled_back.append(rev)
            action = "Faked rollback" if fake else "Rolled back"
            logger.info(f"{action} migration: {rev}")

        return rolled_back

    def _find_migration_file(self, revision: str) -> Optional[Path]:
        """Find migration file by revision prefix."""
        if not self.migrations_dir.exists():
            return None
        candidates = list(self.migrations_dir.glob(f"{revision}*.py"))
        return candidates[0] if candidates else None

    async def verify_checksums(self) -> List[Dict[str, str]]:
        """Verify that applied migration files haven't been tampered with."""
        await self.ensure_tracking_table()
        rows = await self.db.fetch_all(
            f'SELECT "revision", "checksum" FROM "{MIGRATION_TABLE}" ORDER BY "id"'
        )
        mismatches: List[Dict[str, str]] = []
        for row in rows:
            rev = row["revision"]
            stored = row.get("checksum")
            if not stored:
                continue
            path = self._find_migration_file(rev)
            if not path:
                mismatches.append({"revision": rev, "reason": "File not found on disk"})
                continue
            current = _file_checksum(path)
            if current != stored:
                mismatches.append({"revision": rev, "reason": "File modified since applied"})
        return mismatches


# ── Safe SQLite probing ─────────────────────────────────────────────────────


def check_db_exists(db_url: str) -> bool:
    """
    Check if a SQLite database file exists WITHOUT creating WAL/SHM files.

    Uses os.path.exists() for file-based SQLite databases.
    Returns True for :memory: and non-SQLite databases.
    """
    if not db_url.startswith("sqlite"):
        return True  # Non-SQLite databases are assumed to exist

    path = _extract_sqlite_path(db_url)
    if path == ":memory:":
        return True

    return os.path.exists(path)


def check_migrations_applied(db_url: str, migrations_dir: str | Path = "migrations") -> bool:
    """
    Check if there are unapplied migrations WITHOUT creating WAL/SHM.

    For SQLite, uses file:...?mode=ro URI to read-only probe.
    Returns True if all migrations are applied (or no migrations exist).
    """
    import asyncio

    if not check_db_exists(db_url):
        return False

    path = _extract_sqlite_path(db_url)
    if path == ":memory:":
        return True

    mdir = Path(migrations_dir)
    if not mdir.exists():
        return True  # No migrations directory = nothing to apply

    migration_files = sorted(f for f in mdir.glob("*.py") if not f.name.startswith("__"))
    if not migration_files:
        return True

    # Read-only probe using sqlite3 (not aiosqlite) to avoid WAL
    try:
        import sqlite3
        # Use mode=ro to prevent WAL/SHM creation
        ro_uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(ro_uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [MIGRATION_TABLE],
            )
            if not cursor.fetchone():
                conn.close()
                return False  # No migration table → not migrated

            cursor = conn.execute(
                f'SELECT "revision" FROM "{MIGRATION_TABLE}" ORDER BY "id"'
            )
            applied = {row["revision"] for row in cursor.fetchall()}

            for path in migration_files:
                rev = _extract_revision(path)
                if rev and rev not in applied:
                    conn.close()
                    return False
            conn.close()
            return True
        except sqlite3.OperationalError:
            conn.close()
            return False
    except Exception:
        return False


def _extract_sqlite_path(url: str) -> str:
    """Extract the file path from a sqlite:/// URL."""
    for prefix in ("sqlite:///", "sqlite://"):
        if url.startswith(prefix):
            return url[len(prefix):] or ":memory:"
    return url.replace("sqlite:", "").lstrip("/") or ":memory:"


# ── Helper functions ─────────────────────────────────────────────────────────


def _extract_revision(path: Path) -> Optional[str]:
    """Extract revision ID from filename: YYYYMMDD_HHMMSS_slug.py"""
    parts = path.stem.split("_", 2)
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return None


def _extract_slug(path: Path) -> str:
    """Extract slug from filename."""
    parts = path.stem.split("_", 2)
    if len(parts) >= 3:
        return parts[2]
    return path.stem


def _file_checksum(path: Path) -> str:
    """Compute SHA-256 checksum of a migration file."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def _load_migration_module(path: Path, rev: str) -> Any:
    """Load a migration Python module from file path."""
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


def _build_migration_from_module(module: Any) -> Migration:
    """Build a Migration object from a loaded DSL migration module."""
    meta = getattr(module, "Meta", None)
    revision = getattr(meta, "revision", "") if meta else getattr(module, "revision", "")
    slug = getattr(meta, "slug", "") if meta else getattr(module, "slug", "")
    models = getattr(meta, "models", []) if meta else getattr(module, "models", [])
    deps = getattr(meta, "dependencies", []) if meta else []
    operations = getattr(module, "operations", [])

    return Migration(
        revision=revision,
        slug=slug,
        models=models,
        dependencies=deps,
        operations=operations,
    )


def _extract_sql_from_source(path: Path) -> List[str]:
    """Extract SQL from a legacy migration file's source code."""
    import re
    source = path.read_text(encoding="utf-8")
    stmts: List[str] = []

    # Triple-quoted SQL
    for match in re.findall(r'execute\s*\(\s*"""(.*?)"""\s*\)', source, re.DOTALL):
        stmts.append(match.strip())
    for match in re.findall(r"execute\s*\(\s*'''(.*?)'''\s*\)", source, re.DOTALL):
        stmts.append(match.strip())
    # Single-quoted SQL
    for match in re.findall(r"execute\s*\(\s*'(.*?)'\s*\)", source, re.DOTALL):
        stmts.append(match.strip())

    return stmts
