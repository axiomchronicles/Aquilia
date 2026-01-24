"""
AquilaFaults - Routing Integration.

Integrates fault handling with routing system:
1. Return RoutingFault instead of throwing exceptions
2. Pattern validation faults
3. Route conflict detection

This module provides routing fault types and integration utilities.
"""

from typing import Optional, List, Dict, Any
from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
)
from aquilia.faults.domains import (
    RoutingFault,
    RouteNotFoundFault,
    RouteAmbiguousFault,
    PatternInvalidFault,
)


class RouteConflictFault(RoutingFault):
    """Multiple routes match the same pattern."""
    
    def __init__(self, pattern: str, conflicts: List[str]):
        super().__init__(
            code="ROUTE_CONFLICT",
            message=f"Multiple routes conflict on pattern '{pattern}'",
            severity=Severity.ERROR,
            metadata={
                "pattern": pattern,
                "conflicts": conflicts,
                "conflict_count": len(conflicts),
            },
        )


class MethodNotAllowedFault(RoutingFault):
    """HTTP method not allowed for route."""
    
    def __init__(self, method: str, path: str, allowed_methods: List[str]):
        super().__init__(
            code="METHOD_NOT_ALLOWED",
            message=f"Method {method} not allowed for {path}",
            severity=Severity.WARN,
            public=True,
            metadata={
                "method": method,
                "path": path,
                "allowed_methods": allowed_methods,
            },
        )


class RouteParameterFault(RoutingFault):
    """Route parameter validation failed."""
    
    def __init__(self, param_name: str, value: Any, expected_type: str):
        super().__init__(
            code="ROUTE_PARAMETER_INVALID",
            message=f"Route parameter '{param_name}' invalid: expected {expected_type}, got {type(value).__name__}",
            severity=Severity.ERROR,
            public=True,
            metadata={
                "param_name": param_name,
                "value": str(value),
                "expected_type": expected_type,
                "actual_type": type(value).__name__,
            },
        )


def create_routing_fault_handler():
    """
    Create fault handler for routing operations.
    
    Maps routing faults to appropriate HTTP responses.
    """
    from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved
    from aquilia.faults.default_handlers import HTTPResponse
    
    class RoutingFaultHandler(FaultHandler):
        """Handle routing-specific faults."""
        
        def can_handle(self, ctx: FaultContext) -> bool:
            return ctx.fault.domain == FaultDomain.ROUTING
        
        async def handle(self, ctx: FaultContext) -> FaultResult:
            """Map routing fault to HTTP response."""
            fault = ctx.fault
            
            # Determine status code
            status_map = {
                "ROUTE_NOT_FOUND": 404,
                "ROUTE_AMBIGUOUS": 500,
                "PATTERN_INVALID": 500,
                "ROUTE_CONFLICT": 500,
                "METHOD_NOT_ALLOWED": 405,
                "ROUTE_PARAMETER_INVALID": 400,
            }
            
            status = status_map.get(fault.code, 500)
            
            # Build response
            body = {
                "error": {
                    "code": fault.code,
                    "message": fault.message if fault.public else "Internal server error",
                    "domain": fault.domain.value,
                }
            }
            
            # Add trace_id
            if ctx.trace_id:
                body["error"]["trace_id"] = ctx.trace_id
            
            # Add method suggestions for 405
            if fault.code == "METHOD_NOT_ALLOWED":
                body["error"]["allowed_methods"] = fault.metadata.get("allowed_methods", [])
            
            # Add parameter hints for 400
            if fault.code == "ROUTE_PARAMETER_INVALID":
                body["error"]["parameter"] = fault.metadata.get("param_name")
                body["error"]["expected_type"] = fault.metadata.get("expected_type")
            
            headers = {"Content-Type": "application/json"}
            
            # Add Allow header for 405
            if fault.code == "METHOD_NOT_ALLOWED":
                allowed = fault.metadata.get("allowed_methods", [])
                headers["Allow"] = ", ".join(allowed)
            
            response = HTTPResponse(
                status_code=status,
                body=body,
                headers=headers,
            )
            
            return Resolved(response)
    
    return RoutingFaultHandler()


# Routing utilities

def safe_route_lookup(router, path: str, method: str = "GET"):
    """
    Safely lookup route, returning fault instead of throwing.
    
    Args:
        router: Router instance
        path: Request path
        method: HTTP method
    
    Returns:
        Route object or RoutingFault
    """
    try:
        # Try to find route
        route = router.match(path, method)
        if route is None:
            return RouteNotFoundFault(path=path, method=method)
        return route
    except Exception as e:
        # Convert exception to fault
        return RoutingFault(
            code="ROUTE_LOOKUP_ERROR",
            message=f"Error looking up route: {str(e)}",
            severity=Severity.ERROR,
        )


def validate_route_pattern(pattern: str) -> Optional[PatternInvalidFault]:
    """
    Validate route pattern syntax.
    
    Args:
        pattern: Route pattern (e.g., "/users/:id")
    
    Returns:
        PatternInvalidFault if invalid, None if valid
    """
    import re
    
    # Check for valid characters
    if not re.match(r'^[/a-zA-Z0-9:_\-\*\{\}]*$', pattern):
        return PatternInvalidFault(
            pattern=pattern,
            reason="Invalid characters in pattern",
        )
    
    # Check for balanced braces
    if pattern.count('{') != pattern.count('}'):
        return PatternInvalidFault(
            pattern=pattern,
            reason="Unbalanced braces in pattern",
        )
    
    # Check for valid parameter names
    params = re.findall(r':([a-zA-Z_][a-zA-Z0-9_]*)', pattern)
    if len(params) != len(set(params)):
        return PatternInvalidFault(
            pattern=pattern,
            reason="Duplicate parameter names",
        )
    
    return None
