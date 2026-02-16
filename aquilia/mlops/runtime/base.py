"""
Runtime base — abstract interface for inference backends.
"""

from __future__ import annotations

import abc
import logging
import time
from typing import Any, Dict, List, Optional

from .._types import BatchRequest, InferenceResult, ModelpackManifest

logger = logging.getLogger("aquilia.mlops.runtime")


class BaseRuntime(abc.ABC):
    """
    Abstract runtime for model inference.

    Every runtime adapter must implement these methods.
    """

    def __init__(self):
        self._manifest: Optional[ModelpackManifest] = None
        self._model_dir: str = ""
        self._loaded: bool = False
        self._load_time_ms: float = 0.0

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def manifest(self) -> Optional[ModelpackManifest]:
        return self._manifest

    @abc.abstractmethod
    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        """Prepare runtime with model artifacts (download, validate)."""

    @abc.abstractmethod
    async def load(self) -> None:
        """Load model into memory / accelerator."""

    @abc.abstractmethod
    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        """Run inference on a batch of requests."""

    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy" if self._loaded else "not_loaded",
            "model": self._manifest.name if self._manifest else None,
            "version": self._manifest.version if self._manifest else None,
            "load_time_ms": self._load_time_ms,
        }

    async def metrics(self) -> Dict[str, float]:
        """Collect runtime-specific metrics."""
        return {
            "loaded": 1.0 if self._loaded else 0.0,
            "load_time_ms": self._load_time_ms,
        }

    async def unload(self) -> None:
        """Unload model and free resources."""
        self._loaded = False
        self._manifest = None
        logger.info("Runtime unloaded")


def select_runtime(
    manifest: ModelpackManifest,
    preferred: Optional[str] = None,
    gpu_available: bool = False,
) -> BaseRuntime:
    """
    Select the best runtime for the given manifest.

    Selection logic:
    1. If ``preferred`` is specified, use that.
    2. If ONNX file exists → ONNXRuntimeAdapter.
    3. If Triton available + GPU → TritonAdapter.
    4. Fallback → PythonRuntime.
    """
    from .python_runtime import PythonRuntime

    if preferred == "onnxruntime":
        from .onnx_runtime import ONNXRuntimeAdapter
        return ONNXRuntimeAdapter()

    if preferred == "triton":
        from .triton_adapter import TritonAdapter
        return TritonAdapter()

    if preferred == "torchserve":
        from .torchserve_exporter import TorchServeExporter
        return TorchServeExporter()

    if preferred == "bentoml":
        from .bento_exporter import BentoExporter
        return BentoExporter()

    # Auto-detect
    if manifest.entrypoint.endswith(".onnx"):
        try:
            from .onnx_runtime import ONNXRuntimeAdapter
            return ONNXRuntimeAdapter()
        except ImportError:
            pass

    if gpu_available:
        try:
            from .triton_adapter import TritonAdapter
            return TritonAdapter()
        except ImportError:
            pass

    return PythonRuntime()
