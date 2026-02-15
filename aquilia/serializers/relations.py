"""
Aquilia Serializer Relations — Relational field types.

These fields handle relationships between models in serialized output:

- ``PrimaryKeyRelatedField``: Represent relation as PK value
- ``SlugRelatedField``: Represent relation as a slug/unique field value
- ``StringRelatedField``: Represent relation as ``str(obj)``

For nested representations, use a nested ``Serializer`` directly::

    class OrderSerializer(Serializer):
        product = ProductSerializer(read_only=True)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from .fields import SerializerField, empty


# ============================================================================
# Base Related Field
# ============================================================================

class RelatedField(SerializerField):
    """
    Base class for relational fields.

    Subclasses must implement:
    - ``to_representation(value)``
    - ``to_internal_value(data)`` (for writable relations)
    """

    _type_label = "related"

    def __init__(
        self,
        *,
        queryset: Any = None,
        many: bool = False,
        **kwargs,
    ):
        self.queryset = queryset
        self.many = many
        super().__init__(**kwargs)

    def get_queryset(self) -> Any:
        """Return the queryset used to look up related objects."""
        return self.queryset

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.many:
            schema["type"] = "array"
            schema["items"] = self._item_schema()
        else:
            schema.update(self._item_schema())
        return schema

    def _item_schema(self) -> Dict[str, Any]:
        """Schema for a single item (override in subclasses)."""
        return {"type": "string"}


# ============================================================================
# Concrete Related Fields
# ============================================================================

class PrimaryKeyRelatedField(RelatedField):
    """
    Represent a relation as its primary key value.

    Input:  ``{"author": 42}``
    Output: ``{"author": 42}``

    For writes, looks up the related object from the queryset.
    """

    _type_label = "pk_related"

    def __init__(self, *, pk_field: SerializerField | None = None, **kwargs):
        self.pk_field = pk_field
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> Any:
        if value is None:
            return None
        # If value is a model instance, extract pk
        if hasattr(value, "pk"):
            pk = value.pk
        elif hasattr(value, "id"):
            pk = value.id
        else:
            pk = value
        if self.pk_field:
            return self.pk_field.to_representation(pk)
        return pk

    def to_internal_value(self, data: Any) -> Any:
        if self.pk_field:
            data = self.pk_field.to_internal_value(data)
        # In write mode, just return the PK value
        # The serializer's create/update methods handle the actual lookup
        return data

    def _item_schema(self) -> Dict[str, Any]:
        if self.pk_field:
            return self.pk_field.to_schema()
        return {"type": "integer"}


class SlugRelatedField(RelatedField):
    """
    Represent a relation by a unique slug field.

    Usage::

        author = SlugRelatedField(slug_field="username", read_only=True)

    Output: ``{"author": "kai"}``
    """

    _type_label = "slug_related"

    def __init__(self, *, slug_field: str, **kwargs):
        self.slug_field = slug_field
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> Any:
        if value is None:
            return None
        return getattr(value, self.slug_field, None)

    def to_internal_value(self, data: Any) -> Any:
        # Return the slug value; create/update handles lookup
        return data

    def _item_schema(self) -> Dict[str, Any]:
        return {"type": "string"}


class StringRelatedField(RelatedField):
    """
    Represent a relation as ``str(obj)``.

    Always read-only.  Useful for human-readable representations.

    Output: ``{"author": "Kai Nakamura"}``
    """

    _type_label = "string_related"

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def _item_schema(self) -> Dict[str, Any]:
        return {"type": "string"}
