"""
Artifact Store — pluggable storage backends for artifacts.

Provides three implementations:

- **MemoryArtifactStore** — ephemeral, test-friendly
- **FilesystemArtifactStore** — persistent, writes ``.aq.json`` files
  into a configurable directory (default ``artifacts/``)
- **ArtifactStore** — convenience alias that auto-detects

All stores support:

- ``save(artifact)``            — idempotent upsert
- ``load(name, version=)``      — load by name (+ optional version)
- ``load_by_digest(digest)``    — content-addressed lookup
- ``list(kind=, tag=)``         — filtered listing
- ``delete(name, version=)``    — remove artifact(s)
- ``exists(name, version=)``    — existence check
- ``gc(referenced)``            — garbage-collect unreferenced
- ``export_bundle(names, path)``— export subset as a ``.aq-bundle``
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .core import Artifact, ArtifactEnvelope, ArtifactIntegrity

logger = logging.getLogger("aquilia.artifacts.store")


# ── Abstract Protocol ───────────────────────────────────────────────────


class ArtifactStoreProtocol:
    """Minimal interface every store must implement."""

    def save(self, artifact: Artifact) -> str:
        raise NotImplementedError

    def load(self, name: str, *, version: str = "") -> Optional[Artifact]:
        raise NotImplementedError

    def load_by_digest(self, digest: str) -> Optional[Artifact]:
        raise NotImplementedError

    def list_artifacts(
        self,
        *,
        kind: str = "",
        tag_key: str = "",
        tag_value: str = "",
    ) -> List[Artifact]:
        raise NotImplementedError

    def delete(self, name: str, *, version: str = "") -> int:
        raise NotImplementedError

    def exists(self, name: str, *, version: str = "") -> bool:
        raise NotImplementedError


# ── Memory Store ────────────────────────────────────────────────────────


class MemoryArtifactStore(ArtifactStoreProtocol):
    """
    Ephemeral in-memory artifact store.

    Useful for tests and short-lived pipelines.
    """

    __slots__ = ("_artifacts",)

    def __init__(self) -> None:
        # key = (name, version)
        self._artifacts: Dict[tuple, Artifact] = {}

    def save(self, artifact: Artifact) -> str:
        key = (artifact.name, artifact.version)
        self._artifacts[key] = artifact
        return artifact.digest

    def load(self, name: str, *, version: str = "") -> Optional[Artifact]:
        if version:
            return self._artifacts.get((name, version))
        # Return latest (last inserted with this name)
        matches = [a for (n, _v), a in self._artifacts.items() if n == name]
        return matches[-1] if matches else None

    def load_by_digest(self, digest: str) -> Optional[Artifact]:
        for a in self._artifacts.values():
            if a.digest == digest:
                return a
        return None

    def list_artifacts(
        self,
        *,
        kind: str = "",
        tag_key: str = "",
        tag_value: str = "",
    ) -> List[Artifact]:
        result: List[Artifact] = []
        for a in self._artifacts.values():
            if kind and a.kind != kind:
                continue
            if tag_key and tag_key not in a.tags:
                continue
            if tag_value and tag_key and a.tags.get(tag_key) != tag_value:
                continue
            result.append(a)
        return result

    def delete(self, name: str, *, version: str = "") -> int:
        keys = [
            k for k in self._artifacts
            if k[0] == name and (not version or k[1] == version)
        ]
        for k in keys:
            del self._artifacts[k]
        return len(keys)

    def exists(self, name: str, *, version: str = "") -> bool:
        if version:
            return (name, version) in self._artifacts
        return any(n == name for n, _v in self._artifacts)

    def gc(self, referenced: Set[str]) -> int:
        """Remove artifacts whose digest is not in *referenced*."""
        to_remove = [k for k, a in self._artifacts.items() if a.digest not in referenced]
        for k in to_remove:
            del self._artifacts[k]
        return len(to_remove)

    def __len__(self) -> int:
        return len(self._artifacts)

    def clear(self) -> None:
        self._artifacts.clear()

    def __iter__(self):
        return iter(self._artifacts.values())

    def __contains__(self, item) -> bool:
        if isinstance(item, str):
            if item.startswith("sha256:"):
                return any(a.digest == item for a in self._artifacts.values())
            return self.exists(item)
        if isinstance(item, Artifact):
            return any(a.digest == item.digest for a in self._artifacts.values())
        return False

    def count(self, *, kind: str = "") -> int:
        """Count artifacts, optionally filtered by kind."""
        if not kind:
            return len(self._artifacts)
        return sum(1 for a in self._artifacts.values() if a.kind == kind)


# ── Filesystem Store ────────────────────────────────────────────────────


class FilesystemArtifactStore(ArtifactStoreProtocol):
    """
    Persistent filesystem artifact store.

    Writes each artifact as a ``.aq.json`` file::

        <root>/
          <name>-<version>.aq.json
          ...
          _index.json            ← optional index for fast lookup

    File names are sanitised (``/`` → ``_``, ``:`` → ``_``).
    """

    __slots__ = ("root",)

    def __init__(self, root: str = "artifacts") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _safe_filename(name: str, version: str) -> str:
        safe = name.replace("/", "_").replace(":", "_").replace(" ", "_")
        return f"{safe}-{version}.aq.json"

    def _artifact_path(self, name: str, version: str) -> Path:
        return self.root / self._safe_filename(name, version)

    def _iter_files(self):
        """Yield all ``.aq.json`` files in the store directory."""
        for f in sorted(self.root.iterdir()):
            if f.is_file() and f.name.endswith(".aq.json"):
                yield f

    # ── CRUD ─────────────────────────────────────────────────────────

    def save(self, artifact: Artifact) -> str:
        path = self._artifact_path(artifact.name, artifact.version)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(artifact.to_json(), encoding="utf-8")
            tmp.replace(path)  # atomic on POSIX
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise
        logger.info("Saved artifact: %s → %s", artifact.qualified_name, path)
        return artifact.digest

    def load(self, name: str, *, version: str = "") -> Optional[Artifact]:
        if version:
            path = self._artifact_path(name, version)
            if not path.exists():
                return None
            return self._read(path)

        # No version — find latest by name prefix
        prefix = name.replace("/", "_").replace(":", "_").replace(" ", "_") + "-"
        matches: List[Artifact] = []
        for f in self._iter_files():
            if f.name.startswith(prefix):
                a = self._read(f)
                if a:
                    matches.append(a)
        return matches[-1] if matches else None

    def load_by_digest(self, digest: str) -> Optional[Artifact]:
        for f in self._iter_files():
            a = self._read(f)
            if a and a.digest == digest:
                return a
        return None

    def list_artifacts(
        self,
        *,
        kind: str = "",
        tag_key: str = "",
        tag_value: str = "",
    ) -> List[Artifact]:
        result: List[Artifact] = []
        for f in self._iter_files():
            a = self._read(f)
            if a is None:
                continue
            if kind and a.kind != kind:
                continue
            if tag_key and tag_key not in a.tags:
                continue
            if tag_value and tag_key and a.tags.get(tag_key) != tag_value:
                continue
            result.append(a)
        return result

    def delete(self, name: str, *, version: str = "") -> int:
        removed = 0
        if version:
            path = self._artifact_path(name, version)
            if path.exists():
                path.unlink()
                removed = 1
        else:
            prefix = name.replace("/", "_").replace(":", "_").replace(" ", "_") + "-"
            for f in list(self._iter_files()):
                if f.name.startswith(prefix):
                    f.unlink()
                    removed += 1
        return removed

    def exists(self, name: str, *, version: str = "") -> bool:
        if version:
            return self._artifact_path(name, version).exists()
        prefix = name.replace("/", "_").replace(":", "_").replace(" ", "_") + "-"
        return any(f.name.startswith(prefix) for f in self._iter_files())

    def gc(self, referenced: Set[str]) -> int:
        """Remove artifacts whose digest is not in *referenced*."""
        removed = 0
        for f in list(self._iter_files()):
            a = self._read(f)
            if a and a.digest not in referenced:
                f.unlink()
                removed += 1
                logger.info("GC removed: %s", f.name)
        return removed

    def export_bundle(
        self,
        names: List[str],
        output_path: str,
    ) -> str:
        """
        Export a subset of artifacts as a JSON bundle.

        Returns path to the bundle file.
        """
        from .builder import ArtifactBuilder

        items = []
        for name in names:
            a = self.load(name)
            if a:
                items.append(a.to_dict())

        bundle = (
            ArtifactBuilder("bundle", kind="bundle", version="1.0.0")
            .set_payload({"artifacts": items, "count": len(items)})
            .auto_provenance()
            .build()
        )

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(bundle.to_json(), encoding="utf-8")
        logger.info("Exported bundle: %d artifacts → %s", len(items), out)
        return str(out)

    # ── Internal ─────────────────────────────────────────────────────

    @staticmethod
    def _read(path: Path) -> Optional[Artifact]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Artifact.from_dict(data)
        except Exception as exc:
            logger.warning("Corrupt artifact file %s: %s", path, exc)
            return None

    def __len__(self) -> int:
        return sum(1 for _ in self._iter_files())

    def __iter__(self):
        for f in self._iter_files():
            a = self._read(f)
            if a is not None:
                yield a

    def __contains__(self, item) -> bool:
        if isinstance(item, str):
            if item.startswith("sha256:"):
                return self.load_by_digest(item) is not None
            return self.exists(item)
        if isinstance(item, Artifact):
            return self.load_by_digest(item.digest) is not None
        return False

    def count(self, *, kind: str = "") -> int:
        """Count artifacts, optionally filtered by kind."""
        if not kind:
            return len(self)
        return sum(1 for a in self if a.kind == kind)

    def import_bundle(self, bundle_path: str) -> int:
        """
        Import artifacts from a bundle file produced by ``export_bundle``.

        Returns:
            Number of artifacts imported.
        """
        path = Path(bundle_path)
        if not path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        payload = data.get("payload", {})
        items = payload.get("artifacts", []) if isinstance(payload, dict) else []
        imported = 0
        for item_dict in items:
            a = Artifact.from_dict(item_dict)
            self.save(a)
            imported += 1
        logger.info("Imported %d artifact(s) from %s", imported, path)
        return imported


# ── Convenience alias ───────────────────────────────────────────────────


def ArtifactStore(root: str = "artifacts") -> FilesystemArtifactStore:
    """
    Convenience constructor — returns a :class:`FilesystemArtifactStore`.

    Use ``MemoryArtifactStore()`` for tests.
    """
    return FilesystemArtifactStore(root)
