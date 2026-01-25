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
            
        # Validate scope safety before instantiation
        self.validate_scope(controller_class, InstantiationMode.SINGLETON)
        
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
            
            # Resolve type hints (handles string forward references)
            from typing import get_type_hints
            try:
                type_hints = get_type_hints(controller_class.__init__, include_extras=True)
            except Exception:
                # Fallback if get_type_hints fails (e.g. missing imports)
                type_hints = {}
                
            params = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Try to resolve from container
                try:
                    # Get type annotation from hints if available, else raw annotation
                    param_type = type_hints.get(param_name, param.annotation)
                    
                    # INTELLIGENT INFERENCE:
                    # If no type hint is provided, but the default value is a class (type),
                    # assume the user wants an instance of that class injected.
                    if param_type == inspect.Parameter.empty and param.default != inspect.Parameter.empty:
                        if isinstance(param.default, type):
                            param_type = param.default
                    
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
                except Exception as e:
                    # If resolution fails and no default, fail hard
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
                    else:
                        raise RuntimeError(
                            f"Failed to resolve required parameter '{param_name}' "
                            f"for {controller_class.__name__}: {e}"
                        ) from e
            
            return controller_class(**params)
        
        except Exception as e:
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
        try:
            from typing import get_origin, get_args
            
            origin = get_origin(param_type)
            if origin is not None:
                # Handle Annotated[T, Inject(...)]
                args = get_args(param_type)
                if args:
                    actual_type = args[0]
                    # Look for Inject metadata using duck typing
                    for arg in args[1:]:
                        
                        if hasattr(arg, '_inject_tag') or hasattr(arg, '_inject_token'):
                            # print(f"DEBUG: Found Inject-like metadata: {arg}")
                            # Extract tag if any
                            tag = getattr(arg, 'tag', None)
                            # Extract token if any
                            token = getattr(arg, 'token', None)
                            
                            resolve_key = token if token else actual_type
                            
                            # Resolve from container with tag
                            if hasattr(container, 'resolve_async'):
                                return await container.resolve_async(resolve_key, tag=tag)
                            elif hasattr(container, 'resolve'):
                                result = container.resolve(resolve_key, tag=tag)
                                if asyncio.iscoroutine(result):
                                    return await result
                                return result
                            return await self._simple_resolve(resolve_key, container)
            
            # Simple type resolution
            return await self._simple_resolve(param_type, container)
        
        except Exception:
            # If anything fails, try simple resolution
            return await self._simple_resolve(param_type, container)
    
    async def _simple_resolve(self, param_type: Type, container: Any) -> Any:
        """Simple resolution from container."""
        if hasattr(container, 'resolve_async'):
            # Prefer async resolution
            return await container.resolve_async(param_type)
        elif hasattr(container, 'resolve'):
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
        
        # Validate scopes of all dependencies
        import inspect
        try:
            sig = inspect.signature(controller_class.__init__)
            type_hints = self._get_type_hints(controller_class)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Get param type
                param_type = type_hints.get(param_name, param.annotation)
                
                # If inferred from default value
                if param_type == inspect.Parameter.empty and isinstance(param.default, type):
                    param_type = param.default
                
                if param_type == inspect.Parameter.empty:
                    continue
                    
                # Check provider scope
                provider = self.app_container._lookup_provider(
                    self.app_container._token_to_key(param_type), None
                )
                
                if provider:
                    # Singleton/App controllers CANNOT depend on Request/Ephemeral scopes
                    # because the dependency would be cached forever (stale/leak)
                    if provider.meta.scope in ("request", "ephemeral", "transient"):
                        raise ScopeViolationError(controller_class, param_type)
                        
        except ScopeViolationError:
            raise
        except Exception:
            # If validation fails due to inspection issues, log warning but allow proceed
            # (runtime might fail later, but we shouldn't block startup on static analysis bugs)
            pass

    def _get_type_hints(self, cls):
        try:
            from typing import get_type_hints
            return get_type_hints(cls.__init__)
        except Exception:
            return {}


class ScopeViolationError(Exception):
    """Raised when a scope rule is violated."""
    
    def __init__(self, controller_class: Type, provider: Type):
        self.controller_class = controller_class
        self.provider = provider
        super().__init__(
            f"Singleton controller {controller_class.__name__} cannot "
            f"inject request-scoped provider {provider.__name__}"
        )
