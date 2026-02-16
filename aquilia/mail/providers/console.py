"""
Console Provider — prints emails to stdout/logger (development).

Useful for local development and testing.  Does not actually send emails.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from ..envelope import MailEnvelope
from ..providers import IMailProvider, ProviderResult, ProviderResultStatus

logger = logging.getLogger("aquilia.mail.providers.console")


class ConsoleProvider:
    """
    Provider that logs emails to the console instead of sending them.

    This is the default provider in development mode.
    """

    name: str = "console"
    priority: int = 100  # low priority — fallback only
    supports_batching: bool = True
    max_batch_size: int = 100

    def __init__(self, name: str = "console"):
        self.name = name

    async def initialize(self) -> None:
        logger.debug("ConsoleProvider initialized")

    async def shutdown(self) -> None:
        logger.debug("ConsoleProvider shutdown")

    async def send(self, envelope: MailEnvelope) -> ProviderResult:
        """Print the envelope to the console."""
        separator = "=" * 72
        output = (
            f"\n{separator}\n"
            f"  📧 CONSOLE MAIL (not actually sent)\n"
            f"{separator}\n"
            f"  ID:      {envelope.id}\n"
            f"  From:    {envelope.from_email}\n"
            f"  To:      {', '.join(envelope.to)}\n"
        )
        if envelope.cc:
            output += f"  CC:      {', '.join(envelope.cc)}\n"
        if envelope.bcc:
            output += f"  BCC:     {', '.join(envelope.bcc)}\n"
        if envelope.reply_to:
            output += f"  Reply:   {envelope.reply_to}\n"
        output += (
            f"  Subject: {envelope.subject}\n"
            f"  Priority: {envelope.priority}\n"
            f"  Date:    {envelope.created_at}\n"
        )
        if envelope.headers:
            output += f"  Headers: {envelope.headers}\n"
        if envelope.attachments:
            att_names = [a.filename for a in envelope.attachments]
            output += f"  Attachments: {att_names}\n"
        output += f"{'-' * 72}\n"
        if envelope.body_text:
            output += f"{envelope.body_text}\n"
        if envelope.body_html:
            output += f"{'-' * 72}\n"
            output += f"[HTML]\n{envelope.body_html}\n"
        output += f"{separator}\n"

        print(output)
        logger.info(
            "Console mail sent",
            extra={
                "envelope_id": envelope.id,
                "to": envelope.to,
                "subject": envelope.subject,
            },
        )

        return ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_message_id=f"console-{envelope.id}",
        )

    async def send_batch(
        self, envelopes: Sequence[MailEnvelope]
    ) -> List[ProviderResult]:
        """Send a batch of envelopes (sequentially via console)."""
        results = []
        for env in envelopes:
            results.append(await self.send(env))
        return results

    async def health_check(self) -> bool:
        """Console provider is always healthy."""
        return True
