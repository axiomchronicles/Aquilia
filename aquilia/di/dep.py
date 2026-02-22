"""
Dep — Composable dependency descriptor for annotation-driven DI.

Aquilia's answer to FastAPI's Depends(), but built on Annotated[] and
designed for the Aquilia provider/container ecosystem.

Usage::

    from typing import Annotated
    from aquilia.di import Dep

    # Callable dependency — resolved per-request, cached in request DAG
    async def get_db() -> Database:
        return await Database.connect(...)

    async def get_current_user(
        db: Annotated[Database, Dep(get_db)],
        token: Annotated[str, Header("Authorization")],
    ) -> User:
        return await db.find_user_by_token(token)

    class UsersController(Controller):
        @GET("/me")
        async def me(self, ctx, user: Annotated[User, Dep(get_current_user)]):
            return user

    # Generator dependency with teardown
    async def get_db_session():
        session = Session()
        try:
            yield session
        finally:
            await session.close()

    @GET("/items")
    async def list_items(self, ctx, db: Annotated[Session, Dep(get_db_session)]):
        return await db.query(Item).all()

    # Bare Dep() — resolve from container by type (like Inject())
    async def handler(repo: Annotated[UserRepo, Dep()]):
        ...

    # Uncached — fresh instance per injection point
    async def handler(w: Annotated[Worker, Dep(create_worker, cached=False)]):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Optional,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)
import asyncio
import inspect


@dataclass(frozen=True, slots=True)
class Dep:
    """Dependency descriptor for Annotated[]-based injection.

    Attributes:
        call:      Optional callable (sync/async function, generator, or class).
                   If None, resolves from container by type annotation.
        cached:    Whether to cache the result in the per-request DAG.
                   True by default — a shared ``get_db`` appears once in
                   the DAG even if multiple parameters depend on it.
        scope:     Optional scope override. When set, the dependency is
                   resolved/instantiated in the given scope regardless of
                   the callable's own scope hints.
        tag:       Container tag for disambiguation (same semantics as Inject.tag).
        use_cache: Whether to check the container's own instance cache
                   before calling the factory. True by default.
    """

    call: Optional[Callable[..., Any]] = None
    cached: bool = True
    scope: Optional[str] = None
    tag: Optional[str] = None
    use_cache: bool = True

    # ── Internal introspection helpers ───────────────────────────────

    @property
    def is_container_lookup(self) -> bool:
        """True when Dep() has no callable — just resolve by type from container."""
        return self.call is None

    @property
    def is_generator(self) -> bool:
        """True when the callable is an (async) generator → needs teardown."""
        if self.call is None:
            return False
        return (
            inspect.isasyncgenfunction(self.call)
            or inspect.isgeneratorfunction(self.call)
        )

    @property
    def is_async(self) -> bool:
        """True when the callable is async (coroutine or async generator)."""
        if self.call is None:
            return False
        return (
            inspect.iscoroutinefunction(self.call)
            or inspect.isasyncgenfunction(self.call)
        )

    @property
    def cache_key(self) -> str:
        """Stable key for DAG deduplication.

        Uses the callable's id for function deps, or 'container:tag' for lookups.
        """
        if self.call is not None:
            mod = getattr(self.call, "__module__", "")
            qual = getattr(self.call, "__qualname__", "")
            return f"dep:{mod}.{qual}"
        return f"container:{self.tag or ''}"

    def get_sub_dependencies(self) -> dict[str, tuple[type, "Any"]]:
        """Inspect the callable's signature and extract sub-Dep annotations.

        Returns:
            dict mapping param_name → (base_type, metadata).
            If a param has no annotation, metadata is None (resolve by type).
        """
        if self.call is None:
            return {}

        try:
            hints = get_type_hints(self.call, include_extras=True)
        except Exception:
            hints = {}

        sig = inspect.signature(self.call)
        result: dict[str, tuple[type, Any]] = {}

        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            ann = hints.get(pname, param.annotation)
            if ann is inspect.Parameter.empty:
                continue

            base_type, dep_meta = _unpack_annotation(ann)
            result[pname] = (base_type, dep_meta)

        return result


# ── Annotation Helpers ───────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Header:
    """Extract a header value from the current request.

    Usage::

        async def get_token(auth: Annotated[str, Header("Authorization")]) -> str:
            return auth.removeprefix("Bearer ")
    """

    name: str
    alias: Optional[str] = None
    required: bool = True
    default: Any = None
    _di_requires_coercion: bool = field(default=True, init=False, repr=False)

    @property
    def header_key(self) -> str:
        return (self.alias or self.name).lower()

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve header from request context (allows use as Serializer default)."""
        request = context.get("request")
        if request is None:
            if self.required:
                raise ValueError(f"No request available for Header('{self.name}')")
            return self.default

        value = None
        if hasattr(request, "headers"):
            headers = request.headers
            if isinstance(headers, dict):
                value = headers.get(self.header_key)
            elif hasattr(headers, "get"):
                value = headers.get(self.header_key)

        if value is None:
            if self.required:
                raise ValueError(f"Missing required header: {self.name}")
            return self.default
        return value


@dataclass(frozen=True, slots=True)
class Query:
    """Extract a query parameter from the current request.

    Usage::

        async def get_page(page: Annotated[int, Query("page", default=1)]) -> int:
            return page
    """

    name: str
    default: Any = None
    required: bool = False
    _di_requires_coercion: bool = field(default=True, init=False, repr=False)

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve query from request context (allows use as Serializer default)."""
        request = context.get("request")
        if request is None:
            return self.default

        if hasattr(request, "query_param"):
            value = request.query_param(self.name)
        elif hasattr(request, "query_params"):
            qps = request.query_params
            value = qps.get(self.name) if isinstance(qps, dict) else None
        else:
            value = None

        if value is None:
            if self.required:
                raise ValueError(f"Missing required query parameter: {self.name}")
            return self.default
        return value


@dataclass(frozen=True, slots=True)
class Body:
    """Mark a parameter as coming from the request body.

    Usage::

        async def parse_payload(data: Annotated[dict, Body()]) -> dict:
            return data
    """

    media_type: str = "application/json"
    embed: bool = False
    _di_requires_coercion: bool = field(default=True, init=False, repr=False)

    def resolve(self, context: dict[str, Any]) -> Any:
        """Resolve body from request context (async behavior not supported inside sync Serializer)."""
        # Serializer validation is sync, so Body extraction inside a field default is not fully supported
        # unless the request body is already parsed/cached.
        request = context.get("request")
        if request is None:
            return {}

        if hasattr(request, "_body_cache"):
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if not loop or not loop.is_running():
                return asyncio.run(request.json())
        return {}


# ── Internal Utilities ───────────────────────────────────────────────

def _unpack_annotation(annotation: Any) -> tuple[type, Any]:
        """Unpack Annotated[T, Dep(...)] → (T, metadata).

        If no Dep/Header/Query metadata is found, returns (annotation, None).
        Also recognises Inject for backwards compatibility.
        """
        origin = get_origin(annotation)
        if origin is None:
            return (annotation, None)

        try:
            from typing import Annotated

            if origin is Annotated:
                args = get_args(annotation)
                base_type = args[0]
                for meta in args[1:]:
                    if isinstance(meta, Dep):
                        return (base_type, meta)
                    # Backwards compat: treat Inject as Dep()
                    if isinstance(meta, _get_inject_class()):
                        return (
                            base_type,
                            Dep(
                                tag=getattr(meta, "tag", None),
                            ),
                        )
                    # Header/Query/Body are handled by RequestDAG
                    if isinstance(meta, (Header, Query, Body)):
                        return (base_type, meta)
                return (base_type, None)
        except ImportError:
            pass

        return (annotation, None)


def _get_inject_class():
    """Lazy import to avoid circular dependency."""
    try:
        from aquilia.di.decorators import Inject

        return Inject
    except ImportError:
        return type(None)


def _extract_dep_from_annotation(annotation: Any) -> Optional["Dep"]:
    """Extract a Dep instance from an Annotated type, if present."""
    origin = get_origin(annotation)
    if origin is None:
        return None

    try:
        from typing import Annotated

        if origin is Annotated:
            args = get_args(annotation)
            for meta in args[1:]:
                if isinstance(meta, Dep):
                    return meta
                if isinstance(meta, _get_inject_class()):
                    return Dep(tag=getattr(meta, "tag", None))
    except ImportError:
        pass

    return None


def _extract_header(annotation: Any) -> Optional[Header]:
    """Extract a Header from an Annotated type."""
    origin = get_origin(annotation)
    if origin is None:
        return None
    try:
        from typing import Annotated
        if origin is Annotated:
            for meta in get_args(annotation)[1:]:
                if isinstance(meta, Header):
                    return meta
    except ImportError:
        pass
    return None


def _extract_query(annotation: Any) -> Optional[Query]:
    """Extract a Query from an Annotated type."""
    origin = get_origin(annotation)
    if origin is None:
        return None
    try:
        from typing import Annotated
        if origin is Annotated:
            for meta in get_args(annotation)[1:]:
                if isinstance(meta, Query):
                    return meta
    except ImportError:
        pass
    return None


def _extract_body(annotation: Any) -> Optional[Body]:
    """Extract a Body from an Annotated type."""
    origin = get_origin(annotation)
    if origin is None:
        return None
    try:
        from typing import Annotated
        if origin is Annotated:
            for meta in get_args(annotation)[1:]:
                if isinstance(meta, Body):
                    return meta
    except ImportError:
        pass
    return None
