"""
AquilaFaults - Production-grade fault handling system.

Exceptions in Aquilia are NOT just errors — they are **typed fault signals**
that flow through the system with context, lifecycle, and intent.

Philosophy:
- Errors are data, not surprises
- Errors flow through pipelines
- Errors are scoped
- Errors are observable
- Errors are explicit

Core exports:
- Fault: Base fault class
- FaultContext: Runtime context wrapper
- FaultDomain: Domain enumeration
- Severity: Severity levels
- FaultEngine: Runtime fault handler
- FaultHandler: Abstract handler base

Subsystem integrations available in:
- faults.integrations.registry: Registry validation faults
- faults.integrations.di: Dependency injection faults
- faults.integrations.routing: Route matching faults
- faults.integrations.flow: Pipeline and middleware faults
"""

from .core import (
    Fault,
    FaultContext,
    FaultDomain,
    Severity,
    FaultResult,
    Resolved,
    Transformed,
    Escalate,
    RecoveryStrategy,
)

from .engine import (
    FaultEngine,
    get_default_engine,
    process_fault,
)

from .handlers import FaultHandler

from .default_handlers import (
    ExceptionAdapter,
    RetryHandler,
    SecurityFaultHandler,
    ResponseMapper,
    FatalHandler,
    LoggingHandler,
    HTTPResponse,
)

__all__ = [
    # Core types
    "Fault",
    "FaultContext",
    "FaultDomain",
    "Severity",
    "FaultResult",
    "Resolved",
    "Transformed",
    "Escalate",
    "RecoveryStrategy",
    
    # Runtime
    "FaultEngine",
    "FaultHandler",
    "get_default_engine",
    "process_fault",
    
    # Default handlers
    "ExceptionAdapter",
    "RetryHandler",
    "SecurityFaultHandler",
    "ResponseMapper",
    "FatalHandler",
    "LoggingHandler",
    "HTTPResponse",
]
