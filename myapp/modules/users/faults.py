"""
Users Module — Fault Definitions

Structured fault domains for user-related errors.
Uses Aquilia's Fault engine for standardized error handling.
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
    AuthenticationFault,
)


USERS_DOMAIN = FaultDomain(
    name="users",
    description="User management fault domain",
)


class UserNotFoundFault(Fault):
    domain = USERS_DOMAIN
    severity = Severity.WARN
    code = "USER_NOT_FOUND"

    def __init__(self, identifier: str = ""):
        msg = f"User '{identifier}' does not exist." if identifier else "User not found"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, metadata={"identifier": identifier}, public=True)


class DuplicateEmailFault(Fault):
    domain = USERS_DOMAIN
    severity = Severity.WARN
    code = "DUPLICATE_EMAIL"

    def __init__(self, email: str = ""):
        msg = f"Email '{email}' already registered." if email else "Email already registered"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class DuplicateUsernameFault(Fault):
    domain = USERS_DOMAIN
    severity = Severity.WARN
    code = "DUPLICATE_USERNAME"

    def __init__(self, username: str = ""):
        msg = f"Username '{username}' is taken." if username else "Username taken"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class InvalidCredentialsFault(AuthenticationFault):
    def __init__(self):
        super().__init__(reason="Invalid email or password")


class AccountDeactivatedFault(AuthenticationFault):
    def __init__(self):
        super().__init__(reason="Account has been deactivated")


class AccountNotVerifiedFault(AuthenticationFault):
    def __init__(self):
        super().__init__(reason="Email address has not been verified")


class SessionExpiredFault(AuthenticationFault):
    def __init__(self):
        super().__init__(reason="Session has expired, please log in again")


class InsufficientPermissionsFault(AuthenticationFault):
    def __init__(self, required_role: str = ""):
        reason = f"Requires role: {required_role}" if required_role else "Insufficient permissions"
        super().__init__(reason=reason)


class ProfileUpdateFault(Fault):
    domain = USERS_DOMAIN
    severity = Severity.WARN
    code = "PROFILE_UPDATE_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Failed to update user profile"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)
