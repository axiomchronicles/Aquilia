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
    
    # Class-level caches shared across instances
    _signature_cache: Dict[Any, inspect.Signature] = {}
    _pipeline_param_cache: Dict[int, set] = {}  # id(callable) -> set of param names
    _has_lifecycle_hooks: Dict[type, tuple] = {}  # class -> (has_on_request, has_on_response)
    _simple_route_cache: Dict[int, bool] = {}  # id(route) -> is_simple
    
    def __init__(
        self,
        factory: ControllerFactory,
        enable_lifecycle: bool = True,
        fault_engine: Optional[Any] = None,
    ):
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

        Performance (v2):
        - Fast path for monkeypatched handlers (no lifecycle, no DI).
        - Skip lifecycle init check for per-request controllers.
        - Build RequestCtx inline without extra method call for simple cases.
        - Cache inspect.signature results via _bind_parameters.
        """
        controller_class = route.controller_class
        route_metadata = route.route_metadata

        # Fast path: monkeypatched handler (OpenAPI docs, etc.)
        if hasattr(route, "handler") and callable(route.handler):
            ctx = RequestCtx(
                request=request,
                identity=request.state.get("identity"),
                session=request.state.get("session"),
                container=container,
            )
            result = await route.handler(request, ctx)
            return self._to_response(result)

        # Build RequestCtx
        ctx = RequestCtx(
            request=request,
            identity=request.state.get("identity"),
            session=request.state.get("session"),
            container=container,
            state=request.state,
        )

        # Singleton lifecycle init (once per controller class)
        is_singleton = getattr(controller_class, "instantiation_mode", "per_request") == "singleton"
        if self.enable_lifecycle and is_singleton and controller_class not in self._lifecycle_initialized:
            await self._init_controller_lifecycle(controller_class, container)
            self._lifecycle_initialized.add(controller_class)

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
                    pipeline_node, request, ctx, controller,
                )
                if isinstance(result, Response):
                    return result

        # Execute method-level pipeline
        if route_metadata.pipeline:
            for pipeline_node in route_metadata.pipeline:
                result = await self._execute_pipeline_node(
                    pipeline_node, request, ctx, controller,
                )
                if isinstance(result, Response):
                    return result

        # Get handler method
        handler_method = getattr(controller, route_metadata.handler_name)

        # ── Fast path for simple handlers ──
        # Handlers with no pipeline, no serializer, and only ctx/path params
        # can skip the full _bind_parameters machinery.
        route_id = id(route)
        is_simple = ControllerEngine._simple_route_cache.get(route_id)
        if is_simple is None:
            params = route_metadata.parameters
            _rm = getattr(route_metadata, '_raw_metadata', {}) or {}
            has_serializer = (
                getattr(route_metadata, 'request_serializer', None) or _rm.get('request_serializer')
                or getattr(route_metadata, 'response_serializer', None) or _rm.get('response_serializer')
            )
            has_blueprint = (
                getattr(route_metadata, 'request_blueprint', None) or _rm.get('request_blueprint')
                or getattr(route_metadata, 'response_blueprint', None) or _rm.get('response_blueprint')
            )
            has_filters_or_pagination = (
                getattr(route_metadata, 'filterset_class', None) or _rm.get('filterset_class')
                or getattr(route_metadata, 'filterset_fields', None) or _rm.get('filterset_fields')
                or getattr(route_metadata, 'search_fields', None) or _rm.get('search_fields')
                or getattr(route_metadata, 'ordering_fields', None) or _rm.get('ordering_fields')
                or getattr(route_metadata, 'pagination_class', None) or _rm.get('pagination_class')
                or getattr(route_metadata, 'renderer_classes', None) or _rm.get('renderer_classes')
            )
            is_simple = (
                not route.controller_metadata.pipeline
                and not route_metadata.pipeline
                and not has_serializer
                and not has_blueprint
                and not has_filters_or_pagination
                and (not params or all(
                    p.name == 'ctx' or p.source == 'path' for p in params
                ))
            )
            ControllerEngine._simple_route_cache[route_id] = is_simple

        if is_simple:
            # Direct call — skip _bind_parameters, lifecycle hooks, serializer
            try:
                if path_params:
                    result = await self._safe_call(handler_method, ctx, **path_params)
                else:
                    result = await self._safe_call(handler_method, ctx)
                return self._to_response(result)
            except Exception as e:
                self.logger.error(
                    f"Error executing {controller_class.__name__}.{route_metadata.handler_name}: {e}",
                    exc_info=True,
                )
                if self.fault_engine:
                    try:
                        app_name = getattr(route, 'app_name', None)
                        rid = request.state.get('request_id') if isinstance(request.state, dict) else None
                        await self.fault_engine.process(
                            e, app=app_name, route=route.full_path, request_id=rid,
                        )
                    except Exception:
                        pass
                raise

        # Bind parameters
        kwargs = await self._bind_parameters(
            route_metadata, request, ctx, path_params, container,
        )

        # Execute handler
        try:
            # Check lifecycle hooks (cached per class)
            # We check if the method is actually OVERRIDDEN from Controller base,
            # since Controller defines on_request/on_response as no-ops.
            hooks = ControllerEngine._has_lifecycle_hooks.get(controller_class)
            if hooks is None:
                has_on_request = (
                    'on_request' in controller_class.__dict__
                    or any('on_request' in B.__dict__ for B in controller_class.__mro__[1:]
                           if B is not Controller and B is not object)
                )
                has_on_response = (
                    'on_response' in controller_class.__dict__
                    or any('on_response' in B.__dict__ for B in controller_class.__mro__[1:]
                           if B is not Controller and B is not object)
                )
                hooks = (has_on_request, has_on_response)
                ControllerEngine._has_lifecycle_hooks[controller_class] = hooks

            has_on_request, has_on_response = hooks

            if has_on_request:
                await self._safe_call(controller.on_request, ctx)

            result = await self._safe_call(handler_method, ctx, **kwargs)
            result = await self._apply_filters_and_pagination(result, route_metadata, request)
            result = self._apply_response_serializer(result, route_metadata, ctx)
            result = self._apply_response_blueprint(result, route_metadata, ctx)
            response = self._apply_content_negotiation(result, route_metadata, request)
            if response is None:
                response = self._to_response(result)

            if has_on_response:
                await self._safe_call(controller.on_response, ctx, response)

            return response

        except Exception as e:
            self.logger.error(
                f"Error executing {controller_class.__name__}.{route_metadata.handler_name}: {e}",
                exc_info=True,
            )
            if self.fault_engine:
                try:
                    app_name = getattr(route, 'app_name', None)
                    rid = request.state.get('request_id') if isinstance(request.state, dict) else None
                    await self.fault_engine.process(
                        e, app=app_name, route=route.full_path, request_id=rid,
                    )
                except Exception:
                    pass
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
        """Build RequestCtx with auth, session, and state."""
        identity = request.state.get("identity")
        session = request.state.get("session")

        # Only do DI fallback if middleware didn't set identity/session
        if identity is None:
            try:
                identity = await container.resolve_async("identity", optional=True)
            except Exception:
                pass

        if session is None:
            try:
                session = await container.resolve_async("session", optional=True)
            except Exception:
                pass

        return RequestCtx(
            request=request,
            identity=identity,
            session=session,
            container=container,
            state=request.state,
        )
    
    async def _execute_pipeline_node(
        self,
        pipeline_node: Any,
        request: Request,
        ctx: RequestCtx,
        controller: Controller,
    ) -> Optional[Response]:
        """Execute a pipeline node (middleware/guard) with cached signatures."""
        if not callable(pipeline_node):
            return None

        # Cache parameter names by id of callable
        node_id = id(pipeline_node)
        param_names = self._pipeline_param_cache.get(node_id)
        if param_names is None:
            sig = inspect.signature(pipeline_node)
            param_names = set(sig.parameters.keys())
            self._pipeline_param_cache[node_id] = param_names

        kwargs = {}
        if "request" in param_names or "req" in param_names:
            key = "request" if "request" in param_names else "req"
            kwargs[key] = request
        if "ctx" in param_names or "context" in param_names:
            key = "ctx" if "ctx" in param_names else "context"
            kwargs[key] = ctx
        if "controller" in param_names:
            kwargs["controller"] = controller

        result = await self._safe_call(pipeline_node, **kwargs)

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
        - **Blueprint subclasses**: Auto-parsed, cast+sealed from request body

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

        When a parameter is typed as a ``Blueprint`` subclass, the engine
        will:
        1. Parse the request body (JSON or form)
        2. Create the Blueprint with ``data=body, context={request, container}``
        3. Call ``is_sealed(raise_fault=True)``
        4. Inject the Blueprint instance or ``.validated_data``

        If the parameter name is ``blueprint`` or ends with ``_blueprint``
        or ``_bp``, the full Blueprint instance is injected. Otherwise,
        ``blueprint.validated_data`` is injected.

        Similarly, if a ``request_serializer`` or ``request_blueprint``
        is declared on the route decorator, it takes precedence and is
        used for body parsing.
        """
        kwargs = {}
        
        # Check for request_serializer from decorator metadata
        decorator_request_serializer = getattr(route_metadata, 'request_serializer', None)
        if decorator_request_serializer is None:
            raw_meta = getattr(route_metadata, '_raw_metadata', None)
            if raw_meta and isinstance(raw_meta, dict):
                decorator_request_serializer = raw_meta.get('request_serializer')

        # Check for request_blueprint from decorator metadata
        decorator_request_blueprint = getattr(route_metadata, 'request_blueprint', None)
        if decorator_request_blueprint is None:
            raw_meta = getattr(route_metadata, '_raw_metadata', None)
            if raw_meta and isinstance(raw_meta, dict):
                decorator_request_blueprint = raw_meta.get('request_blueprint')
        
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

            # ── Blueprint injection ──────────────────────────────────────
            # If the parameter type is a Blueprint subclass, auto-parse
            # the request body through it.
            param_is_blueprint = self._is_blueprint_class(param.type)
            
            # Also check for decorator-level request_serializer
            use_serializer = None
            use_blueprint = None

            if param_is_serializer:
                use_serializer = param.type
            elif param_is_blueprint:
                use_blueprint = param.type
            elif (
                decorator_request_blueprint
                and self._is_blueprint_class(decorator_request_blueprint)
                and param.source == 'body'
                and not _body_consumed
            ):
                use_blueprint = decorator_request_blueprint
            elif (
                decorator_request_serializer
                and self._is_serializer_class(decorator_request_serializer)
                and param.source == 'body'
                and not _body_consumed
            ):
                use_serializer = decorator_request_serializer

            # ── Blueprint body binding ───────────────────────────────────
            if use_blueprint is not None and not _body_consumed:
                body = await _get_body()
                _body_consumed = True

                # Build context with request + container
                bp_context = {"request": request}
                if container:
                    bp_context["container"] = container
                if ctx.identity:
                    bp_context["identity"] = ctx.identity

                # Handle ProjectedRef (Blueprint["projection"])
                projection = None
                bp_cls = use_blueprint
                try:
                    from aquilia.blueprints.lenses import _ProjectedRef
                    if isinstance(use_blueprint, _ProjectedRef):
                        projection = use_blueprint.projection
                        bp_cls = use_blueprint.blueprint_cls
                except ImportError:
                    pass

                # Determine if PATCH → partial
                is_partial = request.method == "PATCH"

                bp_instance = bp_cls(
                    data=body,
                    partial=is_partial,
                    projection=projection,
                    context=bp_context,
                )
                bp_instance.is_sealed(raise_fault=True)

                # If param name suggests they want the Blueprint instance,
                # inject the full Blueprint. Otherwise inject validated_data.
                inject_instance = (
                    param_name == "blueprint"
                    or param_name.endswith("_blueprint")
                    or param_name.endswith("_bp")
                )

                if inject_instance:
                    kwargs[param_name] = bp_instance
                else:
                    kwargs[param_name] = bp_instance.validated_data
                continue
            
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
                    is_session_param = (
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
    
    _serializer_base_class = None  # Cached Serializer class
    _blueprint_base_class = None   # Cached Blueprint class

    def _is_serializer_class(self, annotation: Any) -> bool:
        """Check if annotation is a Serializer subclass (FastAPI-style detection)."""
        if ControllerEngine._serializer_base_class is None:
            try:
                from aquilia.serializers.base import Serializer
                ControllerEngine._serializer_base_class = Serializer
            except ImportError:
                ControllerEngine._serializer_base_class = type(None)  # sentinel
                return False
        
        base = ControllerEngine._serializer_base_class
        if base is type(None):
            return False
        return (
            isinstance(annotation, type)
            and issubclass(annotation, base)
            and annotation is not base
        )

    def _is_blueprint_class(self, annotation: Any) -> bool:
        """Check if annotation is a Blueprint subclass or ProjectedRef."""
        if ControllerEngine._blueprint_base_class is None:
            try:
                from aquilia.blueprints.core import Blueprint
                ControllerEngine._blueprint_base_class = Blueprint
            except ImportError:
                ControllerEngine._blueprint_base_class = type(None)  # sentinel
                return False

        base = ControllerEngine._blueprint_base_class
        if base is type(None):
            return False

        # Check for ProjectedRef (Blueprint["projection"])
        try:
            from aquilia.blueprints.lenses import _ProjectedRef
            if isinstance(annotation, _ProjectedRef):
                return True
        except ImportError:
            pass

        return (
            isinstance(annotation, type)
            and issubclass(annotation, base)
            and annotation is not base
        )

    def _apply_response_serializer(
        self,
        result: Any,
        route_metadata: Any,
        ctx: RequestCtx,
    ) -> Any:
        """Auto-serialize handler return value via response_serializer."""
        # Fast path: check direct attribute first (avoids dict lookups for common case)
        response_serializer = getattr(route_metadata, 'response_serializer', None)
        if response_serializer is None:
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

    def _apply_response_blueprint(
        self,
        result: Any,
        route_metadata: Any,
        ctx: RequestCtx,
    ) -> Any:
        """Auto-mold handler return value via response_blueprint."""
        # Fast path: check direct attribute first
        response_blueprint = getattr(route_metadata, 'response_blueprint', None)
        if response_blueprint is None:
            raw_meta = getattr(route_metadata, '_raw_metadata', None)
            if raw_meta and isinstance(raw_meta, dict):
                response_blueprint = raw_meta.get('response_blueprint')

        if response_blueprint is None:
            return result

        # Don't re-mold Response objects
        if isinstance(result, Response):
            return result

        try:
            from aquilia.blueprints.integration import render_blueprint_response

            many = isinstance(result, (list, tuple))
            return render_blueprint_response(
                response_blueprint,
                data=result,
                many=many,
            )
        except ImportError:
            self.logger.warning(
                "Blueprint system not available. Returning raw result."
            )
            return result
        except Exception as e:
            self.logger.warning(
                f"Response Blueprint molding failed: {e}. Returning raw result."
            )
            return result
    
    async def _apply_filters_and_pagination(
        self,
        result: Any,
        route_metadata: Any,
        request: Request,
    ) -> Any:
        """
        Apply FilterSet / SearchFilter / OrderingFilter / Pagination
        to the handler's return value.

        Only activates when the route has filtering/pagination metadata
        AND the result is a list (or QuerySet-like object).
        """
        # Resolve metadata attrs (direct or _raw_metadata fallback)
        def _meta(key):
            v = getattr(route_metadata, key, None)
            if v is None:
                raw = getattr(route_metadata, '_raw_metadata', None)
                if raw and isinstance(raw, dict):
                    v = raw.get(key)
            return v

        filterset_class = _meta('filterset_class')
        filterset_fields = _meta('filterset_fields')
        search_fields = _meta('search_fields')
        ordering_fields = _meta('ordering_fields')
        pagination_class = _meta('pagination_class')

        has_filters = any([
            filterset_class, filterset_fields, search_fields, ordering_fields,
        ])

        if not has_filters and not pagination_class:
            return result

        # Don't filter/paginate Response objects
        if isinstance(result, Response):
            return result

        try:
            from .filters import filter_data as _filter_data
            from .pagination import BasePagination
        except ImportError:
            return result

        # Check if result is a list-like (in-memory) or a queryset
        is_queryset = hasattr(result, 'filter') and hasattr(result, 'all')
        is_list = isinstance(result, (list, tuple))

        if not is_list and not is_queryset:
            return result

        # ── Apply filters ────────────────────────────────────────────
        if has_filters:
            if is_queryset:
                try:
                    from .filters import filter_queryset as _filter_qs
                    result = await _filter_qs(
                        result,
                        request,
                        filterset_class=filterset_class,
                        filterset_fields=filterset_fields,
                        search_fields=search_fields,
                        ordering_fields=ordering_fields,
                    )
                except Exception as e:
                    self.logger.warning(f"QuerySet filtering failed: {e}")
            elif is_list:
                result = _filter_data(
                    list(result),
                    request,
                    filterset_class=filterset_class,
                    filterset_fields=filterset_fields,
                    search_fields=search_fields,
                    ordering_fields=ordering_fields,
                )

        # ── Apply pagination ─────────────────────────────────────────
        if pagination_class:
            try:
                paginator = (
                    pagination_class()
                    if isinstance(pagination_class, type)
                    else pagination_class
                )
                if hasattr(result, 'all') and hasattr(paginator, 'paginate_queryset'):
                    result = await paginator.paginate_queryset(result, request)
                else:
                    # Materialise queryset if needed
                    if hasattr(result, 'all'):
                        items = await result.all()
                        data = [
                            i.to_dict() if hasattr(i, 'to_dict') else i
                            for i in items
                        ]
                    else:
                        data = list(result)
                    result = paginator.paginate_list(data, request)
            except Exception as e:
                self.logger.warning(f"Pagination failed: {e}")

        return result

    def _apply_content_negotiation(
        self,
        result: Any,
        route_metadata: Any,
        request: Request,
    ) -> Optional[Response]:
        """
        Select a renderer via content negotiation and build a Response.

        Returns ``None`` if no renderer_classes are configured (default
        path uses ``_to_response``), or a fully-rendered ``Response``.
        """
        # Already a Response — skip
        if isinstance(result, Response):
            return result

        renderer_classes = getattr(route_metadata, 'renderer_classes', None)
        if renderer_classes is None:
            raw = getattr(route_metadata, '_raw_metadata', None)
            if raw and isinstance(raw, dict):
                renderer_classes = raw.get('renderer_classes')

        if not renderer_classes:
            return None  # caller falls through to _to_response

        try:
            from .renderers import ContentNegotiator, BaseRenderer
        except ImportError:
            return None

        # Instantiate renderer classes if they are types
        instances = []
        for rc in renderer_classes:
            if isinstance(rc, type) and issubclass(rc, BaseRenderer):
                instances.append(rc())
            elif isinstance(rc, BaseRenderer):
                instances.append(rc)

        if not instances:
            return None

        negotiator = ContentNegotiator(renderers=instances)
        renderer, media_type = negotiator.select_renderer(request)

        body = renderer.render(
            result,
            request=request,
            response_status=200,
        )

        content_type = media_type
        if renderer.charset:
            content_type = f"{media_type}; charset={renderer.charset}"

        return Response(
            content=body,
            status=200,
            media_type=content_type,
        )

    # Cache for coroutine function checks
    _is_coro_cache: Dict[int, bool] = {}  # id(func) -> is_coroutine
    
    async def _safe_call(self, func: Any, *args, **kwargs) -> Any:
        """Safely call function (sync or async)."""
        fid = id(func)
        is_coro = ControllerEngine._is_coro_cache.get(fid)
        if is_coro is None:
            is_coro = inspect.iscoroutinefunction(func)
            ControllerEngine._is_coro_cache[fid] = is_coro
        
        if is_coro:
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
