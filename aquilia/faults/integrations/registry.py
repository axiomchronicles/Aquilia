"""
AquilaFaults - Registry Integration.

Integrates fault handling with Aquilary Registry system:
1. Replace bare exceptions with structured faults
2. Emit RegistryFault types for validation errors
3. Add fault handlers for registry operations

This module patches the RuntimeRegistry to use AquilaFaults.
"""

from typing import List, Dict, Any
from aquilia.faults import (
    FaultEngine,
    Fault,
    FaultDomain,
    Severity,
)
from aquilia.faults.domains import (
    RegistryFault,
    DependencyCycleFault,
    ManifestInvalidFault,
)


class ManifestLoadFault(RegistryFault):
    """Manifest loading failed."""
    
    def __init__(self, path: str, reason: str):
        super().__init__(
            code="MANIFEST_LOAD_FAILED",
            message=f"Failed to load manifest from '{path}': {reason}",
            metadata={"path": path, "reason": reason},
        )


class AppContextInvalidFault(RegistryFault):
    """App context validation failed."""
    
    def __init__(self, app_name: str, reason: str):
        super().__init__(
            code="APP_CONTEXT_INVALID",
            message=f"App context validation failed for '{app_name}': {reason}",
            metadata={"app_name": app_name, "reason": reason},
        )


class RouteCompilationFault(RegistryFault):
    """Route compilation failed."""
    
    def __init__(self, errors: List[str]):
        super().__init__(
            code="ROUTE_COMPILATION_FAILED",
            message=f"Route compilation failed with {len(errors)} error(s)",
            severity=Severity.ERROR,
            metadata={"errors": errors, "error_count": len(errors)},
        )


class DependencyResolutionFault(RegistryFault):
    """Dependency resolution failed."""
    
    def __init__(self, errors: List[str]):
        super().__init__(
            code="DEPENDENCY_RESOLUTION_FAILED",
            message=f"Dependency resolution failed with {len(errors)} error(s)",
            severity=Severity.ERROR,
            metadata={"errors": errors, "error_count": len(errors)},
        )


def patch_runtime_registry():
    """
    Patch RuntimeRegistry to emit structured faults.
    
    Replaces bare exceptions with AquilaFaults:
    - ValueError → AppContextInvalidFault
    - RuntimeError (routes) → RouteCompilationFault
    - RuntimeError (dependencies) → DependencyResolutionFault
    - DependencyCycleError → DependencyCycleFault (already exists)
    """
    from aquilia.aquilary.core import RuntimeRegistry
    
    # Store original methods
    original_compile_routes = RuntimeRegistry.compile_routes
    original_ensure_dependencies_ready = RuntimeRegistry.ensure_dependencies_ready
    
    def patched_compile_routes(self):
        """Patched compile_routes with fault handling."""
        try:
            return original_compile_routes(self)
        except RuntimeError as e:
            # Extract error messages if present
            msg = str(e)
            if "Route compilation failed:" in msg:
                errors = msg.split("\\n")[1:]  # Skip first line
                raise RouteCompilationFault(errors) from e
            raise
    
    def patched_ensure_dependencies_ready(self):
        """Patched ensure_dependencies_ready with fault handling."""
        try:
            return original_ensure_dependencies_ready(self)
        except RuntimeError as e:
            # Extract error messages if present
            msg = str(e)
            if "Dependency resolution failed:" in msg:
                errors = msg.split("\\n")[1:]  # Skip first line
                raise DependencyResolutionFault(errors) from e
            raise
    
    # Apply patches
    RuntimeRegistry.compile_routes = patched_compile_routes
    RuntimeRegistry.ensure_dependencies_ready = patched_ensure_dependencies_ready


def create_registry_fault_handler():
    """
    Create fault handler for registry operations.
    
    Returns a handler that converts registry faults to structured responses.
    """
    from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved
    
    class RegistryFaultHandler(FaultHandler):
        """Handle registry-specific faults."""
        
        def can_handle(self, ctx: FaultContext) -> bool:
            return ctx.fault.domain == FaultDomain.REGISTRY
        
        async def handle(self, ctx: FaultContext) -> FaultResult:
            """Log registry fault and resolve with diagnostic info."""
            fault = ctx.fault
            
            response = {
                "error": "registry_fault",
                "code": fault.code,
                "message": fault.message,
                "metadata": fault.metadata,
                "trace_id": ctx.trace_id,
            }
            
            return Resolved(response)
    
    return RegistryFaultHandler()


# Auto-patch on import (optional - can be called explicitly)
# patch_runtime_registry()
