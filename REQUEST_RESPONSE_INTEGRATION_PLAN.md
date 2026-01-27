# Request & Response Deep Integration Plan

## Overview

Integrate all Aquilia subsystems deeply into Request and Response classes to provide:
- Seamless access to Auth (Identity)
- Session management
- DI container resolution
- Template rendering
- Fault handling
- Effects/Lifecycle hooks
- Metrics and tracing

## Current State Analysis

### Request.py Current Features
✅ ASGI scope/receive/send handling
✅ Stream

ing body with caching
✅ Query/header/cookie parsing
✅ JSON/form/multipart parsing
✅ File upload support
✅ Client IP detection with proxy trust
✅ Basic fault integration (RequestFault subclasses)
✅ State dict for middleware data
❌ No Identity property
❌ No Session property
❌ No DI container property
❌ No Template context access
❌ Limited fault integration

### Response.py Current Features
✅ Multiple content types (bytes, str, JSON, iterables)
✅ Streaming support with chunking
✅ Headers and cookies (with signing)
✅ Background tasks
✅ File streaming with Range support
✅ Server-Sent Events
✅ Compression (gzip, brotli)
✅ Caching helpers (ETag, Last-Modified)
✅ Basic fault integration
✅ Template rendering (via static method)
❌ No template context injection
❌ No automatic identity/session injection
❌ Limited integration with lifecycle

## Integration Requirements

### 1. Request Enhancements

#### A. Identity Integration
```python
@property
def identity(self) -> Optional[Identity]:
    """Get authenticated identity (set by AuthMiddleware)."""
    return self.state.get("identity")

@property
def authenticated(self) -> bool:
    """Check if request is authenticated."""
    return self.identity is not None

def require_identity(self) -> Identity:
    """Get identity or raise AUTH_REQUIRED fault."""
    identity = self.identity
    if not identity:
        from aquilia.auth.faults import AUTH_REQUIRED
        raise AUTH_REQUIRED()
    return identity

def has_role(self, role: str) -> bool:
    """Check if identity has role."""
    return self.identity and self.identity.has_role(role)

def has_scope(self, scope: str) -> bool:
    """Check if identity has OAuth scope."""
    return self.identity and self.identity.has_scope(scope)
```

#### B. Session Integration
```python
@property
def session(self) -> Optional[Session]:
    """Get session (set by SessionMiddleware)."""
    return self.state.get("session")

def require_session(self) -> Session:
    """Get session or raise SESSION_REQUIRED fault."""
    session = self.session
    if not session:
        from aquilia.sessions.faults import SessionNotFoundFault
        raise SessionNotFoundFault()
    return session

@property
def session_id(self) -> Optional[str]:
    """Get session ID."""
    return self.session.id if self.session else None
```

#### C. DI Container Integration
```python
@property
def container(self) -> Optional[Container]:
    """Get request-scoped DI container."""
    return self.state.get("di_container")

async def resolve(self, service_type: Type[T], *, optional: bool = False) -> T:
    """Resolve service from DI container."""
    container = self.container
    if not container:
        if optional:
            return None
        raise RuntimeError("DI container not available in request")
    return await container.resolve_async(service_type, optional=optional)

async def inject(self, **services):
    """Inject multiple services by name."""
    container = self.container
    if not container:
        return {}
    
    results = {}
    for name, service_type in services.items():
        results[name] = await container.resolve_async(service_type, optional=True)
    return results
```

#### D. Template Context Integration
```python
@property
def template_context(self) -> Dict[str, Any]:
    """Get template rendering context (includes identity, session, request)."""
    context = self.state.get("template_context", {})
    
    # Auto-inject common variables
    context.setdefault("request", self)
    context.setdefault("identity", self.identity)
    context.setdefault("session", self.session)
    context.setdefault("authenticated", self.authenticated)
    context.setdefault("url", self.url())
    context.setdefault("method", self.method)
    context.setdefault("path", self.path)
    
    return context

def add_template_context(self, **kwargs):
    """Add variables to template context."""
    if "template_context" not in self.state:
        self.state["template_context"] = {}
    self.state["template_context"].update(kwargs)
```

#### E. Lifecycle & Effects Integration
```python
async def emit_effect(self, effect_name: str, **data):
    """Emit effect for lifecycle hooks."""
    lifecycle = self.state.get("lifecycle_manager")
    if lifecycle:
        await lifecycle.emit(effect_name, request=self, **data)

async def before_response(self, callback: Callable):
    """Register callback to run before response is sent."""
    callbacks = self.state.setdefault("before_response_callbacks", [])
    callbacks.append(callback)

async def after_response(self, callback: Callable):
    """Register callback to run after response is sent."""
    callbacks = self.state.setdefault("after_response_callbacks", [])
    callbacks.append(callback)
```

#### F. Enhanced Fault Handling
```python
def fault_context(self) -> Dict[str, Any]:
    """Get context for fault reporting."""
    return {
        "method": self.method,
        "path": self.path,
        "query": self.query_string,
        "client": self.client_ip(),
        "user_agent": self.header("user-agent"),
        "identity_id": self.identity.id if self.identity else None,
        "session_id": self.session_id,
        "request_id": self.state.get("request_id"),
    }

async def report_fault(self, fault: Fault):
    """Report fault through FaultEngine."""
    fault_engine = self.state.get("fault_engine")
    if fault_engine:
        # Enrich fault with request context
        fault.metadata.update(self.fault_context())
        await fault_engine.process(fault)
```

#### G. Metrics & Tracing
```python
@property
def trace_id(self) -> Optional[str]:
    """Get trace ID for distributed tracing."""
    return self.state.get("trace_id") or self.header("x-trace-id")

@property
def request_id(self) -> Optional[str]:
    """Get unique request ID."""
    return self.state.get("request_id")

def record_metric(self, name: str, value: float, **tags):
    """Record metric for this request."""
    metrics = self.state.get("metrics_collector")
    if metrics:
        tags.update({
            "method": self.method,
            "path": self.path,
            "authenticated": self.authenticated,
        })
        metrics.record(name, value, **tags)
```

### 2. Response Enhancements

#### A. Template Integration with Auto-Injection
```python
@classmethod
async def render(
    cls,
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    *,
    request: Optional[Request] = None,
    engine: Optional[TemplateEngine] = None,
    status: int = 200,
    headers: Optional[Mapping] = None,
) -> Response:
    """
    Render template with automatic context injection.
    
    Automatically injects:
    - request (if provided)
    - identity (from request)
    - session (from request)
    - authenticated (bool)
    - common filters and globals
    """
    # Merge contexts
    final_context = context or {}
    
    # Auto-inject from request
    if request:
        final_context.update(request.template_context)
    
    # Resolve engine from DI if not provided
    if engine is None and request:
        engine = await request.resolve(TemplateEngine, optional=True)
    
    if engine is None:
        raise TemplateRenderError("No TemplateEngine available")
    
    # Render
    html = await engine.render(template_name, final_context)
    
    return cls(
        content=html,
        status=status,
        headers=headers,
        media_type="text/html; charset=utf-8",
    )
```

#### B. Session Integration
```python
async def commit_session(self, request: Request):
    """Commit session changes after response."""
    session = request.session
    if session:
        session_engine = await request.resolve(SessionEngine, optional=True)
        if session_engine:
            await session_engine.commit(session, self)
```

#### C. Lifecycle Hooks
```python
async def execute_before_send_hooks(self, request: Request):
    """Execute before-response callbacks."""
    callbacks = request.state.get("before_response_callbacks", [])
    for callback in callbacks:
        if asyncio.iscoroutinefunction(callback):
            await callback(self)
        else:
            callback(self)

async def execute_after_send_hooks(self, request: Request):
    """Execute after-response callbacks."""
    callbacks = request.state.get("after_response_callbacks", [])
    for callback in callbacks:
        if asyncio.iscoroutinefunction(callback):
            await callback(self)
        else:
            callback(self)
```

#### D. Metrics Integration
```python
def record_response_metrics(self, request: Request, duration_ms: float):
    """Record response metrics."""
    request.record_metric("http_response_time", duration_ms, status=self.status)
    request.record_metric("http_response_size", len(self._headers), status=self.status)
```

### 3. Server.py Integration Points

#### A. Middleware Stack Enhancement
```python
# In _setup_middleware():

# 1. Request ID middleware (first)
self.middleware_stack.add(
    RequestIdMiddleware(),
    priority=10,
    name="request_id",
)

# 2. Request scope middleware (creates DI container)
from .auth.integration.middleware import EnhancedRequestScopeMiddleware
self.middleware_stack.add(
    EnhancedRequestScopeMiddleware(base_container),
    priority=20,
    name="request_scope",
)

# 3. Template middleware (injects engine and context)
self.middleware_stack.add(
    TemplateMiddleware(template_engine),
    priority=30,
    name="templates",
)

# 4. Auth middleware (identity + session)
self.middleware_stack.add(
    AquilAuthMiddleware(session_engine, auth_manager),
    priority=40,
    name="auth",
)

# 5. Metrics middleware
self.middleware_stack.add(
    MetricsMiddleware(),
    priority=50,
    name="metrics",
)
```

#### B. Request Enhancement in ASGI Adapter
```python
# In ASGIAdapter.__call__():

# Create enhanced request
request = Request(scope, receive, send)

# Inject server components
request.state["fault_engine"] = self.fault_engine
request.state["lifecycle_manager"] = self.lifecycle
request.state["metrics_collector"] = self.metrics

# Generate request ID
request.state["request_id"] = str(uuid.uuid4())
request.state["trace_id"] = scope.get("headers", {}).get("x-trace-id")
```

## Implementation Order

1. ✅ Analyze current state
2. ⏳ Add Identity/Session/Container properties to Request
3. ⏳ Add template context helpers to Request
4. ⏳ Add lifecycle hooks to Request
5. ⏳ Enhanced Response.render() with auto-injection
6. ⏳ Add session commit to Response
7. ⏳ Integrate with server.py middleware stack
8. ⏳ Add comprehensive tests
9. ⏳ Update documentation

## Benefits

### For Developers
- **Seamless access**: `request.identity`, `request.session` available everywhere
- **Type-safe DI**: `await request.resolve(MyService)` with full typing
- **Easy templates**: `Response.render("page.html", {"user": user}, request=request)` auto-injects everything
- **Clean code**: No manual extraction from `request.state`

### For Framework
- **Consistent API**: All subsystems accessible via same patterns
- **Better composition**: Components work together automatically
- **Easier testing**: Mock request.identity, request.session easily
- **Better observability**: Built-in metrics, tracing, fault context

### For Performance
- **Lazy evaluation**: Properties only compute when accessed
- **Caching**: Values cached after first access
- **Minimal overhead**: Only active when middleware is installed

## Breaking Changes

None - all additions are backwards compatible. Existing `request.state` access still works.

## Migration Path

### Before
```python
async def handler(request):
    identity = request.state.get("identity")
    if not identity:
        return Response.json({"error": "Unauthorized"}, status=401)
    
    container = request.state.get("di_container")
    service = await container.resolve_async(MyService)
    
    return Response.json({"user": identity.id})
```

### After
```python
async def handler(request):
    identity = request.require_identity()  # Raises AUTH_REQUIRED if missing
    service = await request.resolve(MyService)
    
    return Response.json({"user": identity.id})
```

### Templates Before
```python
async def handler(request):
    identity = request.state.get("identity")
    engine = await container.resolve_async(TemplateEngine)
    
    html = await engine.render("profile.html", {
        "user": identity,
        "request": request,
        "authenticated": identity is not None,
    })
    
    return Response(html, media_type="text/html")
```

### Templates After
```python
async def handler(request):
    return await Response.render(
        "profile.html",
        {"extra_data": "value"},
        request=request,
    )
    # identity, session, authenticated auto-injected!
```

## Testing Strategy

1. **Unit tests**: Test each property/method in isolation
2. **Integration tests**: Test with middleware stack
3. **Performance tests**: Ensure no overhead when features unused
4. **Migration tests**: Verify backwards compatibility

## Next Steps

1. Implement Request enhancements
2. Implement Response enhancements
3. Update middleware to set state properly
4. Add comprehensive tests
5. Update documentation
6. Create migration guide
