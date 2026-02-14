"""
AquilaFaults - Subsystem Integrations.

Integration modules for connecting AquilaFaults with Aquilia subsystems:
- registry: Registry validation and manifest loading faults
- di: Dependency injection resolution faults
- routing: Route matching and pattern validation faults
- flow: Request/response pipeline and middleware faults

Usage:
    ```python
    from aquilia.faults.integrations import (
        patch_runtime_registry,
        patch_di_container,
        fault_handling_middleware,
        create_routing_fault_handler,
    )
    
    # Patch subsystems
    patch_runtime_registry()
    patch_di_container()
    
    # Register handlers
    engine.register_global(create_routing_fault_handler())
    ```
"""

from .registry import (
    ManifestLoadFault,
    AppContextInvalidFault,
    RouteCompilationFault,
    DependencyResolutionFault,
    patch_runtime_registry,
    create_registry_fault_handler,
)

from .di import (
    CircularDependencyFault,
    ProviderRegistrationFault,
    AsyncResolutionFault,
    patch_di_container,
    create_di_fault_handler,
)

from .routing import (
    RouteConflictFault,
    MethodNotAllowedFault,
    RouteParameterFault,
    create_routing_fault_handler,
    safe_route_lookup,
    validate_route_pattern,
)

from .models import (
    ModelFaultHandler,
    create_model_fault_handler,
    patch_model_registry,
    patch_database_engine,
    patch_all_model_subsystems,
)

# Flow integration removed - flows are deprecated in favor of controllers
# from .flow import (
#     PipelineAbortedFault,
#     HandlerTimeoutFault,
#     MiddlewareChainFault,
#     fault_handling_middleware,
#     timeout_middleware,
#     fault_aware_handler,
#     create_flow_fault_handler,
#     with_cancellation_handling,
#     is_fault_retryable,
#     should_abort_pipeline,
# )


__all__ = [
    # Registry
    "ManifestLoadFault",
    "AppContextInvalidFault",
    "RouteCompilationFault",
    "DependencyResolutionFault",
    "patch_runtime_registry",
    "create_registry_fault_handler",
    
    # DI
    "CircularDependencyFault",
    "ProviderRegistrationFault",
    "AsyncResolutionFault",
    "patch_di_container",
    "create_di_fault_handler",
    
    # Routing
    "RouteConflictFault",
    "MethodNotAllowedFault",
    "RouteParameterFault",
    "create_routing_fault_handler",
    "safe_route_lookup",
    "validate_route_pattern",
    
    # Models
    "ModelFaultHandler",
    "create_model_fault_handler",
    "patch_model_registry",
    "patch_database_engine",
    "patch_all_model_subsystems",
]


# Convenience function to patch all subsystems
def patch_all_subsystems():
    """
    Patch all Aquilia subsystems to use AquilaFaults.
    
    Call this once at application startup to enable
    structured fault handling throughout the system.
    """
    patch_runtime_registry()
    patch_di_container()
    patch_all_model_subsystems()


# Convenience function to create all integration handlers
def create_all_integration_handlers():
    """
    Create fault handlers for all subsystem integrations.
    
    Returns:
        List of FaultHandler instances
    """
    return [
        create_registry_fault_handler(),
        create_di_fault_handler(),
        create_routing_fault_handler(),
        create_model_fault_handler(),
    ]
