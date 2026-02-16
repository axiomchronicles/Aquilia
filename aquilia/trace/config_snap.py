"""
TraceConfigSnapshot — resolved configuration at boot with secrets redacted.

Written to ``.aquilia/config.json``.
"""

from __future__ import annotations

import os
import platform
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceConfigSnapshot"]

_FILENAME = "config.json"

# Patterns for secret redaction
_SECRET_KEYS = re.compile(
    r"(password|secret|token|api_key|apikey|private|credential|auth)",
    re.IGNORECASE,
)
_REDACTED = "***REDACTED***"


def _redact(data: Any, depth: int = 0) -> Any:
    """
    Recursively redact sensitive values in config dictionaries.

    Keys matching common secret patterns (password, token, api_key, etc.)
    have their values replaced with ``***REDACTED***``.
    """
    if depth > 20:
        return "..."
    if isinstance(data, dict):
        return {
            k: (_REDACTED if _SECRET_KEYS.search(k) else _redact(v, depth + 1))
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [_redact(item, depth + 1) for item in data]
    return data


class TraceConfigSnapshot:
    """
    Captures the resolved ``ConfigLoader`` state at boot time.

    Secrets are always redacted before writing to disk.
    Includes Python & OS environment metadata for debugging.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot config from a running ``AquiliaServer``."""
        config = getattr(server, "config", None)
        raw: Dict[str, Any] = {}

        if config is not None:
            try:
                raw = config.to_dict()
            except Exception:
                raw = {}

        redacted = _redact(raw)

        # Environment metadata (non-sensitive)
        env = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "pid": os.getpid(),
            "debug": getattr(server, "_is_debug", lambda: False)(),
        }

        # Subsystem status flags
        subsystems = {
            "sessions": getattr(server, "_session_engine", None) is not None,
            "auth": getattr(server, "_auth_manager", None) is not None,
            "templates": hasattr(server, "template_engine"),
            "mail": getattr(server, "_mail_service", None) is not None,
            "websockets": hasattr(server, "aquila_sockets"),
            "faults": hasattr(server, "fault_engine"),
            "effects": getattr(server, "_effect_registry", None) is not None,
            "database": getattr(server, "_amdl_database", None) is not None,
        }

        # Server metadata
        mode = getattr(server, "mode", None)
        server_meta: Dict[str, Any] = {
            "mode": mode.value if mode else "unknown",
        }
        aquilary = getattr(server, "aquilary", None)
        if aquilary is not None:
            server_meta["fingerprint"] = getattr(aquilary, "fingerprint", "")
            server_meta["app_count"] = len(getattr(aquilary, "app_contexts", []))

        data = {
            "schema_version": 2,
            "captured_at": _now_iso(),
            "config": redacted,
            "environment": env,
            "subsystems": subsystems,
            "server": server_meta,
        }
        _write_json(self.path, data)

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        return _read_json(self.path)

    def config(self) -> Dict[str, Any]:
        return self.read().get("config", {})

    def environment(self) -> Dict[str, Any]:
        return self.read().get("environment", {})

    def subsystems(self) -> Dict[str, bool]:
        return self.read().get("subsystems", {})

    def is_debug(self) -> bool:
        return self.environment().get("debug", False)

    def active_subsystems(self) -> List[str]:
        """Return names of enabled subsystems."""
        return [k for k, v in self.subsystems().items() if v]
