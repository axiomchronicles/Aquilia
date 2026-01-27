"""
WebSocket Faults - Structured error handling for WebSocket operations

Integrates with Aquilia's Fault system for consistent error handling.
"""

from aquilia.faults import Fault, FaultDomain, Severity

# Define WebSocket fault domain
FaultDomain.NETWORK = FaultDomain("network", "Network and WebSocket errors")


class SocketFault(Fault):
    """Base fault for WebSocket operations."""
    
    def __init__(
        self,
        code: str,
        message: str,
        severity: Severity = Severity.ERROR,
        retryable: bool = False,
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.NETWORK,
            severity=severity,
            retryable=retryable,
            **kwargs
        )


# Handshake faults

WS_HANDSHAKE_FAILED = lambda reason="": SocketFault(
    code="WS_HANDSHAKE_FAILED",
    message=f"WebSocket handshake failed: {reason}",
    severity=Severity.ERROR,
    retryable=False, metadata={'http_status': 400},
)

WS_AUTH_REQUIRED = lambda: SocketFault(
    code="WS_AUTH_REQUIRED",
    message="Authentication required for WebSocket connection",
    severity=Severity.WARN,
    retryable=True, metadata={'http_status': 401},
)

WS_FORBIDDEN = lambda reason="": SocketFault(
    code="WS_FORBIDDEN",
    message=f"WebSocket connection forbidden: {reason}",
    severity=Severity.WARN,
    retryable=False, metadata={'http_status': 403},
)

WS_ORIGIN_NOT_ALLOWED = lambda origin="": SocketFault(
    code="WS_ORIGIN_NOT_ALLOWED",
    message=f"Origin not allowed: {origin}",
    severity=Severity.WARN,
    retryable=False, metadata={'http_status': 403},
)

# Message faults

WS_MESSAGE_INVALID = lambda reason="": SocketFault(
    code="WS_MESSAGE_INVALID",
    message=f"Invalid message format: {reason}",
    severity=Severity.WARN,
    retryable=True, metadata={'ws_close_code': 1003},
)

WS_PAYLOAD_TOO_LARGE = lambda size=0, limit=0: SocketFault(
    code="WS_PAYLOAD_TOO_LARGE",
    message=f"Payload too large: {size} bytes (limit: {limit})",
    severity=Severity.WARN,
    retryable=True, metadata={'ws_close_code': 1009},
)

WS_UNSUPPORTED_EVENT = lambda event="": SocketFault(
    code="WS_UNSUPPORTED_EVENT",
    message=f"Unsupported event type: {event}",
    severity=Severity.WARN,
    retryable=True,
)

# Connection faults

WS_CONNECTION_CLOSED = lambda reason="": SocketFault(
    code="WS_CONNECTION_CLOSED",
    message=f"Connection closed: {reason}",
    severity=Severity.INFO,
    retryable=False, metadata={'ws_close_code': 1000},
)

WS_CONNECTION_TIMEOUT = lambda: SocketFault(
    code="WS_CONNECTION_TIMEOUT",
    message="Connection timeout",
    severity=Severity.WARN,
    retryable=False, metadata={'ws_close_code': 1001},
)

# Rate limiting & quotas

WS_RATE_LIMIT_EXCEEDED = lambda limit=0: SocketFault(
    code="WS_RATE_LIMIT_EXCEEDED",
    message=f"Rate limit exceeded: {limit} messages/sec",
    severity=Severity.WARN,
    retryable=True, metadata={'ws_close_code': 1008},
)

WS_QUOTA_EXCEEDED = lambda quota="": SocketFault(
    code="WS_QUOTA_EXCEEDED",
    message=f"Quota exceeded: {quota}",
    severity=Severity.WARN,
    retryable=True, metadata={'ws_close_code': 1008},
)

# Room/subscription faults

WS_ROOM_NOT_FOUND = lambda room="": SocketFault(
    code="WS_ROOM_NOT_FOUND",
    message=f"Room not found: {room}",
    severity=Severity.WARN,
    retryable=True,
)

WS_ROOM_FULL = lambda room="", capacity=0: SocketFault(
    code="WS_ROOM_FULL",
    message=f"Room full: {room} (capacity: {capacity})",
    severity=Severity.WARN,
    retryable=True,
)

WS_ALREADY_SUBSCRIBED = lambda room="": SocketFault(
    code="WS_ALREADY_SUBSCRIBED",
    message=f"Already subscribed to room: {room}",
    severity=Severity.INFO,
    retryable=True,
)

WS_NOT_SUBSCRIBED = lambda room="": SocketFault(
    code="WS_NOT_SUBSCRIBED",
    message=f"Not subscribed to room: {room}",
    severity=Severity.WARN,
    retryable=True,
)

# Adapter faults

WS_ADAPTER_UNAVAILABLE = lambda adapter="": SocketFault(
    code="WS_ADAPTER_UNAVAILABLE",
    message=f"Adapter unavailable: {adapter}",
    severity=Severity.CRITICAL,
    retryable=False,
)

WS_PUBLISH_FAILED = lambda reason="": SocketFault(
    code="WS_PUBLISH_FAILED",
    message=f"Failed to publish message: {reason}",
    severity=Severity.ERROR,
    retryable=True,
)
