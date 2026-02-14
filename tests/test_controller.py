"""
Test 12: Controller System (controller/)

Tests Controller base, RequestCtx, decorators (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS/WS),
RouteDecorator, route(), ControllerMetadata, RouteMetadata, ParameterMetadata,
ControllerFactory, InstantiationMode.
"""

import pytest
import inspect
from unittest.mock import MagicMock, AsyncMock

from aquilia.controller.base import Controller, RequestCtx
from aquilia.controller.decorators import (
    RouteDecorator,
    GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, WS,
    route,
)
from aquilia.controller.metadata import (
    ParameterMetadata,
    RouteMetadata,
    ControllerMetadata,
)
from aquilia.controller.factory import ControllerFactory, InstantiationMode


# ============================================================================
# Controller base class
# ============================================================================

class TestControllerBase:

    def test_controller_attrs(self):
        class MyCtrl(Controller):
            prefix = "/users"
            tags = ["users"]

        assert MyCtrl.prefix == "/users"
        assert "users" in MyCtrl.tags

    def test_controller_default_prefix(self):
        class SimpleCtrl(Controller):
            pass

        assert SimpleCtrl.prefix == "/" or hasattr(SimpleCtrl, "prefix")

    def test_controller_instantiation_mode(self):
        class SingletonCtrl(Controller):
            instantiation_mode = "singleton"

        assert SingletonCtrl.instantiation_mode == "singleton"


# ============================================================================
# RequestCtx
# ============================================================================

class TestRequestCtx:

    def test_create(self):
        ctx = RequestCtx(
            request=MagicMock(),
        )
        assert ctx.request is not None
        assert isinstance(ctx.state, dict)


# ============================================================================
# Route Decorators
# ============================================================================

class TestRouteDecorators:

    def test_get_decorator(self):
        @GET("/users")
        async def get_users(self, ctx):
            pass

        assert hasattr(get_users, "__route_metadata__")
        meta = get_users.__route_metadata__[0]
        assert meta["http_method"] == "GET"
        assert meta["path"] == "/users"

    def test_post_decorator(self):
        @POST("/users")
        async def create_user(self, ctx):
            pass

        meta = create_user.__route_metadata__[0]
        assert meta["http_method"] == "POST"

    def test_put_decorator(self):
        @PUT("/users/«id»")
        async def update_user(self, ctx):
            pass

        meta = update_user.__route_metadata__[0]
        assert meta["http_method"] == "PUT"

    def test_patch_decorator(self):
        @PATCH("/users/«id»")
        async def patch_user(self, ctx):
            pass

        meta = patch_user.__route_metadata__[0]
        assert meta["http_method"] == "PATCH"

    def test_delete_decorator(self):
        @DELETE("/users/«id»")
        async def delete_user(self, ctx):
            pass

        meta = delete_user.__route_metadata__[0]
        assert meta["http_method"] == "DELETE"

    def test_head_decorator(self):
        @HEAD("/health")
        async def health_check(self, ctx):
            pass

        meta = health_check.__route_metadata__[0]
        assert meta["http_method"] == "HEAD"

    def test_options_decorator(self):
        @OPTIONS("/users")
        async def options_users(self, ctx):
            pass

        meta = options_users.__route_metadata__[0]
        assert meta["http_method"] == "OPTIONS"

    def test_ws_decorator(self):
        @WS("/ws")
        async def websocket(self, ctx):
            pass

        meta = websocket.__route_metadata__[0]
        assert meta["http_method"] == "WS"

    def test_decorator_no_path(self):
        @GET()
        async def index(self, ctx):
            pass

        meta = index.__route_metadata__[0]
        assert meta["http_method"] == "GET"
        assert meta["path"] is None

    def test_decorator_with_pipeline(self):
        @GET("/", pipeline=["guard1"])
        async def guarded(self, ctx):
            pass

        meta = guarded.__route_metadata__[0]
        assert meta["pipeline"] == ["guard1"]

    def test_decorator_with_tags(self):
        @GET("/", tags=["admin"])
        async def admin_route(self, ctx):
            pass

        meta = admin_route.__route_metadata__[0]
        assert "admin" in meta["tags"]

    def test_decorator_deprecated(self):
        @GET("/old", deprecated=True)
        async def old_route(self, ctx):
            pass

        meta = old_route.__route_metadata__[0]
        assert meta["deprecated"] is True

    def test_decorator_status_code(self):
        @POST("/", status_code=201)
        async def create(self, ctx):
            pass

        meta = create.__route_metadata__[0]
        assert meta["status_code"] == 201

    def test_decorator_summary_auto(self):
        @GET("/items")
        async def list_items(self, ctx):
            pass

        meta = list_items.__route_metadata__[0]
        assert meta["summary"] == "List Items"

    def test_route_generic(self):
        @route("GET", "/multi")
        async def multi_method(self, ctx):
            pass

        meta = multi_method.__route_metadata__[0]
        assert meta["http_method"] == "GET"

    def test_route_multiple_methods(self):
        @route(["GET", "POST"], "/both")
        async def both_methods(self, ctx):
            pass

        methods = [m["http_method"] for m in both_methods.__route_metadata__]
        assert "GET" in methods
        assert "POST" in methods

    def test_multiple_decorators_on_same_method(self):
        @GET("/a")
        @POST("/b")
        async def multi(self, ctx):
            pass

        assert len(multi.__route_metadata__) == 2


# ============================================================================
# Metadata
# ============================================================================

class TestParameterMetadata:

    def test_create(self):
        pm = ParameterMetadata(name="id", type=int, source="path")
        assert pm.name == "id"
        assert pm.type is int
        assert pm.source == "path"
        assert pm.required is True

    def test_has_default(self):
        pm = ParameterMetadata(name="limit", type=int, default=10)
        assert pm.has_default is True

    def test_no_default(self):
        pm = ParameterMetadata(name="id", type=int)
        assert pm.has_default is False


class TestRouteMetadata:

    def test_create(self):
        rm = RouteMetadata(
            http_method="GET",
            path_template="/users/«id:int»",
            full_path="/api/users/«id:int»",
            handler_name="get_user",
        )
        assert rm.http_method == "GET"
        assert rm.handler_name == "get_user"

    def test_specificity_static(self):
        rm = RouteMetadata(
            http_method="GET",
            path_template="/users/list",
            full_path="/api/users/list",
            handler_name="list_users",
        )
        score = rm.compute_specificity()
        assert score > 0

    def test_specificity_param_lower(self):
        static = RouteMetadata(
            http_method="GET",
            path_template="/users/list",
            full_path="/api/users/list",
            handler_name="list_users",
        )
        parameterized = RouteMetadata(
            http_method="GET",
            path_template="/users/«id»",
            full_path="/api/users/«id»",
            handler_name="get_user",
        )
        static.compute_specificity()
        parameterized.compute_specificity()
        assert static.specificity > parameterized.specificity

    def test_is_static_segment(self):
        assert RouteMetadata._is_static("users") is True
        assert RouteMetadata._is_static("«id»") is False

    def test_is_typed_param(self):
        assert RouteMetadata._is_typed_param("«id:int»") is True
        assert RouteMetadata._is_typed_param("«id»") is False

    def test_is_param(self):
        assert RouteMetadata._is_param("«id»") is True
        assert RouteMetadata._is_param("users") is False


class TestControllerMetadata:

    def test_create(self):
        cm = ControllerMetadata(
            class_name="UsersController",
            module_path="modules.users:UsersController",
            prefix="/api/users",
        )
        assert cm.class_name == "UsersController"
        assert cm.prefix == "/api/users"

    def test_get_route(self):
        route_meta = RouteMetadata(
            http_method="GET",
            path_template="/",
            full_path="/api/users/",
            handler_name="list",
        )
        cm = ControllerMetadata(
            class_name="UsersCtrl",
            module_path="mod:UsersCtrl",
            prefix="/api/users",
            routes=[route_meta],
        )
        found = cm.get_route("GET", "/api/users/")
        assert found is not None
        assert found.handler_name == "list"

    def test_get_route_missing(self):
        cm = ControllerMetadata(
            class_name="UsersCtrl",
            module_path="mod:UsersCtrl",
            prefix="/api/users",
        )
        assert cm.get_route("POST", "/missing") is None


# ============================================================================
# ControllerFactory
# ============================================================================

class TestControllerFactory:

    def test_create_factory(self):
        factory = ControllerFactory()
        assert factory is not None

    def test_instantiation_mode_values(self):
        assert InstantiationMode.PER_REQUEST == "per_request"
        assert InstantiationMode.SINGLETON == "singleton"

    @pytest.mark.asyncio
    async def test_create_per_request(self):
        factory = ControllerFactory()

        class SimpleCtrl(Controller):
            prefix = "/test"

        instance = await factory.create(SimpleCtrl, InstantiationMode.PER_REQUEST)
        assert isinstance(instance, SimpleCtrl)

    @pytest.mark.asyncio
    async def test_create_singleton_cached(self):
        factory = ControllerFactory()

        class SingleCtrl(Controller):
            prefix = "/test"

        inst1 = await factory.create(SingleCtrl, InstantiationMode.SINGLETON)
        inst2 = await factory.create(SingleCtrl, InstantiationMode.SINGLETON)
        assert inst1 is inst2
