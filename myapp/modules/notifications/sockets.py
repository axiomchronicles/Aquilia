"""
Notifications Module — WebSocket Controllers

Real-time notification push, live chat rooms, and presence tracking.

Integrates:
- Aquilia SocketController (@Socket, @OnConnect, @OnDisconnect, @Event, @AckEvent)
- Aquilia WebSocket rooms (publish_room, broadcast)
- Aquilia DI (service injection in socket handlers)
- Aquilia Cache (online presence tracking)
- Aquilia Auth (identity verification on connect)
"""

from aquilia.sockets import SocketController
from aquilia.sockets.decorators import (
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AckEvent,
)
from aquilia.di import Inject
from aquilia.cache import CacheService

from .services import NotificationService
from .faults import (
    WebSocketConnectionFault,
    ChannelPermissionFault,
    BroadcastFault,
)


@Socket("/ws/notifications")
class NotificationSocket(SocketController):
    """
    Real-time notification delivery via WebSocket.

    Sends push notifications to connected clients.
    Tracks online presence via Aquilia Cache.
    """

    @OnConnect()
    async def on_connect(self, sid: str, environ: dict) -> bool:
        """
        Authenticate WebSocket connection.
        Verifies identity and joins user-specific room.
        """
        # extract user identity from session/token
        user_id = environ.get("user_id")
        if not user_id:
            return False  # reject unauthenticated connections

        # join user-specific notification room
        await self.join_room(sid, f"user:{user_id}")
        await self.join_room(sid, "global")

        # track online presence
        cache = await self.container.resolve_async(CacheService)
        await cache.set(
            f"presence:{user_id}",
            {"sid": sid, "status": "online"},
            ttl=3600,
            namespace="presence",
        )

        # send welcome acknowledgment
        await self.emit(sid, "connected", {
            "message": "Connected to notification channel",
            "user_id": user_id,
        })

        return True

    @OnDisconnect()
    async def on_disconnect(self, sid: str) -> None:
        """Clean up presence on disconnect."""
        user_id = self.get_user_id(sid)
        if user_id:
            cache = await self.container.resolve_async(CacheService)
            await cache.delete(f"presence:{user_id}", namespace="presence")
            await self.leave_room(sid, f"user:{user_id}")
            await self.leave_room(sid, "global")

    @Event("subscribe")
    async def subscribe_channel(self, sid: str, data: dict) -> None:
        """Subscribe to a notification channel (e.g., orders, products)."""
        channel = data.get("channel", "")
        if channel:
            await self.join_room(sid, f"channel:{channel}")
            await self.emit(sid, "subscribed", {"channel": channel})

    @Event("unsubscribe")
    async def unsubscribe_channel(self, sid: str, data: dict) -> None:
        """Unsubscribe from a notification channel."""
        channel = data.get("channel", "")
        if channel:
            await self.leave_room(sid, f"channel:{channel}")
            await self.emit(sid, "unsubscribed", {"channel": channel})

    @AckEvent("mark_read")
    async def mark_notification_read(self, sid: str, data: dict) -> dict:
        """Mark notification as read with acknowledgment."""
        user_id = self.get_user_id(sid)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        notification_id = data.get("notification_id", "")
        service = await self.container.resolve_async(NotificationService)
        await service.mark_read(int(user_id), notification_id)

        return {"success": True, "notification_id": notification_id}

    @Event("ping")
    async def ping(self, sid: str, data: dict) -> None:
        """Heartbeat ping for connection health."""
        await self.emit(sid, "pong", {"timestamp": data.get("timestamp")})

    # ── Push helpers (called from services) ──────────────────

    async def push_to_user(self, user_id: int, event: str, data: dict) -> None:
        """Push a notification to a specific user's room."""
        await self.publish_room(f"user:{user_id}", event, data)

    async def push_to_channel(self, channel: str, event: str, data: dict) -> None:
        """Broadcast to all subscribers of a channel."""
        await self.publish_room(f"channel:{channel}", event, data)

    async def push_global(self, event: str, data: dict) -> None:
        """Broadcast to all connected clients."""
        await self.broadcast(event, data)


@Socket("/ws/chat")
class ChatSocket(SocketController):
    """
    Real-time chat rooms with presence.

    Supports:
    - Room-based messaging (order support, vendor chat, etc.)
    - Typing indicators
    - Message delivery receipts
    - User presence in rooms
    """

    @OnConnect()
    async def on_connect(self, sid: str, environ: dict) -> bool:
        user_id = environ.get("user_id")
        if not user_id:
            return False

        await self.emit(sid, "connected", {
            "message": "Connected to chat",
            "user_id": user_id,
        })
        return True

    @OnDisconnect()
    async def on_disconnect(self, sid: str) -> None:
        """Notify rooms of user departure."""
        user_id = self.get_user_id(sid)
        rooms = self.get_rooms(sid)
        for room in rooms:
            await self.publish_room(room, "user_left", {
                "user_id": user_id,
                "room": room,
            })

    @Event("join_room")
    async def join_chat_room(self, sid: str, data: dict) -> None:
        """Join a chat room."""
        room = data.get("room", "")
        if not room:
            return

        await self.join_room(sid, room)
        user_id = self.get_user_id(sid)

        # notify room members
        await self.publish_room(room, "user_joined", {
            "user_id": user_id,
            "room": room,
        })

    @Event("leave_room")
    async def leave_chat_room(self, sid: str, data: dict) -> None:
        """Leave a chat room."""
        room = data.get("room", "")
        if not room:
            return

        user_id = self.get_user_id(sid)
        await self.leave_room(sid, room)

        await self.publish_room(room, "user_left", {
            "user_id": user_id,
            "room": room,
        })

    @AckEvent("send_message")
    async def send_message(self, sid: str, data: dict) -> dict:
        """
        Send a message to a chat room.
        Returns delivery receipt via acknowledgment.
        """
        room = data.get("room", "")
        message = data.get("message", "")
        user_id = self.get_user_id(sid)

        if not room or not message:
            return {"success": False, "error": "Missing room or message"}

        import time
        msg_id = f"msg_{user_id}_{int(time.time() * 1000)}"

        # broadcast to room
        await self.publish_room(room, "new_message", {
            "id": msg_id,
            "room": room,
            "user_id": user_id,
            "message": message,
            "timestamp": time.time(),
        })

        return {"success": True, "message_id": msg_id}

    @Event("typing")
    async def typing_indicator(self, sid: str, data: dict) -> None:
        """Broadcast typing indicator to room."""
        room = data.get("room", "")
        user_id = self.get_user_id(sid)
        is_typing = data.get("is_typing", True)

        if room:
            await self.publish_room(room, "typing", {
                "user_id": user_id,
                "room": room,
                "is_typing": is_typing,
            })

    @Event("read_receipt")
    async def read_receipt(self, sid: str, data: dict) -> None:
        """Send read receipt for messages."""
        room = data.get("room", "")
        message_id = data.get("message_id", "")
        user_id = self.get_user_id(sid)

        if room and message_id:
            await self.publish_room(room, "message_read", {
                "user_id": user_id,
                "message_id": message_id,
                "room": room,
            })


@Socket("/ws/orders")
class OrderTrackingSocket(SocketController):
    """
    Real-time order status updates.
    Customers track their orders live; admins see all order activity.
    """

    @OnConnect()
    async def on_connect(self, sid: str, environ: dict) -> bool:
        user_id = environ.get("user_id")
        if not user_id:
            return False

        # all users join their personal order channel
        await self.join_room(sid, f"orders:user:{user_id}")

        # admins also join the global order feed
        roles = environ.get("roles", [])
        if "admin" in roles:
            await self.join_room(sid, "orders:admin")

        await self.emit(sid, "connected", {"message": "Order tracking active"})
        return True

    @OnDisconnect()
    async def on_disconnect(self, sid: str) -> None:
        pass

    @Event("track_order")
    async def track_order(self, sid: str, data: dict) -> None:
        """Subscribe to updates for a specific order."""
        order_id = data.get("order_id")
        if order_id:
            await self.join_room(sid, f"order:{order_id}")
            await self.emit(sid, "tracking", {
                "order_id": order_id,
                "message": "Now tracking this order",
            })

    @Event("untrack_order")
    async def untrack_order(self, sid: str, data: dict) -> None:
        order_id = data.get("order_id")
        if order_id:
            await self.leave_room(sid, f"order:{order_id}")

    # ── Push helpers (called from OrderService) ──────────────

    async def push_order_update(
        self, order_id: int, user_id: int, status: str, details: dict = None
    ) -> None:
        """Push order status update to relevant subscribers."""
        payload = {
            "order_id": order_id,
            "status": status,
            "details": details or {},
        }
        # notify the order owner
        await self.publish_room(f"orders:user:{user_id}", "order_updated", payload)
        # notify specific order trackers
        await self.publish_room(f"order:{order_id}", "order_updated", payload)
        # notify admin feed
        await self.publish_room("orders:admin", "order_updated", payload)
