"""
Mymod module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity


class MymodNotFoundFault(Fault):
    """
    Raised when mymod item is not found.

    Recovery: Return 404 response
    """

    def __init__(self, item_id: int):
        super().__init__(
            code="MYMOD_NOT_FOUND",
            message=f"Mymod with id {item_id} not found",
            domain=FaultDomain.FLOW,
            severity=Severity.LOW,
            metadata={"item_id": item_id},
        )


class MymodValidationFault(Fault):
    """
    Raised when mymod data validation fails.

    Recovery: Return 400 response with validation errors
    """

    def __init__(self, errors: dict):
        super().__init__(
            code="MYMOD_VALIDATION_ERROR",
            message="Validation failed",
            domain=FaultDomain.FLOW,
            severity=Severity.LOW,
            metadata={"errors": errors},
        )


class MymodOperationFault(Fault):
    """
    Raised when mymod operation fails.

    Recovery: Retry with exponential backoff
    """

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code="MYMOD_OPERATION_FAILED",
            message=f"Operation '{operation}' failed: {reason}",
            domain=FaultDomain.EFFECT,
            severity=Severity.MEDIUM,
            retryable=True,
            metadata={"operation": operation, "reason": reason},
        )