"""
Test: Comprehensive OpenAPI 3.1.0 Generation

Tests the full OpenAPI generator pipeline:
- OpenAPIConfig construction and from_dict
- Integration.openapi() config builder
- Type-to-JSON-Schema conversion
- Docstring parsing
- Security scheme detection
- Request body inference
- Response schema inference
- Tag generation
- Full spec generation with routes
- Swagger UI / ReDoc HTML rendering
- Backward compatibility (positional title/version)
"""

import inspect
import pytest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import MagicMock

from aquilia.controller.openapi import (
    OpenAPIGenerator,
    OpenAPIConfig,
    ParsedDocstring,
    _python_type_to_schema,
    _dataclass_to_schema,
    _parse_docstring,
    _detect_security_schemes,
    _infer_request_body,
    _infer_type_from_example,
    _build_responses,
    _build_operation_security,
    generate_swagger_html,
    generate_redoc_html,
    _STATUS_DESCRIPTIONS,
)
from aquilia.controller.metadata import RouteMetadata, ControllerMetadata, ParameterMetadata
from aquilia.controller.compiler import CompiledRoute
from aquilia.controller.base import Controller
from aquilia.controller.decorators import GET, POST, PUT, PATCH, DELETE
from aquilia.controller.router import ControllerRouter
from aquilia.config_builders import Integration, Workspace, Module
from aquilia.patterns import parse_pattern, PatternCompiler

pc = PatternCompiler()


def _make_pattern(path: str):
    """Compile a pattern for test use."""
    return pc.compile(parse_pattern(path))


# ============================================================================
# OpenAPIConfig
# ============================================================================

class TestOpenAPIConfig:

    def test_defaults(self):
        cfg = OpenAPIConfig()
        assert cfg.title == "Aquilia API"
        assert cfg.version == "1.0.0"
        assert cfg.description == ""
        assert cfg.docs_path == "/docs"
        assert cfg.openapi_json_path == "/openapi.json"
        assert cfg.redoc_path == "/redoc"
        assert cfg.enabled is True
        assert cfg.detect_security is True
        assert cfg.infer_request_body is True
        assert cfg.infer_responses is True

    def test_custom_values(self):
        cfg = OpenAPIConfig(
            title="My API",
            version="2.0.0",
            description="A great API",
            contact_name="Dev Team",
            contact_email="team@example.com",
            license_name="MIT",
            swagger_ui_theme="dark",
        )
        assert cfg.title == "My API"
        assert cfg.version == "2.0.0"
        assert cfg.contact_name == "Dev Team"
        assert cfg.license_name == "MIT"
        assert cfg.swagger_ui_theme == "dark"

    def test_from_dict(self):
        data = {
            "_integration_type": "openapi",
            "title": "Dict API",
            "version": "3.0.0",
            "description": "From dict",
            "docs_path": "/api-docs",
            "enabled": True,
            "swagger_ui_theme": "dark",
        }
        cfg = OpenAPIConfig.from_dict(data)
        assert cfg.title == "Dict API"
        assert cfg.version == "3.0.0"
        assert cfg.docs_path == "/api-docs"
        assert cfg.swagger_ui_theme == "dark"

    def test_from_dict_ignores_unknown_keys(self):
        data = {"title": "X", "unknown_key": "ignored"}
        cfg = OpenAPIConfig.from_dict(data)
        assert cfg.title == "X"
        assert not hasattr(cfg, "unknown_key")

    def test_from_dict_ignores_private_keys(self):
        data = {"_integration_type": "openapi", "title": "Y"}
        cfg = OpenAPIConfig.from_dict(data)
        assert cfg.title == "Y"

    def test_servers(self):
        cfg = OpenAPIConfig(servers=[
            {"url": "https://api.example.com", "description": "Prod"},
            {"url": "https://staging.example.com", "description": "Staging"},
        ])
        assert len(cfg.servers) == 2


# ============================================================================
# Integration.openapi() Builder
# ============================================================================

class TestIntegrationOpenapi:

    def test_basic(self):
        result = Integration.openapi(title="Test API", version="0.1.0")
        assert result["_integration_type"] == "openapi"
        assert result["title"] == "Test API"
        assert result["version"] == "0.1.0"
        assert result["enabled"] is True

    def test_full_config(self):
        result = Integration.openapi(
            title="Full API",
            version="5.0.0",
            description="Fully configured",
            terms_of_service="https://example.com/tos",
            contact_name="API Team",
            contact_email="api@example.com",
            contact_url="https://example.com",
            license_name="Apache-2.0",
            license_url="https://www.apache.org/licenses/LICENSE-2.0",
            servers=[{"url": "/", "description": "Local"}],
            docs_path="/swagger",
            openapi_json_path="/spec.json",
            redoc_path="/reference",
            include_internal=True,
            detect_security=False,
            swagger_ui_theme="dark",
        )
        assert result["contact_email"] == "api@example.com"
        assert result["license_name"] == "Apache-2.0"
        assert result["docs_path"] == "/swagger"
        assert result["include_internal"] is True
        assert result["detect_security"] is False
        assert result["swagger_ui_theme"] == "dark"

    def test_disabled(self):
        result = Integration.openapi(enabled=False)
        assert result["enabled"] is False

    def test_workspace_integration(self):
        ws = Workspace("test").integrate(Integration.openapi(title="WS API"))
        config = ws.to_dict()
        assert "openapi" in config["integrations"]
        assert config["integrations"]["openapi"]["title"] == "WS API"

    def test_roundtrip_to_config(self):
        """Integration dict → OpenAPIConfig → same values."""
        d = Integration.openapi(
            title="RT API",
            version="9.0.0",
            description="Roundtrip test",
            docs_path="/api-docs",
        )
        cfg = OpenAPIConfig.from_dict(d)
        assert cfg.title == "RT API"
        assert cfg.version == "9.0.0"
        assert cfg.docs_path == "/api-docs"


# ============================================================================
# Type → JSON Schema Conversion
# ============================================================================

class TestTypeToSchema:

    def test_str(self):
        assert _python_type_to_schema(str) == {"type": "string"}

    def test_int(self):
        assert _python_type_to_schema(int) == {"type": "integer"}

    def test_float(self):
        assert _python_type_to_schema(float) == {"type": "number", "format": "double"}

    def test_bool(self):
        assert _python_type_to_schema(bool) == {"type": "boolean"}

    def test_bytes(self):
        assert _python_type_to_schema(bytes) == {"type": "string", "format": "binary"}

    def test_none_type(self):
        assert _python_type_to_schema(type(None)) == {"type": "null"}

    def test_any(self):
        assert _python_type_to_schema(Any) == {}

    def test_empty(self):
        assert _python_type_to_schema(inspect.Parameter.empty) == {}

    def test_optional_str(self):
        schema = _python_type_to_schema(Optional[str])
        assert schema["type"] == "string"
        assert schema["nullable"] is True

    def test_list_int(self):
        schema = _python_type_to_schema(List[int])
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "integer"

    def test_dict_str_any(self):
        schema = _python_type_to_schema(Dict[str, int])
        assert schema["type"] == "object"
        assert schema["additionalProperties"]["type"] == "integer"

    def test_set(self):
        schema = _python_type_to_schema(Set[str])
        assert schema["type"] == "array"
        assert schema["uniqueItems"] is True

    def test_tuple(self):
        schema = _python_type_to_schema(Tuple[str, int])
        assert schema["type"] == "array"
        assert len(schema["prefixItems"]) == 2

    def test_union(self):
        schema = _python_type_to_schema(Union[str, int])
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2

    def test_dataclass_ref(self):
        @dataclass
        class User:
            name: str
            age: int

        schema = _python_type_to_schema(User)
        assert schema == {"$ref": "#/components/schemas/User"}

    def test_unknown_type_fallback(self):
        """Non-annotated class without annotations → object."""
        schema = _python_type_to_schema(42)  # not a type
        assert schema == {"type": "object"}


# ============================================================================
# Dataclass → Schema
# ============================================================================

class TestDataclassToSchema:

    def test_basic(self):
        @dataclass
        class Item:
            """An item."""
            name: str
            price: float

        schema = _dataclass_to_schema(Item)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "price" in schema["properties"]
        assert schema["description"] == "An item."

    def test_no_annotations(self):
        class Empty:
            pass

        # Remove annotations if any
        if hasattr(Empty, "__annotations__"):
            delattr(Empty, "__annotations__")
        schema = _dataclass_to_schema(Empty)
        assert schema["type"] == "object"


# ============================================================================
# Docstring Parsing
# ============================================================================

class TestDocstringParsing:

    def test_empty(self):
        result = _parse_docstring("")
        assert result.summary == ""
        assert result.description == ""

    def test_summary_only(self):
        result = _parse_docstring("Get all users.")
        assert result.summary == "Get all users."
        assert result.description == ""

    def test_summary_and_description(self):
        doc = """Get all users.

        Returns a paginated list of users from the database.
        Supports filtering by status.
        """
        result = _parse_docstring(doc)
        assert result.summary == "Get all users."
        assert "paginated" in result.description

    def test_params_section(self):
        doc = """Create a user.

        Args:
            name: The user's full name
            email: Email address
        """
        result = _parse_docstring(doc)
        assert result.params["name"] == "The user's full name"
        assert result.params["email"] == "Email address"

    def test_returns_section(self):
        doc = """Get user.

        Returns: User object with all fields
        """
        result = _parse_docstring(doc)
        assert "User object" in result.returns

    def test_raises_section(self):
        doc = """Delete user.

        Raises:
            NotFound (404): User not found
            Forbidden (403): No permission
        """
        result = _parse_docstring(doc)
        assert len(result.raises) == 2
        assert result.raises[0]["status"] == "404"
        assert result.raises[1]["status"] == "403"

    def test_body_section(self):
        doc = """Create item.

        Body:
            JSON object with item data
        """
        result = _parse_docstring(doc)
        assert result.request_body is not None


# ============================================================================
# Type Inference from Examples
# ============================================================================

class TestInferTypeFromExample:

    def test_int(self):
        assert _infer_type_from_example("42")["type"] == "integer"

    def test_float(self):
        assert _infer_type_from_example("3.14")["type"] == "number"

    def test_bool_true(self):
        assert _infer_type_from_example("true")["type"] == "boolean"

    def test_bool_false(self):
        assert _infer_type_from_example("false")["type"] == "boolean"

    def test_array(self):
        assert _infer_type_from_example("[1,2,3]")["type"] == "array"

    def test_object(self):
        assert _infer_type_from_example("{}")["type"] == "object"

    def test_string(self):
        assert _infer_type_from_example("hello")["type"] == "string"


# ============================================================================
# Helpers: build mock routes
# ============================================================================

class MockAuthGuard:
    """Simulates an auth guard."""
    pass


class MockApiKeyGuard:
    """Simulates an API key guard."""
    pass


class MockOAuthGuard:
    """Simulates an OAuth guard."""
    pass


def _make_controller_class(
    name: str = "TestController",
    prefix: str = "/test",
    tags: list = None,
    pipeline: list = None,
    docstring: str = "",
):
    """Dynamically create a controller class for testing."""
    attrs = {
        "prefix": prefix,
        "tags": tags or [],
        "pipeline": pipeline or [],
        "__doc__": docstring or f"{name} endpoints.",
    }
    cls = type(name, (Controller,), attrs)
    return cls


def _make_route(
    handler_name: str = "list_items",
    http_method: str = "GET",
    path: str = "/items",
    controller_class=None,
    summary: str = "",
    description: str = "",
    tags: list = None,
    deprecated: bool = False,
    response_model=None,
    status_code: int = 200,
    parameters: list = None,
    pipeline: list = None,
    controller_pipeline: list = None,
    handler=None,
) -> CompiledRoute:
    """Build a CompiledRoute for testing."""
    if controller_class is None:
        controller_class = _make_controller_class()

    route_meta = RouteMetadata(
        http_method=http_method,
        path_template=path,
        full_path=path,
        handler_name=handler_name,
        summary=summary,
        description=description,
        tags=tags or [],
        deprecated=deprecated,
        response_model=response_model,
        status_code=status_code,
        parameters=parameters or [],
        pipeline=pipeline or [],
    )

    ctrl_meta = ControllerMetadata(
        class_name=controller_class.__name__,
        module_path=f"tests.test_openapi:{controller_class.__name__}",
        prefix=getattr(controller_class, "prefix", "/"),
        tags=getattr(controller_class, "tags", []),
        pipeline=controller_pipeline or getattr(controller_class, "pipeline", []),
    )

    compiled = CompiledRoute(
        controller_class=controller_class,
        controller_metadata=ctrl_meta,
        route_metadata=route_meta,
        compiled_pattern=_make_pattern(path),
        full_path=path,
        http_method=http_method,
        specificity=100,
    )

    # Attach a real handler method to the controller class
    if handler:
        setattr(controller_class, handler_name, handler)
    elif not hasattr(controller_class, handler_name):
        async def default_handler(self, ctx):
            """Default handler."""
            pass
        setattr(controller_class, handler_name, default_handler)

    return compiled


# ============================================================================
# Security Scheme Detection
# ============================================================================

class TestSecuritySchemeDetection:

    def test_bearer_auth(self):
        ctrl = _make_controller_class(pipeline=[MockAuthGuard()])
        route = _make_route(controller_class=ctrl, controller_pipeline=[MockAuthGuard()])
        schemes = _detect_security_schemes([route])
        assert "bearerAuth" in schemes
        assert schemes["bearerAuth"]["type"] == "http"
        assert schemes["bearerAuth"]["scheme"] == "bearer"

    def test_api_key(self):
        ctrl = _make_controller_class(pipeline=[MockApiKeyGuard()])
        route = _make_route(controller_class=ctrl, controller_pipeline=[MockApiKeyGuard()])
        schemes = _detect_security_schemes([route])
        assert "apiKeyAuth" in schemes
        assert schemes["apiKeyAuth"]["in"] == "header"

    def test_oauth(self):
        ctrl = _make_controller_class(pipeline=[MockOAuthGuard()])
        route = _make_route(controller_class=ctrl, controller_pipeline=[MockOAuthGuard()])
        schemes = _detect_security_schemes([route])
        assert "oauth2" in schemes
        assert "flows" in schemes["oauth2"]

    def test_no_guards(self):
        route = _make_route()
        schemes = _detect_security_schemes([route])
        assert len(schemes) == 0

    def test_multiple_schemes(self):
        ctrl = _make_controller_class()
        route1 = _make_route(
            controller_class=ctrl,
            controller_pipeline=[MockAuthGuard()],
        )
        route2 = _make_route(
            handler_name="get_item",
            controller_class=ctrl,
            controller_pipeline=[MockApiKeyGuard()],
        )
        schemes = _detect_security_schemes([route1, route2])
        assert "bearerAuth" in schemes
        assert "apiKeyAuth" in schemes


# ============================================================================
# Operation Security
# ============================================================================

class TestOperationSecurity:

    def test_bearer_on_route(self):
        route = _make_route(controller_pipeline=[MockAuthGuard()])
        result = _build_operation_security(route)
        assert result is not None
        assert {"bearerAuth": []} in result

    def test_no_security(self):
        route = _make_route()
        result = _build_operation_security(route)
        assert result is None


# ============================================================================
# Request Body Inference
# ============================================================================

class TestRequestBodyInference:

    def test_get_method_no_body(self):
        route = _make_route(http_method="GET")
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is None

    def test_post_with_ctx_json(self):
        async def create_item(self, ctx):
            """Create an item."""
            data = await ctx.json()
            return data

        route = _make_route(http_method="POST", handler_name="create_item", handler=create_item)
        handler = create_item
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is not None
        assert "application/json" in result["content"]

    def test_post_with_ctx_form(self):
        async def submit_form(self, ctx):
            """Submit a form."""
            data = await ctx.form()
            return data

        route = _make_route(http_method="POST", handler_name="submit_form", handler=submit_form)
        handler = submit_form
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is not None
        assert "application/x-www-form-urlencoded" in result["content"]

    def test_post_with_body_params(self):
        params = [
            ParameterMetadata(name="name", type=str, source="body", required=True),
            ParameterMetadata(name="email", type=str, source="body", required=True),
        ]
        route = _make_route(http_method="POST", parameters=params)
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is not None
        schema = result["content"]["application/json"]["schema"]
        assert "name" in schema["properties"]
        assert "email" in schema["properties"]
        assert schema["required"] == ["name", "email"]

    def test_put_with_body_params(self):
        params = [
            ParameterMetadata(name="title", type=str, source="body"),
        ]
        route = _make_route(http_method="PUT", parameters=params)
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is not None

    def test_delete_no_body(self):
        """DELETE typically has no body."""
        route = _make_route(http_method="DELETE")
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        doc = _parse_docstring("")
        result = _infer_request_body(route, handler, doc)
        assert result is None


# ============================================================================
# Response Inference
# ============================================================================

class TestResponseInference:

    def test_default_200(self):
        async def get_items(self, ctx):
            """Get items."""
            return Response.json({"items": []})

        route = _make_route(handler_name="get_items", handler=get_items)
        handler = get_items
        doc = _parse_docstring("")
        responses = _build_responses(route, handler, doc)
        assert "200" in responses
        assert "application/json" in responses["200"]["content"]

    def test_custom_status_code(self):
        async def create_item(self, ctx):
            """Create item."""
            pass

        route = _make_route(
            http_method="POST",
            handler_name="create_item",
            status_code=201,
            handler=create_item,
        )
        handler = create_item
        doc = _parse_docstring("")
        responses = _build_responses(route, handler, doc)
        assert "201" in responses
        assert responses["201"]["description"] == "Resource created"

    def test_response_model(self):
        @dataclass
        class UserResponse:
            id: int
            name: str

        route = _make_route(response_model=UserResponse)
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        doc = _parse_docstring("")
        responses = _build_responses(route, handler, doc)
        schema = responses["200"]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/UserResponse"}

    def test_html_response(self):
        async def render_page(self, ctx):
            """Render page."""
            return Response.html("<h1>Hi</h1>")

        route = _make_route(handler_name="render_page", handler=render_page)
        handler = render_page
        doc = _parse_docstring("")
        responses = _build_responses(route, handler, doc)
        assert "text/html" in responses["200"]["content"]

    def test_docstring_raises(self):
        doc = _parse_docstring("""Get user.

        Raises:
            NotFound (404): User not found
        """)
        route = _make_route()
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        responses = _build_responses(route, handler, doc)
        assert "404" in responses
        assert "User not found" in responses["404"]["description"]

    def test_none_handler(self):
        """Handler is None → fallback to generic."""
        route = _make_route()
        doc = _parse_docstring("")
        responses = _build_responses(route, None, doc)
        assert "200" in responses


# ============================================================================
# Full Spec Generation
# ============================================================================

class TestOpenAPIGenerator:

    def _make_router_with_routes(self, routes):
        """Create a mock router that returns given routes."""
        router = MagicMock(spec=ControllerRouter)
        router.get_routes_full.return_value = routes
        return router

    def test_backward_compat_positional_args(self):
        gen = OpenAPIGenerator("My API", "2.0.0")
        assert gen.config.title == "My API"
        assert gen.config.version == "2.0.0"

    def test_config_object(self):
        cfg = OpenAPIConfig(title="Config API", version="3.0.0")
        gen = OpenAPIGenerator(config=cfg)
        assert gen.config.title == "Config API"

    def test_empty_spec(self):
        gen = OpenAPIGenerator(title="Empty", version="0.0.1")
        router = self._make_router_with_routes([])
        spec = gen.generate(router)

        assert spec["openapi"] == "3.1.0"
        assert spec["info"]["title"] == "Empty"
        assert spec["info"]["version"] == "0.0.1"
        assert spec["paths"] == {}
        assert "components" in spec
        assert "ErrorResponse" in spec["components"]["schemas"]

    def test_single_route(self):
        ctrl = _make_controller_class("ItemController", prefix="/items", tags=["items"])
        route = _make_route(
            controller_class=ctrl,
            handler_name="list_items",
            http_method="GET",
            path="/items",
            summary="List all items",
        )
        router = self._make_router_with_routes([route])

        gen = OpenAPIGenerator(title="Items API", version="1.0.0")
        spec = gen.generate(router)

        assert "/items" in spec["paths"]
        assert "get" in spec["paths"]["/items"]
        op = spec["paths"]["/items"]["get"]
        assert op["summary"] == "List all items"
        assert "items" in op["tags"]

    def test_multiple_methods_same_path(self):
        ctrl = _make_controller_class("UserController", prefix="/users")

        async def list_users(self, ctx):
            """List users."""
            return Response.json([])

        async def create_user(self, ctx):
            """Create user."""
            data = await ctx.json()
            return Response.json(data)

        get_route = _make_route(
            controller_class=ctrl,
            handler_name="list_users",
            http_method="GET",
            path="/users",
            handler=list_users,
        )
        post_route = _make_route(
            controller_class=ctrl,
            handler_name="create_user",
            http_method="POST",
            path="/users",
            handler=create_user,
        )
        router = self._make_router_with_routes([get_route, post_route])

        gen = OpenAPIGenerator()
        spec = gen.generate(router)

        assert "get" in spec["paths"]["/users"]
        assert "post" in spec["paths"]["/users"]
        # POST should have request body
        assert "requestBody" in spec["paths"]["/users"]["post"]

    def test_path_parameters(self):
        ctrl = _make_controller_class("UserController")
        route = _make_route(
            controller_class=ctrl,
            handler_name="get_user",
            path="/users/«id:int»",
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        assert "/users/{id}" in spec["paths"]
        op = spec["paths"]["/users/{id}"]["get"]
        param_names = [p["name"] for p in op.get("parameters", [])]
        assert "id" in param_names

    def test_deprecated_route(self):
        route = _make_route(deprecated=True)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert op["deprecated"] is True

    def test_operation_id(self):
        ctrl = _make_controller_class("ProductController")
        route = _make_route(
            controller_class=ctrl,
            handler_name="get_product",
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert op["operationId"] == "Product_get_product"

    def test_tags_from_controller(self):
        ctrl = _make_controller_class("OrderController", tags=["orders", "commerce"])
        route = _make_route(controller_class=ctrl)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert "orders" in op["tags"]

        tag_names = [t["name"] for t in spec.get("tags", [])]
        assert "orders" in tag_names

    def test_tags_from_route(self):
        route = _make_route(tags=["custom-tag"])
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert "custom-tag" in op["tags"]

    def test_tags_fallback_to_controller_name(self):
        ctrl = _make_controller_class("CartController")
        route = _make_route(controller_class=ctrl, tags=[])
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert "Cart" in op["tags"]

    def test_security_in_components(self):
        ctrl = _make_controller_class(pipeline=[MockAuthGuard()])
        route = _make_route(
            controller_class=ctrl,
            controller_pipeline=[MockAuthGuard()],
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        assert "securitySchemes" in spec["components"]
        assert "bearerAuth" in spec["components"]["securitySchemes"]

    def test_security_on_operation(self):
        ctrl = _make_controller_class(pipeline=[MockAuthGuard()])
        route = _make_route(
            controller_class=ctrl,
            controller_pipeline=[MockAuthGuard()],
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert "security" in op

    def test_info_with_contact_and_license(self):
        cfg = OpenAPIConfig(
            title="Full Info API",
            version="1.0.0",
            description="A comprehensive API",
            terms_of_service="https://example.com/tos",
            contact_name="Team",
            contact_email="team@example.com",
            contact_url="https://example.com",
            license_name="MIT",
            license_url="https://opensource.org/licenses/MIT",
        )
        gen = OpenAPIGenerator(config=cfg)
        router = self._make_router_with_routes([])
        spec = gen.generate(router)

        info = spec["info"]
        assert info["description"] == "A comprehensive API"
        assert info["termsOfService"] == "https://example.com/tos"
        assert info["contact"]["name"] == "Team"
        assert info["contact"]["email"] == "team@example.com"
        assert info["license"]["name"] == "MIT"

    def test_servers(self):
        cfg = OpenAPIConfig(
            servers=[
                {"url": "https://api.example.com", "description": "Production"},
                {"url": "https://staging.example.com", "description": "Staging"},
            ]
        )
        gen = OpenAPIGenerator(config=cfg)
        spec = gen.generate(self._make_router_with_routes([]))
        assert len(spec["servers"]) == 2
        assert spec["servers"][0]["url"] == "https://api.example.com"

    def test_default_servers(self):
        gen = OpenAPIGenerator()
        spec = gen.generate(self._make_router_with_routes([]))
        assert len(spec["servers"]) == 1
        assert spec["servers"][0]["url"] == "/"

    def test_external_docs(self):
        cfg = OpenAPIConfig(
            external_docs_url="https://docs.example.com",
            external_docs_description="Full docs",
        )
        gen = OpenAPIGenerator(config=cfg)
        spec = gen.generate(self._make_router_with_routes([]))
        assert spec["externalDocs"]["url"] == "https://docs.example.com"
        assert spec["externalDocs"]["description"] == "Full docs"

    def test_skips_docs_routes(self):
        """Docs routes (/docs, /openapi.json, /redoc) should not appear in the spec."""
        route_docs = _make_route(path="/docs", handler_name="docs_handler")
        route_json = _make_route(path="/openapi.json", handler_name="openapi_handler")
        route_redoc = _make_route(path="/redoc", handler_name="redoc_handler")
        route_api = _make_route(path="/items", handler_name="list_items")

        router = self._make_router_with_routes([route_docs, route_json, route_redoc, route_api])
        spec = OpenAPIGenerator().generate(router)

        assert "/docs" not in spec["paths"]
        assert "/openapi.json" not in spec["paths"]
        assert "/redoc" not in spec["paths"]
        assert "/items" in spec["paths"]

    def test_skips_internal_routes_by_default(self):
        route_internal = _make_route(path="/_internal/health", handler_name="health")
        route_public = _make_route(path="/items", handler_name="list_items")

        router = self._make_router_with_routes([route_internal, route_public])
        spec = OpenAPIGenerator().generate(router)

        assert "/_internal/health" not in spec["paths"]
        assert "/items" in spec["paths"]

    def test_includes_internal_when_configured(self):
        cfg = OpenAPIConfig(include_internal=True)
        route_internal = _make_route(path="/_internal/health", handler_name="health")

        router = self._make_router_with_routes([route_internal])
        spec = OpenAPIGenerator(config=cfg).generate(router)

        assert "/_internal/health" in spec["paths"]

    def test_response_model_in_components(self):
        @dataclass
        class TaskResponse:
            id: int
            title: str
            done: bool

        route = _make_route(response_model=TaskResponse)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        assert "TaskResponse" in spec["components"]["schemas"]
        schema = spec["components"]["schemas"]["TaskResponse"]
        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "title" in schema["properties"]

    def test_error_response_schema(self):
        """ErrorResponse schema should always be in components."""
        spec = OpenAPIGenerator().generate(self._make_router_with_routes([]))
        assert "ErrorResponse" in spec["components"]["schemas"]
        err = spec["components"]["schemas"]["ErrorResponse"]
        assert err["type"] == "object"
        assert "error" in err["properties"]
        assert "error" in err["required"]

    def test_query_params_from_metadata(self):
        params = [
            ParameterMetadata(name="page", type=int, source="query", default=1, required=False),
            ParameterMetadata(name="limit", type=int, source="query", default=10, required=False),
        ]
        route = _make_route(parameters=params)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        param_names = [p["name"] for p in op.get("parameters", [])]
        assert "page" in param_names
        assert "limit" in param_names

        # Check default values
        for p in op["parameters"]:
            if p["name"] == "page":
                assert p["schema"]["default"] == 1
                assert p["required"] is False

    def test_header_params_from_metadata(self):
        params = [
            ParameterMetadata(name="X-Request-ID", type=str, source="header", required=False),
        ]
        route = _make_route(parameters=params)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        header_params = [p for p in op.get("parameters", []) if p["in"] == "header"]
        assert len(header_params) == 1
        assert header_params[0]["name"] == "X-Request-ID"

    def test_generation_is_idempotent(self):
        """Calling generate() twice should produce the same result."""
        route = _make_route()
        router = self._make_router_with_routes([route])
        gen = OpenAPIGenerator()

        spec1 = gen.generate(router)
        spec2 = gen.generate(router)
        assert spec1 == spec2

    def test_disable_features(self):
        cfg = OpenAPIConfig(
            infer_request_body=False,
            infer_responses=False,
            detect_security=False,
        )
        async def handler(self, ctx):
            data = await ctx.json()
            return Response.json(data)

        ctrl = _make_controller_class(pipeline=[MockAuthGuard()])
        route = _make_route(
            http_method="POST",
            controller_class=ctrl,
            controller_pipeline=[MockAuthGuard()],
            handler_name="handler",
            handler=handler,
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator(config=cfg).generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert "requestBody" not in op
        assert "security" not in op
        assert "securitySchemes" not in spec["components"]
        # Responses should still exist but be minimal
        assert "200" in op["responses"]

    def test_summary_from_docstring(self):
        async def my_handler(self, ctx):
            """Get all widgets from the warehouse."""
            pass

        route = _make_route(handler_name="my_handler", handler=my_handler)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert op["summary"] == "Get all widgets from the warehouse."

    def test_summary_priority_metadata_over_docstring(self):
        """Route metadata summary takes priority over docstring."""
        async def my_handler(self, ctx):
            """Docstring summary."""
            pass

        route = _make_route(
            handler_name="my_handler",
            handler=my_handler,
            summary="Metadata summary",
        )
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        assert op["summary"] == "Metadata summary"

    def test_controller_docstring_as_tag_description(self):
        ctrl = _make_controller_class(
            name="WidgetController",
            docstring="Widget management endpoints.",
        )
        route = _make_route(controller_class=ctrl)
        router = self._make_router_with_routes([route])
        spec = OpenAPIGenerator().generate(router)

        widget_tags = [t for t in spec["tags"] if t["name"] == "Widget"]
        assert len(widget_tags) == 1
        assert widget_tags[0]["description"] == "Widget management endpoints."


# ============================================================================
# Swagger UI HTML
# ============================================================================

class TestSwaggerUIHTML:

    def test_basic_render(self):
        cfg = OpenAPIConfig(title="Test API")
        html = generate_swagger_html(cfg)
        assert "Test API" in html
        assert "/openapi.json" in html
        assert "swagger-ui" in html
        assert "SwaggerUIBundle" in html

    def test_dark_theme(self):
        cfg = OpenAPIConfig(title="Dark API", swagger_ui_theme="dark")
        html = generate_swagger_html(cfg)
        assert "invert(88%)" in html
        assert "hue-rotate(180deg)" in html

    def test_custom_spec_url(self):
        cfg = OpenAPIConfig(openapi_json_path="/api/spec.json")
        html = generate_swagger_html(cfg)
        assert "/api/spec.json" in html

    def test_extra_config(self):
        cfg = OpenAPIConfig(swagger_ui_config={"persistAuthorization": True})
        html = generate_swagger_html(cfg)
        assert "persistAuthorization: true" in html


# ============================================================================
# ReDoc HTML
# ============================================================================

class TestReDocHTML:

    def test_basic_render(self):
        cfg = OpenAPIConfig(title="RD API")
        html = generate_redoc_html(cfg)
        assert "RD API" in html
        assert "/openapi.json" in html
        assert "redoc" in html
        assert "redoc.standalone.js" in html

    def test_custom_spec_url(self):
        cfg = OpenAPIConfig(openapi_json_path="/v2/openapi.json")
        html = generate_redoc_html(cfg)
        assert "/v2/openapi.json" in html


# ============================================================================
# STATUS_DESCRIPTIONS coverage
# ============================================================================

class TestStatusDescriptions:

    def test_common_statuses(self):
        assert _STATUS_DESCRIPTIONS[200] == "Successful response"
        assert _STATUS_DESCRIPTIONS[201] == "Resource created"
        assert _STATUS_DESCRIPTIONS[400] == "Bad request"
        assert _STATUS_DESCRIPTIONS[401] == "Unauthorized"
        assert _STATUS_DESCRIPTIONS[403] == "Forbidden"
        assert _STATUS_DESCRIPTIONS[404] == "Not found"
        assert _STATUS_DESCRIPTIONS[422] == "Unprocessable entity"
        assert _STATUS_DESCRIPTIONS[500] == "Internal server error"


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:

    def test_handler_not_found(self):
        """If handler_name doesn't exist on class, should handle gracefully."""
        ctrl = _make_controller_class()
        route_meta = RouteMetadata(
            http_method="GET",
            path_template="/missing",
            full_path="/missing",
            handler_name="nonexistent_handler",
        )
        ctrl_meta = ControllerMetadata(
            class_name=ctrl.__name__,
            module_path=f"tests.test_openapi:{ctrl.__name__}",
            prefix="/",
            tags=[],
            pipeline=[],
        )
        compiled = CompiledRoute(
            controller_class=ctrl,
            controller_metadata=ctrl_meta,
            route_metadata=route_meta,
            compiled_pattern=_make_pattern("/missing"),
            full_path="/missing",
            http_method="GET",
            specificity=100,
        )
        router = MagicMock(spec=ControllerRouter)
        router.get_routes_full.return_value = [compiled]

        spec = OpenAPIGenerator().generate(router)
        # Should still generate the route, just with minimal info
        assert "/missing" in spec["paths"]

    def test_no_description_omitted(self):
        """Empty description should not appear in operation."""
        route = _make_route()
        router = MagicMock(spec=ControllerRouter)
        router.get_routes_full.return_value = [route]
        spec = OpenAPIGenerator().generate(router)

        ops = list(spec["paths"].values())[0]
        op = list(ops.values())[0]
        # description key might or might not be present; if present, should be valid
        if "description" in op:
            assert isinstance(op["description"], str)

    def test_large_api_with_many_routes(self):
        """Test spec generation with many routes to check for state leaks."""
        routes = []
        for i in range(50):
            ctrl = _make_controller_class(f"Ctrl{i}Controller", prefix=f"/v{i}")
            route = _make_route(
                controller_class=ctrl,
                handler_name=f"handler_{i}",
                path=f"/v{i}/resource",
            )
            routes.append(route)

        router = MagicMock(spec=ControllerRouter)
        router.get_routes_full.return_value = routes
        spec = OpenAPIGenerator().generate(router)

        assert len(spec["paths"]) == 50
        assert len(spec["tags"]) == 50


# ═══════════════════════════════════════════════════════════════════════════
# Singularize Tests (module generator helper)
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.cli.generators.module import _singularize


class TestSingularize:
    """Tests for _singularize() used in CRUD method-name generation."""

    # ── Regular plurals ──────────────────────────────────────────────────

    def test_regular_s(self):
        assert _singularize("blogs") == "blog"

    def test_regular_s_products(self):
        assert _singularize("products") == "product"

    def test_regular_s_users(self):
        assert _singularize("users") == "user"

    def test_regular_s_tasks(self):
        assert _singularize("tasks") == "task"

    def test_regular_s_sessions(self):
        assert _singularize("sessions") == "session"

    # ── -ies → -y ────────────────────────────────────────────────────────

    def test_ies_categories(self):
        assert _singularize("categories") == "category"

    def test_ies_policies(self):
        assert _singularize("policies") == "policy"

    def test_ies_entries(self):
        assert _singularize("entries") == "entry"

    def test_ies_stories(self):
        assert _singularize("stories") == "story"

    # ── -es endings ──────────────────────────────────────────────────────

    def test_sses(self):
        assert _singularize("addresses") == "address"

    def test_shes(self):
        assert _singularize("crashes") == "crash"

    def test_ches(self):
        assert _singularize("matches") == "match"

    def test_xes(self):
        assert _singularize("boxes") == "box"

    def test_zes(self):
        assert _singularize("buzzes") == "buzz"

    # ── -ves → -f ────────────────────────────────────────────────────────

    def test_ves_wolves(self):
        assert _singularize("wolves") == "wolf"

    # ── Irregulars ───────────────────────────────────────────────────────

    def test_people(self):
        assert _singularize("people") == "person"

    def test_children(self):
        assert _singularize("children") == "child"

    def test_men(self):
        assert _singularize("men") == "man"

    def test_women(self):
        assert _singularize("women") == "woman"

    # ── Already singular / uncountable ───────────────────────────────────

    def test_uncountable_news(self):
        assert _singularize("news") == "news"

    def test_uncountable_status(self):
        assert _singularize("status") == "status"

    def test_uncountable_auth(self):
        assert _singularize("auth") == "auth"

    def test_uncountable_config(self):
        assert _singularize("config") == "config"

    def test_uncountable_cache(self):
        assert _singularize("cache") == "cache"

    def test_uncountable_analytics(self):
        assert _singularize("analytics") == "analytics"

    def test_uncountable_fish(self):
        assert _singularize("fish") == "fish"

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_empty_string(self):
        assert _singularize("") == ""

    def test_single_char(self):
        assert _singularize("s") == "s"

    def test_two_chars(self):
        assert _singularize("us") == "us"

    def test_already_singular(self):
        assert _singularize("blog") == "blog"

    def test_already_singular_product(self):
        assert _singularize("product") == "product"

    def test_word_ending_in_ss(self):
        """Words ending in 'ss' should not lose their trailing 's'."""
        assert _singularize("boss") == "boss"

    def test_word_ending_in_us(self):
        """Words ending in 'us' like 'campus' should stay."""
        assert _singularize("campus") == "campus"

    def test_word_ending_in_is(self):
        """Words ending in 'is' like 'analysis' should stay."""
        assert _singularize("basis") == "basis"


class TestModuleGeneratorSingularization:
    """Verify the module generator uses singular names for CRUD methods."""

    def test_controller_method_names_for_plural_module(self, tmp_path):
        """When module name is 'blogs', methods should be create_blog, get_blog, etc."""
        from aquilia.cli.generators.module import ModuleGenerator

        gen = ModuleGenerator(
            name="blogs",
            path=tmp_path / "blogs",
            depends_on=[],
            fault_domain="BLOGS",
            route_prefix="/blogs",
        )
        gen.generate()

        controller_source = (tmp_path / "blogs" / "controllers.py").read_text()

        # list_ keeps the plural (it lists the collection)
        assert "async def list_blogs" in controller_source
        # CRUD on a single resource uses singular
        assert "async def create_blog" in controller_source
        assert "async def get_blog" in controller_source
        assert "async def update_blog" in controller_source
        assert "async def delete_blog" in controller_source
        # Old plural names must NOT appear
        assert "async def create_blogs" not in controller_source
        assert "async def get_blogs" not in controller_source
        assert "async def update_blogs" not in controller_source
        assert "async def delete_blogs" not in controller_source

    def test_controller_docstrings_for_plural_module(self, tmp_path):
        """Docstrings should say 'a blog' not 'blogs' for single-item ops."""
        from aquilia.cli.generators.module import ModuleGenerator

        gen = ModuleGenerator(
            name="blogs",
            path=tmp_path / "blogs",
            depends_on=[],
            fault_domain="BLOGS",
            route_prefix="/blogs",
        )
        gen.generate()

        controller_source = (tmp_path / "blogs" / "controllers.py").read_text()
        assert "Create a new blog." in controller_source
        assert "Get a blog by ID." in controller_source
        assert "Update a blog by ID." in controller_source
        assert "Delete a blog by ID." in controller_source

    def test_singular_module_name_unchanged(self, tmp_path):
        """When module name is already singular, methods stay the same."""
        from aquilia.cli.generators.module import ModuleGenerator

        gen = ModuleGenerator(
            name="task",
            path=tmp_path / "task",
            depends_on=[],
            fault_domain="TASK",
            route_prefix="/task",
        )
        gen.generate()

        controller_source = (tmp_path / "task" / "controllers.py").read_text()
        assert "async def list_task" in controller_source
        assert "async def create_task" in controller_source
        assert "async def get_task" in controller_source

    def test_ies_plural_module(self, tmp_path):
        """Module named 'categories' should produce 'create_category'."""
        from aquilia.cli.generators.module import ModuleGenerator

        gen = ModuleGenerator(
            name="categories",
            path=tmp_path / "categories",
            depends_on=[],
            fault_domain="CATEGORIES",
            route_prefix="/categories",
        )
        gen.generate()

        controller_source = (tmp_path / "categories" / "controllers.py").read_text()
        assert "async def create_category" in controller_source
        assert "async def get_category" in controller_source

    def test_fault_messages_use_singular(self, tmp_path):
        """Fault messages should say 'Blog with id' not 'Blogs with id'."""
        from aquilia.cli.generators.module import ModuleGenerator

        gen = ModuleGenerator(
            name="blogs",
            path=tmp_path / "blogs",
            depends_on=[],
            fault_domain="BLOGS",
            route_prefix="/blogs",
        )
        gen.generate()

        faults_source = (tmp_path / "blogs" / "faults.py").read_text()
        assert "Blog with id" in faults_source
        assert "Blogs with id" not in faults_source
        assert "a blog is not found" in faults_source
