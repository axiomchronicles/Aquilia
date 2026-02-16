"""
AquilaMail Provider Interface — Protocol + result types for mail providers.

All mail delivery backends implement IMailProvider.  The Dispatcher selects
a provider, calls send(envelope), and handles the ProviderResult.

Included backends:
- SMTP (aiosmtplib)          — aquilia.mail.providers.smtp
- AWS SES (aiobotocore)      — aquilia.mail.providers.ses
- SendGrid (httpx)           — aquilia.mail.providers.sendgrid
- Console (dev)              — aquilia.mail.providers.console
- File (dev)                 — aquilia.mail.providers.file
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class ProviderResultStatus(str, Enum):
    """Granular result from a provider send attempt."""

    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"  # retry is appropriate
    PERMANENT_FAILURE = "permanent_failure"  # do not retry
    RATE_LIMITED = "rate_limited"  # retry after backoff


@dataclass
class ProviderResult:
    """Result returned by IMailProvider.send()."""

    status: ProviderResultStatus
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    retry_after: Optional[float] = None  # seconds (for RATE_LIMITED)

    @property
    def is_success(self) -> bool:
        return self.status == ProviderResultStatus.SUCCESS

    @property
    def should_retry(self) -> bool:
        return self.status in (
            ProviderResultStatus.TRANSIENT_FAILURE,
            ProviderResultStatus.RATE_LIMITED,
        )

    def __repr__(self) -> str:
        return (
            f"ProviderResult(status={self.status.value}, "
            f"message_id={self.provider_message_id!r})"
        )


@runtime_checkable
class IMailProvider(Protocol):
    """
    Interface that all mail provider backends must implement.

    Providers are registered in MailConfig.providers and resolved
    by the Dispatcher at send-time.
    """

    name: str
    supports_batching: bool
    max_batch_size: int

    async def send(self, envelope: Any) -> ProviderResult:
        """
        Send a single envelope.

        Args:
            envelope: MailEnvelope to deliver.

        Returns:
            ProviderResult with status and optional message ID.
        """
        ...

    async def send_batch(self, envelopes: List[Any]) -> List[ProviderResult]:
        """
        Send a batch of envelopes (optional; default falls back to sequential).

        Args:
            envelopes: List of MailEnvelope objects.

        Returns:
            List of ProviderResult, one per envelope.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the provider is reachable and healthy.

        Returns:
            True if healthy, False otherwise.
        """
        ...

    async def initialize(self) -> None:
        """Initialize connections / sessions (called at startup)."""
        ...

    async def shutdown(self) -> None:
        """Close connections / sessions (called at shutdown)."""
        ...


# ── Provider implementations ────────────────────────────────────────
from .console import ConsoleProvider
from .file import FileProvider
from .sendgrid import SendGridProvider
from .ses import SESProvider
from .smtp import SMTPProvider

# ── Convenience re-exports ─────────────────────────────────────────

__all__ = [
    "IMailProvider",
    "ProviderResult",
    "ProviderResultStatus",
    "ConsoleProvider",
    "FileProvider",
    "SendGridProvider",
    "SESProvider",
    "SMTPProvider",
]
