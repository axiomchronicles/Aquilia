"""
Artifact Core — the foundational types for Aquilia's artifact system.

Every artifact in Aquilia (compiled manifests, modelpacks, templates,
config snapshots, migration checkpoints) shares the same envelope format:

.. code-block:: json

    {
        "__format__": "aquilia-artifact",
        "schema_version": "1.0",
        "kind": "config",
        "name": "my-app-config",
        "version": "1.2.0",
        "integrity": {"algorithm": "sha256", "digest": "abc123..."},
        "provenance": {"created_at": "...", "created_by": "...", "git_sha": "..."},
        "metadata": {...},
        "payload": {...}
    }
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

# Forward-declared registry: kind-string → Artifact subclass.
# Populated by ``register_artifact_kind()`` in kinds.py.
_KIND_REGISTRY: Dict[str, Type["Artifact"]] = {}


# ── Enums ───────────────────────────────────────────────────────────────


class ArtifactKind(str, Enum):
    """Standard artifact kinds recognised by the framework."""

    CONFIG = "config"
    CODE = "code"
    MODEL = "model"
    TEMPLATE = "template"
    MIGRATION = "migration"
    REGISTRY = "registry"
    ROUTE = "route"
    DI_GRAPH = "di_graph"
    MODULE = "module"
    WORKSPACE = "workspace"
    BUNDLE = "bundle"
    CUSTOM = "custom"


# ── Value Objects ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArtifactIntegrity:
    """Content-addressed integrity proof."""

    algorithm: str = "sha256"
    digest: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"algorithm": self.algorithm, "digest": self.digest}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArtifactIntegrity":
        return cls(algorithm=d.get("algorithm", "sha256"), digest=d.get("digest", ""))

    @classmethod
    def compute(cls, data: bytes, algorithm: str = "sha256") -> "ArtifactIntegrity":
        """Compute integrity from raw bytes."""
        h = hashlib.new(algorithm)
        h.update(data)
        return cls(algorithm=algorithm, digest=h.hexdigest())

    def verify(self, data: bytes) -> bool:
        """Verify that *data* matches this integrity proof."""
        expected = self.__class__.compute(data, self.algorithm)
        return expected.digest == self.digest


@dataclass(frozen=True)
class ArtifactProvenance:
    """Where and when the artifact was produced."""

    created_at: str = ""
    created_by: str = ""
    git_sha: str = ""
    source_path: str = ""
    hostname: str = ""
    build_tool: str = "aquilia"

    def to_dict(self) -> Dict[str, str]:
        return {
            "created_at": self.created_at,
            "created_by": self.created_by,
            "git_sha": self.git_sha,
            "source_path": self.source_path,
            "hostname": self.hostname,
            "build_tool": self.build_tool,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArtifactProvenance":
        return cls(
            created_at=d.get("created_at", ""),
            created_by=d.get("created_by", ""),
            git_sha=d.get("git_sha", ""),
            source_path=d.get("source_path", ""),
            hostname=d.get("hostname", ""),
            build_tool=d.get("build_tool", "aquilia"),
        )

    @classmethod
    def auto(cls, source_path: str = "") -> "ArtifactProvenance":
        """Auto-populate with current env info."""
        import getpass
        import socket

        git_sha = ""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                git_sha = result.stdout.strip()
        except Exception:
            pass

        return cls(
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by=getpass.getuser(),
            git_sha=git_sha,
            source_path=source_path,
            hostname=socket.gethostname(),
        )


# ── Envelope ────────────────────────────────────────────────────────────


@dataclass
class ArtifactEnvelope:
    """
    The outer envelope that wraps every artifact's serialised form.

    This is what gets written to disk / transmitted over the wire.
    """

    format: str = "aquilia-artifact"
    schema_version: str = "1.0"
    kind: str = ""
    name: str = ""
    version: str = ""
    integrity: ArtifactIntegrity = field(default_factory=ArtifactIntegrity)
    provenance: ArtifactProvenance = field(default_factory=ArtifactProvenance)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    payload: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "__format__": self.format,
            "schema_version": self.schema_version,
            "kind": self.kind,
            "name": self.name,
            "version": self.version,
            "integrity": self.integrity.to_dict(),
            "provenance": self.provenance.to_dict(),
            "metadata": self.metadata,
            "tags": self.tags,
            "payload": self.payload,
        }

    @property
    def is_known_kind(self) -> bool:
        """True when *kind* matches a standard :class:`ArtifactKind`."""
        try:
            ArtifactKind(self.kind)
            return True
        except ValueError:
            return False

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArtifactEnvelope":
        return cls(
            format=d.get("__format__", "aquilia-artifact"),
            schema_version=d.get("schema_version", "1.0"),
            kind=d.get("kind", ""),
            name=d.get("name", ""),
            version=d.get("version", ""),
            integrity=ArtifactIntegrity.from_dict(d.get("integrity", {})),
            provenance=ArtifactProvenance.from_dict(d.get("provenance", {})),
            metadata=d.get("metadata", {}),
            tags=d.get("tags", {}),
            payload=d.get("payload"),
        )


# ── Artifact ────────────────────────────────────────────────────────────


class Artifact:
    """
    First-class Aquilia artifact.

    An artifact is a typed, versioned, content-addressed unit of build
    output.  It carries its own integrity proof, provenance, metadata,
    and payload.

    Subclasses (``ModelArtifact``, ``ConfigArtifact``, …) add
    kind-specific convenience methods but all share the same envelope.
    """

    __slots__ = ("_envelope",)

    def __init__(self, envelope: ArtifactEnvelope) -> None:
        self._envelope = envelope

    # ── Identity ─────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._envelope.name

    @property
    def version(self) -> str:
        return self._envelope.version

    @property
    def kind(self) -> str:
        return self._envelope.kind

    @property
    def qualified_name(self) -> str:
        """``name:version`` identifier."""
        return f"{self.name}:{self.version}"

    # ── Integrity ────────────────────────────────────────────────────

    @property
    def digest(self) -> str:
        """Full digest string, e.g. ``sha256:abc123…``."""
        i = self._envelope.integrity
        return f"{i.algorithm}:{i.digest}" if i.digest else ""

    @property
    def integrity(self) -> ArtifactIntegrity:
        return self._envelope.integrity

    def verify(self) -> bool:
        """Re-compute digest from payload and compare."""
        raw = json.dumps(
            self._envelope.payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return self._envelope.integrity.verify(raw)

    # ── Provenance ───────────────────────────────────────────────────

    @property
    def provenance(self) -> ArtifactProvenance:
        return self._envelope.provenance

    @property
    def created_at(self) -> str:
        return self._envelope.provenance.created_at

    @property
    def age_seconds(self) -> float:
        """Seconds since the artifact was created (0.0 if unknown)."""
        if not self.created_at:
            return 0.0
        try:
            ts = datetime.fromisoformat(self.created_at)
            return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())
        except Exception:
            return 0.0

    # ── Metadata ─────────────────────────────────────────────────────

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._envelope.metadata

    @property
    def tags(self) -> Dict[str, str]:
        return self._envelope.tags

    # ── Payload ──────────────────────────────────────────────────────

    @property
    def payload(self) -> Any:
        return self._envelope.payload

    @property
    def envelope(self) -> ArtifactEnvelope:
        return self._envelope

    @property
    def size_bytes(self) -> int:
        """Approximate serialised size of the payload in bytes."""
        if self._envelope.payload is None:
            return 0
        try:
            return len(json.dumps(self._envelope.payload, default=str).encode("utf-8"))
        except Exception:
            return 0

    # ── Evolve ───────────────────────────────────────────────────────

    def evolve(self, *, version: str = "", **payload_overrides: Any) -> "Artifact":
        """
        Create a **new** artifact derived from this one.

        The provenance chain is preserved via a ``derived_from`` tag.
        Payload keys in *payload_overrides* are merged into a copy of
        the current payload (dict-only).

        ::

            v2 = v1.evolve(version="2.0.0", accuracy=0.98)
        """
        from .builder import ArtifactBuilder

        new_version = version or self.version
        builder = (
            ArtifactBuilder(self.name, kind=self.kind, version=new_version)
            .auto_provenance(self.provenance.source_path)
            .tag("derived_from", self.digest)
        )
        # Copy existing tags (except derived_from which we just set)
        for k, v in self.tags.items():
            if k != "derived_from":
                builder.tag(k, v)
        # Copy metadata
        builder.set_metadata(**self.metadata)

        # Build payload
        if isinstance(self.payload, dict):
            new_payload = {**self.payload, **payload_overrides}
        else:
            new_payload = self.payload
        builder.set_payload(new_payload)

        return builder.build()

    # ── Serialisation ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return self._envelope.to_dict()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Artifact":
        """Deserialise and return the correct typed subclass when possible."""
        envelope = ArtifactEnvelope.from_dict(d)
        # If called on Artifact base *and* a subclass is registered, use it
        if cls is Artifact:
            sub = _KIND_REGISTRY.get(envelope.kind)
            if sub is not None:
                return sub(envelope)
        return cls(envelope)

    @classmethod
    def from_json(cls, raw: str) -> "Artifact":
        return cls.from_dict(json.loads(raw))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Artifact":
        return cls.from_json(data.decode("utf-8"))

    # ── Dunder ───────────────────────────────────────────────────────

    def __repr__(self) -> str:
        digest_short = self.digest[:24] + "…" if len(self.digest) > 24 else (self.digest or "<none>")
        return f"<Artifact {self.kind}:{self.qualified_name} digest={digest_short}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Artifact):
            return NotImplemented
        return self.digest == other.digest and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.digest)

    def __lt__(self, other: object) -> bool:
        """Sort by (name, version) for deterministic ordering."""
        if not isinstance(other, Artifact):
            return NotImplemented
        return (self.name, self.version) < (other.name, other.version)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Artifact):
            return NotImplemented
        return (self.name, self.version) <= (other.name, other.version)


# ── Kind Registration ───────────────────────────────────────────────────


def register_artifact_kind(kind: str, cls: Type[Artifact]) -> None:
    """Register a typed subclass so ``Artifact.from_dict`` auto-resolves."""
    _KIND_REGISTRY[kind] = cls
