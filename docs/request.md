# Request API Reference

Production-grade HTTP request handling for Aquilia.

## Overview

The `Request` class is a first-class, typed, async object that wraps ASGI `scope`, `receive`, and `send` callables, providing safe and ergonomic APIs for accessing request data.

## Features

- **Streaming-first**: Incremental body reading with `iter_bytes()`, `iter_text()`
- **Idempotent caching**: Repeated calls to `body()`, `json()`, `form()` are efficient
- **Robust parsing**: URL, query params, headers, cookies, JSON, forms, multipart
- **File uploads**: Streaming multipart parsing with automatic disk spilling
- **Security limits**: Configurable max body size, field count, file size
- **Client IP detection**: Proxy-aware with trust configuration
- **Content negotiation**: Helper methods for Accept, Content-Type, Range, etc.
- **Fault integration**: Typed exceptions that integrate with AquilaFaults

## Installation

Required dependencies:

```bash
pip install python-multipart  # For multipart/form-data parsing
pip install aiofiles           # For async file I/O (optional but recommended)
```

## Basic Usage

### Creating a Request

```python
from aquilia.request import Request

# In an ASGI application
async def app(scope, receive, send):
    request = Request(scope, receive, send)
    
    # Access request properties
    print(f"{request.method} {request.path}")
    print(f"Client IP: {request.client_ip()}")
```

### Reading Body

```python
# Read complete body
body = await request.body()

# Read as text
text = await request.text()

# Parse JSON
data = await request.json()
```

### Streaming Body

```python
# Stream bytes
async for chunk in request.iter_bytes():
    process_chunk(chunk)

# Stream text
async for text_chunk in request.iter_text():
    process_text(text_chunk)
```

## API Reference

### Constructor

```python
Request(
    scope: Mapping[str, Any],
    receive: Callable[..., Awaitable[dict]],
    send: Optional[Callable] = None,
    *,
    max_body_size: int = 10_485_760,        # 10 MiB
    max_field_count: int = 1000,
    max_file_size: int = 2_147_483_648,     # 2 GiB
    upload_tempdir: Optional[PathLike] = None,
    trust_proxy: Union[bool, List[str]] = False,
    chunk_size: int = 64 * 1024,
    json_max_size: int = 10_485_760,
    json_max_depth: int = 64,
    form_memory_threshold: int = 1024 * 1024,  # 1 MiB
)
```

### Properties

#### Basic Properties

```python
request.method -> str                    # HTTP method (GET, POST, etc.)
request.http_version -> str              # HTTP version (1.1, 2, etc.)
request.path -> str                      # Request path (decoded)
request.raw_path -> bytes                # Raw path from ASGI
request.query_string -> str              # Raw query string
request.client -> Optional[tuple]        # (host, port) tuple
request.state -> Dict[str, Any]          # Per-request state dict
```

### Query Parameters

```python
# Get all query params as MultiDict
params = request.query_params()

# Get single param
value = request.query_param("key")
value = request.query_param("key", default="default")

# Access via MultiDict
params.get("key")                        # First value
params.get_all("key")                    # All values
```

**Example:**

```python
# URL: /search?q=python&tag=web&tag=async
params = request.query_params()

query = params.get("q")                  # "python"
tags = params.get_all("tag")            # ["web", "async"]
```

### Headers

```python
# Get headers object
headers = request.headers()

# Get single header (case-insensitive)
value = request.header("content-type")
value = request.header("User-Agent", default="Unknown")

# Check if header exists
if request.has_header("authorization"):
    ...

# Access via Headers object
headers.get("content-type")
headers.get_all("accept")               # All values for header
headers.has("authorization")
```

**Example:**

```python
content_type = request.header("content-type")
if request.is_json():
    data = await request.json()
```

### Cookies

```python
# Get all cookies
cookies = request.cookies()

# Get single cookie
value = request.cookie("session")
value = request.cookie("session", default=None)
```

**Example:**

```python
session_id = request.cookie("session_id")
if session_id:
    session = await load_session(session_id)
```

### URL & Client IP

```python
# Get full URL object
url = request.url()
print(url.scheme)                        # "https"
print(url.host)                          # "example.com"
print(url.path)                          # "/api/users"
print(url.query)                         # "page=1"
print(str(url))                          # Full URL string

# Get base URL
base = request.base_url()                # scheme + host + root_path

# Build URL for route (requires router integration)
url = request.url_for("user_detail", user_id=123)

# Get client IP (proxy-aware)
ip = request.client_ip()
```

**Example:**

```python
# With trust_proxy=True
request = Request(scope, receive, trust_proxy=True)
ip = request.client_ip()  # Respects X-Forwarded-For header
```

### Body Reading

#### Single-shot Methods

```python
# Read complete body as bytes
body = await request.body()

# Read body as text
text = await request.text()
text = await request.text(encoding="latin-1")

# Read exact number of bytes
data = await request.readexactly(100)
```

#### Streaming Methods

```python
# Stream body chunks
async for chunk in request.iter_bytes():
    print(f"Received {len(chunk)} bytes")

# Stream with custom chunk size
async for chunk in request.iter_bytes(chunk_size=8192):
    process(chunk)

# Stream as text
async for text in request.iter_text(encoding="utf-8"):
    print(text)
```

### JSON Parsing

```python
# Parse JSON
data = await request.json()

# Parse with Pydantic model
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

user = await request.json(model=User)
print(user.name, user.age)

# Parse with strict validation
data = await request.json(strict=True)
```

**Security:**
- Enforces `json_max_size` limit
- Enforces `json_max_depth` to prevent deep nesting attacks
- Validates against model if provided

**Example:**

```python
try:
    data = await request.json()
except InvalidJSON as e:
    return error_response("Invalid JSON", 400)
except PayloadTooLarge as e:
    return error_response("Payload too large", 413)
```

### Form Data

#### URL-encoded Forms

```python
# Parse application/x-www-form-urlencoded
form_data = await request.form()

# Get field values
name = form_data.get_field("name")
tags = form_data.get_all_fields("tag")
```

**Example:**

```python
# POST /submit with body: name=John&age=30
form = await request.form()
name = form.get_field("name")  # "John"
age = form.get_field("age")    # "30"
```

#### Multipart Forms & File Uploads

```python
# Parse multipart/form-data
form_data = await request.multipart()

# Get form fields
description = form_data.get_field("description")

# Get uploaded file
upload = form_data.get_file("avatar")
if upload:
    print(upload.filename)
    print(upload.content_type)
    print(upload.size)
    
    # Read file content
    content = await upload.read()
    
    # Stream file content
    async for chunk in upload.stream():
        process(chunk)
    
    # Save file
    await upload.save("/uploads/avatar.jpg")

# Get all files for a field
files = form_data.get_all_files("attachments")
for file in files:
    await file.save(f"/uploads/{file.filename}")
```

**Example:**

```python
# Handle file upload
form = await request.multipart()
avatar = form.get_file("avatar")

if avatar:
    # Sanitized filename
    safe_name = avatar.filename
    
    # Save to disk
    path = await request.save_upload(avatar, f"./uploads/{safe_name}")
    print(f"Saved to {path}")

# Always cleanup
await request.cleanup()
```

### Upload Store Integration

```python
# Use custom storage backend
from aquilia._uploads import LocalUploadStore

store = LocalUploadStore(upload_dir="./uploads")

form = await request.multipart()
file = form.get_file("document")

if file:
    path = await request.stream_upload_to_store(file, store)
    print(f"Stored at {path}")
```

### Content Negotiation

```python
# Check if JSON content
if request.is_json():
    data = await request.json()

# Check accepted media types
if request.accepts("application/json"):
    return json_response(data)
elif request.accepts("text/html"):
    return html_response(template)

# Get content type
ct = request.content_type()

# Get content length
length = request.content_length()
```

### Conditional & Range Requests

```python
# Parse Range header
range_header = request.range()
if range_header:
    for start, end in range_header.ranges:
        print(f"Range: {start}-{end}")

# Parse If-Modified-Since
ims = request.if_modified_since()
if ims:
    if resource.modified_at <= ims:
        return not_modified_response()

# Parse If-None-Match (ETag)
etag = request.if_none_match()
if etag == resource.etag:
    return not_modified_response()
```

### Authorization

```python
# Parse Authorization header
scheme = request.auth_scheme()      # "Bearer" or "Basic"
creds = request.auth_credentials()  # Token or encoded credentials

if scheme == "Bearer":
    token = creds
    user = await verify_token(token)
```

## Controller Integration

Using Request in Aquilia controllers:

```python
from aquilia.controller import Controller, route
from aquilia.request import Request

class UserController(Controller):
    
    @route.post("/users")
    async def create_user(self, ctx):
        request: Request = ctx.request
        
        # Parse JSON payload
        try:
            data = await request.json()
        except InvalidJSON:
            return self.bad_request("Invalid JSON")
        
        user = await self.user_service.create(data)
        return self.created(user)
    
    @route.post("/upload")
    async def upload_file(self, ctx):
        request: Request = ctx.request
        
        # Parse multipart form
        form = await request.multipart()
        file = form.get_file("document")
        
        if not file:
            return self.bad_request("No file uploaded")
        
        # Save file
        path = await request.save_upload(
            file, 
            f"./uploads/{file.filename}"
        )
        
        # Cleanup temp files
        await request.cleanup()
        
        return self.ok({"path": str(path)})
```

## Security Checklist

### Size Limits

- **`max_body_size`**: Prevent memory exhaustion (default: 10 MiB)
- **`max_file_size`**: Limit individual file uploads (default: 2 GiB)
- **`max_field_count`**: Prevent field count attacks (default: 1000)
- **`json_max_size`**: Limit JSON payload size (default: 10 MiB)
- **`json_max_depth`**: Prevent deep nesting attacks (default: 64)

### Filename Sanitization

All uploaded filenames are automatically sanitized:
- Path components removed (`/`, `\`, `..`)
- Null bytes stripped
- Dangerous characters replaced
- Length limited to 255 chars

### Proxy Trust

When using reverse proxies:

```python
# Trust all proxies (dev/internal only)
request = Request(scope, receive, trust_proxy=True)

# Don't trust proxies (default, secure)
request = Request(scope, receive, trust_proxy=False)

# Trust specific IPs (production)
request = Request(
    scope, receive, 
    trust_proxy=["10.0.0.0/8", "172.16.0.0/12"]
)
```

### Temporary File Cleanup

Always cleanup uploaded files:

```python
try:
    form = await request.multipart()
    # Process files...
finally:
    await request.cleanup()
```

## Performance Tips

### Streaming for Large Payloads

For large uploads or downloads, use streaming:

```python
# Bad: Loads entire body into memory
body = await request.body()

# Good: Stream in chunks
async for chunk in request.iter_bytes():
    await process_chunk(chunk)
```

### Memory Threshold for Uploads

Configure `form_memory_threshold` to control when files spill to disk:

```python
# Keep files < 512 KB in memory
request = Request(
    scope, receive,
    form_memory_threshold=512 * 1024
)
```

### Chunk Size

Adjust chunk size for your workload:

```python
# Larger chunks for high-throughput
request = Request(scope, receive, chunk_size=256 * 1024)

# Smaller chunks for low-latency
request = Request(scope, receive, chunk_size=8192)
```

## Error Handling

### Request Faults

```python
from aquilia.request import (
    BadRequest,
    PayloadTooLarge,
    UnsupportedMediaType,
    ClientDisconnect,
    InvalidJSON,
    MultipartParseError,
)

try:
    data = await request.json()
except InvalidJSON as e:
    # Malformed JSON
    return error_response(str(e), 400)
except PayloadTooLarge as e:
    # Exceeded size limit
    max_size = e.context["max_allowed"]
    return error_response(f"Max size: {max_size}", 413)
except ClientDisconnect:
    # Client disconnected
    logger.info("Client disconnected during request")
```

### Integration with FaultEngine

Request faults integrate with AquilaFaults:

```python
from aquilia.faults import FaultEngine

engine = FaultEngine()

try:
    await request.body()
except PayloadTooLarge as fault:
    result = await engine.handle(fault, context={"request": request})
    # Fault engine can transform, log, alert, etc.
```

## Migration from Old Request

### Before

```python
# Old API
query = request.query  # Dict[str, list]
headers = request.headers  # Dict[str, str]
body = await request.body()
json_data = await request.json()
```

### After

```python
# New API
query = request.query_params()  # MultiDict
headers = request.headers()     # Headers object
body = await request.body()     # Same
json_data = await request.json()  # Same, but with validation
```

### Key Changes

1. **Query params**: Now returns `MultiDict` instead of `Dict[str, list]`
2. **Headers**: Returns `Headers` object with case-insensitive access
3. **New methods**: `multipart()`, `files()`, `client_ip()`, etc.
4. **Typed returns**: URL, FormData, UploadFile objects
5. **Security limits**: Configurable via constructor

## Examples

### Login Endpoint

```python
@route.post("/login")
async def login(self, ctx):
    request: Request = ctx.request
    
    try:
        data = await request.json()
    except InvalidJSON:
        return self.bad_request("Invalid JSON")
    
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return self.bad_request("Missing credentials")
    
    user = await self.auth.authenticate(username, password)
    if not user:
        return self.unauthorized("Invalid credentials")
    
    token = await self.auth.create_token(user)
    return self.ok({"token": token})
```

### File Upload with Metadata

```python
@route.post("/documents")
async def upload_document(self, ctx):
    request: Request = ctx.request
    
    try:
        form = await request.multipart()
    except MultipartParseError as e:
        return self.bad_request(f"Upload failed: {e}")
    
    # Get form fields
    title = form.get_field("title")
    description = form.get_field("description")
    
    # Get uploaded file
    file = form.get_file("document")
    if not file:
        return self.bad_request("No document uploaded")
    
    try:
        # Save to storage
        path = await request.save_upload(
            file,
            f"./documents/{file.filename}",
            overwrite=False
        )
        
        # Create database record
        doc = await self.db.documents.create({
            "title": title,
            "description": description,
            "filename": file.filename,
            "path": str(path),
            "size": file.size,
            "content_type": file.content_type,
        })
        
        return self.created(doc)
    
    finally:
        await request.cleanup()
```

### Streaming Response

```python
@route.get("/export")
async def export_data(self, ctx):
    request: Request = ctx.request
    
    # Check client accepts CSV
    if not request.accepts("text/csv"):
        return self.not_acceptable("Only CSV export supported")
    
    # Stream CSV generation
    async def generate_csv():
        yield "id,name,email\n"
        async for user in self.db.users.stream():
            yield f"{user.id},{user.name},{user.email}\n"
    
    return self.stream(generate_csv(), content_type="text/csv")
```

## Advanced Topics

### Custom Upload Store

```python
from aquilia._uploads import UploadStore
import boto3

class S3UploadStore:
    def __init__(self, bucket: str):
        self.s3 = boto3.client("s3")
        self.bucket = bucket
        self._buffers = {}
    
    async def write_chunk(self, upload_id: str, chunk: bytes):
        if upload_id not in self._buffers:
            self._buffers[upload_id] = bytearray()
        self._buffers[upload_id].extend(chunk)
    
    async def finalize(self, upload_id: str, metadata=None):
        data = self._buffers.pop(upload_id)
        key = f"uploads/{metadata['filename']}"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=bytes(data),
            ContentType=metadata.get("content_type"),
        )
        
        return f"s3://{self.bucket}/{key}"
    
    async def abort(self, upload_id: str):
        self._buffers.pop(upload_id, None)

# Usage
store = S3UploadStore("my-bucket")
form = await request.multipart()
file = form.get_file("document")
s3_url = await request.stream_upload_to_store(file, store)
```

### Request Middleware

```python
class LoggingMiddleware:
    async def __call__(self, scope, receive, send):
        request = Request(scope, receive, send)
        
        logger.info(
            f"{request.method} {request.path}",
            extra={
                "client_ip": request.client_ip(),
                "user_agent": request.header("user-agent"),
            }
        )
        
        # Continue processing
        await self.app(scope, receive, send)
```

## See Also

- [Controllers Guide](./CONTROLLERS.md)
- [Middleware Guide](./MIDDLEWARE.md)
- [AquilaFaults Documentation](./AQUILA_FAULTS.md)
- [Response API](./response.md)
