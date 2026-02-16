"""
TraceLifecycleJournal — append-only lifecycle event journal.

Written to ``.aquilia/journal.jsonl`` (JSON Lines format).
Each line is a self-contained JSON object for easy streaming and ``tail -f``.
"""

from __future__ import annotations

import json
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _now_iso

__all__ = ["TraceLifecycleJournal"]

_FILENAME = "journal.jsonl"


class TraceLifecycleJournal:
    """
    Append-only lifecycle event journal.

    Events include boot, shutdown, phase transitions, warnings, errors,
    and custom application events.  Unlike other trace files, the journal
    is **append-only** (JSON Lines) so that history is preserved across
    restarts until ``clean()`` is called.
    """

    __slots__ = ("_root", "_boot_mono",)

    def __init__(self, root: Path) -> None:
        self._root = root
        self._boot_mono: Optional[float] = None  # monotonic ts for uptime

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def _append(self, event: Dict[str, Any]) -> None:
        """Append a single event (JSON line)."""
        event.setdefault("ts", _now_iso())
        event.setdefault("pid", os.getpid())
        with open(self.path, "a") as fp:
            fp.write(json.dumps(event, default=str) + "\n")

    def record_boot(self, server: Any, *, duration_ms: Optional[float] = None) -> None:
        """Record a server boot event with optional startup duration."""
        aquilary = getattr(server, "aquilary", None)
        mode = getattr(server, "mode", None)
        app_count = len(getattr(aquilary, "app_contexts", []))

        routes = getattr(server, "controller_router", None)
        route_count = 0
        if routes is not None:
            try:
                route_count = len(routes.get_routes())
            except Exception:
                pass

        di_total = 0
        runtime = getattr(server, "runtime", None)
        if runtime is not None:
            for c in getattr(runtime, "di_containers", {}).values():
                di_total += len(getattr(c, "_providers", {}))

        # Capture boot monotonic time for uptime calculation
        self._boot_mono = _time.monotonic()

        entry: Dict[str, Any] = {
            "event": "boot",
            "mode": mode.value if mode else "unknown",
            "fingerprint": getattr(aquilary, "fingerprint", ""),
            "app_count": app_count,
            "route_count": route_count,
            "di_providers": di_total,
        }
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        self._append(entry)

    def record_shutdown(self, server: Any) -> None:
        """Record a server shutdown event with uptime if available."""
        entry: Dict[str, Any] = {
            "event": "shutdown",
            "mode": getattr(getattr(server, "mode", None), "value", "unknown"),
        }
        # Compute uptime from boot monotonic timestamp
        if self._boot_mono is not None:
            entry["uptime_s"] = round(_time.monotonic() - self._boot_mono, 3)
        self._append(entry)

    def record_phase(
        self,
        phase: str,
        *,
        app_name: str = "",
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Record a lifecycle phase transition with optional timing."""
        entry: Dict[str, Any] = {"event": "phase", "phase": phase}
        if app_name:
            entry["app"] = app_name
        if error:
            entry["error"] = error
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if detail:
            entry["detail"] = detail
        self._append(entry)

    def record_custom(self, name: str, **data: Any) -> None:
        """Record a custom application event."""
        self._append({"event": "custom", "name": name, **data})

    def record_error(self, error: str, *, context: str = "") -> None:
        """Record an error event."""
        self._append({"event": "error", "error": error, "context": context})

    def record_warning(self, warning: str, *, context: str = "") -> None:
        """Record a warning event."""
        self._append({"event": "warning", "warning": warning, "context": context})

    # ── Read-back ────────────────────────────────────────────────────

    def events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read all (or last *limit*) events."""
        if not self.path.exists():
            return []
        lines = self.path.read_text().strip().splitlines()
        parsed = []
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if limit is not None:
            parsed = parsed[-limit:]
        return parsed

    def boots(self) -> List[Dict[str, Any]]:
        """Return only boot events."""
        return [e for e in self.events() if e.get("event") == "boot"]

    def errors(self) -> List[Dict[str, Any]]:
        """Return only error events."""
        return [e for e in self.events() if e.get("event") == "error"]

    def warnings(self) -> List[Dict[str, Any]]:
        """Return only warning events."""
        return [e for e in self.events() if e.get("event") == "warning"]

    def phases(self) -> List[Dict[str, Any]]:
        """Return only phase events."""
        return [e for e in self.events() if e.get("event") == "phase"]

    def last_boot(self) -> Optional[Dict[str, Any]]:
        boots = self.boots()
        return boots[-1] if boots else None

    def last_shutdown(self) -> Optional[Dict[str, Any]]:
        """Return the most recent shutdown event."""
        shutdowns = [e for e in self.events() if e.get("event") == "shutdown"]
        return shutdowns[-1] if shutdowns else None

    def count(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for _ in self.path.open())

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return last *n* events (like ``tail``)."""
        return self.events(limit=n)

    def clear(self) -> None:
        """Clear journal file."""
        if self.path.exists():
            self.path.unlink()
