"""
Registry Service — HTTP API for publishing, fetching and managing modelpacks.

Default backend: SQLite + filesystem.
Pluggable: Postgres (metadata) + S3/MinIO/OCI (blobs).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._types import ModelpackManifest, StorageAdapter
from ..faults import (
    RegistryConnectionFault,
    PackNotFoundFault,
    ImmutabilityViolationFault,
)
from .._structures import LRUCache
from ..pack.content_store import ContentStore
from ..pack.manifest_schema import validate_manifest
from .models import RegistryDB

logger = logging.getLogger("aquilia.mlops.registry")


class RegistryError(Exception):
    """Base error for registry operations (kept for backward compatibility)."""


class PackNotFoundError(RegistryError):
    """Raised when a modelpack is not found (kept for backward compatibility)."""


class ImmutabilityError(RegistryError):
    """Raised when attempting to overwrite an immutable artifact (kept for backward compatibility)."""


class RegistryService:
    """
    Modelpack registry service.

    Manages publication, retrieval, versioning, and immutability of
    modelpacks.  Default backend is SQLite (metadata) + local filesystem
    (blobs).

    Usage::

        registry = RegistryService(db_path="registry.db", blob_root="./blobs")
        await registry.initialize()

        # Publish
        await registry.publish(manifest, blobs={...})

        # Fetch
        manifest = await registry.fetch("my-model", "v1.0.0")

        # List versions
        versions = await registry.list_versions("my-model")
    """

    def __init__(
        self,
        db_path: str = "registry.db",
        blob_root: str = ".aquilia-store",
        storage_adapter: Optional[StorageAdapter] = None,
        cache_capacity: int = 256,
    ):
        self._db = RegistryDB(db_path)
        self._content_store = ContentStore(blob_root)
        self._storage_adapter = storage_adapter
        self._initialized = False
        # LRU cache for manifest lookups  (key: "name:tag" or "digest:")
        self._cache: LRUCache[str, ModelpackManifest] = LRUCache(cache_capacity)

    async def initialize(self) -> None:
        """Initialize database schema."""
        await self._db.initialize()
        self._initialized = True
        logger.info("Registry initialized (db=%s)", self._db.db_path)

    async def close(self) -> None:
        """Close database connections."""
        await self._db.close()

    def _ensure_init(self) -> None:
        if not self._initialized:
            raise RegistryConnectionFault(
                "Registry not initialized. Call initialize() first.",
            )

    # ── Publish ──────────────────────────────────────────────────────

    async def publish(
        self,
        manifest: ModelpackManifest,
        blobs: Optional[Dict[str, bytes]] = None,
        *,
        force: bool = False,
    ) -> str:
        """
        Publish a modelpack to the registry.

        Args:
            manifest: The modelpack manifest.
            blobs: Dict mapping blob paths to their bytes.
            force: Allow overwriting existing digest (admin only).

        Returns:
            The content digest of the published manifest.

        Raises:
            ImmutabilityError: If digest already exists and ``force=False``.
        """
        self._ensure_init()

        # Validate manifest
        errors = validate_manifest(manifest.to_dict())
        if errors:
            raise RegistryConnectionFault(
                f"Invalid manifest: {'; '.join(errors)}",
                metadata={"validation_errors": errors},
            )

        digest = manifest.content_digest()

        # Check immutability
        existing = await self._db.get_pack_by_digest(digest)
        if existing and not force:
            raise ImmutabilityViolationFault(
                f"Artifact {digest} already exists. Use force=True to overwrite.",
                metadata={"digest": digest, "name": manifest.name},
            )

        # Store blobs
        if blobs:
            for blob_path, data in blobs.items():
                import hashlib
                blob_digest = "sha256:" + hashlib.sha256(data).hexdigest()
                if self._storage_adapter:
                    await self._storage_adapter.put_blob(blob_digest, data)
                else:
                    await self._content_store.store(blob_digest, data)

        # Store manifest metadata
        await self._db.insert_pack(
            name=manifest.name,
            tag=manifest.version,
            digest=digest,
            manifest_json=json.dumps(manifest.to_dict()),
            signed_by=manifest.signed_by,
        )

        # Update tag pointer
        await self._db.upsert_tag(manifest.name, manifest.version, digest)
        # Also update "latest" tag
        await self._db.upsert_tag(manifest.name, "latest", digest)

        logger.info(
            "Published %s:%s (digest=%s)", manifest.name, manifest.version, digest
        )

        # Populate cache
        self._cache.put(f"{manifest.name}:{manifest.version}", manifest)
        self._cache.put(f"{manifest.name}:latest", manifest)
        self._cache.put(f"digest:{digest}", manifest)

        return digest

    # ── Fetch ────────────────────────────────────────────────────────

    async def fetch(self, name: str, tag: str = "latest") -> ModelpackManifest:
        """
        Fetch a modelpack manifest by name and tag.

        Uses LRU cache for O(1) repeat lookups.

        Raises:
            PackNotFoundError: If pack is not found.
        """
        self._ensure_init()

        # Cache hit
        cache_key = f"{name}:{tag}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        row = await self._db.get_pack(name, tag)
        if not row:
            raise PackNotFoundFault(
                f"Pack not found: {name}:{tag}",
                metadata={"name": name, "tag": tag},
            )

        data = json.loads(row["manifest_json"])
        manifest = ModelpackManifest.from_dict(data)
        self._cache.put(cache_key, manifest)
        return manifest

    async def fetch_by_digest(self, digest: str) -> ModelpackManifest:
        """Fetch a modelpack by its content digest (LRU-cached)."""
        self._ensure_init()

        cache_key = f"digest:{digest}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        row = await self._db.get_pack_by_digest(digest)
        if not row:
            raise PackNotFoundFault(
                f"Pack not found: {digest}",
                metadata={"digest": digest},
            )

        data = json.loads(row["manifest_json"])
        manifest = ModelpackManifest.from_dict(data)
        self._cache.put(cache_key, manifest)
        return manifest

    # ── List & Query ─────────────────────────────────────────────────

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Return LRU cache hit/miss statistics."""
        return self._cache.stats

    async def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """List all versions of a modelpack."""
        self._ensure_init()
        return await self._db.list_versions(name)

    async def list_packs(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all modelpacks."""
        self._ensure_init()
        return await self._db.list_packs(limit, offset)

    # ── Promote ──────────────────────────────────────────────────────

    async def promote(
        self,
        name: str,
        tag: str,
        target_tag: str,
    ) -> None:
        """
        Promote a modelpack tag to another tag (e.g., staging → production).

        Copies the digest from ``name:tag`` to ``name:target_tag``.
        """
        self._ensure_init()

        row = await self._db.get_pack(name, tag)
        if not row:
            raise PackNotFoundFault(
                f"Pack not found: {name}:{tag}",
                metadata={"name": name, "tag": tag},
            )

        await self._db.upsert_tag(name, target_tag, row["digest"])
        # Update cache: promoted tag points to same manifest
        cached = self._cache.get(f"{name}:{tag}")
        if cached is not None:
            self._cache.put(f"{name}:{target_tag}", cached)
        logger.info("Promoted %s:%s → %s:%s", name, tag, name, target_tag)

    # ── Delete ───────────────────────────────────────────────────────

    async def delete(self, name: str, tag: str) -> None:
        """Delete a modelpack tag (admin only)."""
        self._ensure_init()
        await self._db.delete_tag(name, tag)
        self._cache.invalidate(f"{name}:{tag}")
        logger.info("Deleted tag %s:%s", name, tag)

    # ── Verify ───────────────────────────────────────────────────────

    async def verify(self, name: str, tag: str) -> Dict[str, Any]:
        """
        Verify integrity of a modelpack.

        Returns:
            Dict with ``valid``, ``digest``, ``signed_by`` keys.
        """
        self._ensure_init()

        row = await self._db.get_pack(name, tag)
        if not row:
            raise PackNotFoundFault(
                f"Pack not found: {name}:{tag}",
                metadata={"name": name, "tag": tag},
            )

        data = json.loads(row["manifest_json"])
        manifest = ModelpackManifest.from_dict(data)
        computed = manifest.content_digest()

        return {
            "valid": computed == row["digest"],
            "digest": row["digest"],
            "computed_digest": computed,
            "signed_by": row.get("signed_by", ""),
            "name": name,
            "tag": tag,
        }
