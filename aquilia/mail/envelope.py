"""
AquilaMail Envelope — The internal representation of a mail message.

An envelope is the immutable record of a message as it passes through
the queue, dispatch, and delivery pipeline.  Envelopes are persisted
in the envelope store and carry all metadata needed for retry, dedup,
rate-limiting, and observability.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class EnvelopeStatus(str, Enum):
    """Lifecycle status of an envelope."""

    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"


class Priority(int, Enum):
    """
    Named priority levels.

    Lower numeric value = higher priority (dispatched first).
    """

    CRITICAL = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    BULK = 100


@dataclass
class Attachment:
    """Attachment metadata (content stored separately in blob store)."""

    filename: str
    content_type: str
    digest: str  # SHA-256 of content (content-addressed)
    size: int  # bytes
    inline: bool = False  # True for inline images (Content-ID)
    content_id: Optional[str] = None  # CID for inline

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "digest": self.digest,
            "size": self.size,
            "inline": self.inline,
            "content_id": self.content_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Attachment":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MailEnvelope:
    """
    Immutable mail envelope — the unit of work in the mail pipeline.

    Created by EmailMessage.build_envelope(), persisted by EnvelopeStore,
    dequeued by Dispatcher, and sent by a Provider.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Status
    status: EnvelopeStatus = EnvelopeStatus.QUEUED
    priority: int = Priority.NORMAL.value

    # Addressing
    from_email: str = ""
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None

    # Content
    subject: str = ""
    body_text: str = ""
    body_html: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # Template (if rendered from ATS)
    template_name: Optional[str] = None
    template_context: Optional[Dict[str, Any]] = None

    # Attachments (metadata; blobs stored separately)
    attachments: List[Attachment] = field(default_factory=list)

    # Retry tracking
    attempts: int = 0
    max_attempts: int = 5
    last_attempt_at: Optional[datetime] = None
    next_attempt_at: Optional[datetime] = None

    # Provider affinity
    provider_name: Optional[str] = None
    provider_message_id: Optional[str] = None

    # Idempotency & dedup
    idempotency_key: Optional[str] = None
    digest: str = ""  # computed lazily

    # Multi-tenant
    tenant_id: Optional[str] = None

    # Observability
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Error tracking
    error_message: Optional[str] = None

    def compute_digest(self) -> str:
        """
        Compute content-based SHA-256 digest for deduplication.

        Digest is stable across retries — computed from subject, sorted
        recipients, body hash, and attachment digests.
        """
        body_hash = hashlib.sha256(
            (self.body_text + (self.body_html or "")).encode()
        ).hexdigest()
        att_digests = sorted(a.digest for a in self.attachments)
        canonical = "|".join([
            self.subject,
            "|".join(sorted(self.to)),
            body_hash,
            "|".join(att_digests),
        ])
        self.digest = hashlib.sha256(canonical.encode()).hexdigest()
        return self.digest

    def all_recipients(self) -> List[str]:
        """All unique recipient addresses (to + cc + bcc)."""
        seen: set[str] = set()
        result: list[str] = []
        for addr in [*self.to, *self.cc, *self.bcc]:
            lower = addr.lower().strip()
            if lower not in seen:
                seen.add(lower)
                result.append(addr)
        return result

    def recipient_domains(self) -> set[str]:
        """Unique set of recipient domains."""
        domains: set[str] = set()
        for addr in self.all_recipients():
            if "@" in addr:
                domains.add(addr.rsplit("@", 1)[1].lower())
        return domains

    def to_dict(self) -> dict:
        """Serialize to dictionary (for DB storage / JSON)."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "priority": self.priority,
            "from_email": self.from_email,
            "to": self.to,
            "cc": self.cc,
            "bcc": self.bcc,
            "reply_to": self.reply_to,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "headers": self.headers,
            "template_name": self.template_name,
            "template_context": self.template_context,
            "attachments": [a.to_dict() for a in self.attachments],
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "next_attempt_at": self.next_attempt_at.isoformat() if self.next_attempt_at else None,
            "provider_name": self.provider_name,
            "provider_message_id": self.provider_message_id,
            "idempotency_key": self.idempotency_key,
            "digest": self.digest,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MailEnvelope":
        """Deserialize from dictionary."""
        attachments = [
            Attachment.from_dict(a) if isinstance(a, dict) else a
            for a in data.get("attachments", [])
        ]
        # Parse datetime strings
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        last_attempt_at = data.get("last_attempt_at")
        if isinstance(last_attempt_at, str):
            last_attempt_at = datetime.fromisoformat(last_attempt_at)

        next_attempt_at = data.get("next_attempt_at")
        if isinstance(next_attempt_at, str):
            next_attempt_at = datetime.fromisoformat(next_attempt_at)

        status_raw = data.get("status", "queued")
        status = EnvelopeStatus(status_raw) if isinstance(status_raw, str) else status_raw

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            created_at=created_at,
            status=status,
            priority=data.get("priority", Priority.NORMAL.value),
            from_email=data.get("from_email", ""),
            to=data.get("to", []),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
            reply_to=data.get("reply_to"),
            subject=data.get("subject", ""),
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            headers=data.get("headers", {}),
            template_name=data.get("template_name"),
            template_context=data.get("template_context"),
            attachments=attachments,
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 5),
            last_attempt_at=last_attempt_at,
            next_attempt_at=next_attempt_at,
            provider_name=data.get("provider_name"),
            provider_message_id=data.get("provider_message_id"),
            idempotency_key=data.get("idempotency_key"),
            digest=data.get("digest", ""),
            tenant_id=data.get("tenant_id"),
            trace_id=data.get("trace_id"),
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message"),
        )

    def __repr__(self) -> str:
        to_str = ", ".join(self.to[:3])
        if len(self.to) > 3:
            to_str += f" (+{len(self.to) - 3})"
        return (
            f"MailEnvelope(id={self.id!r}, status={self.status.value}, "
            f"to=[{to_str}], subject={self.subject!r})"
        )
