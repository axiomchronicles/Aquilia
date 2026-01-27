"""
Test JSON parsing for Request.
"""

import pytest
from aquilia.request import Request, InvalidJSON, PayloadTooLarge, BadRequest


@pytest.mark.asyncio
async def test_json_simple():
    """Test simple JSON parsing."""
    body = b'{"name": "John", "age": 30}'
    
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
    data = await request.json()
    
    assert data["name"] == "John"
    assert data["age"] == 30


@pytest.mark.asyncio
async def test_json_array():
    """Test JSON array parsing."""
    body = b'[1, 2, 3, 4, 5]'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    data = await request.json()
    
    assert data == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_json_nested():
    """Test nested JSON parsing."""
    body = b'''
    {
        "user": {
            "name": "Alice",
            "address": {
                "city": "London",
                "country": "UK"
            }
        },
        "tags": ["python", "web"]
    }
    '''
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    data = await request.json()
    
    assert data["user"]["name"] == "Alice"
    assert data["user"]["address"]["city"] == "London"
    assert "python" in data["tags"]


@pytest.mark.asyncio
async def test_json_invalid():
    """Test invalid JSON."""
    body = b'{"name": "John", invalid}'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    with pytest.raises(InvalidJSON):
        await request.json()


@pytest.mark.asyncio
async def test_json_size_limit():
    """Test JSON size limit enforcement."""
    # Create large JSON
    large_data = {"key": "x" * 20_000_000}  # ~20 MB
    body = str(large_data).encode()
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive, json_max_size=1024)  # 1 KB limit
    
    with pytest.raises(PayloadTooLarge):
        await request.json()


@pytest.mark.asyncio
async def test_json_depth_limit():
    """Test JSON depth limit enforcement."""
    # Create deeply nested JSON
    deep_json = '{"a":' * 100 + '{}' + '}' * 100
    body = deep_json.encode()
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive, json_max_depth=10)
    
    with pytest.raises(InvalidJSON) as exc_info:
        await request.json()
    
    assert "depth" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_json_caching():
    """Test JSON caching (idempotence)."""
    body = b'{"cached": true}'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    # Parse twice
    data1 = await request.json()
    data2 = await request.json()
    
    # Should be same object (cached)
    assert data1 is data2
    assert data1["cached"] is True


@pytest.mark.asyncio
async def test_json_with_pydantic_model():
    """Test JSON parsing with Pydantic model."""
    try:
        from pydantic import BaseModel
    except ImportError:
        pytest.skip("Pydantic not available")
    
    class User(BaseModel):
        name: str
        age: int
    
    body = b'{"name": "Bob", "age": 25}'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    user = await request.json(model=User)
    
    assert isinstance(user, User)
    assert user.name == "Bob"
    assert user.age == 25


@pytest.mark.asyncio
async def test_json_validation_error():
    """Test JSON model validation error."""
    try:
        from pydantic import BaseModel
    except ImportError:
        pytest.skip("Pydantic not available")
    
    class User(BaseModel):
        name: str
        age: int
    
    body = b'{"name": "Bob"}'  # Missing required 'age'
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    
    with pytest.raises(BadRequest) as exc_info:
        await request.json(model=User)
    
    assert "validation" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_json_unicode():
    """Test JSON with Unicode."""
    body = '{"message": "Hello 世界 🌍", "emoji": "😀"}'.encode("utf-8")
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    request = Request(scope, receive)
    data = await request.json()
    
    assert data["message"] == "Hello 世界 🌍"
    assert data["emoji"] == "😀"
