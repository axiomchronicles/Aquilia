"""
Artifact Builder — fluent API for constructing artifacts.

Usage::

    artifact = (
        ArtifactBuilder("my-config", kind="config", version="1.0.0")
        .set_payload({"database": {"url": "sqlite:///db.sqlite3"}})
        .tag("env", "production")
        .tag("team", "platform")
        .set_metadata(author="deploy-bot", pipeline="ci-main")
        .set_provenance(git_sha="abc1234", source_path="config/prod.yaml")
        .build()
    )

Calling ``.build()`` computes the SHA-256 digest of the serialised
payload and freezes the artifact.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .core import (
    Artifact,
    ArtifactEnvelope,
    ArtifactIntegrity,
    ArtifactKind,
    ArtifactProvenance,
)


class ArtifactBuilder:
    """
    Fluent builder for creating :class:`Artifact` instances.

    Every ``set_*`` / ``tag`` / ``add_*`` method returns ``self``
    for chaining.
    """

    __slots__ = (
        "_name",
        "_kind",
        "_version",
        "_payload",
        "_metadata",
        "_tags",
        "_provenance",
        "_files",
    )

    def __init__(
        self,
        name: str,
        *,
        kind: str = "custom",
        version: str = "0.0.0",
    ) -> None:
        self._name = name
        self._kind = kind
        self._version = version
        self._payload: Any = None
        self._metadata: Dict[str, Any] = {}
        self._tags: Dict[str, str] = {}
        self._provenance: Optional[ArtifactProvenance] = None
        self._files: List[Dict[str, Any]] = []

    @classmethod
    def from_artifact(
        cls,
        artifact: "Artifact",
        *,
        version: str = "",
    ) -> "ArtifactBuilder":
        """
        Pre-populate builder from an existing artifact.

        Useful for version-bump or patch workflows::

            v2 = ArtifactBuilder.from_artifact(v1, version="2.0.0") \
                .merge_payload({"accuracy": 0.99}) \
                .build()
        """
        b = cls(
            artifact.name,
            kind=artifact.kind,
            version=version or artifact.version,
        )
        # Deep-copy payload
        if isinstance(artifact.payload, dict):
            b._payload = {**artifact.payload}
        else:
            b._payload = artifact.payload
        b._metadata = dict(artifact.metadata)
        b._tags = dict(artifact.tags)
        b._tags["derived_from"] = artifact.digest
        return b

    # ── Payload ──────────────────────────────────────────────────────

    def set_payload(self, payload: Any) -> "ArtifactBuilder":
        """Set the artifact payload (dict, list, string, bytes, …)."""
        self._payload = payload
        return self

    def merge_payload(self, extra: Dict[str, Any]) -> "ArtifactBuilder":
        """Merge additional keys into an existing dict payload."""
        if self._payload is None:
            self._payload = {}
        if isinstance(self._payload, dict):
            self._payload.update(extra)
        return self

    # ── Metadata ─────────────────────────────────────────────────────

    def set_metadata(self, **kwargs: Any) -> "ArtifactBuilder":
        """Set metadata key-value pairs."""
        self._metadata.update(kwargs)
        return self

    def tag(self, key: str, value: str) -> "ArtifactBuilder":
        """Add a tag (string→string)."""
        self._tags[key] = value
        return self

    def tags(self, **kwargs: str) -> "ArtifactBuilder":
        """Add multiple tags at once."""
        self._tags.update(kwargs)
        return self

    # ── Provenance ───────────────────────────────────────────────────

    def set_provenance(
        self,
        *,
        git_sha: str = "",
        source_path: str = "",
        created_by: str = "",
        hostname: str = "",
    ) -> "ArtifactBuilder":
        """Set provenance explicitly."""
        self._provenance = ArtifactProvenance(
            created_at="",  # will be filled at build time
            created_by=created_by,
            git_sha=git_sha,
            source_path=source_path,
            hostname=hostname,
        )
        return self

    def auto_provenance(self, source_path: str = "") -> "ArtifactBuilder":
        """Auto-detect provenance from the environment."""
        self._provenance = ArtifactProvenance.auto(source_path)
        return self

    # ── Files (for bundle/model artifacts) ───────────────────────────

    def add_file(
        self,
        path: str,
        *,
        role: str = "data",
        digest: str = "",
        size: int = 0,
    ) -> "ArtifactBuilder":
        """Register a file reference inside the artifact."""
        self._files.append(
            {"path": path, "role": role, "digest": digest, "size": size}
        )
        return self

    # ── Version ──────────────────────────────────────────────────────

    def set_version(self, version: str) -> "ArtifactBuilder":
        self._version = version
        return self

    # ── Build ────────────────────────────────────────────────────────

    def build(self) -> Artifact:
        """
        Freeze the artifact and compute its integrity digest.

        Returns:
            A fully-formed :class:`Artifact`.

        Raises:
            ValueError: If *name* is empty.
        """
        if not self._name or not self._name.strip():
            raise ValueError("Artifact name must not be empty")

        # Provenance — auto-fill only once
        if self._provenance is not None:
            prov = self._provenance
        else:
            prov = ArtifactProvenance.auto()

        # Ensure created_at is populated
        if not prov.created_at:
            from datetime import datetime, timezone

            prov = ArtifactProvenance(
                created_at=datetime.now(timezone.utc).isoformat(),
                created_by=prov.created_by,
                git_sha=prov.git_sha,
                source_path=prov.source_path,
                hostname=prov.hostname,
                build_tool=prov.build_tool,
            )

        # Attach file list to payload if present
        payload = self._payload
        if self._files:
            if payload is None:
                payload = {}
            if isinstance(payload, dict):
                payload["_files"] = self._files

        # Compute integrity over the payload
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str,
        ).encode("utf-8")
        integrity = ArtifactIntegrity.compute(payload_bytes)

        envelope = ArtifactEnvelope(
            kind=self._kind,
            name=self._name,
            version=self._version,
            integrity=integrity,
            provenance=prov,
            metadata=self._metadata,
            tags=self._tags,
            payload=payload,
        )

        return Artifact(envelope)
