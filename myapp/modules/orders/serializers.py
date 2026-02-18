"""
Orders Module — Serializers

Nested serializers with cart validation,
order lifecycle projections, and DI-aware defaults.
"""

from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    CharField,
    IntegerField,
    DecimalField,
    BooleanField,
    DateTimeField,
    JSONField,
    UUIDField,
    PrimaryKeyRelatedField,
    CurrentUserDefault,
    InjectDefault,
)

from .models import Order, OrderItem, OrderEvent


# ─── Cart Serializers ─────────────────────────────────────────

class CartItemSerializer(Serializer):
    """Validates individual cart items from session state."""
    product_id = IntegerField(required=True)
    variant_sku = CharField(required=False, allow_null=True, default=None)
    quantity = IntegerField(required=True, min_value=1, max_value=100)

    def validate_quantity(self, value: int) -> int:
        if value < 1:
            raise ValueError("Quantity must be at least 1")
        return value


class CartSerializer(Serializer):
    """Full cart for checkout validation."""
    items = ListSerializer(child=CartItemSerializer())
    shipping_address = JSONField(required=True)
    billing_address = JSONField(required=False, default=None)
    payment_method = CharField(required=True)
    notes = CharField(required=False, allow_blank=True, max_length=1000, default="")
    coupon_code = CharField(required=False, allow_blank=True, default="")

    def validate_items(self, items: list) -> list:
        if not items:
            raise ValueError("Cart cannot be empty")
        return items

    def validate(self, data: dict) -> dict:
        if not data.get("billing_address"):
            data["billing_address"] = data["shipping_address"]
        return data


# ─── Order Item Serializers ───────────────────────────────────

class OrderItemSerializer(ModelSerializer):
    """Read-only serializer for order items."""
    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "variant_sku",
            "product_name", "quantity",
            "unit_price", "total_price", "discount_amount",
            "metadata", "created_at",
        ]
        read_only_fields = [
            "id", "product_name", "unit_price",
            "total_price", "created_at",
        ]


# ─── Order Event Serializers ─────────────────────────────────

class OrderEventSerializer(ModelSerializer):
    """Audit trail entries for order history."""
    class Meta:
        model = OrderEvent
        fields = [
            "id", "event_type", "from_status", "to_status",
            "actor_id", "actor_type", "details", "created_at",
        ]
        read_only_fields = [
            "id", "event_type", "from_status", "to_status",
            "actor_id", "actor_type", "details", "created_at",
        ]


# ─── Order Serializers ───────────────────────────────────────

class OrderListSerializer(ModelSerializer):
    """Compact order view for listings."""
    item_count = IntegerField(read_only=True, default=0)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "status", "payment_status",
            "total", "currency", "item_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order_number", "status", "payment_status",
            "total", "currency", "item_count",
            "created_at", "updated_at",
        ]


class OrderDetailSerializer(ModelSerializer):
    """Full order detail with nested items and event history."""
    items = ListSerializer(child=OrderItemSerializer())
    events = ListSerializer(child=OrderEventSerializer())
    can_cancel = BooleanField(read_only=True)
    is_paid = BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "user",
            "status", "payment_status",
            "subtotal", "tax_amount", "shipping_amount",
            "discount_amount", "total", "currency",
            "shipping_address", "billing_address",
            "notes", "metadata",
            "payment_method", "payment_reference",
            "can_cancel", "is_paid",
            "items", "events",
            "shipped_at", "delivered_at", "cancelled_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order_number", "user",
            "subtotal", "tax_amount", "shipping_amount",
            "discount_amount", "total",
            "payment_reference",
            "shipped_at", "delivered_at", "cancelled_at",
            "created_at", "updated_at",
        ]


class OrderStatusUpdateSerializer(Serializer):
    """Admin serializer for order status transitions."""
    status = CharField(required=True)
    notes = CharField(required=False, allow_blank=True, default="")

    def validate_status(self, value: str) -> str:
        from .models import OrderStatus
        valid = [s.value for s in OrderStatus]
        if value not in valid:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid)}")
        return value
