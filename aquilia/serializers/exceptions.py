"""
Aquilia Serializer Exceptions — Fault-domain integrated error types.

All serializer errors are proper Aquilia Faults with domain, severity,
and structured metadata for programmatic handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..faults.core import Fault, FaultDomain, Severity


# ============================================================================
# Serialization Fault Domain
# ============================================================================

# Register custom domain
SERIALIZATION = FaultDomain.custom("SERIALIZATION")


# ============================================================================
# Fault Classes
# ============================================================================

class SerializationFault(Fault):
    """
    Base fault for all serializer errors.

    Raised when serialization or deserialization fails in a way that
    is NOT a field-level validation error (e.g. structural issues,
    missing serializer configuration, model introspection failures).
    """

    def __init__(
        self,
        code: str = "SERIALIZATION_ERROR",
        message: str = "Serialization failed",
        *,
        severity: Severity = Severity.ERROR,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=SERIALIZATION,
            severity=severity,
            retryable=False,
            public=True,
            metadata=metadata,
        )


class ValidationFault(Fault):
    """
    Raised when serializer-level validation fails.

    Contains structured ``errors`` dict mapping field names (or
    ``"__all__"`` for non-field errors) to lists of error messages.

    Attributes:
        errors: ``{field_name: [messages]}`` or ``{"__all__": [messages]}``
    """

    def __init__(
        self,
        errors: Dict[str, List[str]],
        *,
        message: str = "Validation failed",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.errors = errors
        meta = {"errors": errors}
        if metadata:
            meta.update(metadata)
        super().__init__(
            code="VALIDATION_FAILED",
            message=message,
            domain=SERIALIZATION,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            metadata=meta,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Override to include structured errors in output."""
        base = super().to_dict()
        base["errors"] = self.errors
        return base


class FieldValidationFault(Fault):
    """
    Raised when a single field fails validation.

    Typically collected into a ``ValidationFault`` during full
    serializer validation.
    """

    def __init__(
        self,
        field_name: str,
        messages: List[str],
        *,
        value: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.field_name = field_name
        self.messages = messages
        meta = {"field": field_name, "messages": messages}
        if value is not None:
            meta["value"] = repr(value)
        if metadata:
            meta.update(metadata)
        super().__init__(
            code="FIELD_VALIDATION_FAILED",
            message=f"Field '{field_name}': {'; '.join(messages)}",
            domain=SERIALIZATION,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            metadata=meta,
        )
