"""
AquilaCache — Fault domain integration.

Defines typed cache faults that integrate with Aquilia's
FaultEngine for structured error handling, recovery strategies,
and observability.
"""

from __future__ import annotations

from typing import Any, Optional

from aquilia.faults.core import Fault, FaultDomain, Severity


# Register cache fault domain
FaultDomain.CACHE = FaultDomain("cache", "Cache subsystem faults")


class CacheFault(Fault):
    """Base class for all cache faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.WARN,
        retryable: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.CACHE,
            severity=severity,
            retryable=retryable,
            public=False,
            metadata=metadata,
        )


class CacheMissFault(CacheFault):
    """Cache key not found (informational, non-error)."""
    
    def __init__(self, key: str, namespace: str = "default", **kwargs):
        super().__init__(
            code="CACHE_MISS",
            message=f"Cache miss for key '{key}' in namespace '{namespace}'",
            severity=Severity.INFO,
            retryable=False,
            metadata={"key": key, "namespace": namespace},
        )


class CacheConnectionFault(CacheFault):
    """Failed to connect to cache backend."""
    
    def __init__(self, backend: str, reason: str, **kwargs):
        super().__init__(
            code="CACHE_CONNECTION_FAILED",
            message=f"Cache backend '{backend}' connection failed: {reason}",
            severity=Severity.ERROR,
            retryable=True,
            metadata={"backend": backend, "reason": reason},
        )


class CacheSerializationFault(CacheFault):
    """Failed to serialize/deserialize cache value."""
    
    def __init__(self, key: str, operation: str, reason: str, **kwargs):
        super().__init__(
            code="CACHE_SERIALIZATION_FAILED",
            message=f"Cache {operation} failed for key '{key}': {reason}",
            severity=Severity.WARN,
            retryable=False,
            metadata={"key": key, "operation": operation, "reason": reason},
        )


class CacheCapacityFault(CacheFault):
    """Cache has reached maximum capacity."""
    
    def __init__(self, current_size: int, max_size: int, **kwargs):
        super().__init__(
            code="CACHE_CAPACITY_EXCEEDED",
            message=f"Cache capacity exceeded: {current_size}/{max_size} entries",
            severity=Severity.WARN,
            retryable=True,
            metadata={"current_size": current_size, "max_size": max_size},
        )


class CacheBackendFault(CacheFault):
    """Generic cache backend error."""
    
    def __init__(self, backend: str, operation: str, reason: str, **kwargs):
        super().__init__(
            code="CACHE_BACKEND_ERROR",
            message=f"Cache backend '{backend}' error during {operation}: {reason}",
            severity=Severity.ERROR,
            retryable=True,
            metadata={"backend": backend, "operation": operation, "reason": reason},
        )


class CacheConfigFault(CacheFault):
    """Cache configuration error."""
    
    def __init__(self, reason: str, **kwargs):
        super().__init__(
            code="CACHE_CONFIG_INVALID",
            message=f"Invalid cache configuration: {reason}",
            severity=Severity.FATAL,
            retryable=False,
            metadata={"reason": reason},
        )


class CacheStampedeFault(CacheFault):
    """Cache stampede detected — multiple concurrent loads for same key."""
    
    def __init__(self, key: str, waiters: int = 0, **kwargs):
        super().__init__(
            code="CACHE_STAMPEDE_DETECTED",
            message=f"Cache stampede for key '{key}' ({waiters} concurrent waiters)",
            severity=Severity.WARN,
            retryable=True,
            metadata={"key": key, "waiters": waiters},
        )


class CacheHealthFault(CacheFault):
    """Cache health check failure."""
    
    def __init__(self, backend: str, reason: str = "Health check failed", **kwargs):
        super().__init__(
            code="CACHE_HEALTH_FAILED",
            message=f"Cache backend '{backend}' health check failed: {reason}",
            severity=Severity.ERROR,
            retryable=True,
            metadata={"backend": backend, "reason": reason},
        )
