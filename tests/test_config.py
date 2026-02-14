"""
Test 7: Config System (config.py)

Tests Config, ConfigLoader, NestedNamespace.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path

from aquilia.config import Config, ConfigLoader, ConfigError, NestedNamespace


# ============================================================================
# NestedNamespace
# ============================================================================

class TestNestedNamespace:

    def test_empty(self):
        ns = NestedNamespace()
        with pytest.raises(AttributeError):
            _ = ns.x

    def test_simple_access(self):
        ns = NestedNamespace({"name": "alice", "port": 8080})
        assert ns.name == "alice"
        assert ns.port == 8080

    def test_nested_access(self):
        ns = NestedNamespace({"db": {"host": "localhost", "port": 5432}})
        assert ns.db.host == "localhost"
        assert ns.db.port == 5432

    def test_getitem(self):
        ns = NestedNamespace({"key": "value"})
        assert ns["key"] == "value"

    def test_get_with_default(self):
        ns = NestedNamespace({"a": 1})
        assert ns.get("a") == 1
        assert ns.get("b", 42) == 42

    def test_contains(self):
        ns = NestedNamespace({"present": True})
        assert "present" in ns
        assert "absent" not in ns

    def test_missing_attr_raises(self):
        ns = NestedNamespace({"x": 1})
        with pytest.raises(AttributeError, match="no attribute"):
            _ = ns.y


# ============================================================================
# Config base class
# ============================================================================

class TestConfig:

    def test_is_base_class(self):
        assert Config is not None
        c = Config()
        assert isinstance(c, Config)


# ============================================================================
# ConfigLoader
# ============================================================================

class TestConfigLoader:

    def test_init_defaults(self):
        loader = ConfigLoader()
        assert loader.env_prefix == "AQ_"
        assert loader.config_data == {}

    def test_custom_prefix(self):
        loader = ConfigLoader(env_prefix="MY_")
        assert loader.env_prefix == "MY_"

    def test_merge_dict(self):
        loader = ConfigLoader()
        target = {"a": 1, "b": {"c": 2}}
        source = {"b": {"d": 3}, "e": 4}
        loader._merge_dict(target, source)
        assert target == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

    def test_merge_dict_overwrite(self):
        loader = ConfigLoader()
        target = {"a": 1}
        source = {"a": 2}
        loader._merge_dict(target, source)
        assert target["a"] == 2

    def test_get_dot_path(self):
        loader = ConfigLoader()
        loader.config_data = {"db": {"host": "localhost", "port": 5432}}
        assert loader.get("db.host") == "localhost"
        assert loader.get("db.port") == 5432
        assert loader.get("db.missing") is None
        assert loader.get("db.missing", "default") == "default"

    def test_get_nested(self):
        loader = ConfigLoader()
        loader.config_data = {"a": {"b": {"c": "deep"}}}
        assert loader.get("a.b.c") == "deep"
        assert loader.get("a.b.d", "fallback") == "fallback"

    def test_parse_value_bool(self):
        loader = ConfigLoader()
        assert loader._parse_value("true") is True
        assert loader._parse_value("false") is False
        assert loader._parse_value("yes") is True
        assert loader._parse_value("no") is False
        assert loader._parse_value("1") == 1  # parsed as int

    def test_parse_value_numbers(self):
        loader = ConfigLoader()
        assert loader._parse_value("42") == 42
        assert loader._parse_value("3.14") == 3.14

    def test_parse_value_json(self):
        loader = ConfigLoader()
        result = loader._parse_value('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_value_string(self):
        loader = ConfigLoader()
        assert loader._parse_value("hello") == "hello"

    def test_set_nested(self):
        loader = ConfigLoader()
        loader._set_nested("AQ_DB__HOST", "localhost")
        assert loader.config_data["db"]["host"] == "localhost"

    def test_to_dict(self):
        loader = ConfigLoader()
        loader.config_data = {"key": "value"}
        d = loader.to_dict()
        assert d == {"key": "value"}
        # Should be a copy
        d["new"] = "val"
        assert "new" not in loader.config_data

    def test_load_json_file(self):
        loader = ConfigLoader()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump({"server": {"port": 9090}}, f)
            f.flush()
            loader._load_json_file(Path(f.name))
        os.unlink(f.name)
        assert loader.config_data["server"]["port"] == 9090

    def test_load_env_file(self):
        loader = ConfigLoader()
        with tempfile.NamedTemporaryFile(
            suffix=".env", mode="w", delete=False
        ) as f:
            f.write("AQ_SERVER__PORT=4000\n")
            f.write("# comment\n")
            f.write("AQ_DEBUG=true\n")
            f.flush()
            loader._load_env_file(f.name)
        os.unlink(f.name)
        assert loader.config_data["server"]["port"] == 4000
        assert loader.config_data["debug"] is True

    def test_load_from_env_vars(self):
        loader = ConfigLoader()
        os.environ["AQ_TEST__ENV__VAR"] = "hello"
        try:
            loader._load_from_env()
            assert loader.config_data["test"]["env"]["var"] == "hello"
        finally:
            del os.environ["AQ_TEST__ENV__VAR"]

    def test_get_session_config_defaults(self):
        loader = ConfigLoader()
        sc = loader.get_session_config()
        assert sc["enabled"] is False
        assert sc["transport"]["adapter"] == "cookie"

    def test_get_auth_config_defaults(self):
        loader = ConfigLoader()
        ac = loader.get_auth_config()
        assert ac["enabled"] is False
        assert ac["tokens"]["algorithm"] == "HS256"

    def test_get_template_config_defaults(self):
        loader = ConfigLoader()
        tc = loader.get_template_config()
        assert tc["enabled"] is False
        assert tc["sandbox"] is True

    def test_get_app_config_dataclass(self):
        from dataclasses import dataclass

        @dataclass
        class MyConfig(Config):
            host: str = "localhost"
            port: int = 8080

        loader = ConfigLoader()
        loader.config_data = {"apps": {"myapp": {"port": 3000}}}
        loader._build_apps_namespace()
        cfg = loader.get_app_config("myapp", MyConfig)
        assert cfg.port == 3000
        assert cfg.host == "localhost"

    def test_config_error_on_missing_required(self):
        from dataclasses import dataclass

        @dataclass
        class StrictConfig(Config):
            required_field: str  # No default

        loader = ConfigLoader()
        loader.config_data = {"apps": {"test": {}}}
        loader._build_apps_namespace()
        with pytest.raises(ConfigError, match="required"):
            loader.get_app_config("test", StrictConfig)
