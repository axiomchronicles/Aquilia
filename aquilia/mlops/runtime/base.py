"""
Runtime base — abstract interface for inference backends.

Provides ``BaseRuntime`` (standard) and ``BaseStreamingRuntime``
(for LLM/SLM with token-by-token streaming).
"""

from __future__ import annotations

import abc
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from .._types import (
    BatchRequest,
    InferenceRequest,
    InferenceResult,
    ModelpackManifest,
    StreamChunk,
    TokenUsage,
)

logger = logging.getLogger("aquilia.mlops.runtime")


class BaseRuntime(abc.ABC):
    """
    Abstract runtime for model inference.

    Every runtime adapter must implement these methods.
    """

    def __init__(self) -> None:
        self._manifest: Optional[ModelpackManifest] = None
        self._model_dir: str = ""
        self._loaded: bool = False
        self._load_time_ms: float = 0.0
        self._device: str = "cpu"
        self._total_infer_count: int = 0
        self._total_infer_time_ms: float = 0.0

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def manifest(self) -> Optional[ModelpackManifest]:
        return self._manifest

    @property
    def device(self) -> str:
        return self._device

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
            "device": self._device,
        }

    async def metrics(self) -> Dict[str, float]:
        """Collect runtime-specific metrics."""
        avg = (
            self._total_infer_time_ms / self._total_infer_count
            if self._total_infer_count > 0 else 0.0
        )
        return {
            "loaded": 1.0 if self._loaded else 0.0,
            "load_time_ms": self._load_time_ms,
            "total_infer_count": float(self._total_infer_count),
            "avg_infer_ms": avg,
        }

    async def unload(self) -> None:
        """Unload model and free resources."""
        self._loaded = False
        self._manifest = None
        logger.info("Runtime unloaded")

    async def memory_info(self) -> Dict[str, Any]:
        """Return memory / device usage info (override in subclasses)."""
        return {"device": self._device, "loaded": self._loaded}

    def _detect_device(self) -> str:
        """Auto-detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"


class BaseStreamingRuntime(BaseRuntime):
    """
    Abstract runtime that adds streaming inference for LLM/SLM models.

    Subclasses must implement ``stream_infer`` in addition to ``infer``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._total_tokens_generated: int = 0
        self._total_prompt_tokens: int = 0
        self._total_stream_requests: int = 0

    @abc.abstractmethod
    async def stream_infer(self, request: InferenceRequest) -> AsyncIterator[StreamChunk]:
        """Stream tokens one at a time. Must be an async generator."""
        yield  # type: ignore[misc]

    async def token_usage(self) -> TokenUsage:
        """Return lifetime token usage statistics."""
        return TokenUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_tokens_generated,
            total_tokens=self._total_prompt_tokens + self._total_tokens_generated,
        )

    async def metrics(self) -> Dict[str, float]:
        """Extended metrics including token stats."""
        base = await super().metrics()
        base.update({
            "total_tokens_generated": float(self._total_tokens_generated),
            "total_prompt_tokens": float(self._total_prompt_tokens),
            "total_stream_requests": float(self._total_stream_requests),
        })
        return base


def select_runtime(
    manifest: ModelpackManifest,
    preferred: Optional[str] = None,
    gpu_available: bool = False,
) -> BaseRuntime:
    """
    Select the best runtime for the given manifest.

    Selection logic:
    1. If ``preferred`` is specified, use that.
    2. If manifest is LLM/SLM → HuggingFace streaming runtime.
    3. If ONNX file exists → ONNXRuntimeAdapter.
    4. If Triton available + GPU → TritonAdapter.
    5. Fallback → PythonRuntime.
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

    if preferred in ("huggingface", "vllm", "llamacpp", "ctransformers"):
        return PythonRuntime()  # PythonRuntime handles LLM frameworks

    # Auto-detect LLM models
    if manifest.is_llm:
        return PythonRuntime()

    # Auto-detect ONNX
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
