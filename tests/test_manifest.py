"""
Test 15: Manifest System (manifest.py)

Tests AppManifest, ServiceConfig, SessionConfig, MiddlewareConfig,
FaultHandlerConfig, FaultHandlingConfig, FeatureConfig, TemplateConfig,
LifecycleConfig, ServiceScope, ManifestLoader.
"""

import pytest
from datetime import timedelta

from aquilia.manifest import (
    AppManifest,
    ServiceConfig,
    SessionConfig,
    MiddlewareConfig,
    FaultHandlerConfig,
    FaultHandlingConfig,
    FeatureConfig,
    TemplateConfig,
    LifecycleConfig,
    ServiceScope,
    ManifestLoader,
)


# ============================================================================
# ServiceScope
# ============================================================================

class TestServiceScope:

    def test_values(self):
        assert ServiceScope.SINGLETON == "singleton"
        assert ServiceScope.APP == "app"
        assert ServiceScope.REQUEST == "request"
        assert ServiceScope.TRANSIENT == "transient"
        assert ServiceScope.POOLED == "pooled"
        assert ServiceScope.EPHEMERAL == "ephemeral"


# ============================================================================
# LifecycleConfig
# ============================================================================

class TestLifecycleConfig:

    def test_defaults(self):
        lc = LifecycleConfig()
        assert lc.on_startup is None
        assert lc.on_shutdown is None
        assert lc.depends_on == []
        assert lc.startup_timeout == 30.0

    def test_to_dict(self):
        lc = LifecycleConfig(on_startup="mod:start")
        d = lc.to_dict()
        assert d["on_startup"] == "mod:start"


# ============================================================================
# ServiceConfig
# ============================================================================

class TestServiceConfig:

    def test_create(self):
        sc = ServiceConfig(class_path="mod:MyService")
        assert sc.class_path == "mod:MyService"
        assert sc.scope == ServiceScope.APP
        assert sc.auto_discover is True
        assert sc.required is True

    def test_to_dict(self):
        sc = ServiceConfig(
            class_path="mod:Svc",
            scope=ServiceScope.SINGLETON,
            aliases=["ISvc"],
        )
        d = sc.to_dict()
        assert d["class_path"] == "mod:Svc"
        assert d["scope"] == "singleton"
        assert "ISvc" in d["aliases"]


# ============================================================================
# MiddlewareConfig
# ============================================================================

class TestMiddlewareConfig:

    def test_create(self):
        mc = MiddlewareConfig(class_path="mod:Mw")
        assert mc.class_path == "mod:Mw"
        assert mc.scope == "global"
        assert mc.priority == 50

    def test_to_dict(self):
        mc = MiddlewareConfig(class_path="mod:Mw", priority=10)
        d = mc.to_dict()
        assert d["priority"] == 10


# ============================================================================
# SessionConfig
# ============================================================================

class TestSessionConfig:

    def test_create(self):
        sc = SessionConfig(name="default")
        assert sc.name == "default"
        assert sc.enabled is True
        assert sc.transport == "cookie"
        assert sc.store == "memory"
        assert sc.cookie_secure is True
        assert sc.cookie_httponly is True

    def test_custom(self):
        sc = SessionConfig(
            name="secure",
            ttl=timedelta(hours=1),
            cookie_samesite="Lax",
            store="redis",
        )
        assert sc.store == "redis"
        assert sc.cookie_samesite == "Lax"

    def test_to_dict(self):
        sc = SessionConfig(name="test")
        d = sc.to_dict()
        assert d["name"] == "test"
        assert "transport" in d


# ============================================================================
# FaultHandlerConfig / FaultHandlingConfig
# ============================================================================

class TestFaultConfigs:

    def test_fault_handler_config(self):
        fhc = FaultHandlerConfig(
            domain="AUTH",
            handler_path="mod:handler",
        )
        assert fhc.domain == "AUTH"
        assert fhc.recovery_strategy == "propagate"

    def test_fault_handling_config(self):
        fhcfg = FaultHandlingConfig()
        assert fhcfg.default_domain == "APP"
        assert fhcfg.handlers == []

    def test_fault_handling_to_dict(self):
        fhcfg = FaultHandlingConfig(default_domain="SYSTEM")
        d = fhcfg.to_dict()
        assert d["default_domain"] == "SYSTEM"


# ============================================================================
# FeatureConfig
# ============================================================================

class TestFeatureConfig:

    def test_create(self):
        fc = FeatureConfig(name="beta_feature")
        assert fc.name == "beta_feature"
        assert fc.enabled is False

    def test_to_dict(self):
        fc = FeatureConfig(name="x", enabled=True)
        d = fc.to_dict()
        assert d["enabled"] is True


# ============================================================================
# TemplateConfig
# ============================================================================

class TestTemplateConfig:

    def test_create(self):
        tc = TemplateConfig()
        assert tc.enabled is True
        assert tc.sandbox is True

    def test_to_dict(self):
        tc = TemplateConfig(search_paths=["templates/"])
        d = tc.to_dict()
        assert "templates/" in d["search_paths"]


# ============================================================================
# AppManifest
# ============================================================================

class TestAppManifest:

    def test_minimal(self):
        m = AppManifest(name="myapp", version="1.0.0")
        assert m.name == "myapp"
        assert m.version == "1.0.0"
        assert m.services == []
        assert m.controllers == []

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="must have a name"):
            AppManifest(name="", version="1.0.0")

    def test_missing_version_raises(self):
        with pytest.raises(ValueError, match="must have a version"):
            AppManifest(name="app", version="")

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Invalid app name"):
            AppManifest(name="my-app!", version="1.0.0")

    def test_with_services(self):
        svc = ServiceConfig(class_path="mod:Svc")
        m = AppManifest(name="app", version="1.0.0", services=[svc])
        assert len(m.services) == 1

    def test_with_controllers(self):
        m = AppManifest(
            name="app",
            version="1.0.0",
            controllers=["mod:UserCtrl", "mod:PostCtrl"],
        )
        assert len(m.controllers) == 2

    def test_to_dict(self):
        m = AppManifest(name="app", version="1.0.0", tags=["core"])
        d = m.to_dict()
        assert d["name"] == "app"
        assert "core" in d["tags"]

    def test_fingerprint(self):
        m = AppManifest(name="app", version="1.0.0")
        fp = m.fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_fingerprint_deterministic(self):
        m1 = AppManifest(name="app", version="1.0.0")
        m2 = AppManifest(name="app", version="1.0.0")
        assert m1.fingerprint() == m2.fingerprint()

    def test_fingerprint_changes(self):
        m1 = AppManifest(name="app", version="1.0.0")
        m2 = AppManifest(name="app", version="1.0.1")
        assert m1.fingerprint() != m2.fingerprint()

    def test_legacy_middleware_conversion(self):
        m = AppManifest(
            name="app",
            version="1.0.0",
            middlewares=[("mod:Mw", {"key": "val"})],
        )
        assert len(m.middleware) == 1
        assert m.middleware[0].class_path == "mod:Mw"

    def test_legacy_fault_domain_conversion(self):
        m = AppManifest(
            name="app",
            version="1.0.0",
            default_fault_domain="AUTH",
        )
        assert m.faults is not None
        assert m.faults.default_domain == "AUTH"

    def test_depends_on(self):
        m = AppManifest(
            name="posts",
            version="1.0.0",
            depends_on=["users", "auth"],
        )
        assert "users" in m.depends_on


# ============================================================================
# ManifestLoader
# ============================================================================

class TestManifestLoader:

    def test_load_manifests(self):
        m1 = AppManifest(name="a", version="1.0.0")
        m2 = AppManifest(name="b", version="1.0.0")
        loaded = ManifestLoader.load_manifests([m1, m2])
        assert len(loaded) == 2

    def test_load_manifest_class(self):
        class MyManifest(AppManifest):
            def __init__(self):
                super().__init__(name="mymod", version="1.0.0")

        loaded = ManifestLoader.load_manifests([MyManifest])
        assert loaded[0].name == "mymod"

    def test_duplicate_names_raises(self):
        m1 = AppManifest(name="dup", version="1.0.0")
        m2 = AppManifest(name="dup", version="1.0.0")
        with pytest.raises(ValueError, match="Duplicate app name"):
            ManifestLoader.load_manifests([m1, m2])

    def test_validate_manifest_valid(self):
        m = AppManifest(name="ok", version="1.0.0")
        issues = ManifestLoader.validate_manifest(m)
        assert len(issues) == 0

    def test_validate_manifest_bad_version(self):
        m = AppManifest(name="ok", version="1")
        issues = ManifestLoader.validate_manifest(m)
        assert any("semver" in i for i in issues)

    def test_validate_manifest_self_dependency(self):
        m = AppManifest(name="self", version="1.0.0", depends_on=["self"])
        issues = ManifestLoader.validate_manifest(m)
        assert any("cannot depend on itself" in i for i in issues)

    def test_validate_all(self):
        m1 = AppManifest(name="good", version="1.0.0")
        m2 = AppManifest(name="bad", version="1")  # bad version
        result = ManifestLoader.validate_all([m1, m2])
        assert "good" not in result
        assert "bad" in result
