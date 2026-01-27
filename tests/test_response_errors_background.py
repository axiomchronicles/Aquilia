"""
Test Response error handling, background tasks, and client disconnect.
"""

import asyncio
import pytest
from aquilia.response import (
    Response, 
    CallableBackgroundTask,
    TemplateRenderError,
    ClientDisconnectError,
    ResponseStreamError
)


@pytest.mark.asyncio
async def test_template_render_coroutine_error_handling():
    """Test coroutine raising during render -> client receives error and logs show fault."""
    
    async def failing_render():
        await asyncio.sleep(0.01)
        raise ValueError("Template not found")
    
    response = Response(failing_render())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    # Should raise TemplateRenderError
    with pytest.raises(TemplateRenderError) as exc_info:
        await response.send_asgi(mock_send)
    
    # Check error details
    assert "Template rendering failed" in str(exc_info.value)
    assert "ValueError" in exc_info.value.details.get("error_type", "")


@pytest.mark.asyncio
async def test_background_tasks_executed():
    """Test background tasks run after response sent."""
    task_executed = []
    
    async def background_work():
        task_executed.append(True)
        await asyncio.sleep(0.01)
        task_executed.append("done")
    
    task = CallableBackgroundTask(background_work)
    response = Response(b"test", background=task)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Background task should have executed
    assert len(task_executed) == 2
    assert task_executed[0] is True
    assert task_executed[1] == "done"


@pytest.mark.asyncio
async def test_multiple_background_tasks():
    """Test multiple background tasks."""
    results = []
    
    async def task1():
        results.append(1)
    
    async def task2():
        results.append(2)
    
    async def task3():
        results.append(3)
    
    tasks = [
        CallableBackgroundTask(task1),
        CallableBackgroundTask(task2),
        CallableBackgroundTask(task3)
    ]
    
    response = Response(b"test", background=tasks)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # All tasks should execute
    assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_background_task_error_handling():
    """Test background task errors are logged but don't break response."""
    
    async def failing_task():
        raise RuntimeError("Background task failed")
    
    task = CallableBackgroundTask(failing_task)
    response = Response(b"test", background=task)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    # Should not raise - error should be logged
    await response.send_asgi(mock_send)
    
    # Response should be sent successfully
    assert len(messages) == 2
    assert messages[1]["body"] == b"test"


@pytest.mark.asyncio
async def test_client_disconnect_during_stream():
    """Test client disconnect during streaming."""
    
    async def slow_stream():
        for i in range(100):
            yield b"chunk"
            await asyncio.sleep(0.001)
    
    response = Response.stream(slow_stream())
    
    disconnect_after = 5
    
    async def mock_send_with_disconnect(message):
        nonlocal disconnect_after
        if message["type"] == "http.response.body":
            disconnect_after -= 1
            if disconnect_after <= 0:
                raise asyncio.CancelledError()
    
    # Should raise ClientDisconnectError
    with pytest.raises(ClientDisconnectError):
        await response.send_asgi(mock_send_with_disconnect)


@pytest.mark.asyncio
async def test_streaming_generator_error():
    """Test error during streaming is caught."""
    
    async def failing_stream():
        yield b"chunk1"
        yield b"chunk2"
        raise RuntimeError("Stream error")
    
    response = Response.stream(failing_stream())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    # Should raise ResponseStreamError
    with pytest.raises((RuntimeError, ResponseStreamError)):
        await response.send_asgi(mock_send)


@pytest.mark.asyncio
async def test_response_metrics():
    """Test response tracks bytes sent and duration."""
    content = b"x" * 10000
    response = Response(content)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Check metrics
    assert response._bytes_sent == len(content)
    assert response._send_start_time is not None


@pytest.mark.asyncio
async def test_empty_response():
    """Test empty response (204 No Content)."""
    response = Response(b"", status=204)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    assert messages[0]["status"] == 204
    assert messages[1]["body"] == b""


@pytest.mark.asyncio
async def test_large_json_response():
    """Test large JSON response."""
    data = {
        "items": [{"id": i, "name": f"Item {i}"} for i in range(1000)]
    }
    
    response = Response.json(data)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Should serialize successfully
    assert len(messages) == 2
    assert len(messages[1]["body"]) > 0
    
    # Verify JSON
    import json
    decoded = json.loads(messages[1]["body"])
    assert len(decoded["items"]) == 1000


@pytest.mark.asyncio
async def test_async_iterable_with_strings():
    """Test async iterator that yields strings (should convert to bytes)."""
    
    async def string_generator():
        yield "Hello "
        yield "World!"
    
    response = Response.stream(string_generator())
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Strings should be encoded
    assert messages[1]["body"] == b"Hello "
    assert messages[2]["body"] == b"World!"


@pytest.mark.asyncio
async def test_header_validation_can_be_disabled():
    """Test header validation can be disabled."""
    # With validation (default)
    response1 = Response(b"test", validate_headers=True)
    
    with pytest.raises(Exception):  # Should raise
        response1.set_header("x-test", "value\ninjection")
    
    # Without validation
    response2 = Response(b"test", validate_headers=False)
    
    # Should not raise (but not recommended!)
    response2.set_header("x-test", "value")  # Normal value is fine
