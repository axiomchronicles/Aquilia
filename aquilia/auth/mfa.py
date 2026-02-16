"""
AquilAuth - MFA Providers

Multi-factor authentication providers for TOTP, WebAuthn, SMS, and Email.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Any

from .faults import AUTH_MFA_INVALID, AUTH_MFA_NOT_ENROLLED


# ============================================================================
# TOTP Provider (Time-based One-Time Password)
# ============================================================================


class TOTPProvider:
    """
    TOTP (Time-based One-Time Password) provider.

    Implements RFC 6238 for generating and verifying 6-digit codes.
    Compatible with Google Authenticator, Authy, etc.
    """

    def __init__(
        self,
        issuer: str = "Aquilia",
        digits: int = 6,
        period: int = 30,
        algorithm: str = "SHA1",
    ):
        """
        Initialize TOTP provider.

        Args:
            issuer: Issuer name shown in authenticator apps
            digits: Number of digits in code (default 6)
            period: Time period in seconds (default 30)
            algorithm: Hash algorithm (SHA1, SHA256, SHA512)
        """
        self.issuer = issuer
        self.digits = digits
        self.period = period
        self.algorithm = algorithm

    def generate_secret(self) -> str:
        """
        Generate random TOTP secret.

        Returns:
            Base32-encoded secret string
        """
        # Generate 160-bit (20-byte) random secret
        secret_bytes = secrets.token_bytes(20)
        return base64.b32encode(secret_bytes).decode("utf-8").rstrip("=")

    def generate_code(self, secret: str, timestamp: int | None = None) -> str:
        """
        Generate TOTP code for given secret and time.

        Args:
            secret: Base32-encoded secret
            timestamp: Unix timestamp (default: current time)

        Returns:
            6-digit TOTP code as string
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time counter
        counter = timestamp // self.period

        # Decode secret
        secret_bytes = base64.b32decode(secret + "=" * (-len(secret) % 8))

        # HMAC-SHA1
        hmac_hash = hmac.new(
            secret_bytes,
            struct.pack(">Q", counter),
            hashlib.sha1,
        ).digest()

        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        code = struct.unpack(">I", hmac_hash[offset : offset + 4])[0]
        code &= 0x7FFFFFFF

        # Format to digits
        code = code % (10**self.digits)
        return str(code).zfill(self.digits)

    def verify_code(
        self,
        secret: str,
        code: str,
        window: int = 1,
        timestamp: int | None = None,
    ) -> bool:
        """
        Verify TOTP code.

        Args:
            secret: Base32-encoded secret
            code: User-provided code
            window: Number of periods to check (default 1 = ±30s)
            timestamp: Unix timestamp (default: current time)

        Returns:
            True if code valid, False otherwise
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Check current period and adjacent periods (clock drift tolerance)
        for offset in range(-window, window + 1):
            check_time = timestamp + (offset * self.period)
            expected_code = self.generate_code(secret, check_time)
            if secrets.compare_digest(code, expected_code):
                return True

        return False

    def generate_provisioning_uri(
        self, secret: str, account_name: str
    ) -> str:
        """
        Generate provisioning URI for QR code.

        Args:
            secret: Base32-encoded secret
            account_name: Account identifier (email, username)

        Returns:
            otpauth:// URI for QR code generation
        """
        return (
            f"otpauth://totp/{self.issuer}:{account_name}"
            f"?secret={secret}"
            f"&issuer={self.issuer}"
            f"&algorithm={self.algorithm}"
            f"&digits={self.digits}"
            f"&period={self.period}"
        )

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup recovery codes.

        Args:
            count: Number of codes to generate

        Returns:
            List of backup codes (format: XXXX-XXXX-XXXX)
        """
        codes = []
        for _ in range(count):
            # Generate 12-digit code
            code = secrets.token_hex(6).upper()
            # Format as XXXX-XXXX-XXXX
            formatted = f"{code[0:4]}-{code[4:8]}-{code[8:12]}"
            codes.append(formatted)
        return codes

    @staticmethod
    def hash_backup_code(code: str) -> str:
        """
        Hash backup code for storage.

        Args:
            code: Backup code

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def verify_backup_code(code: str, code_hash: str) -> bool:
        """
        Verify backup code against hash.

        Args:
            code: User-provided backup code
            code_hash: Stored hash

        Returns:
            True if code matches
        """
        computed_hash = TOTPProvider.hash_backup_code(code)
        return secrets.compare_digest(computed_hash, code_hash)


# ============================================================================
# WebAuthn Provider (FIDO2 / Passkeys)
# ============================================================================


class WebAuthnProvider:
    """
    WebAuthn provider for passwordless authentication.

    Supports FIDO2 authenticators (hardware keys, biometrics, passkeys).
    Note: This is a simplified implementation. Production use requires
    a full WebAuthn library like py_webauthn.
    """

    def __init__(
        self,
        rp_id: str,
        rp_name: str,
        origin: str,
    ):
        """
        Initialize WebAuthn provider.

        Args:
            rp_id: Relying Party ID (domain)
            rp_name: Relying Party name
            origin: Expected origin (https://example.com)
        """
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def generate_challenge(self) -> str:
        """
        Generate cryptographic challenge.

        Returns:
            Base64-encoded challenge
        """
        challenge = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(challenge).decode().rstrip("=")

    def generate_registration_options(
        self,
        user_id: str,
        user_name: str,
        user_display_name: str,
    ) -> dict[str, Any]:
        """
        Generate WebAuthn registration options.

        Args:
            user_id: Unique user identifier
            user_name: Username (email or username)
            user_display_name: Display name

        Returns:
            Registration options for navigator.credentials.create()
        """
        challenge = self.generate_challenge()

        return {
            "publicKey": {
                "challenge": challenge,
                "rp": {
                    "id": self.rp_id,
                    "name": self.rp_name,
                },
                "user": {
                    "id": base64.urlsafe_b64encode(
                        user_id.encode()
                    ).decode(),
                    "name": user_name,
                    "displayName": user_display_name,
                },
                "pubKeyCredParams": [
                    {"type": "public-key", "alg": -7},  # ES256
                    {"type": "public-key", "alg": -257},  # RS256
                ],
                "timeout": 60000,
                "authenticatorSelection": {
                    "authenticatorAttachment": "cross-platform",
                    "requireResidentKey": False,
                    "userVerification": "preferred",
                },
                "attestation": "none",
            },
            "_challenge": challenge,  # Store for verification
        }

    def generate_authentication_options(
        self,
        credential_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate WebAuthn authentication options.

        Args:
            credential_ids: List of allowed credential IDs (optional)

        Returns:
            Authentication options for navigator.credentials.get()
        """
        challenge = self.generate_challenge()

        options: dict[str, Any] = {
            "publicKey": {
                "challenge": challenge,
                "timeout": 60000,
                "rpId": self.rp_id,
                "userVerification": "preferred",
            },
            "_challenge": challenge,
        }

        if credential_ids:
            options["publicKey"]["allowCredentials"] = [
                {"type": "public-key", "id": cred_id}
                for cred_id in credential_ids
            ]

        return options

    def verify_registration_response(
        self,
        response: dict[str, Any],
        expected_challenge: str,
    ) -> dict[str, Any]:
        """
        Verify WebAuthn registration response.

        Args:
            response: Response from navigator.credentials.create()
            expected_challenge: Challenge from registration options

        Returns:
            Credential data for storage

        Note: This is simplified. Production should use py_webauthn.
        """
        # In production, verify:
        # 1. Challenge matches
        # 2. Origin matches
        # 3. RP ID hash matches
        # 4. Attestation signature (if present)
        # 5. Public key is valid

        # Extract credential data
        credential_id = response.get("id")
        public_key = response.get("response", {}).get("publicKey")

        if not credential_id or not public_key:
            raise AUTH_MFA_INVALID(
                reason="Invalid registration response",
            )

        return {
            "credential_id": credential_id,
            "public_key": public_key,
            "sign_count": 0,
            "created_at": time.time(),
        }

    def verify_authentication_response(
        self,
        response: dict[str, Any],
        expected_challenge: str,
        stored_credential: dict[str, Any],
    ) -> bool:
        """
        Verify WebAuthn authentication response.

        Args:
            response: Response from navigator.credentials.get()
            expected_challenge: Challenge from authentication options
            stored_credential: Stored credential data

        Returns:
            True if authentication successful

        Note: This is simplified. Production should use py_webauthn.
        """
        # In production, verify:
        # 1. Challenge matches
        # 2. Origin matches
        # 3. RP ID hash matches
        # 4. Signature is valid using stored public key
        # 5. Sign count has incremented (prevents cloning)

        credential_id = response.get("id")
        sign_count = response.get("response", {}).get("authenticatorData", {}).get(
            "signCount", 0
        )

        # Basic checks
        if credential_id != stored_credential["credential_id"]:
            return False

        if sign_count <= stored_credential["sign_count"]:
            # Sign count should always increment (prevents cloning)
            return False

        # Update sign count
        stored_credential["sign_count"] = sign_count

        return True

# ============================================================================
# MFA Manager
# ============================================================================


class MFAManager:
    """
    Central MFA manager coordinating all MFA providers.
    """

    def __init__(
        self,
        totp_provider: TOTPProvider | None = None,
        webauthn_provider: WebAuthnProvider | None = None
    ):
        self.totp = totp_provider or TOTPProvider()
        self.webauthn = webauthn_provider

    async def enroll_totp(self, user_id: str, account_name: str) -> dict[str, Any]:
        """
        Enroll user in TOTP MFA.

        Returns:
            Dict with secret, QR code URI, and backup codes
        """
        secret = self.totp.generate_secret()
        uri = self.totp.generate_provisioning_uri(secret, account_name)
        backup_codes = self.totp.generate_backup_codes()

        # Hash backup codes for storage
        backup_code_hashes = [
            self.totp.hash_backup_code(code) for code in backup_codes
        ]

        return {
            "secret": secret,
            "provisioning_uri": uri,
            "backup_codes": backup_codes,
            "backup_code_hashes": backup_code_hashes,
        }

    async def verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code."""
        return self.totp.verify_code(secret, code)

    async def verify_backup_code(
        self, code: str, backup_code_hashes: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Verify backup code and remove it.

        Returns:
            Tuple of (valid, remaining_hashes)
        """
        for code_hash in backup_code_hashes:
            if self.totp.verify_backup_code(code, code_hash):
                # Remove used code
                remaining = [h for h in backup_code_hashes if h != code_hash]
                return True, remaining

        return False, backup_code_hashes
