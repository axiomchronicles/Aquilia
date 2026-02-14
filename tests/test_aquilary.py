"""
Test 19: Aquilary System (aquilary/)

Tests AppContext, RegistryMode, RegistryFingerprint,
AquilaryRegistry, Aquilary.
"""

import pytest

from aquilia.aquilary.core import (
    AppContext,
    RegistryMode,
    RegistryFingerprint,
    AquilaryRegistry,
)


# ============================================================================
# RegistryMode
# ============================================================================

class TestRegistryMode:

    def test_values(self):
        assert RegistryMode.DEV == "dev"
        assert RegistryMode.PROD == "prod"
        assert RegistryMode.TEST == "test"


# ============================================================================
# AppContext
# ============================================================================

class TestAppContext:

    def test_create(self):
        ctx = AppContext(
            name="users",
            version="1.0.0",
            manifest=None,
            config_namespace={},
        )
        assert ctx.name == "users"
        assert ctx.version == "1.0.0"
        assert ctx.controllers == []
        assert ctx.services == []
        assert ctx.depends_on == []

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="must have a name"):
            AppContext(name="", version="1.0.0", manifest=None, config_namespace={})

    def test_missing_version_raises(self):
        with pytest.raises(ValueError, match="must have a version"):
            AppContext(name="users", version="", manifest=None, config_namespace={})

    def test_with_controllers(self):
        ctx = AppContext(
            name="users",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            controllers=["UserCtrl"],
        )
        assert "UserCtrl" in ctx.controllers

    def test_with_lifecycle(self):
        async def on_start(config, container):
            pass

        ctx = AppContext(
            name="users",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            on_startup=on_start,
        )
        assert ctx.on_startup is not None

    def test_load_order(self):
        ctx = AppContext(
            name="users",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            load_order=5,
        )
        assert ctx.load_order == 5

    def test_depends_on(self):
        ctx = AppContext(
            name="posts",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            depends_on=["users", "auth"],
        )
        assert "users" in ctx.depends_on
        assert "auth" in ctx.depends_on


# ============================================================================
# RegistryFingerprint
# ============================================================================

class TestRegistryFingerprint:

    def test_create(self):
        fp = RegistryFingerprint(
            hash="abc123",
            timestamp="2024-01-01T00:00:00Z",
            mode="dev",
            app_count=3,
            route_count=10,
            manifest_sources=["users", "auth"],
        )
        assert fp.hash == "abc123"
        assert fp.app_count == 3

    def test_to_dict(self):
        fp = RegistryFingerprint(
            hash="abc",
            timestamp="now",
            mode="prod",
            app_count=1,
            route_count=5,
            manifest_sources=["main"],
        )
        d = fp.to_dict()
        assert d["hash"] == "abc"
        assert d["mode"] == "prod"
        assert d["route_count"] == 5


# ============================================================================
# AquilaryRegistry
# ============================================================================

class TestAquilaryRegistry:

    def _make_registry(self):
        ctx = AppContext(
            name="users",
            version="1.0.0",
            manifest=None,
            config_namespace={},
            controllers=["UserCtrl"],
        )
        return AquilaryRegistry(
            app_contexts=[ctx],
            fingerprint="fp_test",
            mode=RegistryMode.DEV,
            dependency_graph={"users": []},
            route_index={},
            validation_report={},
            config=None,
        )

    def test_create(self):
        reg = self._make_registry()
        assert reg.fingerprint == "fp_test"
        assert reg.mode == RegistryMode.DEV
        assert len(reg.app_contexts) == 1

    def test_inspect(self):
        reg = self._make_registry()
        info = reg.inspect()
        assert info["fingerprint"] == "fp_test"
        assert info["app_count"] == 1
        assert info["apps"][0]["name"] == "users"
        assert info["apps"][0]["controllers"] == 1
