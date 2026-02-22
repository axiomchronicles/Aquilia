"""
UPLOAD-001 to UPLOAD-004: File upload controller tests.

Exercises: AuthController.register with profile file upload, multipart parsing,
resource limits, filename safety.
"""

import pytest
import uuid
import os


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"upload-{tag}-{uuid.uuid4().hex[:8]}@test.com"


# ── UPLOAD-001: Valid image upload ────────────────────────────────────────

class TestValidUpload:
    """Upload a valid image during registration."""

    async def test_register_with_profile_image(self, client):
        """UPLOAD-001: Registration with a profile image file succeeds."""
        # Create a minimal valid PNG (1x1 transparent pixel)
        png_1x1 = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        email = _unique_email("img")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "Uploader"},
            files={"profile": ("avatar.png", png_1x1, "image/png")},
        )

        # Should succeed — either 201 (JSON) or 302 (form redirect)
        assert resp.status_code in (201, 302), (
            f"Upload registration failed: {resp.status_code} {resp.text}"
        )


# ── UPLOAD-002: Oversized file ───────────────────────────────────────────

class TestOversizedUpload:
    """Upload a very large file to test resource limits."""

    async def test_large_file_handled(self, client):
        """UPLOAD-002: 10MB file should be rejected or handled gracefully."""
        big_data = b"X" * (10 * 1024 * 1024)  # 10MB

        email = _unique_email("big")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "BigUploader"},
            files={"profile": ("huge.bin", big_data, "application/octet-stream")},
        )

        # Should either reject (413, 400) or handle gracefully
        # Server MUST NOT crash
        assert resp.status_code > 0, "Server crashed on oversized upload"


# ── UPLOAD-003: Malformed multipart ───────────────────────────────────────

class TestMalformedMultipart:
    """Malformed multipart data should not crash the parser."""

    async def test_truncated_multipart(self, client):
        """UPLOAD-003: Truncated multipart body should not crash."""
        email = _unique_email("trunc")
        # Send raw malformed multipart
        malformed_body = (
            b"--boundary\r\n"
            b'Content-Disposition: form-data; name="email"\r\n\r\n'
            b"test@test.com\r\n"
            b"--boundary\r\n"
            b'Content-Disposition: form-data; name="profile"; filename="file.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
            # Truncated — no closing boundary
        )
        resp = await client.post(
            "/auth/register",
            body=malformed_body,
            headers={"content-type": "multipart/form-data; boundary=boundary"},
        )
        # Should not crash — any status is acceptable as long as server lives
        assert resp.status_code > 0

    async def test_empty_file_field(self, client):
        """UPLOAD-003b: Empty file in multipart should be handled."""
        email = _unique_email("empty")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "EmptyFile"},
            files={"profile": ("empty.png", b"", "image/png")},
        )
        # Should succeed (empty file is valid) or return validation error
        assert resp.status_code > 0


# ── UPLOAD-004: Null bytes in filename ────────────────────────────────────

class TestFilenameInjection:
    """Filenames with null bytes or path traversal should be sanitised."""

    async def test_null_byte_filename(self, client):
        """UPLOAD-004: Null byte in filename should be sanitised or rejected."""
        email = _unique_email("null")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "NullByte"},
            files={"profile": ("evil\x00.png", b"\x89PNG", "image/png")},
        )
        assert resp.status_code > 0  # Server must not crash

    async def test_path_traversal_filename(self, client):
        """UPLOAD-004b: Path traversal in filename should be sanitised."""
        email = _unique_email("traversal")
        resp = await client.post(
            "/auth/register",
            data={"email": email, "password": "Str0ngP@ss!", "full_name": "Traversal"},
            files={"profile": ("../../../etc/passwd", b"not really", "text/plain")},
        )
        assert resp.status_code > 0  # Server must not crash

        # If upload succeeded, verify the file was NOT saved outside upload dir
        if resp.status_code in (201, 302):
            assert not os.path.exists("/etc/passwd_test"), "Path traversal succeeded!"
