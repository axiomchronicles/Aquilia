"""
Mode module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MODE = FaultDomain(
    name="MODE",
    description="Mode module faults",
)


class ModeNotFoundFault(Fault):
    """
    Raised when mode item is not found.

    Recovery: Return 404 response
    """

    domain = MODE
    severity = Severity.INFO
    code = "MODE_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Mode with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class ModeValidationFault(Fault):
    """
    Raised when mode data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MODE
    severity = Severity.INFO
    code = "MODE_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class ModeOperationFault(Fault):
    """
    Raised when mode operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MODE
    severity = Severity.WARN
    code = "MODE_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )