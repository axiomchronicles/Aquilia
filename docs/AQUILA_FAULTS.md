# AquilaFaults - Production-Grade Fault Handling

> **Philosophy**: Errors are data, not surprises.

AquilaFaults is Aquilia's first-class exception and fault handling system. Unlike traditional exception handling, AquilaFaults treats errors as **structured data objects** that flow through the system with context, lifecycle, and intent.

## Core Concepts

### 1. Faults are Structured Data

Every fault is a **typed object** with:
- **Code**: Unique identifier (e.g., `USER_NOT_FOUND`)
- **Message**: Human-readable description
- **Domain**: Categorization (CONFIG, REGISTRY, DI, ROUTING, FLOW, EFFECT, IO, SECURITY, SYSTEM)
- **Severity**: Level (INFO, WARN, ERROR, FATAL)
- **Retryable**: Whether fault can be retried
- **Public**: Whether message is safe for external consumption
- **Metadata**: Additional context (user_id, query, etc.)

```python
from aquilia.faults import Fault, FaultDomain, Severity

class UserNotFoundFault(Fault):
    def __init__(self, user_id: str):
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"User '{user_id}' not found",
            domain=FaultDomain.FLOW,
            severity=Severity.ERROR,
            public=True,
            metadata={"user_id": user_id},
        )
```

### 2. Fault Lifecycle (5 Phases)

Every fault flows through five phases:

1. **Origin**: Exception or Fault created
2. **Annotation**: Wrapped with FaultContext (trace_id, app, route, stack)
3. **Propagation**: Routed through handler chain
4. **Resolution**: Resolved, transformed, or escalated
5. **Emission**: Logged and emitted as event

```
Exception → FaultContext → Handler Chain → FaultResult → Event
```

### 3. Scoped Fault Handlers

Handlers are registered at four scopes:

- **Global**: Apply to all faults
- **App**: Apply to specific app
- **Controller**: Apply to specific controller
- **Route**: Apply to specific route

Resolution order: **Route → Controller → App → Global**

```python
engine = FaultEngine()

# Global handler (catches everything)
engine.register_global(ExceptionAdapter())

# App-specific handler
engine.register_app("auth", SecurityFaultHandler())

# Route-specific handler
engine.register_route("/login", ResponseMapper())
```

### 4. Fault Transform Chains

Faults can be transformed while preserving causality:

```python
# Internal database fault
db_fault = DatabaseFault(
    code="CONNECTION_POOL_EXHAUSTED",
    message="Database connection pool exhausted",
)

# Transform to public API fault
api_fault = ApiFault(original_code=db_fault.code)

# Use transform operator (preserves causality)
result = db_fault >> api_fault
```

### 5. Observability by Default

Every fault produces a traceable event with:
- **Trace ID**: Unique identifier for correlation
- **Fingerprint**: Stable hash for grouping similar faults
- **Stack trace**: Captured at origin
- **Scope**: App, route, request_id
- **Causality**: Parent fault references

## Architecture

### Fault Domains (9 Categories)

| Domain | Description | Example Faults |
|--------|-------------|----------------|
| **CONFIG** | Configuration errors | ConfigMissingFault, ConfigInvalidFault |
| **REGISTRY** | Registry/manifest errors | DependencyCycleFault, ManifestInvalidFault |
| **DI** | Dependency injection errors | ProviderNotFoundFault, ScopeViolationFault |
| **ROUTING** | Routing errors | RouteNotFoundFault, RouteAmbiguousFault |
| **FLOW** | Request flow errors | HandlerFault, MiddlewareFault |
| **EFFECT** | External system errors | DatabaseFault, CacheFault |
| **IO** | I/O errors | NetworkFault, FilesystemFault |
| **SECURITY** | Security errors | AuthenticationFault, AuthorizationFault |
| **SYSTEM** | System errors | UnrecoverableFault, ResourceExhaustedFault |

### Severity Levels

| Severity | Description | Recovery Strategy |
|----------|-------------|-------------------|
| **INFO** | Informational (non-error) | Continue |
| **WARN** | Warning (potential issue) | Continue with logging |
| **ERROR** | Error (recoverable) | Retry or return error response |
| **FATAL** | Fatal (unrecoverable) | Terminate server |

### Handler Types

#### 1. ExceptionAdapter

Converts raw Python exceptions to structured Faults:

```python
engine = FaultEngine()
engine.register_global(ExceptionAdapter())

try:
    raise ConnectionError("Network failure")
except Exception as e:
    result = await engine.process(e)  # Converts to NetworkFault
```

#### 2. RetryHandler

Retries transient failures with exponential backoff:

```python
engine.register_global(RetryHandler(
    max_attempts=3,
    base_delay=0.1,
    multiplier=2.0,
    max_delay=10.0,
))
```

#### 3. SecurityFaultHandler

Masks sensitive information in security faults:

```python
# Input: AuthenticationFault(reason="Invalid token: secret_key_xyz")
# Output: AuthenticationFault(reason="Authentication failed")

engine.register_app("api", SecurityFaultHandler())
```

#### 4. ResponseMapper

Maps faults to HTTP/WebSocket/RPC responses:

```python
engine.register_global(ResponseMapper())

# DatabaseFault → HTTP 503 Service Unavailable
# RouteNotFoundFault → HTTP 404 Not Found
# AuthenticationFault → HTTP 401 Unauthorized
# AuthorizationFault → HTTP 403 Forbidden
```

#### 5. FatalHandler

Terminates server on FATAL severity faults:

```python
import sys

engine.register_global(FatalHandler(
    callback=lambda ctx: sys.exit(1),
))
```

#### 6. LoggingHandler

Structured logging for all faults:

```python
engine.register_global(LoggingHandler())
```

## Usage Examples

### Basic Usage

```python
from aquilia.faults import FaultEngine, ExceptionAdapter, ResponseMapper

# Create engine
engine = FaultEngine()

# Register handlers
engine.register_global(ExceptionAdapter())
engine.register_global(ResponseMapper())

# Set context
FaultEngine.set_context(
    app="api",
    route="/users/:id",
    request_id="req_123",
)

# Process fault
try:
    # ... application code ...
except Exception as e:
    result = await engine.process(e)
    
    if isinstance(result, Resolved):
        return result.response  # HTTPResponse
```

### Custom Fault

```python
from aquilia.faults import Fault, FaultDomain, Severity

class RateLimitExceededFault(Fault):
    def __init__(self, limit: int, current: int):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded: {current}/{limit} requests",
            domain=FaultDomain.SECURITY,
            severity=Severity.WARN,
            retryable=True,
            public=True,
            metadata={
                "limit": limit,
                "current": current,
            },
        )
```

### Custom Handler

```python
from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved

class CustomHandler(FaultHandler):
    def can_handle(self, ctx: FaultContext) -> bool:
        return ctx.fault.code == "MY_FAULT"
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        # Custom handling logic
        return Resolved({"status": "handled"})

engine.register_app("myapp", CustomHandler())
```

### Fault Transform Chain

```python
# Define semantic mapping
db_fault = DatabaseFault(code="CONNECTION_ERROR", ...)
api_fault = ApiFault(code="SERVICE_UNAVAILABLE", ...)

# Transform (preserves causality)
public_fault = db_fault >> api_fault

# Process
result = await engine.process(public_fault)
```

### Observability

```python
engine = FaultEngine(debug=True)

# Register event listener
def on_fault(ctx: FaultContext):
    print(f"Fault: {ctx.fault.code}")
    print(f"Trace ID: {ctx.trace_id}")
    print(f"Fingerprint: {ctx.fingerprint()}")

engine.on_fault(on_fault)

# Process fault
await engine.process(fault)

# Inspect history
history = engine.get_history()
for ctx in history:
    print(ctx.to_dict())

# Engine stats
stats = engine.get_stats()
print(stats)
```

## Integration with Aquilia

### Server Integration

```python
from aquilia import AquiliaServer
from aquilia.faults import FaultEngine, ExceptionAdapter, ResponseMapper

server = AquiliaServer()

# Configure fault engine
engine = FaultEngine()
engine.register_global(ExceptionAdapter())
engine.register_global(ResponseMapper())

# Attach to server
server.fault_engine = engine
```

### Middleware Integration

```python
from aquilia.faults import FaultEngine

async def fault_handling_middleware(request, next):
    FaultEngine.set_context(
        app=request.app,
        route=request.route,
        request_id=request.id,
    )
    
    try:
        return await next(request)
    except Exception as e:
        result = await engine.process(e)
        if isinstance(result, Resolved):
            return result.response
        raise
```

### Handler Integration

```python
from aquilia.faults import UserNotFoundFault

async def get_user(user_id: str):
    user = await db.get_user(user_id)
    if not user:
        raise UserNotFoundFault(user_id)
    return user
```

## Best Practices

### 1. Define Domain-Specific Faults

Create custom faults for your domain:

```python
class OrderNotFoundFault(Fault):
    def __init__(self, order_id: str):
        super().__init__(
            code="ORDER_NOT_FOUND",
            message=f"Order '{order_id}' not found",
            domain=FaultDomain.FLOW,
            severity=Severity.ERROR,
            public=True,
        )
```

### 2. Use Transform Chains for Public APIs

Map internal faults to public faults:

```python
internal_fault = DatabaseFault(...)
public_fault = ApiFault(...)

result = internal_fault >> public_fault
```

### 3. Register Handlers at Appropriate Scope

- **Global**: Cross-cutting concerns (logging, exception conversion)
- **App**: App-specific policies (security, rate limiting)
- **Route**: Route-specific handling (custom error responses)

### 4. Mark Faults as Retryable

Enable automatic retry for transient failures:

```python
NetworkFault(..., retryable=True)
```

### 5. Use Public/Private Distinction

Protect sensitive information:

```python
DatabaseFault(
    message="Query failed: SELECT * FROM users WHERE password = 'secret'",
    public=False,  # Never expose to clients
)
```

### 6. Leverage Observability

Use trace IDs and fingerprints for debugging:

```python
# Group similar faults by fingerprint
faults_by_fingerprint = {}
for ctx in engine.get_history():
    fp = ctx.fingerprint()
    if fp not in faults_by_fingerprint:
        faults_by_fingerprint[fp] = []
    faults_by_fingerprint[fp].append(ctx)
```

## Testing

### Unit Tests

```python
import pytest
from aquilia.faults import FaultEngine, ExceptionAdapter

@pytest.mark.asyncio
async def test_exception_conversion():
    engine = FaultEngine()
    engine.register_global(ExceptionAdapter())
    
    result = await engine.process(ConnectionError("test"))
    
    assert isinstance(result, Transformed)
    assert result.fault.code == "CONNECTION_ERROR"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_fault_flow():
    engine = FaultEngine()
    engine.register_global(ExceptionAdapter())
    engine.register_global(ResponseMapper())
    
    FaultEngine.set_context(app="api", route="/test")
    
    result = await engine.process(FileNotFoundError("test.json"))
    
    assert isinstance(result, Resolved)
    assert result.response.status_code == 502
```

### Property Tests

```python
from hypothesis import given, strategies as st

@given(st.text(), st.text())
@pytest.mark.asyncio
async def test_no_faults_lost(code, message):
    engine = FaultEngine(debug=True)
    
    fault = SystemFault(code=code, message=message)
    await engine.process(fault)
    
    # Verify fault is in history
    assert len(engine.get_history()) == 1
    assert engine.get_history()[0].fault.code == code
```

## Performance Considerations

- **Fault creation**: ~1μs (frozen dataclass)
- **Context capture**: ~10μs (includes stack trace)
- **Handler resolution**: O(n) where n = number of handlers
- **Fingerprinting**: ~5μs (hash of code+domain+app+route)
- **Memory**: ~1KB per FaultContext (debug mode)

## Roadmap

- [ ] Crous serialization (save FaultContexts to disk)
- [ ] CLI tool: `aq faults inspect <trace_id>`
- [ ] Metrics (counter by domain/severity)
- [ ] Trace span creation (OpenTelemetry integration)
- [ ] Fault correlation (group related faults)
- [ ] Automatic incident creation (on FATAL)

## Design Principles

1. **Explicit over implicit**: No silent catches
2. **Data over control flow**: Faults are typed objects
3. **Scoped over global**: Handlers are scoped
4. **Observable over opaque**: Every fault is traceable
5. **Deterministic over random**: Handler order is defined

## Comparison with Traditional Exception Handling

| Traditional | AquilaFaults |
|-------------|--------------|
| `try/except` blocks | FaultEngine.process() |
| Bare exceptions | Structured Fault objects |
| No context | FaultContext with trace_id, stack, metadata |
| Silent catches possible | All faults are emitted |
| Global exception handling | Scoped handlers (global/app/route) |
| No retry logic | Built-in RetryHandler |
| Manual status code mapping | Automatic ResponseMapper |
| Security leaks | SecurityFaultHandler masks sensitive data |

---

**AquilaFaults**: Errors are data, not surprises. 🚀
