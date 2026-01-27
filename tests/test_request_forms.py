"""
Test form and multipart parsing for Request.
"""

import pytest
from aquilia.request import Request, UnsupportedMediaType, BadRequest


@pytest.mark.asyncio
async def test_form_urlencoded_simple():
    """Test simple form-urlencoded parsing."""
    body = b"name=John&age=30&city=London"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    form_data = await request.form()
    
    assert form_data.get_field("name") == "John"
    assert form_data.get_field("age") == "30"
    assert form_data.get_field("city") == "London"


@pytest.mark.asyncio
async def test_form_urlencoded_repeated():
    """Test form with repeated field names."""
    body = b"tag=python&tag=web&tag=asyncio"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    form_data = await request.form()
    
    tags = form_data.get_all_fields("tag")
    assert tags == ["python", "web", "asyncio"]


@pytest.mark.asyncio
async def test_form_urlencoded_encoded():
    """Test form with URL encoding."""
    body = b"message=Hello+World&email=user%40example.com"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    form_data = await request.form()
    
    assert form_data.get_field("message") == "Hello World"
    assert form_data.get_field("email") == "user@example.com"


@pytest.mark.asyncio
async def test_form_urlencoded_wrong_content_type():
    """Test form parsing with wrong Content-Type."""
    body = b"name=John"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    with pytest.raises(UnsupportedMediaType):
        await request.form()


@pytest.mark.asyncio
async def test_form_field_count_limit():
    """Test form field count limit."""
    # Create form with many fields
    fields = [f"field{i}=value{i}" for i in range(2000)]
    body = "&".join(fields).encode()
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive, max_field_count=100)
    
    with pytest.raises(BadRequest) as exc_info:
        await request.form()
    
    assert "too many" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_multipart_simple():
    """Test simple multipart form parsing."""
    boundary = b"----boundary123"
    body = (
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="name"\r\n'
        b"\r\n"
        b"John\r\n"
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="age"\r\n'
        b"\r\n"
        b"30\r\n"
        b"------boundary123--\r\n"
    )
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=----boundary123"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    try:
        form_data = await request.multipart()
        assert form_data.get_field("name") == "John"
        assert form_data.get_field("age") == "30"
    except Exception as e:
        # If python-multipart not available, skip
        if "not available" in str(e):
            pytest.skip("python-multipart not available")
        raise


@pytest.mark.asyncio
async def test_multipart_file_upload_small():
    """Test small file upload (in-memory)."""
    boundary = b"----boundary123"
    file_content = b"Hello from file!"
    
    body = (
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="description"\r\n'
        b"\r\n"
        b"Test file\r\n"
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        + file_content + b"\r\n"
        b"------boundary123--\r\n"
    )
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=----boundary123"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    try:
        form_data = await request.multipart()
        
        assert form_data.get_field("description") == "Test file"
        
        upload_file = form_data.get_file("file")
        assert upload_file is not None
        assert upload_file.filename == "test.txt"
        assert upload_file.content_type == "text/plain"
        
        content = await upload_file.read()
        assert content == file_content
        
        # Cleanup
        await request.cleanup()
    
    except Exception as e:
        if "not available" in str(e):
            pytest.skip("python-multipart not available")
        raise


@pytest.mark.asyncio
async def test_multipart_multiple_files():
    """Test multiple file uploads."""
    boundary = b"----boundary123"
    
    body = (
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="file1"; filename="file1.txt"\r\n'
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"Content of file 1\r\n"
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="file2"; filename="file2.txt"\r\n'
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"Content of file 2\r\n"
        b"------boundary123--\r\n"
    )
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=----boundary123"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    try:
        form_data = await request.multipart()
        
        file1 = form_data.get_file("file1")
        file2 = form_data.get_file("file2")
        
        assert file1 is not None
        assert file2 is not None
        assert file1.filename == "file1.txt"
        assert file2.filename == "file2.txt"
        
        # Cleanup
        await request.cleanup()
    
    except Exception as e:
        if "not available" in str(e):
            pytest.skip("python-multipart not available")
        raise


@pytest.mark.asyncio
async def test_multipart_filename_sanitization():
    """Test filename sanitization."""
    boundary = b"----boundary123"
    
    # Dangerous filename with path and special chars
    body = (
        b"------boundary123\r\n"
        b'Content-Disposition: form-data; name="file"; filename="../../etc/passwd"\r\n'
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"malicious\r\n"
        b"------boundary123--\r\n"
    )
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=----boundary123"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    try:
        form_data = await request.multipart()
        
        upload_file = form_data.get_file("file")
        assert upload_file is not None
        
        # Filename should be sanitized (no path components)
        assert "/" not in upload_file.filename
        assert "\\" not in upload_file.filename
        assert ".." not in upload_file.filename
        
        # Cleanup
        await request.cleanup()
    
    except Exception as e:
        if "not available" in str(e):
            pytest.skip("python-multipart not available")
        raise


@pytest.mark.asyncio
async def test_form_caching():
    """Test that form data is cached."""
    body = b"name=John"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    form1 = await request.form()
    form2 = await request.form()
    
    # Should be same object (cached)
    assert form1 is form2
