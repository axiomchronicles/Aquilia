"""
Handler wrapper for dependency injection into controller methods.

This module provides the mechanism to inject dependencies from DI containers
into controller handler methods based on their type annotations.
"""

import inspect
from typing import Any, Callable, Dict, get_type_hints, Optional
from functools import wraps


class DIInjectionError(Exception):
    """Raised when dependency injection fails."""
    pass


class HandlerWrapper:
    """
    Wraps controller handlers to inject dependencies from DI container.
    
    Inspects handler signature and resolves dependencies by:
    1. Checking parameter type annotations
    2. Resolving from request.state.di_container
    3. Falling back to app_container if needed
    4. Passing special parameters like 'request' directly
    """
    
    def __init__(self, handler: Callable, controller_class: type):
        """
        Initialize wrapper.
        
        Args:
            handler: Controller method to wrap
            controller_class: Controller class for context
        """
        self.handler = handler
        self.controller_class = controller_class
        self.signature = inspect.signature(handler)
        self.type_hints = get_type_hints(handler)
        self._cached_params = None
    
    def _analyze_parameters(self) -> Dict[str, Any]:
        """
        Analyze handler parameters for DI resolution.
        
        Returns:
            Dict mapping param names to resolution strategy
        """
        if self._cached_params is not None:
            return self._cached_params
        
        params = {}
        for name, param in self.signature.parameters.items():
            if name == "self":
                continue
            
            # Get type annotation
            param_type = self.type_hints.get(name, None)
            
            # Determine resolution strategy
            if name == "request":
                params[name] = {"strategy": "request", "type": None}
            elif param_type and param_type.__name__ != "inspect._empty":
                # Has type annotation - resolve from DI
                params[name] = {
                    "strategy": "di",
                    "type": param_type,
                    "type_name": param_type.__name__,
                }
            else:
                # No type hint - pass None or skip
                params[name] = {"strategy": "skip", "type": None}
        
        self._cached_params = params
        return params
    
    async def __call__(self, request: Any, **kwargs) -> Any:
        """
        Execute handler with dependency injection.
        
        Args:
            request: Request object with .state.di_container
            **kwargs: Additional parameters (e.g., path params)
            
        Returns:
            Handler result (Response)
        """
        # Analyze parameters
        param_info = self._analyze_parameters()
        
        # Get DI containers
        di_container = getattr(request.state, "di_container", None)
        app_container = getattr(request.state, "app_container", None)
        
        # Build arguments
        handler_kwargs = {}
        
        for param_name, info in param_info.items():
            strategy = info["strategy"]
            
            if strategy == "request":
                # Pass request directly
                handler_kwargs[param_name] = request
            
            elif strategy == "di":
                # Resolve from DI container
                param_type = info["type"]
                type_name = info["type_name"]
                
                try:
                    # Try request container first
                    if di_container:
                        try:
                            service = di_container.resolve(type_name)
                            handler_kwargs[param_name] = service
                            continue
                        except Exception:
                            pass
                    
                    # Fallback to app container
                    if app_container:
                        service = app_container.resolve(type_name)
                        handler_kwargs[param_name] = service
                    else:
                        raise DIInjectionError(
                            f"No DI container available to resolve '{type_name}' "
                            f"for parameter '{param_name}'"
                        )
                
                except Exception as e:
                    raise DIInjectionError(
                        f"Failed to resolve dependency '{type_name}' "
                        f"for parameter '{param_name}' in "
                        f"{self.controller_class.__name__}.{self.handler.__name__}: {e}"
                    ) from e
            
            elif strategy == "skip":
                # Skip parameters without type hints
                continue
        
        # Merge with path/query params
        handler_kwargs.update(kwargs)
        
        # Execute handler
        if inspect.iscoroutinefunction(self.handler):
            return await self.handler(**handler_kwargs)
        else:
            return self.handler(**handler_kwargs)


def wrap_handler(handler: Callable, controller_class: type) -> HandlerWrapper:
    """
    Wrap a controller handler for dependency injection.
    
    Args:
        handler: Controller method
        controller_class: Controller class
        
    Returns:
        Wrapped handler with DI support
    """
    return HandlerWrapper(handler, controller_class)


def inject_dependencies(handler: Callable) -> Callable:
    """
    Decorator to enable dependency injection for a handler.
    
    Usage:
        class MyController:
            @inject_dependencies
            async def endpoint(self, request, MyService: MyService):
                return await MyService.do_something()
    
    Args:
        handler: Controller method
        
    Returns:
        Wrapped handler
    """
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        # Find request in args
        request = None
        for arg in args:
            if hasattr(arg, "state"):
                request = arg
                break
        
        if request is None:
            # No request found, call handler directly
            if inspect.iscoroutinefunction(handler):
                return await handler(*args, **kwargs)
            return handler(*args, **kwargs)
        
        # Create wrapper and inject
        controller_class = handler.__self__.__class__ if hasattr(handler, "__self__") else None
        wrapper_obj = HandlerWrapper(handler, controller_class)
        return await wrapper_obj(request, **kwargs)
    
    return wrapper
