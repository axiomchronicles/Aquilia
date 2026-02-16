"""
Tests for AquilaMail PR1 — Core Types.

Covers:
    - MailEnvelope: creation, serialization, digest, recipients
    - Attachment: creation, serialization
    - EmailMessage: validation, build_envelope, attachments
    - EmailMultiAlternatives: attach_alternative
    - TemplateMessage: template rendering, subject rendering
    - MailConfig: defaults, from_dict, development(), production()
    - ProviderConfig, RetryConfig, etc.: to_dict roundtrips
    - ProviderResult: is_success, should_retry
    - Faults: all 7 fault types
    - ATS template stub: render_string, render_template
    - Service: singleton accessor, send pipeline
    - ConsoleProvider: end-to-end console send
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════
# ENVELOPE
# ═══════════════════════════════════════════════════════════════════

class TestMailEnvelope:
    """Tests for MailEnvelope."""

    def test_create_default(self):
        from aquilia.mail.envelope import MailEnvelope, EnvelopeStatus
        env = MailEnvelope()
        assert env.status == EnvelopeStatus.QUEUED
        assert env.to == []
        assert env.cc == []
        assert env.bcc == []
        assert env.subject == ""
        assert env.body_text == ""
        assert env.body_html is None
        assert env.attempts == 0
        assert env.max_attempts == 5
        assert isinstance(env.id, str)
        assert len(env.id) > 0
        assert isinstance(env.created_at, datetime)

    def test_create_with_values(self):
        from aquilia.mail.envelope import MailEnvelope, EnvelopeStatus, Priority
        env = MailEnvelope(
            from_email="sender@test.com",
            to=["user@test.com"],
            cc=["cc@test.com"],
            subject="Hello",
            body_text="World",
            priority=Priority.HIGH.value,
        )
        assert env.from_email == "sender@test.com"
        assert env.to == ["user@test.com"]
        assert env.cc == ["cc@test.com"]
        assert env.subject == "Hello"
        assert env.body_text == "World"
        assert env.priority == 25

    def test_compute_digest_deterministic(self):
        from aquilia.mail.envelope import MailEnvelope
        env1 = MailEnvelope(
            to=["a@test.com", "b@test.com"],
            subject="Hello",
            body_text="World",
        )
        env2 = MailEnvelope(
            to=["b@test.com", "a@test.com"],  # different order
            subject="Hello",
            body_text="World",
        )
        d1 = env1.compute_digest()
        d2 = env2.compute_digest()
        # Sorted recipients → same digest
        assert d1 == d2
        assert len(d1) == 64  # SHA-256 hex

    def test_compute_digest_different_content(self):
        from aquilia.mail.envelope import MailEnvelope
        env1 = MailEnvelope(to=["a@test.com"], subject="A", body_text="X")
        env2 = MailEnvelope(to=["a@test.com"], subject="B", body_text="X")
        env1.compute_digest()
        env2.compute_digest()
        assert env1.digest != env2.digest

    def test_all_recipients(self):
        from aquilia.mail.envelope import MailEnvelope
        env = MailEnvelope(
            to=["a@test.com", "b@test.com"],
            cc=["c@test.com"],
            bcc=["d@test.com", "A@test.com"],  # duplicate of to
        )
        recipients = env.all_recipients()
        assert len(recipients) == 4  # A@test.com deduped
        assert "a@test.com" in recipients
        assert "b@test.com" in recipients
        assert "c@test.com" in recipients
        assert "d@test.com" in recipients

    def test_recipient_domains(self):
        from aquilia.mail.envelope import MailEnvelope
        env = MailEnvelope(
            to=["a@example.com", "b@test.org"],
            cc=["c@example.com"],
        )
        domains = env.recipient_domains()
        assert domains == {"example.com", "test.org"}

    def test_to_dict_and_from_dict_roundtrip(self):
        from aquilia.mail.envelope import MailEnvelope, Attachment, EnvelopeStatus
        original = MailEnvelope(
            from_email="sender@test.com",
            to=["a@test.com"],
            cc=["b@test.com"],
            bcc=["c@test.com"],
            reply_to="reply@test.com",
            subject="Test Subject",
            body_text="Hello",
            body_html="<h1>Hello</h1>",
            headers={"X-Custom": "value"},
            attachments=[
                Attachment(
                    filename="doc.pdf",
                    content_type="application/pdf",
                    digest="abc123",
                    size=1024,
                )
            ],
            priority=25,
            idempotency_key="idem-123",
            tenant_id="tenant-1",
            metadata={"key": "val"},
        )
        original.compute_digest()
        d = original.to_dict()
        restored = MailEnvelope.from_dict(d)
        assert restored.from_email == original.from_email
        assert restored.to == original.to
        assert restored.cc == original.cc
        assert restored.bcc == original.bcc
        assert restored.subject == original.subject
        assert restored.body_text == original.body_text
        assert restored.body_html == original.body_html
        assert restored.headers == original.headers
        assert len(restored.attachments) == 1
        assert restored.attachments[0].filename == "doc.pdf"
        assert restored.priority == 25
        assert restored.idempotency_key == "idem-123"
        assert restored.tenant_id == "tenant-1"
        assert restored.metadata == {"key": "val"}
        assert restored.digest == original.digest

    def test_from_dict_with_missing_fields(self):
        from aquilia.mail.envelope import MailEnvelope, EnvelopeStatus
        env = MailEnvelope.from_dict({"subject": "Minimal"})
        assert env.subject == "Minimal"
        assert env.status == EnvelopeStatus.QUEUED
        assert env.to == []
        assert isinstance(env.id, str)

    def test_repr(self):
        from aquilia.mail.envelope import MailEnvelope
        env = MailEnvelope(to=["x@test.com"], subject="Hi")
        r = repr(env)
        assert "MailEnvelope" in r
        assert "x@test.com" in r
        assert "Hi" in r

    def test_repr_many_recipients(self):
        from aquilia.mail.envelope import MailEnvelope
        env = MailEnvelope(to=[f"{i}@test.com" for i in range(10)], subject="Bulk")
        r = repr(env)
        assert "(+7)" in r  # 10 - 3 shown


# ═══════════════════════════════════════════════════════════════════
# ATTACHMENT
# ═══════════════════════════════════════════════════════════════════

class TestAttachment:
    """Tests for Attachment dataclass."""

    def test_create(self):
        from aquilia.mail.envelope import Attachment
        att = Attachment(
            filename="report.pdf",
            content_type="application/pdf",
            digest="sha256hex",
            size=2048,
        )
        assert att.filename == "report.pdf"
        assert att.inline is False
        assert att.content_id is None

    def test_inline_attachment(self):
        from aquilia.mail.envelope import Attachment
        att = Attachment(
            filename="logo.png",
            content_type="image/png",
            digest="sha256hex",
            size=512,
            inline=True,
            content_id="logo-cid",
        )
        assert att.inline is True
        assert att.content_id == "logo-cid"

    def test_to_dict_from_dict_roundtrip(self):
        from aquilia.mail.envelope import Attachment
        att = Attachment(
            filename="file.txt",
            content_type="text/plain",
            digest="abc",
            size=100,
            inline=True,
            content_id="cid-1",
        )
        d = att.to_dict()
        restored = Attachment.from_dict(d)
        assert restored.filename == att.filename
        assert restored.content_type == att.content_type
        assert restored.digest == att.digest
        assert restored.size == att.size
        assert restored.inline == att.inline
        assert restored.content_id == att.content_id


# ═══════════════════════════════════════════════════════════════════
# PRIORITY & ENVELOPE STATUS ENUMS
# ═══════════════════════════════════════════════════════════════════

class TestEnums:
    def test_envelope_status_values(self):
        from aquilia.mail.envelope import EnvelopeStatus
        assert EnvelopeStatus.QUEUED.value == "queued"
        assert EnvelopeStatus.SENDING.value == "sending"
        assert EnvelopeStatus.SENT.value == "sent"
        assert EnvelopeStatus.FAILED.value == "failed"
        assert EnvelopeStatus.BOUNCED.value == "bounced"
        assert EnvelopeStatus.CANCELLED.value == "cancelled"

    def test_priority_ordering(self):
        from aquilia.mail.envelope import Priority
        assert Priority.CRITICAL < Priority.HIGH < Priority.NORMAL < Priority.LOW < Priority.BULK

    def test_priority_values(self):
        from aquilia.mail.envelope import Priority
        assert Priority.CRITICAL.value == 0
        assert Priority.HIGH.value == 25
        assert Priority.NORMAL.value == 50
        assert Priority.LOW.value == 75
        assert Priority.BULK.value == 100


# ═══════════════════════════════════════════════════════════════════
# EMAIL MESSAGE
# ═══════════════════════════════════════════════════════════════════

class TestEmailMessage:
    """Tests for EmailMessage."""

    def test_create_basic(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(
            subject="Test",
            body="Hello",
            to=["user@test.com"],
        )
        assert msg.subject == "Test"
        assert msg.body == "Hello"
        assert msg.to == ["user@test.com"]
        assert msg.from_email is None

    def test_validate_email_addresses(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(
            to=["valid@test.com", "Display Name <display@test.com>"],
        )
        assert len(msg.to) == 2

    def test_invalid_email_raises_fault(self):
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.faults import MailValidationFault
        with pytest.raises(MailValidationFault):
            EmailMessage(to=["not-an-email"])

    def test_empty_email_raises_fault(self):
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.faults import MailValidationFault
        with pytest.raises(MailValidationFault):
            EmailMessage(to=[""])

    def test_build_envelope_requires_recipients(self):
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.faults import MailValidationFault
        msg = EmailMessage(subject="No recipients")
        with pytest.raises(MailValidationFault, match="recipient"):
            msg.build_envelope()

    def test_build_envelope_success(self):
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.envelope import EnvelopeStatus
        msg = EmailMessage(
            subject="Hello",
            body="World",
            from_email="sender@test.com",
            to=["user@test.com"],
        )
        envelope, blobs = msg.build_envelope()
        assert envelope.subject == "Hello"
        assert envelope.body_text == "World"
        assert envelope.from_email == "sender@test.com"
        assert envelope.to == ["user@test.com"]
        assert envelope.status == EnvelopeStatus.QUEUED
        assert len(envelope.digest) == 64
        assert blobs == {}

    def test_build_envelope_uses_default_from(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(subject="Hi", body="Test", to=["a@test.com"])
        envelope, _ = msg.build_envelope(default_from="default@app.com")
        assert envelope.from_email == "default@app.com"

    def test_attach_raw(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(to=["a@test.com"])
        msg.attach("data.csv", b"col1,col2\n1,2", "text/csv")
        envelope, blobs = msg.build_envelope()
        assert len(envelope.attachments) == 1
        assert envelope.attachments[0].filename == "data.csv"
        assert len(blobs) == 1

    def test_attach_file(self, tmp_path):
        from aquilia.mail.message import EmailMessage
        f = tmp_path / "test.txt"
        f.write_text("hello")
        msg = EmailMessage(to=["a@test.com"])
        msg.attach_file(f)
        envelope, blobs = msg.build_envelope()
        assert len(envelope.attachments) == 1
        assert envelope.attachments[0].filename == "test.txt"
        assert envelope.attachments[0].content_type == "text/plain"

    def test_attach_file_not_found(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(to=["a@test.com"])
        with pytest.raises(FileNotFoundError):
            msg.attach_file("/nonexistent/file.txt")

    def test_attach_returns_self(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(to=["a@test.com"])
        result = msg.attach("f.txt", b"data", "text/plain")
        assert result is msg  # fluent API

    def test_priority(self):
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.envelope import Priority
        msg = EmailMessage(
            to=["a@test.com"],
            priority=Priority.CRITICAL.value,
        )
        envelope, _ = msg.build_envelope()
        assert envelope.priority == 0

    def test_idempotency_key(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(
            to=["a@test.com"],
            idempotency_key="unique-key-123",
        )
        envelope, _ = msg.build_envelope()
        assert envelope.idempotency_key == "unique-key-123"

    def test_metadata(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(
            to=["a@test.com"],
            metadata={"campaign": "launch"},
        )
        envelope, _ = msg.build_envelope()
        assert envelope.metadata == {"campaign": "launch"}

    def test_repr(self):
        from aquilia.mail.message import EmailMessage
        msg = EmailMessage(subject="Test", to=["a@test.com"])
        r = repr(msg)
        assert "EmailMessage" in r
        assert "Test" in r


# ═══════════════════════════════════════════════════════════════════
# EMAIL MULTI ALTERNATIVES
# ═══════════════════════════════════════════════════════════════════

class TestEmailMultiAlternatives:
    """Tests for EmailMultiAlternatives."""

    def test_attach_alternative(self):
        from aquilia.mail.message import EmailMultiAlternatives
        msg = EmailMultiAlternatives(
            subject="News",
            body="Plain text",
            to=["a@test.com"],
        )
        msg.attach_alternative("<h1>HTML</h1>", "text/html")
        envelope, _ = msg.build_envelope()
        assert envelope.body_text == "Plain text"
        assert envelope.body_html == "<h1>HTML</h1>"

    def test_attach_alternative_returns_self(self):
        from aquilia.mail.message import EmailMultiAlternatives
        msg = EmailMultiAlternatives(to=["a@test.com"])
        result = msg.attach_alternative("<b>Hi</b>", "text/html")
        assert result is msg


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE MESSAGE
# ═══════════════════════════════════════════════════════════════════

class TestTemplateMessage:
    """Tests for TemplateMessage."""

    def test_create(self):
        from aquilia.mail.message import TemplateMessage
        msg = TemplateMessage(
            template="welcome.aqt",
            context={"user": {"name": "Asha"}},
            to=["asha@test.com"],
            subject="Welcome!",
        )
        assert msg.template_name == "welcome.aqt"
        assert msg.template_context == {"user": {"name": "Asha"}}

    def test_build_envelope_renders_template(self, tmp_path):
        from aquilia.mail.message import TemplateMessage
        # Write a template file
        tpl = tmp_path / "greet.aqt"
        tpl.write_text("<p>Hello, << name >>!</p>")

        msg = TemplateMessage(
            template=str(tpl),
            context={"name": "World"},
            to=["a@test.com"],
            subject="Greeting",
        )
        envelope, _ = msg.build_envelope()
        assert envelope.body_html == "<p>Hello, World!</p>"
        assert "Hello, World!" in envelope.body_text  # auto-generated plain text
        assert envelope.template_name == str(tpl)

    def test_subject_ats_rendering(self, tmp_path):
        from aquilia.mail.message import TemplateMessage
        tpl = tmp_path / "body.aqt"
        tpl.write_text("<p>Body</p>")
        msg = TemplateMessage(
            template=str(tpl),
            context={"user_name": "Asha"},
            to=["a@test.com"],
            subject="Hi << user_name >>!",
        )
        envelope, _ = msg.build_envelope()
        assert envelope.subject == "Hi Asha!"

    def test_repr(self):
        from aquilia.mail.message import TemplateMessage
        msg = TemplateMessage(
            template="test.aqt",
            context={},
            to=["a@test.com"],
        )
        r = repr(msg)
        assert "TemplateMessage" in r
        assert "test.aqt" in r


# ═══════════════════════════════════════════════════════════════════
# HTML TO TEXT
# ═══════════════════════════════════════════════════════════════════

class TestHtmlToText:
    """Tests for the _html_to_text helper."""

    def test_strips_tags(self):
        from aquilia.mail.message import _html_to_text
        assert _html_to_text("<p>Hello</p>") == "Hello"

    def test_br_to_newline(self):
        from aquilia.mail.message import _html_to_text
        result = _html_to_text("A<br>B<br/>C")
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_paragraphs_to_double_newlines(self):
        from aquilia.mail.message import _html_to_text
        result = _html_to_text("<p>Para 1</p><p>Para 2</p>")
        assert "Para 1" in result
        assert "Para 2" in result

    def test_empty_input(self):
        from aquilia.mail.message import _html_to_text
        assert _html_to_text("") == ""


# ═══════════════════════════════════════════════════════════════════
# MAIL CONFIG
# ═══════════════════════════════════════════════════════════════════

class TestMailConfig:
    """Tests for MailConfig and sub-configs."""

    def test_defaults(self):
        from aquilia.mail.config import MailConfig
        config = MailConfig()
        assert config.enabled is True
        assert config.default_from == "noreply@localhost"
        assert config.console_backend is False
        assert config.preview_mode is False
        assert config.providers == []
        assert config.retry.max_attempts == 5
        assert config.rate_limit.global_per_minute == 1000

    def test_development(self):
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        assert config.console_backend is True
        assert config.preview_mode is True
        assert config.default_from == "dev@localhost"
        assert len(config.providers) == 1
        assert config.providers[0].type == "console"

    def test_production(self):
        from aquilia.mail.config import MailConfig
        config = MailConfig.production(default_from="noreply@myapp.com")
        assert config.default_from == "noreply@myapp.com"
        assert config.console_backend is False
        assert config.preview_mode is False

    def test_from_dict_basic(self):
        from aquilia.mail.config import MailConfig
        data = {
            "enabled": True,
            "default_from": "test@test.com",
            "subject_prefix": "[Test] ",
            "providers": [
                {"name": "smtp1", "type": "smtp", "host": "smtp.test.com"},
            ],
        }
        config = MailConfig.from_dict(data)
        assert config.default_from == "test@test.com"
        assert config.subject_prefix == "[Test] "
        assert len(config.providers) == 1
        assert config.providers[0].name == "smtp1"
        assert config.providers[0].host == "smtp.test.com"

    def test_from_dict_nested_configs(self):
        from aquilia.mail.config import MailConfig
        data = {
            "retry": {"max_attempts": 3, "base_delay": 2.0, "max_delay": 600, "jitter": False},
            "rate_limit": {"global_per_minute": 500, "per_domain_per_minute": 50},
            "security": {"dkim_enabled": True, "dkim_domain": "test.com"},
        }
        config = MailConfig.from_dict(data)
        assert config.retry.max_attempts == 3
        assert config.retry.base_delay == 2.0
        assert config.retry.jitter is False
        assert config.rate_limit.global_per_minute == 500
        assert config.security.dkim_enabled is True
        assert config.security.dkim_domain == "test.com"

    def test_to_dict_roundtrip(self):
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert d["enabled"] is True
        assert d["console_backend"] is True
        assert len(d["providers"]) == 1


class TestProviderConfig:
    def test_defaults(self):
        from aquilia.mail.config import ProviderConfig
        pc = ProviderConfig(name="smtp1", type="smtp")
        assert pc.priority == 50
        assert pc.enabled is True
        assert pc.use_tls is True
        assert pc.timeout == 30.0

    def test_to_dict(self):
        from aquilia.mail.config import ProviderConfig
        pc = ProviderConfig(name="ses", type="ses")
        d = pc.to_dict()
        assert d["name"] == "ses"
        assert d["type"] == "ses"


class TestRetryConfig:
    def test_defaults(self):
        from aquilia.mail.config import RetryConfig
        rc = RetryConfig()
        assert rc.max_attempts == 5
        assert rc.base_delay == 1.0
        assert rc.max_delay == 3600.0
        assert rc.jitter is True

    def test_to_dict(self):
        from aquilia.mail.config import RetryConfig
        rc = RetryConfig(max_attempts=10)
        d = rc.to_dict()
        assert d["max_attempts"] == 10


class TestRateLimitConfig:
    def test_defaults(self):
        from aquilia.mail.config import RateLimitConfig
        rl = RateLimitConfig()
        assert rl.global_per_minute == 1000
        assert rl.per_domain_per_minute == 100

    def test_to_dict(self):
        from aquilia.mail.config import RateLimitConfig
        rl = RateLimitConfig(global_per_minute=2000)
        d = rl.to_dict()
        assert d["global_per_minute"] == 2000


class TestSecurityConfig:
    def test_defaults(self):
        from aquilia.mail.config import SecurityConfig
        sc = SecurityConfig()
        assert sc.dkim_enabled is False
        assert sc.require_tls is True
        assert sc.pii_redaction_enabled is False


class TestTemplateConfig:
    def test_defaults(self):
        from aquilia.mail.config import TemplateConfig
        tc = TemplateConfig()
        assert tc.template_dirs == ["mail_templates"]
        assert tc.auto_escape is True
        assert tc.cache_compiled is True


class TestQueueConfig:
    def test_defaults(self):
        from aquilia.mail.config import QueueConfig
        qc = QueueConfig()
        assert qc.batch_size == 50
        assert qc.poll_interval == 1.0
        assert qc.dedupe_window_seconds == 3600
        assert qc.retention_days == 30


# ═══════════════════════════════════════════════════════════════════
# PROVIDER RESULT
# ═══════════════════════════════════════════════════════════════════

class TestProviderResult:
    """Tests for ProviderResult."""

    def test_success(self):
        from aquilia.mail.providers import ProviderResult, ProviderResultStatus
        r = ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_message_id="msg-123",
        )
        assert r.is_success is True
        assert r.should_retry is False

    def test_transient_failure(self):
        from aquilia.mail.providers import ProviderResult, ProviderResultStatus
        r = ProviderResult(
            status=ProviderResultStatus.TRANSIENT_FAILURE,
            error_message="timeout",
        )
        assert r.is_success is False
        assert r.should_retry is True

    def test_permanent_failure(self):
        from aquilia.mail.providers import ProviderResult, ProviderResultStatus
        r = ProviderResult(
            status=ProviderResultStatus.PERMANENT_FAILURE,
            error_message="invalid recipient",
        )
        assert r.is_success is False
        assert r.should_retry is False

    def test_rate_limited(self):
        from aquilia.mail.providers import ProviderResult, ProviderResultStatus
        r = ProviderResult(
            status=ProviderResultStatus.RATE_LIMITED,
            retry_after=30.0,
        )
        assert r.is_success is False
        assert r.should_retry is True
        assert r.retry_after == 30.0

    def test_repr(self):
        from aquilia.mail.providers import ProviderResult, ProviderResultStatus
        r = ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_message_id="id-1",
        )
        assert "SUCCESS" in repr(r).upper()


# ═══════════════════════════════════════════════════════════════════
# FAULTS
# ═══════════════════════════════════════════════════════════════════

class TestMailFaults:
    """Tests for all 7 mail fault types."""

    def test_mail_fault_base(self):
        from aquilia.mail.faults import MailFault
        f = MailFault("Something went wrong")
        assert "Something went wrong" in str(f)
        assert f.code == "MAIL_ERROR"

    def test_mail_send_fault_transient(self):
        from aquilia.mail.faults import MailSendFault
        f = MailSendFault(
            "Connection timeout",
            provider="smtp1",
            transient=True,
            envelope_id="env-123",
        )
        assert f.provider == "smtp1"
        assert f.transient is True
        assert f.code == "MAIL_SEND_TRANSIENT"
        assert f.recoverable is True

    def test_mail_send_fault_permanent(self):
        from aquilia.mail.faults import MailSendFault
        f = MailSendFault(
            "Mailbox not found",
            provider="ses",
            transient=False,
        )
        assert f.code == "MAIL_SEND_PERMANENT"
        assert f.recoverable is False

    def test_mail_template_fault(self):
        from aquilia.mail.faults import MailTemplateFault
        f = MailTemplateFault(
            "Syntax error",
            template_name="broken.aqt",
            line=42,
            column=10,
        )
        assert f.template_name == "broken.aqt"
        assert f.code == "MAIL_TEMPLATE_ERROR"

    def test_mail_config_fault(self):
        from aquilia.mail.faults import MailConfigFault
        f = MailConfigFault(
            "Missing SMTP host",
            config_key="mail.providers.smtp.host",
        )
        assert f.code == "MAIL_CONFIG_ERROR"

    def test_mail_suppressed_fault(self):
        from aquilia.mail.faults import MailSuppressedFault
        f = MailSuppressedFault("user@bounced.com", reason="hard_bounce")
        assert f.email == "user@bounced.com"
        assert f.code == "MAIL_SUPPRESSED"
        assert "suppressed" in str(f).lower()

    def test_mail_rate_limit_fault(self):
        from aquilia.mail.faults import MailRateLimitFault
        f = MailRateLimitFault(
            "Too many requests",
            scope="per_domain",
            retry_after=60.0,
        )
        assert f.code == "MAIL_RATE_LIMITED"
        assert f.recoverable is True

    def test_mail_validation_fault(self):
        from aquilia.mail.faults import MailValidationFault
        f = MailValidationFault("Bad address", field="to")
        assert f.code == "MAIL_VALIDATION_ERROR"
        assert f.recoverable is False

    def test_fault_domain_mail(self):
        from aquilia.mail.faults import MailFault
        from aquilia.faults.core import FaultDomain
        assert MailFault.domain == FaultDomain.MAIL
        assert MailFault.domain.name == "mail"


# ═══════════════════════════════════════════════════════════════════
# ATS TEMPLATE STUB
# ═══════════════════════════════════════════════════════════════════

class TestATSTemplateStub:
    """Tests for the ATS template stub."""

    def test_render_string_basic(self):
        from aquilia.mail.template import render_string
        result = render_string("Hello, << name >>!", {"name": "World"})
        assert result == "Hello, World!"

    def test_render_string_dotted(self):
        from aquilia.mail.template import render_string
        result = render_string(
            "Hi << user.name >>!",
            {"user": {"name": "Asha"}},
        )
        assert result == "Hi Asha!"

    def test_render_string_missing_key(self):
        from aquilia.mail.template import render_string
        result = render_string("Hi << missing >>!", {})
        assert result == "Hi !"

    def test_render_string_multiple_expressions(self):
        from aquilia.mail.template import render_string
        result = render_string(
            "<< greeting >>, << name >>! Your code is << code >>.",
            {"greeting": "Hello", "name": "Dev", "code": "42"},
        )
        assert result == "Hello, Dev! Your code is 42."

    def test_render_string_with_filter_stub(self):
        from aquilia.mail.template import render_string
        # Filters are ignored in stub — just the expression part is used
        result = render_string("Hi << name | title >>!", {"name": "asha"})
        assert result == "Hi asha!"  # filter ignored in stub

    def test_render_string_no_expressions(self):
        from aquilia.mail.template import render_string
        result = render_string("No expressions here", {})
        assert result == "No expressions here"

    def test_render_template_from_file(self, tmp_path):
        from aquilia.mail.template import render_template
        tpl = tmp_path / "greet.aqt"
        tpl.write_text("<p>Hello << name >>!</p>")
        result = render_template(
            str(tpl),
            {"name": "World"},
        )
        assert result == "<p>Hello World!</p>"

    def test_render_template_with_dirs(self, tmp_path):
        from aquilia.mail.template import render_template
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "welcome.aqt").write_text("Welcome << user >>!")
        result = render_template(
            "welcome.aqt",
            {"user": "Asha"},
            template_dirs=[str(tpl_dir)],
        )
        assert result == "Welcome Asha!"

    def test_render_template_not_found(self):
        from aquilia.mail.template import render_template
        from aquilia.mail.faults import MailTemplateFault
        with pytest.raises(MailTemplateFault, match="not found"):
            render_template("nonexistent.aqt", {})

    def test_configure_dirs(self, tmp_path):
        from aquilia.mail.template import configure, render_template, _template_dirs
        tpl_dir = tmp_path / "my_templates"
        tpl_dir.mkdir()
        (tpl_dir / "test.aqt").write_text("Value: << x >>")

        old_dirs = list(_template_dirs)
        try:
            configure(template_dirs=[str(tpl_dir)])
            result = render_template("test.aqt", {"x": "42"})
            assert result == "Value: 42"
        finally:
            configure(template_dirs=[str(d) for d in old_dirs])


# ═══════════════════════════════════════════════════════════════════
# SERVICE — Singleton & Pipeline
# ═══════════════════════════════════════════════════════════════════

class TestMailServiceAccessor:
    """Tests for the module-level service accessor."""

    def test_get_mail_service_not_initialized(self):
        from aquilia.mail.service import _get_mail_service, set_mail_service
        import aquilia.mail.service as svc_mod
        # Temporarily clear the singleton
        original = svc_mod._mail_service
        svc_mod._mail_service = None
        try:
            from aquilia.mail.faults import MailConfigFault
            with pytest.raises(MailConfigFault, match="not initialised"):
                _get_mail_service()
        finally:
            svc_mod._mail_service = original

    def test_set_and_get_mail_service(self):
        from aquilia.mail.service import _get_mail_service, set_mail_service, MailService
        import aquilia.mail.service as svc_mod
        original = svc_mod._mail_service
        try:
            svc = MailService()
            set_mail_service(svc)
            assert _get_mail_service() is svc
        finally:
            svc_mod._mail_service = original


class TestMailService:
    """Tests for MailService."""

    def test_create_default(self):
        from aquilia.mail.service import MailService
        svc = MailService()
        assert svc.config is not None
        assert svc._started is False
        assert svc._providers == {}

    def test_create_with_config(self):
        from aquilia.mail.service import MailService
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        svc = MailService(config=config)
        assert svc.config.console_backend is True

    @pytest.mark.asyncio
    async def test_startup_with_console_provider(self):
        from aquilia.mail.service import MailService
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        svc = MailService(config=config)
        await svc.on_startup()
        assert svc._started is True
        assert "console" in svc._providers
        assert svc.is_healthy() is True
        await svc.on_shutdown()
        assert svc._started is False

    @pytest.mark.asyncio
    async def test_shutdown_clears_providers(self):
        from aquilia.mail.service import MailService
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        svc = MailService(config=config)
        await svc.on_startup()
        assert len(svc._providers) > 0
        await svc.on_shutdown()
        assert len(svc._providers) == 0
        assert svc.is_healthy() is False

    def test_get_provider_names_empty(self):
        from aquilia.mail.service import MailService
        svc = MailService()
        assert svc.get_provider_names() == []

    @pytest.mark.asyncio
    async def test_get_provider_names_after_startup(self):
        from aquilia.mail.service import MailService
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        svc = MailService(config=config)
        await svc.on_startup()
        names = svc.get_provider_names()
        assert "console" in names
        await svc.on_shutdown()

    @pytest.mark.asyncio
    async def test_double_startup_idempotent(self):
        from aquilia.mail.service import MailService
        from aquilia.mail.config import MailConfig
        config = MailConfig.development()
        svc = MailService(config=config)
        await svc.on_startup()
        await svc.on_startup()  # Should not fail
        assert svc._started is True
        await svc.on_shutdown()

    @pytest.mark.asyncio
    async def test_double_shutdown_idempotent(self):
        from aquilia.mail.service import MailService
        svc = MailService()
        await svc.on_shutdown()  # Should not fail
        await svc.on_shutdown()
        assert svc._started is False


# ═══════════════════════════════════════════════════════════════════
# CONSOLE PROVIDER
# ═══════════════════════════════════════════════════════════════════

class TestConsoleProvider:
    """Tests for ConsoleProvider."""

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self):
        from aquilia.mail.providers.console import ConsoleProvider
        cp = ConsoleProvider()
        await cp.initialize()
        await cp.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self):
        from aquilia.mail.providers.console import ConsoleProvider
        cp = ConsoleProvider()
        assert await cp.health_check() is True

    @pytest.mark.asyncio
    async def test_send_returns_success(self, capsys):
        from aquilia.mail.providers.console import ConsoleProvider
        from aquilia.mail.envelope import MailEnvelope
        cp = ConsoleProvider()
        env = MailEnvelope(
            from_email="sender@test.com",
            to=["user@test.com"],
            subject="Test",
            body_text="Hello world",
        )
        result = await cp.send(env)
        assert result.is_success is True
        assert result.provider_message_id is not None
        assert result.provider_message_id.startswith("console-")
        # Check console output
        captured = capsys.readouterr()
        assert "sender@test.com" in captured.out
        assert "user@test.com" in captured.out
        assert "Test" in captured.out
        assert "Hello world" in captured.out

    @pytest.mark.asyncio
    async def test_send_with_html(self, capsys):
        from aquilia.mail.providers.console import ConsoleProvider
        from aquilia.mail.envelope import MailEnvelope
        cp = ConsoleProvider()
        env = MailEnvelope(
            from_email="sender@test.com",
            to=["user@test.com"],
            subject="HTML Test",
            body_text="Plain",
            body_html="<h1>Rich</h1>",
        )
        result = await cp.send(env)
        assert result.is_success
        captured = capsys.readouterr()
        assert "<h1>Rich</h1>" in captured.out

    @pytest.mark.asyncio
    async def test_send_batch(self):
        from aquilia.mail.providers.console import ConsoleProvider
        from aquilia.mail.envelope import MailEnvelope
        cp = ConsoleProvider()
        envs = [
            MailEnvelope(to=["a@test.com"], subject=f"Msg {i}")
            for i in range(3)
        ]
        results = await cp.send_batch(envs)
        assert len(results) == 3
        assert all(r.is_success for r in results)


# ═══════════════════════════════════════════════════════════════════
# END-TO-END: Send via MailService with Console Provider
# ═══════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """End-to-end test: EmailMessage → MailService → ConsoleProvider."""

    @pytest.mark.asyncio
    async def test_e2e_send_message(self, capsys):
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.mail.config import MailConfig
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.envelope import EnvelopeStatus
        import aquilia.mail.service as svc_mod

        original = svc_mod._mail_service
        try:
            config = MailConfig.development()
            svc = MailService(config=config)
            await svc.on_startup()
            set_mail_service(svc)

            msg = EmailMessage(
                subject="E2E Test",
                body="Hello from the pipeline!",
                from_email="dev@localhost",
                to=["recipient@test.com"],
            )
            envelope_id = await msg.asend()

            assert envelope_id is not None
            assert isinstance(envelope_id, str)

            # Preview mode is on → should log but say "PREVIEW"
            captured = capsys.readouterr()
            # In preview mode, the console doesn't print the full email
            # but it should still return an envelope_id

            await svc.on_shutdown()
        finally:
            svc_mod._mail_service = original

    @pytest.mark.asyncio
    async def test_e2e_non_preview_console_send(self, capsys):
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.mail.config import MailConfig
        from aquilia.mail.message import EmailMessage
        import aquilia.mail.service as svc_mod

        original = svc_mod._mail_service
        try:
            config = MailConfig(
                console_backend=True,
                preview_mode=False,  # Actually dispatch to console
                default_from="sender@app.com",
            )
            svc = MailService(config=config)
            await svc.on_startup()
            set_mail_service(svc)

            msg = EmailMessage(
                subject="Real Console",
                body="This should print!",
                to=["user@test.com"],
            )
            envelope_id = await msg.asend()
            assert envelope_id is not None

            captured = capsys.readouterr()
            assert "user@test.com" in captured.out
            assert "This should print!" in captured.out

            await svc.on_shutdown()
        finally:
            svc_mod._mail_service = original

    @pytest.mark.asyncio
    async def test_e2e_multi_alternatives(self, capsys):
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.mail.config import MailConfig
        from aquilia.mail.message import EmailMultiAlternatives
        import aquilia.mail.service as svc_mod

        original = svc_mod._mail_service
        try:
            config = MailConfig(console_backend=True, preview_mode=False)
            svc = MailService(config=config)
            await svc.on_startup()
            set_mail_service(svc)

            msg = EmailMultiAlternatives(
                subject="Newsletter",
                body="Plain text version",
                to=["sub@test.com"],
            )
            msg.attach_alternative("<h1>Rich HTML</h1>", "text/html")
            envelope_id = await msg.asend()
            assert envelope_id is not None

            captured = capsys.readouterr()
            assert "Rich HTML" in captured.out

            await svc.on_shutdown()
        finally:
            svc_mod._mail_service = original


# ═══════════════════════════════════════════════════════════════════
# TOP-LEVEL IMPORTS
# ═══════════════════════════════════════════════════════════════════

class TestTopLevelImports:
    """Verify that `import aquilia.mail` exposes the full public API."""

    def test_all_exports(self):
        import aquilia.mail
        expected = [
            "EmailMessage", "EmailMultiAlternatives", "TemplateMessage",
            "send_mail", "asend_mail",
            "MailEnvelope", "EnvelopeStatus", "Priority",
            "MailConfig",
            "IMailProvider", "ProviderResult", "ProviderResultStatus",
            "MailFault", "MailSendFault", "MailTemplateFault",
            "MailConfigFault", "MailSuppressedFault", "MailRateLimitFault",
            "MailValidationFault",
        ]
        for name in expected:
            assert hasattr(aquilia.mail, name), f"Missing export: {name}"
            assert name in aquilia.mail.__all__

    def test_version(self):
        import aquilia.mail
        assert aquilia.mail.__version__ == "1.0.0"
