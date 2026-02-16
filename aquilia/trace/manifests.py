"""
TraceManifest — captures the Aquilary registry fingerprint and module graph.

Written to ``.aquilia/manifest.json``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceManifest"]

_FILENAME = "manifest.json"


class TraceManifest:
    """
    Persists registry fingerprint, module dependency graph, app contexts
    metadata and build timestamps into ``.aquilia/manifest.json``.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot manifest from a running ``AquiliaServer``."""
        aquilary = getattr(server, "aquilary", None)
        runtime = getattr(server, "runtime", None)

        apps: List[Dict[str, Any]] = []
        dep_graph: Dict[str, List[str]] = {}

        if aquilary is not None:
            for ctx in getattr(aquilary, "app_contexts", []):
                apps.append({
                    "name": ctx.name,
                    "version": ctx.version,
                    "load_order": ctx.load_order,
                    "controllers": list(ctx.controllers),
                    "services": list(ctx.services),
                    "models": list(ctx.models),
                    "depends_on": list(ctx.depends_on),
                    "has_startup": ctx.on_startup is not None,
                    "has_shutdown": ctx.on_shutdown is not None,
                    "middleware_count": len(ctx.middlewares),
                })

            dep_graph = getattr(aquilary, "_dependency_graph", {})

        fingerprint = getattr(aquilary, "fingerprint", "")
        mode = getattr(server, "mode", None)

        # Compute content hash (deterministic over apps payload)
        content_hash = hashlib.sha256(
            json.dumps(apps, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        data = {
            "schema_version": 1,
            "captured_at": _now_iso(),
            "fingerprint": fingerprint,
            "content_hash": content_hash,
            "mode": mode.value if mode else "unknown",
            "app_count": len(apps),
            "apps": apps,
            "dependency_graph": dep_graph,
        }

        _write_json(self.path, data)

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        """Read stored manifest."""
        return _read_json(self.path)

    def apps(self) -> List[Dict[str, Any]]:
        """Return app list from stored manifest."""
        return self.read().get("apps", [])

    def fingerprint(self) -> str:
        """Return stored fingerprint."""
        return self.read().get("fingerprint", "")

    def content_hash(self) -> str:
        return self.read().get("content_hash", "")

    def has_changed(self, server: Any) -> bool:
        """
        Check if the running server's manifest differs from the stored one.

        Useful for ``--watch`` rebuilds or deployment gating.
        """
        stored = self.read()
        stored_fp = stored.get("fingerprint", "")
        current_fp = getattr(
            getattr(server, "aquilary", None), "fingerprint", ""
        )
        return stored_fp != current_fp
