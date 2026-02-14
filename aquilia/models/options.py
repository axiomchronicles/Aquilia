"""
Aquilia Model Options — parsed from inner Meta class.

Contains the Options class which stores model metadata like
table_name, ordering, indexes, constraints, abstract, etc.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .fields_module import Index, UniqueConstraint


__all__ = ["Options"]


class Options:
    """
    Parsed model options from inner Meta class.

    Attributes:
        table_name: Database table name
        ordering: Default query ordering
        indexes: Composite indexes
        constraints: Unique constraints
        abstract: Whether model is abstract (no table)
        verbose_name: Human-readable model name
        verbose_name_plural: Human-readable plural
        app_label: Owning module name
        unique_together: Legacy: list of field tuples
        select_on_save: Re-SELECT after save to get DB-computed fields
        managed: Whether migrations manage this table (default True)
        default_permissions: Default permissions to create
        permissions: Extra permissions
        db_tablespace: Tablespace for the table (PostgreSQL)
        get_latest_by: Field(s) for latest() shortcut
        order_with_respect_to: FK field for ordering
        default_related_name: Default related_name template
        required_db_features: Backend features required
        required_db_vendor: Backend vendor required (e.g., "postgresql")
    """

    __slots__ = (
        "table_name",
        "ordering",
        "indexes",
        "constraints",
        "abstract",
        "verbose_name",
        "verbose_name_plural",
        "app_label",
        "unique_together",
        "select_on_save",
        "managed",
        "default_permissions",
        "permissions",
        "db_tablespace",
        "get_latest_by",
        "order_with_respect_to",
        "default_related_name",
        "required_db_features",
        "required_db_vendor",
        "proxy",
        "_model_cls",
    )

    def __init__(
        self,
        model_name: str,
        meta: Optional[type] = None,
        table_attr: Optional[str] = None,
    ):
        self.table_name = table_attr or (
            getattr(meta, "table", None) or getattr(meta, "table_name", None)
            if meta else None
        ) or model_name.lower()
        self.ordering: List[str] = getattr(meta, "ordering", []) if meta else []
        self.indexes: list = getattr(meta, "indexes", []) if meta else []
        self.constraints: list = getattr(meta, "constraints", []) if meta else []
        self.abstract: bool = getattr(meta, "abstract", False) if meta else False
        self.verbose_name: str = getattr(meta, "verbose_name", model_name) if meta else model_name
        self.verbose_name_plural: str = getattr(
            meta, "verbose_name_plural", f"{self.verbose_name}s"
        ) if meta else f"{model_name}s"
        self.app_label: str = getattr(meta, "app_label", "") if meta else ""
        self.unique_together: List[Tuple[str, ...]] = (
            getattr(meta, "unique_together", []) if meta else []
        )
        # Enhanced options
        self.select_on_save: bool = getattr(meta, "select_on_save", False) if meta else False
        self.managed: bool = getattr(meta, "managed", True) if meta else True
        self.default_permissions: Tuple[str, ...] = getattr(
            meta, "default_permissions", ("add", "change", "delete", "view")
        ) if meta else ("add", "change", "delete", "view")
        self.permissions: List[Tuple[str, str]] = getattr(meta, "permissions", []) if meta else []
        self.db_tablespace: str = getattr(meta, "db_tablespace", "") if meta else ""
        self.get_latest_by: Optional[str] = getattr(meta, "get_latest_by", None) if meta else None
        self.order_with_respect_to: Optional[str] = (
            getattr(meta, "order_with_respect_to", None) if meta else None
        )
        self.default_related_name: Optional[str] = (
            getattr(meta, "default_related_name", None) if meta else None
        )
        self.required_db_features: List[str] = (
            getattr(meta, "required_db_features", []) if meta else []
        )
        self.required_db_vendor: Optional[str] = (
            getattr(meta, "required_db_vendor", None) if meta else None
        )
        self.proxy: bool = getattr(meta, "proxy", False) if meta else False
        self._model_cls = None

    @property
    def label(self) -> str:
        """Return app_label.ModelName style label."""
        if self.app_label:
            return f"{self.app_label}.{self.verbose_name}"
        return self.verbose_name

    @property
    def label_lower(self) -> str:
        """Return app_label.model_name style label (lowercase)."""
        return self.label.lower()

    def __repr__(self) -> str:
        return f"<Options: {self.table_name}>"
