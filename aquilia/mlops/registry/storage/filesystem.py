"""
Filesystem storage adapter — stores blobs on local disk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .base import BaseStorageAdapter


class FilesystemStorageAdapter(BaseStorageAdapter):
    """Store blobs on local filesystem in a content-addressable layout."""

    def __init__(self, root: str = ".aquilia-blobs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        algo, hex_hash = digest.split(":", 1)
        return self.root / algo / hex_hash[:2] / hex_hash

    async def put_blob(self, digest: str, data: bytes) -> str:
        path = self._path(digest)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return str(path)

    async def get_blob(self, digest: str) -> bytes:
        path = self._path(digest)
        if not path.exists():
            raise FileNotFoundError(f"Blob not found: {digest}")
        return path.read_bytes()

    async def has_blob(self, digest: str) -> bool:
        return self._path(digest).exists()

    async def delete_blob(self, digest: str) -> None:
        path = self._path(digest)
        if path.exists():
            path.unlink()

    async def list_blobs(self) -> List[str]:
        digests: List[str] = []
        for algo_dir in self.root.iterdir():
            if not algo_dir.is_dir():
                continue
            for prefix_dir in algo_dir.iterdir():
                if not prefix_dir.is_dir():
                    continue
                for blob_file in prefix_dir.iterdir():
                    if blob_file.is_file():
                        digests.append(f"{algo_dir.name}:{blob_file.name}")
        return digests
