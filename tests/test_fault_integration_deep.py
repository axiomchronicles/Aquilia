"""
Tests for deep fault integration in db/ and models/.

Verifies that:
- db/engine.py raises DatabaseConnectionFault, QueryFault instead of bare exceptions
- models/runtime.py raises ModelNotFoundFault, QueryFault, ModelRegistrationFault
- parser.py AMDLParseError is now an AMDLParseFault subclass
- migrations.py raises MigrationFault instead of bare exceptions
- AquiliaDatabase has @service DI marker and lifecycle hooks
- ModelRegistry has @service DI marker and lifecycle hooks
- Backward compatibility: DatabaseError alias still works
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aquilia.db.engine import AquiliaDatabase, DatabaseError
from aquilia.faults.core import Fault, FaultDomain, Severity
from aquilia.faults.domains import (
    AMDLParseFault,
    DatabaseConnectionFault,
    MigrationFault,
    ModelFault,
    ModelNotFoundFault,
    ModelRegistrationFault,
    QueryFault,
    SchemaFault,
)
from aquilia.models.parser import AMDLParseError, parse_amdl
from aquilia.models.runtime import ModelProxy, ModelRegistry, Q


# ── Helpers ──────────────────────────────────────────────────────────────────

def dollar(obj, name):
    """Shorthand: getattr(obj, '$name')"""
    return getattr(obj, f"${name}")


# ============================================================================
# Database Engine — Fault Integration
# ============================================================================

class TestDatabaseFaults:
    """Verify db/engine.py raises structured faults."""

    def test_database_error_is_fault_alias(self):
        """DatabaseError is now an alias for DatabaseConnectionFault."""
        assert DatabaseError is DatabaseConnectionFault

    def test_database_error_backward_compat(self):
        """Old code catching DatabaseError still works."""
        fault = DatabaseConnectionFault(url="sqlite:///x.db", reason="test")
        assert isinstance(fault, DatabaseError)
        assert isinstance(fault, Fault)

    def test_unsupported_scheme_raises_connection_fault(self):
        """Unsupported URL scheme raises DatabaseConnectionFault."""
        with pytest.raises(DatabaseConnectionFault) as exc_info:
            AquiliaDatabase("oracle://host/db")
        assert exc_info.value.code == "DB_CONNECTION_FAILED"
        assert exc_info.value.domain == FaultDomain.MODEL
        assert "oracle" in exc_info.value.message

    def test_unsupported_scheme_also_caught_as_database_error(self):
        """Backward compat: can catch as DatabaseError."""
        with pytest.raises(DatabaseError):
            AquiliaDatabase("oracle://host/db")

    def test_unsupported_scheme_is_retryable(self):
        """DatabaseConnectionFault is retryable."""
        with pytest.raises(DatabaseConnectionFault) as exc_info:
            AquiliaDatabase("redis://host/db")
        assert exc_info.value.retryable is True

    def test_unsupported_scheme_is_fatal_severity(self):
        """DatabaseConnectionFault has FATAL severity."""
        with pytest.raises(DatabaseConnectionFault) as exc_info:
            AquiliaDatabase("redis://host/db")
        assert exc_info.value.severity == Severity.FATAL

    @pytest.mark.asyncio
    async def test_connect_raises_connection_fault_for_postgres(self):
        """Connecting to unreachable PostgreSQL raises DatabaseConnectionFault or ImportError."""
        db = AquiliaDatabase("postgresql://localhost:59999/nonexistent_test_db")
        with pytest.raises((DatabaseConnectionFault, ImportError)):
            await db.connect()

    @pytest.mark.asyncio
    async def test_execute_wraps_error_as_query_fault(self):
        """execute() wraps raw exceptions as QueryFault."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            with pytest.raises(QueryFault) as exc_info:
                await db.execute("INVALID SQL SYNTAX !!!")
            assert exc_info.value.code == "QUERY_FAILED"
            assert exc_info.value.domain == FaultDomain.MODEL
            assert exc_info.value.retryable is True
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_fetch_all_wraps_error_as_query_fault(self):
        """fetch_all() wraps raw exceptions as QueryFault."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            with pytest.raises(QueryFault) as exc_info:
                await db.fetch_all("SELECT * FROM nonexistent_table")
            assert exc_info.value.metadata["operation"] == "fetch_all"
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_fetch_one_wraps_error_as_query_fault(self):
        """fetch_one() wraps raw exceptions as QueryFault."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            with pytest.raises(QueryFault):
                await db.fetch_one("SELECT * FROM ghost_table")
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_fetch_val_wraps_error_as_query_fault(self):
        """fetch_val() wraps raw exceptions as QueryFault."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            with pytest.raises(QueryFault):
                await db.fetch_val("SELECT x FROM phantom")
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many_wraps_error_as_query_fault(self):
        """execute_many() wraps raw exceptions as QueryFault."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            with pytest.raises(QueryFault):
                await db.execute_many("INVALID!!!", [])
        finally:
            await db.disconnect()

    def test_get_database_raises_connection_fault(self):
        """get_database() raises DatabaseConnectionFault when not configured."""
        import aquilia.db.engine as eng
        saved = eng._default_database
        try:
            eng._default_database = None
            with pytest.raises(DatabaseConnectionFault, match="No database configured"):
                eng.get_database()
        finally:
            eng._default_database = saved


# ============================================================================
# Database Engine — DI / Lifecycle Integration
# ============================================================================

class TestDatabaseDI:
    """Verify AquiliaDatabase has DI decorators and lifecycle hooks."""

    def test_service_marker(self):
        """AquiliaDatabase has __di_scope__ from @service decorator."""
        assert hasattr(AquiliaDatabase, "__di_scope__")
        assert AquiliaDatabase.__di_scope__ == "app"

    def test_service_name(self):
        """AquiliaDatabase has __di_name__ from @service decorator."""
        assert hasattr(AquiliaDatabase, "__di_name__")
        assert AquiliaDatabase.__di_name__ == "AquiliaDatabase"

    def test_has_lifecycle_hooks(self):
        """AquiliaDatabase exposes on_startup / on_shutdown methods."""
        db = AquiliaDatabase("sqlite:///:memory:")
        assert hasattr(db, "on_startup")
        assert hasattr(db, "on_shutdown")
        assert callable(db.on_startup)
        assert callable(db.on_shutdown)

    @pytest.mark.asyncio
    async def test_on_startup_connects(self):
        """on_startup() connects the database."""
        db = AquiliaDatabase("sqlite:///:memory:")
        assert not db.is_connected
        await db.on_startup()
        assert db.is_connected
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_on_shutdown_disconnects(self):
        """on_shutdown() disconnects the database."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        assert db.is_connected
        await db.on_shutdown()
        assert not db.is_connected


# ============================================================================
# ModelProxy — Fault Integration
# ============================================================================

SIMPLE_AMDL = """
≪ MODEL Item ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
  meta table = "items"
≪ /MODEL ≫
"""

class TestModelProxyFaults:
    """Verify ModelProxy raises faults instead of bare exceptions."""

    @pytest.fixture
    async def setup(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        registry = ModelRegistry(db=db)
        parsed = parse_amdl(SIMPLE_AMDL)
        for model in parsed.models:
            registry.register_model(model)
        await registry.create_tables(db)
        yield registry, db
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_create_empty_raises_query_fault(self, setup):
        """$create({}) raises QueryFault."""
        registry, db = setup
        Item = registry.get_proxy("Item")
        with pytest.raises(QueryFault) as exc_info:
            await dollar(Item, "create")({})
        assert exc_info.value.code == "QUERY_FAILED"
        assert exc_info.value.metadata["operation"] == "$create"

    @pytest.mark.asyncio
    async def test_get_no_args_raises_query_fault(self, setup):
        """$get() with no pk or filters raises QueryFault."""
        registry, db = setup
        Item = registry.get_proxy("Item")
        with pytest.raises(QueryFault) as exc_info:
            await dollar(Item, "get")()
        assert exc_info.value.metadata["operation"] == "$get"

    @pytest.mark.asyncio
    async def test_delete_no_args_raises_query_fault(self, setup):
        """$delete() with no pk or filters raises QueryFault."""
        registry, db = setup
        Item = registry.get_proxy("Item")
        with pytest.raises(QueryFault) as exc_info:
            await dollar(Item, "delete")()
        assert exc_info.value.metadata["operation"] == "$delete"

    @pytest.mark.asyncio
    async def test_query_one_empty_raises_model_not_found(self, setup):
        """Q.one() with no matches raises ModelNotFoundFault."""
        registry, db = setup
        Item = registry.get_proxy("Item")
        with pytest.raises(ModelNotFoundFault) as exc_info:
            await dollar(Item, "query")().where("1 = 0").one()
        assert exc_info.value.code == "MODEL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_query_one_multiple_raises_query_fault(self, setup):
        """Q.one() with >1 match raises QueryFault."""
        registry, db = setup
        Item = registry.get_proxy("Item")
        await dollar(Item, "create")({"name": "a"})
        await dollar(Item, "create")({"name": "b"})
        with pytest.raises(QueryFault) as exc_info:
            await dollar(Item, "query")().one()
        assert exc_info.value.metadata["operation"] == "one"


# ============================================================================
# ModelProxy — Link Faults
# ============================================================================

LINK_AMDL = """
≪ MODEL Author ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
  meta table = "authors"
≪ /MODEL ≫

≪ MODEL Book ≫
  slot id :: Auto [PK]
  slot title :: Str [max=200]
  slot author_id :: Int []
  link author -> ONE Author [fk=author_id]
  meta table = "books"
≪ /MODEL ≫
"""


class TestModelLinkFaults:
    """Verify $link/$link_many raise faults."""

    @pytest.fixture
    async def setup(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        registry = ModelRegistry(db=db)
        parsed = parse_amdl(LINK_AMDL)
        for model in parsed.models:
            registry.register_model(model)
        await registry.create_tables(db)
        yield registry, db
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_link_unknown_raises_model_not_found(self, setup):
        """$link with unknown name raises ModelNotFoundFault."""
        registry, db = setup
        Author = registry.get_proxy("Author")
        author = await dollar(Author, "create")({"name": "Test"})
        with pytest.raises(ModelNotFoundFault):
            await dollar(author, "link")("nonexistent")

    @pytest.mark.asyncio
    async def test_link_many_unknown_raises_model_not_found(self, setup):
        """$link_many with unknown name raises ModelNotFoundFault."""
        registry, db = setup
        Author = registry.get_proxy("Author")
        author = await dollar(Author, "create")({"name": "Test"})
        with pytest.raises(ModelNotFoundFault):
            await dollar(author, "link_many")("nonexistent")

    @pytest.mark.asyncio
    async def test_link_unregistered_model_raises_registration_fault(self):
        """$link on unregistered proxy raises ModelRegistrationFault."""
        proxy = ModelProxy(name="test")
        proxy._model_node = None
        proxy._registry = None
        with pytest.raises(ModelRegistrationFault) as exc_info:
            await proxy._dollar_link("any")
        assert exc_info.value.code == "MODEL_REGISTRATION_FAILED"

    @pytest.mark.asyncio
    async def test_link_many_unregistered_model_raises_registration_fault(self):
        """$link_many on unregistered proxy raises ModelRegistrationFault."""
        proxy = ModelProxy(name="test")
        proxy._model_node = None
        proxy._registry = None
        with pytest.raises(ModelRegistrationFault):
            await proxy._dollar_link_many("any")


# ============================================================================
# ModelRegistry — DI / Lifecycle Integration
# ============================================================================

class TestModelRegistryDI:
    """Verify ModelRegistry has DI decorators and lifecycle hooks."""

    def test_service_marker(self):
        """ModelRegistry has __di_scope__ from @service decorator."""
        assert hasattr(ModelRegistry, "__di_scope__")
        assert ModelRegistry.__di_scope__ == "app"

    def test_service_name(self):
        """ModelRegistry has __di_name__ from @service decorator."""
        assert hasattr(ModelRegistry, "__di_name__")
        assert ModelRegistry.__di_name__ == "ModelRegistry"

    def test_has_lifecycle_hooks(self):
        """ModelRegistry exposes on_startup / on_shutdown methods."""
        reg = ModelRegistry()
        assert hasattr(reg, "on_startup")
        assert hasattr(reg, "on_shutdown")

    @pytest.mark.asyncio
    async def test_on_startup_creates_tables(self):
        """on_startup() creates tables for registered models."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            registry = ModelRegistry(db=db)
            parsed = parse_amdl(SIMPLE_AMDL)
            for model in parsed.models:
                registry.register_model(model)
            await registry.on_startup()
            # Verify table exists
            exists = await db.table_exists("items")
            assert exists is True
        finally:
            await db.disconnect()


# ============================================================================
# Parser — Fault Integration
# ============================================================================

class TestParserFaults:
    """Verify parser.py AMDLParseError inherits from AMDLParseFault."""

    def test_parse_error_is_fault(self):
        """AMDLParseError is now a Fault subclass."""
        err = AMDLParseError("bad syntax", file="test.amdl", line=5)
        assert isinstance(err, AMDLParseFault)
        assert isinstance(err, ModelFault)
        assert isinstance(err, Fault)
        assert isinstance(err, Exception)

    def test_parse_error_has_fault_metadata(self):
        """AMDLParseError carries fault metadata."""
        err = AMDLParseError("invalid slot type", file="models/user.amdl", line=10)
        assert err.code == "AMDL_PARSE_ERROR"
        assert err.domain == FaultDomain.MODEL
        assert err.severity == Severity.FATAL
        assert err.metadata["file"] == "models/user.amdl"
        assert err.metadata["line"] == 10

    def test_parse_error_backward_compat(self):
        """Code catching AMDLParseError still works."""
        with pytest.raises(AMDLParseError):
            AMDLParseError._test = True  # just verify it can be raised
            raise AMDLParseError("test error", file="test.amdl", line=1)

    def test_parse_error_caught_as_fault(self):
        """Parse errors can be caught as Fault."""
        with pytest.raises(Fault):
            raise AMDLParseError("test error", file="test.amdl", line=1)

    def test_parse_amdl_collects_errors_as_faults(self):
        """parse_amdl() with bad directives collects errors in result."""
        result = parse_amdl("slot x :: BadType", file_path="test.amdl")
        assert len(result.errors) > 0


# ============================================================================
# Migrations — Fault Integration
# ============================================================================

class TestMigrationFaults:
    """Verify migrations.py uses MigrationFault."""

    @pytest.mark.asyncio
    async def test_apply_bad_module_raises_migration_fault(self, tmp_path):
        """apply_migration raises MigrationFault for unloadable files."""
        from aquilia.models.migrations import MigrationRunner
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            runner = MigrationRunner(db, tmp_path)
            # Create a file with bad content
            bad_file = tmp_path / "20990101_000000_bad.py"
            bad_file.write_text("raise SyntaxError('deliberate')\n")
            with pytest.raises(MigrationFault) as exc_info:
                await runner.apply_migration(bad_file)
            assert exc_info.value.code == "MIGRATION_FAILED"
            assert exc_info.value.domain == FaultDomain.MODEL
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_rollback_unknown_revision_raises_migration_fault(self, tmp_path):
        """_rollback_to raises MigrationFault for unknown revision."""
        from aquilia.models.migrations import MigrationRunner
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        try:
            runner = MigrationRunner(db, tmp_path)
            await runner.ensure_tracking_table()
            with pytest.raises(MigrationFault) as exc_info:
                await runner.migrate(target="99999999_999999")
            assert "not in applied migrations" in exc_info.value.message
        finally:
            await db.disconnect()


# ============================================================================
# Cross-Cutting: Faults flow through the Fault pipeline
# ============================================================================

class TestFaultPipeline:
    """Verify all model/db faults inherit from Fault and flow through the engine."""

    def test_all_model_faults_are_fault_instances(self):
        """Every model fault is a Fault with domain=MODEL."""
        faults = [
            DatabaseConnectionFault(url="x", reason="y"),
            QueryFault(model="M", operation="op", reason="r"),
            ModelNotFoundFault(model_name="X"),
            ModelRegistrationFault(model_name="X", reason="r"),
            SchemaFault(table="t", reason="r"),
            MigrationFault(migration="m", reason="r"),
        ]
        for f in faults:
            assert isinstance(f, Fault), f"{type(f).__name__} is not a Fault"
            assert isinstance(f, ModelFault), f"{type(f).__name__} is not a ModelFault"
            assert f.domain == FaultDomain.MODEL

    def test_faults_are_exceptions(self):
        """All faults can be raised/caught as Exception."""
        for fault_cls in (
            DatabaseConnectionFault,
            QueryFault,
            ModelNotFoundFault,
            ModelRegistrationFault,
            SchemaFault,
            MigrationFault,
        ):
            assert issubclass(fault_cls, Exception)


# ============================================================================
# Exports
# ============================================================================

class TestExports:
    """Verify fault types are re-exported from models/ and db/ packages."""

    def test_db_exports_fault_types(self):
        """aquilia.db exports DatabaseConnectionFault, QueryFault, SchemaFault."""
        from aquilia.db import DatabaseConnectionFault as DCF
        from aquilia.db import QueryFault as QF
        from aquilia.db import SchemaFault as SF
        assert DCF is DatabaseConnectionFault
        assert QF is QueryFault
        assert SF is SchemaFault

    def test_models_exports_fault_types(self):
        """aquilia.models exports all model fault types."""
        from aquilia.models import (
            ModelFault as MF,
            AMDLParseFault as APF,
            ModelNotFoundFault as MNFF,
            ModelRegistrationFault as MRF,
            MigrationFault as MigF,
            MigrationConflictFault as MCF,
            QueryFault as QF,
            DatabaseConnectionFault as DCF,
            SchemaFault as SF,
        )
        assert MF is ModelFault
        assert APF is AMDLParseFault
        assert MNFF is ModelNotFoundFault
        assert MRF is ModelRegistrationFault
        assert MigF is MigrationFault
        assert MCF is __import__("aquilia.faults.domains", fromlist=["MigrationConflictFault"]).MigrationConflictFault
        assert QF is QueryFault
        assert DCF is DatabaseConnectionFault
        assert SF is SchemaFault

    def test_database_error_alias_exported(self):
        """aquilia.db.DatabaseError is DatabaseConnectionFault."""
        from aquilia.db import DatabaseError as DE
        assert DE is DatabaseConnectionFault
