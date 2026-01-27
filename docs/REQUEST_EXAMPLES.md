# Request Usage Examples

Quick examples showing how to use the production-grade Request API in Aquilia controllers and applications.

## Basic Request Handling

```python
from aquilia import Controller, route, Request

class APIController(Controller):
    
    @route.get("/users")
    async def list_users(self, ctx):
        request: Request = ctx.request
        
        # Query parameters
        page = int(request.query_param("page", "1"))
        limit = int(request.query_param("limit", "10"))
        
        users = await self.db.users.paginate(page, limit)
        return self.ok(users)
    
    @route.post("/login")
    async def login(self, ctx):
        request: Request = ctx.request
        
        # Parse JSON with validation
        from pydantic import BaseModel
        
        class LoginRequest(BaseModel):
            username: str
            password: str
        
        try:
            data = await request.json(model=LoginRequest)
        except Exception as e:
            return self.bad_request(f"Invalid request: {e}")
        
        # Authenticate
        user = await self.auth.authenticate(
            data.username, 
            data.password
        )
        
        if not user:
            return self.unauthorized("Invalid credentials")
        
        token = await self.auth.create_token(user)
        return self.ok({"token": token, "user": user})
```

## File Upload Handling

```python
from aquilia import Controller, route, Request
from pathlib import Path

class DocumentController(Controller):
    
    @route.post("/documents")
    async def upload_document(self, ctx):
        request: Request = ctx.request
        
        try:
            # Parse multipart form data
            form = await request.multipart()
            
            # Get form fields
            title = form.get_field("title")
            category = form.get_field("category", "general")
            
            # Get uploaded file
            file = form.get_file("document")
            if not file:
                return self.bad_request("No document uploaded")
            
            # Security: Check file size and type
            if file.size and file.size > 50 * 1024 * 1024:  # 50 MB
                return self.bad_request("File too large")
            
            allowed_types = ["application/pdf", "text/plain"]
            if file.content_type not in allowed_types:
                return self.bad_request("Invalid file type")
            
            # Save file
            upload_dir = Path("./uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_path = await request.save_upload(
                file,
                upload_dir / file.filename,
                overwrite=False
            )
            
            # Create database record
            doc = await self.db.documents.create({
                "title": title,
                "category": category,
                "filename": file.filename,
                "path": str(file_path),
                "size": file.size,
                "content_type": file.content_type,
            })
            
            return self.created(doc)
        
        finally:
            # Always cleanup temp files
            await request.cleanup()
    
    @route.post("/upload-multiple")
    async def upload_multiple(self, ctx):
        request: Request = ctx.request
        
        try:
            form = await request.multipart()
            
            # Get multiple files for same field
            files = form.get_all_files("attachments")
            
            saved_files = []
            for file in files:
                path = await file.save(f"./uploads/{file.filename}")
                saved_files.append({
                    "filename": file.filename,
                    "size": file.size,
                    "path": str(path),
                })
            
            return self.ok({"files": saved_files})
        
        finally:
            await request.cleanup()
```

## Advanced Usage

### Streaming Large Payloads

```python
@route.post("/upload-stream")
async def stream_upload(self, ctx):
    request: Request = ctx.request
    
    # Stream body without loading into memory
    size = 0
    hash_obj = hashlib.sha256()
    
    async for chunk in request.iter_bytes():
        size += len(chunk)
        hash_obj.update(chunk)
        
        # Process chunk (write to disk, upload to S3, etc.)
        await self.storage.write_chunk(chunk)
    
    checksum = hash_obj.hexdigest()
    
    return self.ok({
        "size": size,
        "checksum": checksum,
    })
```

### Client IP Detection with Proxy

```python
@route.post("/track")
async def track_event(self, ctx):
    request: Request = ctx.request
    
    # Get real client IP (respects X-Forwarded-For if trust_proxy=True)
    client_ip = request.client_ip()
    user_agent = request.header("user-agent", "Unknown")
    
    await self.analytics.track_event(
        event="page_view",
        ip=client_ip,
        user_agent=user_agent,
    )
    
    return self.ok({"status": "tracked"})
```

### Form Data with Validation

```python
from aquilia._datastructures import MultiDict

@route.post("/subscribe")
async def subscribe(self, ctx):
    request: Request = ctx.request
    
    # Parse URL-encoded form
    form = await request.form()
    
    email = form.get_field("email")
    tags = form.get_all_fields("tag")  # Multiple values
    
    if not email or "@" not in email:
        return self.bad_request("Invalid email")
    
    await self.newsletter.subscribe(email, tags)
    
    return self.ok({"message": "Subscribed successfully"})
```

### Content Negotiation

```python
@route.get("/data")
async def get_data(self, ctx):
    request: Request = ctx.request
    
    data = await self.service.get_data()
    
    # Return JSON or CSV based on Accept header
    if request.accepts("text/csv"):
        csv = self.to_csv(data)
        return self.ok(csv, content_type="text/csv")
    
    elif request.accepts("application/json"):
        return self.json(data)
    
    else:
        return self.not_acceptable("Supported: application/json, text/csv")
```

### Range Requests

```python
@route.get("/files/{file_id}")
async def download_file(self, ctx):
    request: Request = ctx.request
    file_id = ctx.path_params["file_id"]
    
    file_info = await self.storage.get_file(file_id)
    
    # Check for Range header
    range_header = request.range()
    if range_header:
        # Serve partial content
        for start, end in range_header.ranges:
            content = await self.storage.read_range(file_id, start, end)
            return self.partial_content(
                content,
                start=start,
                end=end,
                total=file_info.size,
            )
    
    # Serve full file
    content = await self.storage.read_file(file_id)
    return self.ok(content, content_type=file_info.content_type)
```

### Custom Upload Store (S3)

```python
from aquilia._uploads import UploadStore
import aioboto3

class S3UploadStore:
    """Upload directly to S3."""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.session = aioboto3.Session()
    
    async def write_chunk(self, upload_id: str, chunk: bytes):
        # Implement S3 multipart upload
        pass
    
    async def finalize(self, upload_id: str, metadata=None):
        # Complete multipart upload
        key = f"uploads/{metadata['filename']}"
        return f"s3://{self.bucket}/{key}"
    
    async def abort(self, upload_id: str):
        # Abort multipart upload
        pass

# Usage
@route.post("/upload-s3")
async def upload_to_s3(self, ctx):
    request: Request = ctx.request
    
    form = await request.multipart()
    file = form.get_file("document")
    
    if file:
        store = S3UploadStore(bucket="my-bucket")
        s3_url = await request.stream_upload_to_store(file, store)
        return self.ok({"url": s3_url})
```

## Error Handling

```python
from aquilia.request import (
    BadRequest,
    PayloadTooLarge,
    InvalidJSON,
    ClientDisconnect,
)

@route.post("/process")
async def process_data(self, ctx):
    request: Request = ctx.request
    
    try:
        # Parse JSON with size limits
        data = await request.json()
        
        # Process...
        result = await self.service.process(data)
        
        return self.ok(result)
    
    except InvalidJSON as e:
        # Malformed JSON
        return self.bad_request(f"Invalid JSON: {e}")
    
    except PayloadTooLarge as e:
        # Body too large
        max_size = e.context["max_allowed"]
        return self.error(
            f"Payload exceeds {max_size} bytes",
            status=413
        )
    
    except ClientDisconnect:
        # Client disconnected during processing
        self.logger.info("Client disconnected")
        return None
```

## Configuration

```python
from aquilia import AquiliaServer, Request

# Configure request limits
async def create_request(scope, receive, send):
    return Request(
        scope,
        receive,
        send,
        max_body_size=50 * 1024 * 1024,      # 50 MB
        max_file_size=500 * 1024 * 1024,     # 500 MB
        max_field_count=2000,
        json_max_size=10 * 1024 * 1024,      # 10 MB
        json_max_depth=32,
        form_memory_threshold=2 * 1024 * 1024,  # 2 MB
        trust_proxy=True,                     # Enable X-Forwarded-For
        upload_tempdir="/tmp/aquilia-uploads",
    )

# Use in server
server = AquiliaServer(
    manifest="app.crous",
    # Pass request factory if needed
)
```

## Testing

```python
import pytest
from aquilia.request import Request

@pytest.mark.asyncio
async def test_json_parsing():
    body = b'{"name": "test", "value": 123}'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    data = await request.json()
    
    assert data["name"] == "test"
    assert data["value"] == 123
```

## See Also

- [Full Request API Documentation](../docs/REQUEST.md)
- [Controllers Guide](../docs/CONTROLLERS.md)
- [File Upload Best Practices](../docs/UPLOADS.md)
