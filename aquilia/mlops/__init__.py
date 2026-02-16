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
    # Data classes
    TensorSpec,
    BlobRef,
    Provenance,
    ModelpackManifest,
    InferenceRequest,
    InferenceResult,
    BatchRequest,
    PlacementScore,
    RolloutConfig,
    DriftReport,
    # Protocols
    StorageAdapter,
    Runtime,
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
)

from .pack.builder import ModelpackBuilder
from .pack.content_store import ContentStore
from .registry.service import RegistryService
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
)
from .di_providers import register_mlops_providers, MLOpsConfig
from .controller import MLOpsController
from .middleware import mlops_metrics_middleware, mlops_request_id_middleware
from .lifecycle_hooks import mlops_on_startup, mlops_on_shutdown

__all__ = [
    # Types
    "Framework",
    "RuntimeKind",
    "QuantizePreset",
    "ExportTarget",
    "BatchingStrategy",
    "RolloutStrategy",
    "DriftMethod",
    "TensorSpec",
    "BlobRef",
    "Provenance",
    "ModelpackManifest",
    "InferenceRequest",
    "InferenceResult",
    "BatchRequest",
    "PlacementScore",
    "RolloutConfig",
    "DriftReport",
    "StorageAdapter",
    "Runtime",
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
    # Core classes
    "ModelpackBuilder",
    "ContentStore",
    "RegistryService",
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
    # DI
    "register_mlops_providers",
    "MLOpsConfig",
    # Controller
    "MLOpsController",
    # Middleware
    "mlops_metrics_middleware",
    "mlops_request_id_middleware",
    # Lifecycle
    "mlops_on_startup",
    "mlops_on_shutdown",
]
