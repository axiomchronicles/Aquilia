"""
Mymodule module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MYMODULE = FaultDomain(
    name="MYMODULE",
    description="Mymodule module faults",
)


class MymoduleNotFoundFault(Fault):
    """
    Raised when mymodule item is not found.

    Recovery: Return 404 response
    """

    domain = MYMODULE
    severity = Severity.INFO
    code = "MYMODULE_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Mymodule with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class MymoduleValidationFault(Fault):
    """
    Raised when mymodule data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MYMODULE
    severity = Severity.INFO
    code = "MYMODULE_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class MymoduleOperationFault(Fault):
    """
    Raised when mymodule operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MYMODULE
    severity = Severity.WARN
    code = "MYMODULE_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )