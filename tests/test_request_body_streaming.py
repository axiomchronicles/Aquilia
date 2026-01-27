"""
Test body reading and streaming for Request.
"""

import pytest
from aquilia.request import Request, PayloadTooLarge, ClientDisconnect


@pytest.mark.asyncio
async def test_body_simple():
    """Test simple body reading."""
    body_data = b"Hello, World!"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    body = await request.body()
    
    assert body == body_data


@pytest.mark.asyncio
async def test_body_chunked():
    """Test chunked body reading."""
    chunks = [b"Hello, ", b"World", b"!"]
    chunk_iter = iter(chunks)
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        try:
            chunk = next(chunk_iter)
            has_more = True
        except StopIteration:
            chunk = b""
            has_more = False
        
        return {"type": "http.request", "body": chunk, "more_body": has_more}
    
    request = Request(scope, receive)
    body = await request.body()
    
    assert body == b"Hello, World!"


@pytest.mark.asyncio
async def test_body_caching():
    """Test body caching (idempotence)."""
    body_data = b"cached body"
    call_count = 0
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        nonlocal call_count
        call_count += 1
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    
    body1 = await request.body()
    body2 = await request.body()
    body3 = await request.body()
    
    # Should be same object
    assert body1 is body2 is body3
    assert body1 == body_data
    
    # receive() should only be called once
    assert call_count == 1


@pytest.mark.asyncio
async def test_body_size_limit():
    """Test body size limit enforcement."""
    large_body = b"x" * 20_000_000  # 20 MB
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": large_body, "more_body": False}
    
    request = Request(scope, receive, max_body_size=1024)  # 1 KB limit
    
    with pytest.raises(PayloadTooLarge) as exc_info:
        await request.body()
    
    assert exc_info.value.metadata["max_allowed"] == 1024


@pytest.mark.asyncio
async def test_text_simple():
    """Test text reading."""
    body_data = b"Hello, World!"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    text = await request.text()
    
    assert text == "Hello, World!"


@pytest.mark.asyncio
async def test_text_encoding():
    """Test text with custom encoding."""
    body_data = "Привет мир".encode("utf-8")
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"content-type", b"text/plain; charset=utf-8"),
        ],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    text = await request.text()
    
    assert text == "Привет мир"


@pytest.mark.asyncio
async def test_iter_bytes_simple():
    """Test streaming body bytes."""
    chunks = [b"chunk1", b"chunk2", b"chunk3"]
    chunk_iter = iter(chunks)
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        try:
            chunk = next(chunk_iter)
            has_more = True
        except StopIteration:
            chunk = b""
            has_more = False
        
        return {"type": "http.request", "body": chunk, "more_body": has_more}
    
    request = Request(scope, receive)
    
    collected = []
    async for chunk in request.iter_bytes():
        collected.append(chunk)
    
    assert collected == chunks


@pytest.mark.asyncio
async def test_iter_bytes_after_body():
    """Test iter_bytes after body() was called."""
    body_data = b"cached body"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive, chunk_size=4)
    
    # Read full body first
    body = await request.body()
    assert body == body_data
    
    # Now iter_bytes should yield from cache
    collected = []
    async for chunk in request.iter_bytes():
        collected.append(chunk)
    
    # Should yield in configured chunk size
    assert b"".join(collected) == body_data


@pytest.mark.asyncio
async def test_iter_text():
    """Test streaming body as text."""
    chunks = [b"Hello ", b"World", b"!"]
    chunk_iter = iter(chunks)
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        try:
            chunk = next(chunk_iter)
            has_more = True
        except StopIteration:
            chunk = b""
            has_more = False
        
        return {"type": "http.request", "body": chunk, "more_body": has_more}
    
    request = Request(scope, receive)
    
    collected = []
    async for text_chunk in request.iter_text():
        collected.append(text_chunk)
    
    assert "".join(collected) == "Hello World!"


@pytest.mark.asyncio
async def test_readexactly():
    """Test reading exact number of bytes."""
    body_data = b"0123456789"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    
    data = await request.readexactly(5)
    assert data == b"01234"


@pytest.mark.asyncio
async def test_readexactly_insufficient():
    """Test readexactly with insufficient data."""
    body_data = b"short"
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": body_data, "more_body": False}
    
    request = Request(scope, receive)
    
    with pytest.raises(EOFError):
        await request.readexactly(100)


@pytest.mark.asyncio
async def test_client_disconnect():
    """Test handling client disconnect."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.disconnect"}
    
    request = Request(scope, receive)
    
    with pytest.raises(ClientDisconnect):
        await request.body()
    
    assert request.is_disconnected()


@pytest.mark.asyncio
async def test_client_disconnect_during_streaming():
    """Test client disconnect during streaming."""
    call_count = 0
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    
    async def receive():
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            return {"type": "http.request", "body": b"chunk1", "more_body": True}
        else:
            return {"type": "http.disconnect"}
    
    request = Request(scope, receive)
    
    with pytest.raises(ClientDisconnect):
        chunks = []
        async for chunk in request.iter_bytes():
            chunks.append(chunk)
