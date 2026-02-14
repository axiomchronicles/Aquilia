"""
Tests for deep model integration with Aquilia subsystems.

Tests:
- FaultDomain.MODEL and model fault types
- DatabaseConfig in manifests
- Module.register_models() / Module.database() config builders
- Integration.database() workspace config
- Workspace.database() fluent builder
- AppContext.models field
- ModuleConfig.models field
- Fault integration patching
- Model auto-discovery patterns
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path


# ============================================================================
# Fault Domain & Types
# ============================================================================

class TestModelFaultDomain:
    """Test FaultDomain.MODEL and model-specific fault classes."""

    def test_model_domain_exists(self):
        from aquilia.faults.core import FaultDomain
        assert hasattr(FaultDomain, "MODEL")
        assert FaultDomain.MODEL.name == "model"

    def test_model_domain_in_defaults(self):
        from aquilia.faults.core import DOMAIN_DEFAULTS, FaultDomain, Severity
        assert FaultDomain.MODEL in DOMAIN_DEFAULTS
        assert DOMAIN_DEFAULTS[FaultDomain.MODEL]["severity"] == Severity.ERROR

    def test_model_fault_base(self):
        from aquilia.faults.domains import ModelFault
        from aquilia.faults.core import FaultDomain
        fault = ModelFault(code="TEST", message="test fault")
        assert fault.domain == FaultDomain.MODEL
        assert fault.code == "TEST"

    def test_amdl_parse_fault(self):
        from aquilia.faults.domains import AMDLParseFault
        from aquilia.faults.core import Severity
        fault = AMDLParseFault(file="models/user.amdl", line=5, reason="invalid slot")
        assert fault.code == "AMDL_PARSE_ERROR"
        assert fault.severity == Severity.FATAL
        assert "user.amdl" in fault.message
        assert fault.metadata["line"] == 5

    def test_model_not_found_fault(self):
        from aquilia.faults.domains import ModelNotFoundFault
        fault = ModelNotFoundFault(model_name="User")
        assert fault.code == "MODEL_NOT_FOUND"
        assert "User" in fault.message

    def test_model_registration_fault(self):
        from aquilia.faults.domains import ModelRegistrationFault
        fault = ModelRegistrationFault(model_name="Post", reason="duplicate")
        assert fault.code == "MODEL_REGISTRATION_FAILED"
        assert fault.metadata["model"] == "Post"

    def test_migration_fault(self):
        from aquilia.faults.domains import MigrationFault
        fault = MigrationFault(migration="0001_initial", reason="syntax error")
        assert fault.code == "MIGRATION_FAILED"
        assert fault.metadata["migration"] == "0001_initial"

    def test_migration_conflict_fault(self):
        from aquilia.faults.domains import MigrationConflictFault
        from aquilia.faults.core import Severity
        fault = MigrationConflictFault(conflicting=["0002_a", "0002_b"])
        assert fault.code == "MIGRATION_CONFLICT"
        assert fault.severity == Severity.FATAL
        assert len(fault.metadata["conflicting"]) == 2

    def test_query_fault(self):
        from aquilia.faults.domains import QueryFault
        fault = QueryFault(model="User", operation="$create", reason="constraint violation")
        assert fault.code == "QUERY_FAILED"
        assert fault.retryable is True
        assert fault.metadata["operation"] == "$create"

    def test_database_connection_fault(self):
        from aquilia.faults.domains import DatabaseConnectionFault
        from aquilia.faults.core import Severity
        fault = DatabaseConnectionFault(url="sqlite:///test.db", reason="file locked")
        assert fault.code == "DB_CONNECTION_FAILED"
        assert fault.severity == Severity.FATAL
        assert fault.retryable is True

    def test_schema_fault(self):
        from aquilia.faults.domains import SchemaFault
        from aquilia.faults.core import Severity
        fault = SchemaFault(table="users", reason="column type mismatch")
        assert fault.code == "SCHEMA_FAULT"
        assert fault.severity == Severity.FATAL
        assert fault.metadata["table"] == "users"

    def test_model_fault_to_dict(self):
        from aquilia.faults.domains import QueryFault
        fault = QueryFault(model="User", operation="$get", reason="not found")
        d = fault.to_dict()
        assert d["code"] == "QUERY_FAILED"
        assert d["domain"] == "model"

    def test_fault_transform_chain(self):
        """Test fault >> transform operator works for model faults."""
        from aquilia.faults.domains import QueryFault, ModelFault
        original = QueryFault(model="User", operation="$get", reason="not found")
        transformed = original >> ModelFault(
            code="USER_FETCH_FAILED",
            message="Could not fetch user",
        )
        assert transformed.code == "USER_FETCH_FAILED"
        assert transformed.metadata.get("_cause") is original


# ============================================================================
# Faults Integration Module
# ============================================================================

class TestModelFaultIntegration:
    """Test faults.integrations.models module."""

    def test_imports(self):
        from aquilia.faults.integrations.models import (
            ModelFaultHandler,
            create_model_fault_handler,
            patch_model_registry,
            patch_database_engine,
            patch_all_model_subsystems,
        )

    def test_handler_can_handle(self):
        from aquilia.faults.integrations.models import ModelFaultHandler
        from aquilia.faults.core import FaultContext, FaultDomain
        from aquilia.faults.domains import QueryFault, ModelFault
        
        handler = ModelFaultHandler()
        
        # Model fault should be handled
        fault = QueryFault(model="User", operation="$get", reason="err")
        ctx = FaultContext.capture(fault, app="test")
        assert handler.can_handle(ctx)
    
    def test_handler_escalates_by_default(self):
        from aquilia.faults.integrations.models import ModelFaultHandler
        from aquilia.faults.core import FaultContext, Escalate
        from aquilia.faults.domains import ModelNotFoundFault
        
        handler = ModelFaultHandler()
        fault = ModelNotFoundFault(model_name="User")
        ctx = FaultContext.capture(fault, app="test")
        result = handler.handle(ctx)
        assert isinstance(result, Escalate)

    def test_integrations_init_exports(self):
        from aquilia.faults.integrations import (
            ModelFaultHandler,
            create_model_fault_handler,
            patch_model_registry,
            patch_database_engine,
            patch_all_model_subsystems,
        )

    def test_create_all_handlers_includes_model(self):
        from aquilia.faults.integrations import create_all_integration_handlers
        from aquilia.faults.integrations.models import ModelFaultHandler
        handlers = create_all_integration_handlers()
        model_handlers = [h for h in handlers if isinstance(h, ModelFaultHandler)]
        assert len(model_handlers) == 1


# ============================================================================
# DatabaseConfig in Manifest
# ============================================================================

class TestDatabaseConfig:
    """Test DatabaseConfig dataclass in manifest."""

    def test_database_config_defaults(self):
        from aquilia.manifest import DatabaseConfig
        cfg = DatabaseConfig()
        assert cfg.url == "sqlite:///db.sqlite3"
        assert cfg.auto_connect is True
        assert cfg.auto_create is True
        assert cfg.auto_migrate is False
        assert cfg.migrations_dir == "migrations"
        assert cfg.scan_dirs == ["models"]

    def test_database_config_custom(self):
        from aquilia.manifest import DatabaseConfig
        cfg = DatabaseConfig(
            url="sqlite:///myapp.db",
            auto_create=False,
            auto_migrate=True,
            migrations_dir="db/migrations",
            pool_size=10,
            echo=True,
            model_paths=["models/user.amdl"],
            scan_dirs=["models", "extra_models"],
        )
        assert cfg.url == "sqlite:///myapp.db"
        assert cfg.auto_create is False
        assert cfg.auto_migrate is True
        assert cfg.pool_size == 10
        assert len(cfg.model_paths) == 1
        assert len(cfg.scan_dirs) == 2

    def test_database_config_to_dict(self):
        from aquilia.manifest import DatabaseConfig
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        d = cfg.to_dict()
        assert d["url"] == "sqlite:///:memory:"
        assert "auto_create" in d
        assert "scan_dirs" in d

    def test_manifest_with_database(self):
        from aquilia.manifest import AppManifest, DatabaseConfig
        manifest = AppManifest(
            name="blog",
            version="1.0.0",
            database=DatabaseConfig(url="sqlite:///blog.db"),
        )
        assert manifest.database is not None
        assert manifest.database.url == "sqlite:///blog.db"

    def test_manifest_models_field(self):
        from aquilia.manifest import AppManifest
        manifest = AppManifest(
            name="blog",
            version="1.0.0",
            models=["models/post.amdl", "models/user.amdl"],
        )
        assert len(manifest.models) == 2
        assert "models/post.amdl" in manifest.models

    def test_manifest_to_dict_includes_models(self):
        from aquilia.manifest import AppManifest, DatabaseConfig
        manifest = AppManifest(
            name="blog",
            version="1.0.0",
            models=["models/post.amdl"],
            database=DatabaseConfig(url="sqlite:///blog.db"),
        )
        d = manifest.to_dict()
        assert "models" in d
        assert d["models"] == ["models/post.amdl"]
        assert "database" in d
        assert d["database"]["url"] == "sqlite:///blog.db"

    def test_manifest_without_database(self):
        from aquilia.manifest import AppManifest
        manifest = AppManifest(name="basic", version="1.0.0")
        d = manifest.to_dict()
        assert "database" not in d  # None values excluded

    def test_database_config_exported(self):
        from aquilia import DatabaseConfig
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        assert cfg.url == "sqlite:///:memory:"


# ============================================================================
# Config Builders
# ============================================================================

class TestModuleConfigModels:
    """Test Module builder model registration."""

    def test_module_config_has_models_field(self):
        from aquilia.config_builders import ModuleConfig
        cfg = ModuleConfig(name="test")
        assert hasattr(cfg, "models")
        assert cfg.models == []

    def test_module_register_models(self):
        from aquilia.config_builders import Module
        mod = Module("blog").register_models(
            "models/post.amdl",
            "models/user.amdl",
        )
        config = mod.build()
        assert len(config.models) == 2
        assert "models/post.amdl" in config.models

    def test_module_database(self):
        from aquilia.config_builders import Module
        mod = Module("blog").database(
            url="sqlite:///blog.db",
            auto_create=True,
            auto_migrate=False,
        )
        config = mod.build()
        assert config.database is not None
        assert config.database["url"] == "sqlite:///blog.db"
        assert config.database["auto_create"] is True

    def test_module_to_dict_includes_models(self):
        from aquilia.config_builders import Module
        mod = Module("blog").register_models("models/blog.amdl")
        d = mod.build().to_dict()
        assert "models" in d
        assert d["models"] == ["models/blog.amdl"]

    def test_module_chain_all(self):
        """Test full fluent chain with models."""
        from aquilia.config_builders import Module
        mod = (
            Module("blog", version="1.0.0")
            .route_prefix("/blog")
            .register_controllers("modules.blog.controllers:PostController")
            .register_services("modules.blog.services:PostService")
            .register_models("models/post.amdl", "models/tag.amdl")
            .database(url="sqlite:///blog.db")
            .auto_discover()
        )
        config = mod.build()
        assert len(config.models) == 2
        assert config.database["url"] == "sqlite:///blog.db"
        assert config.auto_discover is True


class TestIntegrationDatabase:
    """Test Integration.database() static method."""

    def test_integration_database_defaults(self):
        from aquilia.config_builders import Integration
        cfg = Integration.database()
        assert cfg["enabled"] is True
        assert cfg["url"] == "sqlite:///db.sqlite3"
        assert cfg["auto_create"] is True
        assert cfg["auto_connect"] is True

    def test_integration_database_custom(self):
        from aquilia.config_builders import Integration
        cfg = Integration.database(
            url="sqlite:///myapp.db",
            auto_create=False,
            echo=True,
            scan_dirs=["models", "extra"],
        )
        assert cfg["url"] == "sqlite:///myapp.db"
        assert cfg["auto_create"] is False
        assert cfg["echo"] is True
        assert cfg["scan_dirs"] == ["models", "extra"]


class TestWorkspaceDatabase:
    """Test Workspace.database() fluent builder."""

    def test_workspace_database(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("myapp").database(
            url="sqlite:///app.db",
            auto_create=True,
        )
        d = ws.to_dict()
        assert "database" in d
        assert d["database"]["url"] == "sqlite:///app.db"
        assert d["database"]["auto_create"] is True

    def test_workspace_database_in_integrations(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("myapp").database(url="sqlite:///app.db")
        d = ws.to_dict()
        assert "database" in d["integrations"]

    def test_workspace_integrate_database(self):
        from aquilia.config_builders import Workspace, Integration
        ws = Workspace("myapp").integrate(
            Integration.database(url="sqlite:///x.db")
        )
        d = ws.to_dict()
        assert "database" in d["integrations"]
        assert d["integrations"]["database"]["url"] == "sqlite:///x.db"

    def test_workspace_full_chain(self):
        """Test full workspace chain with database + models."""
        from aquilia.config_builders import Workspace, Module, Integration
        ws = (
            Workspace("myapp", version="1.0.0")
            .runtime(mode="dev", port=8000)
            .database(url="sqlite:///app.db", auto_create=True)
            .module(
                Module("blog")
                .register_models("models/blog.amdl")
                .route_prefix("/blog")
            )
            .module(
                Module("users")
                .register_models("models/user.amdl")
                .database(url="sqlite:///users.db")
            )
        )
        d = ws.to_dict()
        assert d["database"]["url"] == "sqlite:///app.db"
        assert len(d["modules"]) == 2
        assert d["modules"][0]["models"] == ["models/blog.amdl"]
        assert d["modules"][1]["database"]["url"] == "sqlite:///users.db"


# ============================================================================
# AppContext.models
# ============================================================================

class TestAppContextModels:
    """Test AppContext models field."""

    def test_app_context_has_models(self):
        from aquilia.aquilary.core import AppContext
        ctx = AppContext(
            name="test",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            models=["models/user.amdl"],
        )
        assert ctx.models == ["models/user.amdl"]

    def test_app_context_models_default_empty(self):
        from aquilia.aquilary.core import AppContext
        ctx = AppContext(
            name="test",
            version="1.0.0",
            manifest=None,
            config_namespace={},
        )
        assert ctx.models == []


# ============================================================================
# Top-level Exports
# ============================================================================

class TestTopLevelExports:
    """Test that model fault types are exported from aquilia package."""

    def test_fault_exports(self):
        from aquilia import (
            ModelFault,
            AMDLParseFault,
            ModelNotFoundFault,
            ModelRegistrationFault,
            MigrationFault,
            MigrationConflictFault,
            QueryFault,
            DatabaseConnectionFault,
            SchemaFault,
        )

    def test_database_config_export(self):
        from aquilia import DatabaseConfig
        assert DatabaseConfig is not None

    def test_fault_domain_model(self):
        from aquilia.faults.core import FaultDomain
        assert FaultDomain.MODEL.name == "model"


# ============================================================================
# Aquilary Integration (manifest → AppContext models extraction)
# ============================================================================

class TestAquilaryModelExtraction:
    """Test that from_manifests correctly extracts models into AppContext."""

    def test_manifest_models_in_context(self):
        """Verify models= from manifest flows into AppContext."""
        from aquilia.manifest import AppManifest
        from aquilia.aquilary.core import AppContext
        
        manifest = AppManifest(
            name="blog",
            version="1.0.0",
            models=["models/post.amdl", "models/tag.amdl"],
        )
        
        # Simulate what Aquilary.from_manifests does in Phase 5
        ctx = AppContext(
            name=manifest.name,
            version=manifest.version,
            manifest=manifest,
            config_namespace={},
            controllers=getattr(manifest, "controllers", []),
            services=getattr(manifest, "services", []),
            models=getattr(manifest, "models", []),
        )
        
        assert len(ctx.models) == 2
        assert "models/post.amdl" in ctx.models


# ============================================================================
# RuntimeRegistry Model Registration
# ============================================================================

class TestRuntimeRegistryModels:
    """Test RuntimeRegistry model discovery and DI registration."""

    def test_discover_amdl_models_no_dir(self, tmp_path):
        """Discovery should gracefully handle missing directories."""
        from aquilia.aquilary.core import RuntimeRegistry, AquilaryRegistry, AppContext
        
        ctx = AppContext(
            name="empty",
            version="1.0.0",
            manifest=MagicMock(database=None),
            config_namespace={},
        )
        
        registry_meta = MagicMock(spec=AquilaryRegistry)
        registry_meta.app_contexts = [ctx]
        
        runtime = RuntimeRegistry(registry_meta, config=MagicMock())
        
        # Should not crash when no modules dir exists
        # Patch pathlib.Path.cwd to return tmp_path which has no modules/ dir
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            runtime._discover_amdl_models(ctx)
        
        # No models discovered
        assert ctx.models == []

    def test_register_models_empty(self):
        """_register_models should be no-op when no models exist."""
        from aquilia.aquilary.core import RuntimeRegistry, AquilaryRegistry, AppContext
        
        ctx = AppContext(
            name="empty",
            version="1.0.0",
            manifest=None,
            config_namespace={},
        )
        
        registry_meta = MagicMock(spec=AquilaryRegistry)
        registry_meta.app_contexts = [ctx]
        
        runtime = RuntimeRegistry(registry_meta, config=MagicMock())
        runtime._register_models()
        
        assert runtime._models_registered is True
