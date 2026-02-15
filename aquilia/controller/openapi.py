"""
OpenAPI 3.1.0 Generation for Aquilia Controllers.

Comprehensive spec generation with:
- Full introspection of controller metadata, decorators, and type hints
- Request body inference from handler signatures, docstrings, and source analysis
- Response schema generation from response_model and status_code
- Security scheme detection from pipeline guards
- Tag grouping from controller/module tags
- Server info from runtime config
- Component schema deduplication and $ref resolution
- Swagger UI and ReDoc HTML rendering
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from .router import ControllerRouter
from .compiler import CompiledRoute
from ..patterns.openapi import generate_openapi_path, generate_openapi_params

# Try Annotated for Python 3.9+
try:
    from typing import Annotated
except ImportError:
    Annotated = None  # type: ignore


# ─── Type → JSON Schema mapping ──────────────────────────────────────────────

_PYTHON_TYPE_MAP: Dict[type, Dict[str, str]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number", "format": "double"},
    bool: {"type": "boolean"},
    bytes: {"type": "string", "format": "binary"},
    type(None): {"type": "null"},
}


def _python_type_to_schema(tp: Any) -> Dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema fragment."""
    if tp is inspect.Parameter.empty or tp is Any:
        return {}

    # Basic types
    if tp in _PYTHON_TYPE_MAP:
        return dict(_PYTHON_TYPE_MAP[tp])

    origin = get_origin(tp)
    args = get_args(tp)

    # Optional[X] → nullable
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            schema = _python_type_to_schema(non_none[0])
            schema["nullable"] = True
            return schema
        # Union of multiple types → anyOf
        return {"anyOf": [_python_type_to_schema(a) for a in non_none]}

    # list[X]
    if origin is list or origin is List:
        item_schema = _python_type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}

    # dict[str, X]
    if origin is dict or origin is Dict:
        val_schema = _python_type_to_schema(args[1]) if len(args) > 1 else {}
        return {"type": "object", "additionalProperties": val_schema}

    # tuple → array with prefixItems
    if origin is tuple or origin is Tuple:
        if args:
            return {
                "type": "array",
                "prefixItems": [_python_type_to_schema(a) for a in args],
                "minItems": len(args),
                "maxItems": len(args),
            }
        return {"type": "array"}

    # set → array with uniqueItems
    if origin is set or origin is Set:
        item_schema = _python_type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema, "uniqueItems": True}

    # Annotated[X, ...] → unwrap
    if Annotated is not None and origin is Annotated:
        return _python_type_to_schema(args[0])

    # Dataclass / class with __annotations__
    if isinstance(tp, type) and hasattr(tp, "__annotations__"):
        return {"$ref": f"#/components/schemas/{tp.__name__}"}

    return {"type": "object"}


def _dataclass_to_schema(cls: type) -> Dict[str, Any]:
    """Convert a dataclass or annotated class to a JSON Schema object."""
    if not hasattr(cls, "__annotations__"):
        return {"type": "object"}

    properties: Dict[str, Any] = {}
    required: List[str] = []

    hints = get_type_hints(cls, include_extras=True) if hasattr(cls, "__annotations__") else {}

    for field_name, field_type in hints.items():
        if field_name.startswith("_"):
            continue
        properties[field_name] = _python_type_to_schema(field_type)

        # Determine if required (no default value)
        default = getattr(cls, field_name, inspect.Parameter.empty)
        if default is inspect.Parameter.empty:
            required.append(field_name)

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    doc = inspect.getdoc(cls)
    if doc:
        schema["description"] = doc

    return schema


# ─── Docstring Parsing ────────────────────────────────────────────────────────

@dataclass
class ParsedDocstring:
    """Parsed handler docstring with structured sections."""
    summary: str = ""
    description: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    returns: str = ""
    raises: List[Dict[str, str]] = field(default_factory=list)
    request_body: Optional[str] = None


def _parse_docstring(docstring: str) -> ParsedDocstring:
    """Parse a handler docstring into structured sections."""
    if not docstring:
        return ParsedDocstring()

    lines = docstring.split("\n")
    result = ParsedDocstring()

    # First non-empty line is the summary
    for line in lines:
        stripped = line.strip()
        if stripped:
            result.summary = stripped
            break

    # Everything after the first blank line (after summary) is description
    in_description = False
    description_lines: list[str] = []
    current_section: Optional[str] = None
    current_key: Optional[str] = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip the summary line
        if not in_description and stripped == result.summary:
            continue

        # Detect section headers
        lower = stripped.lower()
        if lower.startswith("args:") or lower.startswith("params:") or lower.startswith("parameters:"):
            current_section = "params"
            in_description = False
            continue
        elif lower.startswith("returns:") or lower.startswith("return:"):
            current_section = "returns"
            result.returns = stripped.split(":", 1)[1].strip()
            in_description = False
            continue
        elif lower.startswith("raises:") or lower.startswith("raise:"):
            current_section = "raises"
            in_description = False
            continue
        elif lower.startswith("body:") or lower.startswith("request body:"):
            current_section = "body"
            result.request_body = stripped.split(":", 1)[1].strip()
            in_description = False
            continue

        if current_section == "params":
            # Parse "name: description" or "name (type): description"
            param_match = re.match(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", stripped)
            if param_match:
                result.params[param_match.group(1)] = param_match.group(2).strip()
                current_key = param_match.group(1)
            elif current_key and stripped:
                result.params[current_key] += " " + stripped
        elif current_section == "raises":
            raise_match = re.match(r"^\s*(\w+)\s*(?:\((\d+)\))?\s*:\s*(.*)", stripped)
            if raise_match:
                result.raises.append({
                    "exception": raise_match.group(1),
                    "status": raise_match.group(2),
                    "description": raise_match.group(3).strip(),
                })
        elif current_section is None and not stripped:
            if result.summary:
                in_description = True
        elif current_section is None and in_description:
            description_lines.append(stripped)

    result.description = "\n".join(description_lines).strip()
    return result


# ─── Security Scheme Detection ────────────────────────────────────────────────

def _detect_security_schemes(
    routes: List[CompiledRoute],
) -> Dict[str, Any]:
    """
    Detect security schemes from pipeline guards on all routes.

    Returns:
        Dict of security scheme definitions for components/securitySchemes.
    """
    schemes: Dict[str, Any] = {}

    for route in routes:
        pipeline = getattr(route.route_metadata, "pipeline", []) or []
        class_pipeline = []
        if route.controller_metadata:
            class_pipeline = getattr(route.controller_metadata, "pipeline", []) or []

        for node in class_pipeline + pipeline:
            cls_name = type(node).__name__ if not isinstance(node, type) else node.__name__
            cls_name_lower = cls_name.lower()

            # Order matters: check more specific patterns first
            if "oauth" in cls_name_lower:
                if "oauth2" not in schemes:
                    schemes["oauth2"] = {
                        "type": "oauth2",
                        "flows": {
                            "authorizationCode": {
                                "authorizationUrl": "/auth/authorize",
                                "tokenUrl": "/auth/token",
                                "scopes": {},
                            }
                        },
                    }
            elif "apikey" in cls_name_lower:
                if "apiKeyAuth" not in schemes:
                    schemes["apiKeyAuth"] = {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                        "description": "API key authentication",
                    }
            elif "authguard" in cls_name_lower or cls_name_lower == "auth":
                if "bearerAuth" not in schemes:
                    schemes["bearerAuth"] = {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT Bearer token authentication",
                    }

    return schemes


# ─── Request Body Inference ───────────────────────────────────────────────────

_BODY_METHODS = {"POST", "PUT", "PATCH"}

# Patterns in docstrings that indicate request body fields
_BODY_DOC_PATTERN = re.compile(
    r"Body:\s*\{([^}]+)\}",
    re.DOTALL | re.IGNORECASE,
)

_BODY_FIELD_PATTERN = re.compile(
    r'"(\w+)"\s*:\s*"?([^",\n}]+)"?',
)


def _infer_request_body(
    route: CompiledRoute,
    handler: Any,
    parsed_doc: ParsedDocstring,
) -> Optional[Dict[str, Any]]:
    """
    Infer request body schema from handler signature, type hints, and source analysis.
    """
    if route.http_method not in _BODY_METHODS:
        return None

    # Strategy 1: Check ParameterMetadata for source='body'
    body_props: Dict[str, Any] = {}
    body_required: List[str] = []
    for param_meta in route.route_metadata.parameters:
        if param_meta.source == "body":
            schema = _python_type_to_schema(param_meta.type)
            body_props[param_meta.name] = schema
            if param_meta.required:
                body_required.append(param_meta.name)

    if body_props:
        body_schema: Dict[str, Any] = {
            "type": "object",
            "properties": body_props,
        }
        if body_required:
            body_schema["required"] = body_required
        return {
            "required": True,
            "content": {
                "application/json": {"schema": body_schema}
            },
        }

    # Strategy 2: look for Body annotation in handler params
    try:
        hints = get_type_hints(handler, include_extras=True)
    except Exception:
        hints = {}

    if handler:
        try:
            sig = inspect.signature(handler)
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls", "ctx"):
                    continue
                hint = hints.get(param_name, param.annotation)
                if hint is inspect.Parameter.empty:
                    continue
                # Check for Annotated[X, Body(...)]
                if Annotated is not None and get_origin(hint) is Annotated:
                    args = get_args(hint)
                    for ann in args[1:]:
                        ann_name = type(ann).__name__.lower() if not isinstance(ann, type) else ann.__name__.lower()
                        if "body" in ann_name:
                            return {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": _python_type_to_schema(args[0]),
                                    }
                                },
                            }
        except (ValueError, TypeError):
            pass

    # Strategy 3: parse docstring for Body: {...} pattern
    docstring = inspect.getdoc(handler) or "" if handler else ""
    body_match = _BODY_DOC_PATTERN.search(docstring)
    if body_match:
        body_text = body_match.group(1)
        fields = _BODY_FIELD_PATTERN.findall(body_text)
        if fields:
            properties: Dict[str, Any] = {}
            for field_name, field_example in fields:
                schema = _infer_type_from_example(field_example.strip())
                schema["example"] = field_example.strip().strip('"')
                properties[field_name] = schema
            return {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": properties,
                        }
                    }
                },
            }

    # Strategy 4: if handler source calls ctx.json() / ctx.form(), assume body
    if handler:
        try:
            source = inspect.getsource(handler)
            if "ctx.json()" in source or "await ctx.json()" in source:
                return {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    },
                }
            if "ctx.form()" in source or "await ctx.form()" in source:
                return {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {"type": "object"},
                        }
                    },
                }
        except (OSError, TypeError):
            pass

    return None


def _infer_type_from_example(example: str) -> Dict[str, Any]:
    """Infer JSON Schema type from a docstring example value."""
    example = example.strip().strip('"').strip("'")

    if example.lower() in ("true", "false"):
        return {"type": "boolean"}
    try:
        int(example)
        return {"type": "integer"}
    except (ValueError, TypeError):
        pass
    try:
        float(example)
        return {"type": "number"}
    except (ValueError, TypeError):
        pass
    if example.startswith("["):
        return {"type": "array", "items": {"type": "string"}}
    if example.startswith("{"):
        return {"type": "object"}
    return {"type": "string"}


# ─── Response Inference ───────────────────────────────────────────────────────

_STATUS_DESCRIPTIONS: Dict[int, str] = {
    200: "Successful response",
    201: "Resource created",
    202: "Accepted for processing",
    204: "No content",
    301: "Moved permanently",
    302: "Found (redirect)",
    304: "Not modified",
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    422: "Unprocessable entity",
    429: "Too many requests",
    500: "Internal server error",
}


def _build_responses(
    route: CompiledRoute,
    handler: Any,
    parsed_doc: ParsedDocstring,
) -> Dict[str, Any]:
    """Build comprehensive response definitions for an operation."""
    responses: Dict[str, Any] = {}

    # Primary success response
    status_code = str(getattr(route.route_metadata, "status_code", 200))
    response_model = getattr(route.route_metadata, "response_model", None)

    success_response: Dict[str, Any] = {
        "description": _STATUS_DESCRIPTIONS.get(int(status_code), "Successful response"),
    }

    if response_model is not None:
        success_response["content"] = {
            "application/json": {
                "schema": _python_type_to_schema(response_model),
            }
        }
    else:
        # Infer from handler source
        try:
            source = inspect.getsource(handler) if handler else ""
        except (OSError, TypeError):
            source = ""

        if "Response.json(" in source:
            success_response["content"] = {
                "application/json": {"schema": {"type": "object"}}
            }
        elif "Response.html(" in source or "render_to_response" in source or "self.render(" in source:
            success_response["content"] = {
                "text/html": {"schema": {"type": "string"}}
            }
        elif "Response.text(" in source:
            success_response["content"] = {
                "text/plain": {"schema": {"type": "string"}}
            }
        else:
            success_response["content"] = {
                "application/json": {"schema": {"type": "object"}}
            }

    responses[status_code] = success_response

    # Error responses from docstring raises
    for raise_info in parsed_doc.raises:
        status = raise_info.get("status", "500")
        if status:
            responses[status] = {
                "description": raise_info.get("description", raise_info["exception"]),
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            }

    # Infer common error responses from handler source
    if handler:
        try:
            source = inspect.getsource(handler)
            for status_match in re.finditer(r"status[=_](\d{3})", source):
                code = status_match.group(1)
                if code.startswith("4") or code.startswith("5"):
                    if code not in responses:
                        responses[code] = {
                            "description": _STATUS_DESCRIPTIONS.get(int(code), f"Error {code}"),
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            },
                        }
        except (OSError, TypeError):
            pass

    return responses


# ─── Operation-Level Security ─────────────────────────────────────────────────

def _build_operation_security(route: CompiledRoute) -> Optional[List[Dict[str, List[str]]]]:
    """Build security requirements for a specific operation."""
    pipeline = getattr(route.route_metadata, "pipeline", []) or []
    class_pipeline = []
    if route.controller_metadata:
        class_pipeline = getattr(route.controller_metadata, "pipeline", []) or []

    security: List[Dict[str, List[str]]] = []

    for node in class_pipeline + pipeline:
        cls_name = type(node).__name__ if not isinstance(node, type) else node.__name__
        cls_name_lower = cls_name.lower()

        # Order matters: check more specific patterns first
        if "oauth" in cls_name_lower:
            security.append({"oauth2": []})
        elif "apikey" in cls_name_lower:
            security.append({"apiKeyAuth": []})
        elif "authguard" in cls_name_lower or cls_name_lower == "auth":
            security.append({"bearerAuth": []})
        elif "scope" in cls_name_lower or "role" in cls_name_lower:
            scopes = []
            if hasattr(node, "scopes"):
                scopes = list(node.scopes)
            elif hasattr(node, "roles"):
                scopes = list(node.roles)
            if security:
                for key in security[-1]:
                    security[-1][key] = scopes
            else:
                security.append({"bearerAuth": scopes})

    return security if security else None


# ─── OpenAPI Configuration ────────────────────────────────────────────────────

@dataclass
class OpenAPIConfig:
    """
    Configuration for OpenAPI spec generation.

    Set via ``Integration.openapi(...)`` in the workspace or
    passed directly to ``OpenAPIGenerator``.
    """
    # Info
    title: str = "Aquilia API"
    version: str = "1.0.0"
    description: str = ""
    terms_of_service: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_url: str = ""
    license_name: str = ""
    license_url: str = ""

    # Servers
    servers: List[Dict[str, str]] = field(default_factory=list)

    # Paths
    docs_path: str = "/docs"
    openapi_json_path: str = "/openapi.json"
    redoc_path: str = "/redoc"

    # Features
    include_internal: bool = False  # include /_internal routes
    group_by_module: bool = True    # group tags by module
    infer_request_body: bool = True
    infer_responses: bool = True
    detect_security: bool = True

    # External docs
    external_docs_url: str = ""
    external_docs_description: str = ""

    # Swagger UI
    swagger_ui_theme: str = ""  # "dark", "monokai", etc.
    swagger_ui_config: Dict[str, Any] = field(default_factory=dict)

    # Enabled flag
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenAPIConfig":
        """Create config from dict (e.g., from workspace config)."""
        config = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# ─── Main Generator ──────────────────────────────────────────────────────────

class OpenAPIGenerator:
    """
    Production-grade OpenAPI 3.1.0 specification generator.

    Generates a complete OpenAPI spec from the compiled controller router
    with full introspection of:
    - Route paths, methods, and parameters (path, query)
    - Request body inference from docstrings, type hints, and source analysis
    - Response schemas from response_model and source analysis
    - Security schemes from pipeline guards
    - Tags from controller and module metadata
    - Server info from config

    Usage::

        generator = OpenAPIGenerator(config=OpenAPIConfig(
            title="My API",
            version="2.0.0",
            description="My awesome API",
        ))
        spec = generator.generate(router)

    Or with backward-compatible positional args::

        generator = OpenAPIGenerator(title="My API", version="2.0.0")
        spec = generator.generate(router)
    """

    def __init__(
        self,
        title: str = "Aquilia API",
        version: str = "1.0.0",
        config: Optional[OpenAPIConfig] = None,
    ):
        if config:
            self.config = config
        else:
            self.config = OpenAPIConfig(title=title, version=version)

        self.paths: Dict[str, Dict[str, Any]] = {}
        self.schemas: Dict[str, Any] = {}
        self.tags: List[Dict[str, Any]] = []
        self._seen_tags: Set[str] = set()
        self._security_schemes: Dict[str, Any] = {}

    def generate(self, router: ControllerRouter) -> Dict[str, Any]:
        """Generate the full OpenAPI 3.1.0 specification."""
        routes = router.get_routes_full()

        # Reset state for fresh generation each call
        self.paths = {}
        self.schemas = {}
        self.tags = []
        self._seen_tags = set()
        self._security_schemes = {}

        # Detect security schemes from all routes
        if self.config.detect_security:
            self._security_schemes = _detect_security_schemes(routes)

        # Process each route
        for route in routes:
            self._add_route(route)

        # Register response_model schemas into components
        for route in routes:
            model = getattr(route.route_metadata, "response_model", None)
            if model is not None and isinstance(model, type) and hasattr(model, "__annotations__"):
                if model.__name__ not in self.schemas:
                    self.schemas[model.__name__] = _dataclass_to_schema(model)

        # Build spec
        spec: Dict[str, Any] = {
            "openapi": "3.1.0",
            "info": self._build_info(),
            "paths": self.paths,
        }

        # Servers
        servers = self.config.servers or self._default_servers()
        if servers:
            spec["servers"] = servers

        # Tags
        if self.tags:
            spec["tags"] = sorted(self.tags, key=lambda t: t["name"])

        # Components
        components: Dict[str, Any] = {}
        if self.schemas:
            components["schemas"] = dict(self.schemas)
        if self._security_schemes:
            components["securitySchemes"] = self._security_schemes

        # Standard error schema
        components.setdefault("schemas", {})["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "Error message"},
                "code": {"type": "string", "description": "Error code"},
                "detail": {
                    "type": "object",
                    "description": "Additional error details",
                    "additionalProperties": True,
                },
            },
            "required": ["error"],
        }
        spec["components"] = components

        # External docs
        if self.config.external_docs_url:
            spec["externalDocs"] = {
                "url": self.config.external_docs_url,
            }
            if self.config.external_docs_description:
                spec["externalDocs"]["description"] = self.config.external_docs_description

        return spec

    # ── Info ──────────────────────────────────────────────────────────────

    def _build_info(self) -> Dict[str, Any]:
        """Build the info object."""
        info: Dict[str, Any] = {
            "title": self.config.title,
            "version": self.config.version,
        }
        if self.config.description:
            info["description"] = self.config.description
        if self.config.terms_of_service:
            info["termsOfService"] = self.config.terms_of_service

        # Contact
        contact: Dict[str, str] = {}
        if self.config.contact_name:
            contact["name"] = self.config.contact_name
        if self.config.contact_email:
            contact["email"] = self.config.contact_email
        if self.config.contact_url:
            contact["url"] = self.config.contact_url
        if contact:
            info["contact"] = contact

        # License
        license_info: Dict[str, str] = {}
        if self.config.license_name:
            license_info["name"] = self.config.license_name
        if self.config.license_url:
            license_info["url"] = self.config.license_url
        if license_info:
            info["license"] = license_info

        return info

    def _default_servers(self) -> List[Dict[str, str]]:
        """Generate default server entries."""
        return [
            {"url": "/", "description": "Current server"},
        ]

    # ── Route Processing ─────────────────────────────────────────────────

    def _add_route(self, route: CompiledRoute):
        """Process a single compiled route into an OpenAPI path operation."""
        # Skip internal routes unless configured
        if not self.config.include_internal and route.full_path.startswith("/_"):
            return

        # Skip docs routes to avoid self-reference
        if route.full_path in (
            self.config.openapi_json_path,
            self.config.docs_path,
            self.config.redoc_path,
        ):
            return

        # Convert pattern to OpenAPI path template
        path = generate_openapi_path(route.compiled_pattern)
        method = route.http_method.lower()

        if path not in self.paths:
            self.paths[path] = {}

        # Get handler and docstring
        handler = getattr(route.controller_class, route.route_metadata.handler_name, None)
        docstring = inspect.getdoc(handler) if handler else ""
        parsed_doc = _parse_docstring(docstring or "")

        # Build operation
        operation = self._build_operation(route, handler, parsed_doc)

        self.paths[path][method] = operation

    def _build_operation(
        self,
        route: CompiledRoute,
        handler: Any,
        parsed_doc: ParsedDocstring,
    ) -> Dict[str, Any]:
        """Build a complete OpenAPI operation object."""
        route_meta = route.route_metadata

        # Operation ID: unique identifier
        controller_name = route.controller_class.__name__.replace("Controller", "")
        operation_id = f"{controller_name}_{route_meta.handler_name}"

        # Summary and description
        summary = route_meta.summary or parsed_doc.summary or route_meta.handler_name.replace("_", " ").title()
        description = route_meta.description or parsed_doc.description or ""

        operation: Dict[str, Any] = {
            "operationId": operation_id,
            "summary": summary,
        }

        if description:
            operation["description"] = description

        # Tags
        tags = list(route_meta.tags) if route_meta.tags else []
        if not tags and route.controller_metadata:
            tags = list(route.controller_metadata.tags) if route.controller_metadata.tags else []
        if not tags:
            # Fall back to controller class name as tag
            tags = [route.controller_class.__name__.replace("Controller", "")]

        operation["tags"] = tags

        # Register tags
        for tag in tags:
            if tag not in self._seen_tags:
                self._seen_tags.add(tag)
                tag_info: Dict[str, Any] = {"name": tag}
                # Add description from controller docstring
                if tag == route.controller_class.__name__.replace("Controller", ""):
                    ctrl_doc = inspect.getdoc(route.controller_class)
                    if ctrl_doc:
                        tag_info["description"] = ctrl_doc.split("\n")[0]
                self.tags.append(tag_info)

        # Parameters (path + query from compiled pattern)
        parameters = list(generate_openapi_params(route.compiled_pattern))

        # Enrich parameters with docstring descriptions
        for param in parameters:
            param_name = param.get("name", "")
            if param_name in parsed_doc.params:
                param["description"] = parsed_doc.params[param_name]

        # Add query parameters from handler metadata
        if handler:
            self._add_query_params_from_metadata(handler, parameters, route, parsed_doc)

        if parameters:
            operation["parameters"] = parameters

        # Request body
        if self.config.infer_request_body and handler:
            request_body = _infer_request_body(route, handler, parsed_doc)
            if request_body:
                operation["requestBody"] = request_body

        # Responses
        if self.config.infer_responses and handler:
            operation["responses"] = _build_responses(route, handler, parsed_doc)
        else:
            operation["responses"] = {
                str(route_meta.status_code): {
                    "description": _STATUS_DESCRIPTIONS.get(route_meta.status_code, "Successful response"),
                }
            }

        # Deprecated
        if route_meta.deprecated:
            operation["deprecated"] = True

        # Security
        if self.config.detect_security:
            security = _build_operation_security(route)
            if security:
                operation["security"] = security

        return operation

    def _add_query_params_from_metadata(
        self,
        handler: Any,
        parameters: List[Dict[str, Any]],
        route: CompiledRoute,
        parsed_doc: ParsedDocstring,
    ):
        """Add query parameters inferred from route metadata."""
        existing_names = {p["name"] for p in parameters}

        for param_meta in route.route_metadata.parameters:
            if param_meta.source == "query" and param_meta.name not in existing_names:
                schema = _python_type_to_schema(param_meta.type)
                param: Dict[str, Any] = {
                    "name": param_meta.name,
                    "in": "query",
                    "required": param_meta.required,
                    "schema": schema,
                }
                if param_meta.name in parsed_doc.params:
                    param["description"] = parsed_doc.params[param_meta.name]
                if param_meta.has_default:
                    param["schema"]["default"] = param_meta.default
                parameters.append(param)
                existing_names.add(param_meta.name)

            elif param_meta.source == "header" and param_meta.name not in existing_names:
                schema = _python_type_to_schema(param_meta.type)
                param = {
                    "name": param_meta.name,
                    "in": "header",
                    "required": param_meta.required,
                    "schema": schema,
                }
                if param_meta.name in parsed_doc.params:
                    param["description"] = parsed_doc.params[param_meta.name]
                parameters.append(param)
                existing_names.add(param_meta.name)


# ─── Swagger UI HTML ─────────────────────────────────────────────────────────

_SWAGGER_UI_VERSION = "5.18.2"

_SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - API Documentation</title>
    <link rel="icon" type="image/png"
          href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/favicon-32x32.png">
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui.css">
    <style>
        html {{ box-sizing: border-box; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin: 0; background: #fafafa; }}
        .topbar {{ display: none !important; }}
        .swagger-ui .info hgroup.main a {{
            font-size: 0;
        }}
        .swagger-ui .info hgroup.main a::after {{
            content: '{title}';
            font-size: 36px;
        }}
        {extra_css}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui-bundle.js">
    </script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui-standalone-preset.js">
    </script>
    <script>
        window.onload = () => {{
            window.ui = SwaggerUIBundle({{
                url: '{spec_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset,
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl,
                ],
                layout: 'StandaloneLayout',
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 2,
                docExpansion: 'list',
                filter: true,
                showExtensions: true,
                showCommonExtensions: true,
                tryItOutEnabled: true,
                {extra_config}
            }});
        }};
    </script>
</body>
</html>"""


def generate_swagger_html(config: OpenAPIConfig) -> str:
    """Generate the Swagger UI HTML page."""
    extra_css = ""
    if config.swagger_ui_theme == "dark":
        extra_css = """
        body { background: #1a1a2e; }
        .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
        .swagger-ui .model-box,
        .swagger-ui section.models {
            filter: invert(100%) hue-rotate(180deg);
        }
        """

    extra_config_parts = []
    for key, value in config.swagger_ui_config.items():
        if isinstance(value, str):
            extra_config_parts.append(f"{key}: '{value}'")
        elif isinstance(value, bool):
            extra_config_parts.append(f"{key}: {'true' if value else 'false'}")
        else:
            extra_config_parts.append(f"{key}: {value}")

    return _SWAGGER_UI_HTML.format(
        title=config.title,
        version=_SWAGGER_UI_VERSION,
        spec_url=config.openapi_json_path,
        extra_css=extra_css,
        extra_config=",\n                ".join(extra_config_parts),
    )


# ─── ReDoc HTML ───────────────────────────────────────────────────────────────

_REDOC_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - API Reference</title>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
          rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='{spec_url}'
           hide-hostname
           expand-responses="200,201"
           path-in-middle-panel
           native-scrollbars>
    </redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""


def generate_redoc_html(config: OpenAPIConfig) -> str:
    """Generate the ReDoc HTML page."""
    return _REDOC_HTML.format(
        title=config.title,
        spec_url=config.openapi_json_path,
    )
