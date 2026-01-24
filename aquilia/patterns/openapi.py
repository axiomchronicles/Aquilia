"""
OpenAPI schema generation from compiled patterns.
"""

from typing import Dict, Any, List
from .compiler.compiler import CompiledPattern


def generate_openapi_params(pattern: CompiledPattern) -> List[Dict[str, Any]]:
    """
    Generate OpenAPI parameter definitions from a compiled pattern.

    Returns a list of parameter objects ready for inclusion in OpenAPI spec.
    """
    return pattern.openapi.get("parameters", [])


def generate_openapi_path(pattern: CompiledPattern) -> str:
    """
    Convert AquilaPattern to OpenAPI path template.

    Example:
        /users/«id:int» -> /users/{id}
    """
    parts = []

    for segment in pattern.ast.segments:
        from .compiler.ast_nodes import StaticSegment, TokenSegment, SplatSegment, OptionalGroup

        if isinstance(segment, StaticSegment):
            parts.append(segment.value)
        elif isinstance(segment, TokenSegment):
            parts.append(f"{{{segment.name}}}")
        elif isinstance(segment, SplatSegment):
            parts.append(f"{{{segment.name}}}")
        elif isinstance(segment, OptionalGroup):
            # Flatten optional groups for OpenAPI
            # OpenAPI doesn't have optional segments, so we generate the full path
            for subseg in segment.segments:
                if isinstance(subseg, StaticSegment):
                    parts.append(subseg.value)
                elif isinstance(subseg, TokenSegment):
                    parts.append(f"{{{subseg.name}}}")

    return "/" + "/".join(parts)


def pattern_to_openapi_operation(
    pattern: CompiledPattern,
    method: str,
    handler_name: str,
    summary: str = "",
    description: str = "",
    tags: List[str] = None,
) -> Dict[str, Any]:
    """
    Generate a complete OpenAPI operation object.

    Args:
        pattern: Compiled pattern
        method: HTTP method (GET, POST, etc.)
        handler_name: Name of handler function
        summary: Operation summary
        description: Operation description
        tags: List of tags

    Returns:
        OpenAPI operation dict
    """
    operation = {
        "operationId": handler_name,
        "parameters": generate_openapi_params(pattern),
        "responses": {
            "200": {
                "description": "Successful response",
            }
        },
    }

    if summary:
        operation["summary"] = summary
    if description:
        operation["description"] = description
    if tags:
        operation["tags"] = tags

    return operation


def patterns_to_openapi_spec(
    patterns: List[tuple[CompiledPattern, str, str]],
    title: str = "Aquilia API",
    version: str = "1.0.0",
    description: str = "",
) -> Dict[str, Any]:
    """
    Generate complete OpenAPI 3.0 specification from patterns.

    Args:
        patterns: List of (pattern, method, handler_name) tuples
        title: API title
        version: API version
        description: API description

    Returns:
        Complete OpenAPI spec dict
    """
    paths = {}

    for pattern, method, handler_name in patterns:
        path = generate_openapi_path(pattern)

        if path not in paths:
            paths[path] = {}

        paths[path][method.lower()] = pattern_to_openapi_operation(
            pattern, method, handler_name
        )

    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": paths,
    }

    if description:
        spec["info"]["description"] = description

    return spec
