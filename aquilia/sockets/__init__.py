"""
AquilaSockets - WebSocket subsystem for Aquilia

Production-grade WebSocket support with:
- Manifest-first & zero import-time effects
- Controller-based declarative syntax
- DI scoped containers per connection
- Auth-first handshake & per-message guards
- Horizontal scaling via adapters (Redis, NATS, Kafka)
- Backpressure & flow control
- Observability & audit
- Secure defaults

Philosophy:
- WebSocket controllers are compiled at build time
- Each connection has its own DI scope
- Messages are typed and validated
- Rooms/namespaces for pub/sub semantics
- Adapter-driven for scale-out
"""

__version__ = "0.1.0"

from .controller import (
    SocketController,
)

from .connection import (
    Connection,
    ConnectionState,
    ConnectionScope,
)

from .decorators import (
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AckEvent,
    Subscribe,
    Unsubscribe,
    Guard,
)

from .envelope import (
    MessageEnvelope,
    MessageType,
    MessageCodec,
    JSONCodec,
    Schema,
)

from .runtime import (
    AquilaSockets,
    SocketRouter,
)

from .adapters import (
    Adapter,
    InMemoryAdapter,
    RedisAdapter,
)

from .guards import (
    SocketGuard,
    HandshakeAuthGuard,
    OriginGuard,
    MessageAuthGuard,
    RateLimitGuard,
)

from .faults import (
    SocketFault,
    WS_HANDSHAKE_FAILED,
    WS_AUTH_REQUIRED,
    WS_MESSAGE_INVALID,
    WS_ROOM_FULL,
    WS_RATE_LIMIT_EXCEEDED,
    WS_CONNECTION_CLOSED,
    WS_PAYLOAD_TOO_LARGE,
)

from .middleware import (
    SocketMiddleware,
    MessageValidationMiddleware,
    RateLimitMiddleware,
)

__all__ = [
    # Core
    "SocketController",
    "Connection",
    
    # Decorators
    "Socket",
    "OnConnect",
    "OnDisconnect",
    "Event",
    "AckEvent",
    "Subscribe",
    "Unsubscribe",
    "Guard",
    
    # Envelope
    "MessageEnvelope",
    "MessageType",
    "MessageCodec",
    "JSONCodec",
    "Schema",
    
    # Connection
    "ConnectionState",
    "ConnectionScope",
    
    # Runtime
    "AquilaSockets",
    "SocketRouter",
    
    # Adapters
    "Adapter",
    "InMemoryAdapter",
    "RedisAdapter",
    
    # Guards
    "SocketGuard",
    "HandshakeAuthGuard",
    "OriginGuard",
    "MessageAuthGuard",
    "RateLimitGuard",
    
    # Faults
    "SocketFault",
    "WS_HANDSHAKE_FAILED",
    "WS_AUTH_REQUIRED",
    "WS_MESSAGE_INVALID",
    "WS_ROOM_FULL",
    "WS_RATE_LIMIT_EXCEEDED",
    "WS_CONNECTION_CLOSED",
    "WS_PAYLOAD_TOO_LARGE",
    
    # Middleware
    "SocketMiddleware",
    "MessageValidationMiddleware",
    "RateLimitMiddleware",
]
