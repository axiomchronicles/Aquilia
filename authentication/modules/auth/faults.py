"""
Auth module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
AUTH = FaultDomain.custom(
    "AUTH",
    "Auth module faults",
)


class AuthNotFoundFault(Fault):
    """
    Raised when a auth is not found.
    """

    domain = AUTH
    severity = Severity.INFO
    code = "AUTH_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Auth with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class AuthValidationFault(Fault):
    """
    Raised when auth data validation fails.
    """

    domain = AUTH
    severity = Severity.INFO
    code = "AUTH_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class AuthOperationFault(Fault):
    """
    Raised when a auth operation fails.
    """

    domain = AUTH
    severity = Severity.WARN
    code = "AUTH_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )


class UserAlreadyExistsFault(Fault):
    """
    Raised when attempting to register a user that already exists.
    """

    domain = AUTH
    severity = Severity.INFO
    code = "USER_ALREADY_EXISTS"

    def __init__(self, email: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"User with email {email} already exists",
            metadata={"email": email},
            retryable=False,
        )


class InvalidCredentialsFault(Fault):
    """
    Raised when login falls due to invalid credentials.
    """

    domain = AUTH
    severity = Severity.INFO
    code = "INVALID_CREDENTIALS"

    def __init__(self):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Invalid email or password",
            retryable=False,
        )