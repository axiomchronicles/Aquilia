"""
Controller Engine - Executes controller methods with full integration.

Integrates with:
- DI system for controller instantiation
- Auth system for identity binding
- Session system for session state
- Middleware for pipeline execution
- Faults for error handling
"""

from typing import Any, Dict, Optional, List
import inspect
import logging

from .base import Controller, RequestCtx
from .factory import ControllerFactory, InstantiationMode
from .compiler import CompiledRoute
from ..request import Request
from ..response import Response
from ..di import Container
from ..middleware import Handler, Middleware


class ControllerEngine:
    """
    Executes controller methods with complete integration.
    
    Responsibilities:
    - Instantiate controllers via DI
    - Build RequestCtx with auth, session, state
    - Execute pipelines (class-level + method-level)
    - Bind path/query/body parameters
    - Handle errors via faults system
    - Lifecycle management
    """
    
    def __init__(
        self,
        factory: ControllerFactory,
        enable_lifecycle: bool = True,
    ):
        """
        Initialize engine.
        
        Args:
            factory: Controller factory for instantiation
            enable_lifecycle: Whether to call lifecycle hooks
        """
        self.factory = factory
        self.enable_lifecycle = enable_lifecycle
        self.logger = logging.getLogger("aquilia.controller.engine")
        self._lifecycle_initialized: set[type] = set()
    
    async def execute(
        self,
        route: CompiledRoute,
        request: Request,
        path_params: Dict[str, Any],
        container: Container,
    ) -> Response:
        """
        Execute a controller route.
        
        Args:
            route: Compiled route to execute
            request: HTTP request
            path_params: Extracted path parameters
            container: Request-scoped DI container
            
        Returns:
            HTTP response
        """
        controller_class = route.controller_class
        route_metadata = route.route_metadata
        
        # Initialize controller lifecycle hooks if needed
        if self.enable_lifecycle and controller_class not in self._lifecycle_initialized:
            await self._init_controller_lifecycle(controller_class, container)
            self._lifecycle_initialized.add(controller_class)
        
        # Instantiate controller
        controller = await self.factory.create(
            controller_class,
            mode=InstantiationMode.PER_REQUEST,
            request_container=container,
        )
        
        # Build RequestCtx
        ctx = await self._build_request_context(request, container)
        
        # Execute class-level pipeline
        if route.controller_metadata.pipeline:
            for pipeline_node in route.controller_metadata.pipeline:
                result = await self._execute_pipeline_node(
                    pipeline_node,
                    request,
                    ctx,
                    controller,
                )
                if isinstance(result, Response):
                    # Pipeline returned early response (e.g., auth failed)
                    return result
        
        # Execute method-level pipeline
        if route_metadata.pipeline:
            for pipeline_node in route_metadata.pipeline:
                result = await self._execute_pipeline_node(
                    pipeline_node,
                    request,
                    ctx,
                    controller,
                )
                if isinstance(result, Response):
                    return result
        
        # Bind parameters
        kwargs = await self._bind_parameters(
            route_metadata,
            request,
            ctx,
            path_params,
            container,
        )
        
        # Get handler method
        handler_method = getattr(controller, route_metadata.handler_name)
        
        # Execute handler
        try:
            # Call on_request hook if exists
            if hasattr(controller, "on_request"):
                await self._safe_call(controller.on_request, ctx)
            
            # Execute handler
            result = await self._safe_call(handler_method, ctx, **kwargs)
            
            # Convert result to Response if needed
            response = self._to_response(result)
            
            # Call on_response hook if exists
            if hasattr(controller, "on_response"):
                await self._safe_call(controller.on_response, ctx, response)
            
            return response
        
        except Exception as e:
            self.logger.error(
                f"Error executing {controller_class.__name__}.{route_metadata.handler_name}: {e}",
                exc_info=True,
            )
            # Let faults system handle it
            raise
    
    async def _init_controller_lifecycle(
        self,
        controller_class: type,
        container: Container,
    ):
        """Initialize controller lifecycle hooks (startup)."""
        # Create temporary instance for lifecycle
        temp_instance = await self.factory.create(
            controller_class,
            mode=InstantiationMode.SINGLETON,
            request_container=container,
        )
        
        if hasattr(temp_instance, "on_startup"):
            try:
                # Build a minimal context for startup (no actual request yet)
                from ..request import Request as RequestClass
                dummy_request = RequestClass(
                    scope={"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": []},
                    receive=lambda: None,
                )
                ctx = RequestCtx(request=dummy_request, identity=None, session=None, container=container, state={})
                await self._safe_call(temp_instance.on_startup, ctx)
                self.logger.info(f"Executed on_startup for {controller_class.__name__}")
            except Exception as e:
                self.logger.error(
                    f"Error in on_startup for {controller_class.__name__}: {e}",
                    exc_info=True,
                )
    
    async def shutdown_controller(self, controller_class: type, container: Container):
        """Execute controller shutdown hooks."""
        if controller_class not in self._lifecycle_initialized:
            return
        
        temp_instance = await self.factory.create(
            controller_class,
            mode=InstantiationMode.SINGLETON,
            request_container=container,
        )
        
        if hasattr(temp_instance, "on_shutdown"):
            try:
                await self._safe_call(temp_instance.on_shutdown)
                self.logger.info(f"Executed on_shutdown for {controller_class.__name__}")
            except Exception as e:
                self.logger.error(
                    f"Error in on_shutdown for {controller_class.__name__}: {e}",
                    exc_info=True,
                )
        
        self._lifecycle_initialized.discard(controller_class)
    
    async def _build_request_context(
        self,
        request: Request,
        container: Container,
    ) -> RequestCtx:
        """
        Build RequestCtx with auth, session, and state.
        
        Looks for:
        - Identity from request.state["identity"] or DI container
        - Session from request.state["session"] or DI container
        """
        # Try to get identity - prefer request state (set by middleware)
        identity = request.state.get("identity")
        if identity is None:
            try:
                identity = await container.resolve_async("identity", optional=True)
            except:
                pass
        
        # Try to get session - prefer request state (set by session middleware)
        session = request.state.get("session")
        if session is None:
            try:
                session = await container.resolve_async("session", optional=True)
            except:
                pass
        
        return RequestCtx(
            request=request,
            identity=identity,
            session=session,
            container=container,
            state=dict(request.state),  # Copy state
        )
    
    async def _execute_pipeline_node(
        self,
        pipeline_node: Any,
        request: Request,
        ctx: RequestCtx,
        controller: Controller,
    ) -> Optional[Response]:
        """
        Execute a pipeline node (middleware/guard).
        
        Returns Response if node returns early, None to continue.
        """
        # Pipeline nodes can be:
        # - Callables
        # - Middleware instances
        # - Guard functions
        
        if callable(pipeline_node):
            sig = inspect.signature(pipeline_node)
            
            # Build arguments based on signature
            kwargs = {}
            for param_name in sig.parameters:
                if param_name == "request" or param_name == "req":
                    kwargs[param_name] = request
                elif param_name == "ctx" or param_name == "context":
                    kwargs[param_name] = ctx
                elif param_name == "controller":
                    kwargs[param_name] = controller
            
            result = await self._safe_call(pipeline_node, **kwargs)
            
            # If result is False or Response, stop pipeline
            if result is False:
                return Response.json({"error": "Pipeline guard failed"}, status=403)
            elif isinstance(result, Response):
                return result
        
        return None
    
    async def _bind_parameters(
        self,
        route_metadata,
        request: Request,
        ctx: RequestCtx,
        path_params: Dict[str, Any],
        container: Container,
    ) -> Dict[str, Any]:
        """
        Bind parameters from request to handler arguments.
        
        Sources:
        - Path parameters
        - Query parameters
        - Request body (JSON/form)
        - DI container
        - Special: ctx, request
        """
        kwargs = {}
        
        for param in route_metadata.parameters:
            param_name = param.name
            
            # Skip ctx (already handled)
            if param_name == "ctx":
                continue
            
            # Path parameters
            if param.source == "path":
                if param_name in path_params:
                    kwargs[param_name] = path_params[param_name]
                elif not param.required and param.default is not inspect.Parameter.empty:
                    kwargs[param_name] = param.default
            
            # Query parameters
            elif param.source == "query":
                value = request.query_param(param_name)
                if value is not None:
                    # Cast to expected type
                    kwargs[param_name] = self._cast_value(value, param.type)
                elif not param.required and param.default is not inspect.Parameter.empty:
                    kwargs[param_name] = param.default
            
            # Body (for POST/PUT/PATCH)
            elif param.source == "body":
                if request.method in ("POST", "PUT", "PATCH"):
                    try:
                        body = await request.json()
                        if param_name in body:
                            kwargs[param_name] = body[param_name]
                        elif not param.required and param.default is not inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                    except:
                        if not param.required and param.default is not inspect.Parameter.empty:
                            kwargs[param_name] = param.default
            
            # DI injection
            elif param.source == "di":
                try:
                    value = await container.resolve_async(param_name, optional=not param.required)
                    if value is not None:
                        kwargs[param_name] = value
                    elif not param.required and param.default is not inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                except:
                    if not param.required and param.default is not inspect.Parameter.empty:
                        kwargs[param_name] = param.default
        
        return kwargs
    
    def _cast_value(self, value: str, annotation: Any) -> Any:
        """Cast string value to target type."""
        if annotation is int or annotation == "int":
            return int(value)
        elif annotation is float or annotation == "float":
            return float(value)
        elif annotation is bool or annotation == "bool":
            return value.lower() in ("true", "1", "yes")
        else:
            return value
    
    async def _safe_call(self, func: Any, *args, **kwargs) -> Any:
        """Safely call function (sync or async)."""
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _to_response(self, result: Any) -> Response:
        """Convert handler result to Response."""
        if isinstance(result, Response):
            return result
        elif isinstance(result, dict):
            return Response.json(result)
        elif isinstance(result, (list, tuple)):
            return Response.json(result)
        elif isinstance(result, str):
            return Response(result, content_type="text/plain")
        elif result is None:
            return Response("", status=204)
        else:
            # Try to serialize
            return Response.json({"result": str(result)})
