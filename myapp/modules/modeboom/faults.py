"""
Modeboom module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MODEBOOM = FaultDomain(
    name="MODEBOOM",
    description="Modeboom module faults",
)


class ModeboomNotFoundFault(Fault):
    """
    Raised when modeboom item is not found.

    Recovery: Return 404 response
    """

    domain = MODEBOOM
    severity = Severity.INFO
    code = "MODEBOOM_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Modeboom with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class ModeboomValidationFault(Fault):
    """
    Raised when modeboom data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MODEBOOM
    severity = Severity.INFO
    code = "MODEBOOM_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class ModeboomOperationFault(Fault):
    """
    Raised when modeboom operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MODEBOOM
    severity = Severity.WARN
    code = "MODEBOOM_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )