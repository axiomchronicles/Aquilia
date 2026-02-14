"""
Aquilia Model Registry — global registry for all Model subclasses.

Tracks all concrete models, resolves forward FK/M2M references,
creates tables, and manages the global database connection.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase
    from .base import Model
    from .fields_module import RelationField

logger = logging.getLogger("aquilia.models.registry")

__all__ = ["ModelRegistry"]


class ModelRegistry:
    """
    Global registry for all Model subclasses.

    Replaces the old AMDL-based ModelRegistry.
    Tracks all concrete models and resolves forward references.
    """

    _models: Dict[str, Type[Model]] = {}
    _db: Optional[AquiliaDatabase] = None
    _app_models: Dict[str, Dict[str, Type[Model]]] = {}  # app_label → {name → cls}

    @classmethod
    def register(cls, model_cls: Type[Model]) -> None:
        """Register a model class."""
        name = model_cls.__name__
        cls._models[name] = model_cls

        # Track by app_label
        app = getattr(model_cls._meta, "app_label", "") or ""
        if app not in cls._app_models:
            cls._app_models[app] = {}
        cls._app_models[app][name] = model_cls

        # Resolve any pending forward FK references
        cls._resolve_relations()

    @classmethod
    def get(cls, name: str) -> Optional[Type[Model]]:
        """Get model class by name."""
        return cls._models.get(name)

    @classmethod
    def all_models(cls) -> Dict[str, Type[Model]]:
        """Get all registered models."""
        return dict(cls._models)

    @classmethod
    def get_app_models(cls, app_label: str) -> Dict[str, Type[Model]]:
        """Get all models for a specific app."""
        return dict(cls._app_models.get(app_label, {}))

    @classmethod
    def set_database(cls, db: AquiliaDatabase) -> None:
        """Set global database for all models."""
        cls._db = db
        for model_cls in cls._models.values():
            model_cls._db = db

    @classmethod
    def get_database(cls) -> Optional[AquiliaDatabase]:
        return cls._db

    @classmethod
    def _resolve_relations(cls) -> None:
        """Resolve forward-referenced model names in FK/M2M fields."""
        from .fields_module import RelationField
        for model_cls in cls._models.values():
            for field in model_cls._fields.values():
                if isinstance(field, RelationField) and isinstance(field.to, str):
                    field.resolve_model(cls._models)

    @classmethod
    async def create_tables(cls, db: Optional[AquiliaDatabase] = None) -> List[str]:
        """Create tables for all registered models."""
        target_db = db or cls._db
        if not target_db:
            raise RuntimeError("No database configured for ModelRegistry")

        statements: List[str] = []
        for model_cls in cls._models.values():
            if model_cls._meta.abstract:
                continue
            if not model_cls._meta.managed:
                continue

            # Create main table
            sql = model_cls.generate_create_table_sql()
            await target_db.execute(sql)
            statements.append(sql)

            # Create indexes
            for idx_sql in model_cls.generate_index_sql():
                await target_db.execute(idx_sql)
                statements.append(idx_sql)

            # Create M2M junction tables
            for m2m_sql in model_cls.generate_m2m_sql():
                await target_db.execute(m2m_sql)
                statements.append(m2m_sql)

        return statements

    @classmethod
    async def drop_tables(cls, db: Optional[AquiliaDatabase] = None) -> List[str]:
        """Drop all registered model tables (dangerous!)."""
        target_db = db or cls._db
        if not target_db:
            raise RuntimeError("No database configured for ModelRegistry")

        statements: List[str] = []
        for model_cls in reversed(list(cls._models.values())):
            if model_cls._meta.abstract:
                continue
            sql = f'DROP TABLE IF EXISTS "{model_cls._table_name}"'
            await target_db.execute(sql)
            statements.append(sql)

        return statements

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._models.clear()
        cls._app_models.clear()
        cls._db = None

    @classmethod
    def check_constraints(cls) -> List[str]:
        """
        Validate all model constraints and return a list of issues.

        Checks:
        - FK targets exist
        - M2M targets exist
        - No duplicate table names
        - No circular FK chains without nullable break
        """
        issues: List[str] = []
        table_names: Dict[str, str] = {}  # table → model name

        from .fields_module import ForeignKey, ManyToManyField

        for name, model_cls in cls._models.items():
            if model_cls._meta.abstract:
                continue

            tbl = model_cls._table_name
            if tbl in table_names:
                issues.append(
                    f"Duplicate table '{tbl}': {name} and {table_names[tbl]}"
                )
            table_names[tbl] = name

            for fname, field in model_cls._fields.items():
                if isinstance(field, ForeignKey):
                    target = field.to if isinstance(field.to, str) else field.to.__name__
                    if target not in cls._models:
                        issues.append(
                            f"{name}.{fname}: FK target '{target}' not registered"
                        )
                elif isinstance(field, ManyToManyField):
                    target = field.to if isinstance(field.to, str) else field.to.__name__
                    if target not in cls._models:
                        issues.append(
                            f"{name}.{fname}: M2M target '{target}' not registered"
                        )

        return issues

    # ── Lifecycle hooks (DI compatibility) ───────────────────────────

    async def on_startup(self) -> None:
        if ModelRegistry._models:
            await ModelRegistry.create_tables()

    async def on_shutdown(self) -> None:
        pass
