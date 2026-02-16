"""
Aquilia Artifacts — Unified artifact system for the framework.

A first-class, content-addressed artifact layer that provides:

- **Envelope format** — every artifact is a typed, versioned, hashed container
- **Pluggable storage** — filesystem, memory, content-addressed (``ArtifactStore``)
- **Builder API** — fluent ``ArtifactBuilder`` for constructing artifacts
- **Reader / inspector** — ``ArtifactReader`` for loading and verifying
- **Typed kinds** — ``CodeArtifact``, ``ModelArtifact``, ``ConfigArtifact``, etc.
- **Provenance** — who built it, when, from what source, git sha
- **Integrity** — SHA-256 content hashing, optional signing
- **GC** — garbage-collect unreferenced artifacts

Quick start::

    from aquilia.artifacts import ArtifactBuilder, ArtifactStore, ArtifactReader

    # Build
    artifact = (
        ArtifactBuilder("my-config", kind="config", version="1.0.0")
        .set_payload({"database": {"url": "sqlite:///db.sqlite3"}})
        .tag("env", "production")
        .build()
    )

    # Store
    store = ArtifactStore("./artifacts")
    store.save(artifact)

    # Read
    reader = ArtifactReader(store)
    loaded = reader.load("my-config", version="1.0.0")

    # Inspect
    print(loaded.digest)      # sha256:abc123...
    print(loaded.metadata)    # {'env': 'production'}
"""

__version__ = "1.0.0"

from .core import (
    Artifact,
    ArtifactEnvelope,
    ArtifactKind,
    ArtifactProvenance,
    ArtifactIntegrity,
    register_artifact_kind,
)
from .builder import ArtifactBuilder
from .store import ArtifactStore, MemoryArtifactStore, FilesystemArtifactStore
from .reader import ArtifactReader
from .kinds import (
    CodeArtifact,
    ModelArtifact,
    ConfigArtifact,
    TemplateArtifact,
    MigrationArtifact,
    RegistryArtifact,
    RouteArtifact,
    DIGraphArtifact,
    BundleArtifact,
)

__all__ = [
    # Core
    "Artifact",
    "ArtifactEnvelope",
    "ArtifactKind",
    "ArtifactProvenance",
    "ArtifactIntegrity",
    "register_artifact_kind",
    # Builder
    "ArtifactBuilder",
    # Store
    "ArtifactStore",
    "MemoryArtifactStore",
    "FilesystemArtifactStore",
    # Reader
    "ArtifactReader",
    # Typed Kinds
    "CodeArtifact",
    "ModelArtifact",
    "ConfigArtifact",
    "TemplateArtifact",
    "MigrationArtifact",
    "RegistryArtifact",
    "RouteArtifact",
    "DIGraphArtifact",
    "BundleArtifact",
]
