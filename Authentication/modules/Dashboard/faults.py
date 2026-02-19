"""
Dashboard module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
DASHBOARD = FaultDomain.custom(
    "DASHBOARD",
    "Dashboard module faults",
)


class DashboardNotFoundFault(Fault):
    """
    Raised when a Dashboard is not found.

    Recovery: Return 404 response
    """

    domain = DASHBOARD
    severity = Severity.INFO
    code = "DASHBOARD_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Dashboard with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class DashboardValidationFault(Fault):
    """
    Raised when Dashboard data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = DASHBOARD
    severity = Severity.INFO
    code = "DASHBOARD_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class DashboardOperationFault(Fault):
    """
    Raised when a Dashboard operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = DASHBOARD
    severity = Severity.WARN
    code = "DASHBOARD_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )