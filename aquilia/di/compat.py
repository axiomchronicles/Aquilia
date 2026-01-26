"""
Compatibility layer with legacy Aquilia DI system.
"""

from contextvars import ContextVar
from typing import Optional

from .core import Container


# Context variable for request container (legacy support)
_request_container_var: ContextVar[Optional[Container]] = ContextVar(
    "request_container",
    default=None,
)


class RequestCtx:
    """
    Legacy RequestCtx compatibility wrapper.
    
    Maps to new Container-based system.
    """
    
    def __init__(self, container: Container):
        self._container = container
    
    @property
    def container(self) -> Container:
        """Get underlying container."""
        return self._container
    
    @container.setter
    def container(self, value: Container):
        """Set underlying container."""
        self._container = value
    
    def get(self, token, *, tag: Optional[str] = None, default=None):
        """
        Get service from container (legacy API).
        
        Args:
            token: Service token/type
            tag: Optional tag
            default: Default value if not found
            
        Returns:
            Service instance or default
        """
        try:
            return self._container.resolve(token, tag=tag, optional=default is not None)
        except Exception:
            return default
    
    async def get_async(self, token, *, tag: Optional[str] = None, default=None):
        """Async version of get."""
        try:
            return await self._container.resolve_async(token, tag=tag, optional=default is not None)
        except Exception:
            return default
    
    @classmethod
    def from_container(cls, container: Container) -> "RequestCtx":
        """Create RequestCtx from container."""
        return cls(container)
    
    @classmethod
    def set_current(cls, ctx: "RequestCtx") -> None:
        """Set current request context."""
        _request_container_var.set(ctx._container)
    
    @classmethod
    def get_current(cls) -> Optional["RequestCtx"]:
        """Get current request context."""
        container = _request_container_var.get()
        if container:
            return cls(container)
        return None


def get_request_container() -> Optional[Container]:
    """
    Get current request container from context.
    
    Returns:
        Container or None if no request context
    """
    return _request_container_var.get()


def set_request_container(container: Container) -> None:
    """
    Set request container in context.
    
    Args:
        container: Container to set
    """
    _request_container_var.set(container)


def clear_request_container() -> None:
    """Clear request container from context."""
    _request_container_var.set(None)
