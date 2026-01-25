"""
Decorators and injection helpers for ergonomic DI usage.
"""

from typing import Any, Callable, Optional, Type, TypeVar, get_type_hints
from dataclasses import dataclass
import functools


T = TypeVar("T")


@dataclass
class Inject:
    """
    Injection metadata marker.
    
    Usage:
        def __init__(self, repo: Annotated[UserRepo, Inject(tag="repo")]):
            ...
    """
    
    token: Optional[Type | str] = None
    tag: Optional[str] = None
    optional: bool = False
    
    # Internal marker for provider introspection
    _inject_token: Optional[Type | str] = None
    _inject_tag: Optional[str] = None
    _inject_optional: bool = False
    
    def __post_init__(self):
        self._inject_token = self.token
        self._inject_tag = self.tag
        self._inject_optional = self.optional


def inject(
    token: Optional[Type | str] = None,
    *,
    tag: Optional[str] = None,
    optional: bool = False,
) -> Inject:
    """
    Create injection metadata.
    
    Args:
        token: Optional explicit token (inferred from type hint if None)
        tag: Optional tag for disambiguation
        optional: If True, inject None if provider not found
        
    Returns:
        Inject metadata object
        
    Example:
        def handler(
            db: Annotated[Database, inject(tag="readonly")],
            cache: Annotated[Cache, inject(optional=True)],
        ):
            ...
    """
    return Inject(token=token, tag=tag, optional=optional)


def service(
    *,
    scope: str = "app",
    tag: Optional[str] = None,
    name: Optional[str] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to mark a class as a DI service.
    
    Args:
        scope: Service scope (singleton, app, request, transient, pooled, ephemeral)
        tag: Optional tag for disambiguation
        name: Optional explicit service name
        
    Returns:
        Decorator function
        
    Example:
        @service(scope="request", tag="primary")
        class UserService:
            def __init__(self, repo: UserRepo):
                self.repo = repo
    """
    def decorator(cls: Type[T]) -> Type[T]:
        # Attach metadata to class
        cls.__di_scope__ = scope  # type: ignore
        cls.__di_tag__ = tag  # type: ignore
        cls.__di_name__ = name or cls.__name__  # type: ignore
        return cls
    
    return decorator


def factory(
    *,
    scope: str = "app",
    tag: Optional[str] = None,
    name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to mark a function as a DI factory.
    
    Args:
        scope: Service scope
        tag: Optional tag for disambiguation
        name: Optional explicit factory name
        
    Returns:
        Decorator function
        
    Example:
        @factory(scope="singleton", name="db_pool")
        async def create_db_pool(config: Config) -> DatabasePool:
            return await DatabasePool.connect(config.db_url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Attach metadata to function
        func.__di_scope__ = scope  # type: ignore
        func.__di_tag__ = tag  # type: ignore
        func.__di_name__ = name or func.__name__  # type: ignore
        func.__di_factory__ = True  # type: ignore
        return func
    
    return decorator


def provides(
    token: Type | str,
    *,
    scope: str = "app",
    tag: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to explicitly declare what a factory provides.
    
    Useful when return type annotation is generic or abstract.
    
    Args:
        token: Type or string key that this factory provides
        scope: Service scope
        tag: Optional tag
        
    Returns:
        Decorator function
        
    Example:
        @provides(UserRepository, scope="app", tag="sql")
        def create_sql_repo(db: Database) -> UserRepository:
            return SqlUserRepository(db)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        func.__di_provides__ = token  # type: ignore
        func.__di_scope__ = scope  # type: ignore
        func.__di_tag__ = tag  # type: ignore
        func.__di_factory__ = True  # type: ignore
        return func
    
    return decorator


def auto_inject(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to auto-inject dependencies into a function.
    
    Looks up dependencies from a thread-local container.
    
    WARNING: This is convenience sugar with some overhead.
    Prefer explicit dependency passing in hot paths.
    
    Example:
        @auto_inject
        async def my_handler(request: Request, db: Database):
            # db is automatically resolved from request container
            ...
    """
    from .compat import get_request_container
    
    sig = func.__signature__ if hasattr(func, "__signature__") else None
    hints = get_type_hints(func) if sig is None else None
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get request container from context
        container = get_request_container()
        if container is None:
            raise RuntimeError("No request container in context; cannot auto-inject")
        
        # Resolve missing dependencies
        if sig:
            params = sig.parameters
        else:
            import inspect
            params = inspect.signature(func).parameters
        
        for param_name, param in params.items():
            if param_name in kwargs or param_name == "self":
                continue
            
            # Get type hint
            type_hint = hints.get(param_name) if hints else param.annotation
            if type_hint is None or type_hint == param.empty:
                continue
            
            # Resolve from container
            try:
                resolved = await container.resolve_async(type_hint)
                kwargs[param_name] = resolved
            except Exception:
                # Optional or has default - skip
                if param.default != param.empty:
                    continue
                raise
        
        return await func(*args, **kwargs)
    
    return wrapper


# Convenience alias
injectable = service
