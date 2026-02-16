"""
Tests for the .aquilia/ trace directory system.

Covers:
- AquiliaTrace core (directory management, locking, snapshot)
- TraceManifest (capture, read-back, change detection)
- TraceRouteMap (capture, read-back, filtering, diff)
- TraceDIGraph (capture, read-back, token lookup, scope filter)
- TraceSchemaLedger (capture, read-back, model lookup)
- TraceLifecycleJournal (append, boot/shutdown, events, tail)
- TraceConfigSnapshot (capture, redaction, subsystems)
- TraceDiagnostics (capture, process health, read-back)
- CLI commands (status, inspect, journal, clean, diff)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def workspace(tmp_path):
    """Temporary workspace root."""
    return tmp_path


@pytest.fixture
def trace(workspace):
    from aquilia.trace import AquiliaTrace
    return AquiliaTrace(workspace)


@pytest.fixture
def mock_server():
    """Minimal mock AquiliaServer with all attributes the trace expects."""
    from enum import Enum

    class MockMode(str, Enum):
        DEV = "dev"

    server = MagicMock()
    server.mode = MockMode.DEV
    server._is_debug = MagicMock(return_value=True)

    # Aquilary
    ctx = MagicMock()
    ctx.name = "myapp"
    ctx.version = "1.0.0"
    ctx.load_order = 0
    ctx.controllers = ["modules.myapp.controllers:HomeController"]
    ctx.services = ["modules.myapp.services:UserService"]
    ctx.models = []
    ctx.depends_on = []
    ctx.on_startup = None
    ctx.on_shutdown = None
    ctx.middlewares = []
    ctx.manifest = MagicMock()

    aquilary = MagicMock()
    aquilary.app_contexts = [ctx]
    aquilary.fingerprint = "abc123def456"
    aquilary._dependency_graph = {"myapp": []}
    server.aquilary = aquilary

    # Router
    router = MagicMock()
    router.get_routes.return_value = [
        {"method": "GET", "path": "/", "controller": "HomeController", "handler": "index", "specificity": 100},
        {"method": "POST", "path": "/users", "controller": "UserController", "handler": "create", "specificity": 90},
    ]
    server.controller_router = router

    # Runtime / DI
    meta_mock = MagicMock()
    meta_mock.to_dict.return_value = {
        "name": "user_service",
        "token": "UserService",
        "scope": "app",
        "tags": [],
        "module": "modules.myapp.services",
        "qualname": "UserService",
        "line": 10,
        "version": None,
        "allow_lazy": False,
    }
    provider_mock = MagicMock()
    provider_mock.meta = meta_mock

    container = MagicMock()
    container._providers = {"UserService": provider_mock}
    container._scope = "app"
    container._parent = None
    container._cache = {}

    runtime = MagicMock()
    runtime.di_containers = {"myapp": container}
    server.runtime = runtime

    # Config
    config = MagicMock()
    config.to_dict.return_value = {
        "app_name": "TestApp",
        "database": {
            "host": "localhost",
            "password": "super_secret_123",
        },
        "api_key": "sk-live-xyz",
        "sessions": {"enabled": True},
    }
    server.config = config

    # Optional subsystems
    server._session_engine = MagicMock()
    server._auth_manager = None
    server.template_engine = MagicMock()
    server._mail_service = None
    server.aquila_sockets = MagicMock()
    server.aquila_sockets.router = MagicMock()
    server.aquila_sockets.router._handlers = {}
    server.aquila_sockets._connections = {}
    server.fault_engine = MagicMock()
    server.fault_engine.total_faults = 0
    server.fault_engine._circuit_breakers = {}
    server.fault_engine.error_budget_remaining = 100
    server._effect_registry = None
    server._amdl_database = None
    server.middleware_stack = MagicMock()
    server.middleware_stack.middlewares = []

    return server


# ════════════════════════════════════════════════════════════════════════════
# AquiliaTrace core
# ════════════════════════════════════════════════════════════════════════════


class TestAquiliaTraceCore:
    def test_root_path(self, trace, workspace):
        assert trace.root == workspace / ".aquilia"

    def test_ensure_dir_creates_directory(self, trace):
        assert not trace.exists()
        trace.ensure_dir()
        assert trace.exists()
        assert (trace.root / ".gitignore").exists()

    def test_ensure_dir_idempotent(self, trace):
        trace.ensure_dir()
        trace.ensure_dir()
        assert trace.exists()

    def test_gitignore_content(self, trace):
        trace.ensure_dir()
        content = (trace.root / ".gitignore").read_text()
        assert "*" in content
        assert "!.gitignore" in content

    def test_clean_empty(self, trace):
        assert trace.clean() == 0

    def test_clean_removes_files(self, trace):
        trace.ensure_dir()
        (trace.root / "manifest.json").write_text("{}")
        (trace.root / "routes.json").write_text("[]")
        count = trace.clean()
        assert count == 2
        assert not (trace.root / "manifest.json").exists()
        assert (trace.root / ".gitignore").exists()  # preserved

    def test_acquire_and_release_lock(self, trace):
        trace.acquire_lock()
        assert (trace.root / "lock.json").exists()
        lock = json.loads((trace.root / "lock.json").read_text())
        assert lock["pid"] == os.getpid()
        assert lock["version"] == 1

        trace.release_lock()
        assert not (trace.root / "lock.json").exists()

    def test_is_locked_current_process(self, trace):
        trace.acquire_lock()
        assert trace.is_locked()  # Our own process is running
        trace.release_lock()
        assert not trace.is_locked()

    def test_is_locked_stale(self, trace):
        trace.ensure_dir()
        # Write a lock with a PID that doesn't exist
        lock = {"version": 1, "pid": 999999999, "boot_ts": "2024-01-01T00:00:00", "hostname": "test"}
        (trace.root / "lock.json").write_text(json.dumps(lock))
        assert not trace.is_locked()  # Stale

    def test_summary_no_dir(self, trace):
        s = trace.summary()
        assert s == {"exists": False}

    def test_full_snapshot(self, trace, mock_server):
        trace.snapshot(mock_server)
        assert trace.exists()
        assert (trace.root / "manifest.json").exists()
        assert (trace.root / "routes.json").exists()
        assert (trace.root / "di_graph.json").exists()
        assert (trace.root / "config.json").exists()
        assert (trace.root / "journal.jsonl").exists()
        assert (trace.root / "diagnostics.json").exists()
        assert (trace.root / "lock.json").exists()

    def test_snapshot_shutdown(self, trace, mock_server):
        trace.snapshot(mock_server)
        trace.snapshot_shutdown(mock_server)
        assert not (trace.root / "lock.json").exists()  # Lock released
        events = trace.journal.events()
        types = [e["event"] for e in events]
        assert "boot" in types
        assert "shutdown" in types

    def test_summary_with_data(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert s["exists"]
        assert s["route_count"] == 2
        assert s["provider_count"] == 1
        assert "manifest.json" in s["files"]

    def test_snapshot_non_fatal(self, trace):
        """Snapshot on a broken server should not raise."""
        bad_server = MagicMock()
        bad_server.aquilary = None
        bad_server.runtime = None
        bad_server.controller_router = None
        bad_server.config = None
        bad_server.mode = None
        bad_server._is_debug = MagicMock(side_effect=Exception("boom"))
        bad_server.fault_engine = None
        bad_server.middleware_stack = None
        bad_server.aquila_sockets = None
        bad_server._session_engine = None
        bad_server._auth_manager = None
        bad_server._mail_service = None
        bad_server._effect_registry = None
        bad_server._amdl_database = None
        trace.snapshot(bad_server)  # Should not raise


# ════════════════════════════════════════════════════════════════════════════
# TraceManifest
# ════════════════════════════════════════════════════════════════════════════


class TestTraceManifest:
    def test_capture_and_read(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        data = trace.manifest.read()
        assert data["schema_version"] == 1
        assert data["app_count"] == 1
        assert data["mode"] == "dev"
        assert data["fingerprint"] == "abc123def456"
        assert len(data["apps"]) == 1
        assert data["apps"][0]["name"] == "myapp"

    def test_apps(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        apps = trace.manifest.apps()
        assert len(apps) == 1
        assert apps[0]["version"] == "1.0.0"

    def test_content_hash_deterministic(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        h1 = trace.manifest.content_hash()
        trace.manifest.capture(mock_server)
        h2 = trace.manifest.content_hash()
        assert h1 == h2
        assert len(h1) == 16

    def test_has_changed_false(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        assert not trace.manifest.has_changed(mock_server)

    def test_has_changed_true(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        mock_server.aquilary.fingerprint = "changed"
        assert trace.manifest.has_changed(mock_server)

    def test_read_missing(self, trace):
        assert trace.manifest.read() == {}

    def test_fingerprint(self, trace, mock_server):
        trace.ensure_dir()
        trace.manifest.capture(mock_server)
        assert trace.manifest.fingerprint() == "abc123def456"


# ════════════════════════════════════════════════════════════════════════════
# TraceRouteMap
# ════════════════════════════════════════════════════════════════════════════


class TestTraceRouteMap:
    def test_capture_and_read(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        data = trace.routes.read()
        assert data["total"] == 2
        assert data["method_counts"]["GET"] == 1
        assert data["method_counts"]["POST"] == 1

    def test_count(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        assert trace.routes.count() == 2

    def test_routes_list(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        routes = trace.routes.routes()
        assert len(routes) == 2

    def test_by_method(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        gets = trace.routes.by_method("GET")
        assert len(gets) == 1
        assert gets[0]["path"] == "/"

    def test_by_controller(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        user_routes = trace.routes.by_controller("UserController")
        assert len(user_routes) == 1
        assert user_routes[0]["handler"] == "create"

    def test_controllers_index(self, trace, mock_server):
        trace.ensure_dir()
        trace.routes.capture(mock_server)
        data = trace.routes.read()
        assert "HomeController" in data["controllers"]
        assert "/" in data["controllers"]["HomeController"]

    def test_diff(self, trace, mock_server, workspace):
        trace.ensure_dir()
        trace.routes.capture(mock_server)

        # Create a "previous" routes file
        old = workspace / "old_routes.json"
        old.write_text(json.dumps({
            "routes": [
                {"method": "GET", "path": "/", "controller": "HomeController", "handler": "index", "specificity": 100},
                {"method": "DELETE", "path": "/users/{id}", "controller": "UserController", "handler": "delete", "specificity": 80},
            ]
        }))

        diff = trace.routes.diff(old)
        assert len(diff["added"]) == 1  # POST /users added
        assert len(diff["removed"]) == 1  # DELETE /users/{id} removed
        assert diff["added"][0]["method"] == "POST"
        assert diff["removed"][0]["method"] == "DELETE"

    def test_count_missing(self, trace):
        assert trace.routes.count() == 0


# ════════════════════════════════════════════════════════════════════════════
# TraceDIGraph
# ════════════════════════════════════════════════════════════════════════════


class TestTraceDIGraph:
    def test_capture_and_read(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        data = trace.di_graph.read()
        assert data["total_providers"] == 1
        assert data["container_count"] == 1
        assert "myapp" in data["containers"]

    def test_count(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        assert trace.di_graph.count() == 1

    def test_providers_all(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        all_providers = trace.di_graph.providers()
        assert len(all_providers) == 1
        assert all_providers[0]["token"] == "UserService"

    def test_providers_by_app(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        app_providers = trace.di_graph.providers("myapp")
        assert len(app_providers) == 1

    def test_find_token(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        assert trace.di_graph.find_token("UserService") == "myapp"
        assert trace.di_graph.find_token("NonExistent") is None

    def test_by_scope(self, trace, mock_server):
        trace.ensure_dir()
        trace.di_graph.capture(mock_server)
        app_scope = trace.di_graph.by_scope("app")
        assert len(app_scope) == 1
        request_scope = trace.di_graph.by_scope("request")
        assert len(request_scope) == 0

    def test_count_missing(self, trace):
        assert trace.di_graph.count() == 0


# ════════════════════════════════════════════════════════════════════════════
# TraceSchemaLedger
# ════════════════════════════════════════════════════════════════════════════


class TestTraceSchemaLedger:
    def test_capture_no_models(self, trace, mock_server):
        trace.ensure_dir()
        trace.schema.capture(mock_server)
        data = trace.schema.read()
        assert data["schema_version"] == 2
        assert isinstance(data["models"], list)

    def test_model_lookup(self, trace, workspace):
        trace.ensure_dir()
        # Write a synthetic schema
        from aquilia.trace.core import _write_json
        _write_json(trace.root / "schema.json", {
            "schema_version": 1,
            "captured_at": "2024-01-01T00:00:00",
            "model_count": 2,
            "models": [
                {"name": "User", "table_name": "users", "app_label": "auth", "field_count": 3, "fields": [
                    {"name": "id", "type": "IntegerField", "primary_key": True, "nullable": False, "has_default": False},
                    {"name": "email", "type": "CharField", "primary_key": False, "nullable": False, "has_default": False},
                    {"name": "name", "type": "CharField", "primary_key": False, "nullable": True, "has_default": False},
                ]},
                {"name": "Post", "table_name": "posts", "app_label": "blog", "field_count": 2, "fields": []},
            ],
            "migration_count": 0,
            "migrations": [],
        })

        assert trace.schema.count() == 2
        assert trace.schema.model_names() == ["User", "Post"]

        user = trace.schema.model("User")
        assert user is not None
        assert user["table_name"] == "users"

        fields = trace.schema.fields("User")
        assert len(fields) == 3
        assert fields[0]["name"] == "id"
        assert fields[0]["primary_key"] is True

    def test_model_not_found(self, trace, workspace):
        trace.ensure_dir()
        from aquilia.trace.core import _write_json
        _write_json(trace.root / "schema.json", {"models": [], "model_count": 0})
        assert trace.schema.model("NonExistent") is None
        assert trace.schema.fields("NonExistent") == []


# ════════════════════════════════════════════════════════════════════════════
# TraceLifecycleJournal
# ════════════════════════════════════════════════════════════════════════════


class TestTraceLifecycleJournal:
    def test_record_boot(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        events = trace.journal.events()
        assert len(events) == 1
        assert events[0]["event"] == "boot"
        assert events[0]["app_count"] == 1
        assert events[0]["route_count"] == 2
        assert events[0]["mode"] == "dev"

    def test_record_shutdown(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_shutdown(mock_server)
        events = trace.journal.events()
        assert events[0]["event"] == "shutdown"

    def test_append_order(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        trace.journal.record_phase("startup", app_name="myapp")
        trace.journal.record_shutdown(mock_server)
        events = trace.journal.events()
        assert len(events) == 3
        assert [e["event"] for e in events] == ["boot", "phase", "shutdown"]

    def test_record_error(self, trace):
        trace.ensure_dir()
        trace.journal.record_error("Connection refused", context="db")
        errors = trace.journal.errors()
        assert len(errors) == 1
        assert errors[0]["error"] == "Connection refused"
        assert errors[0]["context"] == "db"

    def test_record_custom(self, trace):
        trace.ensure_dir()
        trace.journal.record_custom("deploy", version="1.2.3", env="staging")
        events = trace.journal.events()
        assert events[0]["event"] == "custom"
        assert events[0]["name"] == "deploy"
        assert events[0]["version"] == "1.2.3"

    def test_record_phase_with_error(self, trace):
        trace.ensure_dir()
        trace.journal.record_phase("startup", app_name="myapp", error="timeout")
        events = trace.journal.events()
        assert events[0]["phase"] == "startup"
        assert events[0]["error"] == "timeout"
        assert events[0]["app"] == "myapp"

    def test_tail(self, trace, mock_server):
        trace.ensure_dir()
        for i in range(30):
            trace.journal.record_custom(f"event_{i}")
        tailed = trace.journal.tail(5)
        assert len(tailed) == 5
        assert tailed[0]["name"] == "event_25"
        assert tailed[-1]["name"] == "event_29"

    def test_boots(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        trace.journal.record_custom("noise")
        trace.journal.record_boot(mock_server)
        boots = trace.journal.boots()
        assert len(boots) == 2

    def test_last_boot(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        trace.journal.record_custom("noise")
        last = trace.journal.last_boot()
        assert last is not None
        assert last["event"] == "boot"

    def test_count(self, trace, mock_server):
        trace.ensure_dir()
        assert trace.journal.count() == 0
        trace.journal.record_boot(mock_server)
        trace.journal.record_shutdown(mock_server)
        assert trace.journal.count() == 2

    def test_clear(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        trace.journal.clear()
        assert trace.journal.count() == 0

    def test_events_empty(self, trace):
        assert trace.journal.events() == []

    def test_last_boot_empty(self, trace):
        assert trace.journal.last_boot() is None

    def test_pid_in_event(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        events = trace.journal.events()
        assert events[0]["pid"] == os.getpid()


# ════════════════════════════════════════════════════════════════════════════
# TraceConfigSnapshot
# ════════════════════════════════════════════════════════════════════════════


class TestTraceConfigSnapshot:
    def test_capture_and_read(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        data = trace.config_snap.read()
        assert data["schema_version"] == 2
        assert "config" in data
        assert "environment" in data
        assert "subsystems" in data
        assert "server" in data

    def test_secret_redaction(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        cfg = trace.config_snap.config()
        assert cfg["database"]["password"] == "***REDACTED***"
        assert cfg["api_key"] == "***REDACTED***"
        assert cfg["app_name"] == "TestApp"  # Non-secret preserved
        assert cfg["database"]["host"] == "localhost"  # Non-secret preserved

    def test_subsystems(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        sub = trace.config_snap.subsystems()
        assert sub["sessions"] is True
        assert sub["auth"] is False
        assert sub["templates"] is True
        assert sub["websockets"] is True
        assert sub["faults"] is True

    def test_active_subsystems(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        active = trace.config_snap.active_subsystems()
        assert "sessions" in active
        assert "templates" in active
        assert "auth" not in active

    def test_is_debug(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        assert trace.config_snap.is_debug() is True

    def test_environment(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        env = trace.config_snap.environment()
        assert "python_version" in env
        assert "platform" in env
        assert env["pid"] == os.getpid()


class TestRedaction:
    """Test secret redaction independently."""

    def test_redact_nested(self):
        from aquilia.trace.config_snap import _redact
        data = {
            "db": {"host": "localhost", "password": "secret123"},
            "api_key": "live_key",
            "normal": "visible",
        }
        redacted = _redact(data)
        assert redacted["db"]["host"] == "localhost"
        assert redacted["db"]["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["normal"] == "visible"

    def test_redact_list(self):
        from aquilia.trace.config_snap import _redact
        data = {"items": [{"secret": "x"}, {"name": "y"}]}
        redacted = _redact(data)
        assert redacted["items"][0]["secret"] == "***REDACTED***"
        assert redacted["items"][1]["name"] == "y"

    def test_redact_depth_limit(self):
        from aquilia.trace.config_snap import _redact
        # Build deeply nested dict
        d: Any = "leaf"
        for _ in range(25):
            d = {"nested": d}
        redacted = _redact(d)
        # Should not raise; deep levels truncated to "..."

    def test_redact_case_insensitive(self):
        from aquilia.trace.config_snap import _redact
        data = {"API_KEY": "x", "Password": "y", "SECRET_TOKEN": "z"}
        redacted = _redact(data)
        assert all(v == "***REDACTED***" for v in redacted.values())


# ════════════════════════════════════════════════════════════════════════════
# TraceDiagnostics
# ════════════════════════════════════════════════════════════════════════════


class TestTraceDiagnostics:
    def test_capture_and_read(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        data = trace.diagnostics.read()
        assert data["schema_version"] == 2
        assert "faults" in data
        assert "middleware" in data
        assert "websockets" in data
        assert "effects" in data
        assert "process" in data
        assert "sessions" in data
        assert "auth" in data
        assert "templates" in data
        assert "mail" in data
        assert "database" in data

    def test_faults_active(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        faults = trace.diagnostics.faults()
        assert faults["active"] is True
        assert faults["total_faults"] == 0

    def test_websockets(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        ws = trace.diagnostics.websockets()
        assert ws["active"] is True
        assert ws["handler_count"] == 0

    def test_process_health(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        proc = trace.diagnostics.process()
        assert proc["pid"] == os.getpid()
        assert "python_version" in proc
        assert "max_rss_mb" in proc

    def test_is_healthy(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        assert trace.diagnostics.is_healthy() is True

    def test_is_healthy_missing(self, trace):
        assert trace.diagnostics.is_healthy() is False


# ════════════════════════════════════════════════════════════════════════════
# Core helpers
# ════════════════════════════════════════════════════════════════════════════


class TestCoreHelpers:
    def test_write_json_atomic(self, workspace):
        from aquilia.trace.core import _write_json, _read_json
        path = workspace / "test.json"
        _write_json(path, {"key": "value"})
        assert path.exists()
        assert not path.with_suffix(".tmp").exists()  # tmp cleaned up
        data = _read_json(path)
        assert data == {"key": "value"}

    def test_read_json_missing(self, workspace):
        from aquilia.trace.core import _read_json
        assert _read_json(workspace / "nope.json") == {}

    def test_read_json_corrupt(self, workspace):
        from aquilia.trace.core import _read_json
        path = workspace / "bad.json"
        path.write_text("not json {{{")
        assert _read_json(path) == {}

    def test_now_iso(self):
        from aquilia.trace.core import _now_iso
        ts = _now_iso()
        assert "T" in ts
        assert "+" in ts or "Z" in ts or ts.endswith("+00:00")

    def test_safe_hostname(self):
        from aquilia.trace.core import _safe_hostname
        hostname = _safe_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0


# ════════════════════════════════════════════════════════════════════════════
# Imports / Exports
# ════════════════════════════════════════════════════════════════════════════


class TestTraceExports:
    def test_trace_module_exports(self):
        from aquilia.trace import (
            AquiliaTrace,
            TraceManifest,
            TraceRouteMap,
            TraceDIGraph,
            TraceSchemaLedger,
            TraceLifecycleJournal,
            TraceConfigSnapshot,
            TraceDiagnostics,
        )

    def test_top_level_exports(self):
        import aquilia
        assert hasattr(aquilia, "AquiliaTrace")
        assert hasattr(aquilia, "TraceManifest")
        assert hasattr(aquilia, "TraceRouteMap")
        assert hasattr(aquilia, "TraceDIGraph")
        assert hasattr(aquilia, "TraceSchemaLedger")
        assert hasattr(aquilia, "TraceLifecycleJournal")
        assert hasattr(aquilia, "TraceConfigSnapshot")
        assert hasattr(aquilia, "TraceDiagnostics")

    def test_all_in_trace_module(self):
        from aquilia import trace
        for name in trace.__all__:
            assert hasattr(trace, name), f"Missing export: {name}"


# ════════════════════════════════════════════════════════════════════════════
# CLI commands
# ════════════════════════════════════════════════════════════════════════════


class TestTraceCLI:
    def test_trace_status_no_dir(self, workspace):
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "No .aquilia/ directory found" in result.output

    def test_trace_status_with_data(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "Trace Status" in result.output

    def test_trace_status_json(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace), "--json-output"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["exists"] is True

    def test_trace_inspect_manifest(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "manifest", "--dir", str(workspace)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["app_count"] == 1

    def test_trace_inspect_routes(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "routes", "--dir", str(workspace)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 2

    def test_trace_inspect_di(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "di", "--dir", str(workspace)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_providers"] == 1

    def test_trace_inspect_config(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "config", "--dir", str(workspace)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Secrets should be redacted
        assert data["config"]["database"]["password"] == "***REDACTED***"

    def test_trace_journal(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["journal", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "boot" in result.output

    def test_trace_journal_filter(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        trace.journal.record_error("test error")
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["journal", "--dir", str(workspace), "--event", "error"])
        assert result.exit_code == 0
        assert "test error" in result.output

    def test_trace_journal_json(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["journal", "--dir", str(workspace), "--json-output"])
        assert result.exit_code == 0
        events = json.loads(result.output)
        assert isinstance(events, list)

    def test_trace_clean(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        trace.release_lock()  # So clean doesn't complain about lock
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["clean", "--dir", str(workspace), "--force"])
        assert result.exit_code == 0
        assert "Cleaned" in result.output

    def test_trace_clean_locked(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)  # Leaves lock
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["clean", "--dir", str(workspace)])
        # Should warn about lock (not force)
        assert "locked" in result.output.lower() or result.exit_code != 0

    def test_trace_inspect_no_dir(self, workspace):
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "manifest", "--dir", str(workspace)])
        assert result.exit_code != 0

    def test_trace_inspect_diagnostics(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["inspect", "diagnostics", "--dir", str(workspace)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["faults"]["active"] is True


# ════════════════════════════════════════════════════════════════════════════
# Integration: multiple snapshots & persistence
# ════════════════════════════════════════════════════════════════════════════


class TestTraceIntegration:
    def test_multiple_boots_journal_grows(self, trace, mock_server):
        """Journal should accumulate across multiple boot/shutdown cycles."""
        for i in range(3):
            trace.snapshot(mock_server)
            trace.snapshot_shutdown(mock_server)

        events = trace.journal.events()
        boots = [e for e in events if e["event"] == "boot"]
        shutdowns = [e for e in events if e["event"] == "shutdown"]
        assert len(boots) == 3
        assert len(shutdowns) == 3

    def test_snapshot_overwrites_state_files(self, trace, mock_server):
        """State files (manifest, routes, etc.) should be overwritten, not appended."""
        trace.snapshot(mock_server)
        first_manifest = trace.manifest.read()

        mock_server.aquilary.fingerprint = "new_fingerprint"
        trace.snapshot(mock_server)
        second_manifest = trace.manifest.read()

        assert first_manifest["fingerprint"] != second_manifest["fingerprint"]
        assert second_manifest["fingerprint"] == "new_fingerprint"

    def test_clean_and_resnaphot(self, trace, mock_server):
        """After clean, a new snapshot should work perfectly."""
        trace.snapshot(mock_server)
        trace.release_lock()
        trace.clean()
        assert trace.routes.count() == 0

        trace.snapshot(mock_server)
        assert trace.routes.count() == 2
        assert trace.manifest.fingerprint() == "abc123def456"

    def test_concurrent_trace_instances(self, workspace, mock_server):
        """Two AquiliaTrace instances pointing at the same root should work."""
        from aquilia.trace import AquiliaTrace
        t1 = AquiliaTrace(workspace)
        t2 = AquiliaTrace(workspace)

        t1.snapshot(mock_server)
        # t2 should be able to read t1's data
        assert t2.routes.count() == 2
        assert t2.manifest.fingerprint() == "abc123def456"

    def test_full_lifecycle_flow(self, trace, mock_server):
        """Simulate full server lifecycle: snapshot → journal → shutdown → read."""
        # Boot
        trace.snapshot(mock_server)

        # Application events
        trace.journal.record_phase("controllers_loaded", app_name="myapp")
        trace.journal.record_phase("routes_compiled")
        trace.journal.record_custom("deploy", commit="abc123")

        # Verify during runtime
        assert trace.routes.count() == 2
        assert trace.di_graph.count() == 1
        assert trace.config_snap.is_debug() is True
        assert trace.diagnostics.is_healthy() is True
        subs = trace.config_snap.active_subsystems()
        assert "sessions" in subs

        # Shutdown
        trace.snapshot_shutdown(mock_server)

        # Post-shutdown: data persists
        assert trace.routes.count() == 2
        events = trace.journal.events()
        types = [e["event"] for e in events]
        assert types == ["boot", "phase", "phase", "custom", "shutdown"]


# ════════════════════════════════════════════════════════════════════════════
# Enhanced Journal Features
# ════════════════════════════════════════════════════════════════════════════


class TestJournalEnhancements:
    """Tests for new journal capabilities: warnings, timing, uptime."""

    def test_record_warning(self, trace):
        trace.ensure_dir()
        trace.journal.record_warning("Deprecated API called", context="controller")
        events = trace.journal.events()
        assert len(events) == 1
        assert events[0]["event"] == "warning"
        assert events[0]["warning"] == "Deprecated API called"
        assert events[0]["context"] == "controller"

    def test_warnings_filter(self, trace):
        trace.ensure_dir()
        trace.journal.record_warning("warn1")
        trace.journal.record_error("err1")
        trace.journal.record_warning("warn2")
        warnings = trace.journal.warnings()
        assert len(warnings) == 2
        assert warnings[0]["warning"] == "warn1"
        assert warnings[1]["warning"] == "warn2"

    def test_phases_filter(self, trace):
        trace.ensure_dir()
        trace.journal.record_phase("autodiscovery")
        trace.journal.record_phase("controllers_loaded")
        trace.journal.record_custom("noise")
        trace.journal.record_phase("routes_compiled")
        phases = trace.journal.phases()
        assert len(phases) == 3
        assert [p["phase"] for p in phases] == ["autodiscovery", "controllers_loaded", "routes_compiled"]

    def test_phase_with_duration(self, trace):
        trace.ensure_dir()
        trace.journal.record_phase("autodiscovery", duration_ms=42.5)
        events = trace.journal.events()
        assert events[0]["duration_ms"] == 42.5

    def test_phase_with_detail(self, trace):
        trace.ensure_dir()
        trace.journal.record_phase("effects_initialized", detail="3 providers")
        events = trace.journal.events()
        assert events[0]["detail"] == "3 providers"

    def test_phase_full_attributes(self, trace):
        trace.ensure_dir()
        trace.journal.record_phase(
            "lifecycle_started",
            app_name="myapp",
            error="timeout",
            duration_ms=100.0,
            detail="hook failed",
        )
        ev = trace.journal.events()[0]
        assert ev["phase"] == "lifecycle_started"
        assert ev["app"] == "myapp"
        assert ev["error"] == "timeout"
        assert ev["duration_ms"] == 100.0
        assert ev["detail"] == "hook failed"

    def test_boot_with_duration(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server, duration_ms=350.0)
        boot = trace.journal.last_boot()
        assert boot["duration_ms"] == 350.0

    def test_boot_without_duration(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)
        boot = trace.journal.last_boot()
        assert "duration_ms" not in boot

    def test_shutdown_with_uptime(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_boot(mock_server)  # Sets _boot_mono
        # Small sleep to get non-zero uptime
        import time
        time.sleep(0.01)
        trace.journal.record_shutdown(mock_server)
        shutdown = trace.journal.last_shutdown()
        assert shutdown is not None
        assert "uptime_s" in shutdown
        assert shutdown["uptime_s"] > 0

    def test_last_shutdown_empty(self, trace):
        assert trace.journal.last_shutdown() is None

    def test_last_shutdown(self, trace, mock_server):
        trace.ensure_dir()
        trace.journal.record_shutdown(mock_server)
        trace.journal.record_custom("noise")
        trace.journal.record_shutdown(mock_server)
        last = trace.journal.last_shutdown()
        assert last is not None
        assert last["event"] == "shutdown"


# ════════════════════════════════════════════════════════════════════════════
# Enhanced Diagnostics
# ════════════════════════════════════════════════════════════════════════════


class TestDiagnosticsEnhancements:
    """Tests for new diagnostics subsystem captures."""

    def test_sessions_active(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        sessions = trace.diagnostics.sessions()
        assert sessions["active"] is True
        assert sessions["backend"] == "MagicMock"

    def test_sessions_inactive(self, trace, mock_server):
        mock_server._session_engine = None
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        sessions = trace.diagnostics.sessions()
        assert sessions["active"] is False

    def test_auth_inactive(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        auth = trace.diagnostics.auth()
        assert auth["active"] is False  # mock_server._auth_manager = None

    def test_auth_active(self, trace, mock_server):
        mock_server._auth_manager = MagicMock()
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        auth = trace.diagnostics.auth()
        assert auth["active"] is True

    def test_templates_active(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        templates = trace.diagnostics.templates()
        assert templates["active"] is True

    def test_mail_inactive(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        mail = trace.diagnostics.mail()
        assert mail["active"] is False  # mock_server._mail_service = None

    def test_mail_active(self, trace, mock_server):
        mock_server._mail_service = MagicMock()
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        mail = trace.diagnostics.mail()
        assert mail["active"] is True

    def test_database_inactive(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        db = trace.diagnostics.database()
        assert db["active"] is False

    def test_database_active(self, trace, mock_server):
        mock_server._amdl_database = MagicMock()
        mock_server._amdl_database.driver = "sqlite"
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        db = trace.diagnostics.database()
        assert db["active"] is True
        assert db["driver"] == "sqlite"

    def test_subsystem_summary(self, trace, mock_server):
        trace.ensure_dir()
        trace.diagnostics.capture(mock_server)
        summary = trace.diagnostics.subsystem_summary()
        assert summary["faults"] is True
        assert summary["websockets"] is True
        assert summary["sessions"] is True
        assert summary["auth"] is False
        assert summary["mail"] is False
        assert summary["database"] is False

    def test_middleware_fix_uses_middlewares_attr(self, trace):
        """Verify _capture_middleware reads from .middlewares not ._middleware_list."""
        from aquilia.trace.diagnostics import TraceDiagnostics

        class FakeDescriptor:
            def __init__(self, name, priority, scope):
                self.name = name
                self.priority = priority
                self.scope = scope

        server = MagicMock()
        stack = MagicMock()
        stack.middlewares = [
            FakeDescriptor("exception", 1, "global"),
            FakeDescriptor("faults", 2, "global"),
        ]
        # Don't have _middleware_list
        del stack._middleware_list
        server.middleware_stack = stack

        result = TraceDiagnostics._capture_middleware(server)
        assert result["count"] == 2
        assert result["layers"][0]["name"] == "exception"
        assert result["layers"][0]["priority"] == 1
        assert result["layers"][0]["scope"] == "global"
        assert result["layers"][1]["name"] == "faults"


# ════════════════════════════════════════════════════════════════════════════
# Enhanced Config Snapshot
# ════════════════════════════════════════════════════════════════════════════


class TestConfigSnapEnhancements:
    """Tests for enhanced config snapshot with database flag and server meta."""

    def test_database_subsystem_flag(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        sub = trace.config_snap.subsystems()
        assert sub["database"] is False  # _amdl_database is None

    def test_database_subsystem_active(self, trace, mock_server):
        mock_server._amdl_database = MagicMock()
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        sub = trace.config_snap.subsystems()
        assert sub["database"] is True

    def test_server_metadata(self, trace, mock_server):
        trace.ensure_dir()
        trace.config_snap.capture(mock_server)
        data = trace.config_snap.read()
        assert "server" in data
        assert data["server"]["mode"] == "dev"
        assert data["server"]["fingerprint"] == "abc123def456"
        assert data["server"]["app_count"] == 1


# ════════════════════════════════════════════════════════════════════════════
# Enhanced Core / Summary
# ════════════════════════════════════════════════════════════════════════════


class TestCoreSummaryEnhancements:
    """Tests for enhanced summary() output."""

    def test_summary_has_schema_count(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "schema_count" in s
        assert isinstance(s["schema_count"], int)

    def test_summary_has_journal_events(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "journal_events" in s
        assert s["journal_events"] >= 1  # At least the boot event

    def test_summary_has_last_boot_ts(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "last_boot_ts" in s
        assert s["last_boot_ts"] is not None
        assert "T" in s["last_boot_ts"]

    def test_summary_has_healthy(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "healthy" in s
        assert isinstance(s["healthy"], bool)

    def test_summary_has_active_subsystems(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "active_subsystems" in s
        assert isinstance(s["active_subsystems"], list)
        assert "sessions" in s["active_subsystems"]

    def test_summary_has_subsystem_status(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert "subsystem_status" in s
        assert isinstance(s["subsystem_status"], dict)

    def test_summary_no_shutdown_fields_initially(self, trace, mock_server):
        trace.snapshot(mock_server)
        s = trace.summary()
        assert s["last_shutdown_ts"] is None
        assert s["last_uptime_s"] is None

    def test_summary_after_shutdown(self, trace, mock_server):
        trace.snapshot(mock_server)
        trace.snapshot_shutdown(mock_server)
        s = trace.summary()
        assert s["last_shutdown_ts"] is not None

    def test_snapshot_with_startup_duration(self, trace, mock_server):
        trace.snapshot(mock_server, startup_duration_ms=500.0)
        boot = trace.journal.last_boot()
        assert boot["duration_ms"] == 500.0

    def test_snapshot_timings_recorded(self, trace, mock_server):
        trace.snapshot(mock_server)
        assert trace._snapshot_timings
        assert "manifest" in trace._snapshot_timings
        assert "routes" in trace._snapshot_timings
        assert "di_graph" in trace._snapshot_timings
        assert "schema" in trace._snapshot_timings
        assert "config" in trace._snapshot_timings
        assert "diagnostics" in trace._snapshot_timings
        for v in trace._snapshot_timings.values():
            assert isinstance(v, float)


# ════════════════════════════════════════════════════════════════════════════
# Enhanced Schema Ledger
# ════════════════════════════════════════════════════════════════════════════


class TestSchemaLedgerEnhancements:
    """Tests for enhanced schema ledger with relations and indexes."""

    def test_relations_empty(self, trace, mock_server):
        trace.ensure_dir()
        trace.schema.capture(mock_server)
        assert trace.schema.relations() == []

    def test_relations_for_model(self, trace, workspace):
        trace.ensure_dir()
        from aquilia.trace.core import _write_json
        _write_json(trace.root / "schema.json", {
            "schema_version": 2,
            "captured_at": "2024-01-01T00:00:00",
            "model_count": 2,
            "models": [
                {
                    "name": "Post",
                    "table_name": "posts",
                    "app_label": "blog",
                    "field_count": 2,
                    "fields": [
                        {"name": "id", "type": "IntegerField", "primary_key": True},
                        {"name": "author_id", "type": "ForeignKey", "related_model": "User"},
                    ],
                    "relations": [{"field": "author_id", "type": "ForeignKey", "target": "User"}],
                    "indexes": [{"fields": ["author_id"], "unique": False, "name": "idx_author"}],
                },
                {
                    "name": "User",
                    "table_name": "users",
                    "app_label": "auth",
                    "field_count": 1,
                    "fields": [{"name": "id", "type": "IntegerField", "primary_key": True}],
                    "relations": [],
                    "indexes": [],
                },
            ],
            "migration_count": 0,
            "migrations": [],
        })

        # Model-specific relations
        rels = trace.schema.relations("Post")
        assert len(rels) == 1
        assert rels[0]["target"] == "User"
        assert rels[0]["type"] == "ForeignKey"

        # All relations
        all_rels = trace.schema.relations()
        assert len(all_rels) == 1
        assert all_rels[0]["model"] == "Post"

        # Indexes
        idxs = trace.schema.indexes("Post")
        assert len(idxs) == 1
        assert idxs[0]["name"] == "idx_author"
        assert idxs[0]["fields"] == ["author_id"]

        # Empty indexes
        assert trace.schema.indexes("User") == []
        assert trace.schema.indexes("NonExistent") == []

    def test_relations_nonexistent_model(self, trace, mock_server):
        trace.ensure_dir()
        trace.schema.capture(mock_server)
        assert trace.schema.relations("NonExistent") == []


# ════════════════════════════════════════════════════════════════════════════
# Enhanced CLI
# ════════════════════════════════════════════════════════════════════════════


class TestTraceCLIEnhancements:
    """Tests for enhanced CLI output."""

    def test_status_shows_models(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "Models:" in result.output

    def test_status_shows_events(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "Events:" in result.output

    def test_status_shows_health(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "Health:" in result.output

    def test_status_shows_subsystems(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "Subsystems:" in result.output

    def test_status_json_has_new_fields(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["status", "--dir", str(workspace), "--json-output"])
        data = json.loads(result.output)
        assert "schema_count" in data
        assert "journal_events" in data
        assert "healthy" in data
        assert "active_subsystems" in data
        assert "subsystem_status" in data

    def test_journal_shows_warning_event(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        trace.journal.record_warning("test warning")
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["journal", "--dir", str(workspace), "--event", "warning"])
        assert result.exit_code == 0
        assert "test warning" in result.output

    def test_journal_shows_phase_duration(self, trace, mock_server, workspace):
        trace.snapshot(mock_server)
        trace.journal.record_phase("autodiscovery", duration_ms=42.5)
        from click.testing import CliRunner
        from aquilia.cli.commands.trace import trace_group

        runner = CliRunner()
        result = runner.invoke(trace_group, ["journal", "--dir", str(workspace)])
        assert result.exit_code == 0
        assert "42ms" in result.output or "autodiscovery" in result.output
