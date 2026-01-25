"""
Controller Compiler - Compiles controllers to patterns and routes.

Integrates with:
- aquilia.patterns for URL pattern compilation
- aquilia.controller.metadata for controller introspection
- aquilia.router for route registration
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import inspect

from .metadata import (
    extract_controller_metadata,
    ControllerMetadata,
    RouteMetadata,
)
from ..patterns import (
    parse_pattern,
    PatternCompiler,
    CompiledPattern,
    calculate_specificity,
    PatternSemanticError,
)
from ..patterns.compiler.ast_nodes import PatternAST


@dataclass
class CompiledRoute:
    """A compiled controller route with pattern and handler."""
    
    controller_class: type
    controller_metadata: ControllerMetadata
    route_metadata: RouteMetadata
    compiled_pattern: CompiledPattern
    full_path: str
    http_method: str
    specificity: int
    app_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "controller": f"{self.controller_class.__module__}:{self.controller_class.__name__}",
            "route_name": self.route_metadata.handler_name,
            "path": self.full_path,
            "method": self.http_method,
            "specificity": self.specificity,
            "pattern": self.compiled_pattern.to_dict(),
        }


@dataclass
class CompiledController:
    """A fully compiled controller with all routes."""
    
    controller_class: type
    metadata: ControllerMetadata
    routes: List[CompiledRoute]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "controller": f"{self.controller_class.__module__}:{self.controller_class.__name__}",
            "prefix": self.metadata.prefix,
            "routes": [r.to_dict() for r in self.routes],
        }


class ControllerCompiler:
    """
    Compiles controllers into executable routes with pattern matching.
    
    This is the bridge between:
    - Controller metadata extraction
    - Pattern compilation (aquilia.patterns)
    - Route registration
    """
    
    def __init__(self):
        self.pattern_compiler = PatternCompiler()
        self.compiled_controllers: Dict[str, CompiledController] = {}
        self.route_conflicts: List[tuple[str, str]] = []
    
    def compile_controller(self, controller_class: type) -> CompiledController:
        """
        Compile a controller class into routes.
        
        Args:
            controller_class: Controller class to compile
            
        Returns:
            CompiledController with all routes
            
        Raises:
            PatternSemanticError: If patterns are invalid
        """
        # Extract metadata
        module_path = f"{controller_class.__module__}:{controller_class.__name__}"
        metadata = extract_controller_metadata(controller_class, module_path)
        
        # Compile each route
        compiled_routes = []
        
        for route_meta in metadata.routes:
            try:
                compiled_route = self._compile_route(
                    controller_class,
                    metadata,
                    route_meta,
                )
                compiled_routes.append(compiled_route)
            except Exception as e:
                raise PatternSemanticError(
                    f"Failed to compile route {route_meta.handler_name} in {controller_class.__name__}: {e}",
                    file=inspect.getfile(controller_class),
                )
        
        # Sort routes by specificity (descending)
        compiled_routes.sort(key=lambda r: r.specificity, reverse=True)
        
        compiled_controller = CompiledController(
            controller_class=controller_class,
            metadata=metadata,
            routes=compiled_routes,
        )
        
        # Cache it
        controller_key = f"{controller_class.__module__}:{controller_class.__name__}"
        self.compiled_controllers[controller_key] = compiled_controller
        
        return compiled_controller
    
    def _compile_route(
        self,
        controller_class: type,
        controller_metadata: ControllerMetadata,
        route_metadata: RouteMetadata,
    ) -> CompiledRoute:
        """Compile a single route."""
        # Build full path: prefix + route path
        prefix = controller_metadata.prefix.rstrip("/")
        route_path = route_metadata.path_template.lstrip("/") if route_metadata.path_template != "/" else ""
        
        # Handle edge cases
        if prefix and route_path:
            full_path = f"{prefix}/{route_path}"
        elif prefix:
            full_path = prefix or "/"
        else:
            full_path = f"/{route_path}" if route_path else "/"
        
        # Normalize path
        if full_path != "/" and full_path.endswith("/"):
            full_path = full_path.rstrip("/")
        
        # Convert to pattern format (« » style)
        pattern_path = self._convert_to_pattern_syntax(full_path, route_metadata)
        
        # Parse pattern
        try:
            ast = parse_pattern(pattern_path, inspect.getfile(controller_class))
        except Exception as e:
            raise PatternSemanticError(
                f"Failed to parse pattern '{pattern_path}': {e}",
                file=inspect.getfile(controller_class),
            )
        
        # Compile pattern
        compiled_pattern = self.pattern_compiler.compile(ast)
        
        # Calculate specificity
        specificity = route_metadata.specificity
        
        return CompiledRoute(
            controller_class=controller_class,
            controller_metadata=controller_metadata,
            route_metadata=route_metadata,
            compiled_pattern=compiled_pattern,
            full_path=full_path,
            http_method=route_metadata.http_method,
            specificity=specificity,
        )
    
    def _convert_to_pattern_syntax(
        self,
        path: str,
        route_metadata: RouteMetadata,
    ) -> str:
        """
        Convert path with parameters to pattern syntax.
        
        Converts:
        - /users/{id} -> /users/«id:int»
        - /posts/{slug} -> /posts/«slug:str»
        
        Uses parameter metadata to determine types.
        """
        pattern = path
        
        # Extract path parameters from metadata
        param_map = {}
        for param in route_metadata.parameters:
            if param.source == "path":
                # Determine pattern type
                type_str = self._python_type_to_pattern_type(param.type)
                param_map[param.name] = type_str
        
        # Replace {param} with «param:type»
        import re
        def replace_param(match):
            param_name = match.group(1)
            # Check for type annotation in original: {id:int}
            if ":" in param_name:
                name, type_hint = param_name.split(":", 1)
                return f"«{name}:{type_hint}»"
            else:
                # Use type from metadata
                param_type = param_map.get(param_name, "str")
                return f"«{param_name}:{param_type}»"
        
        pattern = re.sub(r'\{([^}]+)\}', replace_param, pattern)
        
        return pattern
    
    def _python_type_to_pattern_type(self, annotation: Any) -> str:
        """Convert Python type annotation to pattern type string."""
        if annotation is int or annotation == "int":
            return "int"
        elif annotation is float or annotation == "float":
            return "float"
        elif annotation is bool or annotation == "bool":
            return "bool"
        elif annotation is str or annotation == "str":
            return "str"
        else:
            # Default to string
            return "str"
    
    def check_conflicts(self, controllers: List[type]) -> List[Dict[str, Any]]:
        """
        Check for route conflicts across controllers.
        
        Args:
            controllers: List of controller classes
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        compiled_list = []
        
        # Compile all controllers
        for ctrl in controllers:
            compiled = self.compile_controller(ctrl)
            compiled_list.append(compiled)
        
        # Check for conflicts (same method + overlapping patterns)
        routes_by_method: Dict[str, List[CompiledRoute]] = {}
        
        for compiled in compiled_list:
            for route in compiled.routes:
                key = route.http_method
                if key not in routes_by_method:
                    routes_by_method[key] = []
                routes_by_method[key].append(route)
        
        # Check each method's routes for conflicts
        for method, routes in routes_by_method.items():
            for i, route1 in enumerate(routes):
                for route2 in routes[i + 1:]:
                    if self._routes_conflict(route1, route2):
                        conflicts.append({
                            "method": method,
                            "route1": {
                                "controller": route1.controller_class.__name__,
                                "path": route1.full_path,
                                "handler": route1.route_metadata.handler_name,
                            },
                            "route2": {
                                "controller": route2.controller_class.__name__,
                                "path": route2.full_path,
                                "handler": route2.route_metadata.handler_name,
                            },
                            "reason": "Ambiguous patterns could match same request",
                        })
        
        return conflicts
    
    def _routes_conflict(self, route1: CompiledRoute, route2: CompiledRoute) -> bool:
        """Check if two routes conflict (ambiguous matching)."""
        # Same exact path
        if route1.full_path == route2.full_path:
            return True
        
        # Check if patterns could overlap
        # This is a simplified check - real implementation would be more sophisticated
        parts1 = route1.full_path.split("/")
        parts2 = route2.full_path.split("/")
        
        if len(parts1) != len(parts2):
            return False
        
        # Check each segment
        for p1, p2 in zip(parts1, parts2):
            # Both static and different
            if "{" not in p1 and "{" not in p2 and p1 != p2:
                return False
            # Continue checking
        
        # Could potentially conflict
        return True
    
    def export_routes(self, controllers: List[type]) -> Dict[str, Any]:
        """
        Export all compiled routes for inspection/debugging.
        
        Args:
            controllers: List of controller classes
            
        Returns:
            Dict with controllers and routes
        """
        compiled = [self.compile_controller(ctrl) for ctrl in controllers]
        
        return {
            "controllers": [c.to_dict() for c in compiled],
            "total_routes": sum(len(c.routes) for c in compiled),
            "conflicts": self.check_conflicts(controllers),
        }
