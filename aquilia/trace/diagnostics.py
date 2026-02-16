"""
TraceDiagnostics — runtime health, performance and error budget snapshot.

Written to ``.aquilia/diagnostics.json``.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceDiagnostics"]

_FILENAME = "diagnostics.json"


class TraceDiagnostics:
    """
    Captures runtime diagnostics: health status, fault budget,
    middleware stack info, WebSocket stats, effect providers,
    artifact index, session/auth/template/mail status,
    and memory usage.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot diagnostics from a running ``AquiliaServer``."""
        data: Dict[str, Any] = {
            "schema_version": 2,
            "captured_at": _now_iso(),
        }

        # Fault engine budget
        data["faults"] = self._capture_faults(server)

        # Middleware stack
        data["middleware"] = self._capture_middleware(server)

        # WebSocket stats
        data["websockets"] = self._capture_websockets(server)

        # Effect providers
        data["effects"] = self._capture_effects(server)

        # Artifact index
        data["artifacts"] = self._capture_artifacts(server)

        # Session engine
        data["sessions"] = self._capture_sessions(server)

        # Auth manager
        data["auth"] = self._capture_auth(server)

        # Template engine
        data["templates"] = self._capture_templates(server)

        # Mail service
        data["mail"] = self._capture_mail(server)

        # Database
        data["database"] = self._capture_database(server)

        # Process health
        data["process"] = self._capture_process()

        _write_json(self.path, data)

    # ── Capture helpers ──────────────────────────────────────────────

    @staticmethod
    def _capture_faults(server: Any) -> Dict[str, Any]:
        engine = getattr(server, "fault_engine", None)
        if engine is None:
            return {"active": False}
        budget = {}
        try:
            budget = {
                "total_faults": getattr(engine, "total_faults", 0),
                "active_circuit_breakers": len(getattr(engine, "_circuit_breakers", {})),
                "error_budget_remaining": getattr(engine, "error_budget_remaining", None),
            }
        except Exception:
            pass
        return {"active": True, **budget}

    @staticmethod
    def _capture_middleware(server: Any) -> Dict[str, Any]:
        stack = getattr(server, "middleware_stack", None)
        if stack is None:
            return {"count": 0, "layers": []}
        layers: List[Dict[str, Any]] = []
        try:
            # MiddlewareStack stores descriptors in .middlewares
            mw_list = getattr(stack, "middlewares", None)
            if mw_list is None:
                # Fallback for older versions
                mw_list = getattr(stack, "_middleware_list", [])
            for mw in mw_list:
                name = getattr(mw, "name", None) or type(getattr(mw, "middleware", mw)).__name__
                priority = getattr(mw, "priority", None)
                scope = getattr(mw, "scope", "global")
                layers.append({"name": str(name), "priority": priority, "scope": scope})
        except Exception:
            pass
        return {"count": len(layers), "layers": layers}

    @staticmethod
    def _capture_websockets(server: Any) -> Dict[str, Any]:
        sockets = getattr(server, "aquila_sockets", None)
        if sockets is None:
            return {"active": False}
        router = getattr(sockets, "router", None)
        handler_count = 0
        if router is not None:
            handler_count = len(getattr(router, "_handlers", {}))
        return {
            "active": True,
            "handler_count": handler_count,
            "active_connections": len(getattr(sockets, "_connections", {})),
        }

    @staticmethod
    def _capture_effects(server: Any) -> Dict[str, Any]:
        registry = getattr(server, "_effect_registry", None)
        if registry is None:
            return {"active": False, "provider_count": 0}
        providers = getattr(registry, "providers", {})
        return {
            "active": True,
            "provider_count": len(providers),
            "provider_names": list(providers.keys()) if isinstance(providers, dict) else [],
        }

    @staticmethod
    def _capture_artifacts(server: Any) -> Dict[str, Any]:
        """Index artifacts on disk (if artifact store is wired)."""
        try:
            from ..artifacts.store import ArtifactStore
            store = ArtifactStore()
            return {
                "count": store.count(),
                "names": list(store.names()) if hasattr(store, "names") else [],
            }
        except Exception:
            return {"count": 0}

    @staticmethod
    def _capture_sessions(server: Any) -> Dict[str, Any]:
        """Capture session engine status."""
        engine = getattr(server, "_session_engine", None)
        if engine is None:
            return {"active": False}
        return {
            "active": True,
            "backend": type(engine).__name__,
        }

    @staticmethod
    def _capture_auth(server: Any) -> Dict[str, Any]:
        """Capture auth manager status."""
        manager = getattr(server, "_auth_manager", None)
        if manager is None:
            return {"active": False}
        return {
            "active": True,
            "backend": type(manager).__name__,
        }

    @staticmethod
    def _capture_templates(server: Any) -> Dict[str, Any]:
        """Capture template engine status."""
        engine = getattr(server, "template_engine", None)
        if engine is None:
            return {"active": False}
        search_paths: List[str] = []
        try:
            for attr in ("search_paths", "_search_paths", "dirs", "template_dirs"):
                paths = getattr(engine, attr, None)
                if paths is not None:
                    search_paths = [str(p) for p in paths]
                    break
        except Exception:
            pass
        return {
            "active": True,
            "engine": type(engine).__name__,
            "search_paths": search_paths,
        }

    @staticmethod
    def _capture_mail(server: Any) -> Dict[str, Any]:
        """Capture mail service status."""
        mail = getattr(server, "_mail_service", None)
        if mail is None:
            return {"active": False}
        return {
            "active": True,
            "service": type(mail).__name__,
        }

    @staticmethod
    def _capture_database(server: Any) -> Dict[str, Any]:
        """Capture database connection status."""
        db = getattr(server, "_amdl_database", None)
        if db is None:
            return {"active": False}
        return {
            "active": True,
            "driver": getattr(db, "driver", "unknown"),
        }

    @staticmethod
    def _capture_process() -> Dict[str, Any]:
        """Basic process health metrics."""
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "pid": os.getpid(),
            "python_version": sys.version.split()[0],
            "max_rss_mb": round(usage.ru_maxrss / (1024 * 1024), 2) if sys.platform == "linux" else round(usage.ru_maxrss / (1024 * 1024), 2),
            "user_time_s": round(usage.ru_utime, 3),
            "system_time_s": round(usage.ru_stime, 3),
        }

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        return _read_json(self.path)

    def faults(self) -> Dict[str, Any]:
        return self.read().get("faults", {})

    def middleware(self) -> Dict[str, Any]:
        return self.read().get("middleware", {})

    def websockets(self) -> Dict[str, Any]:
        return self.read().get("websockets", {})

    def effects(self) -> Dict[str, Any]:
        return self.read().get("effects", {})

    def sessions(self) -> Dict[str, Any]:
        return self.read().get("sessions", {})

    def auth(self) -> Dict[str, Any]:
        return self.read().get("auth", {})

    def templates(self) -> Dict[str, Any]:
        return self.read().get("templates", {})

    def mail(self) -> Dict[str, Any]:
        return self.read().get("mail", {})

    def database(self) -> Dict[str, Any]:
        return self.read().get("database", {})

    def process(self) -> Dict[str, Any]:
        return self.read().get("process", {})

    def is_healthy(self) -> bool:
        """Simple health check based on stored diagnostics."""
        data = self.read()
        if not data:
            return False
        faults = data.get("faults", {})
        # Healthy if fault engine is active and no breakers tripped
        return faults.get("active", False) and faults.get("active_circuit_breakers", 0) == 0

    def subsystem_summary(self) -> Dict[str, bool]:
        """Return active/inactive status for each subsystem."""
        data = self.read()
        if not data:
            return {}
        return {
            key: data.get(key, {}).get("active", False)
            for key in ("faults", "websockets", "effects", "sessions", "auth", "templates", "mail", "database")
        }
