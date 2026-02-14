"""
Redis Adapter - Production-ready WebSocket adapter using Redis

Uses Redis pub/sub for message fanout and sorted sets for presence.
Supports horizontal scaling across multiple workers.
"""

from __future__ import annotations

from typing import Dict, Set, Optional
import logging
import asyncio
import json
import os

from .base import Adapter, RoomInfo
from ..envelope import MessageEnvelope, JSONCodec

logger = logging.getLogger("aquilia.sockets.adapters.redis")


class RedisAdapter(Adapter):
    """
    Redis-backed adapter for multi-worker deployments.
    
    Uses:
    - Redis pub/sub for message fanout
    - Sorted sets for room membership (with TTL cleanup)
    - Hash for connection metadata
    
    Requires: redis or aioredis
    
    Example:
        adapter = RedisAdapter(redis_url="redis://localhost:6379")
        await adapter.initialize()
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        *,
        prefix: str = "aquilia:ws:",
        worker_id: Optional[str] = None,
        connection_ttl: int = 300,  # 5 minutes
    ):
        """
        Initialize Redis adapter.
        
        Args:
            redis_url: Redis connection URL (default: env REDIS_URL)
            prefix: Key prefix for Redis keys
            worker_id: Worker identifier (default: hostname + PID)
            connection_ttl: Connection TTL in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.prefix = prefix
        self.worker_id = worker_id or f"{os.uname().nodename}:{os.getpid()}"
        self.connection_ttl = connection_ttl
        
        self._redis = None
        self._pubsub = None
        self._subscriber_task = None
        self._send_callbacks: Dict[str, Dict[str, callable]] = {}
        self._codec = JSONCodec()
        
    async def initialize(self) -> None:
        """Initialize Redis connection and subscriber."""
        try:
            import redis.asyncio as aioredis
        except ImportError:
            try:
                import aioredis
            except ImportError:
                raise ImportError(
                    "Redis adapter requires 'redis' package. "
                    "Install with: pip install redis[asyncio]"
                )
        
        # Create Redis client
        self._redis = aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=False,  # We handle encoding/decoding
        )
        
        # Create pub/sub
        self._pubsub = self._redis.pubsub()
        
        # Subscribe to global broadcast channel
        await self._pubsub.subscribe(f"{self.prefix}broadcast")
        
        # Start subscriber task
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        
        logger.info(f"RedisAdapter initialized (worker: {self.worker_id})")
    
    async def shutdown(self) -> None:
        """Shutdown Redis connection."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info("RedisAdapter shut down")
    
    def register_send_callback(
        self,
        namespace: str,
        connection_id: str,
        callback: callable,
    ):
        """Register send callback for connection."""
        if namespace not in self._send_callbacks:
            self._send_callbacks[namespace] = {}
        self._send_callbacks[namespace][connection_id] = callback
    
    def unregister_send_callback(
        self,
        namespace: str,
        connection_id: str,
    ):
        """Unregister send callback."""
        if namespace in self._send_callbacks:
            self._send_callbacks[namespace].pop(connection_id, None)
    
    async def _subscriber_loop(self):
        """Listen for Redis pub/sub messages."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    await self._handle_pubsub_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Subscriber loop error: {e}", exc_info=True)
    
    async def _handle_pubsub_message(self, message: dict):
        """Handle incoming pub/sub message."""
        try:
            # Decode message
            data = json.loads(message["data"])
            
            namespace = data["namespace"]
            room = data.get("room")
            envelope_data = data["envelope"]
            exclude_connection = data.get("exclude_connection")
            
            # Reconstruct envelope
            envelope = MessageEnvelope.from_dict(envelope_data)
            
            # Determine recipients
            if room:
                # Room message - send to room members
                recipients = await self.get_room_members(namespace, room)
            else:
                # Broadcast - send to all connections
                recipients = set(self._send_callbacks.get(namespace, {}).keys())
            
            if exclude_connection:
                recipients.discard(exclude_connection)
            
            # Send to local connections
            encoded = self._codec.encode(envelope)
            tasks = []
            
            for connection_id in recipients:
                callback = self._send_callbacks.get(namespace, {}).get(connection_id)
                if callback:
                    tasks.append(callback(encoded))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Error handling pub/sub message: {e}", exc_info=True)
    
    async def publish(
        self,
        namespace: str,
        room: str,
        envelope: MessageEnvelope,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """Publish message to room via Redis pub/sub."""
        channel = f"{self.prefix}room:{namespace}:{room}"
        
        # Publish message
        message = json.dumps({
            "namespace": namespace,
            "room": room,
            "envelope": envelope.to_dict(),
            "exclude_connection": exclude_connection,
        })
        
        await self._redis.publish(channel, message)
        
        # Also subscribe this worker to the room channel if not subscribed
        if self._pubsub:
            await self._pubsub.subscribe(channel)
    
    async def broadcast(
        self,
        namespace: str,
        envelope: MessageEnvelope,
        exclude_connection: Optional[str] = None,
    ) -> None:
        """Broadcast message to all connections in namespace."""
        channel = f"{self.prefix}broadcast"
        
        message = json.dumps({
            "namespace": namespace,
            "envelope": envelope.to_dict(),
            "exclude_connection": exclude_connection,
        })
        
        await self._redis.publish(channel, message)
    
    async def join_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """Add connection to room (Redis sorted set)."""
        key = f"{self.prefix}members:{namespace}:{room}"
        
        # Add to sorted set with current timestamp as score
        import time
        await self._redis.zadd(key, {connection_id: time.time()})
        
        # Set TTL on room key
        await self._redis.expire(key, self.connection_ttl * 2)
        
        logger.debug(f"Connection {connection_id} joined {namespace}/{room}")
    
    async def leave_room(
        self,
        namespace: str,
        room: str,
        connection_id: str,
    ) -> None:
        """Remove connection from room."""
        key = f"{self.prefix}members:{namespace}:{room}"
        
        await self._redis.zrem(key, connection_id)
        
        logger.debug(f"Connection {connection_id} left {namespace}/{room}")
    
    async def get_room_members(
        self,
        namespace: str,
        room: str,
    ) -> Set[str]:
        """Get all connection IDs in room."""
        key = f"{self.prefix}members:{namespace}:{room}"
        
        # Get all members from sorted set
        members = await self._redis.zrange(key, 0, -1)
        
        return set(m.decode("utf-8") if isinstance(m, bytes) else m for m in members)
    
    async def get_room_info(
        self,
        namespace: str,
        room: str,
    ) -> Optional[RoomInfo]:
        """Get room metadata."""
        members = await self.get_room_members(namespace, room)
        
        if not members:
            return None
        
        return RoomInfo(
            namespace=namespace,
            room=room,
            member_count=len(members),
            members=members,
        )
    
    async def list_rooms(self, namespace: str) -> Set[str]:
        """List all rooms in namespace."""
        pattern = f"{self.prefix}members:{namespace}:*"
        
        rooms = set()
        async for key in self._redis.scan_iter(match=pattern):
            # Extract room name from key
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            room = key_str.split(":", 3)[-1]
            rooms.add(room)
        
        return rooms
    
    async def register_connection(
        self,
        namespace: str,
        connection_id: str,
        worker_id: str,
    ) -> None:
        """Register connection in Redis hash."""
        key = f"{self.prefix}connections:{namespace}"
        
        # Store connection metadata
        await self._redis.hset(
            key,
            connection_id,
            json.dumps({
                "worker_id": worker_id,
                "timestamp": asyncio.get_event_loop().time(),
            })
        )
        
        # Set TTL
        await self._redis.expire(key, self.connection_ttl)
        
        logger.debug(f"Registered connection {connection_id} in {namespace}")
    
    async def unregister_connection(
        self,
        namespace: str,
        connection_id: str,
    ) -> None:
        """Unregister connection."""
        key = f"{self.prefix}connections:{namespace}"
        
        await self._redis.hdel(key, connection_id)
        
        # Remove from all rooms
        rooms = await self.list_rooms(namespace)
        for room in rooms:
            await self.leave_room(namespace, room, connection_id)
        
        logger.debug(f"Unregistered connection {connection_id} from {namespace}")
    
    async def get_connection_count(self, namespace: str) -> int:
        """Get active connection count."""
        key = f"{self.prefix}connections:{namespace}"
        
        count = await self._redis.hlen(key)
        return count
