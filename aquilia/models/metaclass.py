"""
Aquilia Model Metaclass — field collection, auto-PK, Meta parsing, registration.

Separates the metaclass logic from the Model base class for cleaner architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from .fields_module import (
    AutoField,
    BigAutoField,
    Field,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
)
from .options import Options
from .manager import Manager, BaseManager

if TYPE_CHECKING:
    from .base import Model

__all__ = ["ModelMeta"]


class ModelMeta(type):
    """
    Metaclass for Aquilia models.

    Handles:
    - Field collection and ordering
    - Auto-PK injection (BigAutoField)
    - Meta class parsing → Options
    - Model registration in ModelRegistry
    - Auto-injection of default Manager
    - Reverse relation descriptors
    """

    def __new__(
        mcs,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs,
    ) -> ModelMeta:
        # Don't process the base Model class itself
        parents = [b for b in bases if isinstance(b, ModelMeta)]
        if not parents:
            return super().__new__(mcs, name, bases, namespace)

        # Extract Meta class
        meta_class = namespace.pop("Meta", None)

        # Extract `table = "..."` or `table_name = "..."` attribute
        table_attr = namespace.pop("table", None) or namespace.pop("table_name", None)

        # Collect fields from current class
        fields: Dict[str, Field] = {}
        m2m_fields: Dict[str, ManyToManyField] = {}

        # Inherit fields from parents
        for parent in bases:
            if hasattr(parent, "_fields"):
                fields.update(parent._fields)
            if hasattr(parent, "_m2m_fields"):
                m2m_fields.update(parent._m2m_fields)

        # Collect new fields
        new_fields: Dict[str, Field] = {}
        for key, value in list(namespace.items()):
            if isinstance(value, ManyToManyField):
                m2m_fields[key] = value
                new_fields[key] = value
            elif isinstance(value, Field):
                fields[key] = value
                new_fields[key] = value

        # Parse options
        opts = Options(name, meta_class, table_attr)

        # Auto-inject PK if no primary key defined (and not abstract)
        if not opts.abstract:
            has_pk = any(f.primary_key for f in fields.values())
            if not has_pk:
                pk_field = BigAutoField()
                pk_field.__set_name__(None, "id")
                fields["id"] = pk_field
                namespace["id"] = pk_field

        # Create class
        cls = super().__new__(mcs, name, bases, namespace)

        # Attach metadata
        cls._fields = fields
        cls._m2m_fields = m2m_fields
        cls._meta = opts
        cls._table_name = opts.table_name
        cls._db = None

        # Determine PK
        cls._pk_name = "id"
        cls._pk_attr = "id"
        for fname, field in fields.items():
            if field.primary_key:
                cls._pk_name = field.column_name
                cls._pk_attr = fname
                break

        # Set name on all fields
        for fname, field in new_fields.items():
            field.__set_name__(cls, fname)
            field.model = cls

        # Collect column names (excludes M2M)
        cls._column_names = [
            f.column_name for f in fields.values()
            if not isinstance(f, ManyToManyField)
        ]

        # Collect attr names (excludes M2M)
        cls._attr_names = [
            fname for fname, f in fields.items()
            if not isinstance(f, ManyToManyField)
        ]

        # Auto-inject default Manager if none declared
        if not opts.abstract and not any(
            isinstance(v, BaseManager) for v in namespace.values()
        ):
            mgr = Manager()
            mgr.__set_name__(cls, "objects")
            cls.objects = mgr

        # Register in global registry (skip abstract)
        if not opts.abstract:
            from .registry import ModelRegistry as _NewRegistry
            _NewRegistry.register(cls)

            # Signal: class_prepared (fired after model class is fully created)
            from .signals import class_prepared
            class_prepared.send_sync(sender=cls)

        return cls
