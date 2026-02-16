"""
TraceDIGraph — DI provider registry and scope tree snapshot.

Written to ``.aquilia/di_graph.json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceDIGraph"]

_FILENAME = "di_graph.json"


class TraceDIGraph:
    """
    Captures DI container hierarchy: per-app provider lists, scope tree,
    token index, and total registration count.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot DI containers from a running ``AquiliaServer``."""
        runtime = getattr(server, "runtime", None)
        containers: Dict[str, Any] = {}

        if runtime is not None:
            for app_name, container in getattr(runtime, "di_containers", {}).items():
                providers_list: List[Dict[str, Any]] = []
                for key, provider in getattr(container, "_providers", {}).items():
                    meta = getattr(provider, "meta", None)
                    if meta is not None:
                        providers_list.append(meta.to_dict())
                    else:
                        providers_list.append({
                            "key": str(key),
                            "type": type(provider).__name__,
                        })

                containers[app_name] = {
                    "scope": getattr(container, "_scope", "unknown"),
                    "provider_count": len(providers_list),
                    "providers": providers_list,
                    "has_parent": getattr(container, "_parent", None) is not None,
                    "cached_count": len(getattr(container, "_cache", {})),
                }

        # Build token index for quick lookups
        token_index: Dict[str, str] = {}  # token → app_name
        for app_name, info in containers.items():
            for p in info.get("providers", []):
                token = p.get("token", p.get("key", ""))
                if token:
                    token_index[token] = app_name

        total = sum(c["provider_count"] for c in containers.values())

        data = {
            "schema_version": 1,
            "captured_at": _now_iso(),
            "total_providers": total,
            "container_count": len(containers),
            "containers": containers,
            "token_index": token_index,
        }
        _write_json(self.path, data)

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        return _read_json(self.path)

    def count(self) -> int:
        return self.read().get("total_providers", 0)

    def providers(self, app_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get providers, optionally filtered by app."""
        data = self.read()
        if app_name:
            return data.get("containers", {}).get(app_name, {}).get("providers", [])
        # All providers across all containers
        result: List[Dict[str, Any]] = []
        for info in data.get("containers", {}).values():
            result.extend(info.get("providers", []))
        return result

    def find_token(self, token: str) -> Optional[str]:
        """Find which app owns a token."""
        return self.read().get("token_index", {}).get(token)

    def by_scope(self, scope: str) -> List[Dict[str, Any]]:
        """Filter providers by scope (singleton, app, request, transient)."""
        return [p for p in self.providers() if p.get("scope") == scope]
