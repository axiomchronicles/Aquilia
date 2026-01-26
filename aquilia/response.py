"""
Response - HTTP response builder with streaming support.
"""

from typing import Any, AsyncIterator, Dict, Optional, Union
import json as json_lib


class Response:
    """
    HTTP response builder supporting bytes, strings, and async streaming.
    """
    
    def __init__(
        self,
        content: Union[bytes, str, dict, list, AsyncIterator[bytes]] = b"",
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.status = status
        self.headers = headers or {}
        self._content = content
        
        # Auto-detect media type
        if media_type:
            self.headers["content-type"] = media_type
        elif isinstance(content, (dict, list)):
            self.headers.setdefault("content-type", "application/json")
        elif isinstance(content, str):
            self.headers.setdefault("content-type", "text/plain; charset=utf-8")
        elif isinstance(content, bytes):
            self.headers.setdefault("content-type", "application/octet-stream")
    
    @classmethod
    def json(cls, data: Any, status: int = 200, **kwargs) -> "Response":
        """Create JSON response."""
        content = json_lib.dumps(data, **kwargs)
        return cls(
            content=content,
            status=status,
            media_type="application/json",
        )
    
    @classmethod
    def html(cls, content: str, status: int = 200) -> "Response":
        """Create HTML response."""
        return cls(
            content=content,
            status=status,
            media_type="text/html; charset=utf-8",
        )
    
    @classmethod
    def text(cls, content: str, status: int = 200) -> "Response":
        """Create text response."""
        return cls(
            content=content,
            status=status,
            media_type="text/plain; charset=utf-8",
        )
    
    @classmethod
    def redirect(cls, url: str, status: int = 307) -> "Response":
        """Create redirect response."""
        return cls(
            content=b"",
            status=status,
            headers={"location": url},
        )
    
    @classmethod
    def stream(cls, iterator: AsyncIterator[bytes], media_type: str = "application/octet-stream") -> "Response":
        """Create streaming response."""
        return cls(
            content=iterator,
            status=200,
            media_type=media_type,
        )
    
    @classmethod
    def render(
        cls,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = "text/html; charset=utf-8",
        engine: Optional[Any] = None,
        request_ctx: Optional[Any] = None
    ) -> "Response":
        """
        Render template and return Response.
        
        Args:
            template_name: Template name
            context: Template variables
            status: HTTP status code
            headers: Additional headers
            content_type: Content-Type header
            engine: TemplateEngine instance (if not using DI)
            request_ctx: Request context
        
        Returns:
            Response with rendered template
        
        Example:
            return Response.render("profile.html", {"user": user})
        """
        # Lazy import to avoid circular dependency
        from aquilia.templates import TemplateEngine
        
        if engine is None:
            # Try to get engine from DI (if available)
            # For now, raise error - engine must be provided
            raise ValueError(
                "TemplateEngine not provided. "
                "Pass engine parameter or use controller.render() helper."
            )
        
        # Create async render function
        async def _render():
            return await engine.render(template_name, context, request_ctx)
        
        return cls(
            content=_render(),
            status=status,
            headers=headers,
            media_type=content_type
        )
    
    def set_cookie(
        self,
        key: str,
        value: str,
        max_age: Optional[int] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None,
    ):
        """Set a cookie."""
        cookie = f"{key}={value}"
        
        if max_age is not None:
            cookie += f"; Max-Age={max_age}"
        
        cookie += f"; Path={path}"
        
        if domain:
            cookie += f"; Domain={domain}"
        
        if secure:
            cookie += "; Secure"
        
        if httponly:
            cookie += "; HttpOnly"
        
        if samesite:
            cookie += f"; SameSite={samesite}"
        
        # Support multiple Set-Cookie headers
        if "set-cookie" in self.headers:
            existing = self.headers["set-cookie"]
            if isinstance(existing, list):
                existing.append(cookie)
            else:
                self.headers["set-cookie"] = [existing, cookie]
        else:
            self.headers["set-cookie"] = cookie
    
    def delete_cookie(self, key: str, path: str = "/", domain: Optional[str] = None):
        """Delete a cookie."""
        self.set_cookie(key, "", max_age=0, path=path, domain=domain)
    
    async def send_asgi(self, send: callable):
        """Send response via ASGI."""
        # Prepare headers
        headers = []
        for key, value in self.headers.items():
            if isinstance(value, list):
                for v in value:
                    headers.append((key.encode(), v.encode()))
            else:
                headers.append((key.encode(), value.encode()))
        
        # Send start
        await send({
            "type": "http.response.start",
            "status": self.status,
            "headers": headers,
        })
        
        # Send body
        if hasattr(self._content, "__aiter__"):
            # Streaming response
            async for chunk in self._content:
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                })
            
            # Send final empty chunk
            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            })
        elif callable(self._content):
            # Async callable (e.g., template render)
            try:
                rendered = await self._content()
                body = self._encode_body(rendered)
                await send({
                    "type": "http.response.body",
                    "body": body,
                    "more_body": False,
                })
            except Exception as e:
                # Handle render errors
                error_body = f"Template render error: {str(e)}".encode()
                await send({
                    "type": "http.response.body",
                    "body": error_body,
                    "more_body": False,
                })
        else:
            # Regular response
            body = self._encode_body(self._content)
            
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })
    
    def _encode_body(self, content: Any) -> bytes:
        """Encode content to bytes."""
        if isinstance(content, bytes):
            return content
        elif isinstance(content, str):
            return content.encode("utf-8")
        elif isinstance(content, (dict, list)):
            return json_lib.dumps(content).encode("utf-8")
        else:
            return str(content).encode("utf-8")


# Common response factories

def Ok(content: Any = None, **kwargs) -> Response:
    """200 OK response."""
    if content is None:
        content = {"status": "ok"}
    return Response.json(content, status=200, **kwargs)


def Created(content: Any = None, **kwargs) -> Response:
    """201 Created response."""
    if content is None:
        content = {"status": "created"}
    return Response.json(content, status=201, **kwargs)


def NoContent() -> Response:
    """204 No Content response."""
    return Response(b"", status=204)


def BadRequest(message: str = "Bad Request", **kwargs) -> Response:
    """400 Bad Request response."""
    return Response.json({"error": message}, status=400, **kwargs)


def Unauthorized(message: str = "Unauthorized", **kwargs) -> Response:
    """401 Unauthorized response."""
    return Response.json({"error": message}, status=401, **kwargs)


def Forbidden(message: str = "Forbidden", **kwargs) -> Response:
    """403 Forbidden response."""
    return Response.json({"error": message}, status=403, **kwargs)


def NotFound(message: str = "Not Found", **kwargs) -> Response:
    """404 Not Found response."""
    return Response.json({"error": message}, status=404, **kwargs)


def InternalError(message: str = "Internal Server Error", **kwargs) -> Response:
    """500 Internal Server Error response."""
    return Response.json({"error": message}, status=500, **kwargs)
