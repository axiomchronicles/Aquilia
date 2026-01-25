"""
OpenAPI Generation for Aquilia Controllers.
"""

from typing import Dict, Any, List, Optional, Type
import inspect
import json

from .router import ControllerRouter
from .compiler import CompiledRoute
from ..patterns.openapi import generate_openapi_path, generate_openapi_params

class OpenAPIGenerator:
    """
    Generates OpenAPI 3.0.0 specification from a ControllerRouter.
    """
    
    def __init__(self, title: str = "Aquilia API", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.paths: Dict[str, Dict[str, Any]] = {}
        self.schemas: Dict[str, Any] = {}

    def generate(self, router: ControllerRouter) -> Dict[str, Any]:
        """Generate the full OpenAPI spec."""
        routes = router.get_routes_full()
        
        for route in routes:
            self._add_route(route)
            
        return {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
            },
            "paths": self.paths,
            "components": {
                "schemas": self.schemas
            }
        }

    def _add_route(self, route: CompiledRoute):
        # Use built-in pattern to OpenAPI path converter
        path = generate_openapi_path(route.compiled_pattern)
        method = route.http_method.lower()
        
        if path not in self.paths:
            self.paths[path] = {}
            
        # Extract handlers and docstrings
        handler = getattr(route.controller_class, route.route_metadata.handler_name)
        docstring = inspect.getdoc(handler) or ""
        summary, description = self._parse_docstring(docstring)
        
        # Use built-in pattern to OpenAPI parameters converter
        parameters = generate_openapi_params(route.compiled_pattern)
        
        # Build operation
        operation = {
            "operationId": route.route_metadata.handler_name,
            "summary": summary or route.route_metadata.handler_name.replace("_", " ").title(),
            "description": description or "",
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"} # Generic response schema
                        }
                    }
                }
            }
        }
        
        if parameters:
            operation["parameters"] = parameters
            
        self.paths[path][method] = operation

    def _parse_docstring(self, docstring: str) -> tuple[Optional[str], Optional[str]]:
        if not docstring:
            return None, None
        lines = [line.strip() for line in docstring.split("\n")]
        summary = lines[0] if lines else None
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
        return summary, description
