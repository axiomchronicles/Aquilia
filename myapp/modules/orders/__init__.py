"""
Orders Module — Order processing, cart, and fulfillment.

Components:
- Models: Order, OrderItem, OrderEvent
- Services: OrderService (cart + checkout + lifecycle)
- Controllers: OrderController, CartController
- Serializers: Cart, Order, and status update serializers
- Faults: Order-specific error handling
"""

from .models import Order, OrderItem, OrderEvent, OrderStatus, PaymentStatus
from .services import OrderService
from .controllers import OrderController, CartController
from .faults import (
    OrderNotFoundFault,
    EmptyCartFault,
    InvalidOrderTransitionFault,
    PaymentFailedFault,
)

__all__ = [
    "Order", "OrderItem", "OrderEvent", "OrderStatus", "PaymentStatus",
    "OrderService",
    "OrderController", "CartController",
    "OrderNotFoundFault", "EmptyCartFault",
    "InvalidOrderTransitionFault", "PaymentFailedFault",
]
