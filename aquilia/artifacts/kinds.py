"""
Typed Artifact Kinds — convenience subclasses with kind-specific helpers.

Each subclass sets ``kind`` automatically and adds domain-specific
payload accessors so consumers don't need to dig into raw dicts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .core import Artifact, ArtifactEnvelope
from .builder import ArtifactBuilder


# ── Helpers ─────────────────────────────────────────────────────────────


def _payload_get(artifact: Artifact, key: str, default: Any = None) -> Any:
    """Safely get a key from a dict payload."""
    if isinstance(artifact.payload, dict):
        return artifact.payload.get(key, default)
    return default


# ── Config Artifact ─────────────────────────────────────────────────────


class ConfigArtifact(Artifact):
    """
    Frozen configuration snapshot.

    Payload is the config dict (same as ``Config.to_dict()``).
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        config: Dict[str, Any],
        **metadata: Any,
    ) -> "ConfigArtifact":
        a = (
            ArtifactBuilder(name, kind="config", version=version)
            .set_payload(config)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def config(self) -> Dict[str, Any]:
        return self.payload if isinstance(self.payload, dict) else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


# ── Code Artifact ───────────────────────────────────────────────────────


class CodeArtifact(Artifact):
    """
    Compiled module / controller / service artifact.

    Payload contains module info, controllers, services, route_prefix, etc.
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        controllers: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        route_prefix: str = "/",
        fault_domain: str = "GENERIC",
        depends_on: Optional[List[str]] = None,
        **metadata: Any,
    ) -> "CodeArtifact":
        payload = {
            "type": "module",
            "route_prefix": route_prefix,
            "fault_domain": fault_domain,
            "depends_on": depends_on or [],
            "controllers": controllers or [],
            "services": services or [],
        }
        a = (
            ArtifactBuilder(name, kind="code", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def controllers(self) -> List[str]:
        return _payload_get(self, "controllers", [])

    @property
    def services(self) -> List[str]:
        return _payload_get(self, "services", [])

    @property
    def route_prefix(self) -> str:
        return _payload_get(self, "route_prefix", "/")

    @property
    def fault_domain(self) -> str:
        return _payload_get(self, "fault_domain", "GENERIC")

    @property
    def depends_on(self) -> List[str]:
        return _payload_get(self, "depends_on", [])


# ── Model Artifact ──────────────────────────────────────────────────────


class ModelArtifact(Artifact):
    """
    ML model artifact.

    Payload includes model metadata (framework, accuracy, entrypoint)
    plus file references to the actual model binaries.
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        framework: str = "custom",
        entrypoint: str = "",
        accuracy: float = 0.0,
        files: Optional[List[Dict[str, Any]]] = None,
        **metadata: Any,
    ) -> "ModelArtifact":
        payload = {
            "type": "model",
            "framework": framework,
            "entrypoint": entrypoint,
            "accuracy": accuracy,
            "files": files or [],
        }
        a = (
            ArtifactBuilder(name, kind="model", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def framework(self) -> str:
        return _payload_get(self, "framework", "custom")

    @property
    def entrypoint(self) -> str:
        return _payload_get(self, "entrypoint", "")

    @property
    def accuracy(self) -> float:
        return _payload_get(self, "accuracy", 0.0)

    @property
    def files(self) -> List[Dict[str, Any]]:
        return _payload_get(self, "files", [])


# ── Template Artifact ───────────────────────────────────────────────────


class TemplateArtifact(Artifact):
    """
    Compiled template artifact.

    Payload contains template names, source hashes, compilation metadata.
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        templates: Optional[Dict[str, Any]] = None,
        **metadata: Any,
    ) -> "TemplateArtifact":
        payload = {
            "type": "templates",
            "templates": templates or {},
            "count": len(templates or {}),
        }
        a = (
            ArtifactBuilder(name, kind="template", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def templates(self) -> Dict[str, Any]:
        return _payload_get(self, "templates", {})

    @property
    def template_count(self) -> int:
        return _payload_get(self, "count", 0)


# ── Migration Artifact ──────────────────────────────────────────────────


class MigrationArtifact(Artifact):
    """
    Database migration checkpoint artifact.

    Records applied migrations, current head, and schema hash.
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        migrations_applied: Optional[List[str]] = None,
        head: str = "",
        schema_hash: str = "",
        **metadata: Any,
    ) -> "MigrationArtifact":
        payload = {
            "type": "migration",
            "migrations_applied": migrations_applied or [],
            "head": head,
            "schema_hash": schema_hash,
        }
        a = (
            ArtifactBuilder(name, kind="migration", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def head(self) -> str:
        return _payload_get(self, "head", "")

    @property
    def migrations_applied(self) -> List[str]:
        return _payload_get(self, "migrations_applied", [])

    @property
    def schema_hash(self) -> str:
        return _payload_get(self, "schema_hash", "")


# ── Registry Artifact ───────────────────────────────────────────────────


class RegistryArtifact(Artifact):
    """Module registry catalog artifact."""

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        modules: Optional[List[Dict[str, Any]]] = None,
        **metadata: Any,
    ) -> "RegistryArtifact":
        payload = {"type": "registry", "modules": modules or []}
        a = (
            ArtifactBuilder(name, kind="registry", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def modules(self) -> List[Dict[str, Any]]:
        return _payload_get(self, "modules", [])


# ── Route Artifact ──────────────────────────────────────────────────────


class RouteArtifact(Artifact):
    """Compiled routing table artifact."""

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        routes: Optional[List[Dict[str, Any]]] = None,
        **metadata: Any,
    ) -> "RouteArtifact":
        payload = {"type": "routes", "routes": routes or []}
        a = (
            ArtifactBuilder(name, kind="route", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def routes(self) -> List[Dict[str, Any]]:
        return _payload_get(self, "routes", [])


# ── DI Graph Artifact ──────────────────────────────────────────────────


class DIGraphArtifact(Artifact):
    """Compiled dependency injection graph artifact."""

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        providers: Optional[List[Dict[str, Any]]] = None,
        **metadata: Any,
    ) -> "DIGraphArtifact":
        payload = {"type": "di_graph", "providers": providers or []}
        a = (
            ArtifactBuilder(name, kind="di_graph", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def providers(self) -> List[Dict[str, Any]]:
        return _payload_get(self, "providers", [])


# ── Bundle Artifact ─────────────────────────────────────────────────────


class BundleArtifact(Artifact):
    """
    Artifact bundle — a container that holds multiple artifacts.

    Used for export/import, deployment snapshots, and backup.
    """

    @classmethod
    def build(
        cls,
        name: str,
        version: str,
        *,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        **metadata: Any,
    ) -> "BundleArtifact":
        items = artifacts or []
        payload = {"type": "bundle", "artifacts": items, "count": len(items)}
        a = (
            ArtifactBuilder(name, kind="bundle", version=version)
            .set_payload(payload)
            .set_metadata(**metadata)
            .auto_provenance()
            .build()
        )
        return cls(a.envelope)

    @property
    def artifacts(self) -> List[Dict[str, Any]]:
        return _payload_get(self, "artifacts", [])

    @property
    def artifact_count(self) -> int:
        return _payload_get(self, "count", 0)

    def unpack(self) -> List[Artifact]:
        """Deserialise contained artifacts."""
        return [Artifact.from_dict(d) for d in self.artifacts]


# ── Registry — typed deserialization support ────────────────────────────

from .core import register_artifact_kind  # noqa: E402

register_artifact_kind("config", ConfigArtifact)
register_artifact_kind("code", CodeArtifact)
register_artifact_kind("model", ModelArtifact)
register_artifact_kind("template", TemplateArtifact)
register_artifact_kind("migration", MigrationArtifact)
register_artifact_kind("registry", RegistryArtifact)
register_artifact_kind("route", RouteArtifact)
register_artifact_kind("di_graph", DIGraphArtifact)
register_artifact_kind("bundle", BundleArtifact)
