"""
Test query parameter parsing for Request.
"""

import pytest
from aquilia.request import Request
from aquilia._datastructures import MultiDict


@pytest.mark.asyncio
async def test_query_params_empty():
    """Test empty query string."""
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
    params = request.query_params()
    
    assert len(params) == 0
    assert request.query_param("foo") is None


@pytest.mark.asyncio
async def test_query_params_single():
    """Test single query parameter."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"foo=bar",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("foo") == "bar"
    assert request.query_param("foo") == "bar"


@pytest.mark.asyncio
async def test_query_params_multiple():
    """Test multiple query parameters."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"foo=bar&baz=qux&hello=world",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("foo") == "bar"
    assert params.get("baz") == "qux"
    assert params.get("hello") == "world"


@pytest.mark.asyncio
async def test_query_params_repeated():
    """Test repeated query parameters."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"tag=python&tag=asyncio&tag=web",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    # First value
    assert params.get("tag") == "python"
    
    # All values
    all_tags = params.get_all("tag")
    assert all_tags == ["python", "asyncio", "web"]


@pytest.mark.asyncio
async def test_query_params_url_encoded():
    """Test URL-encoded query parameters."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"name=John+Doe&message=Hello%20World%21&emoji=%F0%9F%98%80",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("name") == "John Doe"
    assert params.get("message") == "Hello World!"
    assert params.get("emoji") == "😀"


@pytest.mark.asyncio
async def test_query_params_unicode():
    """Test Unicode query parameters."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": "город=Москва&言語=日本語".encode("utf-8"),
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("город") == "Москва"
    assert params.get("言語") == "日本語"


@pytest.mark.asyncio
async def test_query_params_empty_value():
    """Test query parameters with empty values."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"foo=&bar=baz&qux=",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("foo") == ""
    assert params.get("bar") == "baz"
    assert params.get("qux") == ""


@pytest.mark.asyncio
async def test_query_params_special_characters():
    """Test query parameters with special characters."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"key=%26%3D%3F%23&value=a%2Bb%2Fc",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    params = request.query_params()
    
    assert params.get("key") == "&=?#"
    assert params.get("value") == "a+b/c"


@pytest.mark.asyncio
async def test_query_params_caching():
    """Test that query params are cached."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"foo=bar",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    
    # Call multiple times
    params1 = request.query_params()
    params2 = request.query_params()
    
    # Should be same object (cached)
    assert params1 is params2
