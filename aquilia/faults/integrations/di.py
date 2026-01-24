"""
AquilaFaults - DI Integration.

Integrates fault handling with Dependency Injection system:
1. Replace ProviderNotFoundError with ProviderNotFoundFault
2. Add scope violation faults
3. Integrate with DI resolution lifecycle

This module patches the DI Container to use AquilaFaults.
"""

from typing import Optional, List, Any
from aquilia.faults import (
    FaultEngine,
    Fault,
    FaultDomain,
    Severity,
)
from aquilia.faults.domains import (
    DIFault,
    ProviderNotFoundFault,
    ScopeViolationFault,
    DIResolutionFault,
)


class CircularDependencyFault(DIFault):
    """Circular dependency detected."""
    
    def __init__(self, cycle: List[str]):
        cycle_str = " → ".join(cycle)
        super().__init__(
            code="CIRCULAR_DEPENDENCY",
            message=f"Circular dependency detected: {cycle_str}",
            severity=Severity.ERROR,
            metadata={"cycle": cycle, "cycle_length": len(cycle)},
        )


class ProviderRegistrationFault(DIFault):
    """Provider registration failed."""
    
    def __init__(self, token: str, reason: str):
        super().__init__(
            code="PROVIDER_REGISTRATION_FAILED",
            message=f"Failed to register provider for '{token}': {reason}",
            metadata={"token": token, "reason": reason},
        )


class AsyncResolutionFault(DIFault):
    """Async resolution in sync context."""
    
    def __init__(self, token: str):
        super().__init__(
            code="ASYNC_RESOLUTION_IN_SYNC_CONTEXT",
            message=f"Cannot resolve async provider '{token}' in sync context; use await resolve_async()",
            severity=Severity.ERROR,
            metadata={"token": token},
        )


def patch_di_container():
    """
    Patch DI Container to emit structured faults.
    
    Replaces bare exceptions with AquilaFaults:
    - ProviderNotFoundError → ProviderNotFoundFault (already exists)
    - RuntimeError (async) → AsyncResolutionFault
    - ValueError (registration) → ProviderRegistrationFault
    """
    from aquilia.di.core import Container
    from aquilia.di.errors import ProviderNotFoundError as OldProviderNotFoundError
    
    # Store original methods
    original_resolve = Container.resolve
    original_resolve_async = Container.resolve_async
    original_register = Container.register
    
    def patched_resolve(self, token, *, tag=None, optional=False):
        """Patched resolve with fault handling."""
        try:
            return original_resolve(self, token, tag=tag, optional=optional)
        except OldProviderNotFoundError as e:
            # Convert to structured fault
            raise ProviderNotFoundFault(
                token=str(token),
                tag=tag,
                candidates=e.candidates if hasattr(e, 'candidates') else [],
            ) from e
        except RuntimeError as e:
            msg = str(e)
            if "resolve() called from async context" in msg:
                raise AsyncResolutionFault(token=str(token)) from e
            raise
    
    async def patched_resolve_async(self, token, *, tag=None, optional=False):
        """Patched resolve_async with fault handling."""
        try:
            return await original_resolve_async(self, token, tag=tag, optional=optional)
        except OldProviderNotFoundError as e:
            # Convert to structured fault
            raise ProviderNotFoundFault(
                token=str(token),
                tag=tag,
                candidates=e.candidates if hasattr(e, 'candidates') else [],
            ) from e
    
    def patched_register(self, provider):
        """Patched register with fault handling."""
        try:
            return original_register(self, provider)
        except ValueError as e:
            # Extract token from error message
            msg = str(e)
            token = "unknown"
            if "already registered" in msg:
                # Try to extract token
                import re
                match = re.search(r"'([^']+)' already registered", msg)
                if match:
                    token = match.group(1)
            
            raise ProviderRegistrationFault(token=token, reason=msg) from e
    
    # Apply patches
    Container.resolve = patched_resolve
    Container.resolve_async = patched_resolve_async
    Container.register = patched_register


def create_di_fault_handler():
    """
    Create fault handler for DI operations.
    
    Returns a handler that converts DI faults to structured responses.
    """
    from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved
    
    class DIFaultHandler(FaultHandler):
        """Handle DI-specific faults."""
        
        def can_handle(self, ctx: FaultContext) -> bool:
            return ctx.fault.domain == FaultDomain.DI
        
        async def handle(self, ctx: FaultContext) -> FaultResult:
            """Log DI fault and resolve with diagnostic info."""
            fault = ctx.fault
            
            # Build helpful response
            response = {
                "error": "dependency_injection_fault",
                "code": fault.code,
                "message": fault.message,
                "metadata": fault.metadata,
                "trace_id": ctx.trace_id,
            }
            
            # Add suggestions for common issues
            if fault.code == "PROVIDER_NOT_FOUND":
                response["suggestions"] = [
                    "Register a provider for this token",
                    "Check if the provider is in the correct scope",
                    "Verify the token name matches exactly",
                ]
            elif fault.code == "CIRCULAR_DEPENDENCY":
                response["suggestions"] = [
                    "Break the cycle by using lazy injection",
                    "Use a factory or service locator pattern",
                    "Reconsider the dependency structure",
                ]
            elif fault.code == "SCOPE_VIOLATION":
                response["suggestions"] = [
                    "Use a compatible scope (e.g., request → transient)",
                    "Convert singleton to request-scoped",
                    "Use a provider pattern for scope bridging",
                ]
            
            return Resolved(response)
    
    return DIFaultHandler()


# Auto-patch on import (optional - can be called explicitly)
# patch_di_container()
