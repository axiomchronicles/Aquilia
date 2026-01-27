"""
Test basic Response functionality - bytes, text, JSON, headers.
"""

import pytest
from aquilia.response import Response, Ok, Created, BadRequest


@pytest.mark.asyncio
async def test_send_basic_bytes_and_headers():
    """Test sending bytes body with proper ASGI messages."""
    response = Response(b"Hello, World!", status=200)
    response.set_header("x-test-header", "test-value")
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Verify messages
    assert len(messages) == 2
    
    # Check start message
    start = messages[0]
    assert start["type"] == "http.response.start"
    assert start["status"] == 200
    
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["x-test-header"] == "test-value"
    assert "content-type" in headers_dict
    
    # Check body message
    body = messages[1]
    assert body["type"] == "http.response.body"
    assert body["body"] == b"Hello, World!"
    assert body["more_body"] is False


@pytest.mark.asyncio
async def test_send_text_and_default_content_type():
    """Test string content -> text/plain header."""
    response = Response("Hello, World!", status=200)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Check headers
    start = messages[0]
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["content-type"] == "text/plain; charset=utf-8"
    
    # Check body is encoded
    body = messages[1]
    assert body["body"] == b"Hello, World!"


@pytest.mark.asyncio
async def test_json_helper_and_custom_encoder():
    """Test JSON response factory."""
    data = {"name": "Alice", "age": 30, "active": True}
    response = Response.json(data, status=200)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    # Check content-type
    start = messages[0]
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["content-type"] == "application/json; charset=utf-8"
    
    # Check body is JSON
    body = messages[1]
    import json
    decoded = json.loads(body["body"])
    assert decoded == data


@pytest.mark.asyncio
async def test_html_response():
    """Test HTML response factory."""
    html_content = "<html><body>Hello</body></html>"
    response = Response.html(html_content)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    start = messages[0]
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["content-type"] == "text/html; charset=utf-8"


@pytest.mark.asyncio
async def test_redirect():
    """Test redirect response."""
    response = Response.redirect("https://example.com", status=302)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    start = messages[0]
    assert start["status"] == 302
    headers_dict = {k.decode(): v.decode() for k, v in start["headers"]}
    assert headers_dict["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_convenience_factories():
    """Test convenience response factories."""
    # Ok
    ok_resp = Ok({"result": "success"})
    assert ok_resp.status == 200
    
    # Created
    created_resp = Created({"id": 123}, location="/api/items/123")
    assert created_resp.status == 201
    assert created_resp._headers.get("location") == "/api/items/123"
    
    # BadRequest
    bad_resp = BadRequest("Invalid input")
    assert bad_resp.status == 400


@pytest.mark.asyncio
async def test_header_helpers():
    """Test header manipulation methods."""
    response = Response(b"test")
    
    # set_header
    response.set_header("x-custom", "value1")
    assert response._headers["x-custom"] == "value1"
    
    # add_header (multiple values)
    response.add_header("x-multi", "first")
    response.add_header("x-multi", "second")
    assert response._headers["x-multi"] == ["first", "second"]
    
    # unset_header
    response.unset_header("x-custom")
    assert "x-custom" not in response._headers


@pytest.mark.asyncio
async def test_status_codes():
    """Test various HTTP status codes."""
    response = Response(b"", status=404)
    
    messages = []
    
    async def mock_send(message):
        messages.append(message)
    
    await response.send_asgi(mock_send)
    
    assert messages[0]["status"] == 404
