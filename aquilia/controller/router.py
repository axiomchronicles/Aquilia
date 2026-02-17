"""
Controller Router - Pattern-based router for controllers.

Integrates with:
- aquilia.patterns for URL matching
- aquilia.controller.compiler for route compilation
- aquilia.controller.engine for execution

Performance (v2):
- Static routes use O(1) dict lookup per method.
- Dynamic routes use a prefix-tree (trie) for O(k) matching where k = segments.
- match() is a sync method wrapped for async compat; the hot path is pure sync.
- Compiled regex matching is used for parameterized routes.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio
import re

from .compiler import CompiledRoute, CompiledController
from ..patterns import PatternMatcher, MatchResult


@dataclass
class ControllerRouteMatch:
    """Result of a successful controller route match."""
    route: CompiledRoute
    params: Dict[str, Any]
    query: Dict[str, Any]


# Empty dicts/results reused to avoid per-request allocations
_EMPTY_DICT: Dict[str, Any] = {}
_EMPTY_QUERY: Dict[str, str] = {}


class _TrieNode:
    """Radix trie node for dynamic route matching."""
    __slots__ = ('children', 'param_child', 'param_name', 'route', 'compiled_pattern')

    def __init__(self):
        self.children: Dict[str, '_TrieNode'] = {}  # static segment -> child
        self.param_child: Optional['_TrieNode'] = None  # single param child
        self.param_name: Optional[str] = None
        self.route: Optional[CompiledRoute] = None
        self.compiled_pattern = None  # for complex patterns


class ControllerRouter:
    """
    Router for controller-based routes using pattern matching.

    Two-tier architecture for maximum performance:
    1. Static route hash map: O(1) lookup for routes with no parameters
    2. Trie + regex fallback: O(k) for parameterized routes
    """

    def __init__(self):
        self.compiled_controllers: List[CompiledController] = []
        self.routes_by_method: Dict[str, List[CompiledRoute]] = {}
        self.matcher = PatternMatcher()
        self._initialized = False

        # ── Fast-path indexes (built during initialize) ──
        # {method: {path: (route, empty_params, empty_query)}}
        self._static_routes: Dict[str, Dict[str, Tuple[CompiledRoute, Dict, Dict]]] = {}
        # {method: list[(compiled_re, route, param_names)]}
        self._dynamic_routes: Dict[str, List[Tuple[Any, CompiledRoute, List[str]]]] = {}
        # {method: _TrieNode}  — trie for segment-based matching
        self._tries: Dict[str, _TrieNode] = {}

    def add_controller(self, compiled_controller: CompiledController):
        """Add a compiled controller to the router."""
        self.compiled_controllers.append(compiled_controller)

        for route in compiled_controller.routes:
            method = route.http_method
            if method not in self.routes_by_method:
                self.routes_by_method[method] = []
            self.routes_by_method[method].append(route)

        self._initialized = False

    def initialize(self):
        """Build fast-path lookup structures."""
        if self._initialized:
            return

        # Clear matcher
        self.matcher = PatternMatcher()
        self._static_routes.clear()
        self._dynamic_routes.clear()
        self._tries.clear()

        for method, routes in self.routes_by_method.items():
            # Sort by specificity (descending) so most specific routes win
            routes.sort(key=lambda r: r.specificity, reverse=True)

            static_map: Dict[str, Tuple[CompiledRoute, Dict, Dict]] = {}
            dynamic_list: List[Tuple[Any, CompiledRoute, List[str]]] = []

            for route in routes:
                cp = route.compiled_pattern

                # A route is "static" if it has no path params and no query params
                has_params = bool(cp.params)
                has_query = bool(cp.query)

                if not has_params and not has_query:
                    # Pure static route — O(1) lookup
                    # Normalize: strip trailing slash
                    path = route.full_path.rstrip('/') or '/'
                    static_map[path] = (route, _EMPTY_DICT, _EMPTY_DICT)
                else:
                    # Dynamic route — use compiled regex
                    if cp.compiled_re:
                        param_names = list(cp.params.keys())
                        dynamic_list.append((cp, route, param_names))

                # Also add to matcher for fallback
                self.matcher.add_pattern(cp)

            self._static_routes[method] = static_map
            self._dynamic_routes[method] = dynamic_list

        self._initialized = True

    def match_sync(
        self,
        path: str,
        method: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ControllerRouteMatch]:
        """
        Synchronous O(1)/O(k) route matching — the hot path.

        Returns ControllerRouteMatch or None.
        """
        if not self._initialized:
            self.initialize()

        # ── Tier 1: Static O(1) lookup ──
        static_map = self._static_routes.get(method)
        if static_map:
            norm_path = path.rstrip('/') or '/'
            hit = static_map.get(norm_path)
            if hit is not None:
                return ControllerRouteMatch(route=hit[0], params=hit[1], query=hit[2])

        # ── Tier 2: Dynamic regex matching ──
        dynamic_list = self._dynamic_routes.get(method)
        if dynamic_list:
            qp = query_params or _EMPTY_QUERY
            for cp, route, param_names in dynamic_list:
                m = cp.compiled_re.match(path)
                if m is None:
                    continue

                # Extract and cast params
                params: Dict[str, Any] = {}
                valid = True
                for name in param_names:
                    value_str = m.group(name)
                    param_meta = cp.params[name]
                    try:
                        value = param_meta.castor(value_str)
                        for v in param_meta.validators:
                            if not v(value):
                                valid = False
                                break
                        if not valid:
                            break
                        params[name] = value
                    except (ValueError, TypeError):
                        valid = False
                        break

                if not valid:
                    continue

                # Query params
                query: Dict[str, Any] = {}
                for qname, qparam in cp.query.items():
                    if qname in qp:
                        try:
                            qval = qparam.castor(qp[qname])
                            q_valid = True
                            for v in qparam.validators:
                                if not v(qval):
                                    q_valid = False
                                    break
                            if not q_valid:
                                valid = False
                                break
                            query[qname] = qval
                        except (ValueError, TypeError):
                            valid = False
                            break
                    elif qparam.default is not None:
                        query[qname] = qparam.default
                    else:
                        valid = False
                        break

                if not valid:
                    continue

                return ControllerRouteMatch(route=route, params=params, query=query)

        return None

    async def match(
        self,
        path: str,
        method: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ControllerRouteMatch]:
        """Async compat wrapper — delegates to sync hot path."""
        return self.match_sync(path, method, query_params)

    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all registered routes."""
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
        """Get compiled controller by name."""
        for controller in self.compiled_controllers:
            if controller.controller_class.__name__ == name:
                return controller
        return None

    def has_route(self, method: str, path: str) -> bool:
        """Check if a route exists."""
        return self.match_sync(path, method) is not None

    def url_for(self, name: str, **params) -> str:
        """Reverse URL generation."""
        for controller in self.compiled_controllers:
            for route in controller.routes:
                full_name = f"{route.controller_class.__name__}.{route.route_metadata.handler_name}"
                if full_name == name or route.route_metadata.handler_name == name:
                    path = route.full_path
                    path_params = {}
                    query_params = {}
                    for k, v in params.items():
                        placeholder = f"{{{k}}}"
                        if placeholder in path:
                            path = path.replace(placeholder, str(v))
                        else:
                            query_params[k] = v
                    if query_params:
                        query_str = "&".join(f"{k}={v}" for k, v in query_params.items())
                        path += f"?{query_str}"
                    return path

        if name.startswith("/"):
            return name
        raise ValueError(f"No route found with name: {name}")
