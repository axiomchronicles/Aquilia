"""
Adapter Base - Protocol for WebSocket scaling adapters

Adapters provide pub/sub and presence for horizontal scaling.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, Protocol
from dataclasses import dataclass

from ..envelope import MessageEnvelope


@dataclass
class RoomInfo:
    """Room metadata."""
    namespace: str
    room: str
    member_count: int
    members: Set[str]  # connection IDs


class Adapter(Protocol):
    """
    Adapter protocol for WebSocket scaling.
    
    Provides:
    - pub/sub for message fanout across workers
    - Room/presence management
    - Connection tracking
    
    Implementations:
    - InMemoryAdapter: Single-process (dev/testing)
    - RedisAdapter: Redis pub/sub + sorted sets
    - NATSAdapter: NATS messaging
    - KafkaAdapter: Kafka streaming
    """
    
    async def initialize(self) -> None:
        """Initialize adapter (connect to backend)."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown adapter (close connections)."""
        ...
    
    async def publish(
        self,
        namespace: str,
        room: str,
        envelope: MessageEnvelope,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """
        Publish message to room.
        
        Delivers to all connections in room across all workers.
        
        Args:
            namespace: Socket namespace
            room: Room identifier
            envelope: Message envelope
            exclude_connection: Optional connection ID to exclude
        """
        ...
    
    async def broadcast(
        self,
        namespace: str,
        envelope: MessageEnvelope,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """
        Broadcast message to all connections in namespace.
        
        Args:
            namespace: Socket namespace
            envelope: Message envelope
            exclude_connection: Optional connection to exclude
        """
        ...
    
    async def join_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """
        Register connection as room member.
        
        Args:
            namespace: Socket namespace
            room: Room identifier
            connection_id: Connection identifier
        """
        ...
    
    async def leave_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """
        Unregister connection from room.
        
        Args:
            namespace: Socket namespace
            room: Room identifier
            connection_id: Connection identifier
        """
        ...
    
    async def get_room_members(
        self,
        namespace: str,
        room: str,
    ) -> Set[str]:
        """
        Get connection IDs in room.
        
        Args:
            namespace: Socket namespace
            room: Room identifier
            
        Returns:
            Set of connection IDs
        """
        ...
    
    async def get_room_info(
        self,
        namespace: str,
        room: str,
    ) -> Optional[RoomInfo]:
        """
        Get room metadata.
        
        Args:
            namespace: Socket namespace
            room: Room identifier
            
        Returns:
            Room info or None if not found
        """
        ...
    
    async def list_rooms(self, namespace: str) -> Set[str]:
        """
        List all rooms in namespace.
        
        Args:
            namespace: Socket namespace
            
        Returns:
            Set of room identifiers
        """
        ...
    
    async def register_connection(
        self,
        namespace: str,
        connection_id: str,
        worker_id: str,
    ) -> None:
        """
        Register active connection.
        
        Args:
            namespace: Socket namespace
            connection_id: Connection identifier
            worker_id: Worker/process identifier
        """
        ...
    
    async def unregister_connection(
        self,
        namespace: str,
        connection_id: str,
    ) -> None:
        """
        Unregister connection.
        
        Args:
            namespace: Socket namespace
            connection_id: Connection identifier
        """
        ...
    
    async def get_connection_count(self, namespace: str) -> int:
        """
        Get active connection count.
        
        Args:
            namespace: Socket namespace
            
        Returns:
            Number of active connections
        """
        ...
