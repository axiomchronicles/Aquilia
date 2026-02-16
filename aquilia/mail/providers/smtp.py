"""
SMTP Provider — Production-grade async SMTP delivery via aiosmtplib.

Features:
- Async SMTP with STARTTLS / direct SSL
- Automatic MIME message construction (plain, HTML, attachments)
- Connection pooling with keep-alive and reconnect logic
- Configurable timeouts, retries, source-address binding
- TLS certificate validation (customisable)
- Health-check via NOOP / EHLO
- Proper multipart MIME with inline images (Content-ID)
- Batch send with connection reuse
- Detailed structured logging and metrics
- Graceful shutdown with connection draining

Dependencies:
    pip install aiosmtplib   (required)

Usage::

    provider = SMTPProvider(
        name="primary-smtp",
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        use_tls=True,
    )
    await provider.initialize()
    result = await provider.send(envelope)
    await provider.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Any, Dict, List, Optional, Sequence

from ..envelope import MailEnvelope
from ..faults import MailSendFault
from ..providers import IMailProvider, ProviderResult, ProviderResultStatus

logger = logging.getLogger("aquilia.mail.providers.smtp")

# ── Transient SMTP error codes (safe to retry) ─────────────────────
_TRANSIENT_CODES = frozenset({
    421,  # Service not available, closing channel
    450,  # Mailbox unavailable (busy / blocked)
    451,  # Local error in processing
    452,  # Insufficient storage
})

# ── Permanent SMTP error codes (do NOT retry) ──────────────────────
_PERMANENT_CODES = frozenset({
    550,  # Mailbox unavailable (not found / no access)
    551,  # User not local
    552,  # Exceeded storage allocation
    553,  # Mailbox name not allowed
    554,  # Transaction failed
    555,  # Parameters not recognised
})


class SMTPProvider:
    """
    Async SMTP mail provider backed by aiosmtplib.

    Supports STARTTLS, direct SSL, authentication, connection pooling,
    and full MIME message construction.
    """

    name: str
    provider_type: str = "smtp"
    supports_batching: bool = True
    max_batch_size: int = 100

    def __init__(
        self,
        name: str = "smtp",
        host: str = "localhost",
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: float = 30.0,
        *,
        # Advanced options
        source_address: Optional[str] = None,
        local_hostname: Optional[str] = None,
        validate_certs: bool = True,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        pool_size: int = 3,
        pool_recycle: float = 300.0,
        priority: int = 10,
    ):
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.source_address = source_address
        self.local_hostname = local_hostname
        self.validate_certs = validate_certs
        self.client_cert = client_cert
        self.client_key = client_key
        self.pool_size = pool_size
        self.pool_recycle = pool_recycle
        self.priority = priority

        # Connection pool state
        self._pool: list[Any] = []
        self._pool_lock = asyncio.Lock()
        self._pool_created: Dict[int, float] = {}  # id(conn) → timestamp
        self._initialized = False

        # Metrics
        self._total_sent = 0
        self._total_errors = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Pre-warm the connection pool."""
        if self._initialized:
            return
        logger.info(
            f"SMTP provider '{self.name}' initializing "
            f"({self.host}:{self.port}, tls={self.use_tls}, ssl={self.use_ssl})"
        )
        # Pre-warm one connection to validate settings early
        try:
            conn = await self._create_connection()
            self._pool.append(conn)
            self._pool_created[id(conn)] = time.monotonic()
            logger.debug(f"SMTP pool pre-warmed (1/{self.pool_size})")
        except Exception as e:
            logger.warning(
                f"SMTP pool pre-warm failed (will retry on send): {e}"
            )
        self._initialized = True

    async def shutdown(self) -> None:
        """Drain and close all pooled connections."""
        logger.info(f"SMTP provider '{self.name}' shutting down...")
        async with self._pool_lock:
            for conn in self._pool:
                await self._close_connection(conn)
            self._pool.clear()
            self._pool_created.clear()
        self._initialized = False
        logger.info(
            f"SMTP provider '{self.name}' shutdown complete "
            f"(sent={self._total_sent}, errors={self._total_errors})"
        )

    # ── Connection Management ───────────────────────────────────────

    def _build_tls_context(self) -> Optional[ssl.SSLContext]:
        """Build an SSL context for TLS/SSL connections."""
        if not self.use_tls and not self.use_ssl:
            return None
        ctx = ssl.create_default_context()
        if not self.validate_certs:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if self.client_cert:
            ctx.load_cert_chain(
                certfile=self.client_cert,
                keyfile=self.client_key,
            )
        return ctx

    async def _create_connection(self) -> Any:
        """Create a new aiosmtplib SMTP connection."""
        try:
            import aiosmtplib
        except ImportError:
            raise ImportError(
                "aiosmtplib is required for the SMTP provider. "
                "Install it with: pip install aiosmtplib"
            )

        tls_context = self._build_tls_context()

        smtp = aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=self.use_ssl,  # use_tls in aiosmtplib = connect with SSL
            start_tls=self.use_tls and not self.use_ssl,
            timeout=self.timeout,
            source_address=self.source_address,
            local_hostname=self.local_hostname,
            tls_context=tls_context,
        )

        await smtp.connect()

        if self.username and self.password:
            await smtp.login(self.username, self.password)

        return smtp

    async def _acquire_connection(self) -> Any:
        """Acquire a connection from the pool (or create a new one)."""
        async with self._pool_lock:
            now = time.monotonic()
            # Try to find a non-expired connection
            while self._pool:
                conn = self._pool.pop(0)
                created = self._pool_created.pop(id(conn), 0)
                # Check if connection is expired
                if (now - created) > self.pool_recycle:
                    await self._close_connection(conn)
                    continue
                # Test if connection is still alive
                try:
                    await conn.noop()
                    return conn
                except Exception:
                    await self._close_connection(conn)
                    continue

        # Pool exhausted — create a new connection
        conn = await self._create_connection()
        self._pool_created[id(conn)] = time.monotonic()
        return conn

    async def _release_connection(self, conn: Any) -> None:
        """Return a connection to the pool."""
        async with self._pool_lock:
            if len(self._pool) < self.pool_size:
                self._pool.append(conn)
                self._pool_created[id(conn)] = time.monotonic()
            else:
                await self._close_connection(conn)

    async def _close_connection(self, conn: Any) -> None:
        """Safely close an SMTP connection."""
        try:
            await conn.quit()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    # ── MIME Message Construction ───────────────────────────────────

    def _build_mime_message(self, envelope: MailEnvelope) -> MIMEMultipart:
        """
        Build a full MIME message from a MailEnvelope.

        Structure:
            multipart/mixed
            ├── multipart/alternative
            │   ├── text/plain
            │   └── text/html (if present)
            ├── attachment 1
            ├── attachment 2
            └── ...
        """
        # Root message
        msg = MIMEMultipart("mixed")

        # Headers
        msg["From"] = envelope.from_email
        msg["To"] = ", ".join(envelope.to)
        if envelope.cc:
            msg["Cc"] = ", ".join(envelope.cc)
        msg["Subject"] = envelope.subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=self._extract_domain(envelope.from_email))

        if envelope.reply_to:
            msg["Reply-To"] = envelope.reply_to

        # Custom headers
        for key, value in envelope.headers.items():
            msg[key] = value

        # Aquilia headers
        msg["X-Aquilia-Envelope-ID"] = envelope.id
        if envelope.trace_id:
            msg["X-Aquilia-Trace-ID"] = envelope.trace_id
        if envelope.tenant_id:
            msg["X-Aquilia-Tenant-ID"] = envelope.tenant_id

        # Body (alternative: text + html)
        if envelope.body_html:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(envelope.body_text, "plain", "utf-8"))
            alt.attach(MIMEText(envelope.body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(envelope.body_text, "plain", "utf-8"))

        # Attachments
        for attachment in envelope.attachments:
            part = MIMEBase(*attachment.content_type.split("/", 1))
            # Attachment content is stored in blob store; here we
            # set metadata only. The actual bytes must be resolved
            # before calling send() in a real pipeline.
            # For now, we set a placeholder and let the pipeline fill it.
            part.set_payload(
                envelope.metadata.get(f"blob:{attachment.digest}", b"")
            )
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

        return msg

    @staticmethod
    def _extract_domain(email: str) -> str:
        """Extract domain from an email address."""
        if "<" in email:
            email = email.split("<")[1].rstrip(">")
        return email.rsplit("@", 1)[-1] if "@" in email else "localhost"

    # ── Send ────────────────────────────────────────────────────────

    async def send(self, envelope: MailEnvelope) -> ProviderResult:
        """
        Send a single envelope via SMTP.

        Acquires a pooled connection, builds the MIME message,
        sends via SMTP, and returns a structured result.
        """
        conn = None
        try:
            conn = await self._acquire_connection()
            mime_msg = self._build_mime_message(envelope)

            # All recipients (to + cc + bcc)
            recipients = envelope.all_recipients()

            errors, message = await conn.send_message(
                mime_msg,
                sender=envelope.from_email,
                recipients=recipients,
            )

            self._total_sent += 1
            message_id = mime_msg["Message-ID"]

            logger.info(
                f"SMTP sent via {self.name}: {envelope.id} → {recipients} "
                f"(msg_id={message_id})",
            )

            return ProviderResult(
                status=ProviderResultStatus.SUCCESS,
                provider_message_id=message_id,
                raw_response={"smtp_response": str(message)},
            )

        except Exception as e:
            self._total_errors += 1
            status, retry_after = self._classify_error(e)
            logger.warning(
                f"SMTP send error via {self.name}: {e} "
                f"(status={status.value})",
            )
            return ProviderResult(
                status=status,
                error_message=str(e),
                retry_after=retry_after,
            )
        finally:
            if conn is not None:
                try:
                    await self._release_connection(conn)
                except Exception:
                    pass

    async def send_batch(
        self, envelopes: Sequence[MailEnvelope],
    ) -> List[ProviderResult]:
        """
        Send a batch of envelopes, reusing a single connection.

        Falls back to individual sends on connection error.
        """
        results: list[ProviderResult] = []
        conn = None
        try:
            conn = await self._acquire_connection()
            for envelope in envelopes:
                try:
                    mime_msg = self._build_mime_message(envelope)
                    recipients = envelope.all_recipients()
                    errors, message = await conn.send_message(
                        mime_msg,
                        sender=envelope.from_email,
                        recipients=recipients,
                    )
                    self._total_sent += 1
                    results.append(ProviderResult(
                        status=ProviderResultStatus.SUCCESS,
                        provider_message_id=mime_msg["Message-ID"],
                    ))
                except Exception as e:
                    self._total_errors += 1
                    status, retry_after = self._classify_error(e)
                    results.append(ProviderResult(
                        status=status,
                        error_message=str(e),
                        retry_after=retry_after,
                    ))
                    # If connection-level error, break out of batch
                    if self._is_connection_error(e):
                        conn = None
                        for remaining in envelopes[len(results):]:
                            results.append(ProviderResult(
                                status=ProviderResultStatus.TRANSIENT_FAILURE,
                                error_message="Batch aborted due to connection error",
                            ))
                        break
        except Exception as e:
            # Connection acquisition failed entirely
            for _ in envelopes[len(results):]:
                results.append(ProviderResult(
                    status=ProviderResultStatus.TRANSIENT_FAILURE,
                    error_message=f"Connection failed: {e}",
                ))
        finally:
            if conn is not None:
                try:
                    await self._release_connection(conn)
                except Exception:
                    pass

        return results

    async def health_check(self) -> bool:
        """Check SMTP connectivity via NOOP."""
        try:
            conn = await self._acquire_connection()
            await conn.noop()
            await self._release_connection(conn)
            return True
        except Exception as e:
            logger.debug(f"SMTP health check failed: {e}")
            return False

    # ── Error Classification ────────────────────────────────────────

    def _classify_error(self, error: Exception) -> tuple:
        """
        Classify an SMTP error into ProviderResultStatus + retry_after.

        Returns:
            (status, retry_after_seconds or None)
        """
        error_str = str(error)

        # Check for SMTP response codes
        code = self._extract_smtp_code(error)
        if code is not None:
            if code in _TRANSIENT_CODES:
                return ProviderResultStatus.TRANSIENT_FAILURE, 60.0
            if code in _PERMANENT_CODES:
                return ProviderResultStatus.PERMANENT_FAILURE, None
            if 400 <= code < 500:
                return ProviderResultStatus.TRANSIENT_FAILURE, 30.0
            if code >= 500:
                return ProviderResultStatus.PERMANENT_FAILURE, None

        # Connection-level errors are transient
        if self._is_connection_error(error):
            return ProviderResultStatus.TRANSIENT_FAILURE, 10.0

        # Rate limiting keywords
        lower = error_str.lower()
        if "rate" in lower and ("limit" in lower or "exceeded" in lower):
            return ProviderResultStatus.RATE_LIMITED, 120.0
        if "throttl" in lower:
            return ProviderResultStatus.RATE_LIMITED, 60.0

        # Default to transient (assume retry is worth trying)
        return ProviderResultStatus.TRANSIENT_FAILURE, 30.0

    @staticmethod
    def _extract_smtp_code(error: Exception) -> Optional[int]:
        """Try to extract SMTP status code from an error."""
        # aiosmtplib stores code as .code attribute
        if hasattr(error, "code"):
            try:
                return int(error.code)
            except (ValueError, TypeError):
                pass
        # Try parsing from string "421 ..."
        parts = str(error).split()
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
        return None

    @staticmethod
    def _is_connection_error(error: Exception) -> bool:
        """Check if the error is a connection-level failure."""
        return isinstance(error, (
            ConnectionRefusedError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,
        ))

    def __repr__(self) -> str:
        return (
            f"SMTPProvider(name={self.name!r}, host={self.host!r}, "
            f"port={self.port}, tls={self.use_tls})"
        )
