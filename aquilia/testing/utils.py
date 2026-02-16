"""
Aquilia Testing - Request/Response Utility Factories.

Provides helper functions for building ASGI scopes, Request objects,
receive callables, and Response objects for use in tests.
"""

from __future__ import annotations

import json as stdlib_json
from typing import Any, Dict, List, Optional, Sequence, Union

from aquilia.request import Request
from aquilia.response import Response


def make_test_scope(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[List[tuple]] = None,
    scheme: str = "http",
    client: Optional[tuple] = None,
    server: Optional[tuple] = None,
    root_path: str = "",
    http_version: str = "1.1",
    scope_type: str = "http",
) -> dict:
    """
    Build a minimal ASGI HTTP scope for testing.

    Args:
        method: HTTP method.
        path: Request path.
        query_string: Raw query string (without ``?``).
        headers: List of ``(name, value)`` tuples (strings or bytes).
        scheme: URL scheme (``http`` or ``https``).
        client: ``(host, port)`` tuple.
        server: ``(host, port)`` tuple.
        root_path: ASGI root path.
        http_version: HTTP protocol version.
        scope_type: ASGI scope type.

    Returns:
        ASGI scope dictionary.
    """
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for name, value in headers:
            raw_headers.append((
                name.encode("latin-1") if isinstance(name, str) else name,
                value.encode("latin-1") if isinstance(value, str) else value,
            ))

    return {
        "type": scope_type,
        "asgi": {"version": "3.0"},
        "http_version": http_version,
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": (
            query_string.encode("utf-8")
            if isinstance(query_string, str)
            else query_string
        ),
        "headers": raw_headers,
        "scheme": scheme,
        "server": server or ("127.0.0.1", 8000),
        "client": client or ("127.0.0.1", 12345),
        "root_path": root_path,
    }


def make_test_receive(
    body: bytes = b"",
    *,
    chunks: Optional[List[bytes]] = None,
):
    """
    Create an ASGI receive callable.

    Args:
        body: Complete request body bytes.
        chunks: Optional list of body chunks (overrides *body*).

    Returns:
        Async callable matching the ASGI ``receive`` protocol.
    """
    if chunks:
        messages: list[dict] = []
        for i, chunk in enumerate(chunks):
            messages.append({
                "type": "http.request",
                "body": chunk,
                "more_body": i < len(chunks) - 1,
            })
    else:
        messages = [{"type": "http.request", "body": body, "more_body": False}]

    idx = 0

    async def receive():
        nonlocal idx
        if idx < len(messages):
            msg = messages[idx]
            idx += 1
            return msg
        return {"type": "http.disconnect"}

    return receive


def make_test_request(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[List[tuple]] = None,
    body: bytes = b"",
    scheme: str = "http",
    client: Optional[tuple] = None,
    json: Any = None,
    form_data: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> Request:
    """
    Build a full :class:`~aquilia.request.Request` for testing.

    When *json* is provided the body is serialised and the appropriate
    ``Content-Type`` header is injected automatically.  Similarly for
    *form_data*.

    Args:
        method: HTTP method.
        path: Request path.
        query_string: Raw query string.
        headers: Header list.
        body: Raw body bytes.
        scheme: URL scheme.
        client: Client address.
        json: Optional JSON-serialisable payload.
        form_data: Optional ``application/x-www-form-urlencoded`` payload.
        **kwargs: Forwarded to :class:`Request`.

    Returns:
        Fully constructed :class:`Request`.
    """
    headers = list(headers) if headers else []

    if json is not None:
        body = stdlib_json.dumps(json).encode("utf-8")
        headers.append(("content-type", "application/json"))
        headers.append(("content-length", str(len(body))))

    elif form_data is not None:
        from urllib.parse import urlencode
        body = urlencode(form_data).encode("utf-8")
        headers.append(("content-type", "application/x-www-form-urlencoded"))
        headers.append(("content-length", str(len(body))))

    scope = make_test_scope(
        method=method,
        path=path,
        query_string=query_string,
        headers=headers,
        scheme=scheme,
        client=client,
    )
    receive = make_test_receive(body)
    return Request(scope, receive, **kwargs)


def make_test_response(
    content: Union[bytes, str, dict, list] = b"",
    status: int = 200,
    headers: Optional[Dict[str, str]] = None,
    media_type: Optional[str] = None,
) -> Response:
    """
    Build a :class:`~aquilia.response.Response` for assertion helpers.

    Args:
        content: Response body.
        status: HTTP status code.
        headers: Response headers.
        media_type: Content type.

    Returns:
        :class:`Response` instance.
    """
    return Response(
        content=content,
        status=status,
        headers=headers,
        media_type=media_type,
    )


def make_test_ws_scope(
    path: str = "/ws",
    headers: Optional[List[tuple]] = None,
    subprotocols: Optional[List[str]] = None,
    query_string: str = "",
    client: Optional[tuple] = None,
    server: Optional[tuple] = None,
) -> dict:
    """
    Build an ASGI WebSocket scope for testing.

    Args:
        path: WebSocket path.
        headers: Header list.
        subprotocols: Requested subprotocols.
        query_string: Raw query string.
        client: Client address tuple.
        server: Server address tuple.

    Returns:
        ASGI WebSocket scope dictionary.
    """
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for name, value in headers:
            raw_headers.append((
                name.encode("latin-1") if isinstance(name, str) else name,
                value.encode("latin-1") if isinstance(value, str) else value,
            ))

    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": (
            query_string.encode("utf-8")
            if isinstance(query_string, str)
            else query_string
        ),
        "headers": raw_headers,
        "scheme": "ws",
        "server": server or ("127.0.0.1", 8000),
        "client": client or ("127.0.0.1", 12345),
        "subprotocols": subprotocols or [],
    }


def make_upload_file(
    filename: str,
    content: Union[bytes, str],
    content_type: str = "application/octet-stream",
) -> tuple:
    """
    Create a file tuple suitable for :class:`TestClient` upload.

    Returns a ``(filename, content_bytes, content_type)`` tuple.

    Usage::

        files = {"avatar": make_upload_file("photo.jpg", b"\\xff\\xd8...", "image/jpeg")}
        resp = await client.post("/upload", files=files)
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return (filename, content, content_type)
