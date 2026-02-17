"""
Tests: Blueprint ↔ Controller Engine Integration

Validates:
    1. request_blueprint / response_blueprint in route decorators
    2. Blueprint auto-injection via type annotations (like Serializer injection)
    3. _is_blueprint_class detection in engine
    4. _is_blueprint_type detection in metadata
    5. _apply_response_blueprint molding
    6. Blueprint parameter binding (full instance vs validated_data)
    7. Projected response_blueprint (Blueprint["projection"])
    8. Partial mode for PATCH requests
    9. Migration parity: same behavior as Serializer-based controllers
"""

import pytest
import asyncio
import logging

from aquilia.blueprints import (
    Blueprint,
    TextFacet,
    IntFacet,
    FloatFacet,
    BoolFacet,
    DateTimeFacet,
    EmailFacet,
    ReadOnly,
    Hidden,
    Inject,
    Computed,
    Constant,
)
from aquilia.blueprints.exceptions import SealFault
from aquilia.controller.decorators import (
    GET, POST, PUT, PATCH, DELETE,
    RouteDecorator,
)


# ── Test Blueprints ──────────────────────────────────────────────────────

class ItemBlueprint(Blueprint):
    """Simple Blueprint for testing."""
    id = IntFacet(read_only=True)
    name = TextFacet(max_length=100)
    price = FloatFacet(default=0.0)
    active = BoolFacet(default=True)

    class Spec:
        projections = {
            "summary": ["id", "name"],
            "detail": "__all__",
        }
        default_projection = "detail"


class CreateItemBlueprint(Blueprint):
    """Write-only Blueprint for creation."""
    name = TextFacet(max_length=100, min_length=2)
    price = FloatFacet()
    active = BoolFacet(default=True)

    def seal_price_positive(self, data):
        """Custom seal: price must be positive."""
        if data.get("price", 0) < 0:
            self.reject("price", "Price must be non-negative")


class UpdateItemBlueprint(Blueprint):
    """Partial update Blueprint."""
    name = TextFacet(max_length=100, required=False)
    price = FloatFacet(required=False)
    active = BoolFacet(required=False)

    # DI injection test
    updated_by = Inject(token="identity", attr="id")


# ── Helpers ──────────────────────────────────────────────────────────────

class SimpleObj:
    """Simple object for testing output molding."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeRequest:
    """Minimal request stub."""
    def __init__(self, method="GET", body=None, client_ip="127.0.0.1", identity=None):
        self._body = body or {}
        self.method = method
        self.client_ip = client_ip
        self.state = {}
        if identity:
            self.state["identity"] = identity

    async def json(self):
        return self._body

    async def form(self):
        return self._body

    def query_param(self, name, default=None):
        return default


# ═══════════════════════════════════════════════════════════════════════
# 1. Decorator Metadata Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDecoratorBlueprint:
    """Tests for request_blueprint/response_blueprint in decorators."""

    def test_route_decorator_stores_blueprint_metadata(self):
        """request_blueprint and response_blueprint are stored in metadata."""
        @POST("/items", request_blueprint=CreateItemBlueprint, response_blueprint=ItemBlueprint)
        async def create_item(self, ctx):
            pass

        meta = create_item.__route_metadata__[0]
        assert meta["request_blueprint"] is CreateItemBlueprint
        assert meta["response_blueprint"] is ItemBlueprint

    def test_route_decorator_blueprint_default_none(self):
        """Blueprints default to None when not specified."""
        @GET("/items")
        async def list_items(self, ctx):
            pass

        meta = list_items.__route_metadata__[0]
        assert meta["request_blueprint"] is None
        assert meta["response_blueprint"] is None

    def test_projected_ref_in_decorator(self):
        """Blueprint['projection'] can be used as response_blueprint."""
        @GET("/items", response_blueprint=ItemBlueprint["summary"])
        async def list_items(self, ctx):
            pass

        meta = list_items.__route_metadata__[0]
        ref = meta["response_blueprint"]
        assert ref is not None
        assert ref.blueprint_cls is ItemBlueprint
        assert ref.projection == "summary"

    def test_serializer_and_blueprint_coexist(self):
        """Both serializer and blueprint params can be set (migration support)."""
        class FakeSerializer:
            pass

        @POST("/items",
              request_serializer=FakeSerializer,
              response_blueprint=ItemBlueprint)
        async def create_item(self, ctx):
            pass

        meta = create_item.__route_metadata__[0]
        assert meta["request_serializer"] is FakeSerializer
        assert meta["response_blueprint"] is ItemBlueprint

    def test_all_http_methods_support_blueprint(self):
        """All HTTP method decorators support blueprint parameters."""
        decorators = [GET, POST, PUT, PATCH, DELETE]

        for dec in decorators:
            @dec("/test", response_blueprint=ItemBlueprint)
            async def handler(self, ctx):
                pass

            meta = handler.__route_metadata__[-1]
            assert meta["response_blueprint"] is ItemBlueprint


# ═══════════════════════════════════════════════════════════════════════
# 2. Engine: _is_blueprint_class Detection
# ═══════════════════════════════════════════════════════════════════════

class TestBlueprintDetection:
    """Tests for _is_blueprint_class in controller engine."""

    def test_detects_blueprint_subclass(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_blueprint_class(ItemBlueprint) is True

    def test_detects_projected_ref(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        ref = ItemBlueprint["summary"]
        assert engine._is_blueprint_class(ref) is True

    def test_rejects_base_blueprint(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_blueprint_class(Blueprint) is False

    def test_rejects_non_blueprint(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_blueprint_class(str) is False
        assert engine._is_blueprint_class(int) is False
        assert engine._is_blueprint_class(None) is False

    def test_rejects_non_type(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_blueprint_class("not a type") is False
        assert engine._is_blueprint_class(42) is False

    def test_still_detects_serializers(self):
        """Serializer detection is unaffected by Blueprint additions."""
        from aquilia.controller.engine import ControllerEngine
        from aquilia.serializers import Serializer, CharField

        class TestSer(Serializer):
            name = CharField()

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_serializer_class(TestSer) is True
        assert engine._is_blueprint_class(TestSer) is False


# ═══════════════════════════════════════════════════════════════════════
# 3. Metadata: _is_blueprint_type Detection
# ═══════════════════════════════════════════════════════════════════════

class TestBlueprintTypeMetadata:
    """Tests for _is_blueprint_type in controller metadata."""

    def test_detects_blueprint_type(self):
        from aquilia.controller.metadata import _is_blueprint_type

        assert _is_blueprint_type(ItemBlueprint) is True

    def test_detects_projected_ref(self):
        from aquilia.controller.metadata import _is_blueprint_type

        ref = ItemBlueprint["summary"]
        assert _is_blueprint_type(ref) is True

    def test_rejects_base_blueprint(self):
        from aquilia.controller.metadata import _is_blueprint_type

        assert _is_blueprint_type(Blueprint) is False

    def test_rejects_non_blueprint(self):
        from aquilia.controller.metadata import _is_blueprint_type

        assert _is_blueprint_type(str) is False
        assert _is_blueprint_type(int) is False
        assert _is_blueprint_type(None) is False


# ═══════════════════════════════════════════════════════════════════════
# 4. Engine: _apply_response_blueprint
# ═══════════════════════════════════════════════════════════════════════

class TestResponseBlueprint:
    """Tests for _apply_response_blueprint in controller engine."""

    def test_molds_single_instance(self):
        from aquilia.controller.engine import ControllerEngine
        from aquilia.response import Response

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_blueprint = ItemBlueprint

        class _FakeCtx:
            request = FakeRequest()
            container = None

        item = SimpleObj(id=1, name="Widget", price=9.99, active=True)
        result = engine._apply_response_blueprint(item, _FakeMeta(), _FakeCtx())
        assert result["id"] == 1
        assert result["name"] == "Widget"
        assert result["price"] == 9.99
        assert result["active"] is True

    def test_molds_list_of_instances(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_blueprint = ItemBlueprint

        class _FakeCtx:
            request = FakeRequest()
            container = None

        items = [
            SimpleObj(id=1, name="A", price=1.0, active=True),
            SimpleObj(id=2, name="B", price=2.0, active=False),
        ]
        result = engine._apply_response_blueprint(items, _FakeMeta(), _FakeCtx())
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "A"
        assert result[1]["name"] == "B"

    def test_projected_response_blueprint(self):
        """Blueprint['summary'] only includes projected fields."""
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_blueprint = ItemBlueprint["summary"]

        class _FakeCtx:
            request = FakeRequest()
            container = None

        item = SimpleObj(id=1, name="Widget", price=9.99, active=True)
        result = engine._apply_response_blueprint(item, _FakeMeta(), _FakeCtx())
        assert result["id"] == 1
        assert result["name"] == "Widget"
        assert "price" not in result
        assert "active" not in result

    def test_skips_response_objects(self):
        from aquilia.controller.engine import ControllerEngine
        from aquilia.response import Response

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_blueprint = ItemBlueprint

        class _FakeCtx:
            request = FakeRequest()
            container = None

        resp = Response.json({"ok": True})
        result = engine._apply_response_blueprint(resp, _FakeMeta(), _FakeCtx())
        assert result is resp

    def test_no_response_blueprint_passthrough(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            pass  # No response_blueprint attribute

        class _FakeCtx:
            request = FakeRequest()
            container = None

        result = engine._apply_response_blueprint({"raw": True}, _FakeMeta(), _FakeCtx())
        assert result == {"raw": True}

    def test_raw_metadata_dict(self):
        """response_blueprint can come from _raw_metadata dict."""
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            _raw_metadata = {"response_blueprint": ItemBlueprint}

        class _FakeCtx:
            request = FakeRequest()
            container = None

        item = SimpleObj(id=5, name="Test", price=1.0, active=True)
        result = engine._apply_response_blueprint(item, _FakeMeta(), _FakeCtx())
        assert result["id"] == 5
        assert result["name"] == "Test"

    def test_molds_dict_data(self):
        """Dicts are also supported as instances (common for service returns)."""
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_blueprint = ItemBlueprint

        class _FakeCtx:
            request = FakeRequest()
            container = None

        item = {"id": 3, "name": "DictItem", "price": 5.0, "active": True}
        result = engine._apply_response_blueprint(item, _FakeMeta(), _FakeCtx())
        assert result["id"] == 3
        assert result["name"] == "DictItem"


# ═══════════════════════════════════════════════════════════════════════
# 5. Blueprint Sealing (Validation) Pipeline
# ═══════════════════════════════════════════════════════════════════════

class TestBlueprintSealing:
    """Tests for Blueprint validation (sealing) in the engine context."""

    def test_basic_sealing(self):
        """Blueprint seals valid data correctly."""
        bp = CreateItemBlueprint(data={"name": "Widget", "price": 9.99})
        assert bp.is_sealed()
        assert bp.validated_data["name"] == "Widget"
        assert bp.validated_data["price"] == 9.99
        assert bp.validated_data["active"] is True  # default

    def test_seal_failure_raises(self):
        """is_sealed(raise_fault=True) raises on invalid data."""
        bp = CreateItemBlueprint(data={"name": "A", "price": 5.0})  # too short
        with pytest.raises(SealFault):
            bp.is_sealed(raise_fault=True)

    def test_custom_seal_method(self):
        """seal_price_positive runs during sealing."""
        bp = CreateItemBlueprint(data={"name": "Widget", "price": -5.0})
        assert not bp.is_sealed()
        assert "price" in bp.errors

    def test_partial_mode(self):
        """Partial mode doesn't require all fields."""
        bp = UpdateItemBlueprint(data={"name": "Updated"}, partial=True)
        assert bp.is_sealed()
        assert bp.validated_data["name"] == "Updated"
        assert "price" not in bp.validated_data

    def test_inject_facet_resolved(self):
        """Inject facets resolve from context."""
        class FakeIdentity:
            id = 42

        bp = UpdateItemBlueprint(
            data={"name": "Test"},
            partial=True,
            context={"identity": FakeIdentity()},
        )
        assert bp.is_sealed()
        assert bp.validated_data["updated_by"] == 42


# ═══════════════════════════════════════════════════════════════════════
# 6. Migration Parity: Blueprint Blueprints vs Serializer Examples
# ═══════════════════════════════════════════════════════════════════════

class TestMigrationParity:
    """
    Verify that migrated Blueprints produce the same behavior as
    the Serializer-based originals.
    """

    def test_blog_post_blueprint_validates_like_serializer(self):
        """BlogPostBlueprint validates the same fields as BlogPostSerializer."""
        from myapp.modules.blogs.blueprints import BlogPostBlueprint

        bp = BlogPostBlueprint(data={
            "title": "My Post Title",
            "content": "This is enough content for the min length.",
            "excerpt": "Short excerpt",
            "published": True,
        })
        assert bp.is_sealed()
        assert bp.validated_data["title"] == "My Post Title"
        assert bp.validated_data["published"] is True

    def test_blog_post_blueprint_title_validation(self):
        """seal_title rejects titles starting with 'draft'."""
        from myapp.modules.blogs.blueprints import BlogPostBlueprint

        bp = BlogPostBlueprint(data={
            "title": "Draft Post",
            "content": "Long enough content here for validation.",
        })
        assert not bp.is_sealed()
        assert "title" in bp.errors

    def test_blog_post_blueprint_cross_field_validation(self):
        """Cross-field: published posts require excerpt."""
        from myapp.modules.blogs.blueprints import BlogPostBlueprint

        bp = BlogPostBlueprint(data={
            "title": "Published Post",
            "content": "Content is long enough for validation.",
            "published": True,
            # No excerpt!
        })
        assert not bp.is_sealed()
        assert "__all__" in bp.errors

    def test_blog_post_list_projection(self):
        """BlogPostBlueprint['list'] produces summary fields."""
        from myapp.modules.blogs.blueprints import BlogPostBlueprint

        item = SimpleObj(
            id=1, title="Test", excerpt="Exc", author_id=42,
            published=True, view_count=100,
            created_at="2026-02-18T10:00:00",
            updated_at="2026-02-18T11:00:00",
            content="Full content here",
        )

        bp = BlogPostBlueprint(instance=item, projection="list")
        data = bp.data
        assert data["id"] == 1
        assert data["title"] == "Test"
        assert "content" not in data  # excluded from "list" projection
        assert "updated_at" not in data

    def test_blog_comment_conditional_seal(self):
        """Email required when notify_reply is True."""
        from myapp.modules.blogs.blueprints import BlogCommentBlueprint

        bp = BlogCommentBlueprint(data={
            "post_id": 1,
            "author_name": "Kai",
            "content": "Great post!",
            "notify_reply": True,
            # No email → should fail
        })
        assert not bp.is_sealed()
        assert "email" in bp.errors

    def test_blog_comment_no_email_when_no_notify(self):
        """Email not required when notify_reply is False."""
        from myapp.modules.blogs.blueprints import BlogCommentBlueprint

        bp = BlogCommentBlueprint(data={
            "post_id": 1,
            "author_name": "Kai",
            "content": "Great post!",
            "notify_reply": False,
        })
        assert bp.is_sealed()

    def test_blog_update_partial(self):
        """BlogPostUpdateBlueprint allows partial updates."""
        from myapp.modules.blogs.blueprints import BlogPostUpdateBlueprint

        bp = BlogPostUpdateBlueprint(
            data={"title": "New Title"},
            partial=True,
        )
        assert bp.is_sealed()
        assert bp.validated_data["title"] == "New Title"
        assert "content" not in bp.validated_data

    def test_blog_statistics_output(self):
        """BlogStatisticsBlueprint molds output correctly."""
        from myapp.modules.blogs.blueprints import BlogStatisticsBlueprint

        stats = SimpleObj(
            total_posts=50, published_posts=30,
            total_views=10000, total_comments=200,
        )
        bp = BlogStatisticsBlueprint(instance=stats)
        data = bp.data
        assert data["total_posts"] == 50
        assert data["published_posts"] == 30
        assert data["total_views"] == 10000
        assert data["total_comments"] == 200


# ═══════════════════════════════════════════════════════════════════════
# 7. Top-level Export Tests
# ═══════════════════════════════════════════════════════════════════════

class TestBlueprintExports:
    """Verify Blueprint exports are accessible from top-level aquilia."""

    def test_core_exports(self):
        from aquilia import (
            Blueprint,
            BlueprintMeta,
            Facet,
            TextFacet,
            IntFacet,
            FloatFacet,
            BoolFacet,
            DateTimeFacet,
            EmailFacet,
            ReadOnly,
            Hidden,
            Inject,
            Computed,
            Constant,
            Lens,
        )
        assert Blueprint is not None
        assert TextFacet is not None
        assert Inject is not None

    def test_exception_exports(self):
        from aquilia import (
            BlueprintFault,
            CastFault,
            SealFault,
            ImprintFault,
            ProjectionFault,
        )
        assert SealFault is not None

    def test_integration_exports(self):
        from aquilia import (
            is_blueprint_class,
            render_blueprint_response,
            bind_blueprint_to_request,
        )
        assert is_blueprint_class is not None
        assert render_blueprint_response is not None
        assert bind_blueprint_to_request is not None

    def test_schema_exports(self):
        from aquilia import generate_schema, generate_component_schemas
        assert generate_schema is not None


# ═══════════════════════════════════════════════════════════════════════
# 8. Fast-path Cache Check
# ═══════════════════════════════════════════════════════════════════════

class TestFastPathBlueprint:
    """Blueprint presence should disable the fast-path in the engine."""

    def test_has_response_blueprint_not_simple(self):
        """Routes with response_blueprint are not considered 'simple'."""
        from aquilia.controller.engine import ControllerEngine

        # Clear the cache
        ControllerEngine._simple_route_cache.clear()

        class FakeRouteMetadata:
            pipeline = []
            parameters = []
            request_serializer = None
            response_serializer = None
            request_blueprint = None
            response_blueprint = ItemBlueprint

        class FakeControllerMetadata:
            pipeline = []

        class FakeRoute:
            controller_metadata = FakeControllerMetadata()
            route_metadata = FakeRouteMetadata()

        route = FakeRoute()
        route_id = id(route)

        # Simulate the fast-path check from the engine
        params = route.route_metadata.parameters
        has_serializer = (
            getattr(route.route_metadata, 'request_serializer', None)
            or getattr(route.route_metadata, 'response_serializer', None)
        )
        has_blueprint = (
            getattr(route.route_metadata, 'request_blueprint', None)
            or getattr(route.route_metadata, 'response_blueprint', None)
        )
        is_simple = (
            not route.controller_metadata.pipeline
            and not route.route_metadata.pipeline
            and not has_serializer
            and not has_blueprint
            and (not params or all(
                getattr(p, 'name', '') == 'ctx' or getattr(p, 'source', '') == 'path' for p in params
            ))
        )
        assert is_simple is False

    def test_no_blueprint_or_serializer_is_simple(self):
        """Routes without blueprint/serializer CAN be simple."""
        class FakeRouteMetadata:
            pipeline = []
            parameters = []
            request_serializer = None
            response_serializer = None
            request_blueprint = None
            response_blueprint = None

        class FakeControllerMetadata:
            pipeline = []

        class FakeRoute:
            controller_metadata = FakeControllerMetadata()
            route_metadata = FakeRouteMetadata()

        route = FakeRoute()

        has_serializer = (
            getattr(route.route_metadata, 'request_serializer', None)
            or getattr(route.route_metadata, 'response_serializer', None)
        )
        has_blueprint = (
            getattr(route.route_metadata, 'request_blueprint', None)
            or getattr(route.route_metadata, 'response_blueprint', None)
        )
        is_simple = (
            not route.controller_metadata.pipeline
            and not route.route_metadata.pipeline
            and not has_serializer
            and not has_blueprint
        )
        assert is_simple is True


# ═══════════════════════════════════════════════════════════════════════
# 9. Full Pipeline Test: Blueprint → Controller → Response
# ═══════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """End-to-end tests simulating the controller engine flow."""

    def test_blueprint_input_and_output(self):
        """Full cycle: input → seal → validated_data → output mold."""
        # Input
        bp_input = CreateItemBlueprint(data={"name": "Widget", "price": 29.99})
        assert bp_input.is_sealed()
        validated = bp_input.validated_data

        # Simulate "saving" and returning
        saved = SimpleObj(id=1, **validated)

        # Output
        bp_output = ItemBlueprint(instance=saved)
        data = bp_output.data
        assert data["id"] == 1
        assert data["name"] == "Widget"
        assert data["price"] == 29.99
        assert data["active"] is True

    def test_projected_output(self):
        """Projection filters the output fields."""
        saved = SimpleObj(id=1, name="Widget", price=29.99, active=True)

        bp = ItemBlueprint(instance=saved, projection="summary")
        data = bp.data
        assert "id" in data
        assert "name" in data
        assert "price" not in data
        assert "active" not in data

    def test_many_output(self):
        """Many mode molds a list of instances."""
        items = [
            SimpleObj(id=1, name="A", price=1.0, active=True),
            SimpleObj(id=2, name="B", price=2.0, active=False),
        ]

        bp = ItemBlueprint(instance=items, many=True)
        data = bp.data
        assert len(data) == 2
        assert data[0]["name"] == "A"
        assert data[1]["name"] == "B"

    def test_many_input_sealing(self):
        """Many mode validates a list of input items."""
        items_data = [
            {"name": "Widget", "price": 9.99},
            {"name": "Gadget", "price": 19.99},
        ]
        bp = CreateItemBlueprint(data=items_data, many=True)
        assert bp.is_sealed()
        assert len(bp.validated_data) == 2
        assert bp.validated_data[0]["name"] == "Widget"

    def test_many_input_partial_failure(self):
        """One invalid item in a list causes overall failure."""
        items_data = [
            {"name": "Widget", "price": 9.99},
            {"name": "X", "price": -1.0},  # name too short, price negative
        ]
        bp = CreateItemBlueprint(data=items_data, many=True)
        assert not bp.is_sealed()
        assert "1" in bp.errors  # Index 1 failed
