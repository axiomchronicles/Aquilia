"""
AquilaMail — Production-ready async mail subsystem for Aquilia.

Django-like ergonomics with Aquilia-native features:
- Unique Aquilia Template Syntax (ATS) for mail templates
- Provider-agnostic sending (SMTP, SES, SendGrid, custom)
- Reliable delivery: retries, backoff, idempotency, rate-limiting
- Bounce & complaint handling, suppression lists
- Observability: metrics, tracing, structured logs
- Security: DKIM signing, TLS, PII redaction
- DI-scoped, manifest-wired, lifecycle-aware

Quick Start:
    from aquilia.mail import send_mail, asend_mail

    # Synchronous
    send_mail(
        subject="Hello",
        body="Welcome!",
        from_email="noreply@myapp.com",
        to=["user@example.com"],
    )

    # Async
    await asend_mail(
        subject="Hello",
        body="Welcome!",
        to=["user@example.com"],
    )

    # Template-based
    from aquilia.mail import TemplateMessage
    msg = TemplateMessage(
        template="welcome.aqt",
        context={"user": {"name": "Asha"}},
        to=["asha@example.com"],
    )
    await msg.asend()
"""

__version__ = "1.0.0"

# ── Core message types ──────────────────────────────────────────────
from .message import (
    EmailMessage,
    EmailMultiAlternatives,
    TemplateMessage,
)

# ── Convenience API ─────────────────────────────────────────────────
from .service import send_mail, asend_mail

# ── Envelope & config ──────────────────────────────────────────────
from .envelope import MailEnvelope, EnvelopeStatus, Priority
from .config import (
    MailConfig,
    # Config serializers (Aquilia Serializer-based validation)
    ProviderConfigSerializer,
    RetryConfigSerializer,
    RateLimitConfigSerializer,
    SecurityConfigSerializer,
    TemplateConfigSerializer,
    QueueConfigSerializer,
    # Config wrapper objects (backward-compatible attribute access)
    ProviderConfig,
    RetryConfig,
    RateLimitConfig,
    SecurityConfig,
    TemplateConfig,
    QueueConfig,
)

# ── Provider interface & implementations ─────────────────────────────
from .providers import (
    IMailProvider,
    ProviderResult,
    ProviderResultStatus,
    ConsoleProvider,
    FileProvider,
    SendGridProvider,
    SESProvider,
    SMTPProvider,
)

# ── DI providers ───────────────────────────────────────────────────
from .di_providers import (
    MailConfigProvider,
    MailServiceProvider,
    MailProviderRegistry,
    register_mail_providers,
)

# ── Faults ──────────────────────────────────────────────────────────
from .faults import (
    MailFault,
    MailSendFault,
    MailTemplateFault,
    MailConfigFault,
    MailSuppressedFault,
    MailRateLimitFault,
    MailValidationFault,
)

__all__ = [
    # Message types
    "EmailMessage",
    "EmailMultiAlternatives",
    "TemplateMessage",
    # Convenience
    "send_mail",
    "asend_mail",
    # Envelope
    "MailEnvelope",
    "EnvelopeStatus",
    "Priority",
    # Config
    "MailConfig",
    # Config serializers
    "ProviderConfigSerializer",
    "RetryConfigSerializer",
    "RateLimitConfigSerializer",
    "SecurityConfigSerializer",
    "TemplateConfigSerializer",
    "QueueConfigSerializer",
    # Config wrappers
    "ProviderConfig",
    "RetryConfig",
    "RateLimitConfig",
    "SecurityConfig",
    "TemplateConfig",
    "QueueConfig",
    # Provider interface
    "IMailProvider",
    "ProviderResult",
    "ProviderResultStatus",
    # Provider implementations
    "ConsoleProvider",
    "FileProvider",
    "SendGridProvider",
    "SESProvider",
    "SMTPProvider",
    # DI
    "MailConfigProvider",
    "MailServiceProvider",
    "MailProviderRegistry",
    "register_mail_providers",
    # Faults
    "MailFault",
    "MailSendFault",
    "MailTemplateFault",
    "MailConfigFault",
    "MailSuppressedFault",
    "MailRateLimitFault",
    "MailValidationFault",
]
