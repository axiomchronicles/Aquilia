"""
Aquilia MLOps Platform — Shared type definitions.

All protocol classes, enums, TypedDicts and dataclasses shared
across sub-packages live here to avoid circular imports.

Covers SLM→LLM serving, streaming inference, KV-cache management,
token budgets, model-parallel execution, and adaptive batching.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
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
    HUGGINGFACE = "huggingface"
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    CTRANSFORMERS = "ctransformers"
    CUSTOM = "custom"


class RuntimeKind(str, Enum):
    """Available runtime backends."""
    PYTHON = "python"
    ONNXRUNTIME = "onnxruntime"
    TRITON = "triton"
    TORCHSERVE = "torchserve"
    BENTOML = "bentoml"
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    TGI = "tgi"


class QuantizePreset(str, Enum):
    """Quantization presets."""
    MOBILE = "mobile"       # int8, aggressive
    EDGE = "edge"           # int8, balanced
    FP16 = "fp16"           # float16
    BF16 = "bf16"           # bfloat16
    INT8 = "int8"           # int8, dynamic
    INT4 = "int4"           # int4, GPTQ/AWQ
    DYNAMIC = "dynamic"     # dynamic quantization
    GGUF_Q4 = "gguf_q4"    # GGUF 4-bit (llama.cpp)
    GGUF_Q5 = "gguf_q5"    # GGUF 5-bit
    GGUF_Q8 = "gguf_q8"    # GGUF 8-bit
    AWQ = "awq"             # Activation-aware Weight Quantization
    GPTQ = "gptq"           # GPTQ quantization


class ExportTarget(str, Enum):
    """Edge export targets."""
    TFLITE = "tflite"
    COREML = "coreml"
    ONNX_QUANTIZED = "onnx-quantized"
    TENSORRT = "tensorrt"
    TVM = "tvm"
    GGUF = "gguf"
    CTRANSLATE2 = "ctranslate2"


class BatchingStrategy(str, Enum):
    """Batching strategy modes."""
    SIZE = "size"
    TIME = "time"
    HYBRID = "hybrid"
    CONTINUOUS = "continuous"   # continuous batching for LLMs
    ADAPTIVE = "adaptive"      # adaptive based on load/latency


class RolloutStrategy(str, Enum):
    """Release rollout strategies."""
    CANARY = "canary"
    AB_TEST = "ab_test"
    SHADOW = "shadow"
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"


class DriftMethod(str, Enum):
    """Drift detection methods."""
    PSI = "psi"
    KS_TEST = "ks_test"
    DISTRIBUTION = "distribution"
    EMBEDDING = "embedding"      # embedding-space drift for LLMs
    PERPLEXITY = "perplexity"    # perplexity-based drift


class ModelType(str, Enum):
    """Model type classification for serving strategy selection."""
    CLASSICAL_ML = "classical_ml"
    DEEP_LEARNING = "deep_learning"
    SLM = "slm"                    # small language model (< 3B params)
    LLM = "llm"                    # large language model (3B+ params)
    VISION = "vision"
    MULTIMODAL = "multimodal"
    EMBEDDING = "embedding"
    CUSTOM = "custom"


class InferenceMode(str, Enum):
    """Inference execution modes."""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"        # token-by-token streaming
    BATCH = "batch"


class DeviceType(str, Enum):
    """Compute device types."""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"                    # Apple Silicon
    NPU = "npu"
    TPU = "tpu"
    AUTO = "auto"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"              # healthy, requests pass through
    OPEN = "open"                  # unhealthy, requests rejected
    HALF_OPEN = "half_open"        # probing, limited requests


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
class LLMConfig:
    """Configuration specific to LLM/SLM model serving."""
    model_type: ModelType = ModelType.CUSTOM
    max_seq_length: int = 4096
    max_new_tokens: int = 2048
    max_batch_tokens: int = 32768         # total tokens across batch
    kv_cache_max_mb: int = 2048           # max KV cache memory in MB
    tensor_parallel: int = 1              # tensor parallelism degree
    pipeline_parallel: int = 1            # pipeline parallelism degree
    dtype: str = "float16"                # compute dtype
    device: DeviceType = DeviceType.AUTO
    trust_remote_code: bool = False
    tokenizer_name: str = ""              # override tokenizer
    chat_template: str = ""               # chat template override
    rope_scaling: Optional[Dict[str, Any]] = None
    stop_sequences: List[str] = field(default_factory=list)
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = 50
    repetition_penalty: float = 1.0
    stream_chunk_size: int = 1            # tokens per stream chunk
    prefix_caching: bool = True           # enable prefix/prompt caching
    speculative_decoding: bool = False
    draft_model: str = ""                 # draft model for speculative decoding
    draft_tokens: int = 5                 # speculative lookahead

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for f_name in self.__slots__:
            val = getattr(self, f_name)
            if isinstance(val, Enum):
                d[f_name] = val.value
            elif isinstance(val, list):
                d[f_name] = list(val)
            elif isinstance(val, dict):
                d[f_name] = dict(val) if val else {}
            else:
                d[f_name] = val
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LLMConfig":
        kwargs: Dict[str, Any] = {}
        if "model_type" in d:
            kwargs["model_type"] = ModelType(d["model_type"])
        if "device" in d:
            kwargs["device"] = DeviceType(d["device"])
        for k in ("max_seq_length", "max_new_tokens", "max_batch_tokens",
                   "kv_cache_max_mb", "tensor_parallel", "pipeline_parallel",
                   "dtype", "trust_remote_code", "tokenizer_name", "chat_template",
                   "temperature", "top_p", "top_k", "repetition_penalty",
                   "stream_chunk_size", "prefix_caching", "speculative_decoding",
                   "draft_model", "draft_tokens"):
            if k in d:
                kwargs[k] = d[k]
        if "stop_sequences" in d:
            kwargs["stop_sequences"] = list(d["stop_sequences"])
        if "rope_scaling" in d:
            kwargs["rope_scaling"] = d["rope_scaling"]
        return cls(**kwargs)


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
    model_type: str = "custom"
    llm_config: Optional[LLMConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
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
            "model_type": self.model_type,
        }
        if self.llm_config is not None:
            d["llm_config"] = self.llm_config.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelpackManifest":
        sig = d.get("inference_signature", {})
        llm_cfg = None
        if "llm_config" in d and d["llm_config"]:
            llm_cfg = LLMConfig.from_dict(d["llm_config"])
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
            model_type=d.get("model_type", "custom"),
            llm_config=llm_cfg,
        )

    def content_digest(self) -> str:
        """Compute a content-addressable digest for this manifest."""
        import json
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def is_llm(self) -> bool:
        """Check if this manifest represents an LLM/SLM."""
        return self.model_type in (
            ModelType.LLM.value, ModelType.SLM.value,
            "llm", "slm",
        ) or self.framework in (
            Framework.HUGGINGFACE.value, Framework.VLLM.value,
            Framework.LLAMACPP.value, Framework.CTRANSFORMERS.value,
            "huggingface", "vllm", "llamacpp", "ctransformers",
        )


@dataclass(slots=True)
class InferenceRequest:
    """A single inference request."""
    request_id: str
    inputs: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0                          # higher = more urgent
    stream: bool = False                       # streaming response
    max_tokens: int = 0                        # 0 = use default
    timeout_ms: float = 0.0                    # per-request timeout


@dataclass(slots=True)
class InferenceResult:
    """Result of a single inference."""
    request_id: str
    outputs: Dict[str, Any]
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0                       # tokens generated (LLM)
    prompt_tokens: int = 0                     # prompt tokens (LLM)
    finish_reason: str = ""                    # stop, length, error


@dataclass(slots=True)
class StreamChunk:
    """A single chunk in a streaming inference response."""
    request_id: str
    token: str
    token_id: int = 0
    is_finished: bool = False
    finish_reason: str = ""
    cumulative_tokens: int = 0
    latency_ms: float = 0.0


@dataclass(slots=True)
class BatchRequest:
    """Aggregated batch of inference requests."""
    requests: List[InferenceRequest]
    batch_id: str = ""

    @property
    def size(self) -> int:
        return len(self.requests)

    @property
    def total_tokens(self) -> int:
        """Estimate total token budget for LLM batches."""
        return sum(r.max_tokens or 512 for r in self.requests)


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


@dataclass(slots=True)
class CircuitBreakerConfig:
    """Configuration for inference circuit breaker."""
    failure_threshold: int = 5            # failures before opening
    success_threshold: int = 3            # successes in half-open before closing
    timeout_seconds: float = 30.0         # time in open state before half-open
    half_open_max_calls: int = 3          # max concurrent calls in half-open


@dataclass(slots=True)
class TokenUsage:
    """Token usage tracking for LLM inference."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    time_to_first_token_ms: float = 0.0
    kv_cache_usage_mb: float = 0.0


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
class StreamingRuntime(Protocol):
    """Protocol for runtimes that support streaming inference (LLMs)."""

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None: ...
    async def load(self) -> None: ...
    async def unload(self) -> None: ...

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        """Non-streaming inference."""
        ...

    async def stream_infer(self, request: InferenceRequest) -> AsyncIterator[StreamChunk]:
        """Stream tokens one at a time."""
        ...
        yield  # type: ignore[misc]

    async def health(self) -> Dict[str, Any]: ...
    async def metrics(self) -> Dict[str, float]: ...

    async def token_usage(self) -> TokenUsage:
        """Return current token usage stats."""
        ...

    async def memory_info(self) -> Dict[str, Any]:
        """Return memory/device usage info."""
        ...


@runtime_checkable
class PluginHook(Protocol):
    """Protocol for plugin lifecycle hooks."""

    async def on_load(self, context: Dict[str, Any]) -> None: ...
    async def on_prepare(self, manifest: ModelpackManifest) -> None: ...
    async def on_infer(self, batch: BatchRequest, results: List[InferenceResult]) -> None: ...
    async def on_stream_chunk(self, chunk: StreamChunk) -> None: ...
    async def on_unload(self) -> None: ...
