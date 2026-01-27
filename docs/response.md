# Response - Production-Grade HTTP Response Builder

**aquilia.response.Response** — Full-featured, ASGI 3 compliant HTTP response builder with streaming, caching, security, and integration with Aquilia subsystems.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Response Class](#response-class)
  - [Factory Methods](#factory-methods)
  - [Cookie Methods](#cookie-methods)
  - [Header Methods](#header-methods)
  - [Caching Methods](#caching-methods)
  - [ASGI Send](#asgi-send)
- [Helper Classes](#helper-classes)
- [Examples](#examples)
- [Security Checklist](#security-checklist)
- [Background Tasks](#background-tasks)
- [Integration](#integration)
- [Phase 2 Features (TODO)](#phase-2-features)

---

## Overview

The `Response` class provides production-grade HTTP response handling with:

✅ **ASGI 3 Compliance** — Strict adherence to ASGI spec with proper streaming  
✅ **Multiple Content Types** — bytes, str, dict/list (JSON), async/sync iterables, coroutines  
✅ **Streaming-First** — Native support for async iterables, SSE, file streaming  
✅ **RFC-Compliant Headers & Cookies** — Proper encoding, multi-value support, signing  
✅ **Caching & Conditional Responses** — ETag, Last-Modified, Cache-Control, 304 responses  
✅ **Security** — Header validation, secure defaults, HSTS, CSP helpers  
✅ **Background Tasks** — Execute tasks after response sent  
✅ **Fault Integration** — Converts errors to Aquilia Faults  
✅ **Template Integration** — First-class support for TemplateEngine  

---

## Quick Start

### Basic JSON Response

```python
from aquilia import Controller, GET
from aquilia.response import Response

class ApiController(Controller):
    prefix = "/api"
    
    @GET("/users/{user_id}")
    async def get_user(self, ctx):
        user = {"id": ctx.params["user_id"], "name": "Alice"}
        return Response.json(user)
```

### HTML Response (Template)

```python
from aquilia.templates import TemplateEngine

class ProfileController(Controller):
    def __init__(self, templates: TemplateEngine):
        self.templates = templates
    
    @GET("/profile")
    async def view(self, ctx):
        return Response.render(
            "profile.html",
            {"user": ctx.identity},
            engine=self.templates
        )
```

### File Download

```python
@GET("/download/report")
async def download(self, ctx):
    file_path = Path("/var/data/report.pdf")
    return Response.file(file_path, filename="report.pdf")
```

### Server-Sent Events (SSE)

```python
@GET("/events")
async def events(self, ctx):
    async def event_stream():
        for i in range(10):
            yield ServerSentEvent(
                data=f"Event {i}",
                id=str(i),
                event="update"
            )
            await asyncio.sleep(1)
    
    return Response.sse(event_stream())
```

---

## API Reference

### Response Class

#### Constructor

```python
Response(
    content: Union[bytes, str, Mapping, Sequence, AsyncIterator[bytes], Iterator[bytes], Awaitable[Any]] = b"",
    status: int = 200,
    headers: Optional[Mapping[str, Union[str, Sequence[str]]]] = None,
    media_type: Optional[str] = None,
    *,
    background: Optional[Union[BackgroundTask, List[BackgroundTask]]] = None,
    encoding: str = "utf-8",
    validate_headers: bool = True,
)
```

**Parameters:**
- `content` — Response body (auto-encoded based on type)
- `status` — HTTP status code (default 200)
- `headers` — Response headers (supports multi-value for Set-Cookie)
- `media_type` — Content-Type override (auto-detected if None)
- `background` — Background task(s) to run after response sent
- `encoding` — Text encoding (default utf-8)
- `validate_headers` — Validate headers against injection (default True)

**Content Type Handling:**
- `bytes` → sent as-is
- `str` → encoded with `encoding`
- `dict` / `list` → JSON encoded
- `AsyncIterator[bytes]` → streamed with chunked encoding
- `Iterator[bytes]` → streamed in executor (non-blocking)
- `Awaitable[Any]` → awaited, then encoded (e.g., template coroutines)

---

### Factory Methods

#### `Response.json(obj, status=200, *, encoder=None, **kwargs)`

Create JSON response. Uses `orjson` if available, falls back to stdlib `json`.

```python
return Response.json({"status": "ok", "data": items})
```

#### `Response.html(content, status=200)`

Create HTML response.

```python
return Response.html("<h1>Hello World</h1>")
```

#### `Response.text(content, status=200)`

Create plain text response.

```python
return Response.text("Hello, World!")
```

#### `Response.redirect(url, status=307, *, headers=None)`

Create redirect response (default 307 Temporary Redirect).

```python
return Response.redirect("/login", status=302)
```

#### `Response.stream(iterator, status=200, media_type="application/octet-stream")`

Create streaming response from async or sync iterator.

```python
async def data_stream():
    for chunk in large_data:
        yield chunk.encode()

return Response.stream(data_stream())
```

#### `Response.sse(event_iter, status=200)`

Create Server-Sent Events response.

```python
async def events():
    while True:
        yield ServerSentEvent(data="ping", event="heartbeat")
        await asyncio.sleep(30)

return Response.sse(events())
```

#### `Response.file(path, *, filename=None, media_type=None, status=200, use_sendfile=True, chunk_size=65536)`

Stream file download. Supports:
- Auto MIME type detection
- Content-Disposition header
- Efficient async file I/O (via `aiofiles` if available)
- **Phase 2:** Range requests (206 Partial Content)

```python
return Response.file("/data/report.pdf", filename="Q4-Report.pdf")
```

#### `Response.render(template_name, context, *, engine=None, status=200, content_type="text/html; charset=utf-8", request_ctx=None)`

Render template and return response. Integrates with `TemplateEngine`.

```python
return Response.render(
    "dashboard.html",
    {"user": user, "stats": stats},
    engine=self.templates
)
```

---

### Cookie Methods

#### `set_cookie(name, value, *, max_age=None, expires=None, path="/", domain=None, secure=True, httponly=True, samesite="Lax", signed=False, signer=None)`

Set a cookie. Produces RFC-compliant `Set-Cookie` header.

**Security Defaults:**
- `secure=True` — HTTPS only
- `httponly=True` — No JS access
- `samesite="Lax"` — CSRF protection

**Signed Cookies:**
```python
from aquilia.response import CookieSigner

signer = CookieSigner("your-secret-key")
response.set_cookie("session", "user123", signed=True, signer=signer)
```

**Multiple Cookies:**
Multiple `set_cookie()` calls produce multiple `Set-Cookie` headers (RFC compliant).

```python
response.set_cookie("session_id", "abc123")
response.set_cookie("preferences", "dark_mode")
# → Two separate Set-Cookie headers
```

#### `delete_cookie(name, path="/", domain=None)`

Delete cookie by setting `Max-Age=0` and expiry in the past.

```python
response.delete_cookie("session_id")
```

---

### Header Methods

#### `set_header(name, value)`

Set header (replaces existing).

```python
response.set_header("x-custom-header", "value")
```

#### `add_header(name, value)`

Add header (supports multiple values).

```python
response.add_header("vary", "Accept-Encoding")
response.add_header("vary", "Cookie")
# → Vary: Accept-Encoding, Cookie (or multiple headers depending on header type)
```

#### `unset_header(name)`

Remove header.

```python
response.unset_header("x-debug-info")
```

**Header Validation:**  
By default (`validate_headers=True`), headers are validated to prevent injection attacks:
- Control characters → `InvalidHeaderError`
- Newlines (`\r`, `\n`) → `InvalidHeaderError`

Disable if needed (not recommended): `Response(..., validate_headers=False)`

---

### Caching Methods

#### `set_etag(etag, weak=False)`

Set ETag header.

```python
etag = generate_etag(response_body)
response.set_etag(etag)
# → ETag: "abc123..."

response.set_etag(etag, weak=True)
# → ETag: W/"abc123..."
```

#### `set_last_modified(dt: datetime)`

Set Last-Modified header.

```python
from datetime import datetime, timezone

response.set_last_modified(datetime.now(timezone.utc))
# → Last-Modified: Wed, 26 Jan 2026 12:00:00 GMT
```

#### `cache_control(**directives)`

Set Cache-Control header.

```python
# Public cache for 1 hour
response.cache_control(max_age=3600, public=True)

# No caching
response.cache_control(no_cache=True, no_store=True)

# Must revalidate
response.cache_control(max_age=3600, must_revalidate=True)
```

**Directive conversion:**  
Snake_case → kebab-case: `max_age` → `max-age`

#### `secure_headers(*, hsts=True, hsts_max_age=31536000, csp=None, frame_options="DENY", ...)`

Set recommended security headers.

```python
response.secure_headers(
    hsts=True,
    csp="default-src 'self'; script-src 'self' 'unsafe-inline'",
    frame_options="SAMEORIGIN"
)
```

**Sets:**
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`
- `X-Frame-Options`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection`
- `Referrer-Policy`

---

### ASGI Send

#### `async send_asgi(send: Callable, request: Optional[Request] = None)`

Send response via ASGI. Called automatically by Aquilia runtime.

**Behavior:**
1. Sends `http.response.start` with status and headers
2. Sends body based on content type:
   - **Async iterator** → chunks with `more_body=True`, final empty chunk with `more_body=False`
   - **Sync iterator** → run in executor to avoid blocking event loop
   - **Coroutine** → await, then send result
   - **Bytes/str/dict** → encode and send single chunk
3. Handles errors:
   - Template render errors → `TemplateRenderError` fault
   - Client disconnect → `ClientDisconnectError` fault
   - Stream errors → `ResponseStreamError` fault
4. Runs background tasks after body sent
5. Emits metrics (bytes sent, duration)

**Phase 2:** Range request support via `request` parameter.

---

## Helper Classes

### `BackgroundTask` (Protocol)

```python
class BackgroundTask(Protocol):
    async def run(self) -> None:
        ...
```

### `CallableBackgroundTask`

```python
from aquilia.response import CallableBackgroundTask

async def cleanup():
    await database.close()

task = CallableBackgroundTask(cleanup)
response = Response.json(data, background=task)
```

### `ServerSentEvent`

```python
from aquilia.response import ServerSentEvent

event = ServerSentEvent(
    data="User joined",
    id="msg-123",
    event="user_join",
    retry=5000
)
```

### `CookieSigner`

```python
from aquilia.response import CookieSigner

signer = CookieSigner("secret-key", algorithm="sha256")

# Sign
signed_value = signer.sign("user123")

# Verify
original = signer.unsign(signed_value)  # → "user123" or None if invalid
```

---

## Examples

### JSON Endpoint with Caching

```python
@GET("/api/data")
async def get_data(self, ctx):
    data = compute_expensive_data()
    
    response = Response.json(data)
    
    # Cache for 5 minutes
    response.cache_control(max_age=300, public=True)
    
    # Set ETag
    etag = generate_etag(response._encode_body(data))
    response.set_etag(etag)
    
    return response
```

### Conditional Response (304)

```python
from aquilia.response import check_not_modified, not_modified_response

@GET("/document/{id}")
async def get_document(self, ctx):
    doc = await db.get_document(ctx.params["id"])
    
    etag = generate_etag(doc.content.encode())
    last_modified = doc.updated_at
    
    # Check if client has cached version
    if check_not_modified(ctx.request, etag=etag, last_modified=last_modified):
        return not_modified_response(etag=etag)
    
    response = Response.html(doc.content)
    response.set_etag(etag)
    response.set_last_modified(last_modified)
    
    return response
```

### Streaming Download with Progress

```python
@GET("/download/large-file")
async def download_large(self, ctx):
    file_path = Path("/data/large.zip")
    
    async def progress_stream():
        total_size = file_path.stat().st_size
        sent = 0
        
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(65536)
                if not chunk:
                    break
                
                sent += len(chunk)
                # Could emit progress metric here
                logger.info(f"Sent {sent}/{total_size} bytes")
                
                yield chunk
    
    return Response.stream(progress_stream(), media_type="application/zip")
```

### SSE with Retry

```python
@GET("/live-updates")
async def live_updates(self, ctx):
    async def event_source():
        try:
            async for update in monitor.subscribe():
                yield ServerSentEvent(
                    data=json.dumps(update),
                    id=update["id"],
                    event="update",
                    retry=3000  # Reconnect after 3s
                )
        except asyncio.CancelledError:
            logger.info("Client disconnected from SSE")
            raise
    
    return Response.sse(event_source())
```

### Background Task Example

```python
@POST("/api/process")
async def process(self, ctx):
    data = await ctx.request.json()
    
    # Start processing
    task_id = generate_task_id()
    
    async def process_in_background():
        result = await heavy_processing(data)
        await db.save_result(task_id, result)
        await notify_user(ctx.identity.user_id, task_id)
    
    task = CallableBackgroundTask(process_in_background)
    
    return Response.json(
        {"task_id": task_id, "status": "processing"},
        status=202,
        background=task
    )
```

---

## Security Checklist

### Headers

✅ **Use `secure_headers()`** for recommended security headers  
✅ **Enable HSTS** on production HTTPS sites  
✅ **Set CSP** to restrict script sources  
✅ **Validate all headers** (enabled by default)  
✅ **Avoid exposing sensitive info** in custom headers  

### Cookies

✅ **Always use `secure=True`** on HTTPS  
✅ **Always use `httponly=True`** unless JS needs access  
✅ **Set `samesite="Strict"` or `"Lax"`** for CSRF protection  
✅ **Sign sensitive cookies** with `CookieSigner`  
✅ **Rotate signing keys** periodically  
✅ **Set short `max_age`** for session cookies  

### Caching

✅ **Use `no_cache`/`no_store`** for sensitive data  
✅ **Set `private`** for user-specific data  
✅ **Validate ETags** on conditional requests  
✅ **Use weak ETags** for frequently changing content  

### Streaming

✅ **Limit chunk sizes** to prevent memory exhaustion  
✅ **Set timeouts** for slow clients  
✅ **Handle client disconnect** gracefully  
✅ **Validate file paths** before streaming  

---

## Background Tasks

Background tasks run **after** the response body is fully sent to the client. They are useful for:

- Logging/analytics
- Cache updates
- Sending notifications
- Cleanup operations

### Behavior

- Tasks run in order provided
- Errors in tasks are logged but don't affect response
- Tasks are **cancelled** if client disconnects during send (configurable in Phase 2)

### Integration with Runtime

Aquilia runtime executes background tasks via lifecycle coordinator. Ensure your ASGI server supports background task execution (most do).

---

## Integration

### Controllers

Controllers return `Response` instances. The flow runner calls `await response.send_asgi(send, request)`.

```python
class MyController(Controller):
    @GET("/")
    async def index(self, ctx):
        return Response.html("<h1>Hello</h1>")
```

### TemplateEngine

`Response.render()` integrates with `TemplateEngine`:

```python
# Auto-resolved from DI if request_ctx has container
return Response.render("page.html", context, request_ctx=ctx)

# Or explicit
return Response.render("page.html", context, engine=self.templates)
```

### FaultEngine

Response errors are converted to Aquilia Faults:

- `TemplateRenderError` — Template rendering failed
- `ResponseStreamError` — Stream error during send
- `ClientDisconnectError` — Client disconnected
- `InvalidHeaderError` — Header injection attempt
- `RangeNotSatisfiableError` — Invalid Range request (Phase 2)

### Tracing & Metrics

Response emits metrics on send completion:
- `response.bytes_sent` — Total bytes sent
- `response.duration_seconds` — Send duration
- `response.status_code` — HTTP status

Integrate with your metrics backend via lifecycle hooks or middleware.

---

## Phase 2 Features (TODO)

The following features are planned for Phase 2:

### Range Requests (206 Partial Content)

```python
# Automatic Range header parsing
response = Response.file(path, use_sendfile=True)
# → 206 if Range header present
# → Content-Range: bytes 0-1023/5000
```

### Sendfile Optimization

Use platform `sendfile()` for efficient file streaming when supported.

### Compression (gzip, brotli)

```python
response.compress(algorithms=["br", "gzip"])
# or
response.auto_compress(ctx.request.headers.get("accept-encoding"))
```

### Advanced Background Task Control

```python
task = CallableBackgroundTask(func, run_on_disconnect=True)
```

### Cookie Keyring (Key Rotation)

```python
signer = CookieSigner(keyring=["new-key", "old-key"])
signer.unsign(value)  # Tries all keys
```

---

## See Also

- [Request Documentation](request.md)
- [Controllers Guide](CONTROLLERS.md)
- [Template Integration](TEMPLATES_DEEP_INTEGRATION.md)
- [Fault System](AQUILA_FAULTS.md)

---

## License

Part of Aquilia framework. See [LICENSE](../LICENSE).
