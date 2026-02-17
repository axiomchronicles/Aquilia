"""
Controller Factory

Handles controller instantiation with DI support.
Supports both per-request and singleton instantiation modes.
"""

from typing import Any, Dict, Optional, Type, get_origin, get_args
from enum import Enum
import asyncio
import inspect
import logging


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
    """

    # Class-level caches for constructor analysis
    _ctor_info_cache: Dict[Type, Any] = {}  # class -> (sig, type_hints, param_specs)
    
    def __init__(self, app_container: Optional[Any] = None):
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
                if inspect.iscoroutinefunction(instance.on_startup):
                    await instance.on_startup(ctx)
                else:
                    instance.on_startup(ctx)
            self._startup_called.add(controller_class)
        
        self._singletons[controller_class] = instance
        return instance
    
    # Cache for controllers that don't have on_request hook
    _no_on_request: set = set()

    async def _create_per_request(
        self,
        controller_class: Type,
        request_container: Optional[Any],
        ctx: Optional[Any] = None,
    ) -> Any:
        """Create new instance for each request."""
        container = request_container or self.app_container
        
        instance = await self._resolve_and_instantiate(
            controller_class,
            container,
        )
        
        # Fast path: skip on_request for controllers that don't override it from Controller base
        if controller_class not in ControllerFactory._no_on_request:
            # Check if on_request is actually overridden (not just inherited from Controller base)
            has_custom_on_request = (
                'on_request' in controller_class.__dict__
                or any('on_request' in B.__dict__ for B in controller_class.__mro__[1:]
                       if B.__name__ != 'Controller' and B is not object)
            )
            if has_custom_on_request:
                if inspect.iscoroutinefunction(instance.on_request):
                    await instance.on_request(ctx)
                else:
                    instance.on_request(ctx)
            else:
                ControllerFactory._no_on_request.add(controller_class)
        
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
        
        # Get cached constructor info (inspect.signature + get_type_hints are expensive)
        ctor_info = ControllerFactory._ctor_info_cache.get(controller_class)
        if ctor_info is None:
            ctor_info = self._analyze_constructor(controller_class)
            ControllerFactory._ctor_info_cache[controller_class] = ctor_info
        
        if not ctor_info:
            # No injectable params — simple instantiation
            return controller_class()

        try:
            params = {}
            _EMPTY = inspect.Parameter.empty
            
            for param_name, param_type, has_default, default_val in ctor_info:
                try:
                    if param_type is not _EMPTY:
                        resolved = await self._resolve_parameter(
                            param_type,
                            container,
                        )
                        params[param_name] = resolved
                    elif has_default:
                        params[param_name] = default_val
                except Exception:
                    if has_default:
                        params[param_name] = default_val
                    else:
                        raise
            
            return controller_class(**params)
        
        except Exception:
            return controller_class()
    
    @staticmethod
    def _analyze_constructor(controller_class: Type):
        """Analyze constructor once and return a list of (name, type, has_default, default) tuples."""
        try:
            sig = inspect.signature(controller_class.__init__)
            
            from typing import get_type_hints
            try:
                type_hints = get_type_hints(controller_class.__init__, include_extras=True)
            except Exception:
                type_hints = {}
            
            _EMPTY = inspect.Parameter.empty
            result = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_type = type_hints.get(param_name, param.annotation)
                
                # Intelligent inference: default is a class → inject it
                if param_type is _EMPTY and param.default is not _EMPTY:
                    if isinstance(param.default, type):
                        param_type = param.default
                
                has_default = param.default is not _EMPTY
                default_val = param.default if has_default else None
                result.append((param_name, param_type, has_default, default_val))
            
            return result
        except Exception:
            return None
    
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
                    if inspect.iscoroutinefunction(instance.on_shutdown):
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
