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
        sig = inspect.signature(cls.__init__)
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            # Extract type hint
            if param.annotation == inspect.Parameter.empty:
                raise DIError(
                    f"Missing type annotation for parameter '{param_name}' "
                    f"in {cls.__qualname__}.__init__"
                )
            
            # Check for Inject metadata
            dep_info = self._parse_annotation(param.annotation)
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
                for meta in metadata:
                    if hasattr(meta, "_inject_tag"):
                        return {
                            "token": base_type,
                            "tag": meta._inject_tag,
                        }
                
                return {"token": base_type}
        
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
        self._is_async = asyncio.iscoroutinefunction(factory)
        self._dependencies = self._extract_dependencies(factory)
        
        # Build metadata
        module = factory.__module__
        qualname = factory.__qualname__
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
        tags: tuple[str, ...] = (),
    ):
        self._value = value
        
        token_str = token if isinstance(token, str) else f"{token.__module__}.{token.__qualname__}"
        
        self._meta = ProviderMeta(
            name=name or "value",
            token=token_str,
            scope="singleton",
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
                    # Must be called from async context
                    loop = asyncio.get_event_loop()
                    self._instance = loop.run_until_complete(
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
