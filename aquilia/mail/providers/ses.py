"""
AWS SES Provider — Async Amazon Simple Email Service delivery.

Features:
- Async AWS SES v2 via aiobotocore (or boto3 sync fallback)
- Raw email sending (full MIME control) and structured API
- IAM / environment credential auto-discovery
- Configurable region, configuration-set, source-ARN
- Proper error classification (throttle, bounce, permanent)
- Health-check via SES GetAccount
- Batch send with SES SendBulkEmail
- Detailed structured logging
- Automatic MIME construction from MailEnvelope
- Support for SES tags, configuration sets, feedback headers

Dependencies:
    pip install aiobotocore   (recommended for async)
    pip install boto3         (sync fallback)

Usage::

    provider = SESProvider(
        name="aws-ses",
        region="us-east-1",
        configuration_set="my-config-set",
    )
    await provider.initialize()
    result = await provider.send(envelope)
    await provider.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Any, Dict, List, Optional, Sequence

from ..envelope import MailEnvelope
from ..providers import IMailProvider, ProviderResult, ProviderResultStatus

logger = logging.getLogger("aquilia.mail.providers.ses")

# ── SES Error classification ───────────────────────────────────────
_THROTTLE_CODES = frozenset({
    "Throttling",
    "ThrottlingException",
    "TooManyRequestsException",
    "LimitExceededException",
    "MaxSendingRateExceeded",
})

_PERMANENT_CODES = frozenset({
    "MessageRejected",
    "MailFromDomainNotVerifiedException",
    "AccountSendingPausedException",
    "ConfigurationSetDoesNotExistException",
    "InvalidParameterValue",
})


class SESProvider:
    """
    Async AWS SES mail provider.

    Uses aiobotocore for true async I/O. Falls back to boto3 in a
    thread pool if aiobotocore is not installed.
    """

    name: str
    provider_type: str = "ses"
    supports_batching: bool = True
    max_batch_size: int = 50  # SES SendBulkEmail limit

    def __init__(
        self,
        name: str = "ses",
        region: str = "us-east-1",
        *,
        # AWS credentials (None = use environment / IAM role)
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        # SES options
        configuration_set: Optional[str] = None,
        source_arn: Optional[str] = None,
        return_path: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        # Sending mode
        use_raw: bool = True,
        # Connection
        endpoint_url: Optional[str] = None,
        priority: int = 10,
    ):
        self.name = name
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.configuration_set = configuration_set
        self.source_arn = source_arn
        self.return_path = return_path
        self.tags = tags or {}
        self.use_raw = use_raw
        self.endpoint_url = endpoint_url
        self.priority = priority

        # Client state
        self._session: Any = None
        self._client: Any = None
        self._client_ctx: Any = None
        self._use_aiobotocore = False
        self._initialized = False

        # Metrics
        self._total_sent = 0
        self._total_errors = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the SES client (aiobotocore or boto3 fallback)."""
        if self._initialized:
            return

        logger.info(
            f"SES provider '{self.name}' initializing (region={self.region})"
        )

        # Try aiobotocore first (fully async)
        try:
            import aiobotocore.session

            session = aiobotocore.session.get_session()
            kwargs: dict[str, Any] = {
                "service_name": "sesv2",
                "region_name": self.region,
            }
            if self.aws_access_key_id:
                kwargs["aws_access_key_id"] = self.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_session_token:
                kwargs["aws_session_token"] = self.aws_session_token
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url

            self._client_ctx = session.create_client(**kwargs)
            self._client = await self._client_ctx.__aenter__()
            self._use_aiobotocore = True
            logger.debug("SES using aiobotocore (async)")

        except ImportError:
            # Fallback to boto3 (sync, run in thread pool)
            try:
                import boto3

                kwargs = {
                    "service_name": "sesv2",
                    "region_name": self.region,
                }
                if self.aws_access_key_id:
                    kwargs["aws_access_key_id"] = self.aws_access_key_id
                    kwargs["aws_secret_access_key"] = self.aws_secret_access_key
                if self.aws_session_token:
                    kwargs["aws_session_token"] = self.aws_session_token
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url

                self._client = boto3.client(**kwargs)
                self._use_aiobotocore = False
                logger.debug("SES using boto3 (sync fallback)")

            except ImportError:
                raise ImportError(
                    "Either aiobotocore or boto3 is required for the SES provider. "
                    "Install with: pip install aiobotocore  OR  pip install boto3"
                )

        self._initialized = True

    async def shutdown(self) -> None:
        """Close the SES client."""
        logger.info(f"SES provider '{self.name}' shutting down...")
        if self._use_aiobotocore and self._client_ctx is not None:
            try:
                await self._client_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"SES client close error: {e}")
        self._client = None
        self._client_ctx = None
        self._initialized = False
        logger.info(
            f"SES provider '{self.name}' shutdown complete "
            f"(sent={self._total_sent}, errors={self._total_errors})"
        )

    # ── MIME Construction ───────────────────────────────────────────

    def _build_raw_message(self, envelope: MailEnvelope) -> bytes:
        """Build a raw MIME message (bytes) for SES SendRawEmail."""
        msg = MIMEMultipart("mixed")

        msg["From"] = envelope.from_email
        msg["To"] = ", ".join(envelope.to)
        if envelope.cc:
            msg["Cc"] = ", ".join(envelope.cc)
        msg["Subject"] = envelope.subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(
            domain=self._extract_domain(envelope.from_email)
        )
        if envelope.reply_to:
            msg["Reply-To"] = envelope.reply_to

        # Custom headers
        for key, value in envelope.headers.items():
            msg[key] = value

        # Aquilia tracking headers
        msg["X-Aquilia-Envelope-ID"] = envelope.id
        if envelope.trace_id:
            msg["X-Aquilia-Trace-ID"] = envelope.trace_id

        # Body
        if envelope.body_html:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(envelope.body_text, "plain", "utf-8"))
            alt.attach(MIMEText(envelope.body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(envelope.body_text, "plain", "utf-8"))

        # Attachments
        for attachment in envelope.attachments:
            maintype, subtype = attachment.content_type.split("/", 1)
            part = MIMEBase(maintype, subtype)
            blob_data = envelope.metadata.get(
                f"blob:{attachment.digest}", b""
            )
            part.set_payload(blob_data)
            encoders.encode_base64(part)
            if attachment.inline and attachment.content_id:
                part.add_header(
                    "Content-Disposition", "inline",
                    filename=attachment.filename,
                )
                part.add_header("Content-ID", f"<{attachment.content_id}>")
            else:
                part.add_header(
                    "Content-Disposition", "attachment",
                    filename=attachment.filename,
                )
            msg.attach(part)

        return msg.as_bytes()

    @staticmethod
    def _extract_domain(email: str) -> str:
        if "<" in email:
            email = email.split("<")[1].rstrip(">")
        return email.rsplit("@", 1)[-1] if "@" in email else "localhost"

    # ── SES API Helpers ─────────────────────────────────────────────

    def _build_ses_tags(self, envelope: MailEnvelope) -> list:
        """Build SES message tags."""
        tags = [{"Name": k, "Value": v} for k, v in self.tags.items()]
        tags.append({"Name": "aquilia_envelope_id", "Value": envelope.id})
        if envelope.tenant_id:
            tags.append({"Name": "aquilia_tenant_id", "Value": envelope.tenant_id})
        return tags

    async def _call_ses(self, method: str, **kwargs: Any) -> dict:
        """Call an SES API method (async or sync fallback)."""
        if self._use_aiobotocore:
            func = getattr(self._client, method)
            return await func(**kwargs)
        else:
            func = getattr(self._client, method)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: func(**kwargs))

    # ── Send ────────────────────────────────────────────────────────

    async def send(self, envelope: MailEnvelope) -> ProviderResult:
        """Send a single envelope via SES."""
        try:
            if self.use_raw:
                return await self._send_raw(envelope)
            else:
                return await self._send_structured(envelope)
        except Exception as e:
            self._total_errors += 1
            status, retry_after = self._classify_error(e)
            logger.warning(
                f"SES send error via {self.name}: {e} (status={status.value})"
            )
            return ProviderResult(
                status=status,
                error_message=str(e),
                retry_after=retry_after,
            )

    async def _send_raw(self, envelope: MailEnvelope) -> ProviderResult:
        """Send raw MIME message via SES SendRawEmail (v2: send_email with Raw)."""
        raw_bytes = self._build_raw_message(envelope)

        kwargs: dict[str, Any] = {
            "Content": {
                "Raw": {"Data": raw_bytes},
            },
        }

        # Destination (SES needs explicit destination for raw)
        kwargs["Destination"] = {
            "ToAddresses": envelope.to,
        }
        if envelope.cc:
            kwargs["Destination"]["CcAddresses"] = envelope.cc
        if envelope.bcc:
            kwargs["Destination"]["BccAddresses"] = envelope.bcc

        kwargs["FromEmailAddress"] = envelope.from_email

        if self.configuration_set:
            kwargs["ConfigurationSetName"] = self.configuration_set
        if self.source_arn:
            kwargs["FromEmailAddressIdentityArn"] = self.source_arn
        if self.return_path:
            kwargs["FeedbackForwardingEmailAddress"] = self.return_path

        tags = self._build_ses_tags(envelope)
        if tags:
            kwargs["EmailTags"] = tags

        response = await self._call_ses("send_email", **kwargs)
        message_id = response.get("MessageId", "")

        self._total_sent += 1
        logger.info(
            f"SES sent via {self.name}: {envelope.id} "
            f"(ses_msg_id={message_id})"
        )

        return ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_message_id=message_id,
            raw_response=response,
        )

    async def _send_structured(self, envelope: MailEnvelope) -> ProviderResult:
        """Send structured message via SES v2 send_email API."""
        body: dict[str, Any] = {}
        if envelope.body_text:
            body["Text"] = {"Data": envelope.body_text, "Charset": "UTF-8"}
        if envelope.body_html:
            body["Html"] = {"Data": envelope.body_html, "Charset": "UTF-8"}

        kwargs: dict[str, Any] = {
            "FromEmailAddress": envelope.from_email,
            "Destination": {
                "ToAddresses": envelope.to,
            },
            "Content": {
                "Simple": {
                    "Subject": {
                        "Data": envelope.subject,
                        "Charset": "UTF-8",
                    },
                    "Body": body,
                },
            },
        }

        if envelope.cc:
            kwargs["Destination"]["CcAddresses"] = envelope.cc
        if envelope.bcc:
            kwargs["Destination"]["BccAddresses"] = envelope.bcc
        if envelope.reply_to:
            kwargs["ReplyToAddresses"] = [envelope.reply_to]
        if self.configuration_set:
            kwargs["ConfigurationSetName"] = self.configuration_set
        if self.source_arn:
            kwargs["FromEmailAddressIdentityArn"] = self.source_arn

        tags = self._build_ses_tags(envelope)
        if tags:
            kwargs["EmailTags"] = tags

        response = await self._call_ses("send_email", **kwargs)
        message_id = response.get("MessageId", "")

        self._total_sent += 1
        logger.info(
            f"SES sent via {self.name}: {envelope.id} "
            f"(ses_msg_id={message_id})"
        )

        return ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_message_id=message_id,
            raw_response=response,
        )

    async def send_batch(
        self, envelopes: Sequence[MailEnvelope],
    ) -> List[ProviderResult]:
        """Send batch via SES (falls back to sequential for raw mode)."""
        results: list[ProviderResult] = []
        for envelope in envelopes:
            result = await self.send(envelope)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        """Check SES account status via GetAccount."""
        try:
            response = await self._call_ses("get_account")
            # Check if sending is enabled
            send_quota = response.get("SendQuota", {})
            return send_quota.get("Max24HourSend", 0) > 0
        except Exception as e:
            logger.debug(f"SES health check failed: {e}")
            return False

    # ── Error Classification ────────────────────────────────────────

    def _classify_error(self, error: Exception) -> tuple:
        """Classify an SES/AWS error into ProviderResultStatus."""
        error_code = getattr(error, "response", {})
        if isinstance(error_code, dict):
            error_code = (
                error_code.get("Error", {}).get("Code", "")
            )
        else:
            error_code = ""

        # Also check the exception class name
        exc_name = type(error).__name__
        error_str = str(error)

        # Throttling
        if error_code in _THROTTLE_CODES or exc_name in _THROTTLE_CODES:
            return ProviderResultStatus.RATE_LIMITED, 60.0
        if "throttl" in error_str.lower() or "rate" in error_str.lower():
            return ProviderResultStatus.RATE_LIMITED, 60.0

        # Permanent failures
        if error_code in _PERMANENT_CODES or exc_name in _PERMANENT_CODES:
            return ProviderResultStatus.PERMANENT_FAILURE, None

        # Connection errors
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return ProviderResultStatus.TRANSIENT_FAILURE, 15.0

        # Default to transient
        return ProviderResultStatus.TRANSIENT_FAILURE, 30.0

    def __repr__(self) -> str:
        return (
            f"SESProvider(name={self.name!r}, region={self.region!r}, "
            f"config_set={self.configuration_set!r})"
        )
