"""
Tests for AquilaMail Providers — SMTP, SES, SendGrid, File.

Comprehensive tests covering:
    - Provider instantiation and configuration
    - MIME message construction
    - Send pipeline (with mocked backends)
    - Batch sending
    - Error classification (transient, permanent, rate-limited)
    - Health checks
    - Connection pooling (SMTP)
    - File output + index (File)
    - Lifecycle (initialize / shutdown)
    - Discovery / registry integration
    - Edge cases (empty body, inline attachments, custom headers)
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from email import message_from_string
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aquilia.mail.envelope import (
    Attachment,
    EnvelopeStatus,
    MailEnvelope,
    Priority,
)
from aquilia.mail.providers import (
    IMailProvider,
    ProviderResult,
    ProviderResultStatus,
)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_envelope(**overrides) -> MailEnvelope:
    """Create a test MailEnvelope with sensible defaults."""
    defaults = {
        "id": "test-envelope-001",
        "from_email": "sender@example.com",
        "to": ["user@example.com"],
        "subject": "Test Subject",
        "body_text": "Hello, world!",
        "body_html": "<h1>Hello, world!</h1>",
    }
    defaults.update(overrides)
    return MailEnvelope(**defaults)


def _make_envelope_with_attachment(**overrides) -> MailEnvelope:
    """Create a test envelope with an attachment."""
    env = _make_envelope(**overrides)
    env.attachments = [
        Attachment(
            filename="report.pdf",
            content_type="application/pdf",
            digest="abc123",
            size=1024,
        ),
    ]
    env.metadata["blob:abc123"] = b"%PDF-1.4 fake content"
    return env


def _make_envelope_inline_image(**overrides) -> MailEnvelope:
    """Create a test envelope with an inline image."""
    env = _make_envelope(**overrides)
    env.attachments = [
        Attachment(
            filename="logo.png",
            content_type="image/png",
            digest="img001",
            size=512,
            inline=True,
            content_id="logo-cid",
        ),
    ]
    env.metadata["blob:img001"] = b"\x89PNG fake"
    return env


# ═══════════════════════════════════════════════════════════════════
# SMTP Provider Tests
# ═══════════════════════════════════════════════════════════════════


class TestSMTPProviderInit:
    """Tests for SMTPProvider construction and configuration."""

    def test_default_config(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        assert p.name == "smtp"
        assert p.host == "localhost"
        assert p.port == 587
        assert p.use_tls is True
        assert p.use_ssl is False
        assert p.timeout == 30.0
        assert p.pool_size == 3
        assert p.supports_batching is True
        assert p.provider_type == "smtp"

    def test_custom_config(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider(
            name="prod-smtp",
            host="smtp.myapp.com",
            port=465,
            username="user",
            password="pass",
            use_tls=False,
            use_ssl=True,
            timeout=60.0,
            pool_size=5,
            pool_recycle=120.0,
            priority=5,
        )
        assert p.name == "prod-smtp"
        assert p.host == "smtp.myapp.com"
        assert p.port == 465
        assert p.use_ssl is True
        assert p.pool_size == 5
        assert p.priority == 5

    def test_repr(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider(name="test", host="h.com", port=587)
        r = repr(p)
        assert "SMTPProvider" in r
        assert "h.com" in r


class TestSMTPProviderMIME:
    """Tests for SMTP MIME message construction."""

    def test_build_plain_text(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(body_html=None)
        mime = p._build_mime_message(env)
        text = mime.as_string()
        # Body may be base64-encoded; parse to verify
        parsed = message_from_string(text)
        assert "text/plain" in text
        assert env.from_email in text
        assert "X-Aquilia-Envelope-ID" in text
        # Check body via MIME walk
        body_found = False
        for part in parsed.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload and b"Hello, world!" in payload:
                    body_found = True
        assert body_found

    def test_build_html_alternative(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope()
        mime = p._build_mime_message(env)
        text = mime.as_string()
        assert "multipart/alternative" in text
        assert "text/plain" in text
        assert "text/html" in text
        # Verify HTML body via MIME parsing
        parsed = message_from_string(text)
        html_found = False
        for part in parsed.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload and b"<h1>Hello" in payload:
                    html_found = True
        assert html_found

    def test_build_with_cc_bcc(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )
        mime = p._build_mime_message(env)
        assert "cc@example.com" in mime["Cc"]
        # BCC should NOT appear in headers (by email spec)
        # but MailEnvelope carries it for sending, not for MIME headers
        # Our implementation doesn't add BCC to MIME headers (correct)

    def test_build_with_reply_to(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(reply_to="reply@example.com")
        mime = p._build_mime_message(env)
        assert mime["Reply-To"] == "reply@example.com"

    def test_build_with_custom_headers(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(headers={"X-Custom": "value123"})
        mime = p._build_mime_message(env)
        assert mime["X-Custom"] == "value123"

    def test_build_with_attachment(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope_with_attachment()
        mime = p._build_mime_message(env)
        text = mime.as_string()
        assert "report.pdf" in text
        assert "application/pdf" in text

    def test_build_with_inline_image(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope_inline_image()
        mime = p._build_mime_message(env)
        text = mime.as_string()
        assert "logo.png" in text
        assert "logo-cid" in text

    def test_build_with_trace_and_tenant(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(trace_id="trace-xyz", tenant_id="tenant-abc")
        mime = p._build_mime_message(env)
        assert mime["X-Aquilia-Trace-ID"] == "trace-xyz"
        assert mime["X-Aquilia-Tenant-ID"] == "tenant-abc"

    def test_extract_domain(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        assert SMTPProvider._extract_domain("user@example.com") == "example.com"
        assert SMTPProvider._extract_domain("Name <user@foo.org>") == "foo.org"
        assert SMTPProvider._extract_domain("noatsign") == "localhost"

    def test_message_id_uses_sender_domain(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        env = _make_envelope(from_email="admin@myapp.io")
        mime = p._build_mime_message(env)
        msg_id = mime["Message-ID"]
        assert "myapp.io" in msg_id


class TestSMTPProviderSend:
    """Tests for SMTP send with mocked aiosmtplib."""

    @pytest.mark.asyncio
    async def test_send_success(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        mock_conn = AsyncMock()
        mock_conn.send_message = AsyncMock(return_value=({}, "250 OK"))
        mock_conn.noop = AsyncMock()
        mock_conn.quit = AsyncMock()

        p._pool = [mock_conn]
        p._pool_created = {id(mock_conn): __import__("time").monotonic()}

        env = _make_envelope()
        result = await p.send(env)

        assert result.is_success
        assert result.provider_message_id is not None
        assert p._total_sent == 1
        mock_conn.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_connection_error(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()

        # Make _acquire_connection raise
        async def fail_acquire():
            raise ConnectionRefusedError("Connection refused")

        p._acquire_connection = fail_acquire

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.TRANSIENT_FAILURE
        assert "Connection refused" in result.error_message
        assert p._total_errors == 1

    @pytest.mark.asyncio
    async def test_send_batch_success(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        mock_conn = AsyncMock()
        mock_conn.send_message = AsyncMock(return_value=({}, "250 OK"))
        mock_conn.noop = AsyncMock()
        mock_conn.quit = AsyncMock()

        p._pool = [mock_conn]
        p._pool_created = {id(mock_conn): __import__("time").monotonic()}

        envs = [_make_envelope(id=f"env-{i}") for i in range(3)]
        results = await p.send_batch(envs)

        assert len(results) == 3
        assert all(r.is_success for r in results)
        assert p._total_sent == 3


class TestSMTPProviderErrorClassification:
    """Tests for SMTP error classification."""

    def test_transient_code_421(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        err = Exception("421 Service not available")
        err.code = 421
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.TRANSIENT_FAILURE

    def test_permanent_code_550(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        err = Exception("550 Mailbox not found")
        err.code = 550
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.PERMANENT_FAILURE
        assert retry is None

    def test_rate_limit_detection(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        err = Exception("Rate limit exceeded")
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.RATE_LIMITED
        assert retry > 0

    def test_connection_error(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        err = ConnectionRefusedError("refused")
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.TRANSIENT_FAILURE

    def test_is_connection_error(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        assert SMTPProvider._is_connection_error(ConnectionRefusedError())
        assert SMTPProvider._is_connection_error(TimeoutError())
        assert not SMTPProvider._is_connection_error(ValueError())


class TestSMTPProviderLifecycle:
    """Tests for SMTP lifecycle management."""

    @pytest.mark.asyncio
    async def test_shutdown_clears_pool(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        mock_conn = AsyncMock()
        mock_conn.quit = AsyncMock()
        p._pool = [mock_conn]
        p._pool_created = {id(mock_conn): 0}
        p._initialized = True

        await p.shutdown()

        assert len(p._pool) == 0
        assert p._initialized is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()
        mock_conn = AsyncMock()
        mock_conn.noop = AsyncMock()
        mock_conn.quit = AsyncMock()

        p._pool = [mock_conn]
        p._pool_created = {id(mock_conn): __import__("time").monotonic()}

        healthy = await p.health_check()
        assert healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider()

        async def fail():
            raise ConnectionRefusedError()

        p._acquire_connection = fail
        healthy = await p.health_check()
        assert healthy is False

    def test_tls_context_with_tls(self):
        from aquilia.mail.providers.smtp import SMTPProvider
        import ssl

        p = SMTPProvider(use_tls=True)
        ctx = p._build_tls_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_tls_context_no_verify(self):
        from aquilia.mail.providers.smtp import SMTPProvider
        import ssl

        p = SMTPProvider(use_tls=True, validate_certs=False)
        ctx = p._build_tls_context()
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_no_tls_context(self):
        from aquilia.mail.providers.smtp import SMTPProvider

        p = SMTPProvider(use_tls=False, use_ssl=False)
        assert p._build_tls_context() is None


# ═══════════════════════════════════════════════════════════════════
# SES Provider Tests
# ═══════════════════════════════════════════════════════════════════


class TestSESProviderInit:
    """Tests for SESProvider construction."""

    def test_default_config(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        assert p.name == "ses"
        assert p.region == "us-east-1"
        assert p.use_raw is True
        assert p.provider_type == "ses"
        assert p.supports_batching is True

    def test_custom_config(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(
            name="aws-prod",
            region="eu-west-1",
            aws_access_key_id="AKID",
            aws_secret_access_key="SECRET",
            configuration_set="my-config",
            source_arn="arn:aws:ses:eu-west-1:123:identity/x",
            tags={"env": "prod"},
        )
        assert p.region == "eu-west-1"
        assert p.aws_access_key_id == "AKID"
        assert p.configuration_set == "my-config"
        assert p.tags == {"env": "prod"}

    def test_repr(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(name="test", region="ap-southeast-1", configuration_set="cs")
        r = repr(p)
        assert "SESProvider" in r
        assert "ap-southeast-1" in r


class TestSESProviderMIME:
    """Tests for SES raw MIME construction."""

    def test_build_raw_message(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        env = _make_envelope()
        raw = p._build_raw_message(env)
        assert isinstance(raw, bytes)
        text = raw.decode("utf-8", errors="replace")
        assert "Test Subject" in text
        assert "sender@example.com" in text
        assert "X-Aquilia-Envelope-ID" in text

    def test_build_raw_with_attachment(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        env = _make_envelope_with_attachment()
        raw = p._build_raw_message(env)
        text = raw.decode("utf-8", errors="replace")
        assert "report.pdf" in text

    def test_build_ses_tags(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(tags={"env": "prod"})
        env = _make_envelope(tenant_id="t1")
        tags = p._build_ses_tags(env)
        tag_names = [t["Name"] for t in tags]
        assert "env" in tag_names
        assert "aquilia_envelope_id" in tag_names
        assert "aquilia_tenant_id" in tag_names


class TestSESProviderSend:
    """Tests for SES send with mocked AWS client."""

    @pytest.mark.asyncio
    async def test_send_raw_success(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(use_raw=True)
        mock_client = AsyncMock()
        mock_client.send_email = AsyncMock(
            return_value={"MessageId": "ses-msg-001"}
        )
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.is_success
        assert result.provider_message_id == "ses-msg-001"
        assert p._total_sent == 1

    @pytest.mark.asyncio
    async def test_send_structured_success(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(use_raw=False)
        mock_client = AsyncMock()
        mock_client.send_email = AsyncMock(
            return_value={"MessageId": "ses-msg-002"}
        )
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.is_success
        assert result.provider_message_id == "ses-msg-002"

    @pytest.mark.asyncio
    async def test_send_with_configuration_set(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider(configuration_set="my-set")
        mock_client = AsyncMock()
        mock_client.send_email = AsyncMock(
            return_value={"MessageId": "ses-cs-001"}
        )
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        env = _make_envelope()
        await p.send(env)

        call_kwargs = mock_client.send_email.call_args[1]
        assert call_kwargs["ConfigurationSetName"] == "my-set"

    @pytest.mark.asyncio
    async def test_send_error_throttled(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_client = AsyncMock()
        exc = Exception("Throttling")
        exc.response = {"Error": {"Code": "Throttling"}}
        mock_client.send_email = AsyncMock(side_effect=exc)
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.RATE_LIMITED
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_send_error_permanent(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_client = AsyncMock()
        exc = Exception("MessageRejected")
        exc.response = {"Error": {"Code": "MessageRejected"}}
        mock_client.send_email = AsyncMock(side_effect=exc)
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.PERMANENT_FAILURE

    @pytest.mark.asyncio
    async def test_send_batch(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_client = AsyncMock()
        mock_client.send_email = AsyncMock(
            return_value={"MessageId": "batch-msg"}
        )
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        envs = [_make_envelope(id=f"e{i}") for i in range(3)]
        results = await p.send_batch(envs)

        assert len(results) == 3
        assert all(r.is_success for r in results)

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_client = AsyncMock()
        mock_client.get_account = AsyncMock(
            return_value={"SendQuota": {"Max24HourSend": 50000.0}}
        )
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        assert await p.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_client = AsyncMock()
        mock_client.get_account = AsyncMock(side_effect=Exception("denied"))
        p._client = mock_client
        p._use_aiobotocore = True
        p._initialized = True

        assert await p.health_check() is False


class TestSESProviderLifecycle:
    """Tests for SES lifecycle."""

    @pytest.mark.asyncio
    async def test_shutdown_closes_client(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        mock_ctx = AsyncMock()
        p._client_ctx = mock_ctx
        p._client = AsyncMock()
        p._use_aiobotocore = True
        p._initialized = True

        await p.shutdown()

        assert p._client is None
        assert p._initialized is False

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        p._initialized = True

        # Should be a no-op
        await p.initialize()
        assert p._initialized is True


class TestSESProviderErrorClassification:
    """Tests for SES error classification."""

    def test_throttling(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        err = Exception("ThrottlingException")
        err.response = {"Error": {"Code": "ThrottlingException"}}
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.RATE_LIMITED

    def test_message_rejected(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        err = Exception("MessageRejected")
        err.response = {"Error": {"Code": "MessageRejected"}}
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.PERMANENT_FAILURE

    def test_connection_error(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        err = ConnectionError("reset")
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.TRANSIENT_FAILURE

    def test_unknown_error(self):
        from aquilia.mail.providers.ses import SESProvider

        p = SESProvider()
        err = RuntimeError("something weird")
        status, retry = p._classify_error(err)
        assert status == ProviderResultStatus.TRANSIENT_FAILURE


# ═══════════════════════════════════════════════════════════════════
# SendGrid Provider Tests
# ═══════════════════════════════════════════════════════════════════


class TestSendGridProviderInit:
    """Tests for SendGridProvider construction."""

    def test_default_config(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        assert p.name == "sendgrid"
        assert p.api_key == ""
        assert p.sandbox_mode is False
        assert p.click_tracking is True
        assert p.open_tracking is True
        assert p.provider_type == "sendgrid"

    def test_custom_config(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(
            name="sg-prod",
            api_key="SG.test_key",
            sandbox_mode=True,
            click_tracking=False,
            categories=["transactional"],
            asm_group_id=123,
            ip_pool_name="my-pool",
        )
        assert p.api_key == "SG.test_key"
        assert p.sandbox_mode is True
        assert p.click_tracking is False
        assert p.categories == ["transactional"]
        assert p.asm_group_id == 123

    def test_repr(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(name="sg", sandbox_mode=True)
        r = repr(p)
        assert "SendGridProvider" in r
        assert "sandbox=True" in r


class TestSendGridProviderPayload:
    """Tests for SendGrid payload construction."""

    def test_basic_payload(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope()
        payload = p._build_payload(env)

        assert payload["from"] == {"email": "sender@example.com"}
        assert payload["subject"] == "Test Subject"
        assert len(payload["personalizations"]) == 1
        assert payload["personalizations"][0]["to"] == [
            {"email": "user@example.com"}
        ]
        assert any(c["type"] == "text/plain" for c in payload["content"])
        assert any(c["type"] == "text/html" for c in payload["content"])

    def test_payload_with_cc_bcc(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope(
            cc=["cc@test.com"],
            bcc=["bcc@test.com"],
        )
        payload = p._build_payload(env)
        pers = payload["personalizations"][0]
        assert pers["cc"] == [{"email": "cc@test.com"}]
        assert pers["bcc"] == [{"email": "bcc@test.com"}]

    def test_payload_with_reply_to(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope(reply_to="reply@test.com")
        payload = p._build_payload(env)
        assert payload["reply_to"] == {"email": "reply@test.com"}

    def test_payload_sandbox_mode(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(sandbox_mode=True)
        env = _make_envelope()
        payload = p._build_payload(env)
        assert payload["mail_settings"]["sandbox_mode"]["enable"] is True

    def test_payload_tracking(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(click_tracking=False, open_tracking=False)
        env = _make_envelope()
        payload = p._build_payload(env)
        ts = payload["tracking_settings"]
        assert ts["click_tracking"]["enable"] is False
        assert ts["open_tracking"]["enable"] is False

    def test_payload_with_categories(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(categories=["alerts", "system"])
        env = _make_envelope()
        payload = p._build_payload(env)
        assert "alerts" in payload["categories"]
        assert "system" in payload["categories"]

    def test_payload_with_attachment(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope_with_attachment()
        payload = p._build_payload(env)
        atts = payload["attachments"]
        assert len(atts) == 1
        assert atts[0]["filename"] == "report.pdf"
        assert atts[0]["type"] == "application/pdf"
        assert atts[0]["disposition"] == "attachment"

    def test_payload_with_inline_image(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope_inline_image()
        payload = p._build_payload(env)
        atts = payload["attachments"]
        assert atts[0]["disposition"] == "inline"
        assert atts[0]["content_id"] == "logo-cid"

    def test_payload_asm_group(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(asm_group_id=99)
        env = _make_envelope()
        payload = p._build_payload(env)
        assert payload["asm"]["group_id"] == 99

    def test_payload_template_id(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(template_id="d-abc123")
        env = _make_envelope()
        payload = p._build_payload(env)
        assert payload["template_id"] == "d-abc123"

    def test_payload_custom_headers(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope(headers={"X-My-Header": "xyz"})
        payload = p._build_payload(env)
        headers = payload["personalizations"][0]["headers"]
        assert headers["X-My-Header"] == "xyz"
        assert "X-Aquilia-Envelope-ID" in headers

    def test_parse_email_plain(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        result = SendGridProvider._parse_email("user@example.com")
        assert result == {"email": "user@example.com"}

    def test_parse_email_with_display_name(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        result = SendGridProvider._parse_email("John Doe <john@example.com>")
        assert result["email"] == "john@example.com"
        assert result["name"] == "John Doe"

    def test_payload_ip_pool(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(ip_pool_name="warm-pool")
        env = _make_envelope()
        payload = p._build_payload(env)
        assert payload["ip_pool_name"] == "warm-pool"

    def test_payload_tenant_in_categories(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        env = _make_envelope(tenant_id="t1")
        payload = p._build_payload(env)
        assert "tenant:t1" in payload["categories"]


class TestSendGridProviderSend:
    """Tests for SendGrid send with mocked httpx client."""

    @pytest.mark.asyncio
    async def test_send_success(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "sg-msg-001"}
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.is_success
        assert result.provider_message_id == "sg-msg-001"
        assert p._total_sent == 1

    @pytest.mark.asyncio
    async def test_send_rate_limited(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.json = MagicMock(
            return_value={"errors": [{"message": "rate limited"}]}
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.RATE_LIMITED
        assert result.retry_after == 30.0

    @pytest.mark.asyncio
    async def test_send_auth_error(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.bad")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json = MagicMock(
            return_value={"errors": [{"message": "invalid key"}]}
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.PERMANENT_FAILURE

    @pytest.mark.asyncio
    async def test_send_bad_request(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = MagicMock(
            return_value={"errors": [{"message": "invalid email"}]}
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.PERMANENT_FAILURE

    @pytest.mark.asyncio
    async def test_send_server_error(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json = MagicMock(
            return_value={"errors": [{"message": "internal error"}]}
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.TRANSIENT_FAILURE
        assert result.retry_after == 30.0

    @pytest.mark.asyncio
    async def test_send_connection_exception(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=ConnectionError("connection reset")
        )
        p._client = mock_client
        p._initialized = True

        env = _make_envelope()
        result = await p.send(env)

        assert result.status == ProviderResultStatus.TRANSIENT_FAILURE

    @pytest.mark.asyncio
    async def test_send_batch(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider(api_key="SG.test")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "batch"}
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        envs = [_make_envelope(id=f"e{i}") for i in range(3)]
        results = await p.send_batch(envs)

        assert len(results) == 3
        assert all(r.is_success for r in results)


class TestSendGridProviderLifecycle:
    """Tests for SendGrid lifecycle."""

    @pytest.mark.asyncio
    async def test_shutdown(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        p._client = mock_client
        p._initialized = True

        await p.shutdown()

        mock_client.aclose.assert_awaited_once()
        assert p._client is None
        assert p._initialized is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        p._client = mock_client
        p._initialized = True

        assert await p.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from aquilia.mail.providers.sendgrid import SendGridProvider

        p = SendGridProvider()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("down"))
        p._client = mock_client
        p._initialized = True

        assert await p.health_check() is False


# ═══════════════════════════════════════════════════════════════════
# File Provider Tests
# ═══════════════════════════════════════════════════════════════════


class TestFileProviderInit:
    """Tests for FileProvider construction."""

    def test_default_config(self):
        from aquilia.mail.providers.file import FileProvider

        p = FileProvider()
        assert p.name == "file"
        assert str(p.output_dir) == "/tmp/aquilia_mail"
        assert p.max_files == 10000
        assert p.write_index is True
        assert p.provider_type == "file"

    def test_custom_config(self):
        from aquilia.mail.providers.file import FileProvider

        p = FileProvider(
            name="test-file",
            output_dir="/var/mail/test",
            max_files=100,
            write_index=False,
        )
        assert p.name == "test-file"
        assert str(p.output_dir) == "/var/mail/test"
        assert p.max_files == 100
        assert p.write_index is False

    def test_repr(self):
        from aquilia.mail.providers.file import FileProvider

        p = FileProvider(name="f")
        r = repr(p)
        assert "FileProvider" in r


class TestFileProviderLifecycle:
    """Tests for FileProvider lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_creates_dir(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "mail_out")
            p = FileProvider(output_dir=target)
            await p.initialize()
            assert Path(target).exists()
            assert p._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        from aquilia.mail.providers.file import FileProvider

        p = FileProvider()
        p._initialized = True
        await p.shutdown()
        assert p._initialized is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            p._initialized = True
            assert await p.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_bad_dir(self):
        from aquilia.mail.providers.file import FileProvider

        p = FileProvider(output_dir="/nonexistent/path/xyz")
        assert await p.health_check() is False


class TestFileProviderSend:
    """Tests for FileProvider send — writes .eml files."""

    @pytest.mark.asyncio
    async def test_send_creates_eml(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope()
            result = await p.send(env)

            assert result.is_success
            assert "file:" in result.provider_message_id
            assert p._total_sent == 1

            # Check file exists
            eml_files = list(Path(tmpdir).glob("*.eml"))
            assert len(eml_files) == 1

            # Check content is valid email
            content = eml_files[0].read_text(encoding="utf-8")
            assert "Test Subject" in content
            assert "sender@example.com" in content
            assert "user@example.com" in content
            # Body is base64-encoded in MIME — parse and decode to verify
            from email import message_from_string
            parsed = message_from_string(content)
            bodies = []
            for part in parsed.walk():
                if part.get_content_type() in ("text/plain", "text/html"):
                    bodies.append(part.get_payload(decode=True).decode())
            assert any("Hello, world!" in b for b in bodies)

    @pytest.mark.asyncio
    async def test_send_writes_index(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir, write_index=True)
            await p.initialize()

            env = _make_envelope()
            await p.send(env)

            index_path = Path(tmpdir) / "index.jsonl"
            assert index_path.exists()

            line = index_path.read_text().strip()
            entry = json.loads(line)
            assert entry["envelope_id"] == "test-envelope-001"
            assert entry["subject"] == "Test Subject"
            assert entry["to"] == ["user@example.com"]

    @pytest.mark.asyncio
    async def test_send_no_index(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir, write_index=False)
            await p.initialize()

            env = _make_envelope()
            await p.send(env)

            index_path = Path(tmpdir) / "index.jsonl"
            assert not index_path.exists()

    @pytest.mark.asyncio
    async def test_send_with_html(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope()
            await p.send(env)

            eml_files = list(Path(tmpdir).glob("*.eml"))
            content = eml_files[0].read_text(encoding="utf-8")
            assert "multipart/alternative" in content
            # HTML body is base64-encoded in MIME — parse and decode
            from email import message_from_string
            parsed = message_from_string(content)
            html_bodies = []
            for part in parsed.walk():
                if part.get_content_type() == "text/html":
                    html_bodies.append(part.get_payload(decode=True).decode())
            assert any("<h1>Hello" in b for b in html_bodies)

    @pytest.mark.asyncio
    async def test_send_with_attachment(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope_with_attachment()
            await p.send(env)

            eml_files = list(Path(tmpdir).glob("*.eml"))
            content = eml_files[0].read_text(encoding="utf-8")
            # Attachment filename appears in Content-Disposition or Content-Type header
            from email import message_from_string
            parsed = message_from_string(content)
            filenames = []
            for part in parsed.walk():
                fn = part.get_filename()
                if fn:
                    filenames.append(fn)
            assert "report.pdf" in filenames

    @pytest.mark.asyncio
    async def test_send_batch(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            envs = [_make_envelope(id=f"batch-{i}") for i in range(5)]
            results = await p.send_batch(envs)

            assert len(results) == 5
            assert all(r.is_success for r in results)
            assert p._total_sent == 5

            eml_files = list(Path(tmpdir).glob("*.eml"))
            assert len(eml_files) == 5

    @pytest.mark.asyncio
    async def test_send_with_tracking_headers(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope(
                trace_id="trace-123", tenant_id="tenant-456",
            )
            await p.send(env)

            eml_files = list(Path(tmpdir).glob("*.eml"))
            content = eml_files[0].read_text(encoding="utf-8")
            assert "X-Aquilia-Trace-ID: trace-123" in content
            assert "X-Aquilia-Tenant-ID: tenant-456" in content

    @pytest.mark.asyncio
    async def test_eml_parseable(self):
        """Generated .eml files should be parseable by email library."""
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope(
                cc=["cc@test.com"],
                reply_to="reply@test.com",
                headers={"X-Custom": "val"},
            )
            await p.send(env)

            eml_files = list(Path(tmpdir).glob("*.eml"))
            content = eml_files[0].read_text(encoding="utf-8")
            parsed = message_from_string(content)

            assert parsed["From"] == "sender@example.com"
            assert "user@example.com" in parsed["To"]
            assert parsed["Subject"] == "Test Subject"
            assert parsed["Reply-To"] == "reply@test.com"
            assert parsed["X-Custom"] == "val"
            assert parsed["X-Aquilia-Envelope-ID"] == "test-envelope-001"


class TestFileProviderUtilities:
    """Tests for FileProvider utility methods."""

    @pytest.mark.asyncio
    async def test_list_files(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            for i in range(3):
                env = _make_envelope(id=f"list-{i}")
                await p.send(env)

            files = p.list_files()
            assert len(files) == 3

    @pytest.mark.asyncio
    async def test_read_last(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            env = _make_envelope(subject="Last Email")
            await p.send(env)

            last = p.read_last()
            assert last is not None
            assert "Last Email" in last

    @pytest.mark.asyncio
    async def test_read_last_empty(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            assert p.read_last() is None

    @pytest.mark.asyncio
    async def test_clear(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir)
            await p.initialize()

            for i in range(3):
                env = _make_envelope(id=f"clear-{i}")
                await p.send(env)

            assert len(p.list_files()) == 3

            count = p.clear()
            assert count == 3
            assert len(p.list_files()) == 0


class TestFileProviderRotation:
    """Tests for FileProvider file rotation."""

    @pytest.mark.asyncio
    async def test_rotation(self):
        from aquilia.mail.providers.file import FileProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            p = FileProvider(output_dir=tmpdir, max_files=3)
            await p.initialize()

            for i in range(5):
                env = _make_envelope(id=f"rot-{i}")
                await p.send(env)

            files = p.list_files()
            assert len(files) <= 3


# ═══════════════════════════════════════════════════════════════════
# Console Provider Tests (existing, but adding completeness)
# ═══════════════════════════════════════════════════════════════════


class TestConsoleProvider:
    """Additional tests for ConsoleProvider."""

    @pytest.mark.asyncio
    async def test_send_success(self):
        from aquilia.mail.providers.console import ConsoleProvider

        p = ConsoleProvider()
        await p.initialize()

        env = _make_envelope()
        result = await p.send(env)

        assert result.is_success
        assert "console-" in result.provider_message_id

    @pytest.mark.asyncio
    async def test_health_check(self):
        from aquilia.mail.providers.console import ConsoleProvider

        p = ConsoleProvider()
        assert await p.health_check() is True


# ═══════════════════════════════════════════════════════════════════
# Provider Registry Discovery — Finds All Providers
# ═══════════════════════════════════════════════════════════════════


class TestProviderDiscovery:
    """Tests that all providers are discoverable by MailProviderRegistry."""

    def test_registry_discovers_all_built_in(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        discovered = registry.discover()

        # Should find all 5 built-in providers
        assert "smtp" in discovered
        assert "ses" in discovered
        assert "sendgrid" in discovered
        assert "file" in discovered
        assert "console" in discovered

    def test_registry_returns_correct_classes(self):
        from aquilia.mail.di_providers import MailProviderRegistry
        from aquilia.mail.providers.smtp import SMTPProvider
        from aquilia.mail.providers.ses import SESProvider
        from aquilia.mail.providers.sendgrid import SendGridProvider
        from aquilia.mail.providers.file import FileProvider
        from aquilia.mail.providers.console import ConsoleProvider

        registry = MailProviderRegistry()
        assert registry.get_provider_class("smtp") is SMTPProvider
        assert registry.get_provider_class("ses") is SESProvider
        assert registry.get_provider_class("sendgrid") is SendGridProvider
        assert registry.get_provider_class("file") is FileProvider
        assert registry.get_provider_class("console") is ConsoleProvider

    def test_list_types_includes_all(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        types = registry.list_types()
        assert set(types) >= {"smtp", "ses", "sendgrid", "file", "console"}


# ═══════════════════════════════════════════════════════════════════
# Service._create_provider — Factory Wiring
# ═══════════════════════════════════════════════════════════════════


class TestServiceProviderFactory:
    """Tests that MailService._create_provider creates correct provider types."""

    def test_create_smtp_provider(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig(
            name="s1", type="smtp", host="smtp.test.com", port=465,
            username="u", password="p", use_tls=False, use_ssl=True,
        )
        provider = svc._create_provider(pc)
        assert type(provider).__name__ == "SMTPProvider"
        assert provider.host == "smtp.test.com"
        assert provider.port == 465
        assert provider.use_ssl is True

    def test_create_ses_provider(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig({
            "name": "aws", "type": "ses",
            "config": {"region": "eu-west-1"},
        })
        provider = svc._create_provider(pc)
        assert type(provider).__name__ == "SESProvider"
        assert provider.region == "eu-west-1"

    def test_create_sendgrid_provider(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig({
            "name": "sg", "type": "sendgrid",
            "config": {"api_key": "SG.test"},
        })
        provider = svc._create_provider(pc)
        assert type(provider).__name__ == "SendGridProvider"
        assert provider.api_key == "SG.test"

    def test_create_console_provider(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig(name="c", type="console")
        provider = svc._create_provider(pc)
        assert type(provider).__name__ == "ConsoleProvider"

    def test_create_file_provider(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig({
            "name": "f", "type": "file",
            "config": {"output_dir": "/tmp/test_mail"},
        })
        provider = svc._create_provider(pc)
        assert type(provider).__name__ == "FileProvider"
        assert str(provider.output_dir) == "/tmp/test_mail"

    def test_create_unknown_falls_back_to_discovery(self):
        from aquilia.mail.config import ProviderConfig
        from aquilia.mail.faults import MailConfigFault
        from aquilia.mail.service import MailService

        svc = MailService()
        pc = ProviderConfig({
            "name": "bad", "type": "nonexistent_xyz",
            "config": {},
        })
        with pytest.raises(MailConfigFault):
            svc._create_provider(pc)


# ═══════════════════════════════════════════════════════════════════
# Mail Exports — Provider Classes
# ═══════════════════════════════════════════════════════════════════


class TestProviderExports:
    """Tests for provider class exports."""

    def test_all_providers_in_mail_init(self):
        import aquilia.mail as m

        for name in [
            "SMTPProvider", "SESProvider", "SendGridProvider",
            "FileProvider", "ConsoleProvider",
        ]:
            assert name in m.__all__, f"{name} not in __all__"
            assert hasattr(m, name), f"{name} not exported"

    def test_all_providers_in_providers_init(self):
        import aquilia.mail.providers as p

        for name in [
            "SMTPProvider", "SESProvider", "SendGridProvider",
            "FileProvider", "ConsoleProvider",
        ]:
            assert name in p.__all__
            assert hasattr(p, name)

    def test_provider_protocol_compliance(self):
        """All providers should have the IMailProvider methods."""
        from aquilia.mail.providers.smtp import SMTPProvider
        from aquilia.mail.providers.ses import SESProvider
        from aquilia.mail.providers.sendgrid import SendGridProvider
        from aquilia.mail.providers.file import FileProvider
        from aquilia.mail.providers.console import ConsoleProvider

        # Methods are defined on the class
        for cls in [SMTPProvider, SESProvider, SendGridProvider,
                    FileProvider, ConsoleProvider]:
            assert hasattr(cls, "send"), f"{cls.__name__} missing send()"
            assert hasattr(cls, "send_batch"), f"{cls.__name__} missing send_batch()"
            assert hasattr(cls, "health_check"), f"{cls.__name__} missing health_check()"
            assert hasattr(cls, "initialize"), f"{cls.__name__} missing initialize()"
            assert hasattr(cls, "shutdown"), f"{cls.__name__} missing shutdown()"

        # Instance attributes (name, supports_batching) are set in __init__
        instances = [
            SMTPProvider(host="localhost"),
            SESProvider(region="us-east-1"),
            SendGridProvider(api_key="test"),
            FileProvider(),
            ConsoleProvider(),
        ]
        for inst in instances:
            assert hasattr(inst, "name"), f"{type(inst).__name__} missing name"
            assert hasattr(inst, "supports_batching"), f"{type(inst).__name__} missing supports_batching"
