"""
Testaquilia module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
TESTAQUILIA = FaultDomain.custom(
    "TESTAQUILIA",
    "Testaquilia module faults",
)


class TestaquiliaNotFoundFault(Fault):
    """
    Raised when a testaquilia is not found.

    Recovery: Return 404 response
    """

    domain = TESTAQUILIA
    severity = Severity.INFO
    code = "TESTAQUILIA_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Testaquilia with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class TestaquiliaValidationFault(Fault):
    """
    Raised when testaquilia data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = TESTAQUILIA
    severity = Severity.INFO
    code = "TESTAQUILIA_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class TestaquiliaOperationFault(Fault):
    """
    Raised when a testaquilia operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = TESTAQUILIA
    severity = Severity.WARN
    code = "TESTAQUILIA_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )