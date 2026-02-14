"""
Tasks Module - Faults

Showcases:
- Custom fault domain creation
- Multiple severity levels
- Recovery strategy assignment
- Retryable vs non-retryable faults
- Public vs internal faults
- Fault metadata for debugging
"""

from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy


# Custom fault domain for tasks
TASKS_DOMAIN = FaultDomain.custom("TASKS")


class TaskNotFoundFault(Fault):
    """Raised when a task is not found."""

    def __init__(self, task_id: str):
        super().__init__(
            code="TASK_NOT_FOUND",
            message=f"Task '{task_id}' not found",
            domain=TASKS_DOMAIN,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=404,
            metadata={"task_id": task_id},
        )


class TaskAlreadyCompleteFault(Fault):
    """Raised when trying to modify a completed task."""

    def __init__(self, task_id: str):
        super().__init__(
            code="TASK_ALREADY_COMPLETE",
            message=f"Task '{task_id}' is already completed and cannot be modified",
            domain=TASKS_DOMAIN,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=409,
            metadata={"task_id": task_id},
        )


class TaskAssignmentFault(Fault):
    """Raised when task assignment fails (e.g., user at capacity)."""

    def __init__(self, task_id: str, assignee: str, reason: str):
        super().__init__(
            code="TASK_ASSIGNMENT_FAILED",
            message=f"Cannot assign task '{task_id}' to '{assignee}': {reason}",
            domain=TASKS_DOMAIN,
            severity=Severity.WARN,
            retryable=True,  # Can retry after capacity frees up
            public=True,
            status_code=409,
            metadata={
                "task_id": task_id,
                "assignee": assignee,
                "reason": reason,
            },
        )


class TaskProcessingFault(Fault):
    """
    Raised when task processing encounters a transient failure.

    Uses RETRY recovery strategy for automatic retries.
    """

    def __init__(self, task_id: str, error: str):
        super().__init__(
            code="TASK_PROCESSING_ERROR",
            message=f"Error processing task '{task_id}': {error}",
            domain=TASKS_DOMAIN,
            severity=Severity.ERROR,
            retryable=True,
            public=False,  # Internal error, masked from client
            status_code=500,
            metadata={
                "task_id": task_id,
                "error": error,
                "recovery": RecoveryStrategy.RETRY,
            },
        )


class TaskValidationFault(Fault):
    """Raised when task data fails validation."""

    def __init__(self, errors: list):
        super().__init__(
            code="TASK_VALIDATION_FAILED",
            message=f"Task validation failed with {len(errors)} error(s)",
            domain=TASKS_DOMAIN,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=400,
            metadata={"validation_errors": errors},
        )


class TaskQuotaExceededFault(Fault):
    """
    Raised when user exceeds task quota.

    Uses CIRCUIT_BREAK recovery strategy — stops processing
    until quota resets.
    """

    def __init__(self, user_id: str, current: int, limit: int):
        super().__init__(
            code="TASK_QUOTA_EXCEEDED",
            message=f"Task quota exceeded for user '{user_id}' ({current}/{limit})",
            domain=TASKS_DOMAIN,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=429,
            metadata={
                "user_id": user_id,
                "current": current,
                "limit": limit,
                "recovery": RecoveryStrategy.CIRCUIT_BREAK,
            },
        )
