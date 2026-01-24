"""
Route Compiler - Extracts routes from controllers and compiles route table.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path
from .handler_wrapper import wrap_handler


@dataclass
class RouteInfo:
    """Information about a single route."""
    pattern: str
    method: str
    handler: Any  # The bound method
    controller_class: type
    flow: Any  # Flow object if available
    metadata: Dict[str, Any]


@dataclass
class RouteTable:
    """Compiled routing table."""
    routes: List[RouteInfo]
    patterns: Dict[str, RouteInfo]  # pattern:method -> RouteInfo
    conflicts: List[Tuple[RouteInfo, RouteInfo]]  # Conflicting routes


class RouteConflictError(Exception):
    """Raised when route patterns conflict."""
    pass


class RouteCompiler:
    """
    Compiles routes from controller classes.
    Extracts @flow decorators and builds routing table.
    """
    
    def __init__(self):
        self.routes: List[RouteInfo] = []
        self.patterns: Dict[str, RouteInfo] = {}
        self.conflicts: List[Tuple[RouteInfo, RouteInfo]] = []
    
    def compile_controller(self, controller_path: str, config: Any = None) -> List[RouteInfo]:
        """
        Compile routes from a controller module or class.
        
        Supports two formats:
        - "module.path" - Import module and find all controllers
        - "module.path:ClassName" - Import specific controller class
        
        Args:
            controller_path: Import path like "apps.auth.controllers" or "apps.auth.controllers:AuthController"
            config: Optional config for DI
            
        Returns:
            List of extracted routes
        """
        routes = []
        
        try:
            # Check if this is a specific class import (module:Class format)
            if ":" in controller_path:
                module_path, class_name = controller_path.rsplit(":", 1)
                module = importlib.import_module(module_path)
                
                # Get the specific class
                if not hasattr(module, class_name):
                    raise AttributeError(f"Class '{class_name}' not found in module '{module_path}'")
                
                controller_class = getattr(module, class_name)
                if not inspect.isclass(controller_class):
                    raise TypeError(f"{class_name} is not a class")
                
                # Extract routes from this specific controller
                routes.extend(self._extract_routes_from_controller(controller_class, config))
            else:
                # Original behavior: Import module and find all controllers
                module = importlib.import_module(controller_path)
                
                # Find controller classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name.endswith("Controller") and obj.__module__ == module.__name__:
                        routes.extend(self._extract_routes_from_controller(obj, config))
        
        except Exception as e:
            raise ImportError(f"Failed to import controller {controller_path}: {e}") from e
        
        return routes
    
    def _extract_routes_from_controller(self, controller_class: type, config: Any) -> List[RouteInfo]:
        """Extract routes from a controller class."""
        routes = []
        
        # Instantiate controller (needed for bound methods)
        try:
            controller_instance = controller_class()
        except Exception as e:
            # If controller needs DI, we'll handle that later
            controller_instance = None
        
        # Find methods with flow decorators
        for name, method in inspect.getmembers(controller_class, inspect.isfunction):
            if hasattr(method, "__flow__"):
                flow = getattr(method, "__flow__")
                
                # Get handler (bound method if instance available)
                raw_handler = method if controller_instance is None else getattr(controller_instance, name)
                
                # Wrap handler for DI injection
                wrapped_handler = wrap_handler(raw_handler, controller_class)
                
                # Extract route info
                route_info = RouteInfo(
                    pattern=flow.pattern,
                    method=flow.method,
                    handler=wrapped_handler,  # Use wrapped handler
                    controller_class=controller_class,
                    flow=flow,
                    metadata={
                        "handler_name": name,
                        "module": controller_class.__module__,
                        "class": controller_class.__name__,
                        "wrapped": True,  # Mark as wrapped for DI
                    }
                )
                
                routes.append(route_info)
                
                # Check for conflicts
                key = f"{route_info.pattern}:{route_info.method}"
                if key in self.patterns:
                    self.conflicts.append((self.patterns[key], route_info))
                else:
                    self.patterns[key] = route_info
        
        return routes
    
    def compile_from_manifests(self, manifests: List[Dict[str, Any]], config: Any = None) -> RouteTable:
        """
        Compile routes from app manifests.
        
        Args:
            manifests: List of app manifest dicts
            config: Optional config object
            
        Returns:
            Compiled route table
        """
        all_routes = []
        
        for manifest in manifests:
            app_name = manifest.get("name")
            controllers = manifest.get("controllers", [])
            
            for controller_path in controllers:
                # If relative import, make absolute based on app structure
                if not controller_path.startswith("."):
                    # Assume pattern: apps.<app_name>.controllers
                    if not "." in controller_path:
                        controller_path = f"apps.{app_name}.controllers"
                
                try:
                    routes = self.compile_controller(controller_path, config)
                    all_routes.extend(routes)
                except Exception as e:
                    print(f"Warning: Failed to compile controller {controller_path}: {e}")
        
        self.routes = all_routes
        
        return RouteTable(
            routes=all_routes,
            patterns=self.patterns.copy(),
            conflicts=self.conflicts.copy(),
        )
    
    def validate_routes(self) -> List[str]:
        """
        Validate compiled routes.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for conflicts
        if self.conflicts:
            for route1, route2 in self.conflicts:
                errors.append(
                    f"Route conflict: {route1.pattern} [{route1.method}] "
                    f"defined in {route1.metadata['module']}.{route1.metadata['class']} "
                    f"and {route2.metadata['module']}.{route2.metadata['class']}"
                )
        
        # Check for invalid patterns
        for route in self.routes:
            if not route.pattern.startswith("/"):
                errors.append(
                    f"Invalid route pattern '{route.pattern}' in "
                    f"{route.metadata['module']}.{route.metadata['class']}: "
                    "Pattern must start with '/'"
                )
        
        return errors
    
    def get_route_count(self) -> int:
        """Get total number of routes."""
        return len(self.routes)
    
    def get_routes_by_method(self, method: str) -> List[RouteInfo]:
        """Get all routes for a specific HTTP method."""
        return [r for r in self.routes if r.method == method.upper()]
    
    def get_routes_by_pattern(self, pattern: str) -> List[RouteInfo]:
        """Get all routes matching a pattern."""
        return [r for r in self.routes if r.pattern == pattern]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export route table as dictionary."""
        return {
            "total_routes": len(self.routes),
            "routes": [
                {
                    "pattern": r.pattern,
                    "method": r.method,
                    "handler": f"{r.metadata['module']}.{r.metadata['class']}.{r.metadata['handler_name']}",
                    "controller": r.metadata['class'],
                }
                for r in self.routes
            ],
            "conflicts": len(self.conflicts),
        }
