"""
Test Response file streaming, caching, and security.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from aquilia.response import (
    Response, 
    generate_etag, 
    generate_etag_from_file,
    check_not_modified,
    not_modified_response,
    InvalidHeaderError
)


@pytest.mark.asyncio
async def test_file_send_basic():
    """Test basic file streaming."""
    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello from file!\n" * 100)
        temp_path = f.name
    
    try:
        response = Response.file(temp_path, filename="test.txt")
        
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        await response.send_asgi(mock_send)
        
        # Check headers
        start = messages[0]
        headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
        
        assert "content-length" in headers_dict
        assert "accept-ranges" in headers_dict
        assert headers_dict["accept-ranges"] == "bytes"
        assert "content-disposition" in headers_dict
        assert "test.txt" in headers_dict["content-disposition"]
        
        # Check content streamed
        body_chunks = [m["body"] for m in messages[1:] if m["body"]]
        assert len(body_chunks) > 0
        
        full_body = b"".join(body_chunks)
        assert b"Hello from file!" in full_body
    
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_file_media_type_detection():
    """Test MIME type detection for files."""
    # Create temp files with different extensions
    extensions = [".txt", ".json", ".html", ".pdf"]
    
    for ext in extensions:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=ext) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            response = Response.file(temp_path)
            
            # Check media type detected
            content_type = response._headers.get("content-type", "")
            
            if ext == ".txt":
                assert "text/plain" in content_type
            elif ext == ".json":
                assert "application/json" in content_type
            elif ext == ".html":
                assert "text/html" in content_type
            elif ext == ".pdf":
                assert "application/pdf" in content_type
        
        finally:
            Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_etag_helpers():
    """Test ETag generation and setting."""
    content = b"Hello, World!"
    
    # Generate ETag
    etag = generate_etag(content)
    assert len(etag) > 0
    
    # Same content -> same ETag
    etag2 = generate_etag(content)
    assert etag == etag2
    
    # Different content -> different ETag
    etag3 = generate_etag(b"Different content")
    assert etag != etag3
    
    # Set ETag on response
    response = Response(content)
    response.set_etag(etag)
    
    assert '"' + etag + '"' in response._headers["etag"]
    
    # Weak ETag
    response2 = Response(content)
    response2.set_etag(etag, weak=True)
    
    assert response2._headers["etag"].startswith('W/"')


@pytest.mark.asyncio
async def test_etag_from_file():
    """Test ETag generation from file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("File content")
        temp_path = f.name
    
    try:
        etag = generate_etag_from_file(temp_path)
        assert len(etag) > 0
        
        # Same file -> same ETag
        etag2 = generate_etag_from_file(temp_path)
        assert etag == etag2
    
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_last_modified():
    """Test Last-Modified header."""
    response = Response(b"test")
    
    dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    response.set_last_modified(dt)
    
    assert "last-modified" in response._headers
    
    # Verify format is HTTP date
    lm = response._headers["last-modified"]
    assert "Wed" in lm or "Mon" in lm or "Tue" in lm or "Thu" in lm or "Fri" in lm or "Sat" in lm or "Sun" in lm


@pytest.mark.asyncio
async def test_cache_control():
    """Test Cache-Control directives."""
    response = Response(b"test")
    
    # Test various directives
    response.cache_control(max_age=3600, public=True, must_revalidate=True)
    
    cc = response._headers["cache-control"]
    assert "max-age=3600" in cc
    assert "public" in cc
    assert "must-revalidate" in cc
    
    # Test no-cache
    response2 = Response(b"test")
    response2.cache_control(no_cache=True, no_store=True)
    
    cc2 = response2._headers["cache-control"]
    assert "no-cache" in cc2
    assert "no-store" in cc2


@pytest.mark.asyncio
async def test_secure_headers():
    """Test security headers helper."""
    response = Response(b"test")
    
    response.secure_headers(
        hsts=True,
        csp="default-src 'self'",
        frame_options="SAMEORIGIN"
    )
    
    assert "strict-transport-security" in response._headers
    assert "content-security-policy" in response._headers
    assert response._headers["content-security-policy"] == "default-src 'self'"
    assert response._headers["x-frame-options"] == "SAMEORIGIN"
    assert response._headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_header_injection_blocked():
    """Test header with newline raises InvalidHeader."""
    response = Response(b"test")
    
    # Newline in header value should raise
    with pytest.raises(InvalidHeaderError):
        response.set_header("x-test", "value\r\nInjected: bad")
    
    # Newline in header name should raise
    with pytest.raises(InvalidHeaderError):
        response.set_header("x-test\r\n", "value")
    
    # Control characters should raise
    with pytest.raises(InvalidHeaderError):
        response.set_header("x-test", "value\x00bad")


@pytest.mark.asyncio
async def test_check_not_modified():
    """Test 304 Not Modified logic."""
    
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers
    
    # Test ETag match
    etag = "abc123"
    request = MockRequest({"if-none-match": '"abc123"'})
    
    assert check_not_modified(request, etag=etag) is True
    
    # Test ETag mismatch
    request2 = MockRequest({"if-none-match": '"different"'})
    assert check_not_modified(request2, etag=etag) is False
    
    # Test If-Modified-Since
    last_mod = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    request3 = MockRequest({"if-modified-since": "Wed, 01 Jan 2025 00:00:00 GMT"})
    
    assert check_not_modified(request3, last_modified=last_mod) is True


@pytest.mark.asyncio
async def test_not_modified_response():
    """Test 304 response creation."""
    etag = "abc123"
    response = not_modified_response(etag=etag)
    
    assert response.status == 304
    assert response._headers["etag"] == '"abc123"'
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    assert messages[0]["status"] == 304
    assert messages[1]["body"] == b""
