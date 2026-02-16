"""
SendGrid Provider — Async SendGrid Web API v3 delivery via httpx.

Features:
- Async HTTP via httpx (connection pooling, HTTP/2 support)
- Full Mail Send v3 API integration
- Personalisation, categories, custom args, ASM group
- Attachment support (base64 encoded)
- Click/open tracking toggle
- Template ID support (SendGrid dynamic templates)
- Proper error classification (rate-limit, invalid, auth)
- Health-check via scopes endpoint
- Batch sending via personalizations
- Sandbox mode for testing
- Detailed structured logging

Dependencies:
    pip install httpx   (required)

Usage::

    provider = SendGridProvider(
        name="sendgrid-prod",
        api_key="SG.xxx",
    )
    await provider.initialize()
    result = await provider.send(envelope)
    await provider.shutdown()
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional, Sequence

from ..envelope import MailEnvelope
from ..providers import IMailProvider, ProviderResult, ProviderResultStatus

logger = logging.getLogger("aquilia.mail.providers.sendgrid")

_SENDGRID_API_BASE = "https://api.sendgrid.com"
_SEND_ENDPOINT = "/v3/mail/send"
_SCOPES_ENDPOINT = "/v3/scopes"


class SendGridProvider:
    """
    Async SendGrid mail provider using the v3 Web API.

    Uses httpx for async HTTP with connection pooling.
    """

    name: str
    provider_type: str = "sendgrid"
    supports_batching: bool = True
    max_batch_size: int = 1000  # SendGrid personalizations limit

    def __init__(
        self,
        name: str = "sendgrid",
        api_key: str = "",
        *,
        # Sending options
        sandbox_mode: bool = False,
        click_tracking: bool = True,
        open_tracking: bool = True,
        # Categories & metadata
        categories: Optional[List[str]] = None,
        asm_group_id: Optional[int] = None,
        # IP pool
        ip_pool_name: Optional[str] = None,
        # SendGrid dynamic template
        template_id: Optional[str] = None,
        # Connection
        api_base_url: str = _SENDGRID_API_BASE,
        timeout: float = 30.0,
        priority: int = 10,
    ):
        self.name = name
        self.api_key = api_key
        self.sandbox_mode = sandbox_mode
        self.click_tracking = click_tracking
        self.open_tracking = open_tracking
        self.categories = categories or []
        self.asm_group_id = asm_group_id
        self.ip_pool_name = ip_pool_name
        self.template_id = template_id
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.priority = priority

        # HTTP client
        self._client: Any = None
        self._initialized = False

        # Metrics
        self._total_sent = 0
        self._total_errors = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the httpx async client."""
        if self._initialized:
            return

        logger.info(
            f"SendGrid provider '{self.name}' initializing "
            f"(sandbox={self.sandbox_mode})"
        )

        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for the SendGrid provider. "
                "Install it with: pip install httpx"
            )

        if not self.api_key:
            logger.warning(
                f"SendGrid provider '{self.name}' has no API key configured"
            )

        self._client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "aquilia-mail/1.0",
            },
            timeout=httpx.Timeout(self.timeout),
        )
        self._initialized = True

    async def shutdown(self) -> None:
        """Close the httpx client."""
        logger.info(f"SendGrid provider '{self.name}' shutting down...")
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info(
            f"SendGrid provider '{self.name}' shutdown complete "
            f"(sent={self._total_sent}, errors={self._total_errors})"
        )

    # ── Payload Construction ────────────────────────────────────────

    def _build_payload(self, envelope: MailEnvelope) -> dict:
        """Build SendGrid v3 Mail Send payload from a MailEnvelope."""
        payload: dict[str, Any] = {}

        # Personalizations (one per envelope for single send)
        personalization: dict[str, Any] = {
            "to": [{"email": addr} for addr in envelope.to],
        }
        if envelope.cc:
            personalization["cc"] = [{"email": addr} for addr in envelope.cc]
        if envelope.bcc:
            personalization["bcc"] = [{"email": addr} for addr in envelope.bcc]

        # Custom headers per personalization
        custom_headers = dict(envelope.headers)
        custom_headers["X-Aquilia-Envelope-ID"] = envelope.id
        if envelope.trace_id:
            custom_headers["X-Aquilia-Trace-ID"] = envelope.trace_id
        if envelope.tenant_id:
            custom_headers["X-Aquilia-Tenant-ID"] = envelope.tenant_id
        personalization["headers"] = custom_headers

        # Subject (can be overridden per personalization)
        personalization["subject"] = envelope.subject

        payload["personalizations"] = [personalization]

        # From
        from_parts = self._parse_email(envelope.from_email)
        payload["from"] = from_parts

        # Reply-To
        if envelope.reply_to:
            payload["reply_to"] = self._parse_email(envelope.reply_to)

        # Subject (global)
        payload["subject"] = envelope.subject

        # Content
        content: list[dict[str, str]] = []
        if envelope.body_text:
            content.append({"type": "text/plain", "value": envelope.body_text})
        if envelope.body_html:
            content.append({"type": "text/html", "value": envelope.body_html})
        if not content:
            content.append({"type": "text/plain", "value": ""})
        payload["content"] = content

        # Template ID (SendGrid dynamic templates)
        if self.template_id:
            payload["template_id"] = self.template_id

        # Attachments
        if envelope.attachments:
            attachments: list[dict[str, Any]] = []
            for att in envelope.attachments:
                blob_data = envelope.metadata.get(
                    f"blob:{att.digest}", b""
                )
                att_payload: dict[str, Any] = {
                    "content": base64.b64encode(blob_data).decode("ascii"),
                    "type": att.content_type,
                    "filename": att.filename,
                }
                if att.inline and att.content_id:
                    att_payload["disposition"] = "inline"
                    att_payload["content_id"] = att.content_id
                else:
                    att_payload["disposition"] = "attachment"
                attachments.append(att_payload)
            payload["attachments"] = attachments

        # Categories
        categories = list(self.categories)
        if envelope.tenant_id:
            categories.append(f"tenant:{envelope.tenant_id}")
        if categories:
            payload["categories"] = categories[:10]  # SG max 10

        # Tracking settings
        payload["tracking_settings"] = {
            "click_tracking": {"enable": self.click_tracking},
            "open_tracking": {"enable": self.open_tracking},
        }

        # ASM (unsubscribe group)
        if self.asm_group_id is not None:
            payload["asm"] = {"group_id": self.asm_group_id}

        # IP pool
        if self.ip_pool_name:
            payload["ip_pool_name"] = self.ip_pool_name

        # Sandbox mode
        if self.sandbox_mode:
            payload["mail_settings"] = {
                "sandbox_mode": {"enable": True},
            }

        # Custom args for webhook metadata
        payload["custom_args"] = {
            "aquilia_envelope_id": envelope.id,
        }
        if envelope.tenant_id:
            payload["custom_args"]["aquilia_tenant_id"] = envelope.tenant_id

        return payload

    @staticmethod
    def _parse_email(addr: str) -> dict:
        """Parse 'Display Name <email>' or plain email into SG format."""
        addr = addr.strip()
        if "<" in addr and addr.endswith(">"):
            display = addr.split("<")[0].strip().strip('"')
            email = addr.split("<")[1].rstrip(">").strip()
            result: dict[str, str] = {"email": email}
            if display:
                result["name"] = display
            return result
        return {"email": addr}

    # ── Send ────────────────────────────────────────────────────────

    async def send(self, envelope: MailEnvelope) -> ProviderResult:
        """Send a single envelope via SendGrid v3 API."""
        try:
            payload = self._build_payload(envelope)
            response = await self._client.post(_SEND_ENDPOINT, json=payload)

            # SendGrid returns 202 Accepted on success
            if response.status_code in (200, 201, 202):
                # Message ID is in the X-Message-Id header
                message_id = response.headers.get(
                    "X-Message-Id", f"sg-{envelope.id}"
                )
                self._total_sent += 1
                logger.info(
                    f"SendGrid sent via {self.name}: {envelope.id} "
                    f"(sg_msg_id={message_id})"
                )
                return ProviderResult(
                    status=ProviderResultStatus.SUCCESS,
                    provider_message_id=message_id,
                    raw_response={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    },
                )
            else:
                return self._handle_error_response(response, envelope)

        except Exception as e:
            self._total_errors += 1
            status, retry_after = self._classify_exception(e)
            logger.warning(
                f"SendGrid send error via {self.name}: {e} "
                f"(status={status.value})"
            )
            return ProviderResult(
                status=status,
                error_message=str(e),
                retry_after=retry_after,
            )

    def _handle_error_response(
        self, response: Any, envelope: MailEnvelope,
    ) -> ProviderResult:
        """Handle a non-2xx SendGrid response."""
        self._total_errors += 1
        status_code = response.status_code

        try:
            body = response.json()
        except Exception:
            body = {"errors": [{"message": response.text}]}

        errors = body.get("errors", [])
        error_msg = "; ".join(
            e.get("message", str(e)) for e in errors
        ) if errors else f"HTTP {status_code}"

        logger.warning(
            f"SendGrid error via {self.name}: HTTP {status_code} — {error_msg}"
        )

        # Classify by HTTP status
        if status_code == 429:
            # Rate limited
            retry_after = None
            ra_header = response.headers.get("Retry-After")
            if ra_header:
                try:
                    retry_after = float(ra_header)
                except ValueError:
                    retry_after = 60.0
            return ProviderResult(
                status=ProviderResultStatus.RATE_LIMITED,
                error_message=error_msg,
                retry_after=retry_after or 60.0,
                raw_response=body,
            )
        elif status_code in (401, 403):
            # Auth errors are permanent
            return ProviderResult(
                status=ProviderResultStatus.PERMANENT_FAILURE,
                error_message=f"Authentication error: {error_msg}",
                raw_response=body,
            )
        elif status_code == 400:
            # Bad request — usually permanent (invalid payload)
            return ProviderResult(
                status=ProviderResultStatus.PERMANENT_FAILURE,
                error_message=f"Invalid request: {error_msg}",
                raw_response=body,
            )
        elif status_code >= 500:
            # Server error — transient
            return ProviderResult(
                status=ProviderResultStatus.TRANSIENT_FAILURE,
                error_message=f"SendGrid server error: {error_msg}",
                retry_after=30.0,
                raw_response=body,
            )
        else:
            return ProviderResult(
                status=ProviderResultStatus.TRANSIENT_FAILURE,
                error_message=f"Unexpected HTTP {status_code}: {error_msg}",
                retry_after=30.0,
                raw_response=body,
            )

    async def send_batch(
        self, envelopes: Sequence[MailEnvelope],
    ) -> List[ProviderResult]:
        """
        Send batch of envelopes.

        SendGrid supports multiple personalizations in a single API call,
        but only when the body content is identical. For safety, we send
        each envelope individually.
        """
        results: list[ProviderResult] = []
        for envelope in envelopes:
            result = await self.send(envelope)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        """Check SendGrid API access via scopes endpoint."""
        try:
            response = await self._client.get(_SCOPES_ENDPOINT)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"SendGrid health check failed: {e}")
            return False

    # ── Error Classification ────────────────────────────────────────

    def _classify_exception(self, error: Exception) -> tuple:
        """Classify a Python exception into ProviderResultStatus."""
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return ProviderResultStatus.TRANSIENT_FAILURE, 15.0

        error_str = str(error).lower()
        if "timeout" in error_str:
            return ProviderResultStatus.TRANSIENT_FAILURE, 15.0
        if "rate" in error_str or "throttl" in error_str:
            return ProviderResultStatus.RATE_LIMITED, 60.0

        return ProviderResultStatus.TRANSIENT_FAILURE, 30.0

    def __repr__(self) -> str:
        return (
            f"SendGridProvider(name={self.name!r}, "
            f"sandbox={self.sandbox_mode})"
        )
