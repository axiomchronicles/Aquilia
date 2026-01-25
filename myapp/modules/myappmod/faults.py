"""
Myappmod module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MYAPPMOD = FaultDomain(
    name="MYAPPMOD",
    description="Myappmod module faults",
)


class MyappmodNotFoundFault(Fault):
    """
    Raised when myappmod item is not found.

    Recovery: Return 404 response
    """

    domain = MYAPPMOD
    severity = Severity.INFO
    code = "MYAPPMOD_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Myappmod with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class MyappmodValidationFault(Fault):
    """
    Raised when myappmod data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MYAPPMOD
    severity = Severity.INFO
    code = "MYAPPMOD_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class MyappmodOperationFault(Fault):
    """
    Raised when myappmod operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MYAPPMOD
    severity = Severity.WARN
    code = "MYAPPMOD_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )