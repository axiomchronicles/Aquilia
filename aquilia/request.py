"""
Request - Production-grade ASGI request wrapper.

Provides:
- Typed, async request object wrapping ASGI scope/receive/send
- Streaming body support with idempotent caching
- Robust parsing: URL, query, headers, cookies, JSON, forms
- Multipart/form-data streaming with file upload support
- Security limits: max body size, max fields, max file size
- Content negotiation helpers
- Proxy/trust options for client IP detection
- Integration with DI, FaultEngine, and upload stores
"""

from __future__ import annotations

import asyncio
import json as stdlib_json
import tempfile
import uuid
import ipaddress
from http.cookies import SimpleCookie
from pathlib import Path
from typing import (
    Any, AsyncIterator, Awaitable, Callable, Dict, List, 
    Mapping, Optional, Type, TypeVar, Union
)
from urllib.parse import parse_qsl, unquote

from ._datastructures import (
    Headers, MultiDict, ParsedContentType, Range, URL,
    parse_authorization_header, parse_date_header
)
from ._uploads import (
    FormData, UploadFile, UploadStore, LocalUploadStore,
    create_upload_file_from_bytes, create_upload_file_from_path
)
from .faults import Fault, FaultDomain, Severity

# Import python-multipart
try:
    from python_multipart import MultipartParser
    from python_multipart.multipart import parse_options_header
    MULTIPART_AVAILABLE = True
except ImportError:
    MULTIPART_AVAILABLE = False

# Type vars
T = TypeVar("T")
PathLike = Union[str, Path]


# ============================================================================
# Request Faults (Aquilia Fault System Integration)
# ============================================================================

class RequestFault(Fault):
    """Base class for request-related faults."""
    domain = FaultDomain.IO
    severity = Severity.ERROR
    public = True


class BadRequest(RequestFault):
    """Malformed request (400)."""
    code = "BAD_REQUEST"
    message = "Bad request"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


class PayloadTooLarge(RequestFault):
    """Request payload exceeds limits (413)."""
    code = "PAYLOAD_TOO_LARGE"
    message = "Payload too large"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


class UnsupportedMediaType(RequestFault):
    """Unsupported Content-Type (415)."""
    code = "UNSUPPORTED_MEDIA_TYPE"
    message = "Unsupported media type"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


class ClientDisconnect(RequestFault):
    """Client disconnected during request (499)."""
    code = "CLIENT_DISCONNECT"
    message = "Client disconnected"
    severity = Severity.WARN
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            severity=self.severity,
            metadata=metadata
        )


class InvalidJSON(RequestFault):
    """Invalid JSON payload (400)."""
    code = "INVALID_JSON"
    message = "Invalid JSON"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


class InvalidHeader(RequestFault):
    """Invalid header format (400)."""
    code = "INVALID_HEADER"
    message = "Invalid header"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


class MultipartParseError(RequestFault):
    """Multipart parsing failed (400)."""
    code = "MULTIPART_PARSE_ERROR"
    message = "Multipart parsing failed"
    
    def __init__(self, message: str = None, **metadata):
        super().__init__(
            code=self.code,
            message=message or self.message,
            metadata=metadata
        )


# ============================================================================
# Request Class
# ============================================================================

class Request:
    """
    Production-grade request object for Aquilia.
    
    Features:
    - Streaming-first body access
    - Typed query/header/cookie parsing
    - JSON parsing with validation hooks
    - Form and multipart/form-data parsing
    - File upload support with streaming
    - Security limits and sanitization
    - Client IP detection with proxy trust
    - Content negotiation helpers
    """
    
    def __init__(
        self,
        scope: Mapping[str, Any],
        receive: Callable[..., Awaitable[dict]],
        send: Optional[Callable] = None,
        *,
        max_body_size: int = 10_485_760,  # 10 MiB
        max_field_count: int = 1000,
        max_file_size: int = 2_147_483_648,  # 2 GiB
        upload_tempdir: Optional[PathLike] = None,
        trust_proxy: Union[bool, List[str]] = False,
        chunk_size: int = 64 * 1024,
        json_max_size: int = 10_485_760,  # 10 MiB
        json_max_depth: int = 64,
        form_memory_threshold: int = 1024 * 1024,  # 1 MiB
    ):
        """
        Initialize Request.
        
        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable (optional)
            max_body_size: Maximum request body size in bytes
            max_field_count: Maximum number of form fields/parts
            max_file_size: Maximum file upload size in bytes
            upload_tempdir: Directory for temporary upload files
            trust_proxy: Trust proxy headers (True/False or list of IPs)
            chunk_size: Default chunk size for streaming
            json_max_size: Maximum JSON payload size
            json_max_depth: Maximum JSON nesting depth
            form_memory_threshold: Threshold for spilling uploads to disk
        """
        self.scope = scope
        self._receive = receive
        self._send = send
        
        # Configuration
        self.max_body_size = max_body_size
        self.max_field_count = max_field_count
        self.max_file_size = max_file_size
        self.upload_tempdir = Path(upload_tempdir) if upload_tempdir else None
        self.trust_proxy = trust_proxy
        self.chunk_size = chunk_size
        self.json_max_size = json_max_size
        self.json_max_depth = json_max_depth
        self.form_memory_threshold = form_memory_threshold
        
        # State
        self.state: Dict[str, Any] = {}
        
        # Cached values
        self._body: Optional[bytes] = None
        self._body_consumed = False
        self._json: Optional[Any] = None
        self._form_data: Optional[FormData] = None
        self._query_params: Optional[MultiDict] = None
        self._headers: Optional[Headers] = None
        self._cookies: Optional[Dict[str, str]] = None
        self._url: Optional[URL] = None
        self._disconnected = False
        
        # Cleanup tracking
        self._temp_files: List[Path] = []
    
    async def __call__(self) -> "Request":
        """
        Async initializer (called by runtime).
        
        Returns self after any async setup.
        """
        return self
    
    # ========================================================================
    # Basic Properties
    # ========================================================================
    
    @property
    def method(self) -> str:
        """HTTP method (GET, POST, etc.)."""
        return self.scope.get("method", "GET")
    
    @property
    def http_version(self) -> str:
        """HTTP version (e.g., '1.1', '2')."""
        return self.scope.get("http_version", "1.1")
    
    @property
    def path(self) -> str:
        """Request path (decoded)."""
        return self.scope.get("path", "/")
    
    @property
    def raw_path(self) -> bytes:
        """Raw request path (as bytes from ASGI)."""
        return self.scope.get("raw_path", b"/")
    
    @property
    def query_string(self) -> str:
        """Raw query string."""
        return self.scope.get("query_string", b"").decode("utf-8")
    
    @property
    def client(self) -> Optional[tuple]:
        """Client address (host, port)."""
        return self.scope.get("client")
    
    # ========================================================================
    # Query Parameters
    # ========================================================================
    
    @property
    def query_params(self) -> MultiDict:
        """Get parsed query parameters as MultiDict."""
        if self._query_params is None:
            query_string = self.query_string
            if query_string:
                # parse_qsl preserves order and handles repeated params
                items = parse_qsl(query_string, keep_blank_values=True)
                self._query_params = MultiDict(items)
            else:
                self._query_params = MultiDict()
        return self._query_params
    
    def query_param(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get single query parameter."""
        return self.query_params.get(name, default)
    
    # ========================================================================
    # Headers
    # ========================================================================
    
    @property
    def headers(self) -> Headers:
        """Get parsed headers."""
        if self._headers is None:
            raw_headers = self.scope.get("headers", [])
            self._headers = Headers(raw=raw_headers)
        return self._headers
    
    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get single header (case-insensitive)."""
        return self.headers.get(name, default)
    
    def has_header(self, name: str) -> bool:
        """Check if header exists."""
        return self.headers.has(name)
    
    # ========================================================================
    # Cookies
    # ========================================================================
    
    @property
    def cookies(self) -> Mapping[str, str]:
        """Get parsed cookies."""
        if self._cookies is None:
            cookie_header = self.header("cookie", "")
            if cookie_header:
                cookie = SimpleCookie()
                cookie.load(cookie_header)
                self._cookies = {key: morsel.value for key, morsel in cookie.items()}
            else:
                self._cookies = {}
        return self._cookies
    
    def cookie(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get single cookie value."""
        return self.cookies.get(name, default)
    
    # ========================================================================
    # URL Building
    # ========================================================================
    
    def url(self) -> URL:
        """Get full request URL."""
        if self._url is None:
            scheme = self.scope.get("scheme", "http")
            host = self.header("host", "localhost")
            path = self.path
            query = self.query_string
            
            # Parse port from host if present
            if ":" in host:
                host_part, port_part = host.rsplit(":", 1)
                try:
                    port = int(port_part)
                except ValueError:
                    host_part = host
                    port = None
            else:
                host_part = host
                port = None
            
            self._url = URL(
                scheme=scheme,
                host=host_part,
                port=port,
                path=path,
                query=query,
            )
        return self._url
    
    def base_url(self) -> URL:
        """Get base URL (scheme + host + root_path)."""
        url = self.url()
        root_path = self.scope.get("root_path", "")
        return url.replace(path=root_path or "/", query="", fragment="")
    
    def url_for(self, route_name: str, /, **params) -> str:
        """
        Build URL for named route.
        
        This requires a router/URL builder to be injected via state.
        
        Args:
            route_name: Name of the route
            **params: Route parameters
        
        Returns:
            Built URL string
        """
        # Hook for DI-injected URL builder
        url_builder = self.state.get("url_builder")
        if url_builder:
            return url_builder(route_name, **params)
        
        # Fallback: return route name as placeholder
        return f"/{route_name}"
    
    # ========================================================================
    # Client IP (with proxy support)
    # ========================================================================
    
    def client_ip(self) -> str:
        """
        Get client IP address.
        
        Respects trust_proxy configuration to parse forwarded headers.
        
        Returns:
            Client IP address as string
        """
        if not self.trust_proxy:
            # Direct connection
            client = self.client
            return client[0] if client else "0.0.0.0"
        
        # Parse forwarded headers
        # Try X-Forwarded-For first
        forwarded_for = self.header("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can be comma-separated list
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            if ips:
                # Return first (original client)
                return ips[0]
        
        # Try Forwarded header (RFC 7239)
        forwarded = self.header("forwarded")
        if forwarded:
            # Parse "for=..." directive
            import re
            match = re.search(r'for=([^;,]+)', forwarded)
            if match:
                ip_part = match.group(1).strip('"')
                # Remove port if present
                if ":" in ip_part and not "[" in ip_part:
                    ip_part = ip_part.rsplit(":", 1)[0]
                return ip_part.strip("[]")
        
        # Fallback to direct client
        client = self.client
        return client[0] if client else "0.0.0.0"
    
    # ========================================================================
    # Content Helpers
    # ========================================================================
    
    def content_type(self) -> Optional[str]:
        """Get Content-Type header."""
        return self.header("content-type")
    
    def content_length(self) -> Optional[int]:
        """Get Content-Length header as int."""
        length = self.header("content-length")
        if length:
            try:
                return int(length)
            except ValueError:
                return None
        return None
    
    def is_json(self) -> bool:
        """Check if request content type is JSON."""
        ct = self.content_type()
        if ct:
            parsed = ParsedContentType.parse(ct)
            if parsed:
                return parsed.media_type in (
                    "application/json",
                    "application/x-json",
                    "text/json",
                )
        return False
    
    def accepts(self, *media_types: str) -> bool:
        """
        Check if client accepts any of the given media types.
        
        Args:
            *media_types: Media types to check
        
        Returns:
            True if any media type is accepted
        """
        accept = self.header("accept", "*/*")
        accept_lower = accept.lower()
        
        for media_type in media_types:
            if media_type.lower() in accept_lower or "*/*" in accept_lower:
                return True
        
        return False
    
    # ========================================================================
    # Range & Conditional Headers
    # ========================================================================
    
    def range(self) -> Optional[Range]:
        """Parse Range header."""
        range_header = self.header("range")
        return Range.parse(range_header)
    
    def if_modified_since(self) -> Optional[Any]:
        """Parse If-Modified-Since header."""
        ims = self.header("if-modified-since")
        return parse_date_header(ims)
    
    def if_none_match(self) -> Optional[str]:
        """Get If-None-Match header (ETag)."""
        return self.header("if-none-match")
    
    # ========================================================================
    # Authorization Helpers
    # ========================================================================
    
    def auth_scheme(self) -> Optional[str]:
        """Get authorization scheme (e.g., 'Bearer', 'Basic')."""
        auth = self.header("authorization")
        parsed = parse_authorization_header(auth)
        return parsed[0] if parsed else None
    
    def auth_credentials(self) -> Optional[str]:
        """Get authorization credentials."""
        auth = self.header("authorization")
        parsed = parse_authorization_header(auth)
        return parsed[1] if parsed else None
    
    # ========================================================================
    # Body Reading (Streaming & Single-shot)
    # ========================================================================
    
    async def _receive_message(self) -> dict:
        """
        Receive next ASGI message.
        
        Handles disconnect detection.
        """
        try:
            message = await self._receive()
            if message["type"] == "http.disconnect":
                self._disconnected = True
                raise ClientDisconnect("Client disconnected")
            return message
        except asyncio.CancelledError:
            self._disconnected = True
            raise
    
    def is_disconnected(self) -> bool:
        """Check if client has disconnected."""
        return self._disconnected
    
    async def iter_bytes(self, chunk_size: Optional[int] = None) -> AsyncIterator[bytes]:
        """
        Stream request body in chunks.
        
        Args:
            chunk_size: Size of chunks (uses default if not specified)
        
        Yields:
            Body chunks
        
        Raises:
            ClientDisconnect: If client disconnects during streaming
            PayloadTooLarge: If body exceeds max_body_size
        """
        chunk_size = chunk_size or self.chunk_size
        
        # If body already consumed, yield from cache
        if self._body is not None:
            for i in range(0, len(self._body), chunk_size):
                yield self._body[i:i + chunk_size]
            return
        
        if self._body_consumed:
            # Already streamed, nothing to yield
            return
        
        # Stream from ASGI
        total_size = 0
        
        while True:
            message = await self._receive_message()
            
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                
                if chunk:
                    total_size += len(chunk)
                    if total_size > self.max_body_size:
                        raise PayloadTooLarge(
                            f"Request body exceeds maximum size",
                            max_allowed=self.max_body_size,
                            actual=total_size,
                        )
                    yield chunk
                
                if not message.get("more_body", False):
                    break
        
        self._body_consumed = True
    
    async def iter_text(
        self, 
        encoding: str = "utf-8", 
        chunk_size: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Stream request body as text chunks.
        
        Args:
            encoding: Text encoding
            chunk_size: Size of chunks
        
        Yields:
            Text chunks
        """
        async for chunk in self.iter_bytes(chunk_size):
            yield chunk.decode(encoding)
    
    async def body(self) -> bytes:
        """
        Read full request body (idempotent).
        
        Returns:
            Complete request body as bytes
        
        Raises:
            ClientDisconnect: If client disconnects
            PayloadTooLarge: If body exceeds max_body_size
        """
        if self._body is not None:
            return self._body
        
        chunks = []
        total_size = 0
        
        async for chunk in self.iter_bytes():
            chunks.append(chunk)
            total_size += len(chunk)
        
        self._body = b"".join(chunks)
        return self._body
    
    async def text(self, encoding: Optional[str] = None) -> str:
        """
        Read request body as text.
        
        Args:
            encoding: Text encoding (auto-detected from Content-Type if None)
        
        Returns:
            Request body as string
        """
        body_bytes = await self.body()
        
        # Auto-detect encoding from Content-Type
        if encoding is None:
            ct = self.content_type()
            if ct:
                parsed_ct = ParsedContentType.parse(ct)
                if parsed_ct:
                    encoding = parsed_ct.charset
            encoding = encoding or "utf-8"
        
        return body_bytes.decode(encoding)
    
    async def readexactly(self, n: int) -> bytes:
        """
        Read exactly n bytes from request body.
        
        Args:
            n: Number of bytes to read
        
        Returns:
            Exactly n bytes
        
        Raises:
            EOFError: If fewer than n bytes available
        """
        result = bytearray()
        
        async for chunk in self.iter_bytes():
            result.extend(chunk)
            if len(result) >= n:
                self._body = bytes(result)  # Cache what we read
                return bytes(result[:n])
        
        if len(result) < n:
            raise EOFError(f"Expected {n} bytes, got {len(result)}")
        
        return bytes(result)
    
    # ========================================================================
    # JSON Parsing
    # ========================================================================
    
    async def json(
        self, 
        model: Optional[Type[T]] = None, 
        *, 
        strict: bool = True
    ) -> Union[Any, T]:
        """
        Parse request body as JSON.
        
        Args:
            model: Optional model class for validation (Pydantic, dataclass, etc.)
            strict: Whether to enforce strict parsing
        
        Returns:
            Parsed JSON data or validated model instance
        
        Raises:
            InvalidJSON: If JSON is malformed
            PayloadTooLarge: If JSON exceeds size limits
            BadRequest: If validation fails
        """
        if self._json is not None:
            # Already parsed
            if model:
                return self._validate_json_model(self._json, model)
            return self._json
        
        # Read body with size limit
        body_bytes = await self.body()
        
        if len(body_bytes) > self.json_max_size:
            raise PayloadTooLarge(
                f"JSON payload exceeds maximum size",
                max_allowed=self.json_max_size,
                actual=len(body_bytes),
            )
        
        # Parse JSON
        try:
            text = body_bytes.decode("utf-8")
            self._json = stdlib_json.loads(text)
        except UnicodeDecodeError as e:
            raise InvalidJSON(f"Invalid UTF-8 in JSON payload: {e}")
        except stdlib_json.JSONDecodeError as e:
            raise InvalidJSON(f"Invalid JSON: {e}")
        
        # Check depth
        if not self._check_json_depth(self._json, self.json_max_depth):
            raise InvalidJSON(
                f"JSON nesting exceeds maximum depth",
                max_depth=self.json_max_depth,
            )
        
        # Validate with model if provided
        if model:
            return self._validate_json_model(self._json, model)
        
        return self._json
    
    def _check_json_depth(self, obj: Any, max_depth: int, current_depth: int = 0) -> bool:
        """Check if JSON nesting depth is within limits."""
        if current_depth > max_depth:
            return False
        
        if isinstance(obj, dict):
            for value in obj.values():
                if not self._check_json_depth(value, max_depth, current_depth + 1):
                    return False
        elif isinstance(obj, list):
            for item in obj:
                if not self._check_json_depth(item, max_depth, current_depth + 1):
                    return False
        
        return True
    
    def _validate_json_model(self, data: Any, model: Type[T]) -> T:
        """Validate JSON data against model."""
        try:
            # Pydantic v2
            if hasattr(model, "model_validate"):
                return model.model_validate(data)
            # Pydantic v1
            elif hasattr(model, "parse_obj"):
                return model.parse_obj(data)
            # Dataclass or callable
            elif callable(model):
                return model(**data) if isinstance(data, dict) else model(data)
            else:
                return data
        except Exception as e:
            raise BadRequest(f"JSON validation failed: {e}", model=model.__name__)
    
    # ========================================================================
    # Form & Multipart Parsing
    # ========================================================================
    
    async def form(self) -> FormData:
        """
        Parse application/x-www-form-urlencoded form data.
        
        Returns:
            FormData object with fields
        
        Raises:
            UnsupportedMediaType: If Content-Type is not form-urlencoded
            BadRequest: If form data is malformed
        """
        if self._form_data is not None:
            return self._form_data
        
        ct = self.content_type()
        if not ct:
            raise UnsupportedMediaType("No Content-Type header")
        
        parsed_ct = ParsedContentType.parse(ct)
        if not parsed_ct or parsed_ct.media_type != "application/x-www-form-urlencoded":
            raise UnsupportedMediaType(
                f"Expected application/x-www-form-urlencoded, got {ct}"
            )
        
        # Read body
        body_bytes = await self.body()
        body_str = body_bytes.decode(parsed_ct.charset)
        
        # Parse form data
        items = parse_qsl(body_str, keep_blank_values=True)
        
        if len(items) > self.max_field_count:
            raise BadRequest(
                f"Too many form fields",
                max_allowed=self.max_field_count,
                actual=len(items),
            )
        
        fields = MultiDict(items)
        self._form_data = FormData(fields=fields, files={})
        
        return self._form_data
    
    async def multipart(self) -> FormData:
        """
        Parse multipart/form-data.
        
        Supports streaming file uploads with disk spilling.
        
        Returns:
            FormData object with fields and files
        
        Raises:
            UnsupportedMediaType: If Content-Type is not multipart/form-data
            MultipartParseError: If multipart parsing fails
        """
        if self._form_data is not None:
            return self._form_data
        
        if not MULTIPART_AVAILABLE:
            raise MultipartParseError(
                "python-multipart library not available. "
                "Install with: pip install python-multipart"
            )
        
        ct = self.content_type()
        if not ct:
            raise UnsupportedMediaType("No Content-Type header")
        
        parsed_ct = ParsedContentType.parse(ct)
        if not parsed_ct or not parsed_ct.media_type.startswith("multipart/"):
            raise UnsupportedMediaType(
                f"Expected multipart/form-data, got {ct}"
            )
        
        boundary = parsed_ct.boundary
        if not boundary:
            raise BadRequest("No boundary in multipart Content-Type")
        
        # Parse multipart
        return await self._parse_multipart_streaming(boundary.encode())
    
    async def _parse_multipart_streaming(self, boundary: bytes) -> FormData:
        """
        Parse multipart form data with streaming support using python-multipart.
        
        Features:
        - RFC 7578 compliant multipart parsing
        - Streaming with incremental processing
        - Memory-efficient: small files in memory, large files spilled to disk
        - Proper error handling and resource cleanup
        - Size limits enforcement
        """
        fields = MultiDict()
        files: Dict[str, List[UploadFile]] = {}
        
        # Temp directory for uploads
        temp_dir = self.upload_tempdir or Path(tempfile.gettempdir()) / "aquilia_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Current part state
        part_count = 0
        current_field_name: Optional[str] = None
        current_filename: Optional[str] = None
        current_content_type: Optional[str] = None
        current_data = bytearray()
        current_temp_file: Optional[Path] = None
        current_file_handle = None
        current_size = 0
        
        # Header tracking (use list to allow reassignment in nested functions)
        header_state = {
            'field': bytearray(),
            'value': bytearray(),
            'headers': {}
        }
        
        def on_part_begin():
            """Called when a new multipart part begins."""
            nonlocal part_count, current_field_name, current_filename
            nonlocal current_content_type, current_data, current_temp_file
            nonlocal current_file_handle, current_size
            
            part_count += 1
            if part_count > self.max_field_count:
                raise BadRequest(
                    f"Too many multipart parts",
                    max_allowed=self.max_field_count,
                    actual=part_count,
                )
            
            # Reset state
            current_field_name = None
            current_filename = None
            current_content_type = "text/plain"
            current_data = bytearray()
            current_temp_file = None
            current_file_handle = None
            current_size = 0
            header_state['field'] = bytearray()
            header_state['value'] = bytearray()
            header_state['headers'] = {}
        
        def on_part_data(data: bytes, start: int, end: int):
            """Called when part data is received (can be called multiple times)."""
            nonlocal current_data, current_size, current_temp_file, current_file_handle
            
            chunk = data[start:end]
            current_size += len(chunk)
            
            # Enforce file size limits
            if current_filename and current_size > self.max_file_size:
                # Close file handle if open
                if current_file_handle:
                    current_file_handle.close()
                    current_file_handle = None
                
                raise PayloadTooLarge(
                    f"File upload exceeds maximum size",
                    max_allowed=self.max_file_size,
                    actual=current_size,
                    filename=current_filename,
                )
            
            # Handle file uploads with disk spilling
            if current_filename:
                # Check if we should spill to disk
                if current_size > self.form_memory_threshold and not current_temp_file:
                    # Create temp file and write buffered data
                    current_temp_file = temp_dir / f"{uuid.uuid4().hex}_{current_filename}"
                    current_file_handle = open(current_temp_file, "wb")
                    
                    # Write buffered data to disk
                    if current_data:
                        current_file_handle.write(current_data)
                        current_data = bytearray()  # Clear buffer
                    
                    self._temp_files.append(current_temp_file)
                
                # Write to file or buffer
                if current_temp_file and current_file_handle:
                    current_file_handle.write(chunk)
                else:
                    current_data.extend(chunk)
            else:
                # Regular field - keep in memory
                current_data.extend(chunk)
        
        def on_part_end():
            """Called when a multipart part ends."""
            nonlocal current_field_name, current_filename, current_data
            nonlocal current_temp_file, current_file_handle
            
            # Close file handle if open
            if current_file_handle:
                current_file_handle.close()
                current_file_handle = None
            
            if not current_field_name:
                return
            
            if current_filename:
                # File upload
                if current_temp_file:
                    # File was spilled to disk
                    upload = create_upload_file_from_path(
                        filename=current_filename,
                        file_path=current_temp_file,
                        content_type=current_content_type or "application/octet-stream",
                    )
                else:
                    # File kept in memory
                    upload = create_upload_file_from_bytes(
                        filename=current_filename,
                        content=bytes(current_data),
                        content_type=current_content_type or "application/octet-stream",
                    )
                
                # Add to files dict
                if current_field_name not in files:
                    files[current_field_name] = []
                files[current_field_name].append(upload)
            else:
                # Regular field
                try:
                    value = current_data.decode("utf-8")
                except UnicodeDecodeError:
                    value = current_data.decode("utf-8", errors="replace")
                
                fields.add(current_field_name, value)
        
        def on_header_field(data: bytes, start: int, end: int):
            """Called when header field name is received."""
            header_state['field'].extend(data[start:end])
        
        def on_header_value(data: bytes, start: int, end: int):
            """Called when header value is received."""
            header_state['value'].extend(data[start:end])
        
        def on_header_end():
            """Called when a single header line ends."""
            if header_state['field']:
                field_name = header_state['field'].decode("utf-8", errors="replace").lower()
                field_value = header_state['value'].decode("utf-8", errors="replace")
                header_state['headers'][field_name] = field_value
            
            # Reset for next header
            header_state['field'] = bytearray()
            header_state['value'] = bytearray()
        
        def on_headers_finished():
            """Called after all headers parsed - extract metadata."""
            nonlocal current_field_name, current_filename, current_content_type
            
            # Extract field name and filename from Content-Disposition
            content_disposition = header_state['headers'].get("content-disposition", "")
            if content_disposition:
                # Parse using python-multipart helper
                _, options = parse_options_header(content_disposition)
                
                # parse_options_header returns bytes keys/values
                current_field_name = options.get(b"name")
                if current_field_name and isinstance(current_field_name, bytes):
                    current_field_name = current_field_name.decode("utf-8")
                
                filename = options.get(b"filename")
                if filename:
                    if isinstance(filename, bytes):
                        filename = filename.decode("utf-8")
                    # Sanitize filename
                    current_filename = self._sanitize_filename(filename)
            
            # Extract Content-Type
            content_type = header_state['headers'].get("content-type")
            if content_type:
                current_content_type = content_type
        
        # Create parser with callbacks
        callbacks = {
            "on_part_begin": on_part_begin,
            "on_part_data": on_part_data,
            "on_part_end": on_part_end,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end": on_header_end,
            "on_headers_finished": on_headers_finished,
        }
        
        parser = MultipartParser(boundary, callbacks)
        
        try:
            # Stream body to parser
            async for chunk in self.iter_bytes():
                # Feed chunk to parser
                bytes_parsed = parser.write(chunk)
                
                if bytes_parsed != len(chunk):
                    raise MultipartParseError(
                        f"Parser did not consume all bytes: expected {len(chunk)}, got {bytes_parsed}"
                    )
            
            # Finalize parsing
            parser.finalize()
            
        except PayloadTooLarge:
            # Re-raise size limit errors
            raise
        except BadRequest:
            # Re-raise field count errors
            raise
        except Exception as e:
            # Cleanup on error
            if current_file_handle:
                current_file_handle.close()
            await self.cleanup()
            
            # Wrap in MultipartParseError
            if isinstance(e, (RequestFault, Fault)):
                raise
            raise MultipartParseError(f"Multipart parsing failed: {e}")
        
        self._form_data = FormData(fields=fields, files=files)
        return self._form_data
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize uploaded filename."""
        import os
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = filename.replace("\x00", "")
        unsafe = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        for char in unsafe:
            filename = filename.replace(char, "_")
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        
        return filename or "unnamed"
    
    async def files(self) -> Mapping[str, List[UploadFile]]:
        """
        Get uploaded files from multipart request.
        
        Returns:
            Dictionary of field names to lists of UploadFile objects
        """
        form_data = await self.multipart()
        return form_data.files
    
    # ========================================================================
    # Upload Helpers
    # ========================================================================
    
    async def save_upload(
        self, 
        upload: UploadFile, 
        dest: Union[str, PathLike], 
        *, 
        overwrite: bool = False
    ) -> Path:
        """
        Save uploaded file to destination.
        
        Args:
            upload: UploadFile to save
            dest: Destination path
            overwrite: Whether to overwrite existing file
        
        Returns:
            Path to saved file
        """
        return await upload.save(dest, overwrite=overwrite)
    
    async def stream_upload_to_store(
        self, 
        upload: UploadFile, 
        store: UploadStore
    ) -> Path:
        """
        Stream upload to custom storage backend.
        
        Args:
            upload: UploadFile to stream
            store: UploadStore implementation
        
        Returns:
            Final storage path/identifier
        """
        upload_id = str(uuid.uuid4())
        
        try:
            # Stream chunks to store
            async for chunk in upload.stream():
                await store.write_chunk(upload_id, chunk)
            
            # Finalize
            metadata = {
                "filename": upload.filename,
                "content_type": upload.content_type,
                "size": upload.size,
            }
            return await store.finalize(upload_id, metadata)
        
        except Exception as e:
            # Abort on error
            await store.abort(upload_id)
            raise
    
    # ========================================================================
    # Identity Integration (Auth System)
    # ========================================================================
    
    @property
    def identity(self) -> Optional[Any]:  # Returns Identity | None
        """
        Get authenticated identity (set by AuthMiddleware).
        
        Returns:
            Identity object if authenticated, None otherwise
        """
        return self.state.get("identity")
    
    @property
    def authenticated(self) -> bool:
        """
        Check if request is authenticated.
        
        Returns:
            True if identity is present, False otherwise
        """
        return self.identity is not None
    
    def require_identity(self) -> Any:  # Returns Identity
        """
        Get identity or raise AUTH_REQUIRED fault.
        
        Returns:
            Identity object
            
        Raises:
            Fault: AUTH_REQUIRED if no identity
        """
        identity = self.identity
        if not identity:
            # Import here to avoid circular dependency
            from aquilia.faults import Fault, FaultDomain, Severity
            raise Fault(
                code="AUTH_REQUIRED",
                message="Authentication required",
                domain=FaultDomain.SECURITY,
                severity=Severity.WARN,
                metadata={"path": self.path, "method": self.method}
            )
        return identity
    
    def has_role(self, role: str) -> bool:
        """
        Check if identity has specific role.
        
        Args:
            role: Role name to check
            
        Returns:
            True if identity has role, False otherwise
        """
        return self.identity and hasattr(self.identity, "has_role") and self.identity.has_role(role)
    
    def has_scope(self, scope: str) -> bool:
        """
        Check if identity has OAuth scope.
        
        Args:
            scope: Scope name to check
            
        Returns:
            True if identity has scope, False otherwise
        """
        return self.identity and hasattr(self.identity, "has_scope") and self.identity.has_scope(scope)
    
    # ========================================================================
    # Session Integration
    # ========================================================================
    
    @property
    def session(self) -> Optional[Any]:  # Returns Session | None
        """
        Get session (set by SessionMiddleware).
        
        Returns:
            Session object if available, None otherwise
        """
        return self.state.get("session")
    
    def require_session(self) -> Any:  # Returns Session
        """
        Get session or raise SESSION_REQUIRED fault.
        
        Returns:
            Session object
            
        Raises:
            Fault: SESSION_REQUIRED if no session
        """
        session = self.session
        if not session:
            from aquilia.faults import Fault, FaultDomain, Severity
            raise Fault(
                code="SESSION_REQUIRED",
                message="Session required",
                domain=FaultDomain.IO,
                severity=Severity.WARN,
                metadata={"path": self.path, "method": self.method}
            )
        return session
    
    @property
    def session_id(self) -> Optional[str]:
        """
        Get session ID.
        
        Returns:
            Session ID if session available, None otherwise
        """
        session = self.session
        return session.id if session and hasattr(session, "id") else None
    
    # ========================================================================
    # DI Container Integration
    # ========================================================================
    
    @property
    def container(self) -> Optional[Any]:  # Returns Container | None
        """
        Get request-scoped DI container.
        
        Returns:
            DI Container if available, None otherwise
        """
        return self.state.get("di_container") or self.state.get("container")
    
    async def resolve(self, service_type: Type[T], *, optional: bool = False) -> Optional[T]:
        """
        Resolve service from DI container.
        
        Args:
            service_type: Type of service to resolve
            optional: If True, return None instead of raising error
            
        Returns:
            Resolved service instance
            
        Raises:
            RuntimeError: If container not available and optional=False
        """
        container = self.container
        if not container:
            if optional:
                return None
            raise RuntimeError("DI container not available in request")
        
        # Support both sync and async resolve
        if hasattr(container, "resolve_async"):
            return await container.resolve_async(service_type, optional=optional)
        elif hasattr(container, "resolve"):
            result = container.resolve(service_type, optional=optional)
            # If result is awaitable, await it
            if hasattr(result, "__await__"):
                return await result
            return result
        else:
            if optional:
                return None
            raise RuntimeError("Container does not support resolution")
    
    async def inject(self, **services) -> Dict[str, Any]:
        """
        Inject multiple services by name.
        
        Args:
            **services: Mapping of name to service type
            
        Returns:
            Dict mapping names to resolved services
            
        Example:
            services = await request.inject(
                auth=AuthManager,
                session_engine=SessionEngine,
            )
        """
        container = self.container
        if not container:
            return {}
        
        results = {}
        for name, service_type in services.items():
            try:
                results[name] = await self.resolve(service_type, optional=True)
            except Exception:
                results[name] = None
        return results
    
    @property
    def identity(self) -> Optional[Any]:
        """Get authenticated identity from request state."""
        return self.state.get("identity")

    @property
    def session(self) -> Optional[Any]:
        """Get session from request state."""
        return self.state.get("session")

    @property
    def authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.state.get("authenticated", False)

    # ========================================================================
    # Template Context Integration
    # ========================================================================
    
    def flash_messages(self) -> List[Dict[str, Any]]:
        """Get and clear flash messages from session."""
        if not self.session:
            return []
        return self.session.data.pop("_flash_messages", [])

    def has_role(self, role: str) -> bool:
        """Check if authenticated identity has a specific role."""
        if not self.identity:
            return False
        roles = self.identity.get_attribute("roles", [])
        return role in roles

    def is_authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.authenticated

    @property
    def template_context(self) -> Dict[str, Any]:
        """
        Get template rendering context with auto-injected variables.
        
        Automatically includes:
        - request: This request object
        - identity: Authenticated identity (if any)
        - session: Session object (if any)
        - authenticated: Boolean authentication status
        - is_authenticated: Helper to check authentication status
        - url: Current URL
        - method: HTTP method
        - path: Request path
        - flash_messages: Helper to get flash messages
        - has_role: Helper to check user roles
        
        Returns:
            Dict of template context variables
        """
        context = self.state.get("template_context", {}).copy()
        
        # Auto-inject common variables
        context.setdefault("request", self)
        context.setdefault("identity", self.identity)
        context.setdefault("session", self.session)
        context.setdefault("authenticated", self.authenticated)
        context.setdefault("is_authenticated", self.is_authenticated)
        context.setdefault("url", self.url())
        context.setdefault("method", self.method)
        context.setdefault("path", self.path)
        context.setdefault("query_params", dict(self.query_params))
        context.setdefault("flash_messages", self.flash_messages)
        context.setdefault("has_role", self.has_role)
        
        return context
    
    def add_template_context(self, **kwargs) -> None:
        """
        Add variables to template context.
        
        Args:
            **kwargs: Variables to add to context
            
        Example:
            request.add_template_context(title="Home", user=user)
        """
        if "template_context" not in self.state:
            self.state["template_context"] = {}
        self.state["template_context"].update(kwargs)
    
    # ========================================================================
    # Lifecycle & Effects Integration
    # ========================================================================
    
    async def emit_effect(self, effect_name: str, **data) -> None:
        """
        Emit effect for lifecycle hooks.
        
        Args:
            effect_name: Name of the effect to emit
            **data: Additional data to pass to effect handlers
        """
        lifecycle = self.state.get("lifecycle_manager")
        if lifecycle and hasattr(lifecycle, "emit"):
            await lifecycle.emit(effect_name, request=self, **data)
    
    async def before_response(self, callback: Callable[..., Awaitable[None]]) -> None:
        """
        Register callback to run before response is sent.
        
        Args:
            callback: Async callable to execute before response
        """
        callbacks = self.state.setdefault("before_response_callbacks", [])
        callbacks.append(callback)
    
    async def after_response(self, callback: Callable[..., Awaitable[None]]) -> None:
        """
        Register callback to run after response is sent.
        
        Args:
            callback: Async callable to execute after response
        """
        callbacks = self.state.setdefault("after_response_callbacks", [])
        callbacks.append(callback)
    
    # ========================================================================
    # Enhanced Fault Handling
    # ========================================================================
    
    def fault_context(self) -> Dict[str, Any]:
        """
        Get context for fault reporting.
        
        Returns:
            Dict with request metadata for fault enrichment
        """
        return {
            "method": self.method,
            "path": self.path,
            "query": self.query_string,
            "client_ip": self.client_ip(),
            "user_agent": self.header("user-agent"),
            "identity_id": self.identity.id if self.identity and hasattr(self.identity, "id") else None,
            "session_id": self.session_id,
            "request_id": self.state.get("request_id"),
            "trace_id": self.trace_id,
            "authenticated": self.authenticated,
        }
    
    async def report_fault(self, fault: Fault) -> None:
        """
        Report fault through FaultEngine with request context.
        
        Args:
            fault: Fault to report
        """
        fault_engine = self.state.get("fault_engine")
        if fault_engine and hasattr(fault_engine, "process"):
            # Enrich fault with request context
            if hasattr(fault, "metadata"):
                fault.metadata.update(self.fault_context())
            await fault_engine.process(fault)
    
    # ========================================================================
    # Metrics & Tracing Integration
    # ========================================================================
    
    @property
    def trace_id(self) -> Optional[str]:
        """
        Get trace ID for distributed tracing.
        
        Returns:
            Trace ID from state or header
        """
        return self.state.get("trace_id") or self.header("x-trace-id")
    
    @property
    def request_id(self) -> Optional[str]:
        """
        Get unique request ID.
        
        Returns:
            Request ID from state
        """
        return self.state.get("request_id")
    
    def record_metric(self, name: str, value: float, **tags) -> None:
        """
        Record metric for this request.
        
        Args:
            name: Metric name
            value: Metric value
            **tags: Additional tags for metric
        """
        metrics = self.state.get("metrics_collector")
        if metrics and hasattr(metrics, "record"):
            tags.update({
                "method": self.method,
                "path": self.path,
                "authenticated": self.authenticated,
            })
            metrics.record(name, value, **tags)
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    async def cleanup(self) -> None:
        """
        Clean up temporary resources.
        
        Removes temporary upload files.
        """
        # Cleanup form data uploads
        if self._form_data:
            await self._form_data.cleanup()
        
        # Cleanup tracked temp files
        for temp_file in self._temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
        
        self._temp_files.clear()
    
    def __del__(self):
        """Best-effort cleanup on garbage collection."""
        # Note: __del__ is sync, so this is limited
        for temp_file in self._temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
    
    # ========================================================================
    # Legacy Compatibility
    # ========================================================================
    
    def path_params(self) -> Dict[str, Any]:
        """Get path parameters (set by router via state)."""
        return self.state.get("path_params", {})
