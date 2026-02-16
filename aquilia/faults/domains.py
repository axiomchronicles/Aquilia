"""
AquilaFaults - Domain-specific fault types.

Provides concrete fault classes for each domain:
- CONFIG faults
- REGISTRY faults  
- DI faults
- ROUTING faults
- FLOW faults
- EFFECT faults
- IO faults
- SECURITY faults
- SYSTEM faults
"""

from typing import Any, Optional
from .core import Fault, FaultDomain, Severity


# ============================================================================
# CONFIG Faults
# ============================================================================

class ConfigFault(Fault):
    """Base class for configuration faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.FATAL,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.CONFIG,
            severity=severity,
            retryable=False,
            public=False,
            metadata=metadata,
        )


class ConfigMissingFault(ConfigFault):
    """Required configuration is missing."""
    
    def __init__(self, key: str, **kwargs):
        super().__init__(
            code="CONFIG_MISSING",
            message=f"Required configuration key '{key}' is missing",
            metadata={"key": key, **kwargs.get("metadata", {})},
        )


class ConfigInvalidFault(ConfigFault):
    """Configuration value is invalid."""
    
    def __init__(self, key: str, reason: str, **kwargs):
        super().__init__(
            code="CONFIG_INVALID",
            message=f"Configuration key '{key}' is invalid: {reason}",
            metadata={"key": key, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# REGISTRY Faults
# ============================================================================

class RegistryFault(Fault):
    """Base class for Aquilary registry faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.FATAL,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.REGISTRY,
            severity=severity,
            retryable=False,
            public=False,
            metadata=metadata,
        )


class DependencyCycleFault(RegistryFault):
    """Circular dependency detected in app graph."""
    
    def __init__(self, cycle: list[str], **kwargs):
        cycle_str = " → ".join(cycle)
        super().__init__(
            code="DEPENDENCY_CYCLE",
            message=f"Circular dependency detected: {cycle_str}",
            metadata={"cycle": cycle, **kwargs.get("metadata", {})},
        )


class ManifestInvalidFault(RegistryFault):
    """Manifest validation failed."""
    
    def __init__(self, manifest_name: str, errors: list[str], **kwargs):
        super().__init__(
            code="MANIFEST_INVALID",
            message=f"Manifest '{manifest_name}' validation failed: {'; '.join(errors)}",
            metadata={"manifest": manifest_name, "errors": errors, **kwargs.get("metadata", {})},
        )


# ============================================================================
# DI Faults
# ============================================================================

class DIFault(Fault):
    """Base class for dependency injection faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.DI,
            severity=severity,
            retryable=False,
            public=False,
            metadata=metadata,
        )


class ProviderNotFoundFault(DIFault):
    """DI provider not found."""
    
    def __init__(self, provider_name: str, app: Optional[str] = None, **kwargs):
        super().__init__(
            code="PROVIDER_NOT_FOUND",
            message=f"DI provider '{provider_name}' not found" + (f" in app '{app}'" if app else ""),
            metadata={"provider": provider_name, "app": app, **kwargs.get("metadata", {})},
        )


class ScopeViolationFault(DIFault):
    """DI scope violation."""
    
    def __init__(self, provider: str, expected_scope: str, actual_scope: str, **kwargs):
        super().__init__(
            code="SCOPE_VIOLATION",
            message=f"Provider '{provider}' scope violation: expected {expected_scope}, got {actual_scope}",
            metadata={
                "provider": provider,
                "expected_scope": expected_scope,
                "actual_scope": actual_scope,
                **kwargs.get("metadata", {}),
            },
        )


class DIResolutionFault(DIFault):
    """DI resolution failed."""
    
    def __init__(self, provider: str, reason: str, **kwargs):
        super().__init__(
            code="DI_RESOLUTION_FAILED",
            message=f"Failed to resolve '{provider}': {reason}",
            metadata={"provider": provider, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# ROUTING Faults
# ============================================================================

class RoutingFault(Fault):
    """Base class for routing faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        public: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.ROUTING,
            severity=severity,
            retryable=False,
            public=public,
            metadata=metadata,
        )


class RouteNotFoundFault(RoutingFault):
    """Route not found."""
    
    def __init__(self, path: str, method: str, **kwargs):
        super().__init__(
            code="ROUTE_NOT_FOUND",
            message=f"Route not found: {method} {path}",
            metadata={"path": path, "method": method, **kwargs.get("metadata", {})},
        )


class RouteAmbiguousFault(RoutingFault):
    """Multiple routes match the pattern."""
    
    def __init__(self, path: str, matches: list[str], **kwargs):
        super().__init__(
            code="ROUTE_AMBIGUOUS",
            message=f"Multiple routes match '{path}': {', '.join(matches)}",
            severity=Severity.WARN,
            public=False,
            metadata={"path": path, "matches": matches, **kwargs.get("metadata", {})},
        )


class PatternInvalidFault(RoutingFault):
    """Route pattern is invalid."""
    
    def __init__(self, pattern: str, reason: str, **kwargs):
        super().__init__(
            code="PATTERN_INVALID",
            message=f"Invalid route pattern '{pattern}': {reason}",
            severity=Severity.FATAL,
            public=False,
            metadata={"pattern": pattern, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# FLOW Faults
# ============================================================================

class FlowFault(Fault):
    """Base class for flow execution faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        retryable: bool = False,
        public: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.FLOW,
            severity=severity,
            retryable=retryable,
            public=public,
            metadata=metadata,
        )


class HandlerFault(FlowFault):
    """Handler execution failed."""
    
    def __init__(self, handler_name: str, reason: str, **kwargs):
        super().__init__(
            code="HANDLER_FAILED",
            message=f"Handler '{handler_name}' failed: {reason}",
            metadata={"handler": handler_name, "reason": reason, **kwargs.get("metadata", {})},
        )


class MiddlewareFault(FlowFault):
    """Middleware execution failed."""
    
    def __init__(self, middleware_name: str, reason: str, **kwargs):
        super().__init__(
            code="MIDDLEWARE_FAILED",
            message=f"Middleware '{middleware_name}' failed: {reason}",
            metadata={"middleware": middleware_name, "reason": reason, **kwargs.get("metadata", {})},
        )


class FlowCancelledFault(FlowFault):
    """Flow was cancelled (timeout or client disconnect)."""
    
    def __init__(self, reason: str = "timeout", **kwargs):
        super().__init__(
            code="FLOW_CANCELLED",
            message=f"Flow cancelled: {reason}",
            severity=Severity.WARN,
            retryable=False,
            public=True,
            metadata={"reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# EFFECT Faults
# ============================================================================

class EffectFault(Fault):
    """Base class for effect (side-effect) faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        retryable: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.EFFECT,
            severity=severity,
            retryable=retryable,
            public=False,
            metadata=metadata,
        )


class DatabaseFault(EffectFault):
    """Database operation failed."""
    
    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            code="DATABASE_FAULT",
            message=f"Database {operation} failed: {reason}",
            metadata={"operation": operation, "reason": reason, **kwargs.get("metadata", {})},
        )


class CacheFault(EffectFault):
    """Cache operation failed."""
    
    def __init__(self, operation: str, key: str, reason: str, **kwargs):
        super().__init__(
            code="CACHE_FAULT",
            message=f"Cache {operation} for key '{key}' failed: {reason}",
            severity=Severity.WARN,
            metadata={"operation": operation, "key": key, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# IO Faults
# ============================================================================

class IOFault(Fault):
    """Base class for I/O faults."""
    
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
            domain=FaultDomain.IO,
            severity=severity,
            retryable=retryable,
            public=False,
            metadata=metadata,
        )


class NetworkFault(IOFault):
    """Network operation failed."""
    
    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            code="NETWORK_FAULT",
            message=f"Network {operation} failed: {reason}",
            metadata={"operation": operation, "reason": reason, **kwargs.get("metadata", {})},
        )


class FilesystemFault(IOFault):
    """Filesystem operation failed."""
    
    def __init__(self, operation: str, path: str, reason: str, **kwargs):
        super().__init__(
            code="FILESYSTEM_FAULT",
            message=f"Filesystem {operation} on '{path}' failed: {reason}",
            metadata={"operation": operation, "path": path, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# SECURITY Faults
# ============================================================================

class SecurityFault(Fault):
    """Base class for security faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        public: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.SECURITY,
            severity=severity,
            retryable=False,
            public=public,
            metadata=metadata,
        )


class AuthenticationFault(SecurityFault):
    """Authentication failed."""
    
    def __init__(self, reason: str = "Invalid credentials", **kwargs):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=reason,
            metadata={"reason": reason, **kwargs.get("metadata", {})},
        )


class AuthorizationFault(SecurityFault):
    """Authorization failed."""
    
    def __init__(self, resource: str, action: str, **kwargs):
        super().__init__(
            code="AUTHORIZATION_FAILED",
            message=f"Not authorized to {action} resource '{resource}'",
            metadata={"resource": resource, "action": action, **kwargs.get("metadata", {})},
        )


class CSRFViolationFault(SecurityFault):
    """CSRF token validation failed."""
    
    def __init__(self, reason: str = "CSRF validation failed", **kwargs):
        self.reason = reason
        super().__init__(
            code="CSRF_VIOLATION",
            message=reason,
            severity=Severity.WARN,
            public=True,
            metadata={"reason": reason, **kwargs.get("metadata", {})},
        )


class CORSViolationFault(SecurityFault):
    """CORS origin not allowed."""
    
    def __init__(self, origin: str, **kwargs):
        super().__init__(
            code="CORS_VIOLATION",
            message=f"Origin '{origin}' is not allowed by CORS policy",
            severity=Severity.WARN,
            public=True,
            metadata={"origin": origin, **kwargs.get("metadata", {})},
        )


class RateLimitExceededFault(SecurityFault):
    """Rate limit exceeded for client."""
    
    def __init__(self, limit: int, window: float, retry_after: float, **kwargs):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded ({limit} requests per {window}s). Retry after {int(retry_after)}s",
            severity=Severity.WARN,
            public=True,
            metadata={
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
                **kwargs.get("metadata", {}),
            },
        )


class CSPViolationFault(SecurityFault):
    """Content Security Policy violation reported."""
    
    def __init__(self, directive: str, blocked_uri: str = "", **kwargs):
        super().__init__(
            code="CSP_VIOLATION",
            message=f"CSP violation: directive '{directive}' blocked '{blocked_uri}'",
            severity=Severity.WARN,
            public=False,
            metadata={
                "directive": directive,
                "blocked_uri": blocked_uri,
                **kwargs.get("metadata", {}),
            },
        )


# ============================================================================
# SYSTEM Faults
# ============================================================================

class SystemFault(Fault):
    """Base class for fatal system faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.FATAL,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.SYSTEM,
            severity=severity,
            retryable=False,
            public=False,
            metadata=metadata,
        )


class UnrecoverableFault(SystemFault):
    """Unrecoverable system fault."""
    
    def __init__(self, reason: str, **kwargs):
        super().__init__(
            code="UNRECOVERABLE",
            message=f"Unrecoverable system fault: {reason}",
            metadata={"reason": reason, **kwargs.get("metadata", {})},
        )


class ResourceExhaustedFault(SystemFault):
    """System resources exhausted."""
    
    def __init__(self, resource: str, **kwargs):
        super().__init__(
            code="RESOURCE_EXHAUSTED",
            message=f"System resource exhausted: {resource}",
            severity=Severity.FATAL,
            metadata={"resource": resource, **kwargs.get("metadata", {})},
        )


# ============================================================================
# MODEL Faults (ORM / Database)
# ============================================================================

class ModelFault(Fault):
    """Base class for model and database faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        retryable: bool = False,
        public: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.MODEL,
            severity=severity,
            retryable=retryable,
            public=public,
            metadata=metadata,
        )


class AMDLParseFault(ModelFault):
    """AMDL file parsing failed."""
    
    def __init__(self, file: str, line: int, reason: str, **kwargs):
        super().__init__(
            code="AMDL_PARSE_ERROR",
            message=f"AMDL parse error in '{file}' at line {line}: {reason}",
            severity=Severity.FATAL,
            metadata={"file": file, "line": line, "reason": reason, **kwargs.get("metadata", {})},
        )


class ModelNotFoundFault(ModelFault):
    """Model not found in registry."""
    
    def __init__(self, model_name: str, **kwargs):
        super().__init__(
            code="MODEL_NOT_FOUND",
            message=f"Model '{model_name}' not found in ModelRegistry",
            metadata={"model": model_name, **kwargs.get("metadata", {})},
        )


class ModelRegistrationFault(ModelFault):
    """Model registration failed."""
    
    def __init__(self, model_name: str, reason: str, **kwargs):
        super().__init__(
            code="MODEL_REGISTRATION_FAILED",
            message=f"Failed to register model '{model_name}': {reason}",
            metadata={"model": model_name, "reason": reason, **kwargs.get("metadata", {})},
        )


class MigrationFault(ModelFault):
    """Database migration failed."""
    
    def __init__(self, migration: str, reason: str, **kwargs):
        super().__init__(
            code="MIGRATION_FAILED",
            message=f"Migration '{migration}' failed: {reason}",
            metadata={"migration": migration, "reason": reason, **kwargs.get("metadata", {})},
        )


class MigrationConflictFault(ModelFault):
    """Migration conflict detected (e.g. divergent migration branches)."""
    
    def __init__(self, conflicting: list[str], **kwargs):
        super().__init__(
            code="MIGRATION_CONFLICT",
            message=f"Migration conflict: {', '.join(conflicting)}",
            severity=Severity.FATAL,
            metadata={"conflicting": conflicting, **kwargs.get("metadata", {})},
        )


class QueryFault(ModelFault):
    """Query execution failed."""
    
    def __init__(self, model: str, operation: str, reason: str, **kwargs):
        super().__init__(
            code="QUERY_FAILED",
            message=f"Query on '{model}' ({operation}) failed: {reason}",
            retryable=True,
            metadata={"model": model, "operation": operation, "reason": reason, **kwargs.get("metadata", {})},
        )


class DatabaseConnectionFault(ModelFault):
    """Database connection failed."""
    
    def __init__(self, url: str, reason: str, **kwargs):
        super().__init__(
            code="DB_CONNECTION_FAILED",
            message=f"Database connection failed ({url}): {reason}",
            severity=Severity.FATAL,
            retryable=True,
            metadata={"url": url, "reason": reason, **kwargs.get("metadata", {})},
        )


class SchemaFault(ModelFault):
    """Schema creation or validation failed."""
    
    def __init__(self, table: str, reason: str, **kwargs):
        super().__init__(
            code="SCHEMA_FAULT",
            message=f"Schema error for table '{table}': {reason}",
            severity=Severity.FATAL,
            metadata={"table": table, "reason": reason, **kwargs.get("metadata", {})},
        )


# ============================================================================
# SERIALIZATION Faults
# ============================================================================

class SerializerFault(Fault):
    """Base class for serializer faults."""
    
    def __init__(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = Severity.WARN,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=FaultDomain.SERIALIZATION,
            severity=severity,
            retryable=False,
            public=True,
            metadata=metadata,
        )


class SerializerValidationFault(SerializerFault):
    """Serializer validation failed with structured field errors."""
    
    def __init__(self, errors: dict[str, list[str]], **kwargs):
        self.errors = errors
        error_summary = "; ".join(
            f"{k}: {', '.join(v)}" for k, v in errors.items()
        )
        super().__init__(
            code="SERIALIZER_VALIDATION_FAILED",
            message=f"Validation failed: {error_summary}",
            metadata={"errors": errors, **kwargs.get("metadata", {})},
        )
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["errors"] = self.errors
        return base


class SerializerFieldFault(SerializerFault):
    """A specific serializer field failed validation or coercion."""
    
    def __init__(self, field_name: str, messages: list[str], **kwargs):
        super().__init__(
            code="SERIALIZER_FIELD_FAULT",
            message=f"Field '{field_name}': {'; '.join(messages)}",
            metadata={"field": field_name, "messages": messages, **kwargs.get("metadata", {})},
        )


class SerializerConfigFault(SerializerFault):
    """Serializer is misconfigured (e.g. missing Meta.model)."""
    
    def __init__(self, serializer_name: str, reason: str, **kwargs):
        super().__init__(
            code="SERIALIZER_CONFIG_ERROR",
            message=f"Serializer '{serializer_name}' misconfigured: {reason}",
            severity=Severity.ERROR,
            metadata={"serializer": serializer_name, "reason": reason, **kwargs.get("metadata", {})},
        )
