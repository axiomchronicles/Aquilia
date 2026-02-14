"""
Users Module - Faults

Showcases:
- Custom fault classes
- FaultDomain assignment
- Severity levels
- Public vs internal faults
- Metadata attachment
"""

from aquilia.faults import Fault, FaultDomain, Severity


class UserNotFoundFault(Fault):
    """Raised when a user is not found by ID or email."""

    def __init__(self, identifier: str):
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"User '{identifier}' not found",
            domain=FaultDomain.IO,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=404,
            metadata={"identifier": identifier},
        )


class DuplicateEmailFault(Fault):
    """Raised when attempting to register with an existing email."""

    def __init__(self, email: str):
        super().__init__(
            code="DUPLICATE_EMAIL",
            message=f"Email '{email}' is already registered",
            domain=FaultDomain.IO,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=409,
            metadata={"email": email},
        )


class InvalidCredentialsFault(Fault):
    """Raised when login credentials are invalid."""

    def __init__(self):
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
            domain=FaultDomain.SECURITY,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=401,
            metadata={},
        )


class UnauthorizedFault(Fault):
    """Raised when accessing a protected resource without authentication."""

    def __init__(self, resource: str = ""):
        super().__init__(
            code="UNAUTHORIZED",
            message=f"Authentication required{' for ' + resource if resource else ''}",
            domain=FaultDomain.SECURITY,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=401,
            metadata={"resource": resource},
        )


class ForbiddenFault(Fault):
    """Raised when user lacks permission for an action."""

    def __init__(self, action: str = "", required_role: str = ""):
        super().__init__(
            code="FORBIDDEN",
            message=f"Insufficient permissions{' for ' + action if action else ''}",
            domain=FaultDomain.SECURITY,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=403,
            metadata={"action": action, "required_role": required_role},
        )
