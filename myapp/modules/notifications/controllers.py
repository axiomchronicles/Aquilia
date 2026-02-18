"""
Notifications Module — Controllers

REST API for notification history + WebSocket real-time push.
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET, POST, PATCH
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import NotificationService


class NotificationController(Controller):
    """
    Notification REST endpoints for history and management.
    Real-time delivery handled by WebSocket controllers (sockets.py).
    """
    prefix = "/notifications"
    tags = ["Notifications"]

    @GET("/")
    async def list_notifications(self, ctx: RequestCtx) -> Response:
        """List notifications for the authenticated user."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        params = ctx.request.query_params
        service = await ctx.container.resolve_async(NotificationService)
        notifications = await service.get_notifications(
            user_id=int(ctx.identity.id),
            unread_only=params.get("unread_only") == "true",
            limit=int(params.get("limit", 50)),
        )
        return Response.json({"items": notifications, "count": len(notifications)})

    @GET("/unread-count")
    async def unread_count(self, ctx: RequestCtx) -> Response:
        """Get count of unread notifications."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        service = await ctx.container.resolve_async(NotificationService)
        count = await service.get_unread_count(int(ctx.identity.id))
        return Response.json({"unread_count": count})

    @PATCH("/«notification_id»/read")
    async def mark_read(self, ctx: RequestCtx, notification_id: str) -> Response:
        """Mark a single notification as read."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        service = await ctx.container.resolve_async(NotificationService)
        await service.mark_read(int(ctx.identity.id), notification_id)
        return Response.json({"message": "Marked as read"})

    @POST("/mark-all-read")
    async def mark_all_read(self, ctx: RequestCtx) -> Response:
        """Mark all notifications as read."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        service = await ctx.container.resolve_async(NotificationService)
        count = await service.mark_all_read(int(ctx.identity.id))
        return Response.json({"marked": count})
