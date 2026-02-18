"""
CRM Faults — Domain-specific error definitions.
Uses Aquilia fault system with fault domains, severity, and recovery.
"""

from aquilia.faults import Fault, FaultDomain, Severity


# ---- Fault Domains ----
AUTH_DOMAIN = FaultDomain.custom("CRM_AUTH", "CRM authentication faults")
CONTACTS_DOMAIN = FaultDomain.custom("CRM_CONTACTS", "Contact management faults")
COMPANIES_DOMAIN = FaultDomain.custom("CRM_COMPANIES", "Company management faults")
DEALS_DOMAIN = FaultDomain.custom("CRM_DEALS", "Deal/pipeline faults")
TASKS_DOMAIN = FaultDomain.custom("CRM_TASKS", "Task management faults")
MAIL_DOMAIN = FaultDomain.custom("CRM_MAIL", "CRM mail faults")
ANALYTICS_DOMAIN = FaultDomain.custom("CRM_ANALYTICS", "Analytics faults")


# ---- Auth Faults ----
class InvalidCredentialsFault(Fault):
    domain = AUTH_DOMAIN
    severity = Severity.WARN
    code = "INVALID_CREDENTIALS"

    def __init__(self):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Invalid email or password",
            retryable=False,
        )


class UserAlreadyExistsFault(Fault):
    domain = AUTH_DOMAIN
    severity = Severity.INFO
    code = "USER_ALREADY_EXISTS"

    def __init__(self, email: str):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"User with email '{email}' already exists",
            metadata={"email": email},
            retryable=False,
        )


class UnauthorizedFault(Fault):
    domain = AUTH_DOMAIN
    severity = Severity.WARN
    code = "UNAUTHORIZED"

    def __init__(self):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Authentication required",
            retryable=False,
        )


class ForbiddenFault(Fault):
    domain = AUTH_DOMAIN
    severity = Severity.WARN
    code = "FORBIDDEN"

    def __init__(self, reason: str = "Insufficient permissions"):
        super().__init__(
            code=self.code, domain=self.domain,
            message=reason,
            retryable=False,
        )


# ---- Contact Faults ----
class ContactNotFoundFault(Fault):
    domain = CONTACTS_DOMAIN
    severity = Severity.INFO
    code = "CONTACT_NOT_FOUND"

    def __init__(self, contact_id: int):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Contact with id {contact_id} not found",
            metadata={"contact_id": contact_id},
            retryable=False,
        )


class ContactValidationFault(Fault):
    domain = CONTACTS_DOMAIN
    severity = Severity.INFO
    code = "CONTACT_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Contact validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class DuplicateContactFault(Fault):
    domain = CONTACTS_DOMAIN
    severity = Severity.INFO
    code = "DUPLICATE_CONTACT"

    def __init__(self, email: str):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Contact with email '{email}' already exists",
            metadata={"email": email},
            retryable=False,
        )


# ---- Company Faults ----
class CompanyNotFoundFault(Fault):
    domain = COMPANIES_DOMAIN
    severity = Severity.INFO
    code = "COMPANY_NOT_FOUND"

    def __init__(self, company_id: int):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Company with id {company_id} not found",
            metadata={"company_id": company_id},
            retryable=False,
        )


class CompanyValidationFault(Fault):
    domain = COMPANIES_DOMAIN
    severity = Severity.INFO
    code = "COMPANY_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Company validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


# ---- Deal Faults ----
class DealNotFoundFault(Fault):
    domain = DEALS_DOMAIN
    severity = Severity.INFO
    code = "DEAL_NOT_FOUND"

    def __init__(self, deal_id: int):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Deal with id {deal_id} not found",
            metadata={"deal_id": deal_id},
            retryable=False,
        )


class DealValidationFault(Fault):
    domain = DEALS_DOMAIN
    severity = Severity.INFO
    code = "DEAL_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Deal validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


class InvalidStageTransitionFault(Fault):
    domain = DEALS_DOMAIN
    severity = Severity.WARN
    code = "INVALID_STAGE_TRANSITION"

    def __init__(self, from_stage: str, to_stage: str):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Cannot transition deal from '{from_stage}' to '{to_stage}'",
            metadata={"from_stage": from_stage, "to_stage": to_stage},
            retryable=False,
        )


# ---- Task Faults ----
class TaskNotFoundFault(Fault):
    domain = TASKS_DOMAIN
    severity = Severity.INFO
    code = "TASK_NOT_FOUND"

    def __init__(self, task_id: int):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Task with id {task_id} not found",
            metadata={"task_id": task_id},
            retryable=False,
        )


class TaskValidationFault(Fault):
    domain = TASKS_DOMAIN
    severity = Severity.INFO
    code = "TASK_VALIDATION_ERROR"

    def __init__(self, errors: dict):
        super().__init__(
            code=self.code, domain=self.domain,
            message="Task validation failed",
            metadata={"errors": errors},
            retryable=False,
        )


# ---- Mail Faults ----
class MailSendFault(Fault):
    domain = MAIL_DOMAIN
    severity = Severity.ERROR
    code = "MAIL_SEND_FAILED"

    def __init__(self, reason: str):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Failed to send email: {reason}",
            metadata={"reason": reason},
            retryable=True,
        )


class CampaignNotFoundFault(Fault):
    domain = MAIL_DOMAIN
    severity = Severity.INFO
    code = "CAMPAIGN_NOT_FOUND"

    def __init__(self, campaign_id: int):
        super().__init__(
            code=self.code, domain=self.domain,
            message=f"Email campaign with id {campaign_id} not found",
            metadata={"campaign_id": campaign_id},
            retryable=False,
        )
