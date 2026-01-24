"""
AquilaFaults - Flow Engine Integration.

Integrates fault handling with flow engine (request/response pipeline):
1. Support returning Faults from handlers
2. Middleware fault handling capabilities
3. Flow cancellation awareness

This module provides flow integration utilities and middleware.
"""

import asyncio
from typing import Any, Optional, Callable, Awaitable
from aquilia.faults import (
    FaultEngine,
    Fault,
    FaultContext,
    FaultResult,
    Resolved,
    Transformed,
    Escalate,
    FaultDomain,
    Severity,
)
from aquilia.faults.domains import (
    FlowFault,
    HandlerFault,
    MiddlewareFault,
    FlowCancelledFault,
)


class PipelineAbortedFault(FlowFault):
    """Request pipeline aborted by middleware."""
    
    def __init__(self, middleware_name: str, reason: str):
        super().__init__(
            code="PIPELINE_ABORTED",
            message=f"Pipeline aborted by middleware '{middleware_name}': {reason}",
            severity=Severity.WARN,
            metadata={
                "middleware": middleware_name,
                "reason": reason,
            },
        )


class HandlerTimeoutFault(FlowFault):
    """Handler execution timed out."""
    
    def __init__(self, handler_name: str, timeout_seconds: float):
        super().__init__(
            code="HANDLER_TIMEOUT",
            message=f"Handler '{handler_name}' timed out after {timeout_seconds}s",
            severity=Severity.ERROR,
            retryable=True,
            metadata={
                "handler": handler_name,
                "timeout": timeout_seconds,
            },
        )


class MiddlewareChainFault(FlowFault):
    """Middleware chain execution failed."""
    
    def __init__(self, failed_middleware: str, reason: str):
        super().__init__(
            code="MIDDLEWARE_CHAIN_FAILED",
            message=f"Middleware chain failed at '{failed_middleware}': {reason}",
            severity=Severity.ERROR,
            metadata={
                "middleware": failed_middleware,
                "reason": reason,
            },
        )


# ============================================================================
# Fault-Aware Middleware
# ============================================================================

async def fault_handling_middleware(
    request,
    next_handler: Callable[[Any], Awaitable[Any]],
    engine: Optional[FaultEngine] = None,
):
    """
    Core fault handling middleware.
    
    Wraps request processing with fault engine:
    1. Sets fault context (app, route, request_id)
    2. Catches exceptions and converts to faults
    3. Processes faults through engine
    4. Returns appropriate responses
    
    Args:
        request: Request object
        next_handler: Next handler in chain
        engine: FaultEngine instance (creates default if None)
    
    Returns:
        Response or fault response
    """
    if engine is None:
        from aquilia.faults import get_default_engine
        engine = get_default_engine()
    
    # Set fault context
    FaultEngine.set_context(
        app=getattr(request, "app", None),
        route=getattr(request, "route", None),
        request_id=getattr(request, "id", None),
    )
    
    try:
        # Call next handler
        response = await next_handler(request)
        
        # Check if handler returned a Fault
        if isinstance(response, Fault):
            result = await engine.process(response)
            if isinstance(result, Resolved):
                return result.response
            else:
                # Escalated - convert to generic error
                return {
                    "error": "Internal server error",
                    "trace_id": engine.get_stats().get("last_trace_id"),
                }
        
        return response
    
    except asyncio.CancelledError:
        # Flow cancelled
        fault = FlowCancelledFault(reason="Request cancelled")
        result = await engine.process(fault)
        if isinstance(result, Resolved):
            return result.response
        raise
    
    except Exception as e:
        # Process exception through fault engine
        result = await engine.process(e)
        
        if isinstance(result, Resolved):
            return result.response
        else:
            # Escalated - re-raise
            raise
    
    finally:
        # Clear context
        FaultEngine.clear_context()


async def timeout_middleware(
    request,
    next_handler: Callable[[Any], Awaitable[Any]],
    timeout_seconds: float = 30.0,
):
    """
    Timeout middleware with fault emission.
    
    Args:
        request: Request object
        next_handler: Next handler in chain
        timeout_seconds: Timeout in seconds
    
    Returns:
        Response or timeout fault
    """
    try:
        response = await asyncio.wait_for(
            next_handler(request),
            timeout=timeout_seconds,
        )
        return response
    
    except asyncio.TimeoutError:
        # Emit timeout fault
        handler_name = getattr(request, "handler_name", "unknown")
        raise HandlerTimeoutFault(
            handler_name=handler_name,
            timeout_seconds=timeout_seconds,
        )


# ============================================================================
# Handler Utilities
# ============================================================================

def fault_aware_handler(handler: Callable):
    """
    Decorator to make handler fault-aware.
    
    Allows handler to return Fault objects directly instead of raising.
    
    Usage:
        ```python
        @fault_aware_handler
        async def get_user(request):
            user = await db.get_user(request.params["id"])
            if not user:
                return UserNotFoundFault(user_id=request.params["id"])
            return user
        ```
    
    Args:
        handler: Handler function
    
    Returns:
        Wrapped handler
    """
    if asyncio.iscoroutinefunction(handler):
        async def async_wrapper(*args, **kwargs):
            try:
                result = await handler(*args, **kwargs)
                return result
            except Exception as e:
                # Convert exception to fault
                from aquilia.faults import get_default_engine
                engine = get_default_engine()
                fault_result = await engine.process(e)
                
                if isinstance(fault_result, Resolved):
                    return fault_result.response
                raise
        
        return async_wrapper
    else:
        def sync_wrapper(*args, **kwargs):
            try:
                result = handler(*args, **kwargs)
                return result
            except Exception as e:
                # For sync handlers, let fault middleware handle it
                raise
        
        return sync_wrapper


def create_flow_fault_handler():
    """
    Create fault handler for flow operations.
    
    Returns a handler that processes flow-specific faults.
    """
    from aquilia.faults import FaultHandler, FaultContext, FaultResult, Resolved
    from aquilia.faults.default_handlers import HTTPResponse
    
    class FlowFaultHandler(FaultHandler):
        """Handle flow-specific faults."""
        
        def can_handle(self, ctx: FaultContext) -> bool:
            return ctx.fault.domain == FaultDomain.FLOW
        
        async def handle(self, ctx: FaultContext) -> FaultResult:
            """Map flow fault to HTTP response."""
            fault = ctx.fault
            
            # Determine status code
            status_map = {
                "HANDLER_FAULT": 500,
                "MIDDLEWARE_FAULT": 500,
                "FLOW_CANCELLED": 499,  # Client Closed Request
                "PIPELINE_ABORTED": 500,
                "HANDLER_TIMEOUT": 504,  # Gateway Timeout
                "MIDDLEWARE_CHAIN_FAILED": 500,
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
            
            # Add retry hint for retryable faults
            if fault.retryable:
                body["error"]["retryable"] = True
                body["error"]["retry_after"] = 5  # seconds
            
            response = HTTPResponse(
                status_code=status,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            
            return Resolved(response)
    
    return FlowFaultHandler()


# ============================================================================
# Cancellation Utilities
# ============================================================================

async def with_cancellation_handling(coro: Awaitable[Any]) -> Any:
    """
    Wrap coroutine with cancellation fault handling.
    
    Converts CancelledError to FlowCancelledFault.
    
    Args:
        coro: Coroutine to wrap
    
    Returns:
        Result or raises FlowCancelledFault
    """
    try:
        return await coro
    except asyncio.CancelledError:
        raise FlowCancelledFault(reason="Operation cancelled")


def is_fault_retryable(fault: Fault) -> bool:
    """
    Check if fault is retryable.
    
    Args:
        fault: Fault to check
    
    Returns:
        True if fault can be retried
    """
    return fault.retryable


def should_abort_pipeline(fault: Fault) -> bool:
    """
    Check if fault should abort the pipeline.
    
    Args:
        fault: Fault to check
    
    Returns:
        True if pipeline should abort
    """
    # FATAL and ERROR severity faults abort pipeline
    return fault.severity in (Severity.FATAL, Severity.ERROR)
