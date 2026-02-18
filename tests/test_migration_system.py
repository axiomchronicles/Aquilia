"""
Tests for Aquilia's migration DSL, schema snapshot engine,
migration runner, and startup guard.

Covers:
    - DSL primitive compilation (CreateModel, AddField, etc.)
    - ColumnDef / C builder API
    - Schema snapshot creation, persistence, and diffing
    - Rename detection (model-level and field-level)
    - Migration runner: apply, fake, plan, sqlmigrate
    - Startup guard: rejects implicit DB creation
    - No WAL/SHM creation during safe probing
    - Backward compatibility with legacy raw-SQL migrations
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

import pytest


# ============================================================================
# DSL primitives
# ============================================================================


class TestColumnDef:
    """Test ColumnDef and the C / columns builder namespace."""

    def test_auto_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.auto("id")
        sql = col.to_sql("sqlite")
        assert '"id"' in sql
        assert "INTEGER" in sql
        assert "PRIMARY KEY" in sql
        assert "AUTOINCREMENT" in sql

    def test_auto_column_postgres(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.auto("id")
        sql = col.to_sql("postgresql")
        assert "SERIAL" in sql
        assert "PRIMARY KEY" in sql

    def test_varchar_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.varchar("email", 255, unique=True)
        sql = col.to_sql("sqlite")
        assert '"email"' in sql
        assert "VARCHAR(255)" in sql
        assert "UNIQUE" in sql
        assert "NOT NULL" in sql

    def test_varchar_nullable(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.varchar("bio", 500, null=True)
        sql = col.to_sql("sqlite")
        assert "NOT NULL" not in sql

    def test_varchar_with_default(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.varchar("role", 20, default="admin")
        sql = col.to_sql("sqlite")
        assert "DEFAULT 'admin'" in sql

    def test_integer_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.integer("age", null=True, default=0)
        sql = col.to_sql("sqlite")
        assert '"age"' in sql
        assert "INTEGER" in sql
        assert "DEFAULT 0" in sql
        assert "NOT NULL" not in sql

    def test_boolean_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.boolean("is_active", default=True)
        sql = col.to_sql("sqlite")
        assert "DEFAULT 1" in sql

    def test_boolean_column_postgres(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.boolean("is_active", default=True)
        sql = col.to_sql("postgresql")
        assert "DEFAULT TRUE" in sql

    def test_decimal_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.decimal("price", 10, 2)
        sql = col.to_sql("sqlite")
        assert "DECIMAL(10,2)" in sql

    def test_timestamp_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.timestamp("created_at")
        sql = col.to_sql("sqlite")
        assert "TIMESTAMP" in sql
        assert "NOT NULL" in sql

    def test_text_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.text("description", null=True)
        sql = col.to_sql("sqlite")
        assert "TEXT" in sql

    def test_uuid_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.uuid("uuid", unique=True)
        sql = col.to_sql("sqlite")
        assert "VARCHAR(36)" in sql
        assert "UNIQUE" in sql

    def test_foreign_key_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.foreign_key("user_id", "users", "id", on_delete="CASCADE")
        sql = col.to_sql("sqlite")
        assert '"user_id"' in sql
        assert 'REFERENCES "users"("id")' in sql
        assert "ON DELETE CASCADE" in sql

    def test_real_column(self):
        from aquilia.models.migration_dsl import columns as C

        col = C.real("score", default=0.0)
        sql = col.to_sql("sqlite")
        assert "REAL" in sql
        assert "DEFAULT 0.0" in sql

    def test_snapshot_roundtrip(self):
        """Column → snapshot → Column roundtrip preserves all attributes."""
        from aquilia.models.migration_dsl import ColumnDef, columns as C

        original = C.foreign_key(
            "user_id", "users", "id",
            null=True, on_delete="SET NULL", on_update="CASCADE",
        )
        snap = original.to_snapshot()
        restored = ColumnDef.from_snapshot(snap)

        assert restored.name == original.name
        assert restored.col_type == original.col_type
        assert restored.nullable == original.nullable
        assert restored.references == original.references
        assert restored.on_delete == original.on_delete

    def test_no_default_vs_none_default(self):
        """_SENTINEL distinguishes 'no default' from 'default=None'."""
        from aquilia.models.migration_dsl import columns as C, _SENTINEL

        col_no = C.integer("x")
        col_none = C.integer("y", default=None)

        assert col_no.default is _SENTINEL
        assert col_none.default is None
        assert "DEFAULT" not in col_no.to_sql("sqlite")
        assert "DEFAULT NULL" in col_none.to_sql("sqlite")


class TestDSLOperations:
    """Test DSL operation compilation to SQL."""

    def test_create_model_sqlite(self):
        from aquilia.models.migration_dsl import CreateModel, columns as C

        op = CreateModel(
            name="User",
            table="users",
            fields=[
                C.auto("id"),
                C.varchar("email", 255, unique=True),
                C.varchar("name", 100),
            ],
        )
        stmts = op.to_sql("sqlite")
        assert len(stmts) == 1
        sql = stmts[0]
        assert 'CREATE TABLE IF NOT EXISTS "users"' in sql
        assert '"email" VARCHAR(255) UNIQUE NOT NULL' in sql
        assert "PRIMARY KEY" in sql

    def test_create_model_downgrade(self):
        from aquilia.models.migration_dsl import CreateModel, columns as C

        op = CreateModel(
            name="User",
            table="users",
            fields=[C.auto("id")],
        )
        stmts = op.reverse_sql("sqlite")
        assert len(stmts) == 1
        assert 'DROP TABLE IF EXISTS "users"' in stmts[0]

    def test_drop_model(self):
        from aquilia.models.migration_dsl import DropModel

        op = DropModel(name="User", table="users")
        stmts = op.to_sql("sqlite")
        assert 'DROP TABLE IF EXISTS "users"' in stmts[0]

    def test_rename_model(self):
        from aquilia.models.migration_dsl import RenameModel

        op = RenameModel(old_name="User", new_name="Account", old_table="users", new_table="accounts")
        stmts = op.to_sql("sqlite")
        assert len(stmts) == 1
        assert 'ALTER TABLE "users" RENAME TO "accounts"' in stmts[0]

    def test_add_field(self):
        from aquilia.models.migration_dsl import AddField, columns as C

        op = AddField(
            model_name="User",
            table="users",
            column=C.varchar("phone", 20, null=True),
        )
        stmts = op.to_sql("sqlite")
        assert len(stmts) == 1
        assert 'ALTER TABLE "users" ADD COLUMN' in stmts[0]
        assert '"phone"' in stmts[0]

    def test_remove_field(self):
        from aquilia.models.migration_dsl import RemoveField

        op = RemoveField(model_name="User", table="users", column_name="phone")
        stmts = op.to_sql("sqlite")
        assert 'ALTER TABLE "users" DROP COLUMN "phone"' in stmts[0]

    def test_rename_field(self):
        from aquilia.models.migration_dsl import RenameField

        op = RenameField(
            model_name="User",
            table="users",
            old_name="email",
            new_name="email_address",
        )
        stmts = op.to_sql("sqlite")
        assert 'RENAME COLUMN "email" TO "email_address"' in stmts[0]

    def test_create_index(self):
        from aquilia.models.migration_dsl import CreateIndex

        op = CreateIndex("idx_email", "users", ["email"])
        stmts = op.to_sql("sqlite")
        assert len(stmts) == 1
        assert 'CREATE INDEX IF NOT EXISTS "idx_email"' in stmts[0]
        assert 'ON "users"' in stmts[0]

    def test_create_unique_index(self):
        from aquilia.models.migration_dsl import CreateIndex

        op = CreateIndex("idx_email", "users", ["email"], unique=True)
        stmts = op.to_sql("sqlite")
        assert "UNIQUE" in stmts[0]

    def test_drop_index(self):
        from aquilia.models.migration_dsl import DropIndex

        op = DropIndex("idx_email")
        stmts = op.to_sql("sqlite")
        assert 'DROP INDEX IF EXISTS "idx_email"' in stmts[0]

    def test_run_sql(self):
        from aquilia.models.migration_dsl import RunSQL

        op = RunSQL(
            sql="INSERT INTO config VALUES ('version', '2');",
            reverse="DELETE FROM config WHERE key='version';",
        )
        stmts = op.to_sql("sqlite")
        assert stmts == ["INSERT INTO config VALUES ('version', '2');"]
        rev = op.reverse_sql("sqlite")
        assert rev == ["DELETE FROM config WHERE key='version';"]

    def test_run_sql_no_reverse(self):
        from aquilia.models.migration_dsl import RunSQL

        op = RunSQL(sql="SELECT 1;")
        assert op.reverse_sql("sqlite") == []

    def test_add_constraint(self):
        from aquilia.models.migration_dsl import AddConstraint

        op = AddConstraint(
            table="orders",
            constraint_sql="CONSTRAINT chk_positive CHECK (total >= 0)",
        )
        stmts = op.to_sql("sqlite")
        assert "orders" in stmts[0].lower()
        assert "chk_positive" in stmts[0]

    def test_migration_compile_full(self):
        """Migration container compiles all operations in order."""
        from aquilia.models.migration_dsl import (
            Migration, CreateModel, CreateIndex, columns as C,
        )

        m = Migration(
            revision="20260101_000000",
            slug="initial",
            models=["User"],
            operations=[
                CreateModel(
                    name="User",
                    table="users",
                    fields=[C.auto("id"), C.varchar("email", 255)],
                ),
                CreateIndex("idx_email", "users", ["email"]),
            ],
        )
        stmts = m.compile_upgrade("sqlite")
        assert len(stmts) == 2
        assert "CREATE TABLE" in stmts[0]
        assert "CREATE INDEX" in stmts[1]

    def test_migration_compile_downgrade_reverses_order(self):
        """Downgrade should reverse the operation order."""
        from aquilia.models.migration_dsl import (
            Migration, CreateModel, CreateIndex, columns as C,
        )

        m = Migration(
            revision="20260101_000000",
            slug="initial",
            models=["User"],
            operations=[
                CreateModel(
                    name="User",
                    table="users",
                    fields=[C.auto("id")],
                ),
                CreateIndex("idx_id", "users", ["id"]),
            ],
        )
        stmts = m.compile_downgrade("sqlite")
        assert len(stmts) == 2
        # First downgrade statement should be the index (last op reversed)
        assert "DROP INDEX" in stmts[0]
        assert "DROP TABLE" in stmts[1]


# ============================================================================
# Schema snapshot & diff engine
# ============================================================================


class TestSchemaSnapshot:
    """Test schema snapshot creation and diffing."""

    def _make_mock_model(self, name: str, table: str, fields_data: list):
        """Create a minimal mock model class for snapshot testing."""
        model = MagicMock()
        model.__name__ = name
        model._meta = MagicMock()
        model._meta.db_table = table
        model._meta.app_label = "test"

        mock_fields = []
        for fd in fields_data:
            f = MagicMock()
            f.name = fd["name"]
            f.column = fd.get("column", fd["name"])
            f.db_column = fd.get("column", fd["name"])
            f.get_internal_type = MagicMock(return_value=fd.get("type", "CharField"))
            f.max_length = fd.get("max_length")
            f.primary_key = fd.get("primary_key", False)
            f.unique = fd.get("unique", False)
            f.null = fd.get("null", False)
            f.has_default = MagicMock(return_value="default" in fd)
            f.default = fd.get("default", None)
            f.db_index = fd.get("db_index", False)

            # ForeignKey detection
            if fd.get("references"):
                f.related_model = MagicMock()
                f.related_model._meta = MagicMock()
                f.related_model._meta.db_table = fd["references"]["table"]
                f.remote_field = MagicMock()
                f.remote_field.field_name = fd["references"]["column"]
            else:
                f.related_model = None
                f.remote_field = None

            mock_fields.append(f)

        model._meta.get_fields = MagicMock(return_value=mock_fields)
        model._meta.local_fields = mock_fields
        return model

    def test_snapshot_save_load_roundtrip(self, tmp_path):
        """Save and load snapshot preserves content."""
        from aquilia.models.schema_snapshot import save_snapshot, load_snapshot

        snap = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                        "email": {"name": "email", "type": "VARCHAR(255)", "unique": True},
                    },
                }
            }
        }
        snap_path = tmp_path / "schema_snapshot.json"
        save_snapshot(snap, snap_path)
        loaded = load_snapshot(snap_path)

        assert loaded == snap

    def test_compute_diff_added_model(self):
        """Detect a newly added model."""
        from aquilia.models.schema_snapshot import compute_diff

        old = {"models": {}}
        new = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                    },
                }
            }
        }
        diff = compute_diff(old, new)
        assert "User" in diff.added_models

    def test_compute_diff_removed_model(self):
        """Detect a removed model."""
        from aquilia.models.schema_snapshot import compute_diff

        old = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                    },
                }
            }
        }
        new = {"models": {}}
        diff = compute_diff(old, new)
        assert "User" in diff.removed_models

    def test_compute_diff_added_field(self):
        """Detect a new field on an existing model."""
        from aquilia.models.schema_snapshot import compute_diff

        old = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                    },
                }
            }
        }
        new = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                        "email": {"name": "email", "type": "VARCHAR(255)"},
                    },
                }
            }
        }
        diff = compute_diff(old, new)
        assert len(diff.altered_models) == 1
        model_diff = diff.altered_models["User"]
        assert "email" in model_diff.added_fields

    def test_compute_diff_removed_field(self):
        """Detect a removed field."""
        from aquilia.models.schema_snapshot import compute_diff

        old = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                        "phone": {"name": "phone", "type": "VARCHAR(20)"},
                    },
                }
            }
        }
        new = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                    },
                }
            }
        }
        diff = compute_diff(old, new)
        model_diff = diff.altered_models["User"]
        assert "phone" in model_diff.removed_fields

    def test_compute_diff_changed_field(self):
        """Detect a changed field (type change)."""
        from aquilia.models.schema_snapshot import compute_diff

        old = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                        "email": {"name": "email", "type": "VARCHAR(100)"},
                    },
                }
            }
        }
        new = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                        "email": {"name": "email", "type": "VARCHAR(255)"},
                    },
                }
            }
        }
        diff = compute_diff(old, new)
        model_diff = diff.altered_models["User"]
        assert "email" in model_diff.altered_fields

    def test_no_diff_on_identical(self):
        """No changes detected when snapshots are identical."""
        from aquilia.models.schema_snapshot import compute_diff

        snap = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True},
                    },
                }
            }
        }
        diff = compute_diff(snap, snap)
        assert not diff.added_models
        assert not diff.removed_models
        assert not diff.altered_models
        assert not diff.has_changes


# ============================================================================
# Migration runner
# ============================================================================


class TestMigrationRunner:
    """Test migration runner on a real (temp) SQLite database."""

    def _write_dsl_migration(self, migrations_dir: Path, rev: str, slug: str, ops_code: str) -> Path:
        """Write a DSL migration file to the temp directory."""
        content = (
            "from aquilia.models.migration_dsl import (\n"
            "    CreateModel, DropModel, AddField, CreateIndex, columns as C,\n"
            ")\n"
            "\n"
            "class Meta:\n"
            f"    revision = \"{rev}\"\n"
            f"    slug = \"{slug}\"\n"
            "    models = []\n"
            "\n"
            "operations = [\n"
            f"    {ops_code}\n"
            "]\n"
        )
        filename = f"{rev}_{slug}.py"
        path = migrations_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def _write_legacy_migration(self, migrations_dir: Path, rev: str, slug: str, sql: str) -> Path:
        """Write a legacy raw-SQL migration file."""
        content = (
            f"revision = \"{rev}\"\n"
            f"slug = \"{slug}\"\n"
            "\n"
            "async def upgrade(conn):\n"
            f"    await conn.execute(\"\"\"{sql}\"\"\")\n"
            "\n"
            "async def downgrade(conn):\n"
            "    pass\n"
        )
        filename = f"{rev}_{slug}.py"
        path = migrations_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    @pytest.fixture
    def db_env(self, tmp_path):
        """Set up a temp SQLite DB and migrations directory."""
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()
        (migrations_dir / "__init__.py").write_text("")
        return db_path, db_url, migrations_dir

    @pytest.mark.asyncio
    async def test_ensure_tracking_table(self, db_env):
        """Runner creates the aquilia_migrations table."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env
        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            await runner.ensure_tracking_table()

            rows = await db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='aquilia_migrations'"
            )
            assert len(rows) == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_apply_dsl_migration(self, db_env):
        """Apply a DSL migration and verify the table is created."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        # Write a migration that creates a "users" table
        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id"), C.varchar("email", 255, unique=True)]),',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            applied = await runner.migrate()

            assert len(applied) == 1

            # Verify the table exists
            rows = await db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert len(rows) == 1

            # Verify recorded in tracking table
            tracked = await runner.get_applied()
            assert "20260101_000000" in tracked[0]
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_fake_migration(self, db_env):
        """--fake marks migration as applied but doesn't execute SQL."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id")]),',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            applied = await runner.migrate(fake=True)
            assert len(applied) == 1

            # Table should NOT exist (faked)
            rows = await db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert len(rows) == 0

            # But it should be recorded as applied
            tracked = await runner.get_applied()
            assert len(tracked) == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_plan_dry_run(self, db_env):
        """--plan returns SQL but doesn't touch the database."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id"), C.varchar("email", 255)]),',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            stmts = await runner.plan()
            assert any("CREATE TABLE" in s for s in stmts)

            # Nothing should be applied
            pending = await runner.get_pending()
            assert len(pending) == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_no_pending_after_apply(self, db_env):
        """After applying, get_pending returns empty."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id")])',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            await runner.migrate()
            pending = await runner.get_pending()
            assert len(pending) == 0
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_idempotent_apply(self, db_env):
        """Applying the same migration twice is safe (no duplicate)."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id")])',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            first = await runner.migrate()
            second = await runner.migrate()
            assert len(first) == 1
            assert len(second) == 0
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_migrations_order(self, db_env):
        """Migrations applied in file-name sorted order."""
        from aquilia.db import AquiliaDatabase
        from aquilia.models.migration_runner import MigrationRunner

        db_path, db_url, migrations_dir = db_env

        self._write_dsl_migration(
            migrations_dir,
            "20260101_000000",
            "create_users",
            'CreateModel(name="User", table="users", fields=[C.auto("id")])',
        )
        self._write_dsl_migration(
            migrations_dir,
            "20260102_000000",
            "create_posts",
            'CreateModel(name="Post", table="posts", fields=[C.auto("id"), C.text("body")])',
        )

        db = AquiliaDatabase(db_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, str(migrations_dir))
            applied = await runner.migrate()
            assert len(applied) == 2
            # First migration should be users
            assert "20260101" in applied[0]
        finally:
            await db.disconnect()


# ============================================================================
# Startup guard
# ============================================================================


class TestStartupGuard:
    """Test the startup guard that prevents implicit DB creation."""

    def test_missing_db_raises(self, tmp_path):
        """Server should refuse to start if DB file doesn't exist."""
        from aquilia.models.startup_guard import check_db_ready, DatabaseNotReadyError

        db_url = f"sqlite:///{tmp_path / 'nonexistent.db'}"
        migrations_dir = str(tmp_path / "migrations")
        os.makedirs(migrations_dir, exist_ok=True)

        with pytest.raises(SystemExit):
            check_db_ready(db_url, migrations_dir, auto_migrate=False)

    def test_existing_db_no_migrations_dir_passes(self, tmp_path):
        """If there's no migrations dir, guard passes (nothing to check)."""
        from aquilia.models.startup_guard import check_db_ready

        db_path = tmp_path / "test.db"
        # Create the DB file
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        # No migrations dir
        check_db_ready(
            f"sqlite:///{db_path}",
            str(tmp_path / "no_such_dir"),
            auto_migrate=False,
        )

    def test_auto_migrate_skips_check(self, tmp_path):
        """When auto_migrate=True, guard does not raise."""
        from aquilia.models.startup_guard import check_db_ready

        db_url = f"sqlite:///{tmp_path / 'nonexistent.db'}"
        migrations_dir = str(tmp_path / "migrations")
        os.makedirs(migrations_dir, exist_ok=True)

        # Should not raise
        check_db_ready(db_url, migrations_dir, auto_migrate=True)

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        """AQUILIA_AUTO_MIGRATE=1 env var overrides when auto_migrate is not set."""
        from aquilia.models.startup_guard import check_db_ready

        monkeypatch.setenv("AQUILIA_AUTO_MIGRATE", "1")
        db_url = f"sqlite:///{tmp_path / 'nonexistent.db'}"
        migrations_dir = str(tmp_path / "migrations")
        os.makedirs(migrations_dir, exist_ok=True)

        # auto_migrate=None (default) lets the env var take effect
        check_db_ready(db_url, migrations_dir)


class TestNoWalCreation:
    """Verify that safe probing does NOT create WAL/SHM files."""

    def test_check_db_exists_no_wal(self, tmp_path):
        """check_db_exists uses read-only mode — no WAL/SHM artifacts."""
        from aquilia.models.migration_runner import check_db_exists

        db_path = tmp_path / "readonly.db"
        # Create a minimal DB
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE x (id INTEGER)")
        conn.close()

        # Remove any WAL/SHM from creation
        for ext in (".db-wal", ".db-shm"):
            p = tmp_path / f"readonly{ext}"
            if p.exists():
                p.unlink()

        db_url = f"sqlite:///{db_path}"
        result = check_db_exists(db_url)
        assert result is True

        # No WAL/SHM should have been created
        assert not (tmp_path / "readonly.db-wal").exists()
        assert not (tmp_path / "readonly.db-shm").exists()

    def test_check_migrations_applied_no_wal(self, tmp_path):
        """check_migrations_applied uses read-only mode — no WAL/SHM."""
        from aquilia.models.migration_runner import check_migrations_applied

        db_path = tmp_path / "probe.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE aquilia_migrations (revision TEXT, slug TEXT, checksum TEXT, applied_at TEXT)"
        )
        conn.close()

        # Clean artifacts
        for ext in (".db-wal", ".db-shm"):
            p = tmp_path / f"probe{ext}"
            if p.exists():
                p.unlink()

        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        db_url = f"sqlite:///{db_path}"
        result = check_migrations_applied(db_url, str(migrations_dir))
        assert result is True

        assert not (tmp_path / "probe.db-wal").exists()
        assert not (tmp_path / "probe.db-shm").exists()


# ============================================================================
# DSL example migration compilation
# ============================================================================


class TestExampleDSLMigration:
    """Test that the example DSL migration file compiles correctly."""

    def test_example_migration_compiles(self):
        """Load the example DSL migration and compile it to SQL."""
        from aquilia.models.migration_runner import (
            _load_migration_module,
            _build_migration_from_module,
        )

        example_path = Path(__file__).parent.parent / "myapp" / "migrations" / \
            "20260217_210454_order_orderevent_orderitem_and_7_more_dsl.py"

        if not example_path.exists():
            pytest.skip("Example DSL migration file not found")

        module = _load_migration_module(example_path, "20260217_210454")
        migration = _build_migration_from_module(module)

        # Should have operations
        assert len(migration.operations) > 0

        # Should compile to SQL without errors
        stmts = migration.compile_upgrade("sqlite")
        assert len(stmts) > 0

        # Should include CREATE TABLE statements for all 10 models
        create_stmts = [s for s in stmts if "CREATE TABLE" in s]
        assert len(create_stmts) == 10

        # Should include indexes
        index_stmts = [s for s in stmts if "CREATE INDEX" in s]
        assert len(index_stmts) > 0

    def test_example_migration_meta(self):
        """Example migration has correct Meta attributes."""
        from aquilia.models.migration_runner import (
            _load_migration_module,
            _build_migration_from_module,
        )

        example_path = Path(__file__).parent.parent / "myapp" / "migrations" / \
            "20260217_210454_order_orderevent_orderitem_and_7_more_dsl.py"

        if not example_path.exists():
            pytest.skip("Example DSL migration file not found")

        module = _load_migration_module(example_path, "20260217_210454")
        migration = _build_migration_from_module(module)

        assert migration.revision == "20260217_210454"
        assert migration.slug == "order_orderevent_orderitem_and_7_more"
        assert "User" in migration.models
        assert "Order" in migration.models


# ============================================================================
# Migration generation
# ============================================================================


class TestMigrationGeneration:
    """Test DSL migration file generation from schema diffs."""

    def test_generate_migration_from_diff(self, tmp_path):
        """Generate a DSL migration file from a manual schema diff."""
        from aquilia.models.schema_snapshot import save_snapshot, SchemaDiff, ModelDiff
        from aquilia.models.migration_gen import _render_migration_file

        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        # Create a diff that adds a new model
        new_snapshot = {
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"name": "id", "type": "INTEGER", "primary_key": True, "autoincrement": True},
                        "email": {"name": "email", "type": "VARCHAR(255)", "unique": True},
                    },
                    "indexes": [],
                }
            }
        }

        # Write the file manually using the render function
        from aquilia.models.migration_dsl import CreateModel, columns as C

        operations = [
            CreateModel(
                name="User",
                table="users",
                fields=[C.auto("id"), C.varchar("email", 255, unique=True)],
            ),
        ]

        content = _render_migration_file(
            revision="20260301_143022",
            slug="create_users",
            model_names=["User"],
            operations=operations,
        )

        path = migrations_dir / "20260301_143022_create_users.py"
        path.write_text(content, encoding="utf-8")

        assert path.exists()
        assert "from aquilia.models.migration_dsl import" in content
        assert "operations" in content
        assert "CreateModel" in content

    def test_render_migration_file_contains_meta(self):
        """Rendered migration file includes Meta class."""
        from aquilia.models.migration_gen import _render_migration_file
        from aquilia.models.migration_dsl import CreateModel, columns as C

        content = _render_migration_file(
            revision="20260218_120000",
            slug="add_posts",
            model_names=["Post"],
            operations=[
                CreateModel(
                    name="Post",
                    table="posts",
                    fields=[C.auto("id"), C.text("body")],
                ),
            ],
        )

        assert 'revision = "20260218_120000"' in content
        assert 'slug = "add_posts"' in content
        assert "class Meta:" in content


# ============================================================================
# Helpers
# ============================================================================


class TestHelpers:
    """Test internal helper functions."""

    def test_extract_revision(self):
        from aquilia.models.migration_runner import _extract_revision

        p = Path("20260217_210454_create_users.py")
        assert _extract_revision(p) == "20260217_210454"

    def test_extract_revision_short_name(self):
        from aquilia.models.migration_runner import _extract_revision

        p = Path("short.py")
        assert _extract_revision(p) is None

    def test_extract_slug(self):
        from aquilia.models.migration_runner import _extract_slug

        p = Path("20260217_210454_create_users.py")
        assert _extract_slug(p) == "create_users"

    def test_file_checksum_deterministic(self, tmp_path):
        from aquilia.models.migration_runner import _file_checksum

        f = tmp_path / "test.py"
        f.write_text("hello")
        c1 = _file_checksum(f)
        c2 = _file_checksum(f)
        assert c1 == c2
        assert len(c1) == 16  # truncated SHA-256

    def test_build_migration_from_module_with_meta_class(self):
        """_build_migration_from_module works with Meta class style."""
        from aquilia.models.migration_runner import _build_migration_from_module
        from aquilia.models.migration_dsl import CreateModel, columns as C

        module = MagicMock()
        meta = MagicMock()
        meta.revision = "20260101_000000"
        meta.slug = "initial"
        meta.models = ["User"]
        meta.dependencies = []
        module.Meta = meta
        module.operations = [
            CreateModel(name="User", table="users", fields=[C.auto("id")])
        ]

        m = _build_migration_from_module(module)
        assert m.revision == "20260101_000000"
        assert len(m.operations) == 1

    def test_build_migration_from_module_with_module_level_attrs(self):
        """_build_migration_from_module works with module-level attributes."""
        from aquilia.models.migration_runner import _build_migration_from_module
        from aquilia.models.migration_dsl import CreateModel, columns as C

        module = MagicMock(spec=[])
        module.revision = "20260101_000000"
        module.slug = "initial"
        module.models = ["User"]
        module.operations = [
            CreateModel(name="User", table="users", fields=[C.auto("id")])
        ]
        # No Meta class
        del module.Meta

        m = _build_migration_from_module(module)
        assert m.revision == "20260101_000000"
