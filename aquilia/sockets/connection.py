"""
Connection - WebSocket connection abstraction with DI scope

Each WebSocket connection has:
- Unique connection ID
- Request-scoped DI container
- Identity (from handshake auth)
- Session (from handshake)
- Room subscriptions
- State dictionary
- Send/receive capabilities
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging

if TYPE_CHECKING:
    from aquilia.di import Container
    from aquilia.auth.core import Identity
    from aquilia.sessions.core import Session
    from .envelope import MessageEnvelope
    from .adapters.base import Adapter

logger = logging.getLogger("aquilia.sockets.connection")


class ConnectionState(str, Enum):
    """Connection lifecycle state."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class ConnectionScope:
    """Scope metadata for connection."""
    namespace: str  # e.g., "/chat/:namespace"
    path: str       # e.g., "/chat/general"
    path_params: Dict[str, Any]
    query_params: Dict[str, Any]
    headers: Dict[str, str]


class Connection:
    """
    WebSocket connection with DI scope.
    
    Represents a single WebSocket connection and provides:
    - Message sending (send_event, send_raw)
    - Room management (join, leave)
    - Broadcasting (publish_room, broadcast)
    - State management
    - DI container access
    """
    
    def __init__(
        self,
        connection_id: str,
        namespace: str,
        scope: ConnectionScope,
        container: Container,
        adapter: Adapter,
        send_func: callable,
        identity: Optional[Identity] = None,
        session: Optional[Session] = None,
    ):
        """
        Initialize connection.
        
        Args:
            connection_id: Unique connection identifier
            namespace: Socket namespace
            scope: Connection scope metadata
            container: Request-scoped DI container
            adapter: Adapter for pub/sub
            send_func: Low-level send function
            identity: Authenticated identity
            session: Session object
        """
        self.connection_id = connection_id
        self.namespace = namespace
        self.scope = scope
        self.container = container
        self.adapter = adapter
        self._send_func = send_func
        self.identity = identity
        self.session = session
        
        # State
        self.state: Dict[str, Any] = {}
        self._connection_state = ConnectionState.CONNECTING
        self._rooms: Set[str] = set()
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        
        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connection_state == ConnectionState.CONNECTED
    
    @property
    def rooms(self) -> Set[str]:
        """Get subscribed rooms."""
        return self._rooms.copy()
    
    def mark_connected(self):
        """Mark connection as connected."""
        self._connection_state = ConnectionState.CONNECTED
    
    def mark_closing(self):
        """Mark connection as closing."""
        self._connection_state = ConnectionState.CLOSING
    
    def mark_closed(self):
        """Mark connection as closed."""
        self._connection_state = ConnectionState.CLOSED
    
    async def send_event(
        self,
        event: str,
        payload: Dict[str, Any],
        ack: bool = False,
    ) -> Optional[str]:
        """
        Send event message to client.
        
        Args:
            event: Event name
            payload: Event data
            ack: Request acknowledgement
            
        Returns:
            Message ID if ack requested
        """
        from .envelope import MessageEnvelope, MessageType
        
        envelope = MessageEnvelope(
            type=MessageType.EVENT,
            event=event,
            payload=payload,
            ack=ack,
        )
        
        await self.send_envelope(envelope)
        
        return envelope.id if ack else None
    
    async def send_envelope(self, envelope: MessageEnvelope):
        """Send message envelope to client."""
        from .envelope import JSONCodec
        
        codec = JSONCodec()
        data = codec.encode(envelope)
        
        await self._send_func(data)
        
        self.messages_sent += 1
        self.bytes_sent += len(data)
        self.last_activity = datetime.now(timezone.utc)
    
    async def send_raw(self, data: bytes):
        """Send raw bytes to client."""
        await self._send_func(data)
        
        self.messages_sent += 1
        self.bytes_sent += len(data)
        self.last_activity = datetime.now(timezone.utc)
    
    async def send_ack(
        self,
        message_id: str,
        status: str = "ok",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """
        Send acknowledgement message.
        
        Args:
            message_id: Original message ID
            status: "ok" or "error"
            data: Optional response data
            error: Optional error message
        """
        from .envelope import MessageEnvelope, MessageType
        
        ack_envelope = MessageEnvelope(
            id=message_id,
            type=MessageType.ACK,
            event="ack",
            payload={
                "status": status,
                "data": data or {},
                "error": error,
            },
        )
        
        await self.send_envelope(ack_envelope)
    
    async def join(self, room: str) -> bool:
        """
        Join a room (subscribe).
        
        Args:
            room: Room identifier
            
        Returns:
            True if newly joined, False if already member
        """
        if room in self._rooms:
            return False
        
        self._rooms.add(room)
        
        # Register with adapter
        await self.adapter.join_room(
            namespace=self.namespace,
            room=room,
            connection_id=self.connection_id,
        )
        
        logger.debug(f"Connection {self.connection_id} joined room {room}")
        
        return True
    
    async def leave(self, room: str) -> bool:
        """
        Leave a room (unsubscribe).
        
        Args:
            room: Room identifier
            
        Returns:
            True if was member, False otherwise
        """
        if room not in self._rooms:
            return False
        
        self._rooms.discard(room)
        
        # Unregister from adapter
        await self.adapter.leave_room(
            namespace=self.namespace,
            room=room,
            connection_id=self.connection_id,
        )
        
        logger.debug(f"Connection {self.connection_id} left room {room}")
        
        return True
    
    async def leave_all(self):
        """Leave all rooms."""
        for room in list(self._rooms):
            await self.leave(room)
    
    async def disconnect(self, reason: Optional[str] = None, code: int = 1000):
        """
        Disconnect the connection.
        
        Args:
            reason: Optional disconnect reason
            code: WebSocket close code
        """
        self.mark_closing()
        
        # Leave all rooms
        await self.leave_all()
        
        # Send close frame (implementation depends on ASGI adapter)
        logger.info(f"Connection {self.connection_id} disconnecting: {reason}")
    
    def record_received(self, size: int):
        """Record received message stats."""
        self.messages_received += 1
        self.bytes_received += size
        self.last_activity = datetime.now(timezone.utc)
    
    async def resolve(self, name: str, optional: bool = False) -> Any:
        """
        Resolve dependency from container.
        
        Args:
            name: Dependency name
            optional: Don't raise if not found
            
        Returns:
            Resolved dependency
        """
        return await self.container.resolve_async(name, optional=optional)
    
    def __repr__(self) -> str:
        identity_id = self.identity.id if self.identity else "anonymous"
        return (
            f"Connection(id={self.connection_id}, "
            f"namespace={self.namespace}, "
            f"identity={identity_id}, "
            f"rooms={len(self._rooms)}, "
            f"state={self._connection_state.value})"
        )
