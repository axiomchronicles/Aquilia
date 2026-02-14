"""
Chat Module - Services

Showcases:
- Chat room management
- Message history storage
- User presence tracking
- DI service scoping
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid

from aquilia.di import service


@service(scope="app")
class ChatRoomService:
    """
    Manages chat rooms and their metadata.

    App-scoped singleton for shared state across connections.
    """

    def __init__(self):
        self._rooms: Dict[str, Dict[str, Any]] = {
            "general": {
                "id": "general",
                "name": "General",
                "description": "General discussion",
                "created_at": datetime.utcnow().isoformat(),
                "is_public": True,
            },
            "random": {
                "id": "random",
                "name": "Random",
                "description": "Off-topic chat",
                "created_at": datetime.utcnow().isoformat(),
                "is_public": True,
            },
        }

    async def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        return self._rooms.get(room_id)

    async def list_rooms(self) -> List[Dict[str, Any]]:
        return list(self._rooms.values())

    async def create_room(
        self, name: str, description: str = "", is_public: bool = True
    ) -> Dict[str, Any]:
        room_id = name.lower().replace(" ", "-")
        room = {
            "id": room_id,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "is_public": is_public,
        }
        self._rooms[room_id] = room
        return room

    async def delete_room(self, room_id: str) -> bool:
        return self._rooms.pop(room_id, None) is not None


@service(scope="app")
class MessageService:
    """
    Message history and storage.

    Stores recent messages per room (last 100).
    """

    def __init__(self):
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._max_per_room = 100
        # Seed with some initial messages
        self._seed_initial_messages()

    def _seed_initial_messages(self):
        """Add some initial messages for demonstration."""
        initial_messages = [
            {
                "room": "general",
                "sender": "System",
                "text": "Welcome to Aquilia Chat! 🚀",
            },
            {
                "room": "general",
                "sender": "Admin",
                "text": "Feel free to introduce yourself and start chatting!",
            },
            {
                "room": "random",
                "sender": "System",
                "text": "This is the random channel - anything goes!",
            },
        ]

        for msg_data in initial_messages:
            room_id = msg_data["room"]
            if room_id not in self._messages:
                self._messages[room_id] = []

            message = {
                "id": str(uuid.uuid4()),
                "room_id": room_id,
                "sender": msg_data["sender"],
                "text": msg_data["text"],
                "type": "text",
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._messages[room_id].append(message)

    async def add_message(
        self,
        room_id: str,
        sender: str,
        text: str,
        message_type: str = "text",
    ) -> Dict[str, Any]:
        """Store a message in a room."""
        if room_id not in self._messages:
            self._messages[room_id] = []

        message = {
            "id": str(uuid.uuid4()),
            "room_id": room_id,
            "sender": sender,
            "text": text,
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._messages[room_id].append(message)

        # Keep only last N messages
        if len(self._messages[room_id]) > self._max_per_room:
            self._messages[room_id] = self._messages[room_id][-self._max_per_room:]

        return message

    async def get_history(
        self, room_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get message history for a room."""
        messages = self._messages.get(room_id, [])
        return messages[-limit:]

    async def get_stats(self) -> Dict[str, Any]:
        """Get message statistics."""
        total = sum(len(msgs) for msgs in self._messages.values())
        return {
            "total_messages": total,
            "rooms_with_messages": len(self._messages),
        }


@service(scope="app")
class PresenceService:
    """
    User presence tracking.

    Tracks which users are online and in which rooms.
    """

    def __init__(self):
        self._online_users: Dict[str, Dict[str, Any]] = {}  # conn_id -> user info
        self._room_members: Dict[str, Set[str]] = {}  # room_id -> set of conn_ids

    async def user_connected(self, conn_id: str, username: str):
        """Mark user as online."""
        self._online_users[conn_id] = {
            "username": username,
            "connected_at": datetime.utcnow().isoformat(),
            "rooms": set(),
        }

    async def user_disconnected(self, conn_id: str) -> Optional[str]:
        """Mark user as offline, return username."""
        user = self._online_users.pop(conn_id, None)
        if user:
            # Remove from all rooms
            for room_id in user.get("rooms", set()):
                if room_id in self._room_members:
                    self._room_members[room_id].discard(conn_id)
            return user["username"]
        return None

    async def join_room(self, conn_id: str, room_id: str):
        """Add user to room."""
        if room_id not in self._room_members:
            self._room_members[room_id] = set()
        self._room_members[room_id].add(conn_id)

        if conn_id in self._online_users:
            self._online_users[conn_id]["rooms"].add(room_id)

    async def leave_room(self, conn_id: str, room_id: str):
        """Remove user from room."""
        if room_id in self._room_members:
            self._room_members[room_id].discard(conn_id)
        if conn_id in self._online_users:
            self._online_users[conn_id]["rooms"].discard(room_id)

    async def get_room_members(self, room_id: str) -> List[str]:
        """Get usernames in a room."""
        conn_ids = self._room_members.get(room_id, set())
        return [
            self._online_users[cid]["username"]
            for cid in conn_ids
            if cid in self._online_users
        ]

    async def get_online_count(self) -> int:
        return len(self._online_users)

    async def get_online_users(self) -> List[str]:
        return [u["username"] for u in self._online_users.values()]
