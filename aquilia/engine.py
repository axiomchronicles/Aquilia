"""
Engine - Request context for dependency injection.
"""

from .di import Container


class RequestCtx:
    """Request context with DI container and state."""
    
    def __init__(self, container: Container, request_id: str):
        self.container = container
        self.request_id = request_id
        self.state = {}
    
    async def resolve(self, name: str, optional: bool = False):
        """Resolve dependency from container."""
        return await self.container.resolve_async(name, optional=optional)
    
    async def dispose(self):
        """Clean up request-scoped resources."""
        await self.container.shutdown()
