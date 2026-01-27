from typing import Any, Dict
import logging

from aquilia.sockets import (
    SocketController, 
    Socket,
    OnConnect, 
    OnDisconnect, 
    Event, 
    Connection
)
from aquilia.di import Inject
from aquilia.auth.core import Identity

# Import service for business logic
from .services import MyappmodService

logger = logging.getLogger("myappmod.sockets")


@Socket("/myappmod/ws/chat")
class ChatSocket(SocketController):
    """
    Authenticated Chat WebSocket.
    
    Path: /myappmod/ws/chat
    """
    def __init__(self, service: MyappmodService = Inject()):
        self.service = service
    
    @OnConnect()
    async def on_connect(self, conn: Connection):
        """Handle new chat connection."""
        if not conn.identity:
            # Reject anonymous users
            logger.warning(f"Anonymous connection rejected: {conn.connection_id}")
            await conn.disconnect(reason="Authentication required", code=4001)
            return
            
        logger.info(f"Chat connected: {conn.identity.id}")
        
        # Send welcome message
        await conn.send_event("system.welcome", {
            "message": f"Welcome to Aquilia Chat, {conn.identity.id}!",
            "online_users": 42  # Dummy value
        })
        
        # Determine user room from identity
        user_room = f"user:{conn.identity.id}"
        await conn.join(user_room)

    @OnDisconnect()
    async def on_disconnect(self, conn: Connection, reason: str):
        logger.info(f"Chat disconnected: {conn.connection_id} ({reason})")

    @Event("chat.join")
    async def join_room(self, conn: Connection, payload: Dict[str, Any]):
        """Join a chat room."""
        room = payload.get("room")
        if not room:
            return {"error": "Room required"}
            
        # Permission check (dummy)
        if room.startswith("admin") and "admin" not in conn.identity.roles:
            return {"error": "Forbidden"}
            
        await conn.join(room)
        
        # Notify room
        await self.publish_room(room, "chat.member_joined", {
            "user": conn.identity.id,
            "room": room
        })
        
        return {"status": "joined", "room": room}

    @Event("chat.message")
    async def handle_message(self, conn: Connection, payload: Dict[str, Any]):
        """Handle chat message."""
        room = payload.get("room")
        text = payload.get("text")
        
        if not room or not text:
            return {"error": "Room and text required"}
            
        if room not in conn.rooms:
            return {"error": "Not joined to room"}
            
        # Persist message via service
        # msg_id = await self.service.save_message(...)
        
        # Broadcast to room
        await self.publish_room(room, "chat.message", {
            "from": conn.identity.id,
            "text": text,
            "room": room,
            "ts": "now"
        })
        
        return {"status": "sent"}


@Socket("/myappmod/ws/notifications")
class NotificationSocket(SocketController):
    """
    Notification WebSocket (Server -> Client).
    
    Path: /myappmod/ws/notifications
    """
    
    @OnConnect()
    async def on_connect(self, conn: Connection):
        if not conn.identity:
            await conn.disconnect("Auth required")
            return
            
        # Subscribe to user's personal notification channel
        # Use simple ID-based topic
        topic = f"notifications:{conn.identity.id}"
        await conn.join(topic)
        
        logger.info(f"Notification subscription active for {conn.identity.id}")


@Socket("/myappmod/ws/feed")
class PublicFeedSocket(SocketController):
    """
    Public Feed WebSocket (Broadcast).
    
    Path: /myappmod/ws/feed
    """
    
    @OnConnect()
    async def on_connect(self, conn: Connection):
        # Allow anonymous
        await conn.join("public_feed")
        
        user_type = "User" if conn.identity else "Guest"
        logger.info(f"Feed listener connected ({user_type})")
