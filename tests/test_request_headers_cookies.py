"""
Test header and cookie parsing for Request.
"""

import pytest
from aquilia.request import Request


@pytest.mark.asyncio
async def test_headers_basic():
    """Test basic header access."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"user-agent", b"TestClient/1.0"),
            (b"accept", b"*/*"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.header("content-type") == "application/json"
    assert request.header("user-agent") == "TestClient/1.0"
    assert request.header("accept") == "*/*"


@pytest.mark.asyncio
async def test_headers_case_insensitive():
    """Test case-insensitive header access."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"Content-Type", b"text/html"),
            (b"X-Custom-Header", b"value"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    # Different cases should all work
    assert request.header("content-type") == "text/html"
    assert request.header("Content-Type") == "text/html"
    assert request.header("CONTENT-TYPE") == "text/html"
    
    assert request.header("x-custom-header") == "value"
    assert request.header("X-CUSTOM-HEADER") == "value"


@pytest.mark.asyncio
async def test_headers_multiple_values():
    """Test headers with multiple values."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"accept", b"text/html"),
            (b"accept", b"application/json"),
            (b"accept", b"*/*"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    headers = request.headers()
    
    # Get first value
    assert headers.get("accept") == "text/html"
    
    # Get all values
    all_accepts = headers.get_all("accept")
    assert all_accepts == ["text/html", "application/json", "*/*"]


@pytest.mark.asyncio
async def test_headers_missing():
    """Test accessing missing headers."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.header("nonexistent") is None
    assert request.header("nonexistent", "default") == "default"
    assert not request.has_header("nonexistent")


@pytest.mark.asyncio
async def test_headers_has():
    """Test checking header existence."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.has_header("content-type")
    assert request.has_header("Content-Type")
    assert not request.has_header("authorization")


@pytest.mark.asyncio
async def test_cookies_basic():
    """Test basic cookie parsing."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"cookie", b"session=abc123; theme=dark"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    cookies = request.cookies()
    
    assert cookies["session"] == "abc123"
    assert cookies["theme"] == "dark"
    assert request.cookie("session") == "abc123"
    assert request.cookie("theme") == "dark"


@pytest.mark.asyncio
async def test_cookies_empty():
    """Test empty cookies."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    cookies = request.cookies()
    
    assert len(cookies) == 0
    assert request.cookie("session") is None
    assert request.cookie("session", "default") == "default"


@pytest.mark.asyncio
async def test_cookies_special_values():
    """Test cookies with special values."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"cookie", b'data="quoted value"; empty=; special=%20%3D%26'),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    cookies = request.cookies()
    
    assert cookies["data"] == "quoted value"
    assert cookies["empty"] == ""


@pytest.mark.asyncio
async def test_content_type_parsing():
    """Test Content-Type parsing."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.content_type() == "application/json; charset=utf-8"
    assert request.is_json()


@pytest.mark.asyncio
async def test_authorization_parsing():
    """Test Authorization header parsing."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer token123"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.auth_scheme() == "Bearer"
    assert request.auth_credentials() == "token123"


@pytest.mark.asyncio
async def test_content_length():
    """Test Content-Length parsing."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-length", b"42"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.content_length() == 42


@pytest.mark.asyncio
async def test_accepts():
    """Test Accept header checking."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"accept", b"text/html,application/json;q=0.9,*/*;q=0.8"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.accepts("text/html")
    assert request.accepts("application/json")
    assert request.accepts("anything")  # */*
    assert request.accepts("text/html", "application/xml")
