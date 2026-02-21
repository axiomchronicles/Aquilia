"""
E2E Auth Tests — MFA (Multi-Factor Authentication)

Tests TOTP enrollment, code generation/verification, and backup codes.
"""

import time
import pytest

from aquilia.auth.mfa import TOTPProvider, MFAManager


class TestTOTPEnrollmentAndVerification:
    """TOTP (Google Authenticator compatible) tests."""

    async def test_totp_enroll_and_verify(self, mfa_manager):
        """Full TOTP enrollment: generate secret → generate code → verify."""
        enrollment = await mfa_manager.enroll_totp("user-001", "user@test.com")

        secret = enrollment["secret"]
        assert len(secret) > 10  # Base32 encoded secret

        # Generate code at current time
        code = mfa_manager.totp.generate_code(secret)

        # Verify code
        is_valid = await mfa_manager.verify_totp(secret, code)
        assert is_valid is True

    async def test_totp_invalid_code(self, mfa_manager):
        """Wrong TOTP code returns False."""
        enrollment = await mfa_manager.enroll_totp("user-002", "user2@test.com")
        secret = enrollment["secret"]

        is_valid = await mfa_manager.verify_totp(secret, "000000")
        assert is_valid is False

    def test_totp_time_window(self, totp_provider):
        """Codes from adjacent time periods are accepted (±1 window)."""
        secret = totp_provider.generate_secret()
        current_time = int(time.time())

        # Generate code for current period
        code = totp_provider.generate_code(secret, current_time)

        # Verify with window=1 (accepts ±30s)
        assert totp_provider.verify_code(secret, code, window=1, timestamp=current_time) is True

        # Code from previous period should also be accepted
        prev_code = totp_provider.generate_code(secret, current_time - 30)
        assert totp_provider.verify_code(secret, prev_code, window=1, timestamp=current_time) is True

        # Code from next period should also be accepted
        next_code = totp_provider.generate_code(secret, current_time + 30)
        assert totp_provider.verify_code(secret, next_code, window=1, timestamp=current_time) is True

    def test_totp_out_of_window(self, totp_provider):
        """Code far outside the time window is rejected."""
        secret = totp_provider.generate_secret()
        current_time = int(time.time())

        # Code from 5 minutes ago (10 periods)
        old_code = totp_provider.generate_code(secret, current_time - 300)
        assert totp_provider.verify_code(secret, old_code, window=1, timestamp=current_time) is False


class TestBackupCodes:
    """Backup code generation and verification."""

    async def test_backup_code_verify(self, mfa_manager):
        """Valid backup code passes verification."""
        enrollment = await mfa_manager.enroll_totp("user-003", "user3@test.com")

        backup_codes = enrollment["backup_codes"]
        backup_hashes = enrollment["backup_code_hashes"]

        assert len(backup_codes) == 10
        assert len(backup_hashes) == 10

        # Verify first backup code
        valid, remaining = await mfa_manager.verify_backup_code(
            backup_codes[0], backup_hashes
        )
        assert valid is True
        assert len(remaining) == 9  # One code consumed

    async def test_invalid_backup_code(self, mfa_manager):
        """Invalid backup code returns False and doesn't consume codes."""
        enrollment = await mfa_manager.enroll_totp("user-004", "user4@test.com")
        backup_hashes = enrollment["backup_code_hashes"]

        valid, remaining = await mfa_manager.verify_backup_code(
            "FAKE-CODE-1234", backup_hashes
        )
        assert valid is False
        assert len(remaining) == 10  # No code consumed

    async def test_backup_code_consumes_on_use(self, mfa_manager):
        """Used backup code is removed from remaining list, can't be reused."""
        enrollment = await mfa_manager.enroll_totp("user-005", "user5@test.com")

        codes = enrollment["backup_codes"]
        hashes = enrollment["backup_code_hashes"]

        # Use first code
        valid1, remaining1 = await mfa_manager.verify_backup_code(codes[0], hashes)
        assert valid1 is True

        # Try to use it again — should fail
        valid2, remaining2 = await mfa_manager.verify_backup_code(codes[0], remaining1)
        assert valid2 is False
        assert len(remaining2) == 9


class TestProvisioningURI:
    """TOTP provisioning URI for QR codes."""

    def test_provisioning_uri_format(self, totp_provider):
        """URI follows otpauth:// schema."""
        secret = totp_provider.generate_secret()
        uri = totp_provider.generate_provisioning_uri(secret, "user@test.com")

        assert uri.startswith("otpauth://totp/")
        assert "AquiliaTest" in uri
        assert "user@test.com" in uri
        assert f"secret={secret}" in uri
        assert "algorithm=SHA1" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_backup_codes_format(self, totp_provider):
        """Backup codes have XXXX-XXXX-XXXX format."""
        codes = totp_provider.generate_backup_codes(5)
        assert len(codes) == 5
        for code in codes:
            parts = code.split("-")
            assert len(parts) == 3
            for part in parts:
                assert len(part) == 4
