"""
Aquilia Composite Fields — group multiple primitives into one logical attribute.

Provides:
- CompositeField: Groups multiple primitive fields with serialization
- CompositePrimaryKey: Composite primary key definition
- CompositeAttribute: Read/write descriptor for composite access

Usage:
    class Address(CompositeField):
        street = CharField(max_length=200)
        city = CharField(max_length=100)
        zip_code = CharField(max_length=20)

    class Order(Model):
        shipping_address = Address(prefix="ship")
        # Creates columns: ship_street, ship_city, ship_zip_code
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from ..fields_module import Field, CharField, UNSET, FieldValidationError


__all__ = [
    "CompositeField",
    "CompositePrimaryKey",
    "CompositeAttribute",
]


class CompositeAttribute:
    """
    Descriptor that provides read/write access to a group of columns
    as a single Python dict/namedtuple.

    Usage:
        class Order(Model):
            _ship_street = CharField(max_length=200)
            _ship_city = CharField(max_length=100)

            shipping = CompositeAttribute(
                fields=["_ship_street", "_ship_city"],
                keys=["street", "city"],
            )

        order = Order(...)
        order.shipping  # → {"street": "123 Main", "city": "NYC"}
        order.shipping = {"street": "456 Oak", "city": "LA"}
    """

    def __init__(
        self,
        *,
        fields: List[str],
        keys: Optional[List[str]] = None,
    ):
        self.fields = fields
        self.keys = keys or fields

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        result = {}
        for field_name, key in zip(self.fields, self.keys):
            result[key] = getattr(instance, field_name, None)
        return result

    def __set__(self, instance, value):
        if isinstance(value, dict):
            for field_name, key in zip(self.fields, self.keys):
                if key in value:
                    setattr(instance, field_name, value[key])
        elif isinstance(value, (list, tuple)):
            for field_name, val in zip(self.fields, value):
                setattr(instance, field_name, val)


class CompositeField(Field):
    """
    Groups multiple primitive fields into one logical attribute.

    The sub-fields are stored as individual columns but accessed
    as a single dict-like attribute on the model.

    Serialization strategy: JSON (stored as TEXT column for simplicity)
    or expanded columns (one per sub-field, with a prefix).

    Args:
        schema: Dict mapping sub-field names to Field instances
        prefix: Column name prefix for expanded storage
        strategy: "json" (single TEXT column) or "expand" (multiple columns)

    Usage (JSON strategy — single column):
        coordinates = CompositeField(
            schema={"lat": FloatField(), "lng": FloatField()},
            strategy="json",
        )

    Usage (Expanded strategy — multiple columns):
        address = CompositeField(
            schema={
                "street": CharField(max_length=200),
                "city": CharField(max_length=100),
                "zip": CharField(max_length=20),
            },
            prefix="addr",
            strategy="expand",
        )
    """

    _field_type = "COMPOSITE"

    def __init__(
        self,
        *,
        schema: Dict[str, Field],
        prefix: str = "",
        strategy: str = "json",
        **kwargs,
    ):
        self.schema = schema
        self.prefix = prefix
        self.strategy = strategy
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.null:
                return None
            raise FieldValidationError(self.name, "Cannot be null")
        if not isinstance(value, dict):
            raise FieldValidationError(
                self.name, f"Expected dict, got {type(value).__name__}"
            )
        # Validate each sub-field
        cleaned = {}
        for key, field in self.schema.items():
            sub_val = value.get(key)
            cleaned[key] = field.validate(sub_val)
        return cleaned

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if self.strategy == "json":
            return json.dumps(value)
        return value

    def sql_type(self, dialect: str = "sqlite") -> str:
        if self.strategy == "json":
            if dialect == "postgresql":
                return "JSONB"
            return "TEXT"
        # For expanded strategy, this field itself doesn't produce a column
        return "TEXT"

    def deconstruct(self) -> Dict[str, Any]:
        d = super().deconstruct()
        d["strategy"] = self.strategy
        d["prefix"] = self.prefix
        d["schema"] = {
            k: v.deconstruct() for k, v in self.schema.items()
        }
        return d


class CompositePrimaryKey:
    """
    Declares a composite primary key across multiple fields.

    This is not a Field itself — it's a Meta-level declaration.

    Usage:
        class OrderItem(Model):
            order_id = IntegerField()
            product_id = IntegerField()

            class Meta:
                primary_key = CompositePrimaryKey(fields=["order_id", "product_id"])

    The metaclass reads this from Meta and generates:
        PRIMARY KEY ("order_id", "product_id")
    as a table-level constraint instead of a column-level PK.
    """

    def __init__(self, *, fields: List[str]):
        if len(fields) < 2:
            raise ValueError("CompositePrimaryKey requires at least 2 fields")
        self.fields = fields

    def sql(self) -> str:
        """Generate the SQL PRIMARY KEY constraint."""
        cols = ", ".join(f'"{f}"' for f in self.fields)
        return f"PRIMARY KEY ({cols})"

    def deconstruct(self) -> Dict[str, Any]:
        return {"type": "CompositePrimaryKey", "fields": self.fields}
