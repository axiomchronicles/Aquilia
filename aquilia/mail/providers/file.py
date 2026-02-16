"""
File Provider — Writes emails to .eml files on disk.

Useful for local development, CI/CD testing, and audit logging.
Each email is written as a standard RFC 2822 .eml file that can be
opened directly in any mail client (Thunderbird, Outlook, etc.).

Features:
- RFC 2822-compliant .eml output with full MIME structure
- Automatic directory creation with configurable output path
- Structured index file (JSON) for easy test assertions
- Automatic cleanup / rotation by max file count
- Filename includes timestamp + envelope ID for easy sorting
- Thread-safe async file I/O via asyncio
- Health-check validates directory writability

Usage::

    provider = FileProvider(
        name="file",
        output_dir="/tmp/aquilia_mail",
    )
    await provider.initialize()
    result = await provider.send(envelope)
    await provider.shutdown()

    # Files are at:
    #   /tmp/aquilia_mail/2026-02-16T10-30-00_<envelope_id>.eml
    #   /tmp/aquilia_mail/index.jsonl   (one JSON line per email)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..envelope import MailEnvelope
from ..providers import IMailProvider, ProviderResult, ProviderResultStatus

logger = logging.getLogger("aquilia.mail.providers.file")


class FileProvider:
    """
    Mail provider that writes emails to .eml files on disk.

    Ideal for development, testing, and audit trails.
    """

    name: str
    provider_type: str = "file"
    supports_batching: bool = True
    max_batch_size: int = 1000

    def __init__(
        self,
        name: str = "file",
        output_dir: str = "/tmp/aquilia_mail",
        *,
        # Options
        max_files: int = 10000,
        write_index: bool = True,
        include_metadata: bool = True,
        file_extension: str = ".eml",
        priority: int = 90,
    ):
        self.name = name
        self.output_dir = Path(output_dir)
        self.max_files = max_files
        self.write_index = write_index
        self.include_metadata = include_metadata
        self.file_extension = file_extension
        self.priority = priority

        self._initialized = False
        self._write_lock = asyncio.Lock()

        # Metrics
        self._total_sent = 0
        self._total_errors = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create the output directory."""
        if self._initialized:
            return

        logger.info(
            f"File provider '{self.name}' initializing "
            f"(dir={self.output_dir})"
        )

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Output directory ready: {self.output_dir}")
        except OSError as e:
            logger.error(f"Cannot create output directory: {e}")
            raise

        self._initialized = True

    async def shutdown(self) -> None:
        """No cleanup needed for file provider."""
        logger.info(
            f"File provider '{self.name}' shutdown "
            f"(sent={self._total_sent}, errors={self._total_errors})"
        )
        self._initialized = False

    # ── MIME Construction ───────────────────────────────────────────

    def _build_mime_message(self, envelope: MailEnvelope) -> MIMEMultipart:
        """Build a full MIME message for .eml output."""
        msg = MIMEMultipart("mixed")

        # Standard headers
        msg["From"] = envelope.from_email
        msg["To"] = ", ".join(envelope.to)
        if envelope.cc:
            msg["Cc"] = ", ".join(envelope.cc)
        if envelope.bcc:
            msg["Bcc"] = ", ".join(envelope.bcc)
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
        msg["X-Aquilia-Provider"] = f"file:{self.name}"
        msg["X-Aquilia-Status"] = envelope.status.value
        if envelope.trace_id:
            msg["X-Aquilia-Trace-ID"] = envelope.trace_id
        if envelope.tenant_id:
            msg["X-Aquilia-Tenant-ID"] = envelope.tenant_id
        if envelope.priority is not None:
            msg["X-Priority"] = str(envelope.priority)

        # Body
        if envelope.body_html:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(envelope.body_text, "plain", "utf-8"))
            alt.attach(MIMEText(envelope.body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(envelope.body_text or "", "plain", "utf-8"))

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

        return msg

    @staticmethod
    def _extract_domain(email: str) -> str:
        if "<" in email:
            email = email.split("<")[1].rstrip(">")
        return email.rsplit("@", 1)[-1] if "@" in email else "localhost"

    # ── File Operations ─────────────────────────────────────────────

    def _generate_filename(self, envelope: MailEnvelope) -> str:
        """Generate a sortable filename: timestamp_envelopeID.eml"""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H-%M-%S")
        safe_id = envelope.id.replace("/", "_")[:50]
        return f"{ts}_{safe_id}{self.file_extension}"

    async def _write_file(self, path: Path, content: str | bytes) -> None:
        """Write content to a file asynchronously."""
        loop = asyncio.get_running_loop()
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        await loop.run_in_executor(
            None,
            lambda: path.write_text(content, encoding="utf-8")
            if isinstance(content, str)
            else path.write_bytes(content),
        )

    async def _write_index_entry(self, envelope: MailEnvelope, filename: str) -> None:
        """Append a JSONL entry to the index file."""
        if not self.write_index:
            return

        index_path = self.output_dir / "index.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "envelope_id": envelope.id,
            "filename": filename,
            "from": envelope.from_email,
            "to": envelope.to,
            "cc": envelope.cc,
            "bcc": envelope.bcc,
            "subject": envelope.subject,
            "priority": envelope.priority,
            "status": envelope.status.value,
        }
        if self.include_metadata and envelope.metadata:
            # Exclude blob data from index
            entry["metadata"] = {
                k: v for k, v in envelope.metadata.items()
                if not k.startswith("blob:")
            }
        if envelope.tenant_id:
            entry["tenant_id"] = envelope.tenant_id
        if envelope.trace_id:
            entry["trace_id"] = envelope.trace_id

        line = json.dumps(entry, default=str) + "\n"

        async with self._write_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: index_path.open("a", encoding="utf-8").write(line),
            )

    async def _rotate_if_needed(self) -> None:
        """Remove oldest files if max_files exceeded."""
        try:
            loop = asyncio.get_running_loop()

            def _count_and_rotate():
                eml_files = sorted(
                    self.output_dir.glob(f"*{self.file_extension}"),
                    key=lambda f: f.stat().st_mtime,
                )
                excess = len(eml_files) - self.max_files
                if excess > 0:
                    for f in eml_files[:excess]:
                        f.unlink(missing_ok=True)
                    logger.debug(f"Rotated {excess} old mail files")

            await loop.run_in_executor(None, _count_and_rotate)
        except Exception as e:
            logger.debug(f"File rotation error: {e}")

    # ── Send ────────────────────────────────────────────────────────

    async def send(self, envelope: MailEnvelope) -> ProviderResult:
        """Write the envelope as an .eml file to disk."""
        try:
            filename = self._generate_filename(envelope)
            filepath = self.output_dir / filename

            # Build MIME message
            mime_msg = self._build_mime_message(envelope)
            eml_content = mime_msg.as_string()

            # Write the .eml file
            await self._write_file(filepath, eml_content)

            # Write index entry
            await self._write_index_entry(envelope, filename)

            # Rotate old files if needed
            await self._rotate_if_needed()

            self._total_sent += 1
            logger.info(
                f"File mail written: {filepath} "
                f"(envelope={envelope.id}, to={envelope.to})"
            )

            return ProviderResult(
                status=ProviderResultStatus.SUCCESS,
                provider_message_id=f"file:{filename}",
                raw_response={"path": str(filepath)},
            )

        except Exception as e:
            self._total_errors += 1
            logger.error(f"File provider write error: {e}")
            return ProviderResult(
                status=ProviderResultStatus.TRANSIENT_FAILURE,
                error_message=f"File write error: {e}",
            )

    async def send_batch(
        self, envelopes: Sequence[MailEnvelope],
    ) -> List[ProviderResult]:
        """Write a batch of envelopes to disk."""
        results: list[ProviderResult] = []
        for envelope in envelopes:
            result = await self.send(envelope)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        """Check that the output directory exists and is writable."""
        try:
            if not self.output_dir.exists():
                return False
            # Try writing a temp file
            test_file = self.output_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return True
        except Exception as e:
            logger.debug(f"File provider health check failed: {e}")
            return False

    # ── Utility ─────────────────────────────────────────────────────

    def list_files(self) -> List[Path]:
        """List all .eml files in the output directory (sorted by time)."""
        if not self.output_dir.exists():
            return []
        return sorted(
            self.output_dir.glob(f"*{self.file_extension}"),
            key=lambda f: f.stat().st_mtime,
        )

    def read_last(self) -> Optional[str]:
        """Read the most recent .eml file (useful for testing)."""
        files = self.list_files()
        if not files:
            return None
        return files[-1].read_text(encoding="utf-8")

    def clear(self) -> int:
        """Remove all .eml files and the index (useful for testing)."""
        count = 0
        for f in self.output_dir.glob(f"*{self.file_extension}"):
            f.unlink(missing_ok=True)
            count += 1
        index = self.output_dir / "index.jsonl"
        if index.exists():
            index.unlink()
        return count

    def __repr__(self) -> str:
        return (
            f"FileProvider(name={self.name!r}, dir={self.output_dir!r}, "
            f"files={self._total_sent})"
        )
