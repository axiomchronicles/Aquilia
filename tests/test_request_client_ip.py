"""
Test client IP detection and proxy trust for Request.
"""

import pytest
from aquilia.request import Request


@pytest.mark.asyncio
async def test_client_ip_direct():
    """Test direct client IP (no proxy)."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": ("192.168.1.100", 12345),
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive, trust_proxy=False)
    
    assert request.client_ip() == "192.168.1.100"


@pytest.mark.asyncio
async def test_client_ip_no_client():
    """Test client IP when client is None."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": None,
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive, trust_proxy=False)
    
    assert request.client_ip() == "0.0.0.0"


@pytest.mark.asyncio
async def test_client_ip_x_forwarded_for():
    """Test X-Forwarded-For header with trust_proxy."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.1, 198.51.100.1, 192.168.1.1"),
        ],
        "client": ("192.168.1.1", 12345),
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive, trust_proxy=True)
    
    # Should return first IP (original client)
    assert request.client_ip() == "203.0.113.1"


@pytest.mark.asyncio
async def test_client_ip_forwarded_header():
    """Test Forwarded header (RFC 7239) with trust_proxy."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"forwarded", b'for=198.51.100.17;proto=https'),
        ],
        "client": ("192.168.1.1", 12345),
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive, trust_proxy=True)
    
    assert request.client_ip() == "198.51.100.17"


@pytest.mark.asyncio
async def test_client_ip_trust_proxy_false():
    """Test that X-Forwarded-For is ignored when trust_proxy=False."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.1"),
        ],
        "client": ("192.168.1.1", 12345),
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive, trust_proxy=False)
    
    # Should return direct client IP, ignore header
    assert request.client_ip() == "192.168.1.1"


@pytest.mark.asyncio
async def test_client_property():
    """Test client property."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": ("10.0.0.5", 8080),
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.client == ("10.0.0.5", 8080)


@pytest.mark.asyncio
async def test_url_building():
    """Test URL building."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/users",
        "query_string": b"page=2&limit=10",
        "scheme": "https",
        "headers": [
            (b"host", b"example.com"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    url = request.url()
    
    assert url.scheme == "https"
    assert url.host == "example.com"
    assert url.path == "/api/users"
    assert "page=2" in url.query
    assert str(url) == "https://example.com/api/users?page=2&limit=10"


@pytest.mark.asyncio
async def test_base_url():
    """Test base URL."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/users",
        "query_string": b"page=2",
        "scheme": "https",
        "root_path": "/app",
        "headers": [
            (b"host", b"example.com"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    base_url = request.base_url()
    
    assert str(base_url) == "https://example.com/app"
    assert base_url.query == ""


@pytest.mark.asyncio
async def test_http_version():
    """Test HTTP version property."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "http_version": "2",
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.http_version == "2"


@pytest.mark.asyncio
async def test_method_and_path():
    """Test method and path properties."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/submit",
        "raw_path": b"/api/submit",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    assert request.method == "POST"
    assert request.path == "/api/submit"
    assert request.raw_path == b"/api/submit"
