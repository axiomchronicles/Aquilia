"""
Admin Module — Fault Definitions
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
    AuthenticationFault,
)


ADMIN_DOMAIN = FaultDomain(
    name="admin",
    description="Admin operations fault domain",
)


class AdminAccessDeniedFault(AuthenticationFault):
    def __init__(self):
        super().__init__(reason="Admin access denied — requires administrator privileges")


class BulkOperationFault(Fault):
    domain = ADMIN_DOMAIN
    severity = Severity.ERROR
    code = "BULK_OPERATION_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Bulk operation failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class SystemHealthFault(Fault):
    domain = ADMIN_DOMAIN
    severity = Severity.FATAL
    code = "SYSTEM_HEALTH_ISSUE"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "System health check detected issues"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class ConfigurationFault(Fault):
    domain = ADMIN_DOMAIN
    severity = Severity.ERROR
    code = "CONFIG_UPDATE_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Configuration update failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)
