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
        fault_engine: Optional[Any] = None,
    ):
        """
        Initialize engine.
        
        Args:
            factory: Controller factory for instantiation
            enable_lifecycle: Whether to call lifecycle hooks
            fault_engine: FaultEngine for structured error handling
        """
        self.factory = factory
        self.enable_lifecycle = enable_lifecycle
        self.fault_engine = fault_engine
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
        
        # Fast path: monkeypatched handler (e.g. OpenAPI docs routes).
        # These bypass the full controller lifecycle entirely.
        if hasattr(route, "handler") and callable(route.handler):
            ctx = await self._build_request_context(request, container)
            result = await route.handler(request, ctx)
            return self._to_response(result)
        
        # Initialize controller lifecycle hooks if needed
        # Only for Singleton controllers or if we want to support startup hooks generally?
        # Docs say on_startup is singleton only.
        is_singleton = getattr(controller_class, "instantiation_mode", "per_request") == "singleton"
        
        if self.enable_lifecycle and is_singleton and controller_class not in self._lifecycle_initialized:
            await self._init_controller_lifecycle(controller_class, container)
            self._lifecycle_initialized.add(controller_class)
        
        # Build RequestCtx before controller instantiation so it's available for on_request hook
        ctx = await self._build_request_context(request, container)
        
        # Instantiate controller
        controller = await self.factory.create(
            controller_class,
            mode=InstantiationMode.PER_REQUEST,
            request_container=container,
            ctx=ctx,
        )
        
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
            
            # Auto-serialize response if response_serializer is set
            result = self._apply_response_serializer(result, route_metadata, ctx)
            
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
            # Process through fault engine if available
            if self.fault_engine:
                try:
                    app_name = getattr(route, 'app_name', None)
                    await self.fault_engine.process(
                        e,
                        app=app_name,
                        route=route.full_path,
                        request_id=getattr(request.state, 'get', lambda k, d=None: d)('request_id'),
                    )
                except Exception:
                    pass  # Fault engine processing is best-effort
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
        - **Serializer subclasses**: Auto-parsed from request body (FastAPI-style)

        When a parameter is typed as a ``Serializer`` subclass, the engine
        will:
        1. Parse the request body (JSON or form)
        2. Create the serializer with ``data=body, context={request, container}``
        3. Call ``is_valid(raise_fault=True)``
        4. Inject ``serializer.validated_data`` as the parameter value

        If the parameter name is ``serializer`` or ends with ``_serializer``,
        the full serializer instance is injected instead of just the
        validated data.  This gives the handler access to ``.save()``,
        ``.errors``, etc.

        Similarly, if a ``request_serializer`` is declared on the route
        decorator, it takes precedence and is used for body parsing.
        """
        kwargs = {}
        
        # Check for request_serializer from decorator metadata
        decorator_request_serializer = getattr(route_metadata, 'request_serializer', None)
        if decorator_request_serializer is None:
            raw_meta = getattr(route_metadata, '_raw_metadata', None)
            if raw_meta and isinstance(raw_meta, dict):
                decorator_request_serializer = raw_meta.get('request_serializer')
        
        # Track if body has been consumed by a serializer
        _body_consumed = False
        _body_cache = None
        
        async def _get_body():
            nonlocal _body_cache
            if _body_cache is not None:
                return _body_cache
            try:
                _body_cache = await request.json()
            except Exception:
                try:
                    _body_cache = await request.form()
                except Exception:
                    _body_cache = {}
            return _body_cache
        
        for param in route_metadata.parameters:
            param_name = param.name
            
            # Skip ctx (already handled)
            if param_name == "ctx":
                continue
            
            # ── FastAPI-style Serializer injection ───────────────────────
            # If the parameter type is a Serializer subclass, auto-parse
            # the request body through it.
            param_is_serializer = self._is_serializer_class(param.type)
            
            # Also check for decorator-level request_serializer
            use_serializer = None
            if param_is_serializer:
                use_serializer = param.type
            elif (
                decorator_request_serializer
                and self._is_serializer_class(decorator_request_serializer)
                and param.source == "body"
                and not _body_consumed
            ):
                use_serializer = decorator_request_serializer
            
            if use_serializer is not None and not _body_consumed:
                body = await _get_body()
                _body_consumed = True
                
                # Build context with request + container for DI defaults
                ser_context = {"request": request}
                if container:
                    ser_context["container"] = container
                if ctx.identity:
                    ser_context["identity"] = ctx.identity
                
                serializer = use_serializer(
                    data=body,
                    context=ser_context,
                )
                serializer.is_valid(raise_fault=True)
                
                # If param name suggests they want the serializer instance,
                # inject the full serializer (access to .save(), .errors, etc.)
                # Otherwise inject just the validated_data dict.
                inject_instance = (
                    param_name == "serializer"
                    or param_name.endswith("_serializer")
                    or param_name.endswith("_ser")
                )
                
                if inject_instance:
                    kwargs[param_name] = serializer
                else:
                    kwargs[param_name] = serializer.validated_data
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
                    # For Session and Identity, we use optional=True so we can raise our own Faults
                    from aquilia.sessions import Session as SessionClass
                    is_session_param = (
                        param.type is SessionClass or 
                        param_name == "session" or
                        (hasattr(param.type, "__name__") and param.type.__name__ == "Session")
                    )
                    
                    is_identity_param = (
                        param_name == "identity" or 
                        (hasattr(param.type, "__name__") and param.type.__name__ == "Identity")
                    )

                    is_optional = not param.required or is_session_param or is_identity_param
                    
                    # Resolve by type if available, otherwise by name
                    resolve_token = param.type if param.type is not inspect.Parameter.empty else param_name
                    value = await container.resolve_async(resolve_token, optional=is_optional)
                    
                    if is_session_param and value is None:
                        # Try to resolve session proactively
                        try:
                            from aquilia.sessions import SessionEngine
                            engine = await container.resolve_async(SessionEngine)
                            value = await engine.resolve(request)
                            # Update context and request for downstream handlers/decorators
                            ctx.session = value
                            request.state['session'] = value
                        except Exception:
                            pass
                    
                    # ENFORCEMENT: If this is a Session, and it's None, but requested as required
                    # then raise SessionRequiredFault.
                    if value is None and param.required:
                        if is_session_param:
                            from aquilia.sessions.decorators import SessionRequiredFault
                            raise SessionRequiredFault()
                        elif is_identity_param:
                            from aquilia.sessions.decorators import AuthenticationRequiredFault
                            raise AuthenticationRequiredFault()
                            
                    if value is not None:
                        kwargs[param_name] = value
                    elif not param.required and param.default is not inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                except Exception as e:
                    # Reraise session/auth faults
                    from aquilia.sessions.decorators import SessionRequiredFault, AuthenticationRequiredFault
                    if isinstance(e, (SessionRequiredFault, AuthenticationRequiredFault)):
                        raise
                        
                    if not param.required and param.default is not inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        # Re-raise original error if it's not handled
                        raise
        
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
    
    def _is_serializer_class(self, annotation: Any) -> bool:
        """Check if annotation is a Serializer subclass (FastAPI-style detection)."""
        try:
            from aquilia.serializers.base import Serializer
            return (
                isinstance(annotation, type)
                and issubclass(annotation, Serializer)
                and annotation is not Serializer
            )
        except ImportError:
            return False
    
    def _apply_response_serializer(
        self,
        result: Any,
        route_metadata: Any,
        ctx: RequestCtx,
    ) -> Any:
        """
        Auto-serialize handler return value via response_serializer.

        If the route has a ``response_serializer`` in its metadata (set via
        ``@POST("/", response_serializer=MySerializer)``), the return value
        is passed through the serializer's ``to_representation()`` before
        being converted to a ``Response``.

        Supports:
        - Single instance → ``Serializer(instance=result).data``
        - List/tuple → ``Serializer.many(instance=result).data``
        - Already a Response → passthrough (no serialization)
        - Already a dict → passthrough (assume pre-serialized)
        """
        # Get response serializer from route metadata
        response_serializer = getattr(route_metadata, 'response_serializer', None)
        if response_serializer is None:
            # Check raw metadata dict (from decorator)
            raw_meta = getattr(route_metadata, '_raw_metadata', None)
            if raw_meta and isinstance(raw_meta, dict):
                response_serializer = raw_meta.get('response_serializer')
        
        if response_serializer is None or not self._is_serializer_class(response_serializer):
            return result
        
        # Don't re-serialize Response objects
        if isinstance(result, Response):
            return result
        
        # Build context for the serializer
        ser_context = {"request": ctx.request}
        if ctx.container:
            ser_context["container"] = ctx.container
        
        try:
            if isinstance(result, (list, tuple)):
                serializer = response_serializer.many(instance=result, context=ser_context)
            else:
                serializer = response_serializer(instance=result, context=ser_context)
            return serializer.data
        except Exception as e:
            self.logger.warning(
                f"Response serialization failed: {e}. Returning raw result."
            )
            return result
    
    async def _safe_call(self, func: Any, *args, **kwargs) -> Any:
        """Safely call function (sync or async)."""
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
    
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
