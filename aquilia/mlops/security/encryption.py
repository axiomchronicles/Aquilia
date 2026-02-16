"""
Encryption at rest for registry blobs.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("aquilia.mlops.security.encryption")


class BlobEncryptor:
    """
    Encrypts / decrypts blob data at rest using Fernet (AES-128-CBC).

    The ``cryptography`` library is already an Aquilia dependency.
    """

    def __init__(self, key: Optional[bytes] = None):
        from cryptography.fernet import Fernet

        self._key = key or Fernet.generate_key()
        self._fernet = Fernet(self._key)

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        return self._fernet.decrypt(token)

    @property
    def key(self) -> bytes:
        return self._key

    @classmethod
    def from_key(cls, key: bytes) -> "BlobEncryptor":
        return cls(key=key)
