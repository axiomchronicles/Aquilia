# Request Quick Reference

One-page reference for the Aquilia Request API.

## Import

```python
from aquilia import Request
from aquilia.request import (
    BadRequest, PayloadTooLarge, InvalidJSON, 
    ClientDisconnect, UnsupportedMediaType
)
```

## Common Patterns

### Basic Request Info

```python
request.method              # GET, POST, etc.
request.path                # /api/users
request.client_ip()         # 203.0.113.1 (proxy-aware)
request.url()               # Full URL object
str(request.url())          # https://example.com/api/users?page=1
```

### Query Parameters

```python
page = request.query_param("page", "1")
tags = request.query_params().get_all("tag")
```

### Headers

```python
auth = request.header("authorization")
if request.has_header("x-api-key"):
    api_key = request.header("x-api-key")

ct = request.content_type()
length = request.content_length()
```

### Cookies

```python
session_id = request.cookie("session")
cookies = request.cookies()
```

### Body Reading

```python
# Read all
body = await request.body()
text = await request.text()

# Stream
async for chunk in request.iter_bytes():
    process(chunk)
```

### JSON

```python
# Simple
data = await request.json()

# With validation (Pydantic)
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

user = await request.json(model=User)
```

### Forms

```python
# URL-encoded
form = await request.form()
email = form.get_field("email")
tags = form.get_all_fields("tag")

# Multipart
form = await request.multipart()
title = form.get_field("title")
file = form.get_file("upload")

# Always cleanup
await request.cleanup()
```

### File Uploads

```python
form = await request.multipart()
file = form.get_file("document")

if file:
    print(f"Name: {file.filename}")
    print(f"Type: {file.content_type}")
    print(f"Size: {file.size}")
    
    # Read content
    content = await file.read()
    
    # Or stream
    async for chunk in file.stream():
        process(chunk)
    
    # Or save
    path = await file.save("./uploads/file.pdf")
```

### Content Negotiation

```python
if request.is_json():
    data = await request.json()

if request.accepts("application/json"):
    return json_response(data)
```

### Authorization

```python
scheme = request.auth_scheme()      # Bearer
token = request.auth_credentials()  # abc123xyz
```

### Range Requests

```python
range_header = request.range()
if range_header:
    for start, end in range_header.ranges:
        # Serve bytes [start:end]
        pass
```

## Configuration

```python
Request(
    scope, receive, send,
    max_body_size=10*1024*1024,      # 10 MB
    max_file_size=100*1024*1024,     # 100 MB
    max_field_count=1000,
    json_max_size=10*1024*1024,
    json_max_depth=64,
    trust_proxy=True,                 # Enable X-Forwarded-For
    upload_tempdir="/tmp/uploads",
)
```

## Error Handling

```python
try:
    data = await request.json()
except InvalidJSON:
    return {"error": "Invalid JSON"}, 400
except PayloadTooLarge:
    return {"error": "Payload too large"}, 413
except ClientDisconnect:
    logger.info("Client disconnected")
```

## Security Checklist

✅ Set `max_body_size` (default: 10 MB)
✅ Set `max_file_size` (default: 2 GB)
✅ Set `max_field_count` (default: 1000)
✅ Filenames automatically sanitized
✅ Configure `trust_proxy` correctly
✅ Always call `await request.cleanup()` after file uploads
✅ Validate uploaded content types
✅ Check file sizes before processing

## Controller Example

```python
from aquilia import Controller, route

class FileController(Controller):
    
    @route.post("/upload")
    async def upload(self, ctx):
        request = ctx.request
        
        try:
            form = await request.multipart()
            file = form.get_file("file")
            
            if not file:
                return self.bad_request("No file")
            
            path = await request.save_upload(
                file, 
                f"./uploads/{file.filename}"
            )
            
            return self.ok({"path": str(path)})
        
        finally:
            await request.cleanup()
```

## Testing

```python
import pytest

@pytest.mark.asyncio
async def test_request():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api",
        "query_string": b"key=value",
        "headers": [(b"content-type", b"application/json")],
    }
    
    body = b'{"test": true}'
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    assert request.method == "POST"
    assert request.query_param("key") == "value"
    
    data = await request.json()
    assert data["test"] is True
```

## See Full Documentation

- [Complete API Reference](./docs/REQUEST.md)
- [Usage Examples](./docs/REQUEST_EXAMPLES.md)
- [Migration Guide](./docs/REQUEST.md#migration-from-old-request)
