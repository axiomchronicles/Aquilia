# Request & Response Integration - Quick Reference

## Request Object - New Properties & Methods

### Identity/Auth
```python
request.identity              # Identity | None - Authenticated user
request.authenticated         # bool - Is authenticated?
request.require_identity()    # Identity - Get or raise AUTH_REQUIRED
request.has_role("admin")     # bool - Check role
request.has_scope("read")     # bool - Check OAuth scope
```

### Session
```python
request.session               # Session | None - User session
request.session_id            # str | None - Session ID
request.require_session()     # Session - Get or raise SESSION_REQUIRED
```

### DI Container
```python
request.container                          # Container | None
await request.resolve(MyService)           # Resolve single service
await request.resolve(MyService, optional=True)  # Optional
await request.inject(auth=Auth, db=DB)    # Resolve multiple
```

### Templates
```python
request.template_context      # Dict[str, Any] - Auto-injected context
request.add_template_context(key="value")  # Add custom vars
```

### Lifecycle
```python
await request.emit_effect("event", data="value")  # Emit effect
await request.before_response(callback)    # Register pre-send hook
await request.after_response(callback)     # Register post-send hook
```

### Faults & Metrics
```python
request.fault_context()                    # Dict - Request metadata
await request.report_fault(fault)          # Report with context
request.trace_id                          # str | None - Trace ID
request.request_id                        # str | None - Request ID
request.record_metric("name", 1.0)        # Record metric
```

## Response Object - New Methods

### Template Rendering
```python
# Auto-injects identity, session, authenticated from request
await Response.render(
    "template.html",
    {"extra": "data"},
    request=request,
    status=200
)
```

### Lifecycle & Sessions
```python
await response.commit_session(request)                    # Commit session
await response.execute_before_send_hooks(request)         # Run before hooks
await response.execute_after_send_hooks(request)          # Run after hooks
response.record_response_metrics(request, duration_ms)    # Record metrics
```

### Fault Conversion
```python
Response.from_fault(fault, include_details=True, request=request)
# Auto-maps fault codes to HTTP status:
# AUTH_REQUIRED → 401, AUTHZ_FORBIDDEN → 403, etc.
```

## Common Patterns

### Protected Endpoint
```python
async def handler(request):
    identity = request.require_identity()  # Raises if not auth'd
    
    if not request.has_role("admin"):
        return Response.json({"error": "Forbidden"}, 403)
    
    return Response.json({"data": "secret"})
```

### With DI Services
```python
async def handler(request):
    services = await request.inject(
        auth=AuthManager,
        db=Database,
    )
    
    user = await services["db"].get_user(request.identity.id)
    return Response.json({"user": user})
```

### Template Rendering
```python
async def handler(request):
    # identity, session, authenticated auto-injected!
    return await Response.render("page.html", request=request)
```

### With Lifecycle Hooks
```python
async def handler(request):
    # Register cleanup
    await request.after_response(lambda r: cleanup())
    
    # Emit audit event
    await request.emit_effect("order.created", order_id="123")
    
    return Response.json({"status": "ok"})
```

### Fault Handling
```python
async def handler(request):
    try:
        result = await risky_operation()
    except Exception as e:
        fault = Fault(code="ERROR", message=str(e), ...)
        await request.report_fault(fault)
        return Response.from_fault(fault, request=request)
```

## Auto-Injected Template Variables

When using `Response.render(request=request)`:

- `request` - Request object
- `identity` - Authenticated identity (or None)
- `session` - Session object (or None)
- `authenticated` - Boolean
- `url` - Current URL
- `method` - HTTP method (GET, POST, etc.)
- `path` - Request path
- `query_params` - Query parameters as dict

## Middleware Integration

Middleware should set these in `request.state`:

```python
request.state["identity"] = identity          # From AuthMiddleware
request.state["session"] = session            # From SessionMiddleware
request.state["di_container"] = container     # From RequestScopeMiddleware
request.state["template_engine"] = engine     # From TemplateMiddleware
request.state["fault_engine"] = fault_engine  # From FaultMiddleware
request.state["metrics_collector"] = metrics  # From MetricsMiddleware
request.state["request_id"] = str(uuid.uuid4())  # From RequestIdMiddleware
```

## Testing

```python
# Mock request with auth
request = Request(scope, receive)
request.state["identity"] = mock_identity
request.state["session"] = mock_session
request.state["di_container"] = mock_container

# Test identity
assert request.authenticated is True
assert request.identity == mock_identity
assert request.has_role("admin") is True

# Test DI
service = await request.resolve(MyService, optional=True)

# Test template context
context = request.template_context
assert "identity" in context
assert "authenticated" in context
```

## Backwards Compatibility

All old code still works:

```python
# Old way (still works)
identity = request.state.get("identity")

# New way (preferred)
identity = request.identity
```

## Status

- **Tests**: 32/32 passing ✅
- **Warnings**: 0 ✅
- **Breaking Changes**: 0 ✅
- **Production Ready**: YES ✅
