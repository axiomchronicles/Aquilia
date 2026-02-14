"""
Tests for Migration System — MigrationOps, generation, and runner.
"""

import tempfile
import pytest
from aquilia.models.parser import parse_amdl
from aquilia.models.runtime import ModelProxy, ModelRegistry
from aquilia.models.migrations import (
    MigrationOps,
    MigrationRunner,
    generate_migration_file,
)
from aquilia.db.engine import AquiliaDatabase


# ── Helper ───────────────────────────────────────────────────────────────────

def dollar(obj, name):
    """Shorthand: getattr(obj, '$name')"""
    return getattr(obj, f"${name}")


# ── AMDL source ──────────────────────────────────────────────────────────────

SIMPLE_AMDL = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot username :: Str [max=150, unique]
  slot email :: Str [max=255, nullable]
  meta table = "aq_user"
≪ /MODEL ≫
"""


@pytest.fixture
async def db():
    database = AquiliaDatabase("sqlite:///:memory:")
    await database.connect()
    yield database
    await database.disconnect()


# ── MigrationOps ─────────────────────────────────────────────────────────────


class TestMigrationOps:
    """Test migration operation builder."""

    def test_create_table(self):
        """Build CREATE TABLE statement."""
        ops = MigrationOps()
        ops.create_table("test_tbl", [
            '"id" INTEGER PRIMARY KEY AUTOINCREMENT',
            '"name" VARCHAR(100) NOT NULL',
        ])
        assert len(ops._statements) == 1
        assert "CREATE TABLE" in ops._statements[0]
        assert "test_tbl" in ops._statements[0]

    def test_drop_table(self):
        """Build DROP TABLE statement."""
        ops = MigrationOps()
        ops.drop_table("test_tbl")
        assert "DROP TABLE" in ops._statements[0]

    def test_column_helpers(self):
        """Column type helpers produce valid SQL fragments."""
        assert "PRIMARY KEY" in MigrationOps.pk()
        assert "VARCHAR(100)" in MigrationOps.varchar("name", 100)
        assert "TEXT" in MigrationOps.text("body")
        assert "BLOB" in MigrationOps.blob("data")
        assert "INTEGER" in MigrationOps.boolean("active")
        assert "TIMESTAMP" in MigrationOps.timestamp("created")
        assert "REAL" in MigrationOps.real("price")


# ── Migration File Generation ────────────────────────────────────────────────


class TestMigrationGeneration:
    """Test migration file creation."""

    def test_generate_migration_file(self):
        """Generate a migration Python file."""
        result = parse_amdl(SIMPLE_AMDL)
        models = result.models

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_migration_file(models, tmpdir, slug="test_initial")

            assert str(path).endswith(".py")

            with open(path) as f:
                content = f.read()

            assert "async def upgrade" in content
            assert "async def downgrade" in content
            assert "CREATE TABLE" in content
            assert "aq_user" in content

    def test_migration_file_has_revision(self):
        """Migration file contains revision hash."""
        result = parse_amdl(SIMPLE_AMDL)
        models = result.models

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_migration_file(models, tmpdir, slug="rev_test")

            with open(path) as f:
                content = f.read()

            assert "revision" in content


# ── MigrationRunner ──────────────────────────────────────────────────────────


class TestMigrationRunner:
    """Test migration application and tracking."""

    @pytest.mark.asyncio
    async def test_tracking_table_created(self, db):
        """Runner creates tracking table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = MigrationRunner(db, tmpdir)
            await runner.ensure_tracking_table()

            exists = await db.table_exists("aquilia_migrations")
            assert exists is True

    @pytest.mark.asyncio
    async def test_get_applied_empty(self, db):
        """No applied migrations initially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = MigrationRunner(db, tmpdir)
            applied = await runner.get_applied()
            assert applied == []

    @pytest.mark.asyncio
    async def test_apply_migration(self, db):
        """Apply a generated migration."""
        result = parse_amdl(SIMPLE_AMDL)
        models = result.models

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_migration_file(models, tmpdir)

            runner = MigrationRunner(db, tmpdir)
            await runner.migrate()

            # Table should exist
            exists = await db.table_exists("aq_user")
            assert exists is True

            # Migration tracked
            applied = await runner.get_applied()
            assert len(applied) == 1

    @pytest.mark.asyncio
    async def test_migrate_idempotent(self, db):
        """Running migrate twice is safe."""
        result = parse_amdl(SIMPLE_AMDL)
        models = result.models

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_migration_file(models, tmpdir)

            runner = MigrationRunner(db, tmpdir)
            await runner.migrate()
            await runner.migrate()  # Should be no-op

            tracked = await runner.get_applied()
            assert len(tracked) == 1


class TestEndToEnd:
    """End-to-end: parse → migrate → CRUD."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Complete workflow: parse, migrate, create, query."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        try:
            # Parse
            result = parse_amdl(SIMPLE_AMDL)
            assert not result.errors

            # Register and create tables
            registry = ModelRegistry(db)
            for model in result.models:
                registry.register_model(model)
            await registry.create_tables(db)

            # CRUD via $-API
            User = registry.get_proxy("User")
            user = await dollar(User, "create")({"username": "e2e_user", "email": "e2e@test.com"})
            assert user.id is not None

            found = await dollar(User, "get")(pk=user.id)
            assert found.username == "e2e_user"

            rows = await dollar(User, "query")().all()
            assert len(rows) == 1

            await dollar(User, "update")(
                filters={"id": user.id},
                values={"username": "updated_user"},
            )
            updated = await dollar(User, "get")(pk=user.id)
            assert updated.username == "updated_user"

            await dollar(User, "delete")(pk=user.id)
            gone = await dollar(User, "get")(pk=user.id)
            assert gone is None
        finally:
            await db.disconnect()
