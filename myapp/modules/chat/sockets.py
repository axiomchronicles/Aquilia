"""
Chat Module - WebSocket Controller

Showcases:
- @Socket decorator for namespace definition
- @OnConnect / @OnDisconnect lifecycle handlers
- @Event for handling named events
- @AckEvent for events requiring acknowledgment
- Room management (join/leave/broadcast)
- Connection state management
- Per-connection identity
- Message broadcasting patterns
- Service integration for persistence
"""

from aquilia.sockets import (
    SocketController,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AckEvent,
    Subscribe,
    Unsubscribe,
)
from .services import ChatRoomService, MessageService, PresenceService


@Socket("/chat")
class ChatSocket(SocketController):
    """
    Real-time chat WebSocket controller with service integration.

    Demonstrates the full WebSocket lifecycle:
    1. Client connects → @OnConnect
    2. Client sends events → @Event / @AckEvent
    3. Server broadcasts → self.broadcast_to_room()
    4. Client disconnects → @OnDisconnect

    Usage (JavaScript client):
        const ws = new WebSocket("ws://localhost:8000/chat");

        ws.onopen = () => {
            ws.send(JSON.stringify({
                event: "set_username",
                data: { username: "Alice" }
            }));
        };

        ws.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            console.log(data);
        };

        // Send a message
        ws.send(JSON.stringify({
            event: "message",
            data: { text: "Hello everyone!", room: "general" }
        }));
    """

    namespace = "/chat"

    def __init__(
        self,
        rooms: ChatRoomService = None,
        messages: MessageService = None,
        presence: PresenceService = None,
    ):
        super().__init__()
        self.rooms = rooms or ChatRoomService()
        self.messages = messages or MessageService()
        self.presence = presence or PresenceService()

    @OnConnect()
    async def on_connect(self, connection):
        """
        Handle new WebSocket connection.

        - Assign a temporary guest username
        - Join the default "general" room
        - Notify others of the new connection
        - Register with presence service
        """
        username = f"guest_{connection.id[:8]}"
        connection.state["username"] = username
        connection.state["rooms"] = {"general"}

        # Register with presence service
        await self.presence.user_connected(connection.id, username)

        # Send welcome message
        await connection.send_json({
            "type": "system",
            "event": "welcome",
            "data": {
                "message": "Welcome to Aquilia Chat!",
                "connection_id": connection.id,
                "username": username,
                "default_room": "general",
            },
        })

        # Join general room
        await connection.join_room("general")
        await self.presence.join_room(connection.id, "general")

        # Notify room
        await self.broadcast_to_room("general", {
            "type": "system",
            "event": "user_joined",
            "data": {
                "username": username,
                "room": "general",
            },
        }, exclude=connection.id)

    @OnDisconnect()
    async def on_disconnect(self, connection):
        """
        Handle WebSocket disconnection.

        - Leave all rooms
        - Notify others
        - Unregister from presence service
        """
        username = connection.state.get("username", "unknown")
        rooms = connection.state.get("rooms", set())

        for room in rooms:
            await connection.leave_room(room)
            await self.presence.leave_room(connection.id, room)
            await self.broadcast_to_room(room, {
                "type": "system",
                "event": "user_left",
                "data": {
                    "username": username,
                    "room": room,
                },
            })

        # Unregister from presence
        await self.presence.user_disconnected(connection.id)

    @AckEvent("set_username")
    async def set_username(self, connection, data):
        """
        Set username for the connection.

        Event: set_username
        Data: { "username": "Alice" }
        Response: { "status": "ok", "username": "Alice" }

        Uses @AckEvent — the return value is sent back as acknowledgment.
        """
        old_username = connection.state.get("username", "unknown")
        new_username = data.get("username", "").strip()

        if not new_username:
            return {"status": "error", "message": "Username cannot be empty"}

        if len(new_username) > 32:
            return {"status": "error", "message": "Username too long (max 32 chars)"}

        connection.state["username"] = new_username

        # Notify rooms of name change
        for room in connection.state.get("rooms", set()):
            await self.broadcast_to_room(room, {
                "type": "system",
                "event": "username_changed",
                "data": {
                    "old_username": old_username,
                    "new_username": new_username,
                    "room": room,
                },
            }, exclude=connection.id)

        return {"status": "ok", "username": new_username}

    @Event("message")
    async def on_message(self, connection, data):
        """
        Handle incoming chat message.

        Event: message
        Data: { "text": "Hello!", "room": "general" }

        Broadcasts the message to all connections in the specified room
        and stores it in message history.
        """
        text = data.get("text", "").strip()
        room = data.get("room", "general")
        username = connection.state.get("username", "anonymous")

        if not text:
            await connection.send_json({
                "type": "error",
                "event": "message_error",
                "data": {"message": "Empty message"},
            })
            return

        if len(text) > 2000:
            await connection.send_json({
                "type": "error",
                "event": "message_error",
                "data": {"message": "Message too long (max 2000 chars)"},
            })
            return

        # Store message in history
        await self.messages.add_message(
            room_id=room,
            sender=username,
            text=text,
            message_type="text"
        )

        # Broadcast to room
        await self.broadcast_to_room(room, {
            "type": "message",
            "event": "new_message",
            "data": {
                "text": text,
                "from": username,
                "room": room,
                "connection_id": connection.id,
            },
        })

    @AckEvent("join_room")
    async def join_room(self, connection, data):
        """
        Join a chat room.

        Event: join_room
        Data: { "room": "random" }
        """
        room = data.get("room", "").strip()
        if not room:
            return {"status": "error", "message": "Room name required"}

        username = connection.state.get("username", "anonymous")
        rooms = connection.state.get("rooms", set())

        if room in rooms:
            return {"status": "error", "message": f"Already in room '{room}'"}

        # Join room
        await connection.join_room(room)
        rooms.add(room)
        connection.state["rooms"] = rooms

        # Register with presence
        await self.presence.join_room(connection.id, room)

        # Notify room
        await self.broadcast_to_room(room, {
            "type": "system",
            "event": "user_joined",
            "data": {"username": username, "room": room},
        }, exclude=connection.id)

        return {"status": "ok", "room": room, "message": f"Joined '{room}'"}

    @AckEvent("leave_room")
    async def leave_room(self, connection, data):
        """
        Leave a chat room.

        Event: leave_room
        Data: { "room": "random" }
        """
        room = data.get("room", "").strip()
        if not room:
            return {"status": "error", "message": "Room name required"}

        username = connection.state.get("username", "anonymous")
        rooms = connection.state.get("rooms", set())

        if room not in rooms:
            return {"status": "error", "message": f"Not in room '{room}'"}

        if room == "general":
            return {"status": "error", "message": "Cannot leave the general room"}

        # Leave room
        await connection.leave_room(room)
        rooms.discard(room)
        connection.state["rooms"] = rooms

        # Unregister from presence
        await self.presence.leave_room(connection.id, room)

        # Notify room
        await self.broadcast_to_room(room, {
            "type": "system",
            "event": "user_left",
            "data": {"username": username, "room": room},
        })

        return {"status": "ok", "room": room, "message": f"Left '{room}'"}

    @Subscribe("typing")
    async def on_typing_start(self, connection, data):
        """
        Handle typing indicator.

        Event: typing (subscribe)
        Data: { "room": "general" }

        Broadcasts typing indicator to room, excluding the sender.
        """
        room = data.get("room", "general")
        username = connection.state.get("username", "anonymous")

        await self.broadcast_to_room(room, {
            "type": "presence",
            "event": "typing",
            "data": {
                "username": username,
                "room": room,
                "is_typing": True,
            },
        }, exclude=connection.id)

    @Unsubscribe("typing")
    async def on_typing_stop(self, connection, data):
        """
        Handle typing stop indicator.

        Event: typing (unsubscribe)
        Data: { "room": "general" }
        """
        room = data.get("room", "general")
        username = connection.state.get("username", "anonymous")

        await self.broadcast_to_room(room, {
            "type": "presence",
            "event": "typing",
            "data": {
                "username": username,
                "room": room,
                "is_typing": False,
            },
        }, exclude=connection.id)

    @AckEvent("list_rooms")
    async def list_rooms(self, connection, data):
        """
        List available rooms and joined rooms.

        Event: list_rooms
        Data: {}
        """
        joined = list(connection.state.get("rooms", set()))
        return {
            "status": "ok",
            "joined_rooms": joined,
            "available_rooms": ["general", "random", "tech", "gaming"],
        }


@Socket("/notifications")
class NotificationSocket(SocketController):
    """
    Notification WebSocket controller.

    Demonstrates a simpler socket pattern for one-way server → client push.
    """

    namespace = "/notifications"

    @OnConnect()
    async def on_connect(self, connection):
        """Register for notifications."""
        connection.state["subscriptions"] = set()
        await connection.send_json({
            "type": "system",
            "event": "connected",
            "data": {"message": "Notification channel connected"},
        })

    @OnDisconnect()
    async def on_disconnect(self, connection):
        """Cleanup notification subscriptions."""
        pass

    @AckEvent("subscribe")
    async def subscribe_topic(self, connection, data):
        """
        Subscribe to a notification topic.

        Event: subscribe
        Data: { "topic": "orders" }
        """
        topic = data.get("topic", "")
        if not topic:
            return {"status": "error", "message": "Topic required"}

        subs = connection.state.get("subscriptions", set())
        subs.add(topic)
        connection.state["subscriptions"] = subs
        await connection.join_room(f"notify:{topic}")

        return {"status": "ok", "topic": topic, "subscribed": True}

    @AckEvent("unsubscribe")
    async def unsubscribe_topic(self, connection, data):
        """
        Unsubscribe from a notification topic.

        Event: unsubscribe
        Data: { "topic": "orders" }
        """
        topic = data.get("topic", "")
        subs = connection.state.get("subscriptions", set())
        subs.discard(topic)
        connection.state["subscriptions"] = subs
        await connection.leave_room(f"notify:{topic}")

        return {"status": "ok", "topic": topic, "subscribed": False}
