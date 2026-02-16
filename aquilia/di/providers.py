"""
Provider implementations for different instantiation strategies.
"""

from typing import Any, Callable, Coroutine, Type, Optional, Dict, List, TypeVar
import inspect
import asyncio
from dataclasses import dataclass

from .core import Provider, ProviderMeta, ResolveCtx
from .errors import DIError


T = TypeVar("T")


class ClassProvider:
    """
    Provider that instantiates a class by resolving constructor dependencies.
    
    Supports async __init__ via async_init() convention.
    """
    
    __slots__ = ("_meta", "_cls", "_dependencies", "_has_async_init")
    
    def __init__(
        self,
        cls: Type[T],
        scope: str = "app",
        tags: tuple[str, ...] = (),
        allow_lazy: bool = False,
    ):
        self._cls = cls
        self._dependencies = self._extract_dependencies(cls)
        self._has_async_init = hasattr(cls, "async_init")
        
        # Build metadata
        module = cls.__module__
        qualname = cls.__qualname__
        token = f"{module}.{qualname}"
        
        # Try to get source file and line
        try:
            source_file = inspect.getsourcefile(cls)
            _, line = inspect.getsourcelines(cls)
        except (TypeError, OSError):
            source_file = module
            line = None
        
        self._meta = ProviderMeta(
            name=cls.__name__,
            token=token,
            scope=scope,
            tags=tags,
            module=module,
            qualname=qualname,
            line=line,
            allow_lazy=allow_lazy,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Instantiate class by resolving dependencies."""
        # Resolve dependencies
        resolved_deps = {}
        for dep_name, dep_info in self._dependencies.items():
            dep_token = dep_info["token"]
            dep_tag = dep_info.get("tag")
            
            resolved = await ctx.container.resolve_async(
                dep_token,
                tag=dep_tag,
                optional=dep_info.get("optional", False),
            )
            resolved_deps[dep_name] = resolved
        
        # Instantiate
        instance = self._cls(**resolved_deps)
        
        # Call async_init if present
        if self._has_async_init:
            await instance.async_init()
        
        return instance
    
    async def shutdown(self) -> None:
        """No-op for class provider (instances handle their own shutdown)."""
        pass
    
    def _extract_dependencies(self, cls: Type) -> Dict[str, Dict[str, Any]]:
        """
        Extract dependencies from __init__ signature.
        
        Returns:
            Dict mapping parameter names to dependency info
        """
        deps = {}
        
        # Check if using default object.__init__
        if cls.__init__ is object.__init__:
            return deps
            
        try:
            sig = inspect.signature(cls.__init__)
        except ValueError:
            # Handle classes like builtins that might not support signature inspection
            return deps
        
        try:
            type_hints = inspect.get_annotations(cls.__init__, eval_str=True)
        except Exception:
            # Fallback for older python or failure
            try:
                from typing import get_type_hints
                type_hints = get_type_hints(cls.__init__)
            except Exception:
                type_hints = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            # Skip varargs and kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            
            # Extract type hint
            # Prefer resolved hint, fallback to raw annotation
            annotation = type_hints.get(param_name, param.annotation)
            
            if annotation == inspect.Parameter.empty:
                # If default value exists, it's optional and we skip dependency injection
                if param.default != inspect.Parameter.empty:
                    continue
                    
                raise DIError(
                    f"Missing type annotation for parameter '{param_name}' "
                    f"in {cls.__qualname__}.__init__"
                )
            
            # Check for Inject metadata
            dep_info = self._parse_annotation(annotation)
            dep_info["optional"] = param.default != inspect.Parameter.empty
            
            deps[param_name] = dep_info
        
        return deps
    
    def _parse_annotation(self, annotation: Any) -> Dict[str, Any]:
        """Parse type annotation for Inject metadata."""
        from typing import get_origin, get_args
        
        # Check for Annotated[Type, Inject(...)]
        origin = get_origin(annotation)
        if origin is not None:
            from typing import Annotated
            if origin is Annotated:
                args = get_args(annotation)
                base_type = args[0]
                metadata = args[1:] if len(args) > 1 else ()
                
                # Look for Inject marker
                result = {"token": base_type}
                for meta in metadata:
                    if hasattr(meta, "_inject_token") and meta._inject_token is not None:
                        result["token"] = meta._inject_token
                    if hasattr(meta, "_inject_tag"):
                        result["tag"] = meta._inject_tag
                    if hasattr(meta, "_inject_optional"):
                        result["optional"] = meta._inject_optional
                return result
        
        # Plain type annotation
        return {"token": annotation}


class FactoryProvider:
    """
    Provider that calls a factory function to produce instances.
    
    Supports both sync and async factories.
    """
    
    __slots__ = ("_meta", "_factory", "_is_async", "_dependencies")
    
    def __init__(
        self,
        factory: Callable,
        scope: str = "app",
        tags: tuple[str, ...] = (),
        name: Optional[str] = None,
    ):
        self._factory = factory
        self._is_async = inspect.iscoroutinefunction(factory)
        self._dependencies = self._extract_dependencies(factory)
        
        # Build metadata
        module = factory.__module__
        qualname = factory.__qualname__
        
        # Check for explicit name in metadata if name arg is None
        if name is None:
            if hasattr(factory, "__di_name__") and factory.__di_name__ != factory.__name__:
                name = factory.__di_name__
        
        token = name or f"{module}.{qualname}"
        
        try:
            source_file = inspect.getsourcefile(factory)
            _, line = inspect.getsourcelines(factory)
        except (TypeError, OSError):
            source_file = module
            line = None
        
        self._meta = ProviderMeta(
            name=name or factory.__name__,
            token=token,
            scope=scope,
            tags=tags,
            module=module,
            qualname=qualname,
            line=line,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Call factory with resolved dependencies."""
        # Resolve dependencies
        resolved_deps = {}
        for dep_name, dep_info in self._dependencies.items():
            resolved = await ctx.container.resolve_async(
                dep_info["token"],
                tag=dep_info.get("tag"),
                optional=dep_info.get("optional", False),
            )
            resolved_deps[dep_name] = resolved
        
        # Call factory
        if self._is_async:
            return await self._factory(**resolved_deps)
        else:
            return self._factory(**resolved_deps)
    
    async def shutdown(self) -> None:
        """No-op for factory provider."""
        pass
    
    def _extract_dependencies(self, factory: Callable) -> Dict[str, Dict[str, Any]]:
        """Extract dependencies from factory signature."""
        deps = {}
        sig = inspect.signature(factory)
        
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                # Factory parameters must be annotated
                continue
            
            dep_info = {"token": param.annotation}
            dep_info["optional"] = param.default != inspect.Parameter.empty
            deps[param_name] = dep_info
        
        return deps


class ValueProvider:
    """Provider that returns a pre-bound constant value."""
    
    __slots__ = ("_meta", "_value")
    
    def __init__(
        self,
        value: Any,
        token: Type | str,
        name: Optional[str] = None,
        scope: str = "singleton",
        tags: tuple[str, ...] = (),
    ):
        token_str = token if isinstance(token, str) else f"{token.__module__}.{token.__qualname__}"
        self._value = value
        self._meta = ProviderMeta(
            name=name or "value",
            token=token_str,
            scope=scope,
            tags=tags,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Return pre-bound value."""
        return self._value
    
    async def shutdown(self) -> None:
        """No-op for value provider."""
        pass


class PoolProvider:
    """
    Provider that manages a pool of instances.
    
    Uses asyncio.Queue for FIFO/LIFO pooling.
    """
    
    __slots__ = (
        "_meta",
        "_factory",
        "_pool",
        "_max_size",
        "_strategy",
        "_created",
    )
    
    def __init__(
        self,
        factory: Callable[[], Coroutine[Any, Any, T]],
        max_size: int,
        token: Type | str,
        name: Optional[str] = None,
        strategy: str = "FIFO",  # FIFO or LIFO
        tags: tuple[str, ...] = (),
    ):
        self._factory = factory
        self._max_size = max_size
        self._strategy = strategy
        self._pool: Optional[asyncio.Queue] = None
        self._created = 0
        
        token_str = token if isinstance(token, str) else f"{token.__module__}.{token.__qualname__}"
        
        self._meta = ProviderMeta(
            name=name or "pool",
            token=token_str,
            scope="pooled",
            tags=tags,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Acquire instance from pool (creates pool on first call)."""
        if self._pool is None:
            if self._strategy == "LIFO":
                self._pool = asyncio.LifoQueue(maxsize=self._max_size)
            else:
                self._pool = asyncio.Queue(maxsize=self._max_size)
        
        # Try to get from pool (non-blocking)
        try:
            instance = self._pool.get_nowait()
            return instance
        except asyncio.QueueEmpty:
            pass
        
        # Pool empty - create new instance if under limit
        if self._created < self._max_size:
            instance = await self._factory()
            self._created += 1
            return instance
        
        # Wait for available instance
        return await self._pool.get()
    
    async def release(self, instance: Any) -> None:
        """Release instance back to pool."""
        if self._pool is not None:
            try:
                self._pool.put_nowait(instance)
            except asyncio.QueueFull:
                # Pool full - destroy instance
                if hasattr(instance, "close"):
                    await instance.close()
    
    async def shutdown(self) -> None:
        """Shutdown pool and clean up instances."""
        if self._pool is None:
            return
        
        while not self._pool.empty():
            try:
                instance = self._pool.get_nowait()
                if hasattr(instance, "close"):
                    await instance.close()
            except asyncio.QueueEmpty:
                break


class AliasProvider:
    """Provider that aliases one token to another."""
    
    __slots__ = ("_meta", "_target_token", "_target_tag")
    
    def __init__(
        self,
        token: Type | str,
        target_token: Type | str,
        target_tag: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self._target_token = target_token
        self._target_tag = target_tag
        
        token_str = token if isinstance(token, str) else f"{token.__module__}.{token.__qualname__}"
        
        self._meta = ProviderMeta(
            name=name or "alias",
            token=token_str,
            scope="singleton",  # Aliases don't create instances
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Resolve target token."""
        return await ctx.container.resolve_async(
            self._target_token,
            tag=self._target_tag,
        )
    
    async def shutdown(self) -> None:
        """No-op for alias provider."""
        pass


class LazyProxyProvider:
    """
    Provider that creates a lazy proxy for cycle resolution.
    
    Only use when explicitly allowed in manifest.
    """
    
    __slots__ = ("_meta", "_target_token", "_target_tag", "_proxy_class")
    
    def __init__(
        self,
        token: Type | str,
        target_token: Type | str,
        target_tag: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self._target_token = target_token
        self._target_tag = target_tag
        self._proxy_class = self._create_proxy_class()
        
        token_str = token if isinstance(token, str) else f"{token.__module__}.{token.__qualname__}"
        
        self._meta = ProviderMeta(
            name=name or "lazy_proxy",
            token=token_str,
            scope="singleton",
            allow_lazy=True,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Create lazy proxy."""
        proxy = self._proxy_class(
            ctx.container,
            self._target_token,
            self._target_tag,
        )
        return proxy
    
    async def shutdown(self) -> None:
        """No-op for lazy proxy."""
        pass
    
    def _create_proxy_class(self) -> Type:
        """Create proxy class that defers resolution."""
        class LazyProxy:
            __slots__ = ("_container", "_token", "_tag", "_instance")
            
            def __init__(self, container, token, tag):
                self._container = container
                self._token = token
                self._tag = tag
                self._instance = None
            
            def _resolve(self):
                """Resolve actual instance on first access."""
                if self._instance is None:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop is not None and loop.is_running():
                        raise RuntimeError(
                            f"Cannot lazily resolve '{self._token}' synchronously "
                            f"inside a running async event loop. Use "
                            f"'await container.resolve_async(...)' or resolve "
                            f"eagerly during startup."
                        )
                    self._instance = asyncio.run(
                        self._container.resolve_async(self._token, tag=self._tag)
                    )
                return self._instance
            
            def __getattr__(self, name):
                instance = self._resolve()
                return getattr(instance, name)
            
            def __call__(self, *args, **kwargs):
                instance = self._resolve()
                return instance(*args, **kwargs)
        
        return LazyProxy


class ScopedProvider:
    """
    Wrapper provider that enforces scope semantics.
    
    Used for request/ephemeral scopes.
    """
    
    __slots__ = ("_meta", "_inner_provider", "_scope")
    
    def __init__(self, inner: Provider, scope: str):
        self._inner_provider = inner
        self._scope = scope
        
        # Copy metadata but override scope
        inner_meta = inner.meta
        self._meta = ProviderMeta(
            name=inner_meta.name,
            token=inner_meta.token,
            scope=scope,
            tags=inner_meta.tags,
            module=inner_meta.module,
            qualname=inner_meta.qualname,
            line=inner_meta.line,
            version=inner_meta.version,
            allow_lazy=inner_meta.allow_lazy,
        )
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Delegate to inner provider."""
        return await self._inner_provider.instantiate(ctx)
    
    async def shutdown(self) -> None:
        """Delegate to inner provider."""
        await self._inner_provider.shutdown()


class SerializerProvider:
    """
    DI Provider that creates Serializer instances with request context.

    When resolved, the provider:
    1. Parses the request body (JSON or form data)
    2. Creates the serializer with ``data=body`` and a context dict
       containing ``request``, ``container``, and ``identity``
    3. Returns the **serializer instance** (not yet validated)

    The handler can then call ``serializer.is_valid()`` and ``serializer.save()``.

    This mirrors FastAPI's ``Depends()`` pattern but for Aquilia serializers.

    Usage::

        from aquilia.di import Container
        from aquilia.di.providers import SerializerProvider

        container.register(
            SerializerProvider(UserSerializer, scope="request")
        )

        # In handler:
        async def create_user(self, ctx, serializer: UserSerializer):
            serializer.is_valid(raise_fault=True)
            user = await serializer.save()
            return Response.json(UserSerializer(instance=user).data, status=201)
    """

    __slots__ = ("_meta", "_serializer_cls", "_auto_validate")

    def __init__(
        self,
        serializer_cls: type,
        *,
        scope: str = "request",
        auto_validate: bool = False,
        tags: tuple[str, ...] = (),
    ):
        self._serializer_cls = serializer_cls
        self._auto_validate = auto_validate

        module = serializer_cls.__module__
        qualname = serializer_cls.__qualname__
        token = f"{module}.{qualname}"

        try:
            source_file = inspect.getsourcefile(serializer_cls)
            _, line = inspect.getsourcelines(serializer_cls)
        except (TypeError, OSError):
            source_file = module
            line = None

        self._meta = ProviderMeta(
            name=serializer_cls.__name__,
            token=token,
            scope=scope,
            tags=tags,
            module=module,
            qualname=qualname,
            line=line,
        )

    @property
    def meta(self) -> ProviderMeta:
        return self._meta

    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """
        Create serializer instance with request data from DI context.

        The provider looks for a ``Request`` instance in the container
        to parse the body.  If no request is available (e.g. testing),
        the serializer is created without data.
        """
        container = ctx.container

        # Try to resolve request from container
        request = None
        data = None
        identity = None

        try:
            request = await container.resolve_async("aquilia.request.Request", optional=True)
        except Exception:
            pass

        if request is not None:
            try:
                data = await request.json()
            except Exception:
                try:
                    data = await request.form()
                except Exception:
                    data = {}

            # Get identity
            state = getattr(request, "state", None)
            if state:
                identity = state.get("identity") if isinstance(state, dict) else getattr(state, "identity", None)

        # Build context
        from aquilia.serializers.fields import empty
        ser_context = {"container": container}
        if request is not None:
            ser_context["request"] = request
        if identity is not None:
            ser_context["identity"] = identity

        serializer = self._serializer_cls(
            data=data if data is not None else empty,
            context=ser_context,
        )

        if self._auto_validate and data is not None:
            serializer.is_valid(raise_fault=True)

        return serializer

    async def shutdown(self) -> None:
        """No-op for serializer provider."""
        pass
