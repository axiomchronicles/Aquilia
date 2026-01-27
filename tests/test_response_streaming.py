"""
Test Response streaming - async iterables, sync iterables, coroutines.
"""

import asyncio
import pytest
from aquilia.response import Response, ServerSentEvent


@pytest.mark.asyncio
async def test_streaming_async_iterable():
    """Test async iterator yields several chunks -> messages with more_body True then False."""
    
    async def async_generator():
        yield b"chunk1"
        yield b"chunk2"
        yield b"chunk3"
    
    response = Response.stream(async_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Verify messages
    assert len(messages) == 5  # start + 3 chunks + final empty
    
    # Start message
    assert messages[0]["type"] == "http.response.start"
    assert messages[0]["status"] == 200
    
    # Chunk messages
    assert messages[1]["body"] == b"chunk1"
    assert messages[1]["more_body"] is True
    
    assert messages[2]["body"] == b"chunk2"
    assert messages[2]["more_body"] is True
    
    assert messages[3]["body"] == b"chunk3"
    assert messages[3]["more_body"] is True
    
    # Final empty chunk
    assert messages[4]["body"] == b""
    assert messages[4]["more_body"] is False


@pytest.mark.asyncio
async def test_streaming_sync_iterable_to_thread():
    """Test sync generator used -> ensure not blocking loop (use to_thread)."""
    
    def sync_generator():
        for i in range(3):
            yield f"line{i}\n".encode()
    
    response = Response.stream(sync_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Should have processed all chunks
    assert len(messages) == 5  # start + 3 chunks + final
    
    # Check chunks
    assert messages[1]["body"] == b"line0\n"
    assert messages[2]["body"] == b"line1\n"
    assert messages[3]["body"] == b"line2\n"


@pytest.mark.asyncio
async def test_coroutine_content():
    """Test coroutine returning content."""
    
    async def render_content():
        await asyncio.sleep(0.01)  # Simulate async work
        return "Rendered content"
    
    response = Response(render_content())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Should have 2 messages (start + body)
    assert len(messages) == 2
    
    body = messages[1]
    assert body["body"] == b"Rendered content"
    assert body["more_body"] is False


@pytest.mark.asyncio
async def test_sse_formatting():
    """Test SSE events are formatted correctly and flushed."""
    
    async def event_generator():
        yield ServerSentEvent(data="First message", id="1", event="greeting")
        yield ServerSentEvent(data="Second message", id="2")
        yield ServerSentEvent(data="Line1\nLine2\nLine3")  # Multi-line
    
    response = Response.sse(event_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Check content-type
    start = messages[0]
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["content-type"] == "text/event-stream; charset=utf-8"
    assert headers_dict["cache-control"] == "no-cache"
    
    # Check event formatting
    chunk1 = messages[1]["body"].decode()
    assert "id: 1" in chunk1
    assert "event: greeting" in chunk1
    assert "data: First message" in chunk1
    assert chunk1.endswith("\n\n")
    
    # Multi-line data
    chunk3 = messages[3]["body"].decode()
    assert "data: Line1" in chunk3
    assert "data: Line2" in chunk3
    assert "data: Line3" in chunk3


@pytest.mark.asyncio
async def test_streaming_empty_iterator():
    """Test empty iterator."""
    
    async def empty_generator():
        return
        yield  # Never reached
    
    response = Response.stream(empty_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Should have start + final empty
    assert len(messages) == 2
    assert messages[1]["body"] == b""
    assert messages[1]["more_body"] is False


@pytest.mark.asyncio
async def test_large_streaming():
    """Test streaming large chunks."""
    
    chunk_size = 1024 * 64  # 64KB chunks
    num_chunks = 10
    
    async def large_generator():
        for i in range(num_chunks):
            yield b"x" * chunk_size
    
    response = Response.stream(large_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Verify all chunks sent
    assert len(messages) == num_chunks + 2  # start + chunks + final
    
    for i in range(1, num_chunks + 1):
        assert len(messages[i]["body"]) == chunk_size
        assert messages[i]["more_body"] is True
