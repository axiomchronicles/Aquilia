"""
Aquilia Testing - HTTP & WebSocket Test Client.

Provides ``TestClient`` (like Django's ``Client`` / Starlette's ``TestClient``)
that issues in-process ASGI requests without a running socket.
"""

from __future__ import annotations

import asyncio
import json as stdlib_json
import io
import time as _time
from typing import (
    Any, AsyncIterator, Awaitable, Callable, Dict, List,
    Mapping, Optional, Sequence, Tuple, Union,
)

from aquilia.request import Request
from aquilia.response import Response
from aquilia.controller.base import RequestCtx

from .utils import make_test_scope, make_test_receive


class TestResponse:
    """
    Wrapper around captured ASGI response events.

    Provides a friendly API for assertions in tests.
    """

    __slots__ = (
        "status_code", "headers", "body", "_json_cache",
        "content_type", "charset", "elapsed", "request_method",
        "request_path",
    )

    def __init__(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: bytes,
        *,
        elapsed: float = 0.0,
        request_method: str = "",
        request_path: str = "",
    ):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self._json_cache: Any = None
        self.elapsed = elapsed
        self.request_method = request_method
        self.request_path = request_path

        ct = headers.get("content-type", "")
        self.content_type = ct.split(";")[0].strip()
        self.charset = "utf-8"
        if "charset=" in ct:
            self.charset = ct.split("charset=")[-1].strip()

    # -- Convenience accessors -------------------------------------------

    @property
    def text(self) -> str:
        """Body decoded as text."""
        return self.body.decode(self.charset)

    def json(self) -> Any:
        """Parse body as JSON."""
        if self._json_cache is None:
            self._json_cache = stdlib_json.loads(self.body)
        return self._json_cache

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    @property
    def content_length(self) -> Optional[int]:
        """Return Content-Length as int, or None."""
        cl = self.headers.get("content-length")
        return int(cl) if cl is not None else None

    @property
    def location(self) -> Optional[str]:
        """Return Location header (useful for redirects)."""
        return self.headers.get("location")

    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.headers.get(name.lower(), default)

    def has_header(self, name: str) -> bool:
        """Check if header exists."""
        return name.lower() in self.headers

    def __repr__(self) -> str:
        return (
            f"<TestResponse [{self.status_code}] "
            f"{self.content_type} {len(self.body)}B "
            f"{self.elapsed:.1f}ms>"
        )


class TestClient:
    """
    In-process ASGI test client for Aquilia.

    Does NOT open network sockets — instead it invokes the ASGI application
    directly, captures response events, and returns a :class:`TestResponse`.

    Usage::

        from aquilia.testing import TestClient, TestServer

        async with TestServer(manifests=[m]) as srv:
            client = TestClient(srv)
            resp = await client.get("/api/users")
            assert resp.status_code == 200

    The client supports cookies across requests (like a real browser),
    automatic redirect following, bearer token auth, and multipart uploads.
    """

    MAX_REDIRECTS = 20

    def __init__(
        self,
        server_or_app: Any,
        *,
        base_url: str = "http://testserver",
        default_headers: Optional[Dict[str, str]] = None,
        raise_server_exceptions: bool = True,
        follow_redirects: bool = False,
    ):
        """
        Args:
            server_or_app: A :class:`TestServer`, :class:`AquiliaServer`,
                or raw ASGI app callable.
            base_url: Base URL used in scope (not opened).
            default_headers: Headers injected into every request.
            raise_server_exceptions: Re-raise unhandled server errors.
            follow_redirects: Automatically follow 3xx redirects.
        """
        from .server import TestServer

        if isinstance(server_or_app, TestServer):
            self._app = server_or_app.app
            self._server = server_or_app
        elif hasattr(server_or_app, "app"):
            self._app = server_or_app.app
            self._server = server_or_app
        else:
            self._app = server_or_app
            self._server = None

        self._base_url = base_url
        self._default_headers = default_headers or {}
        self._cookies: Dict[str, str] = {}
        self._raise_server_exceptions = raise_server_exceptions
        self._follow_redirects = follow_redirects
        self._history: List[TestResponse] = []

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def set_bearer_token(self, token: str) -> None:
        """Set Authorization: Bearer <token> header for all requests."""
        self._default_headers["authorization"] = f"Bearer {token}"

    def clear_auth(self) -> None:
        """Remove Authorization header."""
        self._default_headers.pop("authorization", None)

    # ------------------------------------------------------------------
    # Response history
    # ------------------------------------------------------------------

    @property
    def history(self) -> List[TestResponse]:
        """Redirect chain history from the last request."""
        return list(self._history)

    # ------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------

    async def get(self, path: str, **kw) -> TestResponse:
        return await self._request("GET", path, **kw)

    async def post(
        self,
        path: str,
        json: Any = None,
        data: Optional[Dict[str, str]] = None,
        body: bytes = b"",
        files: Optional[Dict[str, Any]] = None,
        **kw,
    ) -> TestResponse:
        return await self._request("POST", path, json=json, data=data, body=body, files=files, **kw)

    async def put(self, path: str, json: Any = None, body: bytes = b"", files: Optional[Dict[str, Any]] = None, **kw) -> TestResponse:
        return await self._request("PUT", path, json=json, body=body, files=files, **kw)

    async def patch(self, path: str, json: Any = None, body: bytes = b"", files: Optional[Dict[str, Any]] = None, **kw) -> TestResponse:
        return await self._request("PATCH", path, json=json, body=body, files=files, **kw)

    async def delete(self, path: str, **kw) -> TestResponse:
        return await self._request("DELETE", path, **kw)

    async def head(self, path: str, **kw) -> TestResponse:
        return await self._request("HEAD", path, **kw)

    async def options(self, path: str, **kw) -> TestResponse:
        return await self._request("OPTIONS", path, **kw)

    # ------------------------------------------------------------------
    # Cookie management
    # ------------------------------------------------------------------

    def set_cookie(self, name: str, value: str) -> None:
        self._cookies[name] = value

    def delete_cookie(self, name: str) -> None:
        """Remove a specific cookie."""
        self._cookies.pop(name, None)

    def clear_cookies(self) -> None:
        self._cookies.clear()

    @property
    def cookies(self) -> Dict[str, str]:
        """Read-only view of the cookie jar."""
        return dict(self._cookies)

    # ------------------------------------------------------------------
    # Core request execution
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        query_string: str = "",
        json: Any = None,
        data: Optional[Dict[str, str]] = None,
        body: bytes = b"",
        files: Optional[Dict[str, Any]] = None,
        scheme: str = "http",
        client: Optional[tuple] = None,
        follow_redirects: Optional[bool] = None,
    ) -> TestResponse:
        """Issue an in-process ASGI request."""
        self._history.clear()
        should_follow = follow_redirects if follow_redirects is not None else self._follow_redirects

        resp = await self._single_request(
            method, path, headers=headers, query_string=query_string,
            json=json, data=data, body=body, files=files,
            scheme=scheme, client=client,
        )

        # Follow redirects
        redirect_count = 0
        while should_follow and resp.is_redirect and redirect_count < self.MAX_REDIRECTS:
            redirect_count += 1
            self._history.append(resp)
            location = resp.header("location") or ""
            if not location:
                break
            # Follow with GET (PRG pattern)
            resp = await self._single_request(
                "GET", location, scheme=scheme, client=client,
            )

        return resp

    async def _single_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        query_string: str = "",
        json: Any = None,
        data: Optional[Dict[str, str]] = None,
        body: bytes = b"",
        files: Optional[Dict[str, Any]] = None,
        scheme: str = "http",
        client: Optional[tuple] = None,
    ) -> TestResponse:
        """Issue a single ASGI request (no redirect following)."""
        # Build combined headers
        combined_headers: list[tuple[str, str]] = []
        for k, v in self._default_headers.items():
            combined_headers.append((k.lower(), v))
        if headers:
            for k, v in headers.items():
                combined_headers.append((k.lower(), v))

        # Inject cookies
        if self._cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
            combined_headers.append(("cookie", cookie_str))

        # Serialise JSON / form / multipart body
        if json is not None:
            body = stdlib_json.dumps(json).encode("utf-8")
            combined_headers.append(("content-type", "application/json"))
            combined_headers.append(("content-length", str(len(body))))
        elif files is not None:
            body, content_type = _build_multipart(data or {}, files)
            combined_headers.append(("content-type", content_type))
            combined_headers.append(("content-length", str(len(body))))
        elif data is not None:
            from urllib.parse import urlencode
            body = urlencode(data).encode("utf-8")
            combined_headers.append(("content-type", "application/x-www-form-urlencoded"))
            combined_headers.append(("content-length", str(len(body))))
        elif body:
            combined_headers.append(("content-length", str(len(body))))

        # Build ASGI scope
        scope = make_test_scope(
            method=method,
            path=path,
            query_string=query_string,
            headers=combined_headers,
            scheme=scheme,
            client=client,
        )

        # Receive callable
        receive = make_test_receive(body)

        # Capture response events
        response_started = False
        status_code = 200
        resp_headers: Dict[str, str] = {}
        body_parts: list[bytes] = []
        _exception: Optional[BaseException] = None

        async def send(event: dict):
            nonlocal response_started, status_code, resp_headers
            if event["type"] == "http.response.start":
                response_started = True
                status_code = event["status"]
                for hdr_name, hdr_val in event.get("headers", []):
                    name = (
                        hdr_name.decode("latin-1")
                        if isinstance(hdr_name, bytes)
                        else hdr_name
                    )
                    val = (
                        hdr_val.decode("latin-1")
                        if isinstance(hdr_val, bytes)
                        else hdr_val
                    )
                    name_lower = name.lower()
                    # Handle multi-value headers (Set-Cookie)
                    if name_lower == "set-cookie" and name_lower in resp_headers:
                        resp_headers[name_lower] += ", " + val
                    else:
                        resp_headers[name_lower] = val
            elif event["type"] == "http.response.body":
                body_parts.append(event.get("body", b""))

        # Execute ASGI app with timing
        start_time = _time.monotonic()
        try:
            await self._app(scope, receive, send)
        except Exception as exc:
            _exception = exc
            if self._raise_server_exceptions:
                raise
        elapsed_ms = (_time.monotonic() - start_time) * 1000

        # Parse Set-Cookie headers for cookie jar
        if "set-cookie" in resp_headers:
            self._parse_set_cookie(resp_headers["set-cookie"])

        return TestResponse(
            status_code=status_code,
            headers=resp_headers,
            body=b"".join(body_parts),
            elapsed=elapsed_ms,
            request_method=method,
            request_path=path,
        )

    def _parse_set_cookie(self, header: str):
        """Extract cookies from ``Set-Cookie`` header."""
        for part in header.split(","):
            part = part.strip()
            if "=" in part:
                kv = part.split(";")[0]
                name, _, value = kv.partition("=")
                self._cookies[name.strip()] = value.strip()


# -----------------------------------------------------------------------
# Multipart builder
# -----------------------------------------------------------------------

def _build_multipart(
    data: Dict[str, str],
    files: Dict[str, Any],
) -> Tuple[bytes, str]:
    """
    Build a multipart/form-data body from form fields and files.

    Files can be:
    - ``bytes``: raw content (auto-named)
    - ``(filename, content_bytes)``: named file
    - ``(filename, content_bytes, content_type)``: named file with type

    Returns:
        ``(body_bytes, content_type_header)``
    """
    import uuid
    boundary = f"----AquiliaTestBoundary{uuid.uuid4().hex[:16]}"
    parts: list[bytes] = []

    # Form fields
    for name, value in data.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )

    # File fields
    for field_name, file_info in files.items():
        if isinstance(file_info, bytes):
            filename = field_name
            content = file_info
            content_type = "application/octet-stream"
        elif isinstance(file_info, (tuple, list)):
            if len(file_info) == 2:
                filename, content = file_info
                content_type = "application/octet-stream"
            else:
                filename, content, content_type = file_info[:3]
        else:
            raise TypeError(
                f"File for {field_name!r}: expected bytes or tuple, got {type(file_info)}"
            )

        if isinstance(content, str):
            content = content.encode("utf-8")

        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
            + content
            + b"\r\n"
        )

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


class WebSocketTestClient:
    """
    In-process WebSocket test client.

    Simulates a WebSocket connection by feeding ASGI events directly
    into the application's ``websocket`` handler.

    Usage::

        ws = WebSocketTestClient(server)
        await ws.connect("/ws/chat")
        await ws.send_json({"type": "message", "text": "hello"})
        msg = await ws.receive_json()
        await ws.close()
    """

    def __init__(self, server_or_app: Any):
        from .server import TestServer

        if isinstance(server_or_app, TestServer):
            self._app = server_or_app.app
        elif hasattr(server_or_app, "app"):
            self._app = server_or_app.app
        else:
            self._app = server_or_app

        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._receive_queue: asyncio.Queue = asyncio.Queue()
        self._app_task: Optional[asyncio.Task] = None
        self._accepted = False
        self._closed = False

    async def connect(
        self,
        path: str = "/ws",
        headers: Optional[List[tuple]] = None,
        subprotocols: Optional[List[str]] = None,
    ) -> None:
        """Initiate WebSocket handshake."""
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "headers": [
                (n.encode() if isinstance(n, str) else n,
                 v.encode() if isinstance(v, str) else v)
                for n, v in (headers or [])
            ],
            "scheme": "ws",
            "server": ("127.0.0.1", 8000),
            "client": ("127.0.0.1", 12345),
            "subprotocols": subprotocols or [],
        }

        async def receive():
            return await self._send_queue.get()

        async def send(event: dict):
            if event["type"] == "websocket.accept":
                self._accepted = True
            elif event["type"] == "websocket.close":
                self._closed = True
            await self._receive_queue.put(event)

        # Send connect event
        await self._send_queue.put({"type": "websocket.connect"})

        # Launch app handler as a background task
        self._app_task = asyncio.create_task(self._app(scope, receive, send))

        # Wait for accept
        event = await asyncio.wait_for(self._receive_queue.get(), timeout=5.0)
        if event["type"] != "websocket.accept":
            raise ConnectionError(f"WebSocket not accepted: {event}")

    async def send_text(self, text: str) -> None:
        await self._send_queue.put({"type": "websocket.receive", "text": text})

    async def send_json(self, data: Any) -> None:
        await self.send_text(stdlib_json.dumps(data))

    async def send_bytes(self, data: bytes) -> None:
        await self._send_queue.put({"type": "websocket.receive", "bytes": data})

    async def receive(self, timeout: float = 5.0) -> dict:
        return await asyncio.wait_for(self._receive_queue.get(), timeout=timeout)

    async def receive_text(self, timeout: float = 5.0) -> str:
        event = await self.receive(timeout)
        return event.get("text", "")

    async def receive_json(self, timeout: float = 5.0) -> Any:
        text = await self.receive_text(timeout)
        return stdlib_json.loads(text)

    async def receive_bytes(self, timeout: float = 5.0) -> bytes:
        """Receive binary data from the WebSocket."""
        event = await self.receive(timeout)
        return event.get("bytes", b"")

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently connected."""
        return self._accepted and not self._closed

    async def close(self, code: int = 1000) -> None:
        await self._send_queue.put({
            "type": "websocket.disconnect",
            "code": code,
        })
        if self._app_task and not self._app_task.done():
            try:
                await asyncio.wait_for(self._app_task, timeout=2.0)
            except (asyncio.TimeoutError, Exception):
                self._app_task.cancel()
        self._closed = True

    # Async context manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        if not self._closed:
            await self.close()
