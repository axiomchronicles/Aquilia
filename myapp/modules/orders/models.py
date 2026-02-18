"""
Orders Module — Models

Aquilia ORM models for order processing and fulfillment.
"""

from aquilia.models import (
    Model,
    CharField,
    TextField,
    IntegerField,
    DecimalField,
    BooleanField,
    DateTimeField,
    JSONField,
    UUIDField,
    ForeignKey,
    Index,
    CASCADE,
    PROTECT,
    SET_NULL,
)
from aquilia.models.enums import TextChoices


class OrderStatus(TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"
    FAILED = "failed", "Failed"


class PaymentStatus(TextChoices):
    PENDING = "pending", "Pending"
    AUTHORIZED = "authorized", "Authorized"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"


class Order(Model):
    """
    Order model — full lifecycle from cart to fulfillment.

    Integrated with:
    - Aquilia Sessions (cart state via SessionState)
    - Aquilia Cache (order status caching)
    - Aquilia Mail (order confirmation emails)
    - Aquilia Faults (payment/inventory fault domains)
    """
    table = "orders"

    order_number = UUIDField(unique=True, editable=False)
    user = ForeignKey("users.User", on_delete=PROTECT, related_name="orders")
    status = CharField(max_length=20, default=OrderStatus.PENDING)
    payment_status = CharField(max_length=25, default=PaymentStatus.PENDING)
    subtotal = DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_amount = DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = DecimalField(max_digits=12, decimal_places=2, default=0)
    total = DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = CharField(max_length=3, default="USD")
    shipping_address = JSONField(default=dict)
    billing_address = JSONField(default=dict)
    notes = TextField(null=True)
    metadata = JSONField(default=dict)
    payment_method = CharField(max_length=50, null=True)
    payment_reference = CharField(max_length=255, null=True)
    shipped_at = DateTimeField(null=True)
    delivered_at = DateTimeField(null=True)
    cancelled_at = DateTimeField(null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["order_number"]),
            Index(fields=["user", "-created_at"]),
            Index(fields=["status", "-created_at"]),
            Index(fields=["payment_status"]),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    @property
    def is_paid(self) -> bool:
        return self.payment_status == PaymentStatus.CAPTURED

    @property
    def can_cancel(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED)


class OrderItem(Model):
    """Individual items within an order."""
    table = "order_items"

    order = ForeignKey("Order", on_delete=CASCADE, related_name="items")
    product = ForeignKey("products.Product", on_delete=PROTECT, related_name="order_items")
    variant_sku = CharField(max_length=50, null=True)
    product_name = CharField(max_length=255)
    quantity = IntegerField(default=1)
    unit_price = DecimalField(max_digits=10, decimal_places=2)
    total_price = DecimalField(max_digits=12, decimal_places=2)
    discount_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    metadata = JSONField(default=dict)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            Index(fields=["order"]),
            Index(fields=["product"]),
        ]


class OrderEvent(Model):
    """Audit trail for order state transitions."""
    table = "order_events"

    order = ForeignKey("Order", on_delete=CASCADE, related_name="events")
    event_type = CharField(max_length=50)
    from_status = CharField(max_length=20, null=True)
    to_status = CharField(max_length=20, null=True)
    actor_id = CharField(max_length=255, null=True)
    actor_type = CharField(max_length=20, default="system")
    details = JSONField(default=dict)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [Index(fields=["order", "-created_at"])]
