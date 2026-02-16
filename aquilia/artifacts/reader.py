"""
Artifact Reader — load, inspect, verify, and query artifacts.

Sits on top of any :class:`ArtifactStoreProtocol` and adds
higher-level operations:

- ``load`` / ``load_or_fail`` — retrieve with optional version
- ``inspect`` — print a human-readable summary
- ``verify`` / ``batch_verify`` — integrity verification
- ``diff`` — compare two artifact versions
- ``history`` — list all versions of a named artifact
- ``search`` — find by kind, tags, metadata
- ``stats`` — aggregate statistics
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .core import Artifact
from .store import ArtifactStoreProtocol

logger = logging.getLogger("aquilia.artifacts.reader")


class ArtifactReader:
    """
    High-level artifact reader / inspector.

    Wraps a store and adds convenience query + verification methods.
    """

    __slots__ = ("_store",)

    def __init__(self, store: ArtifactStoreProtocol) -> None:
        self._store = store

    @property
    def store(self) -> ArtifactStoreProtocol:
        """Underlying store reference."""
        return self._store

    # ── Load ─────────────────────────────────────────────────────────

    def load(self, name: str, *, version: str = "") -> Optional[Artifact]:
        """Load an artifact by name and optional version."""
        return self._store.load(name, version=version)

    def load_or_fail(self, name: str, *, version: str = "") -> Artifact:
        """Load or raise ``FileNotFoundError``."""
        a = self._store.load(name, version=version)
        if a is None:
            label = f"{name}:{version}" if version else name
            raise FileNotFoundError(f"Artifact not found: {label}")
        return a

    def load_by_digest(self, digest: str) -> Optional[Artifact]:
        """Content-addressed lookup."""
        return self._store.load_by_digest(digest)

    # ── Query ────────────────────────────────────────────────────────

    def list_all(self, *, kind: str = "") -> List[Artifact]:
        """List all artifacts, optionally filtered by kind."""
        return self._store.list_artifacts(kind=kind)

    def history(self, name: str) -> List[Artifact]:
        """All versions of a named artifact, oldest first."""
        all_artifacts = self._store.list_artifacts()
        return sorted(
            [a for a in all_artifacts if a.name == name],
            key=lambda a: a.created_at,
        )

    def search(
        self,
        *,
        kind: str = "",
        tag_key: str = "",
        tag_value: str = "",
        name_prefix: str = "",
    ) -> List[Artifact]:
        """
        Search artifacts by kind, tag, or name prefix.
        """
        candidates = self._store.list_artifacts(
            kind=kind, tag_key=tag_key, tag_value=tag_value,
        )
        if name_prefix:
            candidates = [a for a in candidates if a.name.startswith(name_prefix)]
        return candidates

    def names(self) -> List[str]:
        """Unique artifact names in the store (sorted)."""
        return sorted({a.name for a in self._store.list_artifacts()})

    def latest(self, name: str) -> Optional[Artifact]:
        """Latest version of a named artifact by creation time."""
        versions = self.history(name)
        return versions[-1] if versions else None

    # ── Verify ───────────────────────────────────────────────────────

    def verify(self, artifact: Artifact) -> bool:
        """
        Re-compute the payload digest and compare to stored integrity.
        """
        return artifact.verify()

    def verify_by_name(self, name: str, *, version: str = "") -> Optional[bool]:
        """
        Load + verify an artifact.

        Returns ``None`` if the artifact does not exist, ``True`` if
        integrity passes, ``False`` if tampered.
        """
        a = self._store.load(name, version=version)
        if a is None:
            return None
        return self.verify(a)

    def batch_verify(self) -> Tuple[int, int, List[str]]:
        """
        Verify every artifact in the store.

        Returns:
            ``(passed, failed, failed_names)``
        """
        passed = 0
        failed = 0
        failed_names: List[str] = []

        for a in self._store.list_artifacts():
            if a.verify():
                passed += 1
            else:
                failed += 1
                failed_names.append(a.qualified_name)

        return passed, failed, failed_names

    # ── Inspect ──────────────────────────────────────────────────────

    @staticmethod
    def inspect(artifact: Artifact) -> Dict[str, Any]:
        """
        Return a human-readable inspection summary.
        """
        payload_size = 0
        payload_preview = ""
        if artifact.payload is not None:
            raw = json.dumps(artifact.payload, default=str)
            payload_size = len(raw)
            payload_preview = raw[:120] + ("…" if len(raw) > 120 else "")

        return {
            "name": artifact.name,
            "version": artifact.version,
            "kind": artifact.kind,
            "digest": artifact.digest,
            "created_at": artifact.created_at,
            "created_by": artifact.provenance.created_by,
            "git_sha": artifact.provenance.git_sha,
            "hostname": artifact.provenance.hostname,
            "source_path": artifact.provenance.source_path,
            "tags": artifact.tags,
            "metadata": artifact.metadata,
            "metadata_keys": list(artifact.metadata.keys()),
            "payload_type": type(artifact.payload).__name__,
            "payload_size": payload_size,
            "payload_preview": payload_preview,
            "size_bytes": artifact.size_bytes,
            "verified": artifact.verify(),
        }

    # ── Diff ─────────────────────────────────────────────────────────

    @staticmethod
    def diff(a: Artifact, b: Artifact) -> Dict[str, Any]:
        """
        Compare two artifacts and return a diff summary.

        Works best when payloads are dicts.
        """
        result: Dict[str, Any] = {
            "name_match": a.name == b.name,
            "kind_match": a.kind == b.kind,
            "version_a": a.version,
            "version_b": b.version,
            "digest_match": a.digest == b.digest,
            "provenance_changed": a.provenance != b.provenance,
            "tags_changed": a.tags != b.tags,
            "metadata_changed": a.metadata != b.metadata,
        }

        if isinstance(a.payload, dict) and isinstance(b.payload, dict):
            keys_a = set(a.payload.keys())
            keys_b = set(b.payload.keys())
            result["added_keys"] = sorted(keys_b - keys_a)
            result["removed_keys"] = sorted(keys_a - keys_b)
            result["common_keys"] = sorted(keys_a & keys_b)
            changed = []
            for k in keys_a & keys_b:
                if a.payload[k] != b.payload[k]:
                    changed.append(k)
            result["changed_keys"] = changed
        else:
            result["payload_diff"] = "non-dict payloads, cannot diff"

        return result

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """
        Aggregate statistics about the store.

        Returns a dict with total count, breakdown by kind, total size,
        unique names, and oldest/newest timestamps.
        """
        all_artifacts = self._store.list_artifacts()
        by_kind: Dict[str, int] = {}
        total_size = 0
        names_set: set = set()
        oldest = ""
        newest = ""

        for a in all_artifacts:
            by_kind[a.kind] = by_kind.get(a.kind, 0) + 1
            total_size += a.size_bytes
            names_set.add(a.name)
            ts = a.created_at
            if ts:
                if not oldest or ts < oldest:
                    oldest = ts
                if not newest or ts > newest:
                    newest = ts

        return {
            "total": len(all_artifacts),
            "by_kind": by_kind,
            "unique_names": len(names_set),
            "total_size_bytes": total_size,
            "oldest": oldest,
            "newest": newest,
        }
