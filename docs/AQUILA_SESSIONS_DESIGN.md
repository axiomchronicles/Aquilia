# AquilaSessions - Design Specification

## Philosophy & Core Principles

AquilaSessions is Aquilia's production-grade session management system built on these non-negotiable principles:

1. **Sessions are capabilities** - Grant scoped access to state and identity
2. **Sessions are explicit** - No hidden globals, no magic `request.session`
3. **Sessions are policy-driven** - Creation, renewal, persistence governed by declared policies
4. **Sessions are observable** - Every session mutation is auditable
5. **Sessions are transport-agnostic** - HTTP cookies are just one adapter

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Flow Handler                            │
│  async def handler(session: Session):                       │
│      session.data["count"] = session.data.get("count", 0)+1│
└────────────────────┬────────────────────────────────────────┘
                     │ (DI injection)
┌────────────────────▼────────────────────────────────────────┐
│                   SessionEngine                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Detection   │→ │  Resolution  │→ │  Validation  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Binding    │→ │   Mutation   │→ │    Commit    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────┬─────────────────────────────────────────┬──────────┘
        │                                         │
        ▼                                         ▼
┌───────────────┐                        ┌──────────────────┐
│SessionTransport│                       │  SessionStore    │
│ ┌───────────┐ │                        │ ┌──────────────┐ │
│ │  Cookie   │ │                        │ │   Memory     │ │
│ │  Header   │ │                        │ │   Redis      │ │
│ │  Token    │ │                        │ │   File       │ │
│ └───────────┘ │                        │ └──────────────┘ │
└───────────────┘                        └──────────────────┘
```

## Session Lifecycle (Deterministic)

### Phase 1: Detection
**Input:** Request (HTTP/WebSocket/etc.)  
**Action:** Extract session reference from transport  
**Output:** SessionID | None

```python
# Transport adapter extracts session ID
session_id = transport.extract(request)  # → "sess_abc123..." or None
```

### Phase 2: Resolution
**Input:** SessionID | None  
**Action:** Load from store or create new  
**Output:** Session

```python
if session_id:
    session = await store.load(session_id)
    if not session:
        emit_fault(SESSION_INVALID)
        session = await create_new_session(policy)
else:
    session = await create_new_session(policy)
```

### Phase 3: Validation
**Input:** Session  
**Action:** Check expiry, idle timeout, concurrency  
**Output:** Valid Session | Fault

```python
if session.is_expired():
    emit_fault(SESSION_EXPIRED)
    raise SessionExpiredFault()

if session.idle_timeout_exceeded():
    emit_fault(SESSION_IDLE_TIMEOUT)
    raise SessionIdleTimeoutFault()

if policy.concurrency.violated(session):
    emit_fault(SESSION_CONCURRENCY_VIOLATION)
    raise SessionConcurrencyFault()
```

### Phase 4: Binding
**Input:** Valid Session  
**Action:** Bind to request context and DI scope  
**Output:** Session available for injection

```python
# Store in request state
request.state["session"] = session

# Register in DI container (request scope)
await container.register_instance(Session, session)
```

### Phase 5: Mutation
**Input:** Bound Session  
**Action:** Handler reads/writes session.data  
**Output:** Modified Session (if touched)

```python
# Handler explicitly requests and mutates
async def handler(session: Session):
    session.data["user_id"] = 42
    session.data["last_action"] = "profile_view"
    # Session marked as dirty
```

### Phase 6: Commit
**Input:** Modified Session  
**Action:** Persist, rotate, or destroy per policy  
**Output:** Updated Session

```python
if session.is_dirty:
    if policy.rotate_on_use:
        old_id = session.id
        session = await rotate_session(session)
        await store.delete(old_id)
    
    await store.save(session)
    emit_event("session_committed", session)
```

### Phase 7: Emission
**Input:** Committed Session  
**Action:** Transport writes updated reference  
**Output:** Response with session cookie/header

```python
transport.inject(response, session)
# → Set-Cookie: session=sess_xyz789; HttpOnly; Secure
```

## Core Types

### Session (Core Data Object)

```python
@dataclass
class Session:
    """
    Core session object - explicit state container with lifecycle.
    
    Sessions are NOT implicit cookies. They are explicit capabilities
    that grant scoped access to state and identity.
    """
    id: SessionID              # Opaque, cryptographically random
    principal: SessionPrincipal | None  # Who owns this session
    data: dict[str, Any]       # Application state (mutable)
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime | None
    scope: SessionScope        # REQUEST | CONNECTION | USER | DEVICE
    flags: set[SessionFlag]    # AUTHENTICATED, EPHEMERAL, ROTATABLE, etc.
    version: int = 0           # Optimistic concurrency control
    
    # Internal tracking
    _dirty: bool = False       # Has data been modified?
    _policy_name: str = ""     # Which policy governs this session
    
    def is_expired(self) -> bool:
        """Check if session has passed expiry."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def idle_timeout_exceeded(self, policy: SessionPolicy) -> bool:
        """Check if idle timeout exceeded."""
        if not policy.idle_timeout:
            return False
        idle_duration = datetime.utcnow() - self.last_accessed_at
        return idle_duration >= policy.idle_timeout
    
    def touch(self) -> None:
        """Mark session as accessed (updates last_accessed_at)."""
        self.last_accessed_at = datetime.utcnow()
        self._dirty = True
    
    def mark_authenticated(self, principal: SessionPrincipal) -> None:
        """Bind principal and mark as authenticated."""
        self.principal = principal
        self.flags.add(SessionFlag.AUTHENTICATED)
        self._dirty = True
    
    def clear_authentication(self) -> None:
        """Remove authentication."""
        self.principal = None
        self.flags.discard(SessionFlag.AUTHENTICATED)
        self._dirty = True
    
    @property
    def is_authenticated(self) -> bool:
        """Check if session has authenticated principal."""
        return SessionFlag.AUTHENTICATED in self.flags
    
    @property
    def is_dirty(self) -> bool:
        """Check if session needs persistence."""
        return self._dirty
```

### SessionID (Opaque Identifier)

```python
class SessionID:
    """
    Opaque session identifier.
    
    Rules:
    - Never encode meaning (no user ID, no timestamps)
    - Cryptographically random (32+ bytes entropy)
    - URL-safe encoding
    - Prefixed for identification (sess_)
    """
    def __init__(self, raw: bytes | None = None):
        if raw is None:
            raw = secrets.token_bytes(32)
        self._raw = raw
        self._encoded = f"sess_{base64.urlsafe_b64encode(raw).decode().rstrip('=')}"
    
    def __str__(self) -> str:
        return self._encoded
    
    def __repr__(self) -> str:
        return f"SessionID({self._encoded[:16]}...)"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SessionID):
            return False
        return self._raw == other._raw
    
    def __hash__(self) -> int:
        return hash(self._raw)
    
    @classmethod
    def from_string(cls, encoded: str) -> "SessionID":
        """Parse from encoded string."""
        if not encoded.startswith("sess_"):
            raise ValueError("Invalid session ID format")
        
        raw_b64 = encoded[5:]
        # Add padding if needed
        padding = 4 - (len(raw_b64) % 4)
        if padding != 4:
            raw_b64 += "=" * padding
        
        raw = base64.urlsafe_b64decode(raw_b64)
        return cls(raw)
```

### SessionPrincipal (Identity Binding)

```python
@dataclass
class SessionPrincipal:
    """
    Represents who the session belongs to.
    
    A session may exist without a principal (anonymous).
    Principal binding is explicit and auditable.
    """
    kind: Literal["user", "service", "device", "anonymous"]
    id: str                     # Unique identifier within kind
    attributes: dict[str, Any]  # Additional claims/metadata
    
    def is_user(self) -> bool:
        return self.kind == "user"
    
    def is_service(self) -> bool:
        return self.kind == "service"
    
    def is_anonymous(self) -> bool:
        return self.kind == "anonymous"
    
    def has_attribute(self, key: str) -> bool:
        return key in self.attributes
    
    def get_attribute(self, key: str, default=None):
        return self.attributes.get(key, default)
```

### SessionScope (Lifetime Semantics)

```python
class SessionScope(str, Enum):
    """
    Defines session lifetime semantics.
    
    Scope determines when and how session state persists.
    """
    REQUEST = "request"        # Lives only for single request (no persistence)
    CONNECTION = "connection"  # WebSocket / long-lived connection
    USER = "user"             # Persistent user session (typical web session)
    DEVICE = "device"         # Bound to device fingerprint (mobile apps)
    
    def requires_persistence(self) -> bool:
        """Check if this scope requires store persistence."""
        return self in (SessionScope.USER, SessionScope.DEVICE, SessionScope.CONNECTION)
    
    def is_ephemeral(self) -> bool:
        """Check if session is ephemeral (no persistence)."""
        return self == SessionScope.REQUEST
```

### SessionFlag (Behavioral Markers)

```python
class SessionFlag(str, Enum):
    """
    Flags that modify session behavior.
    """
    AUTHENTICATED = "authenticated"    # Has authenticated principal
    EPHEMERAL = "ephemeral"           # Never persist to store
    ROTATABLE = "rotatable"           # ID should rotate on privilege change
    RENEWABLE = "renewable"           # Can extend TTL on use
    READ_ONLY = "read_only"           # Data mutations disallowed
    LOCKED = "locked"                 # Concurrency lock active
```

### SessionPolicy (Behavioral Contract)

```python
@dataclass
class SessionPolicy:
    """
    Policy defines how sessions behave.
    
    Policies are the source of truth for:
    - Lifetime management
    - Rotation rules
    - Persistence strategy
    - Concurrency limits
    """
    name: str                          # Policy identifier (e.g., "user_default")
    ttl: timedelta | None              # Total lifetime (None = no expiry)
    idle_timeout: timedelta | None     # Max idle time before expiry
    rotate_on_use: bool = False        # Rotate ID on each request
    rotate_on_privilege_change: bool = True  # Rotate ID when auth changes
    persistence: PersistencePolicy     # How to persist sessions
    concurrency: ConcurrencyPolicy     # Concurrent session limits
    transport: TransportPolicy         # How sessions travel
    scope: SessionScope = SessionScope.USER
    
    def should_rotate(self, session: Session, privilege_changed: bool = False) -> bool:
        """Determine if session ID should rotate."""
        if privilege_changed and self.rotate_on_privilege_change:
            return True
        if self.rotate_on_use:
            return True
        return False
    
    def calculate_expiry(self, now: datetime) -> datetime | None:
        """Calculate session expiry time."""
        if not self.ttl:
            return None
        return now + self.ttl
    
    def is_valid(self, session: Session, now: datetime) -> tuple[bool, str]:
        """Validate session against policy."""
        # Check expiry
        if session.expires_at and now >= session.expires_at:
            return False, "expired"
        
        # Check idle timeout
        if self.idle_timeout:
            idle = now - session.last_accessed_at
            if idle >= self.idle_timeout:
                return False, "idle_timeout"
        
        return True, "valid"
```

### Sub-Policies

```python
@dataclass
class PersistencePolicy:
    """Controls how sessions persist."""
    enabled: bool = True
    store_name: str = "default"  # Which SessionStore to use
    write_through: bool = True   # Immediate vs eventual persistence
    compress: bool = False       # Compress session data
    

@dataclass
class ConcurrencyPolicy:
    """Controls concurrent session limits."""
    max_sessions_per_principal: int | None = None  # None = unlimited
    behavior_on_limit: Literal["reject", "evict_oldest", "evict_all"] = "evict_oldest"
    
    def violated(self, principal: SessionPrincipal, active_count: int) -> bool:
        """Check if concurrency limit violated."""
        if self.max_sessions_per_principal is None:
            return False
        return active_count > self.max_sessions_per_principal


@dataclass
class TransportPolicy:
    """Controls how sessions travel."""
    adapter: Literal["cookie", "header", "token"] = "cookie"
    cookie_name: str = "aquilia_session"
    cookie_httponly: bool = True
    cookie_secure: bool = True
    cookie_samesite: Literal["strict", "lax", "none"] = "lax"
    header_name: str = "X-Session-ID"
```

## Integration Contracts

### 1. Flow Engine Integration

Sessions are injected explicitly into handlers:

```python
# Handler WITHOUT session - no session resolution happens
@flow("/public").GET
async def public_endpoint():
    return Response.json({"message": "No session needed"})

# Handler WITH session - SessionEngine resolves/creates session
@flow("/profile").GET
async def profile(session: Session):
    user_id = session.principal.id if session.is_authenticated else None
    return Response.json({"user_id": user_id})

# Handler WITH optional session
@flow("/mixed").GET
async def mixed(session: Session | None = None):
    if session and session.is_authenticated:
        return Response.json({"mode": "authenticated"})
    return Response.json({"mode": "anonymous"})
```

**Contract:**
- If handler parameter is `session: Session`, SessionEngine MUST provide a session
- If handler parameter is `session: Session | None`, SessionEngine provides if available
- If handler does not declare session parameter, SessionEngine does not run

### 2. Dependency Injection Integration

```python
# SessionEngine is app-scoped
@service(scope="app", name="SessionEngine")
class SessionEngine:
    def __init__(self, config: Config, fault_engine: FaultEngine):
        self.config = config
        self.fault_engine = fault_engine

# Session is request-scoped (created per request)
# Cannot be injected into app-scoped services (scope violation)

# Example: SessionEngine creates and registers Session
async def resolve_session(self, request: Request, container: Container) -> Session:
    session = await self._load_or_create(request)
    # Register as request-scoped instance
    await container.register_instance(Session, session, scope="request")
    return session
```

**Contract:**
- `SessionEngine` = app-scoped service (singleton per app)
- `SessionStore` = app-scoped service
- `Session` = request-scoped instance (created per request)
- Scope violations (session in app-scoped service) = DI error

### 3. Faults Integration

Define session-specific fault domain and codes:

```python
# New FaultDomain
class FaultDomain(str, Enum):
    ...
    SESSION = "session"  # Session-related faults

# Session fault codes
SESSION_EXPIRED = "SESSION_EXPIRED"
SESSION_INVALID = "SESSION_INVALID"
SESSION_CONCURRENCY_VIOLATION = "SESSION_CONCURRENCY_VIOLATION"
SESSION_STORE_UNAVAILABLE = "SESSION_STORE_UNAVAILABLE"
SESSION_ROTATION_FAILED = "SESSION_ROTATION_FAILED"
SESSION_POLICY_VIOLATION = "SESSION_POLICY_VIOLATION"

# Session faults inherit from Fault
class SessionFault(Fault):
    """Base class for session-related faults."""
    domain = FaultDomain.SESSION

class SessionExpiredFault(SessionFault):
    code = SESSION_EXPIRED
    message = "Session has expired"
    severity = Severity.WARN
    public = True  # Safe to show user

class SessionConcurrencyViolationFault(SessionFault):
    code = SESSION_CONCURRENCY_VIOLATION
    message = "Too many concurrent sessions"
    severity = Severity.ERROR
    public = True
```

**Contract:**
- All session errors = structured Faults (not bare exceptions)
- Emit FaultContext with session_id, principal, policy metadata
- Faults include recovery hints (e.g., "re-authenticate")

### 4. Config Integration

Session policies defined in config:

```yaml
# config/default.py
sessions:
  default_policy: "user_default"
  
  policies:
    user_default:
      ttl: 604800  # 7 days (seconds)
      idle_timeout: 1800  # 30 minutes
      rotate_on_use: false
      rotate_on_privilege_change: true
      persistence:
        enabled: true
        store_name: "redis"
        write_through: true
      concurrency:
        max_sessions_per_principal: 5
        behavior_on_limit: "evict_oldest"
      transport:
        adapter: "cookie"
        cookie_name: "aquilia_session"
        cookie_httponly: true
        cookie_secure: true
        cookie_samesite: "lax"
      scope: "user"
    
    api_token:
      ttl: 3600  # 1 hour
      idle_timeout: null
      rotate_on_use: false
      rotate_on_privilege_change: false
      persistence:
        enabled: true
        store_name: "redis"
      transport:
        adapter: "header"
        header_name: "X-API-Token"
      scope: "user"
    
    ephemeral:
      ttl: null
      idle_timeout: null
      persistence:
        enabled: false
      transport:
        adapter: "cookie"
      scope: "request"
  
  stores:
    redis:
      type: "redis"
      url: "redis://localhost:6379/0"
      key_prefix: "aquilia:session:"
    
    memory:
      type: "memory"
      max_sessions: 10000
```

**Contract:**
- Policies validated at startup
- Invalid policy = ConfigError (fatal fault)
- Policy names referenced in manifests must exist

### 5. Aquilary (Registry) Integration

Manifests declare session requirements:

```python
class MyAppManifest(AppManifest):
    name = "my_app"
    version = "1.0.0"
    
    # Declare session requirements
    sessions = {
        "required": True,           # This app requires sessions
        "policy": "user_default",   # Default policy for this app
        "stores": ["redis"],        # Required stores
    }
    
    controllers = [...]
    services = [...]
```

**Contract:**
- Registry validates session requirements at compile time
- Missing policies/stores = ManifestValidationError
- SessionEngine initialized before app startup

## Security Guarantees

1. **Cryptographic Randomness**
   - Session IDs use `secrets.token_bytes(32)` (256 bits entropy)
   - Never predictable or guessable

2. **Atomic Rotation**
   - Old session ID invalidated atomically with new ID creation
   - No window where both IDs are valid (prevents session fixation)

3. **Idle Timeout Enforcement**
   - Enforced on every access, not just at creation
   - Cannot be bypassed by keeping connection alive

4. **Concurrency Limits**
   - Per-principal session limits enforced
   - Prevents session flooding attacks

5. **No Session Fixation**
   - New session ID on privilege change (login)
   - Old session fully destroyed

6. **Explicit Destruction**
   - Sessions destroyed on logout
   - Policy violations trigger automatic destruction

7. **Transport Security**
   - HttpOnly cookies prevent XSS access
   - Secure flag enforces HTTPS
   - SameSite prevents CSRF

## Observability

Emit structured events for every session operation:

```python
# Event structure
{
    "event": "session_created",
    "timestamp": "2026-01-24T12:00:00Z",
    "session_id_hash": "sha256:abc123...",  # Hashed for privacy
    "principal": {
        "kind": "user",
        "id": "user_123"
    },
    "policy": "user_default",
    "scope": "user",
    "request_id": "req_xyz789",
    "ip_address": "192.168.1.1"
}
```

**Events:**
- `session_created` - New session created
- `session_loaded` - Existing session loaded from store
- `session_rotated` - Session ID rotated
- `session_committed` - Session persisted to store
- `session_destroyed` - Session explicitly destroyed
- `session_expired` - Session expired (natural or forced)
- `session_concurrency_violation` - Too many sessions
- `session_store_error` - Store operation failed

**CLI Introspection:**
```bash
# View active sessions (dev mode)
aq inspect sessions

# Output:
# Active Sessions (5):
# sess_abc123... | user:123 | user_default | expires: 2026-01-31
# sess_def456... | user:456 | user_default | expires: 2026-01-31
# ...

# View session details
aq inspect sessions sess_abc123...

# Output:
# Session: sess_abc123...
# Principal: user:123
# Policy: user_default
# Created: 2026-01-24 12:00:00
# Last Access: 2026-01-24 13:45:12
# Expires: 2026-01-31 12:00:00
# Data: {"cart_items": 3, "preferences": {...}}
```

## Anti-Patterns (Forbidden)

1. ❌ **Global `request.session` objects**
   - Sessions MUST be explicitly injected via DI

2. ❌ **Implicit session creation**
   - Session creation MUST be explicit and policy-driven

3. ❌ **Silent session renewal**
   - TTL extension MUST be observable and policy-controlled

4. ❌ **Mixing auth logic into session store**
   - Store only persists, auth logic belongs in handlers

5. ❌ **Using cookies as the session model**
   - Cookies are transport, not the data model

6. ❌ **Encoding data in session ID**
   - Session IDs are opaque identifiers, not JWTs

## Acceptance Criteria

AquilaSessions is complete when:

✅ Sessions feel explicit and intentional  
✅ Handlers clearly declare when they need session state  
✅ Session behavior is consistent across transports  
✅ Production behavior is predictable and auditable  
✅ Debugging session issues does not require guessing  
✅ All security guarantees are tested and verified  
✅ Integration with Flow, DI, Faults is seamless  
✅ Documentation shows common patterns clearly  

## Implementation Phases

### Phase 1: Core Types (THIS PHASE)
- [ ] Session, SessionID, SessionPrincipal
- [ ] SessionScope, SessionFlag
- [ ] SessionPolicy and sub-policies
- [ ] Fault definitions

### Phase 2: Engine & Stores
- [ ] SessionEngine (lifecycle orchestrator)
- [ ] MemoryStore (dev/testing)
- [ ] RedisStore (production)
- [ ] FileStore (debugging)

### Phase 3: Transport & Integration
- [ ] CookieTransport
- [ ] HeaderTransport
- [ ] DI integration
- [ ] Flow Engine integration

### Phase 4: Faults & Config
- [ ] Session fault handlers
- [ ] Config schema validation
- [ ] Aquilary manifest integration

### Phase 5: Observability & Testing
- [ ] Event emission
- [ ] CLI inspection commands
- [ ] Comprehensive test suite
- [ ] Property-based tests

---

**Status:** Design complete, ready for implementation  
**Next:** Implement Phase 1 - Core Types
