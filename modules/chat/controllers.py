"""
Example Chat WebSocket Controller

Demonstrates:
- Room-based chat
- Presence tracking
- Message history
- Typing indicators
"""

from aquilia.sockets import (
    SocketController,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    Subscribe,
    Unsubscribe,
    Connection,
    Schema,
)
from aquilia.di import Inject
from typing import Optional, Dict, List, Any
from datetime import datetime


# Mock presence service (would be real DI service)
class PresenceService:
    """Track online users."""
    
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
    
    async def join(self, user_id: str, connection_id: str, metadata: Dict[str, Any]):
        """Mark user as online."""
        self.users[user_id] = {
            "connection_id": connection_id,
            "joined_at": datetime.utcnow().isoformat(),
            **metadata
        }
    
    async def leave(self, user_id: str):
        """Mark user as offline."""
        self.users.pop(user_id, None)
    
    def get_online_users(self) -> List[str]:
        """Get list of online user IDs."""
        return list(self.users.keys())


@Socket("/chat/:namespace")
class ChatSocket(SocketController):
    """
    Chat WebSocket controller.
    
    Supports:
    - Room-based messaging
    - User presence
    - Typing indicators
    - Message acknowledgements
    """
    
    def __init__(self, presence: Optional[PresenceService] = None):
        """
        Initialize chat controller.
        
        Args:
            presence: Presence service (DI injected)
        """
        super().__init__()
        self.presence = presence or PresenceService()
    
    @OnConnect()
    async def on_connect(self, conn: Connection):
        """
        Handle new connection.
        
        Sends welcome message and current online users.
        """
        # Track user presence
        if conn.identity:
            await self.presence.join(
                user_id=conn.identity.id,
                connection_id=conn.connection_id,
                metadata={
                    "namespace": conn.scope.path_params.get("namespace", "general"),
                }
            )
        
        # Send welcome
        await conn.send_event("system.welcome", {
            "message": f"Welcome to chat!",
            "user_id": conn.identity.id if conn.identity else "anonymous",
            "namespace": conn.scope.path_params.get("namespace", "general"),
            "online_users": self.presence.get_online_users(),
        })
    
    @OnDisconnect()
    async def on_disconnect(self, conn: Connection, reason: Optional[str]):
        """
        Handle disconnection.
        
        Removes user from presence and notifies room.
        """
        if conn.identity:
            await self.presence.leave(conn.identity.id)
            
            # Notify rooms
            for room in conn.rooms:
                await self.publish_room(room, "user.left", {
                    "user_id": conn.identity.id,
                    "reason": reason,
                })
    
    @Event("message.send", schema=Schema({
        "room": str,
        "text": (str, {"min_length": 1, "max_length": 1000}),
    }))
    async def handle_message(self, conn: Connection, payload: Dict[str, Any]):
        """
        Handle chat message.
        
        Broadcasts to all users in room.
        """
        room = payload["room"]
        text = payload["text"]
        
        # Broadcast to room
        await self.publish_room(room, "message.receive", {
            "from": conn.identity.id if conn.identity else "anonymous",
            "room": room,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    @Subscribe("room.join")
    async def subscribe_room(self, conn: Connection, payload: Dict[str, Any]):
        """
        Handle room subscription.
        
        Adds user to room and notifies others.
        """
        room = payload["room"]
        
        # Join room
        await conn.join(room)
        
        # Notify user
        await conn.send_event("room.joined", {
            "room": room,
            "members": await self.get_room_member_count(room),
        })
        
        # Notify others
        await self.publish_room(room, "user.joined", {
            "user_id": conn.identity.id if conn.identity else "anonymous",
            "room": room,
        })
    
    @Unsubscribe("room.leave")
    async def unsubscribe_room(self, conn: Connection, payload: Dict[str, Any]):
        """
        Handle room unsubscription.
        
        Removes user from room.
        """
        room = payload["room"]
        
        # Leave room
        await conn.leave(room)
        
        # Notify user
        await conn.send_event("room.left", {"room": room})
        
        # Notify others
        await self.publish_room(room, "user.left", {
            "user_id": conn.identity.id if conn.identity else "anonymous",
            "room": room,
        })
    
    @Event("typing.start", schema=Schema({"room": str}))
    async def handle_typing_start(self, conn: Connection, payload: Dict[str, Any]):
        """Handle typing indicator start."""
        room = payload["room"]
        
        await self.publish_room(room, "typing.indicator", {
            "user_id": conn.identity.id if conn.identity else "anonymous",
            "room": room,
            "typing": True,
        })
    
    @Event("typing.stop", schema=Schema({"room": str}))
    async def handle_typing_stop(self, conn: Connection, payload: Dict[str, Any]):
        """Handle typing indicator stop."""
        room = payload["room"]
        
        await self.publish_room(room, "typing.indicator", {
            "user_id": conn.identity.id if conn.identity else "anonymous",
            "room": room,
            "typing": False,
        })
    
    async def get_room_member_count(self, room: str) -> int:
        """Get number of members in room."""
        if self.adapter:
            members = await self.adapter.get_room_members(self.namespace, room)
            return len(members)
        return 0
