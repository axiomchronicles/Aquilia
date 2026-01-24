# AquilaSessions - Quick Start Guide

**Version:** 0.1.0  
**Status:** Production Ready (Core Implementation)

## Overview

AquilaSessions provides **explicit, policy-driven session management** for Aquilia applications. Unlike framework magic, sessions are explicit capabilities that you inject where needed.

### Core Philosophy

1. **Sessions are capabilities** - Explicit resources, not ambient authority
2. **Sessions are explicit** - No hidden cookies, declare what you need
3. **Sessions are policy-driven** - Behavior configured, not hardcoded
4. **Sessions are observable** - All mutations emit events
5. **Sessions are transport-agnostic** - Work across HTTP, WebSocket, future protocols

---

## Installation

AquilaSessions is included in Aquilia 0.2.0+:

```bash
pip install aquilia>=0.2.0
```

---

## 5-Minute Quick Start

### Step 1: Define Session Policy

```python
from datetime import timedelta
from aquilia.sessions import SessionPolicy, PersistencePolicy, TransportPolicy

# User session: 7 days, cookie-based
user_policy = SessionPolicy(
    name="user_default",
    ttl=timedelta(days=7),
    idle_timeout=timedelta(minutes=30),
    rotate_on_privilege_change=True,
    persistence=PersistencePolicy(
        enabled=True,
        store_name="memory",
    ),
    transport=TransportPolicy(
        adapter="cookie",
        cookie_httponly=True,
        cookie_secure=True,
        cookie_samesite="lax",
    ),
)
```

### Step 2: Create Session Engine

```python
from aquilia.sessions import SessionEngine, MemoryStore, CookieTransport

# Create storage backend
store = MemoryStore(max_sessions=10000)

# Create transport adapter
transport = CookieTransport(user_policy.transport)

# Create session engine
engine = SessionEngine(
    policy=user_policy,
    store=store,
    transport=transport,
)
```

### Step 3: Use Sessions in Handlers

```python
from aquilia import flow, Response
from aquilia.sessions import Session, SessionPrincipal

@flow("/").GET
async def index(session: Session):
    """Session automatically injected by DI."""
    return Response.json({
        "authenticated": session.is_authenticated,
        "user_id": session.principal.id if session.principal else None,
    })

@flow("/login").POST
async def login(request, session: Session):
    """Authenticate and mark session."""
    data = await request.json()
    
    # Your authentication logic here
    user = authenticate(data["email"], data["password"])
    
    if user:
        principal = SessionPrincipal(
            kind="user",
            id=user["id"],
            attributes={"name": user["name"]},
        )
        session.mark_authenticated(principal)
        
        return Response.json({"message": "Logged in"})
    
    return Response.json({"error": "Invalid credentials"}, status=401)

@flow("/profile").GET
async def profile(session: Session):
    """Access session data."""
    if not session.is_authenticated:
        return Response.json({"error": "Unauthorized"}, status=401)
    
    return Response.json({
        "user": session.principal.id,
        "name": session.principal.get_attribute("name"),
    })

@flow("/logout").POST
async def logout(session: Session):
    """Clear session."""
    session.clear_authentication()
    session.clear_data()
    
    return Response.json({"message": "Logged out"})
```

### Step 4: Add Middleware

```python
class SessionMiddleware:
    """Integrates session lifecycle with requests."""
    
    def __init__(self, engine: SessionEngine):
        self.engine = engine
    
    async def __call__(self, request, call_next):
        # Resolve session at request start
        session = await self.engine.resolve(request, container=None)
        request.state["session"] = session
        
        # Process request
        privilege_before = session.is_authenticated
        response = await call_next(request)
        privilege_after = session.is_authenticated
        
        # Commit session at request end
        await self.engine.commit(
            session,
            response,
            privilege_changed=(privilege_before != privilege_after)
        )
        
        return response

# Add to app
app.middleware(SessionMiddleware(engine))
```

---

## Common Patterns

### Store Cart Data

```python
@flow("/cart/add").POST
async def add_to_cart(request, session: Session):
    data = await request.json()
    
    cart = session.data.get("cart", {})
    cart[data["item_id"]] = data["quantity"]
    session.data["cart"] = cart
    
    return Response.json({"cart": cart})
```

### Check Authentication

```python
async def require_auth(session: Session):
    """Dependency that requires authentication."""
    if not session.is_authenticated:
        raise HTTPException(401, "Authentication required")
    return session
```

### Access User Info

```python
@flow("/me").GET
async def current_user(session: Session):
    if not session.is_authenticated:
        return Response.json({"error": "Unauthorized"}, status=401)
    
    return Response.json({
        "id": session.principal.id,
        "kind": session.principal.kind.value,
        "attributes": session.principal.attributes,
    })
```

### Track Session Activity

```python
# Register event handler
def log_session_events(event_data):
    print(f"[SESSION] {event_data['event']}: {event_data.get('principal_id')}")

engine.on_event(log_session_events)
```

---

## Built-in Session Policies

### 1. User Sessions (Default)

```python
from aquilia.sessions import DEFAULT_USER_POLICY

# 7 days TTL, 30 min idle, cookie-based
engine = SessionEngine(
    policy=DEFAULT_USER_POLICY,
    store=MemoryStore(),
    transport=CookieTransport(DEFAULT_USER_POLICY.transport),
)
```

### 2. API Token Sessions

```python
from aquilia.sessions import API_TOKEN_POLICY

# 1 hour TTL, header-based, no concurrency limit
engine = SessionEngine(
    policy=API_TOKEN_POLICY,
    store=MemoryStore(),
    transport=HeaderTransport(API_TOKEN_POLICY.transport),
)
```

### 3. Ephemeral Sessions

```python
from aquilia.sessions import EPHEMERAL_POLICY

# No persistence, request-scoped
engine = SessionEngine(
    policy=EPHEMERAL_POLICY,
    store=MemoryStore(),
    transport=CookieTransport(EPHEMERAL_POLICY.transport),
)
```

---

## Storage Backends

### Memory Store (Single Server)

```python
from aquilia.sessions import MemoryStore

store = MemoryStore(
    max_sessions=10000,  # LRU eviction when full
)

# Get stats
stats = store.get_stats()
print(f"Sessions: {stats['total_sessions']}")
```

### File Store (Development)

```python
from aquilia.sessions import FileStore

store = FileStore(
    directory="/tmp/sessions",  # One file per session
)
```

### Redis Store (Production - Coming Soon)

```python
# Future implementation
from aquilia.sessions import RedisStore

store = RedisStore(
    redis_url="redis://localhost:6379",
    key_prefix="sess:",
)
```

---

## Transport Adapters

### Cookie Transport (Web Apps)

```python
from aquilia.sessions import CookieTransport, TransportPolicy

transport = CookieTransport(TransportPolicy(
    adapter="cookie",
    cookie_name="session_id",
    cookie_httponly=True,   # XSS protection
    cookie_secure=True,     # HTTPS only
    cookie_samesite="lax",  # CSRF protection
    cookie_path="/",
    cookie_domain=None,     # Current domain
))
```

### Header Transport (APIs)

```python
from aquilia.sessions import HeaderTransport, TransportPolicy

transport = HeaderTransport(TransportPolicy(
    adapter="header",
    header_name="X-Session-ID",
))
```

---

## Security Best Practices

### 1. Always Use HTTPS in Production

```python
transport = CookieTransport(TransportPolicy(
    cookie_secure=True,  # Cookies only over HTTPS
))
```

### 2. Rotate Sessions on Privilege Change

```python
policy = SessionPolicy(
    rotate_on_privilege_change=True,  # New ID on login/logout
)
```

### 3. Set Idle Timeout

```python
policy = SessionPolicy(
    idle_timeout=timedelta(minutes=30),  # Expire inactive sessions
)
```

### 4. Limit Concurrent Sessions

```python
from aquilia.sessions import ConcurrencyPolicy

policy = SessionPolicy(
    concurrency=ConcurrencyPolicy(
        max_sessions_per_principal=5,      # Max 5 sessions per user
        behavior_on_limit="evict_oldest",   # Evict oldest on limit
    ),
)
```

### 5. Use HttpOnly Cookies

```python
transport = CookieTransport(TransportPolicy(
    cookie_httponly=True,  # Prevent JavaScript access
))
```

---

## Troubleshooting

### Session Not Persisting

**Problem:** Session data lost after request

**Solution:** Check policy persistence enabled:

```python
policy = SessionPolicy(
    persistence=PersistencePolicy(enabled=True),  # Must be True
)
```

### Session Expired Immediately

**Problem:** Session expires too quickly

**Solution:** Check TTL and idle timeout:

```python
policy = SessionPolicy(
    ttl=timedelta(days=7),           # Total lifetime
    idle_timeout=timedelta(minutes=30),  # Inactivity timeout
)
```

### Cookie Not Set

**Problem:** No session cookie in response

**Solution:** Ensure middleware commits session:

```python
await engine.commit(session, response)
```

### Session Not Injected

**Problem:** `session: Session` parameter not working

**Solution:** Register SessionMiddleware and ensure DI integration:

```python
app.middleware(SessionMiddleware(engine))
```

---

## Next Steps

- **[Full Documentation](AQUILA_SESSIONS_DESIGN.md)** - Complete architecture and design
- **[Examples](../examples/sessions_demo.py)** - Working demo application
- **[Integration Guide](AQUILA_SESSIONS_INTEGRATION.md)** - DI, Flow, Config integration
- **[API Reference](AQUILA_SESSIONS_API.md)** - Complete API documentation

---

## FAQ

**Q: Are sessions stored in memory?**  
A: By default, MemoryStore is used. For production multi-server deployments, use RedisStore (coming soon).

**Q: Can I use multiple session policies?**  
A: Yes! Create multiple SessionEngines with different policies and use them in different routes.

**Q: Are sessions secure?**  
A: Yes - 256-bit cryptographic IDs, HttpOnly cookies, rotation on privilege change, idle timeout enforcement.

**Q: Do sessions work with WebSocket?**  
A: Yes - implement WebSocketTransport adapter (coming soon). Architecture is transport-agnostic.

**Q: Can I customize session storage?**  
A: Yes - implement the `SessionStore` protocol with your own backend (database, Redis, etc.).

---

## Status

| Component | Status | Production Ready |
|-----------|--------|------------------|
| Core Types | ✅ Complete | Yes |
| Session Policy | ✅ Complete | Yes |
| Session Faults | ✅ Complete | Yes |
| MemoryStore | ✅ Complete | Yes (single server) |
| FileStore | ✅ Complete | No (dev only) |
| CookieTransport | ✅ Complete | Yes |
| HeaderTransport | ✅ Complete | Yes |
| SessionEngine | ✅ Complete | Yes |
| DI Integration | ⏳ In Progress | Partial |
| Flow Integration | ⏳ In Progress | Partial |
| Config Integration | 📝 Planned | No |
| RedisStore | 📝 Planned | No |
| WebSocketTransport | 📝 Planned | No |

---

**Ready to build?** Start with the [demo application](../examples/sessions_demo.py) and explore the [full design document](AQUILA_SESSIONS_DESIGN.md).
