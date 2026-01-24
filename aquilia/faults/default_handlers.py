"""
AquilaFaults - Default Handlers.

Pre-built handlers for common fault scenarios:
1. ExceptionAdapter: Convert raw Python exceptions to Faults
2. RetryHandler: Retry transient failures with exponential backoff
3. SecurityFaultHandler: Mask sensitive information in security faults
4. ResponseMapper: Map faults to HTTP/WebSocket/RPC responses
5. FatalHandler: Terminate server on FATAL severity faults

These handlers provide production-ready fault handling out-of-the-box.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Callable
from dataclasses import dataclass

from .core import (
    FaultContext,
    FaultResult,
    Resolved,
    Transformed,
    Escalate,
    Severity,
    FaultDomain,
)
from .handlers import FaultHandler
from .domains import (
    IOFault,
    NetworkFault,
    DatabaseFault,
    SecurityFault,
    AuthenticationFault,
    AuthorizationFault,
    SystemFault,
)


# ============================================================================
# 1. ExceptionAdapter - Convert raw exceptions to Faults
# ============================================================================

@dataclass(frozen=True, slots=True)
class ExceptionMapping:
    """Maps exception type to Fault factory."""
    exception_type: type[Exception]
    fault_factory: Callable[[Exception], Any]  # Returns Fault
    retryable: bool = False


class ExceptionAdapter(FaultHandler):
    """
    Convert raw Python exceptions to structured Faults.
    
    Maps common exception types to appropriate fault domains:
    - ConnectionError → NetworkFault
    - TimeoutError → NetworkFault
    - FileNotFoundError → IOFault
    - PermissionError → SecurityFault
    - asyncio.CancelledError → FlowCancelledFault
    - etc.
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_global(ExceptionAdapter())
        ```
    """
    
    def __init__(self, custom_mappings: Optional[list[ExceptionMapping]] = None):
        """
        Initialize exception adapter.
        
        Args:
            custom_mappings: Additional exception mappings
        """
        self.mappings: list[ExceptionMapping] = [
            # Network errors
            ExceptionMapping(
                ConnectionError,
                lambda e: NetworkFault(
                    operation="connect",
                    reason=str(e),
                ),
                retryable=True,
            ),
            ExceptionMapping(
                TimeoutError,
                lambda e: NetworkFault(
                    operation="request",
                    reason=str(e),
                ),
                retryable=True,
            ),
            
            # I/O errors
            ExceptionMapping(
                FileNotFoundError,
                lambda e: IOFault(
                    code="FILE_NOT_FOUND",
                    message=str(e),
                ),
            ),
            ExceptionMapping(
                PermissionError,
                lambda e: SecurityFault(
                    code="PERMISSION_DENIED",
                    message=str(e),
                    severity=Severity.ERROR,
                ),
            ),
            
            # Type/Value errors
            ExceptionMapping(
                TypeError,
                lambda e: SystemFault(
                    code="TYPE_ERROR",
                    message=str(e),
                ),
            ),
            ExceptionMapping(
                ValueError,
                lambda e: SystemFault(
                    code="VALUE_ERROR",
                    message=str(e),
                ),
            ),
        ]
        
        if custom_mappings:
            self.mappings.extend(custom_mappings)
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Only handle if cause is unmapped exception."""
        return ctx.cause is not None
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Convert exception to appropriate Fault."""
        if ctx.cause is None:
            return Escalate()
        
        # Find matching mapping
        for mapping in self.mappings:
            if isinstance(ctx.cause, mapping.exception_type):
                fault = mapping.fault_factory(ctx.cause)
                return Transformed(fault)
        
        # No mapping found
        return Escalate()


# ============================================================================
# 2. RetryHandler - Retry transient failures
# ============================================================================

class RetryHandler(FaultHandler):
    """
    Retry transient failures with exponential backoff.
    
    Only retries faults marked as retryable.
    Uses exponential backoff: delay = base_delay * (multiplier ** attempt).
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_global(RetryHandler(max_attempts=3))
        ```
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.1,
        multiplier: float = 2.0,
        max_delay: float = 10.0,
    ):
        """
        Initialize retry handler.
        
        Args:
            max_attempts: Maximum retry attempts
            base_delay: Base delay in seconds
            multiplier: Backoff multiplier
            max_delay: Maximum delay in seconds
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.multiplier = multiplier
        self.max_delay = max_delay
        
        # Track retry attempts per fingerprint
        self._attempts: dict[str, int] = {}
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Only handle retryable faults."""
        return ctx.fault.retryable
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Retry fault with exponential backoff."""
        fingerprint = ctx.fingerprint()
        attempt = self._attempts.get(fingerprint, 0)
        
        if attempt >= self.max_attempts:
            # Max attempts reached, escalate
            return Escalate()
        
        # Calculate delay
        delay = min(
            self.base_delay * (self.multiplier ** attempt),
            self.max_delay,
        )
        
        # Wait
        await asyncio.sleep(delay)
        
        # Increment attempt counter
        self._attempts[fingerprint] = attempt + 1
        
        # Return transformed with retry metadata
        return Transformed(
            ctx.fault,
            metadata={
                "retry_attempt": attempt + 1,
                "retry_delay": delay,
            },
        )


# ============================================================================
# 3. SecurityFaultHandler - Mask sensitive information
# ============================================================================

class SecurityFaultHandler(FaultHandler):
    """
    Mask sensitive information in security faults.
    
    Replaces detailed error messages with generic messages for:
    - AuthenticationFault → "Authentication failed"
    - AuthorizationFault → "Access denied"
    
    Prevents leaking information to attackers.
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_app("api", SecurityFaultHandler())
        ```
    """
    
    def __init__(self, mask_metadata: bool = True):
        """
        Initialize security fault handler.
        
        Args:
            mask_metadata: Whether to remove metadata
        """
        self.mask_metadata = mask_metadata
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Only handle security faults."""
        return isinstance(ctx.fault, SecurityFault)
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Mask sensitive information."""
        fault = ctx.fault
        
        # Generic messages
        if isinstance(fault, AuthenticationFault):
            message = "Authentication failed"
        elif isinstance(fault, AuthorizationFault):
            message = "Access denied"
        else:
            message = "Security error"
        
        # Create masked fault
        masked = type(fault)(
            code=fault.code,
            message=message if fault.public else fault.message,
            severity=fault.severity,
            metadata={} if self.mask_metadata else fault.metadata,
        )
        
        return Transformed(masked)


# ============================================================================
# 4. ResponseMapper - Map faults to HTTP responses
# ============================================================================

@dataclass(frozen=True, slots=True)
class HTTPResponse:
    """HTTP response representation."""
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str]


class ResponseMapper(FaultHandler):
    """
    Map faults to HTTP/WebSocket/RPC responses.
    
    Maps fault domains to appropriate status codes:
    - CONFIG → 500 Internal Server Error
    - REGISTRY → 500 Internal Server Error
    - DI → 500 Internal Server Error
    - ROUTING → 404 Not Found
    - FLOW → 500 Internal Server Error
    - EFFECT → 503 Service Unavailable
    - IO → 502 Bad Gateway
    - SECURITY → 401/403
    - SYSTEM → 500 Internal Server Error
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_global(ResponseMapper())
        
        # In handler:
        result = await engine.process(fault)
        if isinstance(result, Resolved):
            return result.response  # HTTPResponse
        ```
    """
    
    def __init__(self):
        """Initialize response mapper."""
        self.status_map = {
            FaultDomain.CONFIG: 500,
            FaultDomain.REGISTRY: 500,
            FaultDomain.DI: 500,
            FaultDomain.ROUTING: 404,
            FaultDomain.FLOW: 500,
            FaultDomain.EFFECT: 503,
            FaultDomain.IO: 502,
            FaultDomain.SECURITY: 401,
            FaultDomain.SYSTEM: 500,
        }
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Handle all faults."""
        return True
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Map fault to HTTP response."""
        fault = ctx.fault
        
        # Determine status code
        status = self.status_map.get(fault.domain, 500)
        
        # For security faults, distinguish auth vs authz
        if fault.domain == FaultDomain.SECURITY:
            if isinstance(fault, AuthorizationFault):
                status = 403
        
        # Build response body
        body = {
            "error": {
                "code": fault.code,
                "message": fault.message if fault.public else "Internal server error",
                "domain": fault.domain.value,
                "severity": fault.severity.value,
            }
        }
        
        # Add trace_id for debugging
        if ctx.trace_id:
            body["error"]["trace_id"] = ctx.trace_id
        
        # Add metadata if fault is public
        if fault.public and fault.metadata:
            body["error"]["metadata"] = fault.metadata
        
        response = HTTPResponse(
            status_code=status,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        
        return Resolved(response)


# ============================================================================
# 5. FatalHandler - Terminate on FATAL faults
# ============================================================================

class FatalHandler(FaultHandler):
    """
    Terminate server on FATAL severity faults.
    
    Used for unrecoverable errors that require server restart:
    - Configuration corruption
    - Critical system resource exhaustion
    - Security compromises
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_global(FatalHandler(callback=lambda: sys.exit(1)))
        ```
    """
    
    def __init__(
        self,
        callback: Optional[Callable[[FaultContext], None]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize fatal handler.
        
        Args:
            callback: Callback to invoke on FATAL fault (e.g., sys.exit)
            logger: Logger for fatal messages
        """
        self.callback = callback
        self.logger = logger or logging.getLogger("aquilia.faults")
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Only handle FATAL severity."""
        return ctx.fault.severity == Severity.FATAL
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Log and invoke callback."""
        self.logger.critical(
            f"FATAL fault detected: {ctx.fault.code} - {ctx.fault.message}",
            extra={"fault_context": ctx.to_dict()},
        )
        
        if self.callback:
            self.callback(ctx)
        
        # Return resolved (server should terminate)
        return Resolved(None)


# ============================================================================
# 6. LoggingHandler - Structured logging
# ============================================================================

class LoggingHandler(FaultHandler):
    """
    Log all faults with structured metadata.
    
    Always escalates (does not resolve faults).
    Used for observability.
    
    Usage:
        ```python
        engine = FaultEngine()
        engine.register_global(LoggingHandler())
        ```
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize logging handler.
        
        Args:
            logger: Logger to use
        """
        self.logger = logger or logging.getLogger("aquilia.faults")
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Handle all faults."""
        return True
    
    async def handle(self, ctx: FaultContext) -> FaultResult:
        """Log fault and escalate."""
        log_level = {
            Severity.INFO: logging.INFO,
            Severity.WARN: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.FATAL: logging.CRITICAL,
        }[ctx.fault.severity]
        
        self.logger.log(
            log_level,
            f"[{ctx.fault.domain.value}] {ctx.fault.code}: {ctx.fault.message}",
            extra={
                "fault": ctx.to_dict(),
                "fingerprint": ctx.fingerprint(),
            },
        )
        
        return Escalate()
