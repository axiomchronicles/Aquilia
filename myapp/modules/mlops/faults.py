"""
Mlops module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
MLOPS = FaultDomain.custom(
    "MLOPS",
    "Mlops module faults",
)


class MlopsNotFoundFault(Fault):
    """
    Raised when a mlop is not found.

    Recovery: Return 404 response
    """

    domain = MLOPS
    severity = Severity.INFO
    code = "MLOPS_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Mlop with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class MlopsValidationFault(Fault):
    """
    Raised when mlop data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = MLOPS
    severity = Severity.INFO
    code = "MLOPS_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class MlopsOperationFault(Fault):
    """
    Raised when a mlop operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = MLOPS
    severity = Severity.WARN
    code = "MLOPS_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )