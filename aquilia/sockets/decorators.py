"""
Socket Controller Decorators - Declarative WebSocket controller syntax

Provides Aquilia-first decorator syntax:
- @Socket(path) - Declare WebSocket namespace
- @OnConnect() - Handshake handler
- @OnDisconnect() - Cleanup handler
- @Event(name, schema) - Message handler
- @AckEvent(name) - Acknowledgement-enabled event
- @Subscribe(event) - Room subscription handler
- @Unsubscribe(event) - Room unsubscription handler
- @Guard() - Per-method or per-controller guard
"""

from typing import Any, Callable, Optional, TypeVar
from functools import wraps
import inspect

from .envelope import Schema

F = TypeVar('F', bound=Callable[..., Any])


class Socket:
    """
    WebSocket controller decorator.
    
    Declares a WebSocket namespace and path pattern.
    
    Example:
        @Socket("/chat/:namespace")
        class ChatSocket(SocketController):
            ...
    """
    
    def __init__(
        self,
        path: str,
        *,
        allowed_origins: Optional[list[str]] = None,
        max_connections: Optional[int] = None,
        message_rate_limit: Optional[int] = None,  # messages per second
        max_message_size: int = 65536,  # 64KB default
        compression: bool = True,
        subprotocols: Optional[list[str]] = None,
    ):
        """
        Initialize Socket decorator.
        
        Args:
            path: URL path pattern (supports Aquilia patterns like /:id)
            allowed_origins: Whitelist of allowed origins
            max_connections: Max concurrent connections per namespace
            message_rate_limit: Messages per second per connection
            max_message_size: Max message size in bytes
            compression: Enable WebSocket compression
            subprotocols: Supported WebSocket subprotocols
        """
        self.path = path
        self.allowed_origins = allowed_origins
        self.max_connections = max_connections
        self.message_rate_limit = message_rate_limit
        self.max_message_size = max_message_size
        self.compression = compression
        self.subprotocols = subprotocols
    
    def __call__(self, cls: type) -> type:
        """Attach metadata to controller class."""
        # Store metadata on class
        cls.__socket_metadata__ = {
            'path': self.path,
            'allowed_origins': self.allowed_origins,
            'max_connections': self.max_connections,
            'message_rate_limit': self.message_rate_limit,
            'max_message_size': self.max_message_size,
            'compression': self.compression,
            'subprotocols': self.subprotocols,
        }
        
        return cls


class OnConnect:
    """
    Handshake handler decorator.
    
    Called when connection is established (after auth).
    Can accept or reject connection by raising Fault.
    
    Example:
        @OnConnect()
        async def on_connect(self, conn: Connection):
            await conn.send_event("system.welcome", {"msg": "hi"})
    """
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'on_connect',
        }
        return func


class OnDisconnect:
    """
    Disconnect handler decorator.
    
    Called when connection is closed.
    
    Example:
        @OnDisconnect()
        async def on_disconnect(self, conn: Connection, reason: Optional[str]):
            await self.presence.leave(conn.identity.id)
    """
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'on_disconnect',
        }
        return func


class Event:
    """
    Message event handler decorator.
    
    Binds incoming event type to handler method.
    
    Example:
        @Event("message.send", schema=Schema({"room": str, "text": str}))
        async def handle_message(self, conn: Connection, payload):
            await self.publish_room(payload["room"], "message.receive", {...})
    """
    
    def __init__(
        self,
        event: str,
        *,
        schema: Optional[Schema] = None,
        ack: bool = False,
    ):
        """
        Initialize Event decorator.
        
        Args:
            event: Event name to handle
            schema: Optional payload schema for validation
            ack: Automatically send ack on success
        """
        self.event = event
        self.schema = schema
        self.ack = ack
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'event',
            'event': self.event,
            'schema': self.schema,
            'ack': self.ack,
        }
        return func


class AckEvent:
    """
    Acknowledgement-enabled event handler.
    
    Automatically sends ack on completion.
    
    Example:
        @AckEvent("data.request")
        async def handle_data_request(self, conn: Connection, payload):
            data = await self.fetch_data(payload["id"])
            return {"data": data}  # Sent as ack payload
    """
    
    def __init__(
        self,
        event: str,
        *,
        schema: Optional[Schema] = None,
    ):
        """
        Initialize AckEvent decorator.
        
        Args:
            event: Event name
            schema: Optional payload schema
        """
        self.event = event
        self.schema = schema
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'event',
            'event': self.event,
            'schema': self.schema,
            'ack': True,
        }
        return func


class Subscribe:
    """
    Room subscription handler.
    
    Sugar for joining rooms.
    
    Example:
        @Subscribe("room.join")
        async def subscribe_room(self, conn: Connection, payload):
            room = payload["room"]
            await conn.join(room)
            await conn.send_event("room.joined", {"room": room})
    """
    
    def __init__(self, event: str, *, schema: Optional[Schema] = None):
        """
        Initialize Subscribe decorator.
        
        Args:
            event: Event name
            schema: Optional payload schema
        """
        self.event = event
        self.schema = schema
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'subscribe',
            'event': self.event,
            'schema': self.schema,
        }
        return func


class Unsubscribe:
    """
    Room unsubscription handler.
    
    Sugar for leaving rooms.
    
    Example:
        @Unsubscribe("room.leave")
        async def unsubscribe_room(self, conn: Connection, payload):
            room = payload["room"]
            await conn.leave(room)
            await conn.send_event("room.left", {"room": room})
    """
    
    def __init__(self, event: str, *, schema: Optional[Schema] = None):
        """
        Initialize Unsubscribe decorator.
        
        Args:
            event: Event name
            schema: Optional payload schema
        """
        self.event = event
        self.schema = schema
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'unsubscribe',
            'event': self.event,
            'schema': self.schema,
        }
        return func


class Guard:
    """
    Guard decorator for WebSocket handlers.
    
    Can be applied at class level or method level.
    
    Example:
        @Guard()
        async def auth_guard(self, conn: Connection):
            if not conn.identity:
                raise WS_AUTH_REQUIRED()
    """
    
    def __init__(self, *, priority: int = 50):
        """
        Initialize Guard decorator.
        
        Args:
            priority: Execution priority (lower = earlier)
        """
        self.priority = priority
    
    def __call__(self, func: F) -> F:
        """Attach metadata to method."""
        func.__socket_handler__ = {
            'type': 'guard',
            'priority': self.priority,
        }
        return func
