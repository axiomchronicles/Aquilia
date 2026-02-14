"""
Message Envelope - Typed message protocol for WebSocket communication

Provides:
- Structured message envelope (JSON default)
- Message validation and schema support
- Codec abstraction (JSON, MessagePack, etc.)
- Ack semantics
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import json
import uuid


class MessageType(str, Enum):
    """Message type discriminator."""
    EVENT = "event"           # Regular event message
    ACK = "ack"               # Acknowledgement response
    SYSTEM = "system"         # System control message
    CONTROL = "control"       # Connection control (ping, pong)


@dataclass
class MessageEnvelope:
    """
    Standard message envelope for WebSocket communication.
    
    Format:
    {
        "id": "uuid-v4",          // optional - for ack/trace
        "type": "event",          // "event" | "ack" | "system" | "control"
        "event": "message.send",  // event name
        "payload": { ... },       // event data
        "meta": {
            "ts": 1670000000,     // timestamp
            "trace_id": "..."     // optional trace ID
        },
        "ack": true|false         // request ack
    }
    """
    
    type: MessageType
    event: str
    payload: Dict[str, Any]
    id: Optional[str] = None
    ack: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure meta has timestamp."""
        if "ts" not in self.meta:
            self.meta["ts"] = int(datetime.now(timezone.utc).timestamp())
        
        if self.ack and not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "event": self.event,
            "payload": self.payload,
            "meta": self.meta,
            "ack": self.ack,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageEnvelope:
        """Deserialize from dictionary.
        
        Accepts both protocol format (``payload``) and simplified
        client format (``data``) so that browser clients sending
        ``{"event": "...", "data": {...}}`` are handled correctly.
        """
        # Accept both 'payload' (protocol) and 'data' (client shorthand)
        payload = data.get("payload") or data.get("data", {})
        return cls(
            id=data.get("id"),
            type=MessageType(data.get("type", "event")),
            event=data["event"],
            payload=payload,
            meta=data.get("meta", {}),
            ack=data.get("ack", False),
        )
    
    def create_ack(
        self,
        status: str = "ok",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> MessageEnvelope:
        """Create acknowledgement response."""
        return MessageEnvelope(
            id=self.id,
            type=MessageType.ACK,
            event=f"{self.event}.ack",
            payload={
                "status": status,
                "data": data or {},
                "error": error,
                "original_id": self.id,
            },
            ack=False,
            meta={
                "ts": int(datetime.now(timezone.utc).timestamp()),
                "trace_id": self.meta.get("trace_id"),
            },
        )


@dataclass
class AckEnvelope:
    """Acknowledgement message."""
    id: str
    status: str  # "ok" | "error"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    original_id: Optional[str] = None
    
    def to_envelope(self, event: str = "ack") -> MessageEnvelope:
        """Convert to message envelope."""
        return MessageEnvelope(
            id=self.id,
            type=MessageType.ACK,
            event=event,
            payload={
                "status": self.status,
                "data": self.data or {},
                "error": self.error,
                "original_id": self.original_id,
            },
        )


# Schema validation

class Schema:
    """
    Simple schema validator for message payloads.
    
    Example:
        schema = Schema({
            "room": str,
            "text": (str, lambda s: len(s) < 1000),
            "priority": (int, {"min": 0, "max": 10}),
        })
    """
    
    def __init__(self, spec: Dict[str, Any]):
        """
        Initialize schema.
        
        Args:
            spec: Schema specification
                - key: field name
                - value: type or (type, constraints)
        """
        self.spec = spec
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate data against schema.
        
        Returns:
            (is_valid, error_message)
        """
        for field, field_spec in self.spec.items():
            # Required field check
            if field not in data:
                return False, f"Missing required field: {field}"
            
            value = data[field]
            
            # Type check
            if isinstance(field_spec, type):
                expected_type = field_spec
                if not isinstance(value, expected_type):
                    return False, f"Field {field}: expected {expected_type.__name__}, got {type(value).__name__}"
            
            # Type with constraints
            elif isinstance(field_spec, tuple):
                expected_type, constraints = field_spec
                
                if not isinstance(value, expected_type):
                    return False, f"Field {field}: expected {expected_type.__name__}, got {type(value).__name__}"
                
                # Callable constraint
                if callable(constraints):
                    if not constraints(value):
                        return False, f"Field {field}: validation failed"
                
                # Dict constraints
                elif isinstance(constraints, dict):
                    if expected_type == int or expected_type == float:
                        if "min" in constraints and value < constraints["min"]:
                            return False, f"Field {field}: must be >= {constraints['min']}"
                        if "max" in constraints and value > constraints["max"]:
                            return False, f"Field {field}: must be <= {constraints['max']}"
                    
                    if expected_type == str:
                        if "min_length" in constraints and len(value) < constraints["min_length"]:
                            return False, f"Field {field}: must be >= {constraints['min_length']} chars"
                        if "max_length" in constraints and len(value) > constraints["max_length"]:
                            return False, f"Field {field}: must be <= {constraints['max_length']} chars"
        
        return True, None


# Message codecs

class MessageCodec(Protocol):
    """Protocol for message encoding/decoding."""
    
    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode envelope to bytes."""
        ...
    
    def decode(self, data: bytes) -> MessageEnvelope:
        """Decode bytes to envelope."""
        ...


class JSONCodec:
    """JSON message codec."""
    
    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode envelope to JSON bytes."""
        return json.dumps(envelope.to_dict()).encode("utf-8")
    
    def decode(self, data: bytes) -> MessageEnvelope:
        """Decode JSON bytes to envelope."""
        obj = json.loads(data.decode("utf-8"))
        return MessageEnvelope.from_dict(obj)


class MsgPackCodec:
    """MessagePack codec for efficient binary encoding."""
    
    def __init__(self):
        try:
            import msgpack
            self.msgpack = msgpack
        except ImportError:
            raise ImportError("msgpack-python is required for MsgPackCodec")
    
    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode envelope to MessagePack bytes."""
        return self.msgpack.packb(envelope.to_dict())
    
    def decode(self, data: bytes) -> MessageEnvelope:
        """Decode MessagePack bytes to envelope."""
        obj = self.msgpack.unpackb(data, raw=False)
        return MessageEnvelope.from_dict(obj)
