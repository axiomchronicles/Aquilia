"""
Modeboom module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
# Using FLOW domain for application logic
MODEBOOM = FaultDomain.FLOW


class ModeboomNotFoundFault(Fault):
    """
    Raised when modeboom item is not found.

    Recovery: Return 404 response
    """

    domain = FaultDomain.ROUTING
    severity = Severity.WARN
    code = "MODEBOOM_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            message=f"Modeboom with id {item_id} not found",
            domain=self.domain,
            metadata={"item_id": item_id},
        )


class ModeboomValidationFault(Fault):
    """
    Raised when modeboom data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MODEBOOM
    severity = Severity.WARN
    code = "MODEBOOM_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            message="Validation failed",
            domain=self.domain,
            metadata={"errors": errors},
        )


class ModeboomOperationFault(Fault):
    """
    Raised when modeboom operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MODEBOOM
    severity = Severity.ERROR
    code = "MODEBOOM_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            message=f"Operation '{operation}' failed: {reason}",
            domain=self.domain,
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )