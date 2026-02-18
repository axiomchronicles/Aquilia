"""
Dummy module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
DUMMY = FaultDomain.custom(
    "DUMMY",
    "Dummy module faults",
)


class DummyNotFoundFault(Fault):
    """
    Raised when a dummy is not found.

    Recovery: Return 404 response
    """

    domain = DUMMY
    severity = Severity.INFO
    code = "DUMMY_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Dummy with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class DummyValidationFault(Fault):
    """
    Raised when dummy data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = DUMMY
    severity = Severity.INFO
    code = "DUMMY_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class DummyOperationFault(Fault):
    """
    Raised when a dummy operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = DUMMY
    severity = Severity.WARN
    code = "DUMMY_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )