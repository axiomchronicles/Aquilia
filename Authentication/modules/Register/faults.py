"""
Register module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
REGISTER = FaultDomain.custom(
    "REGISTER",
    "Register module faults",
)


class RegisterNotFoundFault(Fault):
    """
    Raised when a Register is not found.

    Recovery: Return 404 response
    """

    domain = REGISTER
    severity = Severity.INFO
    code = "REGISTER_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Register with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class RegisterValidationFault(Fault):
    """
    Raised when Register data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = REGISTER
    severity = Severity.INFO
    code = "REGISTER_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class RegisterOperationFault(Fault):
    """
    Raised when a Register operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = REGISTER
    severity = Severity.WARN
    code = "REGISTER_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )