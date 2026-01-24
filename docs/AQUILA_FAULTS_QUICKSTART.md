# AquilaFaults - Quick Start Guide

Get started with AquilaFaults in 5 minutes.

## Installation

```python
# AquilaFaults is built-in to Aquilia
from aquilia.faults import FaultEngine, ExceptionAdapter, ResponseMapper
```

## Basic Setup

```python
from aquilia.faults import FaultEngine, ExceptionAdapter, ResponseMapper

# Create fault engine
engine = FaultEngine()

# Register default handlers
engine.register_global(ExceptionAdapter())  # Convert exceptions
engine.register_global(ResponseMapper())    # Map to HTTP responses

# Set context (usually done by middleware)
FaultEngine.set_context(
    app="my_app",
    route="/api/users/:id",
    request_id="req_123",
)
```

## Handling Exceptions

```python
try:
    # Your code here
    result = await some_operation()
except Exception as e:
    # Process fault
    result = await engine.process(e)
    
    if isinstance(result, Resolved):
        # Fault was resolved (e.g., HTTP response)
        return result.response
    else:
        # Fault escalated (no handler resolved it)
        raise
```

## Creating Custom Faults

```python
from aquilia.faults import Fault, FaultDomain, Severity

class UserNotFoundFault(Fault):
    """User not found in database."""
    
    def __init__(self, user_id: str):
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"User '{user_id}' not found",
            domain=FaultDomain.FLOW,
            severity=Severity.ERROR,
            public=True,  # Safe to show to clients
            metadata={"user_id": user_id},
        )

# Usage
raise UserNotFoundFault(user_id="user_123")
```

## Built-in Handlers

### 1. ExceptionAdapter - Convert exceptions to faults

```python
from aquilia.faults import ExceptionAdapter

engine.register_global(ExceptionAdapter())

# Automatically converts:
# - ConnectionError → NetworkFault
# - FileNotFoundError → IOFault
# - PermissionError → SecurityFault
```

### 2. RetryHandler - Retry transient failures

```python
from aquilia.faults import RetryHandler

engine.register_global(RetryHandler(
    max_attempts=3,      # Retry up to 3 times
    base_delay=0.1,      # Start with 0.1s delay
    multiplier=2.0,      # Double delay each time
    max_delay=10.0,      # Cap at 10s
))
```

### 3. SecurityFaultHandler - Mask sensitive data

```python
from aquilia.faults import SecurityFaultHandler

# For security-sensitive apps
engine.register_app("auth", SecurityFaultHandler())

# Converts:
# AuthenticationFault("Invalid token: secret_xyz") 
# → AuthenticationFault("Authentication failed")
```

### 4. ResponseMapper - Convert to HTTP responses

```python
from aquilia.faults import ResponseMapper

engine.register_global(ResponseMapper())

# Maps fault domains to status codes:
# - ROUTING → 404 Not Found
# - SECURITY (auth) → 401 Unauthorized
# - SECURITY (authz) → 403 Forbidden
# - EFFECT → 503 Service Unavailable
# - IO → 502 Bad Gateway
# - Everything else → 500 Internal Server Error
```

### 5. LoggingHandler - Structured logging

```python
from aquilia.faults import LoggingHandler

engine.register_global(LoggingHandler())

# Logs all faults with:
# - Severity-based log level
# - Trace ID
# - Fingerprint
# - Full context
```

## Scoped Handlers

Handlers can be registered at different scopes:

```python
# Global - applies to ALL faults
engine.register_global(ExceptionAdapter())

# App-specific
engine.register_app("auth", SecurityFaultHandler())

# Controller-specific
engine.register_controller("UserController", CustomHandler())

# Route-specific
engine.register_route("/login", LoginErrorHandler())

# Resolution order: Route → Controller → App → Global
```

## Transform Chains

Convert internal faults to public faults:

```python
from aquilia.faults.domains import DatabaseFault

# Internal fault (not safe for clients)
internal_fault = DatabaseFault(
    operation="query",
    reason="Connection pool exhausted",
)

# Public fault (safe for clients)
class ServiceUnavailableFault(Fault):
    def __init__(self):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message="Service temporarily unavailable",
            domain=FaultDomain.EFFECT,
            severity=Severity.ERROR,
            public=True,
        )

public_fault = ServiceUnavailableFault()

# Transform (preserves causality)
result = internal_fault >> public_fault
```

## Observability

### Event Listeners

```python
def on_fault(ctx):
    print(f"Fault: {ctx.fault.code}")
    print(f"Trace ID: {ctx.trace_id}")
    print(f"Fingerprint: {ctx.fingerprint()}")

engine.on_fault(on_fault)
```

### Debug Mode

```python
# Enable debug mode to record history
engine = FaultEngine(debug=True)

# ... process some faults ...

# Inspect history
history = engine.get_history()
for ctx in history:
    print(f"{ctx.trace_id}: {ctx.fault.code}")

# Engine stats
stats = engine.get_stats()
print(f"Total handlers: {sum(stats['handlers'].values())}")
```

## Common Patterns

### Middleware Pattern

```python
async def fault_handling_middleware(request, next):
    # Set context for this request
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

### Custom Handler Pattern

```python
from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved

class RateLimitHandler(FaultHandler):
    def can_handle(self, ctx: FaultContext) -> bool:
        return ctx.fault.code == "RATE_LIMIT_EXCEEDED"
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        # Custom handling logic
        return Resolved({
            "error": "Rate limit exceeded",
            "retry_after": 60,
        })

engine.register_global(RateLimitHandler())
```

### Service Integration Pattern

```python
async def call_external_service():
    try:
        response = await http_client.get("https://api.example.com")
        return response.json()
    except TimeoutError as e:
        # ExceptionAdapter converts to NetworkFault
        # RetryHandler retries automatically
        raise  # Let fault system handle it
```

## Pre-built Fault Types

### Flow Faults

```python
from aquilia.faults.domains import UserNotFoundFault, HandlerFault

raise HandlerFault(
    handler="get_user",
    reason="Invalid user ID format",
)
```

### Security Faults

```python
from aquilia.faults.domains import AuthenticationFault, AuthorizationFault

raise AuthenticationFault(reason="Invalid credentials")
raise AuthorizationFault(resource="/admin", action="read")
```

### Effect Faults

```python
from aquilia.faults.domains import DatabaseFault, CacheFault

raise DatabaseFault(operation="insert", reason="Duplicate key")
raise CacheFault(operation="get", key="user:123", reason="Connection timeout")
```

### IO Faults

```python
from aquilia.faults.domains import NetworkFault, FilesystemFault

raise NetworkFault(operation="request", reason="Connection refused")
raise FilesystemFault(operation="read", path="/etc/config", reason="Permission denied")
```

## Best Practices

### 1. Always Set Context

```python
# Before processing requests
FaultEngine.set_context(app="api", route="/users", request_id="req_123")
```

### 2. Use Domain-Specific Faults

```python
# Good: Specific fault type
raise UserNotFoundFault(user_id="123")

# Bad: Generic exception
raise ValueError("User not found")
```

### 3. Mark Retryable Faults

```python
NetworkFault(..., retryable=True)   # Can be retried
DatabaseFault(..., retryable=False)  # Should not retry
```

### 4. Use Public/Private Correctly

```python
# Public - safe for clients
Fault(..., public=True, message="User not found")

# Private - internal only
Fault(..., public=False, message="Database query: SELECT * FROM users")
```

### 5. Register Handlers at Appropriate Scope

```python
# Cross-cutting concerns → Global
engine.register_global(ExceptionAdapter())
engine.register_global(LoggingHandler())

# App-specific policies → App
engine.register_app("auth", SecurityFaultHandler())

# Route-specific handling → Route
engine.register_route("/admin", AdminErrorHandler())
```

## Running the Demo

```bash
cd /Users/kuroyami/PyProjects/Aquilia
PYTHONPATH=. python examples/faults_demo.py
```

Expected output:
```
======================================================================
DEMO 1: Exception Conversion
======================================================================
✓ FileNotFoundError → IOFault

======================================================================
DEMO 2: Retry Logic
======================================================================
Attempt 1 failed, retrying...
Attempt 2 failed, retrying...
✓ Success on attempt 3

... (7 demos total)
```

## Common Issues

### Issue: "No module named 'aquilia'"

**Solution**: Set PYTHONPATH
```bash
PYTHONPATH=/path/to/Aquilia python your_script.py
```

### Issue: Faults not being caught

**Solution**: Ensure handlers are registered before processing
```python
engine.register_global(ExceptionAdapter())  # BEFORE processing
result = await engine.process(exception)
```

### Issue: Sensitive data leaking

**Solution**: Use SecurityFaultHandler and mark faults as private
```python
engine.register_app("api", SecurityFaultHandler())

Fault(..., public=False)  # Not safe for clients
```

## Next Steps

- Read full documentation: `docs/AQUILA_FAULTS.md`
- See implementation details: `docs/AQUILA_FAULTS_IMPLEMENTATION.md`
- Review example code: `examples/faults_demo.py`
- Explore domain-specific faults: `aquilia/faults/domains.py`
- Create custom handlers: `aquilia/faults/handlers.py`

---

**Quick Start Complete!** 🚀

For questions or issues, see the full documentation or examine the working demo.
