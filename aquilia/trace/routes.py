"""
TraceRouteMap — compiled route table snapshot.

Written to ``.aquilia/routes.json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceRouteMap"]

_FILENAME = "routes.json"


class TraceRouteMap:
    """
    Captures the full compiled route table from ``ControllerRouter``
    including HTTP method, path, controller class, handler name,
    specificity score and pipeline information.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot routes from a running ``AquiliaServer``."""
        router = getattr(server, "controller_router", None)
        routes_raw: List[Dict[str, Any]] = []

        if router is not None:
            # ControllerRouter.get_routes() returns list of dicts
            try:
                routes_raw = router.get_routes()
            except Exception:
                routes_raw = []

        # Enrich with per-method counts
        method_counts: Dict[str, int] = {}
        for r in routes_raw:
            m = r.get("method", "GET")
            method_counts[m] = method_counts.get(m, 0) + 1

        # Build controller index
        controllers: Dict[str, List[str]] = {}
        for r in routes_raw:
            ctrl = r.get("controller", "")
            if ctrl not in controllers:
                controllers[ctrl] = []
            controllers[ctrl].append(r.get("path", "/"))

        data = {
            "schema_version": 1,
            "captured_at": _now_iso(),
            "total": len(routes_raw),
            "method_counts": method_counts,
            "controllers": controllers,
            "routes": routes_raw,
        }
        _write_json(self.path, data)

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        return _read_json(self.path)

    def count(self) -> int:
        return self.read().get("total", 0)

    def routes(self) -> List[Dict[str, Any]]:
        return self.read().get("routes", [])

    def by_method(self, method: str) -> List[Dict[str, Any]]:
        """Filter stored routes by HTTP method."""
        return [r for r in self.routes() if r.get("method") == method]

    def by_controller(self, name: str) -> List[Dict[str, Any]]:
        """Filter stored routes by controller class name."""
        return [r for r in self.routes() if r.get("controller") == name]

    def diff(self, other_path: Path) -> Dict[str, Any]:
        """
        Diff current stored routes against another ``routes.json``.

        Returns ``{"added": [...], "removed": [...], "changed": [...]}``.
        """
        current = {
            f"{r['method']} {r['path']}": r for r in self.routes()
        }
        other = _read_json(other_path)
        other_routes = {
            f"{r['method']} {r['path']}": r
            for r in other.get("routes", [])
        }

        added = [v for k, v in current.items() if k not in other_routes]
        removed = [v for k, v in other_routes.items() if k not in current]

        changed = []
        for key in current.keys() & other_routes.keys():
            cur, old = current[key], other_routes[key]
            if cur.get("handler") != old.get("handler") or cur.get("specificity") != old.get("specificity"):
                changed.append({"current": cur, "previous": old})

        return {"added": added, "removed": removed, "changed": changed}
