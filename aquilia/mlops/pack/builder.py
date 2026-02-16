"""
Modelpack Builder — Creates ``.aquilia`` archive artifacts.

A modelpack is a TAR.GZ archive containing:
- ``model/``         — binary blobs (model.pt, model.onnx, …)
- ``manifest.json``  — model metadata and inference signature
- ``env.lock``       — pip/conda lock file
- ``provenance.json``— git sha, dataset checksum
- ``signature.sig``  — optional artifact signature (GPG/RSA)
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .._types import (
    BlobRef,
    Framework,
    ModelpackManifest,
    Provenance,
    TensorSpec,
)
from ..faults import (
    PackBuildFault,
    PackIntegrityFault,
)
from .content_store import ContentStore

logger = logging.getLogger("aquilia.mlops.pack")


def _sha256_file(path: Union[str, Path]) -> str:
    """Compute SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class ModelpackBuilder:
    """
    Builds a modelpack archive from local files.

    Usage::

        builder = ModelpackBuilder(name="my-model", version="v1.0.0")
        builder.add_model("out/model.pt", framework="pytorch")
        builder.add_env_lock("requirements.txt")
        builder.set_signature(
            inputs=[TensorSpec("x", "float32", [None, 64])],
            outputs=[TensorSpec("y", "float32", [None, 10])],
        )
        pack_path = await builder.save("./dist")
    """

    def __init__(
        self,
        name: str,
        version: str,
        framework: str = "custom",
        signed_by: str = "",
    ):
        self.name = name
        self.version = version
        self.framework = framework
        self.signed_by = signed_by

        self._model_files: List[Dict[str, Any]] = []
        self._env_lock_path: Optional[str] = None
        self._provenance = Provenance()
        self._inputs: List[TensorSpec] = []
        self._outputs: List[TensorSpec] = []
        self._metadata: Dict[str, Any] = {}
        self._entrypoint: str = ""

    # ── Builder API ─────────────────────────────────────────────────────

    def add_model(
        self,
        path: str,
        *,
        framework: Optional[str] = None,
        entrypoint: bool = True,
    ) -> "ModelpackBuilder":
        """Add a model file to the pack."""
        if framework:
            self.framework = framework
        self._model_files.append({"path": path, "entrypoint": entrypoint})
        if entrypoint:
            self._entrypoint = Path(path).name
        return self

    def add_file(self, path: str) -> "ModelpackBuilder":
        """Add an auxiliary file to the pack."""
        self._model_files.append({"path": path, "entrypoint": False})
        return self

    def add_env_lock(self, path: str) -> "ModelpackBuilder":
        """Set the environment lock file."""
        self._env_lock_path = path
        return self

    def set_signature(
        self,
        inputs: List[TensorSpec],
        outputs: List[TensorSpec],
    ) -> "ModelpackBuilder":
        """Set the inference signature."""
        self._inputs = inputs
        self._outputs = outputs
        return self

    def set_provenance(
        self,
        git_sha: str = "",
        dataset_snapshot: str = "",
        dockerfile: str = "",
    ) -> "ModelpackBuilder":
        """Set provenance metadata."""
        self._provenance = Provenance(
            git_sha=git_sha,
            dataset_snapshot=dataset_snapshot,
            dockerfile=dockerfile,
            build_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return self

    def set_metadata(self, **kwargs: Any) -> "ModelpackBuilder":
        """Set arbitrary metadata key-value pairs."""
        self._metadata.update(kwargs)
        return self

    # ── Build ───────────────────────────────────────────────────────────

    async def save(
        self,
        output_dir: str = ".",
        *,
        content_store: Optional[ContentStore] = None,
        sign_key: Optional[str] = None,
    ) -> str:
        """
        Build the ``.aquilia`` archive and return its path.

        Args:
            output_dir: Directory to write the archive.
            content_store: Optional content store to index blobs.
            sign_key: Optional GPG key ID for signing.

        Returns:
            Absolute path to the created ``.aquilia`` file.
        """
        if not self._model_files:
            raise PackBuildFault("No model files added. Call add_model() before save().")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        blobs: List[BlobRef] = []

        # Compute digests for all model files
        for entry in self._model_files:
            fpath = Path(entry["path"])
            if not fpath.exists():
                raise PackBuildFault(
                    f"Model file not found: {fpath}",
                    metadata={"path": str(fpath)},
                )
            digest = _sha256_file(fpath)
            size = fpath.stat().st_size
            blobs.append(BlobRef(path=fpath.name, digest=digest, size=size))

            # Store in content store if provided
            if content_store:
                data = fpath.read_bytes()
                await content_store.store(digest, data)

        # Build manifest
        manifest = ModelpackManifest(
            name=self.name,
            version=self.version,
            framework=self.framework,
            entrypoint=self._entrypoint,
            inputs=self._inputs,
            outputs=self._outputs,
            env_lock=Path(self._env_lock_path).name if self._env_lock_path else "env.lock",
            provenance=self._provenance,
            blobs=blobs,
            created_at=datetime.now(timezone.utc).isoformat(),
            signed_by=self.signed_by,
            metadata=self._metadata,
        )

        # Create archive
        safe_name = self.name.replace("/", "_").replace(":", "_")
        archive_name = f"{safe_name}-{self.version}.aquilia"
        archive_path = output_path / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            # Add model files under model/
            for entry in self._model_files:
                fpath = Path(entry["path"])
                tar.add(str(fpath), arcname=f"model/{fpath.name}")

            # Add manifest.json
            manifest_data = json.dumps(manifest.to_dict(), indent=2).encode()
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_data)
            info.mtime = int(time.time())
            tar.addfile(info, io.BytesIO(manifest_data))

            # Add env.lock if provided
            if self._env_lock_path and Path(self._env_lock_path).exists():
                tar.add(self._env_lock_path, arcname="env.lock")

            # Add provenance.json
            prov_data = json.dumps(self._provenance.to_dict(), indent=2).encode()
            pinfo = tarfile.TarInfo(name="provenance.json")
            pinfo.size = len(prov_data)
            pinfo.mtime = int(time.time())
            tar.addfile(pinfo, io.BytesIO(prov_data))

        logger.info("Built modelpack: %s (%d bytes)", archive_path, archive_path.stat().st_size)

        # ── Produce a typed ModelArtifact alongside the archive ─────────
        try:
            from aquilia.artifacts import ModelArtifact, FilesystemArtifactStore

            file_refs = [
                {"path": b.path, "digest": b.digest, "size": b.size}
                for b in blobs
            ]
            model_artifact = ModelArtifact.build(
                name=self.name,
                version=self.version,
                framework=self.framework,
                entrypoint=self._entrypoint,
                accuracy=self._metadata.get("accuracy", 0.0),
                files=file_refs,
                archive_path=str(archive_path.resolve()),
                signed_by=self.signed_by,
            )
            artifact_dir = output_path / ".aq"
            store = FilesystemArtifactStore(str(artifact_dir))
            store.save(model_artifact)
            logger.info(
                "ModelArtifact written: %s [%s]",
                model_artifact.qualified_name,
                model_artifact.digest,
            )
        except Exception as exc:
            logger.debug("Skipped ModelArtifact creation: %s", exc)

        return str(archive_path.resolve())

    # ── Unpack ──────────────────────────────────────────────────────────

    @staticmethod
    async def unpack(archive_path: str, output_dir: str = ".") -> ModelpackManifest:
        """
        Unpack a ``.aquilia`` archive and return its manifest.

        Args:
            archive_path: Path to the ``.aquilia`` file.
            output_dir: Directory to extract into.

        Returns:
            Parsed ``ModelpackManifest``.
        """
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=str(output), filter="data")

        manifest_path = output / "manifest.json"
        if not manifest_path.exists():
            raise PackIntegrityFault(
                f"manifest.json not found in {archive_path}",
                metadata={"archive": str(archive_path)},
            )

        with open(manifest_path) as f:
            data = json.load(f)

        manifest = ModelpackManifest.from_dict(data)

        # Verify blob digests
        for blob in manifest.blobs:
            blob_path = output / "model" / blob.path
            if blob_path.exists():
                actual = _sha256_file(blob_path)
                if actual != blob.digest:
                    raise PackIntegrityFault(
                        f"Blob integrity check failed for {blob.path}: "
                        f"expected {blob.digest}, got {actual}",
                        metadata={
                            "blob": blob.path,
                            "expected": blob.digest,
                            "actual": actual,
                        },
                    )

        logger.info("Unpacked modelpack: %s v%s", manifest.name, manifest.version)
        return manifest

    @staticmethod
    async def inspect(archive_path: str) -> ModelpackManifest:
        """Read manifest from archive without full extraction."""
        with tarfile.open(archive_path, "r:gz") as tar:
            member = tar.getmember("manifest.json")
            f = tar.extractfile(member)
            if f is None:
                raise PackIntegrityFault(
                    "manifest.json not readable in archive",
                    metadata={"archive": str(archive_path)},
                )
            data = json.load(f)
        return ModelpackManifest.from_dict(data)
