"""
Blogs module faults (error handling).

Faults define domain-specific errors and their recovery strategies.
They are automatically registered with the fault handling system.
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Define fault domain for this module
BLOGS = FaultDomain(
    name="BLOGS",
    description="Blogs module faults",
)


class BlogsNotFoundFault(Fault):
    """
    Raised when a blog is not found.

    Recovery: Return 404 response
    """

    domain = BLOGS
    severity = Severity.INFO
    code = "BLOGS_NOT_FOUND"

    def __init__(self, item_id: int):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Blog with id {item_id} not found",
            metadata={"item_id": item_id},
            retryable=False,
        )


class BlogsValidationFault(Fault):
    """
    Raised when blog data validation fails.

    Recovery: Return 400 response with validation errors
    """

    domain = BLOGS
    severity = Severity.INFO
    code = "BLOGS_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message="Validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class BlogsOperationFault(Fault):
    """
    Raised when a blog operation fails.

    Recovery: Retry with exponential backoff
    """

    domain = BLOGS
    severity = Severity.WARN
    code = "BLOGS_OPERATION_FAILED"

    def __init__(self, operation: str, reason: str):
        super().__init__(
            code=self.code,
            domain=self.domain,
            message=f"Operation '{operation}' failed: {reason}",
            metadata={"operation": operation, "reason": reason},
            retryable=True,
        )