"""
Tests for the Dep descriptor, RequestDAG, and annotation-driven DI.

Covers:
- Dep descriptor properties and sub-dependency introspection
- RequestDAG resolution with deduplication and parallel branches
- Generator dependency teardown
- Header/Query/Body extraction in Dep callables
- Backwards compat with Inject
- Bug fixes: FactoryProvider Annotated parsing, metadata generic classification
"""

import asyncio
import inspect
import pytest
from typing import Annotated, Optional, List
from dataclasses import dataclass

from aquilia.di import Container, Dep, Header, Query, Body, RequestDAG, Inject
from aquilia.di.dep import _unpack_annotation, _extract_dep_from_annotation
from aquilia.di.request_dag import RequestDAG as RequestDAGImpl
from aquilia.di.core import ProviderMeta
from aquilia.di.providers import FactoryProvider, ValueProvider
from aquilia.testing.di import TestContainer


# ── Fixtures ─────────────────────────────────────────────────────────

class FakeRequest:
    """Minimal request mock for DAG tests."""

    def __init__(self, headers=None, query_params=None, body=None):
        self._headers = headers or {}
        self._query_params = query_params or {}
        self._body = body or {}

    @property
    def headers(self):
        return self._headers

    def query_param(self, name):
        return self._query_params.get(name)

    async def json(self):
        return self._body

    async def form(self):
        return self._body


# ═══════════════════════════════════════════════════════════════════════
# Test Group 1: Dep Descriptor
# ═══════════════════════════════════════════════════════════════════════

class TestDepDescriptor:
    """Unit tests for the Dep dataclass."""

    def test_bare_dep_is_container_lookup(self):
        d = Dep()
        assert d.is_container_lookup is True
        assert d.is_generator is False
        assert d.is_async is False

    def test_dep_with_callable(self):
        async def get_db():
            return "db"

        d = Dep(call=get_db)
        assert d.is_container_lookup is False
        assert d.is_async is True
        assert d.is_generator is False
        assert "get_db" in d.cache_key

    def test_dep_with_sync_callable(self):
        def get_config():
            return {"debug": True}

        d = Dep(call=get_config)
        assert d.is_async is False
        assert d.is_generator is False

    def test_dep_with_async_generator(self):
        async def get_session():
            yield "session"

        d = Dep(call=get_session)
        assert d.is_generator is True
        assert d.is_async is True

    def test_dep_with_sync_generator(self):
        def get_conn():
            yield "conn"

        d = Dep(call=get_conn)
        assert d.is_generator is True

    def test_dep_cached_default(self):
        d = Dep(call=lambda: 1)
        assert d.cached is True

    def test_dep_uncached(self):
        d = Dep(call=lambda: 1, cached=False)
        assert d.cached is False

    def test_dep_with_tag(self):
        d = Dep(tag="primary")
        assert d.tag == "primary"
        assert d.is_container_lookup is True

    def test_sub_dependencies_extraction(self):
        async def dep_func(x: int, y: str = "default"):
            return (x, y)

        d = Dep(call=dep_func)
        subs = d.get_sub_dependencies()
        assert "x" in subs
        assert "y" in subs
        assert subs["x"][0] is int
        assert subs["y"][0] is str

    def test_sub_deps_with_annotated_dep(self):
        async def get_db():
            return "db"

        async def get_user(db: Annotated[str, Dep(get_db)]):
            return f"user:{db}"

        d = Dep(call=get_user)
        subs = d.get_sub_dependencies()
        assert "db" in subs
        base_type, sub_dep = subs["db"]
        assert base_type is str
        assert isinstance(sub_dep, Dep)
        assert sub_dep.call is get_db


# ═══════════════════════════════════════════════════════════════════════
# Test Group 2: Annotation Unpacking
# ═══════════════════════════════════════════════════════════════════════

class TestAnnotationUnpacking:
    """Tests for _unpack_annotation utility."""

    def test_plain_type(self):
        base, dep = _unpack_annotation(int)
        assert base is int
        assert dep is None

    def test_annotated_with_dep(self):
        ann = Annotated[str, Dep(tag="x")]
        base, dep = _unpack_annotation(ann)
        assert base is str
        assert isinstance(dep, Dep)
        assert dep.tag == "x"

    def test_annotated_with_inject_compat(self):
        ann = Annotated[str, Inject(tag="y")]
        base, dep = _unpack_annotation(ann)
        assert base is str
        assert isinstance(dep, Dep)
        assert dep.tag == "y"

    def test_annotated_no_markers(self):
        ann = Annotated[str, "some metadata"]
        base, dep = _unpack_annotation(ann)
        assert base is str
        assert dep is None

    def test_extract_dep(self):
        async def f():
            return 1

        ann = Annotated[int, Dep(f)]
        dep = _extract_dep_from_annotation(ann)
        assert dep is not None
        assert dep.call is f


# ═══════════════════════════════════════════════════════════════════════
# Test Group 3: RequestDAG Resolution
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRequestDAGResolution:
    """Test per-request DAG resolution."""

    async def test_container_lookup(self):
        class DummyService:
            pass

        container = TestContainer(scope="app")
        svc = DummyService()
        # Mock provider token_str computation is slightly naive, using a string token is safer if not fully qualified
        container.register_value("dummy_token", svc)

        dag = RequestDAG(container)
        dep = Dep(tag="dummy_token") 
        # Actually bare Dep() tries type by default. Let's register value against the type using Container.bind or mock
        # Let's just fix the mock token
        from aquilia.di.providers import ValueProvider
        container.register(ValueProvider(svc, token=DummyService))

        dep = Dep()  # bare → container lookup
        result = await dag.resolve(dep, DummyService)
        assert result is svc
        await dag.teardown()

    async def test_callable_dep_resolution(self):
        call_count = 0

        async def get_value():
            nonlocal call_count
            call_count += 1
            return 42

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_value)
        result = await dag.resolve(dep, int)
        assert result == 42
        assert call_count == 1

        await dag.teardown()

    async def test_dep_caching_deduplication(self):
        call_count = 0

        async def get_db():
            nonlocal call_count
            call_count += 1
            return "db_connection"

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_db)
        r1 = await dag.resolve(dep, str)
        r2 = await dag.resolve(dep, str)

        assert r1 is r2  # same object — cached
        assert call_count == 1  # called only once

        await dag.teardown()

    async def test_dep_uncached_creates_fresh(self):
        call_count = 0

        async def create_worker():
            nonlocal call_count
            call_count += 1
            return f"worker-{call_count}"

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=create_worker, cached=False)
        r1 = await dag.resolve(dep, str)
        r2 = await dag.resolve(dep, str)

        assert r1 != r2  # different objects
        assert call_count == 2  # called twice

        await dag.teardown()

    async def test_chained_sub_dependencies(self):
        """Test A → B → C resolution chain."""
        async def get_config():
            return {"db_url": "sqlite://"}

        async def get_db(config: Annotated[dict, Dep(get_config)]):
            return f"db({config['db_url']})"

        async def get_user(db: Annotated[str, Dep(get_db)]):
            return f"user(from:{db})"

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_user)
        result = await dag.resolve(dep, str)
        assert result == "user(from:db(sqlite://))"

        await dag.teardown()

    async def test_diamond_dependency_dedup(self):
        """Test diamond: A→C, B→C, handler→(A,B). C resolved once."""
        call_count = 0

        async def get_db():
            nonlocal call_count
            call_count += 1
            return "db"

        async def get_users(db: Annotated[str, Dep(get_db)]):
            return f"users({db})"

        async def get_orders(db: Annotated[str, Dep(get_db)]):
            return f"orders({db})"

        async def get_dashboard(
            users: Annotated[str, Dep(get_users)],
            orders: Annotated[str, Dep(get_orders)],
        ):
            return f"dashboard({users},{orders})"

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_dashboard)
        result = await dag.resolve(dep, str)

        assert "users(db)" in result
        assert "orders(db)" in result
        assert call_count == 1  # get_db called only once!

        await dag.teardown()

    async def test_sync_callable(self):
        def get_version():
            return "1.0.0"

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_version)
        result = await dag.resolve(dep, str)
        assert result == "1.0.0"

        await dag.teardown()

    async def test_cycle_detection(self):
        # Create a cycle: a → b → a
        async def dep_a(b: Annotated[str, Dep(None)]):
            return f"a({b})"

        async def dep_b(a: Annotated[str, Dep(None)]):
            return f"b({a})"

        # We can't easily create a real cycle with Dep(call=...) since
        # the functions reference each other. Let's test the sentinel.
        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        # Manually test cycle detection by pre-setting cache sentinel
        from aquilia.di.request_dag import _RESOLVING

        dep = Dep(call=lambda: 1)
        dag._cache[dep.cache_key] = _RESOLVING

        with pytest.raises(RuntimeError, match="Circular dependency"):
            await dag.resolve(dep, int)

        await dag.teardown()


# ═══════════════════════════════════════════════════════════════════════
# Test Group 4: Generator Dependency Teardown
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestGeneratorTeardown:
    """Test async/sync generator deps with teardown."""

    async def test_async_generator_yields_and_tears_down(self):
        teardown_ran = False

        async def get_session():
            nonlocal teardown_ran
            yield "session_obj"
            teardown_ran = True

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_session)
        result = await dag.resolve(dep, str)
        assert result == "session_obj"
        assert teardown_ran is False  # not yet

        await dag.teardown()
        assert teardown_ran is True  # now cleaned up

    async def test_sync_generator_yields_and_tears_down(self):
        teardown_ran = False

        def get_conn():
            nonlocal teardown_ran
            yield "connection"
            teardown_ran = True

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        dep = Dep(call=get_conn)
        result = await dag.resolve(dep, str)
        assert result == "connection"
        assert teardown_ran is False

        await dag.teardown()
        assert teardown_ran is True

    async def test_multiple_generators_lifo_teardown(self):
        order = []

        async def gen_a():
            yield "a"
            order.append("a_teardown")

        async def gen_b():
            yield "b"
            order.append("b_teardown")

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        await dag.resolve(Dep(call=gen_a), str)
        await dag.resolve(Dep(call=gen_b), str)

        await dag.teardown()
        # LIFO: b teardown before a
        assert order == ["b_teardown", "a_teardown"]

    async def test_teardown_error_suppressed(self):
        async def bad_gen():
            yield "value"
            raise ValueError("cleanup failed")

        container = TestContainer(scope="app")
        dag = RequestDAG(container)

        await dag.resolve(Dep(call=bad_gen), str)
        # Should not raise
        await dag.teardown()


# ═══════════════════════════════════════════════════════════════════════
# Test Group 5: Header/Query/Body Extraction
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRequestExtractors:
    """Test Header/Query/Body extraction in Dep callables."""

    async def test_header_extraction(self):
        async def get_token(auth: Annotated[str, Header("Authorization")]):
            return auth.removeprefix("Bearer ")

        request = FakeRequest(headers={"authorization": "Bearer abc123"})
        container = TestContainer(scope="app")
        dag = RequestDAG(container, request)

        dep = Dep(call=get_token)
        result = await dag.resolve(dep, str)
        assert result == "abc123"

        await dag.teardown()

    async def test_query_extraction(self):
        async def get_page(page: Annotated[int, Query("page", default=1)]):
            return page

        request = FakeRequest(query_params={"page": "3"})
        container = TestContainer(scope="app")
        dag = RequestDAG(container, request)

        dep = Dep(call=get_page)
        result = await dag.resolve(dep, int)
        assert result == 3

        await dag.teardown()

    async def test_query_default(self):
        async def get_page(page: Annotated[int, Query("page", default=1)]):
            return page

        request = FakeRequest()
        container = TestContainer(scope="app")
        dag = RequestDAG(container, request)

        dep = Dep(call=get_page)
        result = await dag.resolve(dep, int)
        assert result == 1

        await dag.teardown()

    async def test_missing_required_header_raises(self):
        async def need_auth(token: Annotated[str, Header("X-Token")]):
            return token

        request = FakeRequest()
        container = TestContainer(scope="app")
        dag = RequestDAG(container, request)

        dep = Dep(call=need_auth)
        with pytest.raises(ValueError, match="Missing required header"):
            await dag.resolve(dep, str)

        await dag.teardown()


# ═══════════════════════════════════════════════════════════════════════
# Test Group 6: Bug Fixes
# ═══════════════════════════════════════════════════════════════════════

class TestBugFixes:
    """Verify the 4 bug fixes are working."""

    def test_factory_provider_parses_annotated(self):
        """Bug: FactoryProvider._extract_dependencies ignored Annotated."""

        async def my_factory(db: Annotated[str, Inject(tag="primary")]):
            return f"result({db})"

        provider = FactoryProvider(my_factory, scope="app")
        deps = provider._dependencies
        assert "db" in deps
        assert deps["db"]["token"] is str
        assert deps["db"]["tag"] == "primary"

    def test_metadata_optional_not_classified_as_di(self):
        """Bug: Optional[str] was classified as source='di'."""
        from aquilia.controller.metadata import _extract_method_params

        def handler(self, ctx, name: Optional[str] = None, count: int = 0):
            pass

        sig = inspect.signature(handler)
        params = _extract_method_params(handler, sig, "/test")

        for p in params:
            if p.name == "name":
                assert p.source == "query", f"Optional[str] should be query, got {p.source}"
            elif p.name == "count":
                assert p.source == "query"

    def test_metadata_list_not_classified_as_di(self):
        """Bug: List[int] was classified as source='di'."""
        from aquilia.controller.metadata import _extract_method_params

        def handler(self, ctx, ids: List[int] = None):
            pass

        sig = inspect.signature(handler)
        params = _extract_method_params(handler, sig, "/test")

        for p in params:
            if p.name == "ids":
                assert p.source == "query", f"List[int] should be query, got {p.source}"

    def test_metadata_dep_classified_as_dep(self):
        """Verify: Annotated[T, Dep(...)] is classified as source='dep'."""
        from aquilia.controller.metadata import _extract_method_params

        async def get_db():
            return "db"

        def handler(self, ctx, db: Annotated[str, Dep(get_db)]):
            pass

        sig = inspect.signature(handler)
        params = _extract_method_params(handler, sig, "/test")

        for p in params:
            if p.name == "db":
                assert p.source == "dep", f"Dep() should be dep, got {p.source}"

    def test_metadata_inject_still_classified_as_di(self):
        """Verify: Annotated[T, Inject()] still classified as source='di'."""
        from aquilia.controller.metadata import _extract_method_params

        def handler(self, ctx, repo: Annotated[str, Inject(tag="main")]):
            pass

        sig = inspect.signature(handler)
        params = _extract_method_params(handler, sig, "/test")

        for p in params:
            if p.name == "repo":
                assert p.source == "di", f"Inject() should be di, got {p.source}"
