"""
Orders Module — Services

Full order lifecycle with session-based cart,
inventory reservation, mail notifications, and cache integration.
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from aquilia.di import service, Inject
from aquilia.cache import CacheService, cached, invalidate
from aquilia.mail import EmailMessage
from aquilia.mail.service import MailService
from aquilia.models import Q, F, atomic

from .models import Order, OrderItem, OrderEvent, OrderStatus, PaymentStatus
from .faults import (
    OrderNotFoundFault,
    EmptyCartFault,
    InvalidOrderTransitionFault,
    PaymentFailedFault,
    OrderCancellationFault,
    OrderLimitExceededFault,
)

from ..products.services import ProductService
from ..users.services import UserService


# ── Valid order status transitions ────────────────────────────
VALID_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED, OrderStatus.FAILED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
    OrderStatus.FAILED: {OrderStatus.PENDING},
}


@service(scope="app")
class OrderService:
    """
    Order lifecycle management.

    Integrates:
    - Aquilia Sessions (cart stored in SessionState)
    - Aquilia Cache (order caching, cart invalidation)
    - Aquilia Mail (order confirmation, shipping updates)
    - Aquilia ORM (transactions via atomic())
    - Aquilia Faults (structured order errors)
    - Aquilia DI (service injection)
    """

    def __init__(
        self,
        products: ProductService = Inject(ProductService),
        users: UserService = Inject(UserService),
        cache: CacheService = Inject(CacheService),
        mail: MailService = Inject(MailService),
    ):
        self.products = products
        self.users = users
        self.cache = cache
        self.mail = mail

    # ── Cart Operations (Session-backed) ─────────────────────

    async def get_cart(self, session_state: dict) -> list:
        """Retrieve cart from Aquilia SessionState."""
        return session_state.get("cart", [])

    async def add_to_cart(
        self, session_state: dict, product_id: int, quantity: int, variant_sku: str = None
    ) -> list:
        """Add item to session-backed cart."""
        cart = session_state.get("cart", [])

        # check if item already in cart
        for item in cart:
            if item["product_id"] == product_id and item.get("variant_sku") == variant_sku:
                item["quantity"] += quantity
                session_state["cart"] = cart
                return cart

        cart.append({
            "product_id": product_id,
            "variant_sku": variant_sku,
            "quantity": quantity,
        })
        session_state["cart"] = cart
        return cart

    async def remove_from_cart(
        self, session_state: dict, product_id: int, variant_sku: str = None
    ) -> list:
        cart = session_state.get("cart", [])
        cart = [
            item for item in cart
            if not (item["product_id"] == product_id and item.get("variant_sku") == variant_sku)
        ]
        session_state["cart"] = cart
        return cart

    async def clear_cart(self, session_state: dict) -> None:
        session_state["cart"] = []

    # ── Order Lifecycle ──────────────────────────────────────

    @invalidate(namespace="orders")
    async def place_order(self, user_id: int, cart_data: dict) -> Order:
        """
        Create order from validated cart data.
        Uses Aquilia ORM atomic() for transactional safety.
        """
        items = cart_data["items"]
        if not items:
            raise EmptyCartFault()

        user = await self.users.get_by_id(user_id)

        async with atomic():
            subtotal = Decimal("0")
            order_items = []

            for cart_item in items:
                product = await self.products.get_by_id(cart_item["product_id"])
                quantity = cart_item["quantity"]

                # reserve inventory
                await self.products.reserve_stock(product.id, quantity)

                unit_price = Decimal(str(product.price))
                item_total = unit_price * quantity
                subtotal += item_total

                order_items.append({
                    "product_id": product.id,
                    "variant_sku": cart_item.get("variant_sku"),
                    "product_name": product.name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": item_total,
                })

            # calculate totals
            tax_rate = Decimal("0.08")
            tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"))
            shipping = Decimal("9.99") if subtotal < Decimal("100") else Decimal("0")
            total = subtotal + tax_amount + shipping

            # create order
            order = Order(
                order_number=str(uuid.uuid4()),
                user_id=user_id,
                status=OrderStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_amount=shipping,
                total=total,
                shipping_address=cart_data.get("shipping_address", {}),
                billing_address=cart_data.get("billing_address", {}),
                payment_method=cart_data.get("payment_method", ""),
                notes=cart_data.get("notes", ""),
            )
            await order.save()

            # create order items
            for item_data in order_items:
                order_item = OrderItem(order_id=order.id, **item_data)
                await order_item.save()

            # log creation event
            await self._log_event(
                order.id, "order_created", None, OrderStatus.PENDING,
                actor_id=str(user_id), actor_type="customer",
            )

        # send confirmation email (non-blocking)
        await self._send_order_email(user, order, "confirmation")

        return order

    @invalidate(namespace="orders")
    async def update_status(
        self,
        order_id: int,
        new_status: str,
        actor_id: str = "system",
        actor_type: str = "system",
        notes: str = "",
    ) -> Order:
        """Transition order status with validation."""
        order = await self.get_by_id(order_id)
        old_status = order.status

        if new_status not in VALID_TRANSITIONS.get(old_status, set()):
            raise InvalidOrderTransitionFault(old_status, new_status)

        order.status = new_status

        # set timestamps based on status
        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.SHIPPED:
            order.shipped_at = now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
            # release inventory
            items = await OrderItem.objects.filter(order_id=order.id).all()
            for item in items:
                await self.products.release_stock(item.product_id, item.quantity)

        await order.save()

        await self._log_event(
            order.id, "status_changed", old_status, new_status,
            actor_id=actor_id, actor_type=actor_type,
            details={"notes": notes} if notes else {},
        )

        return order

    # ── Queries ──────────────────────────────────────────────

    @cached(ttl=120, namespace="orders")
    async def get_by_id(self, order_id: int) -> Order:
        order = await Order.objects.filter(id=order_id).first()
        if not order:
            raise OrderNotFoundFault(str(order_id))
        return order

    @cached(ttl=120, namespace="orders")
    async def get_by_order_number(self, order_number: str) -> Order:
        order = await Order.objects.filter(order_number=order_number).first()
        if not order:
            raise OrderNotFoundFault(order_number)
        return order

    @cached(ttl=60, namespace="orders:list")
    async def list_orders(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        qs = Order.objects.get_queryset()
        if user_id:
            qs = qs.filter(user_id=user_id)
        if status:
            qs = qs.filter(status=status)

        total = await qs.count()
        offset = (page - 1) * page_size
        orders = await qs.order_by("-created_at")[offset : offset + page_size].all()

        return {
            "items": orders,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    async def get_order_items(self, order_id: int) -> list:
        return await OrderItem.objects.filter(order_id=order_id).all()

    async def get_order_events(self, order_id: int) -> list:
        return await OrderEvent.objects.filter(order_id=order_id).order_by("-created_at").all()

    # ── Internals ────────────────────────────────────────────

    async def _log_event(
        self,
        order_id: int,
        event_type: str,
        from_status: Optional[str],
        to_status: Optional[str],
        actor_id: str = "system",
        actor_type: str = "system",
        details: dict = None,
    ) -> None:
        event = OrderEvent(
            order_id=order_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor_id,
            actor_type=actor_type,
            details=details or {},
        )
        await event.save()

    async def _send_order_email(self, user, order: Order, email_type: str) -> None:
        """Send order-related emails via Aquilia MailService."""
        try:
            subjects = {
                "confirmation": f"Order Confirmed — #{order.order_number}",
                "shipped": f"Your Order Has Shipped — #{order.order_number}",
                "delivered": f"Order Delivered — #{order.order_number}",
                "cancelled": f"Order Cancelled — #{order.order_number}",
            }
            msg = EmailMessage(
                subject=subjects.get(email_type, "Order Update"),
                to=[user.email],
                body=f"Hello {user.full_name or user.username},\n\n"
                     f"Your order #{order.order_number} status: {order.status}\n"
                     f"Total: {order.currency} {order.total}\n\n"
                     f"— Nexus",
            )
            await self.mail.asend_mail(msg)
        except Exception:
            pass
