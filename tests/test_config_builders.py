"""
Test 16: Config Builders (config_builders.py)

Tests Workspace, Module, Integration, RuntimeConfig, ModuleConfig, AuthConfig.
"""

import pytest

from aquilia.config_builders import (
    Workspace,
    Module,
    Integration,
    RuntimeConfig,
    ModuleConfig,
    AuthConfig,
)


# ============================================================================
# RuntimeConfig
# ============================================================================

class TestRuntimeConfig:

    def test_defaults(self):
        rc = RuntimeConfig()
        assert rc.mode == "dev"
        assert rc.host == "127.0.0.1"
        assert rc.port == 8000
        assert rc.reload is True
        assert rc.workers == 1

    def test_custom(self):
        rc = RuntimeConfig(mode="prod", port=3000, workers=4)
        assert rc.mode == "prod"
        assert rc.port == 3000
        assert rc.workers == 4


# ============================================================================
# ModuleConfig
# ============================================================================

class TestModuleConfig:

    def test_create(self):
        mc = ModuleConfig(name="users")
        assert mc.name == "users"
        assert mc.auto_discover is True

    def test_to_dict(self):
        mc = ModuleConfig(name="users", version="1.0.0")
        d = mc.to_dict()
        assert d["name"] == "users"
        assert d["fault_domain"] == "USERS"
        assert d["route_prefix"] == "/users"


# ============================================================================
# Module builder
# ============================================================================

class TestModule:

    def test_basic(self):
        mod = Module("users")
        cfg = mod.build()
        assert cfg.name == "users"

    def test_fluent_chain(self):
        mod = (
            Module("users", version="1.0.0")
            .route_prefix("/api/users")
            .fault_domain("USER")
            .depends_on("auth")
            .tags("core", "api")
        )
        cfg = mod.build()
        assert cfg.route_prefix == "/api/users"
        assert cfg.fault_domain == "USER"
        assert "auth" in cfg.depends_on
        assert "core" in cfg.tags

    def test_register_controllers(self):
        mod = Module("users").register_controllers("UserCtrl")
        cfg = mod.build()
        assert "UserCtrl" in cfg.controllers

    def test_register_services(self):
        mod = Module("users").register_services("UserService")
        cfg = mod.build()
        assert "UserService" in cfg.services

    def test_register_sockets(self):
        mod = Module("chat").register_sockets("ChatSocket")
        cfg = mod.build()
        assert "ChatSocket" in cfg.socket_controllers

    def test_register_middlewares(self):
        mod = Module("api").register_middlewares("RateLimiter")
        cfg = mod.build()
        assert "RateLimiter" in cfg.middlewares

    def test_auto_discover(self):
        mod = Module("users").auto_discover(False)
        cfg = mod.build()
        assert cfg.auto_discover is False


# ============================================================================
# AuthConfig
# ============================================================================

class TestAuthConfig:

    def test_defaults(self):
        ac = AuthConfig()
        assert ac.enabled is True
        assert ac.algorithm == "HS256"
        assert ac.secret_key is None
        assert ac.require_auth_by_default is False

    def test_to_dict(self):
        ac = AuthConfig(secret_key="mysecret")
        d = ac.to_dict()
        assert d["tokens"]["secret_key"] == "mysecret"
        assert d["enabled"] is True


# ============================================================================
# Integration
# ============================================================================

class TestIntegration:

    def test_auth(self):
        config = Integration.auth(secret_key="test")
        assert config["enabled"] is True
        assert config["tokens"]["secret_key"] == "test"

    def test_auth_with_config(self):
        ac = AuthConfig(secret_key="from_config", algorithm="RS256")
        config = Integration.auth(config=ac)
        assert config["tokens"]["algorithm"] == "RS256"

    def test_di(self):
        config = Integration.di(auto_wire=True)
        assert config["auto_wire"] is True

    def test_routing(self):
        config = Integration.routing(strict_matching=False)
        assert config["strict_matching"] is False

    def test_fault_handling(self):
        config = Integration.fault_handling(default_strategy="recover")
        assert config["default_strategy"] == "recover"

    def test_patterns(self):
        config = Integration.patterns()
        assert config["enabled"] is True

    def test_registry(self):
        config = Integration.registry()
        assert config["enabled"] is True


# ============================================================================
# Integration.templates
# ============================================================================

class TestIntegrationTemplates:

    def test_defaults(self):
        builder = Integration.templates.defaults()
        assert builder["enabled"] is True
        assert builder["sandbox"] is True

    def test_source(self):
        builder = Integration.templates.source("views/", "shared/")
        assert "views/" in builder["search_paths"]
        assert "shared/" in builder["search_paths"]

    def test_secure(self):
        builder = Integration.templates.defaults().secure()
        assert builder["sandbox"] is True
        assert builder["sandbox_policy"] == "strict"

    def test_cached(self):
        builder = Integration.templates.defaults().cached("memory")
        assert builder["cache"] == "memory"

    def test_precompile(self):
        builder = Integration.templates.defaults().precompile()
        assert builder["precompile"] is True

    def test_unsafe_dev_mode(self):
        builder = Integration.templates.defaults().unsafe_dev_mode()
        assert builder["sandbox"] is False
        assert builder["cache"] == "none"


# ============================================================================
# Workspace
# ============================================================================

class TestWorkspace:

    def test_basic(self):
        ws = Workspace("myapp")
        assert repr(ws) == "Workspace(name='myapp', version='0.1.0', modules=0)"

    def test_runtime(self):
        ws = Workspace("app").runtime(mode="prod", port=3000)
        d = ws.to_dict()
        assert d["runtime"]["mode"] == "prod"
        assert d["runtime"]["port"] == 3000

    def test_add_module(self):
        ws = Workspace("app").module(Module("users"))
        d = ws.to_dict()
        assert len(d["modules"]) == 1
        assert d["modules"][0]["name"] == "users"

    def test_add_multiple_modules(self):
        ws = (
            Workspace("app")
            .module(Module("users"))
            .module(Module("posts"))
        )
        d = ws.to_dict()
        assert len(d["modules"]) == 2

    def test_integrate_auth(self):
        ws = Workspace("app").integrate(Integration.auth(secret_key="test"))
        d = ws.to_dict()
        assert "auth" in d["integrations"]

    def test_integrate_di(self):
        ws = Workspace("app").integrate(Integration.di())
        d = ws.to_dict()
        assert "dependency_injection" in d["integrations"]

    def test_security(self):
        ws = Workspace("app").security(cors_enabled=True)
        d = ws.to_dict()
        assert d["security"]["cors_enabled"] is True

    def test_telemetry(self):
        ws = Workspace("app").telemetry(tracing_enabled=True)
        d = ws.to_dict()
        assert d["telemetry"]["tracing_enabled"] is True

    def test_full_workspace(self):
        ws = (
            Workspace("myapp", version="1.0.0")
            .runtime(mode="dev", port=8000)
            .module(
                Module("users", version="1.0.0")
                .route_prefix("/api/users")
                .fault_domain("USER")
            )
            .integrate(Integration.auth(secret_key="secret"))
            .integrate(Integration.di())
            .security(cors_enabled=True)
            .telemetry(metrics_enabled=True)
        )
        d = ws.to_dict()
        assert d["workspace"]["name"] == "myapp"
        assert d["workspace"]["version"] == "1.0.0"
        assert len(d["modules"]) == 1
        assert "auth" in d["integrations"]
        assert d["security"]["cors_enabled"] is True

    def test_to_dict_structure(self):
        ws = Workspace("test")
        d = ws.to_dict()
        assert "workspace" in d
        assert "runtime" in d
        assert "modules" in d
        assert "integrations" in d
