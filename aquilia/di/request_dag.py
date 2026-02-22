"""
RequestDAG — Per-request dependency graph resolver.

Builds a DAG from handler parameter annotations, resolves the full
sub-dependency tree with deduplication, parallel independent branches,
and generator teardown.

Performance:
    - Zero overhead for handlers without ``Dep()`` annotations.
    - O(1) cache lookups for repeated sub-deps within a request.
    - ``asyncio.gather()`` for independent parallel branches.
    - LIFO teardown ordering (like nested context managers).
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Generator, Optional, Type, get_args, get_origin
import asyncio
import inspect
import logging

from .dep import (
    Body,
    Dep,
    Header,
    Query,
    _extract_body,
    _extract_dep_from_annotation,
    _extract_header,
    _extract_query,
    _unpack_annotation,
)

logger = logging.getLogger("aquilia.di.dag")

# Sentinel for "currently resolving" (cycle guard)
_RESOLVING = object()


class RequestDAG:
    """Per-request dependency resolution graph.

    Created once per handler invocation.  Resolves the dependency tree
    built from ``Dep()`` annotations with:

    - **Sub-dependency deduplication**: if A→C and B→C, C is resolved
      once and the result is shared.
    - **Parallel resolution**: independent branches are gathered.
    - **Generator teardown**: async/sync generators are yielded, and
      their cleanup code runs during ``teardown()``.
    - **Container integration**: bare ``Dep()`` (no callable) falls
      through to ``container.resolve_async(type)``.

    Usage::

        dag = RequestDAG(container, request)
        value = await dag.resolve(dep_descriptor, expected_type)
        # ... use value ...
        await dag.teardown()  # runs generator cleanups in LIFO order
    """

    __slots__ = ("_container", "_request", "_cache", "_teardowns", "_resolving")

    def __init__(self, container: Any, request: Any = None):
        """
        Args:
            container: DI container (app or request-scoped).
            request:   Current HTTP request, used for Header/Query/Body
                       extraction inside Dep callables.
        """
        self._container = container
        self._request = request
        self._cache: dict[str, Any] = {}
        self._teardowns: list[AsyncGenerator | Generator] = []
        self._resolving: set[str] = set()

    # ── Public API ───────────────────────────────────────────────────

    async def resolve(self, dep: Dep, param_type: type) -> Any:
        """Resolve a single Dep descriptor.

        Args:
            dep:        The ``Dep(...)`` descriptor from the annotation.
            param_type: The base type extracted from ``Annotated[T, Dep(...)]``.

        Returns:
            The resolved dependency value.

        Raises:
            RuntimeError: On circular dependency.
        """
        # Fast path: container-only lookup (no callable)
        if dep.is_container_lookup:
            return await self._resolve_from_container(param_type, dep.tag)

        cache_key = dep.cache_key

        # Check DAG cache (deduplication)
        if dep.cached and cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached is _RESOLVING:
                raise RuntimeError(
                    f"Circular dependency detected in request DAG: "
                    f"{dep.call.__qualname__ if dep.call else param_type}"
                )
            return cached

        # Mark as resolving (cycle guard)
        if dep.cached:
            self._resolving.add(cache_key)
            self._cache[cache_key] = _RESOLVING

        try:
            result = await self._invoke(dep)

            # Cache result
            if dep.cached:
                self._cache[cache_key] = result
                self._resolving.discard(cache_key)

            return result

        except Exception:
            # Clean up sentinel on failure
            if dep.cached:
                self._cache.pop(cache_key, None)
                self._resolving.discard(cache_key)
            raise

    async def teardown(self) -> None:
        """Run generator teardowns in LIFO order.

        This should be called after the handler has returned (or raised),
        typically in a ``finally`` block.
        """
        errors: list[Exception] = []
        for gen in reversed(self._teardowns):
            try:
                if inspect.isasyncgen(gen):
                    try:
                        await gen.__anext__()
                    except StopAsyncIteration:
                        pass
                elif inspect.isgenerator(gen):
                    try:
                        next(gen)
                    except StopIteration:
                        pass
            except Exception as exc:
                logger.warning(f"Error during Dep teardown: {exc}")
                errors.append(exc)

        self._teardowns.clear()
        self._cache.clear()

        if errors:
            logger.warning(f"{len(errors)} teardown error(s) suppressed")

    # ── Internal ─────────────────────────────────────────────────────

    async def _invoke(self, dep: Dep) -> Any:
        """Invoke a Dep callable after resolving its sub-dependencies."""
        assert dep.call is not None

        # 1. Inspect sub-dependencies
        sub_deps = dep.get_sub_dependencies()

        # 2. Resolve all sub-dependencies
        kwargs = await self._resolve_sub_deps(sub_deps)

        # 3. Call the callable
        if dep.is_generator:
            return await self._invoke_generator(dep, kwargs)
        elif dep.is_async:
            return await dep.call(**kwargs)
        else:
            result = dep.call(**kwargs)
            # Handle sync functions that accidentally return coroutines
            if inspect.isawaitable(result):
                return await result
            return result

    async def _resolve_sub_deps(
        self, sub_deps: dict[str, tuple[type, Any]]
    ) -> dict[str, Any]:
        """Resolve sub-dependencies, parallelising independent branches."""
        if not sub_deps:
            return {}

        # Separate into parallel-resolvable groups
        tasks: dict[str, Any] = {}

        for pname, (ptype, sub_dep) in sub_deps.items():
            tasks[pname] = self._resolve_single_sub_dep(pname, ptype, sub_dep)

        # Gather all in parallel
        if len(tasks) == 1:
            # Optimisation: skip gather for single dependency
            key = next(iter(tasks))
            return {key: await tasks[key]}

        keys = list(tasks.keys())
        coros = [tasks[k] for k in keys]
        results = await asyncio.gather(*coros)
        return dict(zip(keys, results))

    async def _resolve_single_sub_dep(
        self, pname: str, ptype: type, sub_dep: Any
    ) -> Any:
        """Resolve a single sub-dependency parameter."""
        # Check for Header/Query/Body extractors first
        if self._request is not None:
            if isinstance(sub_dep, Header):
                return self._extract_header_value(sub_dep, ptype)
            if isinstance(sub_dep, Query):
                return self._extract_query_value(sub_dep, ptype)
            if isinstance(sub_dep, Body):
                return await self._extract_body_value(sub_dep)

        if isinstance(sub_dep, Dep):
            # Recursive Dep resolution
            base_type, _ = _unpack_annotation(ptype)
            return await self.resolve(sub_dep, base_type)

        base_type = _get_base_type(ptype)
        if _is_serializer_type(base_type):
            serializer = await base_type.from_request_async(
                self._request, container=self._container
            )
            serializer.is_valid(raise_fault=True)
            if pname == "serializer" or pname.endswith("_serializer") or pname.endswith("_ser"):
                return serializer
            return serializer.validated_data

        # No Dep/extractor annotation → resolve from container by type
        return await self._resolve_from_container(ptype, tag=None)

    async def _invoke_generator(self, dep: Dep, kwargs: dict[str, Any]) -> Any:
        """Invoke a generator Dep and track teardown."""
        if inspect.isasyncgenfunction(dep.call):
            gen = dep.call(**kwargs)
            value = await gen.__anext__()
            self._teardowns.append(gen)
            return value
        elif inspect.isgeneratorfunction(dep.call):
            gen = dep.call(**kwargs)
            value = next(gen)
            self._teardowns.append(gen)
            return value
        else:
            raise TypeError(f"{dep.call} is not a generator function")

    async def _resolve_from_container(self, param_type: type, tag: str | None) -> Any:
        """Resolve from DI container by type."""
        try:
            return await self._container.resolve_async(param_type, tag=tag, optional=False)
        except Exception:
            # Try by qualified name as fallback
            if isinstance(param_type, type):
                key = f"{param_type.__module__}.{param_type.__qualname__}"
                try:
                    return await self._container.resolve_async(key, tag=tag, optional=False)
                except Exception:
                    pass
            raise

    # ── Request data extraction ──────────────────────────────────────

    def _extract_header_value(self, header: Header, ptype: type) -> Any:
        """Extract header value from request."""
        if self._request is None:
            if header.required:
                raise ValueError(f"No request available for Header('{header.name}')")
            return header.default

        # Try Aquilia's request API
        value = None
        if hasattr(self._request, "headers"):
            headers = self._request.headers
            if isinstance(headers, dict):
                value = headers.get(header.header_key)
            elif hasattr(headers, "get"):
                value = headers.get(header.header_key)

        if value is None:
            if header.required:
                raise ValueError(f"Missing required header: {header.name}")
            return header.default

        return value

    def _extract_query_value(self, query: Query, ptype: type) -> Any:
        """Extract query parameter from request."""
        if self._request is None:
            return query.default

        if hasattr(self._request, "query_param"):
            value = self._request.query_param(query.name)
        elif hasattr(self._request, "query_params"):
            qps = self._request.query_params
            value = qps.get(query.name) if isinstance(qps, dict) else None
        else:
            value = None

        if value is None:
            if query.required:
                raise ValueError(f"Missing required query parameter: {query.name}")
            return query.default

        # Try to cast to expected type
        base_type = _get_base_type(ptype)
        if base_type is int:
            return int(value)
        elif base_type is float:
            return float(value)
        elif base_type is bool:
            return value.lower() in ("true", "1", "yes")
        return value

    async def _extract_body_value(self, body: Body) -> Any:
        """Extract body from request."""
        if self._request is None:
            return {}

        try:
            return await self._request.json()
        except Exception:
            try:
                return await self._request.form()
            except Exception:
                return {}


# ── Module-level helpers ─────────────────────────────────────────────

def _extract_header_from_type(annotation: Any) -> Header | None:
    """Check if annotation is Annotated[T, Header(...)]."""
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


def _extract_query_from_type(annotation: Any) -> Query | None:
    """Check if annotation is Annotated[T, Query(...)]."""
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


def _extract_body_from_type(annotation: Any) -> Body | None:
    """Check if annotation is Annotated[T, Body(...)]."""
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


def _get_base_type(annotation: Any) -> type:
    """Unwrap Annotated[T, ...] → T."""
    origin = get_origin(annotation)
    if origin is not None:
        try:
            from typing import Annotated
            if origin is Annotated:
                return get_args(annotation)[0]
        except ImportError:
            pass
    return annotation


def _is_serializer_type(annotation: Any) -> bool:
    """Check if type is a Serializer subclass."""
    try:
        from aquilia.serializers.base import Serializer
        return (
            isinstance(annotation, type)
            and issubclass(annotation, Serializer)
            and annotation is not Serializer
        )
    except ImportError:
        return False
