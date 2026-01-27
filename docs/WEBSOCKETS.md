# AquilaSockets - WebSocket Subsystem for Aquilia

**Production-grade WebSocket support with manifest-first design, DI integration, and horizontal scaling.**

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Controller Syntax](#controller-syntax)
5. [Connection Lifecycle](#connection-lifecycle)
6. [Message Protocol](#message-protocol)
7. [Rooms & Broadcasting](#rooms--broadcasting)
8. [Authentication & Authorization](#authentication--authorization)
9. [Scaling with Adapters](#scaling-with-adapters)
10. [Middleware & Guards](#middleware--guards)
11. [Compilation & Artifacts](#compilation--artifacts)
12. [CLI Tools](#cli-tools)
13. [Client SDK](#client-sdk)
14. [Security](#security)
15. [Performance & Tuning](#performance--tuning)
16. [Examples](#examples)

---

## Overview

AquilaSockets extends Aquilia's manifest-first, controller-based architecture to WebSocket connections with:

- **Declarative Controller Syntax**: Class-based controllers with decorators (@Socket, @Event, @OnConnect)
- **Manifest-First & Zero Import-Time Effects**: Controllers are compiled at build time (`aq compile`)
- **Deep DI Integration**: Each connection has its own request-scoped DI container
- **Auth-First**: Handshake authentication via tokens/cookies, optional per-message auth
- **Horizontal Scaling**: Redis/NATS/Kafka adapters for multi-worker deployments
- **Rooms & Presence**: Built-in pub/sub semantics for group messaging
- **Backpressure & Flow Control**: Rate limiting, buffering, and quota enforcement
- **Observability**: Metrics, traces, and audit events
- **Type Safety**: Schema validation for messages with compile-time checks

---

## Quick Start

### 1. Create a WebSocket Controller

```python
# modules/chat/controllers.py
from aquilia.sockets import (
    SocketController, Socket, OnConnect, OnDisconnect, Event,
    Connection, Schema
)
from aquilia.di import Inject

@Socket("/chat/:namespace")
class ChatSocket(SocketController):
    def __init__(self, presence=Inject(tag="presence")):
        self.presence = presence
    
    @OnConnect()
    async def on_connect(self, conn: Connection):
        await conn.send_event("system.welcome", {
            "msg": f"Welcome {conn.identity.id}"
        })
    
    @Event("message.send", schema=Schema({
        "room": str,
        "text": (str, {"max_length": 1000})
    }))
    async def handle_message(self, conn: Connection, payload):
        room = payload["room"]
        await self.publish_room(room, "message.receive", {
            "from": conn.identity.id,
            "text": payload["text"]
        })
    
    @OnDisconnect()
    async def cleanup(self, conn: Connection, reason: Optional[str]):
        await self.presence.leave(conn.identity.id)
```

### 2. Register in Manifest

```python
# workspace.py or module manifest
from aquilia.manifest import AppManifest
from modules.chat.controllers import ChatSocket

manifest = AppManifest(
    name="chat",
    controllers=[ChatSocket],
    websockets={
        "adapter": "redis",  # or "inmemory" for dev
        "redis_url": "redis://localhost:6379"
    }
)
```

### 3. Compile

```bash
aq compile
# Generates artifacts/ws.crous
```

### 4. Run Server

```bash
aq serve
# WebSocket available at ws://localhost:8000/chat/:namespace
```

### 5. Connect from Client

```javascript
const ws = new WebSocket("ws://localhost:8000/chat/general?token=YOUR_TOKEN");

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: "event",
        event: "message.send",
        payload: { room: "general", text: "Hello!" }
    }));
};

ws.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    console.log(`Event: ${envelope.event}`, envelope.payload);
};
```

---

## Core Concepts

### Namespaces

Namespaces are WebSocket endpoints defined by path patterns:

```python
@Socket("/chat/:namespace")  # Matches /chat/general, /chat/support, etc.
@Socket("/notifications")    # Matches /notifications exactly
```

### Controllers

Controllers are classes that handle WebSocket connections:

- **One controller per namespace**
- **DI injection via constructor**
- **Lifecycle hooks**: `@OnConnect`, `@OnDisconnect`
- **Message handlers**: `@Event`, `@Subscribe`, `@Unsubscribe`

### Connections

Each WebSocket connection is represented by a `Connection` object:

- Unique connection ID
- Request-scoped DI container
- Authenticated identity (from handshake)
- Session (if enabled)
- Room subscriptions
- State dictionary

### Messages

Messages follow a structured envelope format:

```json
{
  "id": "uuid-v4",
  "type": "event",
  "event": "message.send",
  "payload": { "room": "general", "text": "hi" },
  "meta": { "ts": 1670000000 },
  "ack": false
}
```

---

## Controller Syntax

### @Socket - Declare Namespace

```python
@Socket(
    "/chat/:namespace",
    allowed_origins=["https://example.com"],
    max_connections=1000,
    message_rate_limit=10,  # messages/sec per connection
    max_message_size=65536,  # 64KB
    compression=True,
)
class ChatSocket(SocketController):
    pass
```

### @OnConnect - Handshake Handler

```python
@OnConnect()
async def on_connect(self, conn: Connection):
    # Called after successful handshake
    # Can accept or reject by raising Fault
    
    await conn.send_event("welcome", {"user": conn.identity.id})
```

### @OnDisconnect - Cleanup Handler

```python
@OnDisconnect()
async def on_disconnect(self, conn: Connection, reason: Optional[str]):
    # Called when connection closes
    # Clean up resources, notify others, etc.
    
    await self.presence.remove(conn.identity.id)
```

### @Event - Message Handler

```python
@Event("message.send", schema=Schema({
    "room": str,
    "text": (str, {"min_length": 1, "max_length": 1000})
}))
async def handle_message(self, conn: Connection, payload):
    # payload is validated against schema
    room = payload["room"]
    text = payload["text"]
    
    await self.publish_room(room, "message.receive", {
        "from": conn.identity.id,
        "text": text
    })
```

### @AckEvent - Acknowledgement Handler

```python
@AckEvent("data.request", schema=Schema({"id": str}))
async def handle_data_request(self, conn: Connection, payload):
    data = await self.fetch_data(payload["id"])
    
    # Return value is sent as ack payload
    return {"data": data}
```

### @Subscribe / @Unsubscribe - Room Handlers

```python
@Subscribe("room.join")
async def join_room(self, conn: Connection, payload):
    room = payload["room"]
    await conn.join(room)
    await conn.send_event("room.joined", {"room": room})

@Unsubscribe("room.leave")
async def leave_room(self, conn: Connection, payload):
    room = payload["room"]
    await conn.leave(room)
    await conn.send_event("room.left", {"room": room})
```

### @Guard - Security Guards

```python
@Guard(priority=10)
async def auth_guard(self, conn: Connection):
    if not conn.identity:
        raise WS_AUTH_REQUIRED()
    
    if not conn.identity.has_role("user"):
        raise WS_FORBIDDEN("Insufficient permissions")
```

---

## Connection Lifecycle

1. **HTTP Upgrade**: Client sends WebSocket upgrade request
2. **Handshake**: 
   - Route matching
   - Authentication (token/cookie/session)
   - Origin validation
   - Guard execution
3. **Accept**: Connection accepted, DI container created
4. **@OnConnect**: Controller's on_connect handler called
5. **Message Loop**: Process incoming messages
6. **Disconnect**: Client or server closes connection
7. **@OnDisconnect**: Cleanup handler called
8. **Teardown**: Rooms left, DI container disposed

### DI Container Lifecycle

Each connection gets a **request-scoped DI container**:

```python
@Socket("/chat/:namespace")
class ChatSocket(SocketController):
    def __init__(
        self,
        db=Inject(tag="db"),
        cache=Inject(tag="cache", scope="request")
    ):
        self.db = db      # Shared across connections
        self.cache = cache  # Per-connection instance
```

Container is automatically disposed on disconnect.

---

## Message Protocol

### Message Types

- `event`: Regular event message
- `ack`: Acknowledgement response
- `system`: System control message
- `control`: Connection control (ping/pong)

### Sending Messages

```python
# Simple event
await conn.send_event("notification", {"msg": "New message"})

# Event with ack request
msg_id = await conn.send_event("data.request", {"id": "123"}, ack=True)

# Raw bytes
await conn.send_raw(binary_data)

# Manual ack
await conn.send_ack(message_id="msg123", status="ok", data={"result": "success"})
```

### Schema Validation

Schemas validate message payloads:

```python
Schema({
    "room": str,
    "text": (str, {"min_length": 1, "max_length": 1000}),
    "priority": (int, {"min": 0, "max": 10}),
})
```

Validation errors raise `WS_MESSAGE_INVALID` fault.

---

## Rooms & Broadcasting

### Joining Rooms

```python
# Join room
await conn.join("general")

# Check membership
if "general" in conn.rooms:
    print("In general room")

# Leave room
await conn.leave("general")

# Leave all rooms
await conn.leave_all()
```

### Publishing to Rooms

```python
# Publish to room (fanout to all members)
await self.publish_room("general", "message.receive", {
    "from": conn.identity.id,
    "text": "Hello everyone!"
})

# Broadcast to entire namespace
await self.broadcast("announcement", {
    "msg": "Server maintenance in 5 minutes"
}, exclude_connection=conn.connection_id)
```

### Room Membership

```python
# Get room members
members = await adapter.get_room_members(namespace, room)

# Get room info
info = await adapter.get_room_info(namespace, room)
print(f"Room: {info.room}, Members: {info.member_count}")

# List all rooms
rooms = await adapter.list_rooms(namespace)
```

---

## Authentication & Authorization

### Handshake Authentication

Multiple auth methods supported:

1. **Bearer Token** (Authorization header):
   ```javascript
   const ws = new WebSocket("ws://localhost:8000/chat/general", {
       headers: { Authorization: "Bearer YOUR_TOKEN" }
   });
   ```

2. **Query String Token**:
   ```javascript
   const ws = new WebSocket("ws://localhost:8000/chat/general?token=YOUR_TOKEN");
   ```

3. **Session Cookie** (automatic if session middleware enabled)

### Handshake Guards

```python
from aquilia.sockets import HandshakeAuthGuard, OriginGuard

@Socket(
    "/chat/:namespace",
    guards=[
        HandshakeAuthGuard(require_identity=True),
        OriginGuard(allowed_origins=["https://example.com"]),
    ]
)
class ChatSocket(SocketController):
    pass
```

### Per-Message Authorization

```python
@Guard(priority=10)
async def message_auth_guard(self, conn: Connection):
    # Validate identity hasn't been revoked
    if not await self.auth_manager.is_identity_valid(conn.identity):
        raise WS_FORBIDDEN("Identity revoked")
```

### Custom Guards

```python
class AdminGuard(SocketGuard):
    async def check_handshake(self, scope, identity, session):
        if not identity or not identity.has_role("admin"):
            raise WS_FORBIDDEN("Admin only")
        return True
```

---

## Scaling with Adapters

Adapters provide pub/sub for horizontal scaling across workers.

### InMemoryAdapter (Development)

```python
# Single-process, no external dependencies
from aquilia.sockets.adapters import InMemoryAdapter

adapter = InMemoryAdapter()
await adapter.initialize()
```

### RedisAdapter (Production)

```python
from aquilia.sockets.adapters import RedisAdapter

adapter = RedisAdapter(
    redis_url="redis://localhost:6379",
    prefix="aquilia:ws:",
    connection_ttl=300,
)
await adapter.initialize()
```

**Features:**
- Redis pub/sub for message fanout
- Sorted sets for room membership
- Automatic cleanup of stale connections
- Supports multi-worker deployments

### Custom Adapters

Implement the `Adapter` protocol:

```python
from aquilia.sockets.adapters import Adapter

class NATSAdapter(Adapter):
    async def publish(self, namespace, room, envelope):
        # Publish to NATS subject
        await self.nc.publish(f"{namespace}.{room}", envelope)
    
    # ... implement other methods
```

---

## Middleware & Guards

### Message Middleware

Process messages before handlers:

```python
from aquilia.sockets.middleware import MessageValidationMiddleware, RateLimitMiddleware

middleware_chain = MiddlewareChain()
middleware_chain.add(MessageValidationMiddleware(max_message_size=64*1024))
middleware_chain.add(RateLimitMiddleware(messages_per_second=10, burst=20))
```

### Custom Middleware

```python
class LoggingMiddleware:
    async def __call__(self, conn, envelope, next):
        logger.info(f"Message from {conn.identity.id}: {envelope.event}")
        result = await next(conn, envelope)
        return result
```

### Guards

Guards run at handshake or per-message:

- **Handshake Guards**: Run once at connection establishment
- **Message Guards**: Run for each message

```python
@Socket("/admin")
class AdminSocket(SocketController):
    @Guard(priority=5)
    async def admin_only(self, conn: Connection):
        if not conn.identity.has_role("admin"):
            raise WS_FORBIDDEN()
```

---

## Compilation & Artifacts

### Compile Controllers

```bash
aq compile
```

Generates `artifacts/ws.crous` containing:

```json
{
  "version": "1.0.0",
  "type": "websockets",
  "controllers": [
    {
      "class_name": "ChatSocket",
      "namespace": "/chat/:namespace",
      "events": [
        {
          "event": "message.send",
          "handler_name": "handle_message",
          "schema": { ... },
          "ack": false
        }
      ],
      "config": { ... }
    }
  ]
}
```

### Validate

```bash
aq validate
```

Checks for:
- Namespace conflicts
- Duplicate event handlers
- Schema errors
- Missing handlers

---

## CLI Tools

### Inspect Namespaces

```bash
aq ws inspect
# Shows all WebSocket namespaces and their events
```

### Broadcast Message (Admin)

```bash
aq ws broadcast \
    --namespace /chat \
    --room general \
    --event message.receive \
    --payload '{"text":"Server announcement"}'
```

### Kick Connection

```bash
aq ws kick --conn <connection-id> --reason "Violated rules"
```

### Purge Room

```bash
aq ws purge-room --namespace /chat --room spam-room
```

### Generate Client SDK

```bash
aq ws gen-client --lang ts --out clients/chat.ts
```

Generates TypeScript client with:
- Typed message payloads
- Type-safe send methods
- Event listeners

---

## Client SDK

### TypeScript Client (Generated)

```typescript
import { ChatSocketClient } from "./clients/chat";

const client = new ChatSocketClient("ws://localhost:8000/chat/general", "YOUR_TOKEN");

// Send message
client.messageSend({ room: "general", text: "Hello!" });

// Listen for events
client.onMessageReceive((payload) => {
    console.log(`${payload.from}: ${payload.text}`);
});

// Close connection
client.close();
```

### Manual Client (JavaScript)

```javascript
const ws = new WebSocket("ws://localhost:8000/chat/general?token=TOKEN");

ws.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    
    if (envelope.type === "event") {
        console.log(envelope.event, envelope.payload);
    }
};

ws.send(JSON.stringify({
    type: "event",
    event: "message.send",
    payload: { room: "general", text: "Hi!" }
}));
```

---

## Security

### Security Checklist

- [ ] Enable handshake authentication (`HandshakeAuthGuard`)
- [ ] Validate origins (`OriginGuard` or `allowed_origins`)
- [ ] Set message size limits (`max_message_size`)
- [ ] Enable rate limiting (`message_rate_limit` or middleware)
- [ ] Use TLS/WSS in production
- [ ] Validate all message payloads (schemas)
- [ ] Implement per-connection quotas
- [ ] Monitor for anomalies (message rate spikes)
- [ ] Audit connection events (artifacts/ws/audit/*.crous)

### Rate Limiting

Per-connection:
```python
@Socket("/chat", message_rate_limit=10)  # 10 msg/sec
```

Via middleware:
```python
RateLimitMiddleware(messages_per_second=10, burst=20)
```

### Message Size Limits

```python
@Socket("/chat", max_message_size=65536)  # 64KB
```

### Origin Validation

```python
@Socket("/chat", allowed_origins=[
    "https://example.com",
    "https://*.example.com"
])
```

---

## Performance & Tuning

### Connection Limits

```python
@Socket("/chat", max_connections=1000)
```

### Backpressure Strategies

Configure adapter for slow clients:

```python
# In manifest
websockets={
    "adapter": "redis",
    "backpressure": {
        "strategy": "buffer",  # "buffer" | "drop" | "disconnect"
        "buffer_size": 100,    # messages
    }
}
```

### Compression

```python
@Socket("/chat", compression=True)  # Per-message compression
```

### Metrics

Monitor:
- `ws.connections_active`
- `ws.messages_in_total`
- `ws.messages_out_total`
- `ws.messages_rejected_total`
- `ws.latency_ms`

---

## Examples

See `modules/chat/` for complete example:

- `controllers.py`: Chat controller with rooms and presence
- `client.html`: HTML/JS client

Run example:

```bash
cd /path/to/aquilia
aq compile
aq serve
# Open client.html in browser
```

---

## Integration with Aquilia Features

### DI Integration

```python
@Socket("/chat")
class ChatSocket(SocketController):
    def __init__(
        self,
        db=Inject(tag="db"),
        cache=Inject(tag="cache"),
        logger=Inject(tag="logger")
    ):
        self.db = db
        self.cache = cache
        self.logger = logger
```

### Session Integration

```python
@OnConnect()
async def on_connect(self, conn: Connection):
    if conn.session:
        user_id = conn.session.get("user_id")
        # Use session data
```

### Auth Integration

```python
@OnConnect()
async def on_connect(self, conn: Connection):
    if conn.identity:
        # Identity resolved from token/session
        roles = conn.identity.get_attribute("roles", [])
```

### Fault Integration

```python
from aquilia.sockets.faults import WS_AUTH_REQUIRED, WS_FORBIDDEN

@Event("admin.action")
async def admin_action(self, conn: Connection, payload):
    if not conn.identity.has_role("admin"):
        raise WS_FORBIDDEN("Admin role required")
```

---

## Next Steps

1. **Read Examples**: See `modules/chat/` for complete example
2. **Run Tests**: `pytest tests/test_websockets.py`
3. **Try Tutorial**: Follow quick start guide above
4. **Check API Reference**: See inline docstrings in code
5. **Join Community**: Ask questions in GitHub discussions

---

## API Reference

### Core Classes

- `SocketController`: Base controller class
- `Connection`: WebSocket connection abstraction
- `MessageEnvelope`: Message structure
- `Schema`: Payload validation

### Decorators

- `@Socket(path)`: Declare namespace
- `@OnConnect()`: Handshake handler
- `@OnDisconnect()`: Cleanup handler
- `@Event(name, schema)`: Message handler
- `@AckEvent(name)`: Ack-enabled handler
- `@Subscribe(event)`: Room subscription
- `@Unsubscribe(event)`: Room unsubscription
- `@Guard()`: Security guard

### Adapters

- `InMemoryAdapter`: Single-process
- `RedisAdapter`: Multi-worker with Redis

### Faults

- `WS_AUTH_REQUIRED`
- `WS_FORBIDDEN`
- `WS_ORIGIN_NOT_ALLOWED`
- `WS_MESSAGE_INVALID`
- `WS_PAYLOAD_TOO_LARGE`
- `WS_RATE_LIMIT_EXCEEDED`

---

**Version**: 0.1.0  
**License**: Same as Aquilia  
**Maintainer**: Aquilia Team
