"""
Base storage adapter — abstract interface for blob backends.
"""

from __future__ import annotations

import abc
from typing import List


class BaseStorageAdapter(abc.ABC):
    """Abstract base for blob storage backends."""

    @abc.abstractmethod
    async def put_blob(self, digest: str, data: bytes) -> str:
        """Store a blob, return storage path or URI."""

    @abc.abstractmethod
    async def get_blob(self, digest: str) -> bytes:
        """Retrieve a blob by digest."""

    @abc.abstractmethod
    async def has_blob(self, digest: str) -> bool:
        """Check if a blob exists."""

    @abc.abstractmethod
    async def delete_blob(self, digest: str) -> None:
        """Delete a blob."""

    @abc.abstractmethod
    async def list_blobs(self) -> List[str]:
        """List all blob digests."""
