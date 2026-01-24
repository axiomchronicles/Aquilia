"""
AquilAuth - Crous Artifacts

Signed configuration artifacts for keys, policies, and audit logs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from .tokens import KeyDescriptor


# ============================================================================
# Artifact Types
# ============================================================================


@dataclass
class CrousArtifact:
    """Base crous artifact."""

    artifact_type: str
    artifact_id: str
    version: int
    created_at: datetime
    created_by: str
    signature: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    def compute_hash(self) -> str:
        """Compute SHA256 hash of artifact (for signing)."""
        # Create canonical representation
        data = self.to_dict()
        data.pop("signature", None)  # Exclude signature from hash

        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class KeyArtifact(CrousArtifact):
    """Cryptographic key artifact."""

    key_descriptor: KeyDescriptor

    def __init__(
        self,
        artifact_id: str,
        key_descriptor: KeyDescriptor,
        created_by: str,
        version: int = 1,
    ):
        super().__init__(
            artifact_type="auth_key",
            artifact_id=artifact_id,
            version=version,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.key_descriptor = key_descriptor

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["key_descriptor"] = self.key_descriptor.to_dict()
        return data


@dataclass
class PolicyArtifact(CrousArtifact):
    """Authorization policy artifact."""

    policy_id: str
    policy_data: dict[str, Any]

    def __init__(
        self,
        artifact_id: str,
        policy_id: str,
        policy_data: dict[str, Any],
        created_by: str,
        version: int = 1,
    ):
        super().__init__(
            artifact_type="auth_policy",
            artifact_id=artifact_id,
            version=version,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.policy_id = policy_id
        self.policy_data = policy_data

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["policy_id"] = self.policy_id
        data["policy_data"] = self.policy_data
        return data


@dataclass
class AuditEventArtifact(CrousArtifact):
    """Audit event artifact."""

    event_type: str
    identity_id: str | None
    resource: str | None
    action: str | None
    result: str
    details: dict[str, Any]

    def __init__(
        self,
        artifact_id: str,
        event_type: str,
        result: str,
        created_by: str,
        identity_id: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        version: int = 1,
    ):
        super().__init__(
            artifact_type="audit_event",
            artifact_id=artifact_id,
            version=version,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.event_type = event_type
        self.identity_id = identity_id
        self.resource = resource
        self.action = action
        self.result = result
        self.details = details or {}


# ============================================================================
# Artifact Signer
# ============================================================================


class ArtifactSigner:
    """Signs and verifies crous artifacts."""

    def __init__(self, signing_key: KeyDescriptor):
        """
        Initialize artifact signer.

        Args:
            signing_key: Key descriptor for signing
        """
        self.signing_key = signing_key

    def sign_artifact(self, artifact: CrousArtifact) -> str:
        """
        Sign artifact.

        Args:
            artifact: Artifact to sign

        Returns:
            Base64-encoded signature
        """
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        import base64

        # Compute artifact hash
        artifact_hash = artifact.compute_hash()

        # Load private key
        private_key = serialization.load_pem_private_key(
            self.signing_key.private_key_pem.encode(),
            password=None,
        )

        # Sign hash
        if isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                artifact_hash.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported key type: {type(private_key)}")

        # Encode signature
        return base64.b64encode(signature).decode()

    def verify_artifact(
        self, artifact: CrousArtifact, signature: str
    ) -> bool:
        """
        Verify artifact signature.

        Args:
            artifact: Artifact to verify
            signature: Base64-encoded signature

        Returns:
            True if signature valid
        """
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.exceptions import InvalidSignature
        import base64

        try:
            # Compute artifact hash
            artifact_hash = artifact.compute_hash()

            # Load public key
            public_key = serialization.load_pem_public_key(
                self.signing_key.public_key_pem.encode()
            )

            # Decode signature
            sig_bytes = base64.b64decode(signature)

            # Verify signature
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    sig_bytes,
                    artifact_hash.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
            else:
                raise ValueError(f"Unsupported key type: {type(public_key)}")

            return True

        except InvalidSignature:
            return False
        except Exception:
            return False


# ============================================================================
# Artifact Store
# ============================================================================


class MemoryArtifactStore:
    """In-memory artifact store for development/testing."""

    def __init__(self):
        self._artifacts: dict[str, CrousArtifact] = {}

    async def save_artifact(self, artifact: CrousArtifact) -> None:
        """Save artifact."""
        self._artifacts[artifact.artifact_id] = artifact

    async def get_artifact(self, artifact_id: str) -> CrousArtifact | None:
        """Get artifact by ID."""
        return self._artifacts.get(artifact_id)

    async def list_artifacts(
        self, artifact_type: str | None = None
    ) -> list[CrousArtifact]:
        """List artifacts by type."""
        artifacts = list(self._artifacts.values())

        if artifact_type:
            artifacts = [
                a for a in artifacts if a.artifact_type == artifact_type
            ]

        return artifacts


# ============================================================================
# Audit Logger
# ============================================================================


class AuditLogger:
    """Audit event logger with crous artifact integration."""

    def __init__(
        self,
        artifact_store: MemoryArtifactStore,
        signer: ArtifactSigner | None = None,
    ):
        """
        Initialize audit logger.

        Args:
            artifact_store: Artifact storage
            signer: Artifact signer (optional)
        """
        self.artifact_store = artifact_store
        self.signer = signer

    async def log_event(
        self,
        event_type: str,
        result: str,
        identity_id: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEventArtifact:
        """
        Log audit event.

        Args:
            event_type: Event type (auth_login, auth_logout, etc.)
            result: Result (success, failure, denied)
            identity_id: Identity performing action
            resource: Resource being accessed
            action: Action being performed
            details: Additional event details

        Returns:
            Created audit event artifact
        """
        import secrets

        # Create artifact
        artifact = AuditEventArtifact(
            artifact_id=f"audit_{secrets.token_hex(16)}",
            event_type=event_type,
            result=result,
            created_by=identity_id or "system",
            identity_id=identity_id,
            resource=resource,
            action=action,
            details=details,
        )

        # Sign artifact
        if self.signer:
            artifact.signature = self.signer.sign_artifact(artifact)

        # Save artifact
        await self.artifact_store.save_artifact(artifact)

        return artifact

    async def query_events(
        self,
        event_type: str | None = None,
        identity_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEventArtifact]:
        """
        Query audit events.

        Args:
            event_type: Filter by event type
            identity_id: Filter by identity
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            List of matching audit events
        """
        artifacts = await self.artifact_store.list_artifacts("audit_event")

        # Filter
        results = []
        for artifact in artifacts:
            if not isinstance(artifact, AuditEventArtifact):
                continue

            if event_type and artifact.event_type != event_type:
                continue

            if identity_id and artifact.identity_id != identity_id:
                continue

            if start_time and artifact.created_at < start_time:
                continue

            if end_time and artifact.created_at > end_time:
                continue

            results.append(artifact)

        return results
