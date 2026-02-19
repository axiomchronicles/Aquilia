"""
Login module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
LOGIN = FaultDomain.custom(
    "LOGIN",
    "Login module faults",
)


class LoginNotFoundFault(Fault):
    """
    Raised when a Login is not found.

    Recovery: Return 404 response
    """

    domain = LOGIN
    severity = Severity.INFO
    code = "LOGIN_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Login with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class LoginValidationFault(Fault):
    """
    Raised when Login data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = LOGIN
    severity = Severity.INFO
    code = "LOGIN_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class LoginOperationFault(Fault):
    """
    Raised when a Login operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = LOGIN
    severity = Severity.WARN
    code = "LOGIN_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )