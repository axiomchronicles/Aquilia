"""
Controller Router - Pattern-based router for controllers.

Integrates with:
- aquilia.patterns for URL matching
- aquilia.controller.compiler for route compilation
- aquilia.controller.engine for execution
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio

from .compiler import CompiledRoute, CompiledController
from ..patterns import PatternMatcher, MatchResult


@dataclass
class ControllerRouteMatch:
    """Result of a successful controller route match."""
    route: CompiledRoute
    params: Dict[str, Any]
    query: Dict[str, Any]


class ControllerRouter:
    """
    Router for controller-based routes using pattern matching.
    
    Uses aquilia.patterns for sophisticated URL matching with types,
    constraints, and validation.
    """
    
    def __init__(self):
        self.compiled_controllers: List[CompiledController] = []
        self.routes_by_method: Dict[str, List[CompiledRoute]] = {}
        self.matcher = PatternMatcher()
        self._initialized = False
    
    def add_controller(self, compiled_controller: CompiledController):
        """
        Add a compiled controller to the router.
        
        Args:
            compiled_controller: Compiled controller with routes
        """
        self.compiled_controllers.append(compiled_controller)
        
        # Add routes to method index
        for route in compiled_controller.routes:
            method = route.http_method
            if method not in self.routes_by_method:
                self.routes_by_method[method] = []
            self.routes_by_method[method].append(route)
        
        # Mark as not initialized (need to rebuild matcher)
        self._initialized = False
    
    def initialize(self):
        """
        Initialize the router (build pattern matcher).
        
        Must be called after all controllers are added and before matching.
        """
        if self._initialized:
            return
        
        # Clear matcher
        self.matcher = PatternMatcher()
        
        # Add all patterns sorted by specificity
        all_routes = []
        for routes in self.routes_by_method.values():
            all_routes.extend(routes)
        
        # Sort by specificity (descending)
        all_routes.sort(key=lambda r: r.specificity, reverse=True)
        
        # Add to matcher
        for route in all_routes:
            self.matcher.add_pattern(route.compiled_pattern)
        
        self._initialized = True
    
    async def match(
        self,
        path: str,
        method: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ControllerRouteMatch]:
        """
        Match a request to a controller route.
        
        Args:
            path: Request path
            method: HTTP method (GET, POST, etc.)
            query_params: Query string parameters
            
        Returns:
            ControllerRouteMatch if found, None otherwise
        """
        if not self._initialized:
            self.initialize()
        
        # Get routes for this method
        method_routes = self.routes_by_method.get(method, [])
        if not method_routes:
            return None
        
        # Try to match path against patterns
        query_params = query_params or {}
        
        # Try each route in specificity order
        for route in method_routes:
            # Use pattern matcher
            match_result = await self.matcher._try_match(
                route.compiled_pattern,
                path,
                query_params,
            )
            
            if match_result:
                return ControllerRouteMatch(
                    route=route,
                    params=match_result.params,
                    query=match_result.query,
                )
        
        return None
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """
        Get all registered routes.
        
        Returns:
            List of route information dicts
        """
        routes = []
        
        for controller in self.compiled_controllers:
            for route in controller.routes:
                routes.append({
                    "method": route.http_method,
                    "path": route.full_path,
                    "controller": route.controller_class.__name__,
                    "handler": route.route_metadata.handler_name,
                    "specificity": route.specificity,
                    "pipeline": [
                        p.__name__ if hasattr(p, "__name__") else str(p)
                        for p in (route.route_metadata.pipeline or [])
                    ],
                })
        
        return routes

    def get_routes_full(self) -> List[CompiledRoute]:
        """Get all CompiledRoute objects."""
        routes = []
        for controller in self.compiled_controllers:
            routes.extend(controller.routes)
        return routes
    
    def get_controller(self, name: str) -> Optional[CompiledController]:
        """
        Get compiled controller by name.
        
        Args:
            name: Controller class name
            
        Returns:
            CompiledController if found
        """
        for controller in self.compiled_controllers:
            if controller.controller_class.__name__ == name:
                return controller
        return None
    
    def has_route(self, method: str, path: str) -> bool:
        """
        Check if a route exists.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            True if route exists
        """
        match = asyncio.run(self.match(path, method))
        return match is not None
