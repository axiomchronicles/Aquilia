"""
In-Memory Adapter - Single-process WebSocket adapter

For development and testing. No external dependencies.
Not suitable for multi-worker production deployments.
"""

from __future__ import annotations

from typing import Dict, Set, Optional
from collections import defaultdict
import logging
import asyncio

from .base import Adapter, RoomInfo
from ..envelope import MessageEnvelope

logger = logging.getLogger("aquilia.sockets.adapters.inmemory")


class InMemoryAdapter(Adapter):
    """
    In-memory adapter for single-process deployments.
    
    Stores rooms and connections in memory.
    Fast but cannot scale horizontally.
    
    Use cases:
    - Development
    - Testing
    - Single-worker production (small scale)
    """
    
    def __init__(self):
        """Initialize in-memory adapter."""
        # {namespace: {room: set(connection_ids)}}
        self._rooms: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # {namespace: {connection_id: worker_id}}
        self._connections: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        # {namespace: {connection_id: send_callback}}
        self._send_callbacks: Dict[str, Dict[str, callable]] = defaultdict(dict)
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize adapter."""
        self._initialized = True
        logger.info("InMemoryAdapter initialized")
    
    async def shutdown(self) -> None:
        """Shutdown adapter."""
        self._rooms.clear()
        self._connections.clear()
        self._send_callbacks.clear()
        self._initialized = False
        logger.info("InMemoryAdapter shut down")
    
    def register_send_callback(
        self,
        namespace: str,
        connection_id: str,
        callback: callable,
    ):
        """
        Register send callback for connection.
        
        This allows the adapter to send messages directly to connections.
        
        Args:
            namespace: Socket namespace
            connection_id: Connection identifier
            callback: Async callable(data: bytes)
        """
        self._send_callbacks[namespace][connection_id] = callback
    
    def unregister_send_callback(
        self,
        namespace: str,
        connection_id: str,
    ):
        """Unregister send callback."""
        if connection_id in self._send_callbacks[namespace]:
            del self._send_callbacks[namespace][connection_id]
    
    async def publish(
        self,
        namespace: str,
        room: str,
        envelope: MessageEnvelope,
    ) -> None:
        """Publish message to room."""
        room_members = self._rooms[namespace].get(room, set())
        
        if not room_members:
            logger.debug(f"No members in room {namespace}/{room}")
            return
        
        # Encode message once
        from ..envelope import JSONCodec
        codec = JSONCodec()
        data = codec.encode(envelope)
        
        # Send to all members
        tasks = []
        for connection_id in room_members:
            callback = self._send_callbacks[namespace].get(connection_id)
            if callback:
                tasks.append(callback(data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug(f"Published to {len(room_members)} members in {namespace}/{room}")
    
    async def broadcast(
        self,
        namespace: str,
        envelope: MessageEnvelope,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """Broadcast message to all connections in namespace."""
        connections = set(self._connections[namespace].keys())
        
        if exclude_connection:
            connections.discard(exclude_connection)
        
        if not connections:
            return
        
        # Encode message once
        from ..envelope import JSONCodec
        codec = JSONCodec()
        data = codec.encode(envelope)
        
        # Send to all connections
        tasks = []
        for connection_id in connections:
            callback = self._send_callbacks[namespace].get(connection_id)
            if callback:
                tasks.append(callback(data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug(f"Broadcast to {len(connections)} connections in {namespace}")
    
    async def join_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """Register connection as room member."""
        self._rooms[namespace][room].add(connection_id)
        logger.debug(f"Connection {connection_id} joined {namespace}/{room}")
    
    async def leave_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """Unregister connection from room."""
        if room in self._rooms[namespace]:
            self._rooms[namespace][room].discard(connection_id)
            
            # Clean up empty rooms
            if not self._rooms[namespace][room]:
                del self._rooms[namespace][room]
        
        logger.debug(f"Connection {connection_id} left {namespace}/{room}")
    
    async def get_room_members(
        self,
        namespace: str,
        room: str,
    ) -> Set[str]:
        """Get connection IDs in room."""
        return self._rooms[namespace].get(room, set()).copy()
    
    async def get_room_info(
        self,
        namespace: str,
        room: str,
    ) -> Optional[RoomInfo]:
        """Get room metadata."""
        members = self._rooms[namespace].get(room)
        
        if members is None:
            return None
        
        return RoomInfo(
            namespace=namespace,
            room=room,
            member_count=len(members),
            members=members.copy(),
        )
    
    async def list_rooms(self, namespace: str) -> Set[str]:
        """List all rooms in namespace."""
        return set(self._rooms[namespace].keys())
    
    async def register_connection(
        self,
        namespace: str,
        connection_id: str,
        worker_id: str,
    ) -> None:
        """Register active connection."""
        self._connections[namespace][connection_id] = worker_id
        logger.debug(f"Registered connection {connection_id} in {namespace}")
    
    async def unregister_connection(
        self,
        namespace: str,
        connection_id: str,
    ) -> None:
        """Unregister connection."""
        if connection_id in self._connections[namespace]:
            del self._connections[namespace][connection_id]
        
        # Remove from all rooms
        for room in list(self._rooms[namespace].keys()):
            self._rooms[namespace][room].discard(connection_id)
            
            # Clean up empty rooms
            if not self._rooms[namespace][room]:
                del self._rooms[namespace][room]
        
        logger.debug(f"Unregistered connection {connection_id} from {namespace}")
    
    async def get_connection_count(self, namespace: str) -> int:
        """Get active connection count."""
        return len(self._connections[namespace])
