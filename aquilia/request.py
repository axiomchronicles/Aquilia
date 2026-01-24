"""
Request - ASGI request wrapper with typed parsing and streaming support.
"""

from typing import Any, Dict, Optional, Type, TypeVar
from urllib.parse import parse_qs
import json


T = TypeVar("T")


class Request:
    """
    Request object wrapping ASGI scope and receive callable.
    Provides convenient access to request data.
    """
    
    def __init__(self, scope: dict, receive: callable):
        self.scope = scope
        self._receive = receive
        self._body: Optional[bytes] = None
        self._json: Optional[Any] = None
        self.state: Dict[str, Any] = {}
    
    @property
    def method(self) -> str:
        """HTTP method (GET, POST, etc.)."""
        return self.scope.get("method", "GET")
    
    @property
    def path(self) -> str:
        """Request path."""
        return self.scope.get("path", "/")
    
    @property
    def query_string(self) -> str:
        """Raw query string."""
        return self.scope.get("query_string", b"").decode("utf-8")
    
    @property
    def query(self) -> Dict[str, list]:
        """Parsed query parameters."""
        if not self.query_string:
            return {}
        return parse_qs(self.query_string)
    
    def query_param(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get single query parameter."""
        values = self.query.get(key, [])
        return values[0] if values else default
    
    @property
    def headers(self) -> Dict[str, str]:
        """Request headers."""
        return {
            key.decode("utf-8"): value.decode("utf-8")
            for key, value in self.scope.get("headers", [])
        }
    
    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get single header (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self.headers.items():
            if key.lower() == name_lower:
                return value
        return default
    
    @property
    def content_type(self) -> Optional[str]:
        """Content-Type header."""
        return self.header("content-type")
    
    @property
    def client(self) -> Optional[tuple]:
        """Client address (host, port)."""
        return self.scope.get("client")
    
    @property
    def url(self) -> str:
        """Full URL."""
        scheme = self.scope.get("scheme", "http")
        host = self.header("host", "localhost")
        path = self.path
        query = self.query_string
        
        url = f"{scheme}://{host}{path}"
        if query:
            url += f"?{query}"
        return url
    
    async def body(self) -> bytes:
        """Read full request body."""
        if self._body is None:
            chunks = []
            while True:
                message = await self._receive()
                if message["type"] == "http.request":
                    chunk = message.get("body", b"")
                    if chunk:
                        chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    break
            
            self._body = b"".join(chunks)
        
        return self._body
    
    async def text(self) -> str:
        """Read body as text."""
        body = await self.body()
        return body.decode("utf-8")
    
    async def json(self, model: Optional[Type[T]] = None) -> Any:
        """
        Parse body as JSON.
        
        Args:
            model: Optional type to validate/parse into
            
        Returns:
            Parsed JSON data (or model instance)
        """
        if self._json is None:
            text = await self.text()
            self._json = json.loads(text)
        
        if model:
            # Basic validation/instantiation
            if hasattr(model, "model_validate"):
                # Pydantic v2
                return model.model_validate(self._json)
            elif hasattr(model, "parse_obj"):
                # Pydantic v1
                return model.parse_obj(self._json)
            else:
                # Plain dataclass or dict
                return model(**self._json) if callable(model) else self._json
        
        return self._json
    
    async def form(self) -> Dict[str, list]:
        """Parse form data."""
        body = await self.text()
        return parse_qs(body)
    
    async def stream(self):
        """Stream request body chunks."""
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    yield chunk
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break
    
    def path_params(self) -> Dict[str, Any]:
        """Get path parameters (set by router)."""
        return self.state.get("path_params", {})
