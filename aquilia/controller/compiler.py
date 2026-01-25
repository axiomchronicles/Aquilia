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
    
    def compile_controller(
        self, 
        controller_class: type,
        base_prefix: Optional[str] = None,
    ) -> CompiledController:
        """
        Compile a controller class into routes.
        
        Args:
            controller_class: Controller class to compile
            base_prefix: Optional base prefix from module/app
            
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
                    base_prefix=base_prefix,
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
        base_prefix: Optional[str] = None,
    ) -> CompiledRoute:
        """Compile a single route."""
        from aquilia.utils.urls import join_paths
        
        # Build components
        base = base_prefix or ""
        ctrl_prefix = controller_metadata.prefix or ""
        route_path = route_metadata.path_template or ""
        
        # Robust join
        full_path = join_paths(base, ctrl_prefix, route_path)
        
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
    
    def validate_route_tree(self, compiled_controllers: List[CompiledController]) -> List[Dict[str, Any]]:
        """
        Validate the entire compiled route tree for conflicts.
        
        This is the preferred validation method as it accounts for 
        applied prefixes and mounted locations.
        
        Args:
            compiled_controllers: List of already compiled controllers
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        routes_by_method: Dict[str, List[CompiledRoute]] = {}
        
        # Group by method
        for compiled in compiled_controllers:
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
                                "module": route1.controller_class.__module__,
                            },
                            "route2": {
                                "controller": route2.controller_class.__name__,
                                "path": route2.full_path,
                                "handler": route2.route_metadata.handler_name,
                                "module": route2.controller_class.__module__,
                            },
                            "reason": "Ambiguous patterns could match same request",
                        })
        return conflicts

    def check_conflicts(self, controllers: List[type]) -> List[Dict[str, Any]]:
        """
        Check for route conflicts across controllers (Legacy).
        
        WARNING: This assumes NO module prefixes. For robust checking,
        use validate_route_tree() with compiled controllers.
        
        Args:
            controllers: List of controller classes
            
        Returns:
            List of conflict descriptions
        """
        # Compile all controllers (without prefixes)
        compiled_list = [self.compile_controller(ctrl) for ctrl in controllers]
        return self.validate_route_tree(compiled_list)
    
    def _routes_conflict(self, route1: CompiledRoute, route2: CompiledRoute) -> bool:
        """Check if two routes conflict (ambiguous matching)."""
        # Same exact path
        if route1.full_path == route2.full_path:
            return True
        
        # Check if patterns could overlap
        parts1 = list(filter(None, route1.full_path.split("/")))
        parts2 = list(filter(None, route2.full_path.split("/")))
        
        if len(parts1) != len(parts2):
            return False
        
        # Helper to extract type from "«name:type»" or return None if static
        def get_segment_info(segment):
            if segment.startswith("«") and segment.endswith("»"):
                content = segment[1:-1]
                if ":" in content:
                    _, type_str = content.split(":", 1)
                    return "dynamic", type_str
                return "dynamic", "str"
            return "static", segment

        # Check each segment
        for p1, p2 in zip(parts1, parts2):
            kind1, info1 = get_segment_info(p1)
            kind2, info2 = get_segment_info(p2)
            
            # Both static
            if kind1 == "static" and kind2 == "static":
                if info1 != info2:
                    return False # Distinct static paths
            
            # One static, one dynamic
            elif kind1 == "static" and kind2 == "dynamic":
                if info2 == "int" and not info1.isdigit():
                    return False # Static is not int
                # If dynamic is string, it overlaps with any static string
                
            elif kind1 == "dynamic" and kind2 == "static":
                if info1 == "int" and not info2.isdigit():
                    return False # Static is not int
            
            # Both dynamic
            else:
                # If different types (e.g. int vs bool), might not conflict?
                # But widely overlapping types (str vs int) do conflict for numbers.
                # Assuming conflict for safety if both are dynamic at same pos.
                pass
                
        # If we got here, all segments potentially overlap
        return True
    
    def export_routes(self, controllers: List[CompiledController]) -> Dict[str, Any]:
        """
        Export all compiled routes for inspection/debugging.
        
        Args:
            controllers: List of CompiledController
            
        Returns:
            Dict with controllers and routes
        """
        return {
            "controllers": [c.to_dict() for c in controllers],
            "total_routes": sum(len(c.routes) for c in controllers),
            "conflicts": self.validate_route_tree(controllers),
        }
