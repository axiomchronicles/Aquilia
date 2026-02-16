"""
TraceSchemaLedger — model registry and migration state snapshot.

Written to ``.aquilia/schema.json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import _write_json, _read_json, _now_iso

__all__ = ["TraceSchemaLedger"]

_FILENAME = "schema.json"


class TraceSchemaLedger:
    """
    Captures the model registry state: registered models, field schemas,
    relations, migration history and table metadata.
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root / _FILENAME

    # ── Write ────────────────────────────────────────────────────────

    def capture(self, server: Any) -> None:
        """Snapshot model registry from a running ``AquiliaServer``."""
        models: List[Dict[str, Any]] = []

        try:
            from ..models.registry import ModelRegistry

            for name, model_cls in ModelRegistry.all_models().items():
                meta = getattr(model_cls, "_meta", None)
                fields_info: List[Dict[str, Any]] = []
                relations: List[Dict[str, Any]] = []

                if meta is not None:
                    for fname, fobj in getattr(meta, "fields", {}).items():
                        field_entry: Dict[str, Any] = {
                            "name": fname,
                            "type": type(fobj).__name__,
                            "primary_key": getattr(fobj, "primary_key", False),
                            "nullable": getattr(fobj, "null", False),
                            "has_default": getattr(fobj, "default", None) is not None,
                            "unique": getattr(fobj, "unique", False),
                        }

                        # Track FK / relations
                        related_model = getattr(fobj, "related_model", None) or getattr(fobj, "to", None)
                        if related_model is not None:
                            rel_name = related_model if isinstance(related_model, str) else getattr(related_model, "__name__", str(related_model))
                            field_entry["related_model"] = rel_name
                            on_delete = getattr(fobj, "on_delete", None)
                            if on_delete is not None:
                                field_entry["on_delete"] = str(on_delete)
                            relations.append({
                                "field": fname,
                                "type": type(fobj).__name__,
                                "target": rel_name,
                            })

                        fields_info.append(field_entry)

                    # Check for indexes
                    indexes: List[Dict[str, Any]] = []
                    for idx in getattr(meta, "indexes", []):
                        indexes.append({
                            "fields": list(getattr(idx, "fields", [])),
                            "unique": getattr(idx, "unique", False),
                            "name": getattr(idx, "name", ""),
                        })

                models.append({
                    "name": name,
                    "table_name": getattr(meta, "table_name", name.lower()),
                    "app_label": getattr(meta, "app_label", ""),
                    "field_count": len(fields_info),
                    "fields": fields_info,
                    "relations": relations,
                    "indexes": indexes if meta is not None else [],
                })
        except Exception:
            pass

        # Migration state
        migrations: List[Dict[str, Any]] = []
        try:
            db = getattr(server, "_amdl_database", None)
            if db is not None and hasattr(db, "applied_migrations"):
                for m in db.applied_migrations:
                    migrations.append({
                        "name": getattr(m, "name", str(m)),
                        "applied_at": getattr(m, "applied_at", None),
                    })
        except Exception:
            pass

        data = {
            "schema_version": 2,
            "captured_at": _now_iso(),
            "model_count": len(models),
            "models": models,
            "migration_count": len(migrations),
            "migrations": migrations,
        }
        _write_json(self.path, data)

    # ── Read-back ────────────────────────────────────────────────────

    def read(self) -> Dict[str, Any]:
        return _read_json(self.path)

    def models(self) -> List[Dict[str, Any]]:
        return self.read().get("models", [])

    def model(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific model's schema info."""
        for m in self.models():
            if m.get("name") == name:
                return m
        return None

    def model_names(self) -> List[str]:
        return [m["name"] for m in self.models()]

    def count(self) -> int:
        return self.read().get("model_count", 0)

    def fields(self, model_name: str) -> List[Dict[str, Any]]:
        m = self.model(model_name)
        return m.get("fields", []) if m else []

    def relations(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relations, optionally for a specific model."""
        if model_name:
            m = self.model(model_name)
            return m.get("relations", []) if m else []
        # All relations across all models
        result: List[Dict[str, Any]] = []
        for m in self.models():
            for r in m.get("relations", []):
                result.append({"model": m["name"], **r})
        return result

    def indexes(self, model_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a specific model."""
        m = self.model(model_name)
        return m.get("indexes", []) if m else []
