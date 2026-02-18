"""
Orders Module — Controllers

Order lifecycle management with session-based cart,
checkout flow, and admin order management.

Integrates:
- Aquilia Sessions (cart state in SessionState)
- Aquilia Controller/Response/RequestCtx
- Aquilia Serializers
- Aquilia Faults
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET, POST, PUT, DELETE, PATCH
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import OrderService
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderStatusUpdateSerializer,
    OrderItemSerializer,
    OrderEventSerializer,
)
from ..users.faults import InsufficientPermissionsFault


class CartController(Controller):
    """
    Session-backed shopping cart.
    Cart state lives in Aquilia SessionState — no database hit for cart ops.
    """
    prefix = "/cart"
    tags = ["Cart"]

    @GET("/")
    async def get_cart(self, ctx: RequestCtx) -> Response:
        """Get current cart contents from session."""
        order_service = await ctx.container.resolve_async(OrderService)
        cart = await order_service.get_cart(ctx.session)
        return Response.json({"items": cart, "count": len(cart)})

    @POST("/items")
    async def add_item(self, ctx: RequestCtx) -> Response:
        """Add product to cart."""
        serializer = await CartItemSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        order_service = await ctx.container.resolve_async(OrderService)
        cart = await order_service.add_to_cart(
            ctx.session,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"],
            variant_sku=serializer.validated_data.get("variant_sku"),
        )
        return Response.json({"items": cart, "count": len(cart)})

    @DELETE("/items/«product_id:int»")
    async def remove_item(self, ctx: RequestCtx, product_id: int) -> Response:
        """Remove product from cart."""
        variant_sku = ctx.request.query_params.get("variant_sku")
        order_service = await ctx.container.resolve_async(OrderService)
        cart = await order_service.remove_from_cart(
            ctx.session, product_id, variant_sku
        )
        return Response.json({"items": cart, "count": len(cart)})

    @DELETE("/")
    async def clear_cart(self, ctx: RequestCtx) -> Response:
        """Clear entire cart."""
        order_service = await ctx.container.resolve_async(OrderService)
        await order_service.clear_cart(ctx.session)
        return Response.json({"items": [], "count": 0})


class OrderController(Controller):
    """
    Order management — checkout, order history, status tracking.
    """
    prefix = "/orders"
    tags = ["Orders"]

    @POST("/checkout")
    async def checkout(self, ctx: RequestCtx) -> Response:
        """
        Convert cart to order.
        Validates cart, reserves inventory, processes payment,
        sends confirmation via Aquilia Mail.
        """
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await CartSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        order_service = await ctx.container.resolve_async(OrderService)
        order = await order_service.place_order(
            user_id=int(ctx.identity.id),
            cart_data=serializer.validated_data,
        )

        # clear cart after successful order
        await order_service.clear_cart(ctx.session)

        result = OrderDetailSerializer(instance=order)
        return Response.json(result.data, status=201)

    @GET("/")
    async def list_orders(self, ctx: RequestCtx) -> Response:
        """List orders for the authenticated user (or all for admin)."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        params = ctx.request.query_params
        order_service = await ctx.container.resolve_async(OrderService)

        is_admin = "admin" in (ctx.identity.attributes.get("roles", []) or [])
        user_id = None if is_admin and params.get("all") == "true" else int(ctx.identity.id)

        result = await order_service.list_orders(
            user_id=user_id,
            status=params.get("status"),
            page=int(params.get("page", 1)),
            page_size=int(params.get("page_size", 20)),
        )

        serializer = OrderListSerializer.many(instance=result["items"])
        return Response.json({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "pages": result["pages"],
        })

    @GET("/«order_id:int»")
    async def get_order(self, ctx: RequestCtx, order_id: int) -> Response:
        """Get full order detail with items and event history."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        order_service = await ctx.container.resolve_async(OrderService)
        order = await order_service.get_by_id(order_id)

        # verify ownership or admin
        is_admin = "admin" in (ctx.identity.attributes.get("roles", []) or [])
        if order.user_id != int(ctx.identity.id) and not is_admin:
            return Response.json({"error": "Forbidden"}, status=403)

        serializer = OrderDetailSerializer(instance=order)
        return Response.json(serializer.data)

    @GET("/number/«order_number»")
    async def get_by_number(self, ctx: RequestCtx, order_number: str) -> Response:
        """Look up order by order number."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        order_service = await ctx.container.resolve_async(OrderService)
        order = await order_service.get_by_order_number(order_number)
        serializer = OrderDetailSerializer(instance=order)
        return Response.json(serializer.data)

    @POST("/«order_id:int»/cancel")
    async def cancel_order(self, ctx: RequestCtx, order_id: int) -> Response:
        """Cancel an order (if eligible)."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        order_service = await ctx.container.resolve_async(OrderService)
        order = await order_service.update_status(
            order_id,
            "cancelled",
            actor_id=ctx.identity.id,
            actor_type="customer",
        )
        serializer = OrderDetailSerializer(instance=order)
        return Response.json(serializer.data)

    @GET("/«order_id:int»/events")
    async def get_order_events(self, ctx: RequestCtx, order_id: int) -> Response:
        """Get order event audit trail."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        order_service = await ctx.container.resolve_async(OrderService)
        events = await order_service.get_order_events(order_id)
        serializer = OrderEventSerializer.many(instance=events)
        return Response.json(serializer.data)

    # ── Admin Status Management ──────────────────────────────

    @PATCH("/«order_id:int»/status")
    async def update_status(self, ctx: RequestCtx, order_id: int) -> Response:
        """Admin: update order status with transition validation."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        serializer = await OrderStatusUpdateSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        order_service = await ctx.container.resolve_async(OrderService)
        order = await order_service.update_status(
            order_id,
            new_status=serializer.validated_data["status"],
            actor_id=ctx.identity.id,
            actor_type="admin",
            notes=serializer.validated_data.get("notes", ""),
        )
        result = OrderDetailSerializer(instance=order)
        return Response.json(result.data)
