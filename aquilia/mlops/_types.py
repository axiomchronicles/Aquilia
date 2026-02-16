"""
Aquilia MLOps Platform — Shared type definitions.

All protocol classes, enums, TypedDicts and dataclasses shared
across sub-packages live here to avoid circular imports.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)


# ── Enums ──────────────────────────────────────────────────────────────────

class Framework(str, Enum):
    """Supported ML frameworks."""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    ONNX = "onnx"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CUSTOM = "custom"


class RuntimeKind(str, Enum):
    """Available runtime backends."""
    PYTHON = "python"
    ONNXRUNTIME = "onnxruntime"
    TRITON = "triton"
    TORCHSERVE = "torchserve"
    BENTOML = "bentoml"


class QuantizePreset(str, Enum):
    """Quantization presets."""
    MOBILE = "mobile"       # int8, aggressive
    EDGE = "edge"           # int8, balanced
    FP16 = "fp16"           # float16
    INT8 = "int8"           # int8, dynamic
    DYNAMIC = "dynamic"     # dynamic quantization


class ExportTarget(str, Enum):
    """Edge export targets."""
    TFLITE = "tflite"
    COREML = "coreml"
    ONNX_QUANTIZED = "onnx-quantized"
    TENSORRT = "tensorrt"
    TVM = "tvm"


class BatchingStrategy(str, Enum):
    """Batching strategy modes."""
    SIZE = "size"
    TIME = "time"
    HYBRID = "hybrid"


class RolloutStrategy(str, Enum):
    """Release rollout strategies."""
    CANARY = "canary"
    AB_TEST = "ab_test"
    SHADOW = "shadow"
    BLUE_GREEN = "blue_green"


class DriftMethod(str, Enum):
    """Drift detection methods."""
    PSI = "psi"
    KS_TEST = "ks_test"
    DISTRIBUTION = "distribution"


# ── Data Classes ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TensorSpec:
    """Describes a single tensor in the inference signature."""
    name: str
    dtype: str          # e.g. "float32", "int64"
    shape: List[Any]    # e.g. [None, 64] — None means dynamic

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "dtype": self.dtype, "shape": self.shape}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TensorSpec":
        return cls(name=d["name"], dtype=d["dtype"], shape=d["shape"])


@dataclass(frozen=True)
class BlobRef:
    """Reference to a blob inside a modelpack."""
    path: str
    digest: str     # "sha256:..."
    size: int       # bytes

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "digest": self.digest, "size": self.size}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BlobRef":
        return cls(path=d["path"], digest=d["digest"], size=d["size"])


@dataclass(slots=True)
class Provenance:
    """Provenance metadata for reproducibility."""
    git_sha: str = ""
    dataset_snapshot: str = ""
    dockerfile: str = ""
    build_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "git_sha": self.git_sha,
            "dataset_snapshot": self.dataset_snapshot,
            "dockerfile": self.dockerfile,
            "build_timestamp": self.build_timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Provenance":
        return cls(**{k: d.get(k, "") for k in ("git_sha", "dataset_snapshot", "dockerfile", "build_timestamp")})


@dataclass(slots=True)
class ModelpackManifest:
    """
    Complete manifest for a modelpack artifact.

    This is the authoritative schema for ``manifest.json`` inside
    every ``.aquilia`` archive.
    """
    name: str
    version: str
    framework: str
    entrypoint: str
    inputs: List[TensorSpec] = field(default_factory=list)
    outputs: List[TensorSpec] = field(default_factory=list)
    env_lock: str = "env.lock"
    provenance: Provenance = field(default_factory=Provenance)
    blobs: List[BlobRef] = field(default_factory=list)
    created_at: str = ""
    signed_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "framework": self.framework,
            "entrypoint": self.entrypoint,
            "inference_signature": {
                "inputs": [t.to_dict() for t in self.inputs],
                "outputs": [t.to_dict() for t in self.outputs],
            },
            "env_lock": self.env_lock,
            "provenance": self.provenance.to_dict(),
            "blobs": [b.to_dict() for b in self.blobs],
            "created_at": self.created_at,
            "signed_by": self.signed_by,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelpackManifest":
        sig = d.get("inference_signature", {})
        return cls(
            name=d["name"],
            version=d["version"],
            framework=d.get("framework", "custom"),
            entrypoint=d.get("entrypoint", ""),
            inputs=[TensorSpec.from_dict(i) for i in sig.get("inputs", [])],
            outputs=[TensorSpec.from_dict(o) for o in sig.get("outputs", [])],
            env_lock=d.get("env_lock", "env.lock"),
            provenance=Provenance.from_dict(d.get("provenance", {})),
            blobs=[BlobRef.from_dict(b) for b in d.get("blobs", [])],
            created_at=d.get("created_at", ""),
            signed_by=d.get("signed_by", ""),
            metadata=d.get("metadata", {}),
        )

    def content_digest(self) -> str:
        """Compute a content-addressable digest for this manifest."""
        import json
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(slots=True)
class InferenceRequest:
    """A single inference request."""
    request_id: str
    inputs: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class InferenceResult:
    """Result of a single inference."""
    request_id: str
    outputs: Dict[str, Any]
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BatchRequest:
    """Aggregated batch of inference requests."""
    requests: List[InferenceRequest]
    batch_id: str = ""

    @property
    def size(self) -> int:
        return len(self.requests)


@dataclass(slots=True)
class PlacementScore:
    """Score for scheduler placement decisions."""
    node_id: str
    device_affinity: float = 0.0
    memory_fit: float = 0.0
    current_load: float = 0.0
    cold_start_cost: float = 0.0
    total: float = 0.0

    def compute(
        self,
        w1: float = 0.3,
        w2: float = 0.3,
        w3: float = 0.25,
        w4: float = 0.15,
    ) -> float:
        self.total = (
            w1 * self.device_affinity
            + w2 * self.memory_fit
            + w3 * (1.0 - self.current_load)
            + w4 * (1.0 - self.cold_start_cost)
        )
        return self.total


@dataclass(slots=True)
class RolloutConfig:
    """Configuration for a traffic rollout."""
    from_version: str
    to_version: str
    strategy: RolloutStrategy = RolloutStrategy.CANARY
    percentage: int = 10
    metric: str = "latency_p95"
    threshold: float = 0.0
    auto_rollback: bool = True
    step_interval_seconds: int = 300


@dataclass(slots=True)
class DriftReport:
    """Result of a drift detection analysis."""
    method: DriftMethod
    score: float
    threshold: float
    is_drifted: bool
    feature_scores: Dict[str, float] = field(default_factory=dict)
    window_start: str = ""
    window_end: str = ""


# ── Protocols ──────────────────────────────────────────────────────────────

@runtime_checkable
class StorageAdapter(Protocol):
    """Protocol for blob storage backends."""

    async def put_blob(self, digest: str, data: bytes) -> str:
        """Store blob, return storage path."""
        ...

    async def get_blob(self, digest: str) -> bytes:
        """Retrieve blob by digest."""
        ...

    async def has_blob(self, digest: str) -> bool:
        """Check if blob exists."""
        ...

    async def delete_blob(self, digest: str) -> None:
        """Delete blob."""
        ...

    async def list_blobs(self) -> List[str]:
        """List all blob digests."""
        ...


@runtime_checkable
class Runtime(Protocol):
    """Protocol for model runtime backends."""

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        """Prepare runtime with modelpack artifacts."""
        ...

    async def load(self) -> None:
        """Load model into memory."""
        ...

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        """Run inference on a batch."""
        ...

    async def health(self) -> Dict[str, Any]:
        """Health check."""
        ...

    async def metrics(self) -> Dict[str, float]:
        """Collect runtime metrics."""
        ...

    async def unload(self) -> None:
        """Unload model and free resources."""
        ...


@runtime_checkable
class PluginHook(Protocol):
    """Protocol for plugin lifecycle hooks."""

    async def on_load(self, context: Dict[str, Any]) -> None: ...
    async def on_prepare(self, manifest: ModelpackManifest) -> None: ...
    async def on_infer(self, batch: BatchRequest, results: List[InferenceResult]) -> None: ...
    async def on_unload(self) -> None: ...
