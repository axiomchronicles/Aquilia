"""
AquilaMail Messages — Developer-facing message classes.

Django-like API:
    EmailMessage          — plain text (optionally with HTML)
    EmailMultiAlternatives — plain text + HTML + arbitrary MIME alternatives
    TemplateMessage       — rendered from an ATS template

All classes support both sync (.send()) and async (.asend()) delivery.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .envelope import Attachment, MailEnvelope, EnvelopeStatus, Priority
from .faults import MailValidationFault

# Basic email regex for fast validation (not RFC-complete but practical)
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$"
)


def _validate_email(addr: str, field_name: str = "email") -> str:
    """Validate and normalise a single email address."""
    addr = addr.strip()
    if not addr:
        raise MailValidationFault(f"Empty {field_name} address", field=field_name)
    # Handle "Display Name <addr>" format
    if "<" in addr and addr.endswith(">"):
        display, raw = addr.rsplit("<", 1)
        raw = raw.rstrip(">").strip()
    else:
        raw = addr
    if not _EMAIL_RE.match(raw):
        raise MailValidationFault(
            f"Invalid {field_name} address: {addr!r}", field=field_name
        )
    return addr


def _validate_list(
    addrs: Optional[Sequence[str]], field_name: str
) -> List[str]:
    """Validate a list of email addresses."""
    if not addrs:
        return []
    return [_validate_email(a, field_name) for a in addrs]


class EmailMessage:
    """
    A single email message — the primary API for sending mail.

    Mirrors Django's EmailMessage but integrated with Aquilia's
    envelope pipeline, DI, and fault system.

    Usage:
        msg = EmailMessage(
            subject="Hello",
            body="World",
            to=["user@example.com"],
        )
        msg.send()            # sync
        await msg.asend()     # async

        # With attachments
        msg.attach("report.pdf", pdf_bytes, "application/pdf")
        msg.attach_file("/tmp/invoice.pdf")
    """

    def __init__(
        self,
        subject: str = "",
        body: str = "",
        from_email: Optional[str] = None,
        to: Optional[Sequence[str]] = None,
        cc: Optional[Sequence[str]] = None,
        bcc: Optional[Sequence[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        priority: int = Priority.NORMAL.value,
        idempotency_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.subject = subject
        self.body = body
        self.from_email = from_email  # None → uses MailConfig.default_from
        self.to = _validate_list(to, "to")
        self.cc = _validate_list(cc, "cc")
        self.bcc = _validate_list(bcc, "bcc")
        self.reply_to = reply_to
        self.extra_headers = headers or {}
        self.priority = priority
        self.idempotency_key = idempotency_key
        self.tenant_id = tenant_id
        self.metadata = metadata or {}

        # Attachment buffer: list of (filename, content_bytes, content_type)
        self._attachments: List[Tuple[str, bytes, str]] = list(attachments or [])
        self._alternatives: List[Tuple[str, str]] = []  # (content, mimetype)

    # ── Attachment API ──────────────────────────────────────────────

    def attach(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> "EmailMessage":
        """Attach raw bytes."""
        self._attachments.append((filename, content, content_type))
        return self

    def attach_file(
        self,
        path: Union[str, Path],
        content_type: Optional[str] = None,
    ) -> "EmailMessage":
        """Attach a file from disk."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Attachment not found: {p}")
        if content_type is None:
            import mimetypes
            content_type, _ = mimetypes.guess_type(str(p))
            content_type = content_type or "application/octet-stream"
        self._attachments.append((p.name, p.read_bytes(), content_type))
        return self

    # ── Envelope builder ────────────────────────────────────────────

    def _build_attachment_records(self) -> Tuple[List[Attachment], Dict[str, bytes]]:
        """
        Build Attachment records and a digest→bytes map for blob storage.

        Returns:
            (attachment_records, blobs_to_store)
        """
        records: list[Attachment] = []
        blobs: dict[str, bytes] = {}
        for filename, content, ct in self._attachments:
            digest = hashlib.sha256(content).hexdigest()
            records.append(
                Attachment(
                    filename=filename,
                    content_type=ct,
                    digest=digest,
                    size=len(content),
                )
            )
            blobs[digest] = content
        return records, blobs

    def build_envelope(
        self,
        default_from: str = "noreply@localhost",
    ) -> Tuple[MailEnvelope, Dict[str, bytes]]:
        """
        Build a MailEnvelope + blob map ready for storage and dispatch.

        Args:
            default_from: Fallback from address if self.from_email is None.

        Returns:
            (envelope, attachment_blobs)
        """
        if not self.to and not self.cc and not self.bcc:
            raise MailValidationFault(
                "At least one recipient (to, cc, or bcc) is required",
                field="to",
            )

        att_records, blobs = self._build_attachment_records()

        body_html: Optional[str] = None
        if self._alternatives:
            for content, mimetype in self._alternatives:
                if mimetype == "text/html":
                    body_html = content
                    break

        envelope = MailEnvelope(
            from_email=self.from_email or default_from,
            to=list(self.to),
            cc=list(self.cc),
            bcc=list(self.bcc),
            reply_to=self.reply_to,
            subject=self.subject,
            body_text=self.body,
            body_html=body_html,
            headers=dict(self.extra_headers),
            attachments=att_records,
            priority=self.priority,
            idempotency_key=self.idempotency_key,
            tenant_id=self.tenant_id,
            metadata=self.metadata,
        )
        envelope.compute_digest()
        return envelope, blobs

    # ── Send API ────────────────────────────────────────────────────

    def send(self, fail_silently: bool = False) -> Optional[str]:
        """
        Send synchronously.

        Returns:
            envelope_id on success, None if fail_silently and error.
        """
        from .service import _get_mail_service

        svc = _get_mail_service()
        try:
            return asyncio.get_event_loop().run_until_complete(
                svc.send_message(self)
            )
        except Exception:
            if fail_silently:
                return None
            raise

    async def asend(self, fail_silently: bool = False) -> Optional[str]:
        """
        Send asynchronously.

        Returns:
            envelope_id on success.
        """
        from .service import _get_mail_service

        svc = _get_mail_service()
        try:
            return await svc.send_message(self)
        except Exception:
            if fail_silently:
                return None
            raise

    def __repr__(self) -> str:
        return (
            f"EmailMessage(subject={self.subject!r}, "
            f"to={self.to!r})"
        )


class EmailMultiAlternatives(EmailMessage):
    """
    Email with multiple content alternatives (e.g., plain text + HTML).

    Usage:
        msg = EmailMultiAlternatives(
            subject="Newsletter",
            body="Plain text fallback",
            to=["subscriber@example.com"],
        )
        msg.attach_alternative("<h1>HTML version</h1>", "text/html")
        await msg.asend()
    """

    def attach_alternative(
        self, content: str, mimetype: str = "text/html"
    ) -> "EmailMultiAlternatives":
        """Add an alternative content representation."""
        self._alternatives.append((content, mimetype))
        return self


class TemplateMessage(EmailMessage):
    """
    Email rendered from an Aquilia Template Syntax (ATS) template.

    The template is rendered at build_envelope() time.  The rendered HTML
    becomes the body_html and an auto-generated plain text becomes body_text.

    Usage:
        msg = TemplateMessage(
            template="welcome.aqt",
            context={"user": {"name": "Asha"}},
            to=["asha@example.com"],
            subject="Welcome, << user.name >>!",
        )
        await msg.asend()
    """

    def __init__(
        self,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        subject: str = "",
        from_email: Optional[str] = None,
        to: Optional[Sequence[str]] = None,
        cc: Optional[Sequence[str]] = None,
        bcc: Optional[Sequence[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        priority: int = Priority.NORMAL.value,
        idempotency_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            subject=subject,
            body="",  # populated after render
            from_email=from_email,
            to=to,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            headers=headers,
            attachments=attachments,
            priority=priority,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
            metadata=metadata,
        )
        self.template_name = template
        self.template_context = context or {}

    def build_envelope(
        self, default_from: str = "noreply@localhost"
    ) -> Tuple[MailEnvelope, Dict[str, bytes]]:
        """Build envelope, rendering the template first."""
        from .template import render_template

        # Render the ATS template
        rendered_html = render_template(
            self.template_name, self.template_context
        )

        # Auto-generate plain text from HTML (basic strip)
        rendered_text = _html_to_text(rendered_html)

        # Subject may contain ATS expressions — render inline
        if "<<" in self.subject:
            from .template import render_string
            self.subject = render_string(self.subject, self.template_context)

        self.body = rendered_text
        self._alternatives.append((rendered_html, "text/html"))

        envelope, blobs = super().build_envelope(default_from)
        envelope.template_name = self.template_name
        envelope.template_context = self.template_context
        return envelope, blobs

    def __repr__(self) -> str:
        return (
            f"TemplateMessage(template={self.template_name!r}, "
            f"to={self.to!r})"
        )


# ── Helpers ─────────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_WS_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    """Basic HTML → plain text conversion for multipart fallback."""
    text = html
    # Convert <br> to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Convert </p>, </div>, </tr> to double newlines
    text = re.sub(r"</(p|div|tr|li|h[1-6])>", "\n\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = _TAG_RE.sub("", text)
    # Collapse whitespace
    lines = []
    for line in text.split("\n"):
        stripped = _MULTI_WS_RE.sub(" ", line).strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)
