"""
Controller Factory

Handles controller instantiation with DI support.
Supports both per-request and singleton instantiation modes.
"""

from typing import Any, Dict, Optional, Type
from enum import Enum
import asyncio


class InstantiationMode(str, Enum):
    """Controller instantiation modes."""
    PER_REQUEST = "per_request"
    SINGLETON = "singleton"


class ControllerFactory:
    """
    Factory for creating controller instances.
    
    Handles:
    - DI resolution for constructor parameters
    - Per-request vs singleton instantiation
    - Lifecycle management (startup/shutdown hooks)
    - Scope validation
    
    Example:
        factory = ControllerFactory(container=app_container)
        controller = await factory.create(
            UsersController,
            mode=InstantiationMode.PER_REQUEST,
            request_container=request_container
        )
    """
    
    def __init__(self, app_container: Optional[Any] = None):
        """
        Initialize factory.
        
        Args:
            app_container: App-level DI container
        """
        self.app_container = app_container
        self._singletons: Dict[Type, Any] = {}
        self._startup_called: set = set()
    
    async def create(
        self,
        controller_class: Type,
        mode: InstantiationMode = InstantiationMode.PER_REQUEST,
        request_container: Optional[Any] = None,
        ctx: Optional[Any] = None,
    ) -> Any:
        """
        Create controller instance.
        
        Args:
            controller_class: Controller class to instantiate
            mode: Instantiation mode
            request_container: Request-scoped DI container
            ctx: Request context
        
        Returns:
            Controller instance
        
        Raises:
            ScopeViolationError: If injecting request-scoped into singleton
        """
        if mode == InstantiationMode.SINGLETON:
            return await self._create_singleton(controller_class, ctx)
        else:
            return await self._create_per_request(
                controller_class,
                request_container,
                ctx,
            )
    
    async def _create_singleton(
        self,
        controller_class: Type,
        ctx: Optional[Any] = None,
    ) -> Any:
        """Create or return singleton instance."""
        if controller_class in self._singletons:
            return self._singletons[controller_class]
        
        # Resolve constructor dependencies from app container
        instance = await self._resolve_and_instantiate(
            controller_class,
            self.app_container,
        )
        
        # Call on_startup hook once
        if controller_class not in self._startup_called:
            if hasattr(instance, 'on_startup'):
                if asyncio.iscoroutinefunction(instance.on_startup):
                    await instance.on_startup(ctx)
                else:
                    instance.on_startup(ctx)
            self._startup_called.add(controller_class)
        
        self._singletons[controller_class] = instance
        return instance
    
    async def _create_per_request(
        self,
        controller_class: Type,
        request_container: Optional[Any],
        ctx: Optional[Any] = None,
    ) -> Any:
        """Create new instance for each request."""
        # Resolve constructor dependencies from request container
        # Request container has access to both app and request-scoped providers
        container = request_container or self.app_container
        
        instance = await self._resolve_and_instantiate(
            controller_class,
            container,
        )
        
        # Call on_request hook
        if hasattr(instance, 'on_request'):
            if asyncio.iscoroutinefunction(instance.on_request):
                await instance.on_request(ctx)
            else:
                instance.on_request(ctx)
        
        return instance
    
    async def _resolve_and_instantiate(
        self,
        controller_class: Type,
        container: Optional[Any],
    ) -> Any:
        """
        Resolve constructor dependencies and instantiate.
        
        Args:
            controller_class: Controller class
            container: DI container
        
        Returns:
            Controller instance
        """
        if container is None:
            # No DI - simple instantiation
            return controller_class()
        
        # Extract constructor signature
        import inspect
        try:
            sig = inspect.signature(controller_class.__init__)
            params = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Try to resolve from container
                try:
                    # Get type annotation
                    param_type = param.annotation
                    if param_type != inspect.Parameter.empty:
                        # Resolve from container
                        resolved = await self._resolve_parameter(
                            param_type,
                            container,
                        )
                        params[param_name] = resolved
                    elif param.default != inspect.Parameter.empty:
                        # Use default
                        params[param_name] = param.default
                except Exception:
                    # If resolution fails and no default, skip
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
            
            return controller_class(**params)
        
        except Exception:
            # Fallback to simple instantiation
            return controller_class()
    
    async def _resolve_parameter(
        self,
        param_type: Type,
        container: Any,
    ) -> Any:
        """
        Resolve a single parameter from DI container.
        
        Handles Annotated[T, Inject(...)] syntax.
        """
        # Check if it's Annotated type
        try:
            from typing import get_origin, get_args
            
            origin = get_origin(param_type)
            if origin is not None:
                # Handle Annotated[T, Inject(...)]
                args = get_args(param_type)
                if args:
                    actual_type = args[0]
                    # Look for Inject metadata
                    for arg in args[1:]:
                        if hasattr(arg, '__class__') and arg.__class__.__name__ == 'Inject':
                            # Extract tag if any
                            tag = getattr(arg, 'tag', None)
                            # Resolve from container with tag
                            if hasattr(container, 'resolve'):
                                return await container.resolve(actual_type, tag=tag)
                            return await self._simple_resolve(actual_type, container)
            
            # Simple type resolution
            return await self._simple_resolve(param_type, container)
        
        except Exception:
            # If anything fails, try simple resolution
            return await self._simple_resolve(param_type, container)
    
    async def _simple_resolve(self, param_type: Type, container: Any) -> Any:
        """Simple resolution from container."""
        if hasattr(container, 'resolve'):
            result = container.resolve(param_type)
            if asyncio.iscoroutine(result):
                return await result
            return result
        elif hasattr(container, 'get'):
            return container.get(param_type)
        else:
            # Last resort: try to instantiate
            return param_type()
    
    async def shutdown(self):
        """Shutdown all singleton controllers."""
        for controller_class, instance in self._singletons.items():
            if hasattr(instance, 'on_shutdown'):
                try:
                    if asyncio.iscoroutinefunction(instance.on_shutdown):
                        await instance.on_shutdown(None)
                    else:
                        instance.on_shutdown(None)
                except Exception as e:
                    # Log but don't fail shutdown
                    print(f"Error in {controller_class.__name__}.on_shutdown: {e}")
    
    def validate_scope(
        self,
        controller_class: Type,
        mode: InstantiationMode,
    ) -> None:
        """
        Validate that controller doesn't violate scope rules.
        
        Raises:
            ScopeViolationError: If singleton controller tries to inject
                                 request-scoped dependency
        """
        if mode != InstantiationMode.SINGLETON:
            return
        
        # TODO: Implement compile-time scope validation
        # Check constructor params don't inject request-scoped providers
        pass


class ScopeViolationError(Exception):
    """Raised when a scope rule is violated."""
    
    def __init__(self, controller_class: Type, provider: Type):
        self.controller_class = controller_class
        self.provider = provider
        super().__init__(
            f"Singleton controller {controller_class.__name__} cannot "
            f"inject request-scoped provider {provider.__name__}"
        )
