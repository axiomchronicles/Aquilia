"""
Aquilia MLOps Platform

Production-ready model packaging, registry, serving, observability,
and release management — fully integrated with the Aquilia framework.

Quick start::

    from aquilia.mlops import ModelpackBuilder, RegistryClient, PythonRuntime

    # Create a modelpack
    builder = ModelpackBuilder(name="my-model", version="v1.0.0")
    builder.add_model("model.pt", framework="pytorch")
    pack_path = await builder.save("./out")

    # Publish to registry
    client = RegistryClient("http://localhost:8080")
    await client.push(pack_path)

    # Serve
    runtime = PythonRuntime()
    await runtime.prepare(manifest, model_dir)
    await runtime.load()
"""

from ._types import (
    # Enums
    Framework,
    RuntimeKind,
    QuantizePreset,
    ExportTarget,
    BatchingStrategy,
    RolloutStrategy,
    DriftMethod,
    ModelType,
    InferenceMode,
    DeviceType,
    CircuitState,
    # Data classes
    TensorSpec,
    BlobRef,
    Provenance,
    LLMConfig,
    ModelpackManifest,
    InferenceRequest,
    InferenceResult,
    StreamChunk,
    BatchRequest,
    PlacementScore,
    RolloutConfig,
    DriftReport,
    CircuitBreakerConfig,
    TokenUsage,
    # Protocols
    StorageAdapter,
    Runtime,
    StreamingRuntime,
    PluginHook,
)

from ._structures import (
    RingBuffer,
    LRUCache,
    AtomicCounter,
    ExponentialDecay,
    SlidingWindow,
    TopKHeap,
    BloomFilter,
    ConsistentHash,
    ModelLineageDAG,
    LineageNode,
    ExperimentLedger,
    Experiment,
    ExperimentArm,
    CircuitBreaker,
    TokenBucketRateLimiter,
    AdaptiveBatchQueue,
    MemoryTracker,
)

from .pack.builder import ModelpackBuilder
from .pack.content_store import ContentStore
from .registry.service import RegistryService
from .runtime.base import BaseRuntime, BaseStreamingRuntime
from .runtime.python_runtime import PythonRuntime
from .serving.server import ModelServingServer, WarmupStrategy
from .serving.batching import DynamicBatcher
from .observe.metrics import MetricsCollector
from .observe.drift import DriftDetector
from .plugins.host import PluginHost

# Integration modules
from .faults import (
    MLOpsFault,
    PackBuildFault,
    PackIntegrityFault,
    PackSignatureFault,
    RegistryConnectionFault,
    PackNotFoundFault,
    ImmutabilityViolationFault,
    InferenceFault,
    BatchTimeoutFault,
    RuntimeLoadFault,
    WarmupFault,
    DriftDetectionFault,
    MetricsExportFault,
    RolloutAdvanceFault,
    AutoRollbackFault,
    PlacementFault,
    ScalingFault,
    SigningFault,
    PermissionDeniedFault,
    EncryptionFault,
    PluginLoadFault,
    PluginHookFault,
    # Resilience faults
    CircuitBreakerFault,
    CircuitBreakerOpenFault,
    CircuitBreakerExhaustedFault,
    RateLimitFault,
    # Streaming faults
    StreamingFault,
    StreamInterruptedFault,
    TokenLimitExceededFault,
    # Memory faults
    MemoryFault,
    MemorySoftLimitFault,
    MemoryHardLimitFault,
)
from .di_providers import register_mlops_providers, MLOpsConfig
from .controller import MLOpsController
from .middleware import (
    mlops_metrics_middleware,
    mlops_request_id_middleware,
    mlops_rate_limit_middleware,
    mlops_circuit_breaker_middleware,
    register_mlops_middleware,
)
from .lifecycle_hooks import mlops_on_startup, mlops_on_shutdown

__all__ = [
    # Types — Enums
    "Framework",
    "RuntimeKind",
    "QuantizePreset",
    "ExportTarget",
    "BatchingStrategy",
    "RolloutStrategy",
    "DriftMethod",
    "ModelType",
    "InferenceMode",
    "DeviceType",
    "CircuitState",
    # Types — Data classes
    "TensorSpec",
    "BlobRef",
    "Provenance",
    "LLMConfig",
    "ModelpackManifest",
    "InferenceRequest",
    "InferenceResult",
    "StreamChunk",
    "BatchRequest",
    "PlacementScore",
    "RolloutConfig",
    "DriftReport",
    "CircuitBreakerConfig",
    "TokenUsage",
    # Types — Protocols
    "StorageAdapter",
    "Runtime",
    "StreamingRuntime",
    "PluginHook",
    # Data Structures
    "RingBuffer",
    "LRUCache",
    "AtomicCounter",
    "ExponentialDecay",
    "SlidingWindow",
    "TopKHeap",
    "BloomFilter",
    "ConsistentHash",
    "ModelLineageDAG",
    "LineageNode",
    "ExperimentLedger",
    "Experiment",
    "ExperimentArm",
    "CircuitBreaker",
    "TokenBucketRateLimiter",
    "AdaptiveBatchQueue",
    "MemoryTracker",
    # Core classes
    "ModelpackBuilder",
    "ContentStore",
    "RegistryService",
    "BaseRuntime",
    "BaseStreamingRuntime",
    "PythonRuntime",
    "ModelServingServer",
    "WarmupStrategy",
    "DynamicBatcher",
    "MetricsCollector",
    "DriftDetector",
    "PluginHost",
    # Faults
    "MLOpsFault",
    "PackBuildFault",
    "PackIntegrityFault",
    "PackSignatureFault",
    "RegistryConnectionFault",
    "PackNotFoundFault",
    "ImmutabilityViolationFault",
    "InferenceFault",
    "BatchTimeoutFault",
    "RuntimeLoadFault",
    "WarmupFault",
    "DriftDetectionFault",
    "MetricsExportFault",
    "RolloutAdvanceFault",
    "AutoRollbackFault",
    "PlacementFault",
    "ScalingFault",
    "SigningFault",
    "PermissionDeniedFault",
    "EncryptionFault",
    "PluginLoadFault",
    "PluginHookFault",
    "CircuitBreakerFault",
    "CircuitBreakerOpenFault",
    "CircuitBreakerExhaustedFault",
    "RateLimitFault",
    "StreamingFault",
    "StreamInterruptedFault",
    "TokenLimitExceededFault",
    "MemoryFault",
    "MemorySoftLimitFault",
    "MemoryHardLimitFault",
    # DI
    "register_mlops_providers",
    "MLOpsConfig",
    # Controller
    "MLOpsController",
    # Middleware
    "mlops_metrics_middleware",
    "mlops_request_id_middleware",
    "mlops_rate_limit_middleware",
    "mlops_circuit_breaker_middleware",
    "register_mlops_middleware",
    # Lifecycle
    "mlops_on_startup",
    "mlops_on_shutdown",
]
