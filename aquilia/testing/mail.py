"""
Aquilia Testing - Mail Testing Utilities.

Provides :class:`MailTestMixin` with a captured outbox and
:class:`CapturedMail` for rich assertions on sent messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapturedMail:
    """A mail message captured during testing."""
    to: List[str]
    subject: str
    body: str = ""
    html_body: str = ""
    from_email: str = ""
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    provider: str = ""
    template_name: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"<CapturedMail to={self.to} "
            f"subject={self.subject!r}>"
        )


# Module-level outbox for capturing sent mail
_mail_outbox: List[CapturedMail] = []


def get_outbox() -> List[CapturedMail]:
    """Return the global mail outbox."""
    return _mail_outbox


def clear_outbox() -> None:
    """Clear the global mail outbox."""
    _mail_outbox.clear()


def capture_mail(
    to: List[str],
    subject: str,
    body: str = "",
    **kwargs: Any,
) -> CapturedMail:
    """Add a message to the outbox (called by the test mail provider)."""
    msg = CapturedMail(to=to, subject=subject, body=body, **kwargs)
    _mail_outbox.append(msg)
    return msg


class MailTestMixin:
    """
    Mixin providing mail assertion helpers.

    Captures all outgoing mail in a test outbox instead of sending
    it through a real provider.

    Usage::

        class TestNotifications(AquiliaTestCase, MailTestMixin):
            enable_mail = True

            async def test_welcome_email(self):
                await self.client.post("/register", json={...})
                self.assert_mail_sent(to="alice@example.com")
                self.assert_mail_subject_contains("Welcome")
    """

    def setUp(self) -> None:
        super().setUp() if hasattr(super(), "setUp") else None
        clear_outbox()

    @property
    def mail_outbox(self) -> List[CapturedMail]:
        """All captured mail messages."""
        return get_outbox()

    @property
    def latest_mail(self) -> Optional[CapturedMail]:
        """Return the most recently sent mail, or None."""
        outbox = self.mail_outbox
        return outbox[-1] if outbox else None

    def get_mail_for(self, address: str) -> List[CapturedMail]:
        """Return all mail sent to a specific address."""
        return [m for m in self.mail_outbox if address in m.to]

    def assert_mail_sent(
        self,
        to: Optional[str] = None,
        count: Optional[int] = None,
        msg: str = "",
    ):
        """Assert that mail was sent."""
        outbox = self.mail_outbox
        if to is not None:
            matching = [m for m in outbox if to in m.to]
            assert matching, (
                f"No mail sent to {to!r}. "
                f"Outbox ({len(outbox)} messages): "
                f"{[m.to for m in outbox]}. {msg}"
            )
        elif count is not None:
            assert len(outbox) == count, (
                f"Expected {count} messages, got {len(outbox)}. {msg}"
            )
        else:
            assert outbox, f"No mail was sent. {msg}"

    def assert_no_mail_sent(self, msg: str = ""):
        """Assert that no mail was sent."""
        assert not self.mail_outbox, (
            f"Expected no mail, got {len(self.mail_outbox)}: "
            f"{[m.subject for m in self.mail_outbox]}. {msg}"
        )

    def assert_mail_count(self, expected: int, msg: str = ""):
        """Assert exact number of messages in the outbox."""
        actual = len(self.mail_outbox)
        assert actual == expected, (
            f"Expected {expected} mail messages, got {actual}. {msg}"
        )

    def assert_mail_to(self, address: str, msg: str = ""):
        """Assert at least one message was sent to *address*."""
        matching = self.get_mail_for(address)
        assert matching, (
            f"No mail sent to {address!r}. "
            f"Recipients: {[m.to for m in self.mail_outbox]}. {msg}"
        )

    def assert_mail_from(self, address: str, msg: str = ""):
        """Assert at least one message was sent from *address*."""
        matching = [m for m in self.mail_outbox if m.from_email == address]
        assert matching, (
            f"No mail from {address!r}. "
            f"Senders: {[m.from_email for m in self.mail_outbox]}. {msg}"
        )

    def assert_mail_subject_contains(self, text: str, msg: str = ""):
        """Assert at least one message has a subject containing *text*."""
        matching = [m for m in self.mail_outbox if text in m.subject]
        assert matching, (
            f"No mail with subject containing {text!r}. "
            f"Subjects: {[m.subject for m in self.mail_outbox]}. {msg}"
        )

    def assert_mail_body_contains(self, text: str, msg: str = ""):
        """Assert at least one message has body containing *text*."""
        matching = [m for m in self.mail_outbox if text in m.body or text in m.html_body]
        assert matching, (
            f"No mail with body containing {text!r}. {msg}"
        )

    def assert_mail_has_attachment(self, filename: Optional[str] = None, msg: str = ""):
        """Assert at least one message has an attachment."""
        for m in self.mail_outbox:
            if m.attachments:
                if filename is None:
                    return
                for att in m.attachments:
                    if att.get("filename") == filename or att.get("name") == filename:
                        return
        if filename:
            raise AssertionError(f"No mail with attachment {filename!r}. {msg}")
        raise AssertionError(f"No mail with attachments. {msg}")

    def assert_mail_cc(self, address: str, msg: str = ""):
        """Assert at least one message has *address* in CC."""
        matching = [m for m in self.mail_outbox if address in m.cc]
        assert matching, (
            f"No mail with CC {address!r}. {msg}"
        )

    def assert_mail_bcc(self, address: str, msg: str = ""):
        """Assert at least one message has *address* in BCC."""
        matching = [m for m in self.mail_outbox if address in m.bcc]
        assert matching, (
            f"No mail with BCC {address!r}. {msg}"
        )
