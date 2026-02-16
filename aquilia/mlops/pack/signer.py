"""
Artifact signing and verification.

Supports HMAC-SHA256 (built-in, no external deps) and optional
GPG / RSA signing when ``cryptography`` is available.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aquilia.mlops.pack.signer")


class SignatureError(Exception):
    """Raised when signature verification fails."""


class HMACSigner:
    """
    HMAC-SHA256 signer for modelpack archives.

    Quick-start signer that ships with zero external dependencies
    beyond the stdlib + ``cryptography`` already in Aquilia's deps.
    """

    def __init__(self, secret: str):
        self._secret = secret.encode()

    def sign(self, data: bytes) -> str:
        """Produce an HMAC-SHA256 hex signature."""
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        """Verify an HMAC-SHA256 hex signature."""
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)


class RSASigner:
    """
    RSA signer using ``cryptography`` (already an Aquilia dependency).
    """

    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ):
        self._private_key_path = private_key_path
        self._public_key_path = public_key_path

    def sign(self, data: bytes) -> bytes:
        """Sign data with RSA private key."""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        if not self._private_key_path:
            raise SignatureError("Private key path not configured")

        key_data = Path(self._private_key_path).read_bytes()
        private_key = serialization.load_pem_private_key(key_data, password=None)
        return private_key.sign(  # type: ignore[union-attr]
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify RSA signature with public key."""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature

        if not self._public_key_path:
            raise SignatureError("Public key path not configured")

        key_data = Path(self._public_key_path).read_bytes()
        public_key = serialization.load_pem_public_key(key_data)
        try:
            public_key.verify(  # type: ignore[union-attr]
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False


async def sign_archive(
    archive_path: str,
    signer: HMACSigner | RSASigner,
    output_sig_path: Optional[str] = None,
) -> str:
    """
    Sign a modelpack archive and write signature file.

    Returns the path to the ``.sig`` file.
    """
    data = Path(archive_path).read_bytes()

    if isinstance(signer, HMACSigner):
        sig = signer.sign(data).encode()
    else:
        sig = signer.sign(data)

    sig_path = output_sig_path or archive_path + ".sig"
    Path(sig_path).write_bytes(sig)
    logger.info("Signed archive: %s -> %s", archive_path, sig_path)
    return sig_path


async def verify_archive(
    archive_path: str,
    sig_path: str,
    signer: HMACSigner | RSASigner,
) -> bool:
    """Verify a modelpack archive against its signature file."""
    data = Path(archive_path).read_bytes()
    sig = Path(sig_path).read_bytes()

    if isinstance(signer, HMACSigner):
        return signer.verify(data, sig.decode())
    else:
        return signer.verify(data, sig)
