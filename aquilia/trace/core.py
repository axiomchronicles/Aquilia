"""
AquiliaTrace core — the central tracker that owns the ``.aquilia/`` directory.

Directory layout::

    .aquilia/
    ├── manifest.json          # Build manifest (fingerprint, modules, deps)
    ├── routes.json            # Compiled route table
    ├── di_graph.json          # DI provider tree
    ├── schema.json            # Model registry + migration ledger
    ├── journal.jsonl          # Lifecycle event journal (append-only)
    ├── config.json            # Resolved config snapshot (secrets redacted)
    ├── diagnostics.json       # Health / perf / error budget
    ├── lock.json              # Trace lock (PID, boot time)
    └── .gitignore             # Auto-generated
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("aquilia.trace")

_GITIGNORE_CONTENT = """\
# Aquilia trace directory — safe to delete, regenerated on boot.
*
!.gitignore
"""

_LOCK_VERSION = 1


class AquiliaTrace:
    """
    Central tracker that manages the ``.aquilia/`` directory.

    All sub-trackers are lazily created and write individual JSON files.
    The trace directory is created on first write and can be safely
    deleted at any time — Aquilia regenerates it on next ``startup()``.
    """

    __slots__ = (
        "_root",
        "_manifest",
        "_routes",
        "_di_graph",
        "_schema",
        "_journal",
        "_config_snap",
        "_diagnostics",
        "_boot_ts",
        "_boot_mono",
        "_snapshot_timings",
    )

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        ws = workspace_root or Path.cwd()
        self._root = ws / ".aquilia"
        self._boot_ts = datetime.now(timezone.utc).isoformat()
        self._boot_mono: Optional[float] = None

        # Lazy sub-trackers
        self._manifest: Optional["TraceManifest"] = None
        self._routes: Optional["TraceRouteMap"] = None
        self._di_graph: Optional["TraceDIGraph"] = None
        self._schema: Optional["TraceSchemaLedger"] = None
        self._journal: Optional["TraceLifecycleJournal"] = None
        self._config_snap: Optional["TraceConfigSnapshot"] = None
        self._diagnostics: Optional["TraceDiagnostics"] = None
        self._snapshot_timings: Dict[str, float] = {}

    # ── Directory management ─────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    def ensure_dir(self) -> Path:
        """Create ``.aquilia/`` with a ``.gitignore`` if it doesn't exist."""
        self._root.mkdir(parents=True, exist_ok=True)
        gitignore = self._root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_CONTENT)
        return self._root

    def exists(self) -> bool:
        return self._root.is_dir()

    def clean(self) -> int:
        """Delete all trace files (not the directory itself). Returns count."""
        if not self._root.is_dir():
            return 0
        count = 0
        for f in self._root.iterdir():
            if f.name == ".gitignore":
                continue
            if f.is_file():
                f.unlink()
                count += 1
        return count

    # ── Lock ─────────────────────────────────────────────────────────

    def acquire_lock(self) -> None:
        """Write a lock file with PID and boot timestamp."""
        self.ensure_dir()
        lock = {
            "version": _LOCK_VERSION,
            "pid": os.getpid(),
            "boot_ts": self._boot_ts,
            "hostname": _safe_hostname(),
        }
        _write_json(self._root / "lock.json", lock)

    def release_lock(self) -> None:
        lock_path = self._root / "lock.json"
        if lock_path.exists():
            lock_path.unlink()

    def is_locked(self) -> bool:
        lock_path = self._root / "lock.json"
        if not lock_path.exists():
            return False
        try:
            lock = json.loads(lock_path.read_text())
            pid = lock.get("pid", -1)
            # Check if process is still running
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                # Stale lock
                return False
        except Exception:
            return False

    # ── Sub-trackers (lazy) ──────────────────────────────────────────

    @property
    def manifest(self) -> "TraceManifest":
        if self._manifest is None:
            from .manifests import TraceManifest
            self._manifest = TraceManifest(self._root)
        return self._manifest

    @property
    def routes(self) -> "TraceRouteMap":
        if self._routes is None:
            from .routes import TraceRouteMap
            self._routes = TraceRouteMap(self._root)
        return self._routes

    @property
    def di_graph(self) -> "TraceDIGraph":
        if self._di_graph is None:
            from .di_graph import TraceDIGraph
            self._di_graph = TraceDIGraph(self._root)
        return self._di_graph

    @property
    def schema(self) -> "TraceSchemaLedger":
        if self._schema is None:
            from .schema import TraceSchemaLedger
            self._schema = TraceSchemaLedger(self._root)
        return self._schema

    @property
    def journal(self) -> "TraceLifecycleJournal":
        if self._journal is None:
            from .journal import TraceLifecycleJournal
            self._journal = TraceLifecycleJournal(self._root)
        return self._journal

    @property
    def config_snap(self) -> "TraceConfigSnapshot":
        if self._config_snap is None:
            from .config_snap import TraceConfigSnapshot
            self._config_snap = TraceConfigSnapshot(self._root)
        return self._config_snap

    @property
    def diagnostics(self) -> "TraceDiagnostics":
        if self._diagnostics is None:
            from .diagnostics import TraceDiagnostics
            self._diagnostics = TraceDiagnostics(self._root)
        return self._diagnostics

    # ── Full snapshot ────────────────────────────────────────────────

    def snapshot(self, server: Any, *, startup_duration_ms: Optional[float] = None) -> None:
        """
        Take a full snapshot from a running ``AquiliaServer``.

        Called automatically during ``startup()`` and ``shutdown()``.

        Args:
            server: The running AquiliaServer instance.
            startup_duration_ms: Total startup duration in ms (if measured externally).
        """
        self.ensure_dir()
        self.acquire_lock()
        self._boot_mono = time.monotonic()
        self._snapshot_timings = {}

        try:
            self._timed_capture("manifest", lambda: self.manifest.capture(server))
            self._timed_capture("routes", lambda: self.routes.capture(server))
            self._timed_capture("di_graph", lambda: self.di_graph.capture(server))
            self._timed_capture("schema", lambda: self.schema.capture(server))
            self._timed_capture("config", lambda: self.config_snap.capture(server))
            self._timed_capture("diagnostics", lambda: self.diagnostics.capture(server))
            self.journal.record_boot(server, duration_ms=startup_duration_ms)
        except Exception as exc:
            logger.warning("Trace snapshot failed (non-fatal): %s", exc)

    def snapshot_shutdown(self, server: Any) -> None:
        """Record shutdown state and release the trace lock."""
        try:
            self.journal.record_shutdown(server)
            self.diagnostics.capture(server)
        except Exception as exc:
            logger.warning("Trace shutdown snapshot failed (non-fatal): %s", exc)
        finally:
            self.release_lock()

    def _timed_capture(self, name: str, fn: Any) -> None:
        """Run a capture function and record its duration in ms."""
        t0 = time.monotonic()
        try:
            fn()
        finally:
            self._snapshot_timings[name] = round((time.monotonic() - t0) * 1000, 2)

    # ── Read-back ────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Return a comprehensive summary of the trace directory."""
        if not self.exists():
            return {"exists": False}

        files = [f.name for f in self._root.iterdir() if f.is_file() and f.name != ".gitignore"]

        # Journal stats
        journal_count = self.journal.count()
        last_boot = self.journal.last_boot()
        last_shutdown = self.journal.last_shutdown()

        # Schema stats
        schema_count = self.schema.count()

        # Diagnostics health
        healthy = self.diagnostics.is_healthy()
        subsystem_status = self.diagnostics.subsystem_summary()

        # Config active subsystems
        active_subs = self.config_snap.active_subsystems()

        return {
            "exists": True,
            "root": str(self._root),
            "files": sorted(files),
            "locked": self.is_locked(),
            "manifest": self.manifest.read(),
            "route_count": self.routes.count(),
            "provider_count": self.di_graph.count(),
            "schema_count": schema_count,
            "journal_events": journal_count,
            "last_boot_ts": last_boot.get("ts") if last_boot else None,
            "last_boot_duration_ms": last_boot.get("duration_ms") if last_boot else None,
            "last_shutdown_ts": last_shutdown.get("ts") if last_shutdown else None,
            "last_uptime_s": last_shutdown.get("uptime_s") if last_shutdown else None,
            "healthy": healthy,
            "active_subsystems": active_subs,
            "subsystem_status": subsystem_status,
            "snapshot_timings_ms": dict(self._snapshot_timings) if self._snapshot_timings else None,
        }


# ── Helpers ──────────────────────────────────────────────────────────────


def _write_json(path: Path, data: Any) -> None:
    """Atomic JSON write (write-to-tmp then rename)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


def _read_json(path: Path) -> Any:
    """Read JSON, return empty dict on failure."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _safe_hostname() -> str:
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
