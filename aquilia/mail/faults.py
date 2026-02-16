"""
AquilaMail Faults — Structured, typed fault definitions for the mail subsystem.

Integrates with Aquilia's FaultDomain system so all mail errors are inspectable,
recoverable, and observable through the standard fault pipeline.
"""

from __future__ import annotations

from typing import Any, Optional

from ..faults.core import Fault, FaultDomain, Severity


# ── Mail Fault Domain ───────────────────────────────────────────────
FaultDomain.MAIL = FaultDomain("mail", "Email sending, templating, and delivery faults")


# ── Base ────────────────────────────────────────────────────────────

class MailFault(Fault):
    """Base class for all mail-subsystem faults."""

    domain = FaultDomain.MAIL
    severity = Severity.ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str = "MAIL_ERROR",
        severity: Severity = Severity.ERROR,
        details: Optional[dict[str, Any]] = None,
        recoverable: bool = False,
        envelope_id: Optional[str] = None,
    ):
        self.envelope_id = envelope_id
        self.recoverable = recoverable
        metadata = {**(details or {}), "envelope_id": envelope_id} if envelope_id else (details or {})
        super().__init__(
            message=message,
            code=code,
            domain=FaultDomain.MAIL,
            severity=severity,
            retryable=recoverable,
            metadata=metadata,
        )


# ── Specific fault types ───────────────────────────────────────────

class MailSendFault(MailFault):
    """Provider-level send failure (transient or permanent)."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        transient: bool = True,
        envelope_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.provider = provider
        self.transient = transient
        super().__init__(
            message=message,
            code="MAIL_SEND_TRANSIENT" if transient else "MAIL_SEND_PERMANENT",
            severity=Severity.WARN if transient else Severity.ERROR,
            details={**(details or {}), "provider": provider, "transient": transient},
            recoverable=transient,
            envelope_id=envelope_id,
        )


class MailTemplateFault(MailFault):
    """Template parse, compile, or render error."""

    def __init__(
        self,
        message: str,
        *,
        template_name: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.template_name = template_name
        super().__init__(
            message=message,
            code="MAIL_TEMPLATE_ERROR",
            severity=Severity.ERROR,
            details={
                **(details or {}),
                "template_name": template_name,
                "line": line,
                "column": column,
            },
            recoverable=False,
        )


class MailConfigFault(MailFault):
    """Mail configuration error (missing provider, bad credentials, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="MAIL_CONFIG_ERROR",
            severity=Severity.FATAL,
            details={**(details or {}), "config_key": config_key},
            recoverable=False,
        )


class MailSuppressedFault(MailFault):
    """Recipient is on the suppression list."""

    def __init__(
        self,
        email: str,
        *,
        reason: str = "suppressed",
        details: Optional[dict[str, Any]] = None,
    ):
        self.email = email
        super().__init__(
            message=f"Recipient {email} is suppressed: {reason}",
            code="MAIL_SUPPRESSED",
            severity=Severity.WARN,
            details={**(details or {}), "email": email, "suppression_reason": reason},
            recoverable=False,
        )


class MailRateLimitFault(MailFault):
    """Rate limit exceeded for provider or domain."""

    def __init__(
        self,
        message: str,
        *,
        scope: str = "global",
        retry_after: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="MAIL_RATE_LIMITED",
            severity=Severity.WARN,
            details={**(details or {}), "scope": scope, "retry_after": retry_after},
            recoverable=True,
        )


class MailValidationFault(MailFault):
    """Invalid email address, missing fields, or envelope validation error."""

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="MAIL_VALIDATION_ERROR",
            severity=Severity.ERROR,
            details={**(details or {}), "field": field},
            recoverable=False,
        )
