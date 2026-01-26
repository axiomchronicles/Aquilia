"""
AquilaFaults - Core types and fault taxonomy.

Defines:
- Fault base class (structured fault objects)
- FaultContext (runtime context wrapper)
- FaultDomain (explicit fault domains)
- Severity levels
- Fault lifecycle primitives
"""

from __future__ import annotations

import sys
import time
import hashlib
import traceback
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Type
from datetime import datetime


# ============================================================================
# Severity & Domain Enums
# ============================================================================

class Severity(str, Enum):
    """
    Fault severity levels.
    
    Determines logging level, alerting, and recovery strategy.
    """
    INFO = "info"       # Informational, no action needed
    WARN = "warn"       # Warning, should be reviewed
    ERROR = "error"     # Error, immediate attention
    FATAL = "fatal"     # Fatal, unrecoverable, abort
    
    # Aliases
    LOW = INFO
    MEDIUM = WARN
    HIGH = ERROR
    CRITICAL = FATAL


class FaultDomain:
    """
    Fault domains (taxonomy).
    
    Identifies the functional area where a fault occurred.
    Can be one of the standard domains or a custom module-specific domain.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.value = name  # For compatibility with Enum consumers
        self.description = description
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"FaultDomain(name='{self.name}')"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FaultDomain):
            return self.name == other.name
        return str(self) == str(other)
    
    def __hash__(self) -> int:
        return hash(self.name)


# Standard Domains
FaultDomain.CONFIG = FaultDomain("config", "Configuration errors")
FaultDomain.REGISTRY = FaultDomain("registry", "Aquilary registry errors")
FaultDomain.DI = FaultDomain("di", "Dependency injection errors")
FaultDomain.ROUTING = FaultDomain("routing", "Route matching errors")
FaultDomain.FLOW = FaultDomain("flow", "Handler execution errors")
FaultDomain.EFFECT = FaultDomain("effect", "Side effect failures")
FaultDomain.IO = FaultDomain("io", "I/O operations")
FaultDomain.SECURITY = FaultDomain("security", "Security and auth")
FaultDomain.SYSTEM = FaultDomain("system", "System level faults")


class RecoveryStrategy(str, Enum):
    """
    Fault recovery strategies.
    
    Determines how the fault handling system should react effectively.
    """
    PROPAGATE = "propagate"   # Default: Bubble up to next handler
    RETRY = "retry"           # Retry operation (with backoff)
    FALLBACK = "fallback"     # Return fallback value
    MASK = "mask"             # Suppress error (log only)
    CIRCUIT_BREAK = "break"   # Trip circuit breaker



# Domain defaults
DOMAIN_DEFAULTS = {
    FaultDomain.CONFIG: {"severity": Severity.FATAL, "retryable": False},
    FaultDomain.REGISTRY: {"severity": Severity.FATAL, "retryable": False},
    FaultDomain.DI: {"severity": Severity.ERROR, "retryable": False},
    FaultDomain.ROUTING: {"severity": Severity.ERROR, "retryable": False},
    FaultDomain.FLOW: {"severity": Severity.ERROR, "retryable": False},
    FaultDomain.EFFECT: {"severity": Severity.ERROR, "retryable": True},
    FaultDomain.IO: {"severity": Severity.WARN, "retryable": True},
    FaultDomain.SECURITY: {"severity": Severity.ERROR, "retryable": False},
    FaultDomain.SYSTEM: {"severity": Severity.FATAL, "retryable": False},
}


# ============================================================================
# Fault - Base Class
# ============================================================================

class Fault(Exception):
    """
    Base fault class - structured, typed fault object.
    
    A fault is NOT a bare exception. It is a first-class value with:
    - Stable machine-readable code
    - Human-readable message
    - Severity level
    - Domain classification
    - Retry semantics
    - Public exposure control
    
    Faults may be raised OR returned from handlers (Flow Engine supports both).
    
    Attributes:
        code: Stable machine-readable identifier (e.g., "USER_NOT_FOUND")
        message: Human-readable summary
        severity: Fault severity (INFO, WARN, ERROR, FATAL)
        domain: Fault domain (CONFIG, DI, ROUTING, etc.)
        retryable: Whether this fault can be retried
        public: Whether safe to expose to client
        metadata: Additional context data
    
    Example:
        ```python
        raise Fault(
            code="USER_NOT_FOUND",
            message="User with ID 123 not found",
            domain=FaultDomain.FLOW,
            severity=Severity.ERROR,
            public=True,
        )
        ```
    """
    
    def __init__(
        self,
        code: str | None = None,
        message: str | None = None,
        *,
        domain: FaultDomain | None = None,
        severity: Optional[Severity] = None,
        retryable: Optional[bool] = None,
        public: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize fault.
        """
        # Fallback to class attributes if not provided
        self.code = code if code is not None else getattr(self, "code", None)
        self.message = message if message is not None else getattr(self, "message", None)
        self.domain = domain if domain is not None else getattr(self, "domain", None)

        if self.code is None or self.message is None or self.domain is None:
            raise TypeError(f"{self.__class__.__name__} missing required code, message, or domain")

        super().__init__(self.message)
        
        # Immutable core properties are already set
        
        # Apply domain defaults if not specified
        # Default to ERROR/non-retryable for custom domains
        defaults = DOMAIN_DEFAULTS.get(domain, {"severity": Severity.ERROR, "retryable": False})
        self.severity = severity or defaults["severity"]
        self.retryable = retryable if retryable is not None else defaults["retryable"]
        
        # Public exposure
        self.public = public
        
        # Metadata (mutable)
        self.metadata = metadata or {}
    
    def __str__(self) -> str:
        """String representation."""
        return f"[{self.code}] {self.message}"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"Fault(code={self.code!r}, domain={self.domain.value}, "
            f"severity={self.severity.value}, public={self.public})"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize fault to dictionary.
        
        Returns:
            Dictionary representation suitable for logging/serialization
        """
        return {
            "code": self.code,
            "message": self.message,
            "domain": self.domain.value,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "public": self.public,
            "metadata": self.metadata,
        }
    
    def __rshift__(self, other: Type[Fault] | Fault) -> Fault:
        """
        Fault transform chain operator.
        
        Transforms this fault into another while preserving causality.
        
        Usage:
            ```python
            raise DatabaseFault(...) >> ApiFault("USER_FETCH_FAILED")
            ```
        
        Args:
            other: Target fault class or instance
        
        Returns:
            New fault with this fault as cause
        """
        if isinstance(other, type) and issubclass(other, Fault):
            # Class provided - instantiate with this as cause
            new_fault = other(
                code=f"{self.code}_TRANSFORMED",
                message=f"Transformed from {self.code}: {self.message}",
                domain=self.domain,
            )
        elif isinstance(other, Fault):
            # Instance provided - use as-is
            new_fault = other
        else:
            raise TypeError(f"Cannot transform fault to {type(other)}")
        
        # Preserve causality in metadata
        new_fault.metadata["_cause"] = self
        new_fault.metadata["_transform_chain"] = self.metadata.get("_transform_chain", []) + [self.code]
        
        return new_fault


# ============================================================================
# FaultContext - Runtime Context Wrapper
# ============================================================================

@dataclass(slots=True)
class FaultContext:
    """
    Runtime context wrapper for faults.
    
    Every fault is wrapped with runtime context when it propagates through
    the system. Context is appended, never overwritten.
    
    Attributes:
        fault: The underlying fault
        app: App name (if fault occurred in app scope)
        route: Route pattern (if fault occurred during request)
        request_id: Request ID (if fault occurred during request)
        trace_id: Unique trace ID for this fault occurrence
        timestamp: When fault was captured
        cause: Original exception (if fault wraps an exception)
        stack: Stack frames from fault origin
        metadata: Additional runtime metadata
        parent: Parent fault context (for nested faults)
    """
    
    fault: Fault
    trace_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Scope context
    app: Optional[str] = None
    route: Optional[str] = None
    request_id: Optional[str] = None
    
    # Causality
    cause: Optional[Exception] = None
    stack: list[Any] = field(default_factory=list)  # List of traceback frames
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Nesting
    parent: Optional[FaultContext] = None
    
    @classmethod
    def capture(
        cls,
        fault: Fault,
        *,
        app: Optional[str] = None,
        route: Optional[str] = None,
        request_id: Optional[str] = None,
        cause: Optional[Exception] = None,
        parent: Optional[FaultContext] = None,
    ) -> FaultContext:
        """
        Capture fault with runtime context.
        
        Automatically extracts stack trace and generates trace ID.
        
        Args:
            fault: Fault to capture
            app: App name
            route: Route pattern
            request_id: Request ID
            cause: Original exception
            parent: Parent fault context
        
        Returns:
            FaultContext with captured runtime information
        """
        # Generate trace ID
        trace_data = f"{fault.code}:{time.time_ns()}"
        trace_id = hashlib.sha256(trace_data.encode()).hexdigest()[:16]
        
        # Extract stack trace
        stack = []
        if cause and hasattr(cause, "__traceback__"):
            stack = traceback.extract_tb(cause.__traceback__)
        elif sys.exc_info()[2] is not None:
            stack = traceback.extract_tb(sys.exc_info()[2])
        
        # Build context
        ctx = cls(
            fault=fault,
            trace_id=trace_id,
            app=app,
            route=route,
            request_id=request_id,
            cause=cause,
            stack=stack,
            parent=parent,
        )
        
        # Inherit parent context
        if parent:
            ctx.metadata["parent_trace_id"] = parent.trace_id
            ctx.metadata["parent_code"] = parent.fault.code
        
        return ctx
    
    def fingerprint(self) -> str:
        """
        Generate stable fingerprint for this fault occurrence.
        
        Fingerprint = hash(code + domain + app + route)
        
        Used for:
        - Deduplication
        - Grouping similar faults
        - Incident correlation
        
        Returns:
            16-character hex fingerprint
        """
        data = ":".join([
            self.fault.code,
            self.fault.domain.value,
            self.app or "",
            self.route or "",
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize context to dictionary.
        
        Returns:
            Dictionary representation suitable for logging/serialization
        """
        return {
            "fault": self.fault.to_dict(),
            "trace_id": self.trace_id,
            "fingerprint": self.fingerprint(),
            "timestamp": self.timestamp.isoformat(),
            "scope": {
                "app": self.app,
                "route": self.route,
                "request_id": self.request_id,
            },
            "cause": str(self.cause) if self.cause else None,
            "stack_depth": len(self.stack),
            "metadata": self.metadata,
            "parent_trace_id": self.metadata.get("parent_trace_id"),
        }
    
    def __str__(self) -> str:
        """String representation."""
        scope = f"app={self.app}, route={self.route}" if self.app else "global"
        return f"FaultContext[{self.trace_id}]({scope}): {self.fault}"


# ============================================================================
# FaultResult - Handler result types
# ============================================================================

@dataclass(frozen=True)
class Resolved:
    """
    Fault was resolved and should not propagate further.
    
    Contains response to return to caller.
    """
    response: Any


@dataclass(frozen=True)
class Transformed:
    """
    Fault was transformed into another fault.
    
    New fault will continue propagating.
    """
    fault: Fault
    preserve_context: bool = True


@dataclass(frozen=True)
class Escalate:
    """
    Fault should escalate to next handler in chain.
    
    Handler declined to handle this fault.
    """
    pass


# Union type for handler results
FaultResult = Resolved | Transformed | Escalate
