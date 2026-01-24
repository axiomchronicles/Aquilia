"""
AquilaFaults - Fault handlers.

Defines fault handler abstraction and resolution logic.

Handlers are registered at scopes:
- global
- app
- controller  
- route

Resolution order: Route → Controller → App → Global
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from .core import FaultContext, FaultResult


class FaultHandler(ABC):
    """
    Abstract base class for fault handlers.
    
    Fault handlers process FaultContext and return FaultResult:
    - Resolved: Fault was handled, return response
    - Transformed: Fault was transformed into another fault
    - Escalate: Fault should propagate to next handler
    
    Handlers are registered at different scopes and invoked in order:
    Route → Controller → App → Global
    
    Example:
        ```python
        class RetryHandler(FaultHandler):
            async def handle(self, ctx: FaultContext) -> FaultResult:
                if ctx.fault.retryable and ctx.metadata.get("retry_count", 0) < 3:
                    # Retry logic
                    return Transformed(ctx.fault)
                return Escalate()
        ```
    """
    
    @abstractmethod
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """
        Handle fault context.
        
        Args:
            ctx: Fault context to handle
        
        Returns:
            FaultResult (Resolved, Transformed, or Escalate)
        """
        pass
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """
        Check if this handler can handle the fault.
        
        Override to implement pre-filtering logic.
        
        Args:
            ctx: Fault context
        
        Returns:
            True if handler can process this fault
        """
        return True


class CompositeHandler(FaultHandler):
    """
    Composite handler that chains multiple handlers.
    
    Tries handlers in order until one resolves or transforms the fault.
    """
    
    def __init__(self, handlers: list[FaultHandler]):
        """
        Initialize composite handler.
        
        Args:
            handlers: List of handlers to try in order
        """
        self.handlers = handlers
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """
        Try each handler in order.
        
        Args:
            ctx: Fault context
        
        Returns:
            First non-Escalate result, or Escalate if all decline
        """
        from .core import Escalate
        
        for handler in self.handlers:
            if not handler.can_handle(ctx):
                continue
            
            result = await handler.handle(ctx)
            
            # If handler resolved or transformed, stop
            if not isinstance(result, Escalate):
                return result
        
        # All handlers declined
        return Escalate()


class ScopedHandlerRegistry:
    """
    Registry of fault handlers at different scopes.
    
    Maintains handlers for:
    - Global scope (all faults)
    - App scope (faults in specific app)
    - Controller scope (faults in specific controller)
    - Route scope (faults in specific route)
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._global: list[FaultHandler] = []
        self._app: dict[str, list[FaultHandler]] = {}
        self._controller: dict[str, list[FaultHandler]] = {}
        self._route: dict[str, list[FaultHandler]] = {}
    
    def register_global(self, handler: FaultHandler):
        """Register global handler."""
        self._global.append(handler)
    
    def register_app(self, app: str, handler: FaultHandler):
        """Register app-scoped handler."""
        if app not in self._app:
            self._app[app] = []
        self._app[app].append(handler)
    
    def register_controller(self, controller: str, handler: FaultHandler):
        """Register controller-scoped handler."""
        if controller not in self._controller:
            self._controller[controller] = []
        self._controller[controller].append(handler)
    
    def register_route(self, route: str, handler: FaultHandler):
        """Register route-scoped handler."""
        if route not in self._route:
            self._route[route] = []
        self._route[route].append(handler)
    
    def get_handlers(
        self,
        *,
        app: Optional[str] = None,
        controller: Optional[str] = None,
        route: Optional[str] = None,
    ) -> list[FaultHandler]:
        """
        Get applicable handlers for context.
        
        Returns handlers in resolution order:
        Route → Controller → App → Global
        
        Args:
            app: App name
            controller: Controller name
            route: Route pattern
        
        Returns:
            List of handlers in resolution order
        """
        handlers = []
        
        # Route-specific handlers (highest priority)
        if route and route in self._route:
            handlers.extend(self._route[route])
        
        # Controller-specific handlers
        if controller and controller in self._controller:
            handlers.extend(self._controller[controller])
        
        # App-specific handlers
        if app and app in self._app:
            handlers.extend(self._app[app])
        
        # Global handlers (lowest priority)
        handlers.extend(self._global)
        
        return handlers
