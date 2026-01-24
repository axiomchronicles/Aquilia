"""
Mymodapp module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MYMODAPP = FaultDomain(
    name="MYMODAPP",
    description="Mymodapp module faults",
)


class MymodappNotFoundFault(Fault):
    """
    Raised when mymodapp item is not found.

    Recovery: Return 404 response
    """

    domain = MYMODAPP
    severity = Severity.LOW
    code = "MYMODAPP_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            message=f"{self.name.capitalize()} with id {item_id} not found",
            context={"item_id": item_id},
            recovery_strategy=RecoveryStrategy.PROPAGATE,
        )


class MymodappValidationFault(Fault):
    """
    Raised when mymodapp data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MYMODAPP
    severity = Severity.LOW
    code = "MYMODAPP_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            message="Validation failed",
            context={"errors": errors},
            recovery_strategy=RecoveryStrategy.PROPAGATE,
        )


class MymodappOperationFault(Fault):
    """
    Raised when mymodapp operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MYMODAPP
    severity = Severity.MEDIUM
    code = "MYMODAPP_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Operation '{operation}' failed: {reason}",
            context={"operation": operation, "reason": reason},
            recovery_strategy=RecoveryStrategy.RETRY,
        )