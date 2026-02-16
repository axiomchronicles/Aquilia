"""
Python in-process runtime — loads and runs models natively in Python.

Supports PyTorch, scikit-learn, XGBoost, LightGBM, and custom callables.
"""

from __future__ import annotations

import importlib
import logging
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .._types import (
    BatchRequest,
    InferenceRequest,
    InferenceResult,
    ModelpackManifest,
)
from .base import BaseRuntime

logger = logging.getLogger("aquilia.mlops.runtime.python")


class PythonRuntime(BaseRuntime):
    """
    In-process Python runtime.

    Loads the model file and calls its ``predict`` / ``forward`` method
    (or a user-supplied callable).

    Supported formats:
    - ``.pt`` / ``.pth`` — PyTorch (``torch.load``)
    - ``.pkl`` / ``.joblib`` — pickle / joblib
    - ``.py`` — Python module with a ``predict(inputs)`` function
    - Custom callable via ``set_predict_fn``
    """

    def __init__(self, predict_fn: Optional[Callable] = None):
        super().__init__()
        self._model: Any = None
        self._predict_fn: Optional[Callable] = predict_fn
        self._inference_count: int = 0
        self._total_latency_ms: float = 0.0

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        self._manifest = manifest
        self._model_dir = model_dir
        logger.info(
            "Prepared PythonRuntime: %s v%s (dir=%s)",
            manifest.name, manifest.version, model_dir,
        )

    async def load(self) -> None:
        if not self._manifest:
            raise RuntimeError("Runtime not prepared. Call prepare() first.")

        start = time.monotonic()
        model_path = Path(self._model_dir) / "model" / self._manifest.entrypoint

        if not model_path.exists():
            # Try without model/ prefix
            model_path = Path(self._model_dir) / self._manifest.entrypoint

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        ext = model_path.suffix.lower()

        if ext in (".pt", ".pth"):
            self._model = self._load_pytorch(model_path)
        elif ext in (".pkl", ".joblib"):
            self._model = self._load_pickle(model_path)
        elif ext == ".py":
            self._model = self._load_python_module(model_path)
        elif ext == ".onnx":
            # Delegate to ONNX runtime if available
            logger.warning("ONNX model detected in PythonRuntime; consider using ONNXRuntimeAdapter")
            self._model = None
        else:
            raise ValueError(f"Unsupported model format: {ext}")

        self._loaded = True
        self._load_time_ms = (time.monotonic() - start) * 1000
        logger.info("Model loaded in %.1fms", self._load_time_ms)

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        results: List[InferenceResult] = []

        for req in batch.requests:
            start = time.monotonic()

            if self._predict_fn:
                outputs = self._predict_fn(req.inputs)
            elif hasattr(self._model, "predict"):
                outputs = self._model.predict(req.inputs)
            elif hasattr(self._model, "forward"):
                outputs = self._model.forward(req.inputs)
            elif callable(self._model):
                outputs = self._model(req.inputs)
            else:
                raise RuntimeError("Model has no predict/forward/callable method")

            latency = (time.monotonic() - start) * 1000
            self._inference_count += 1
            self._total_latency_ms += latency

            results.append(InferenceResult(
                request_id=req.request_id,
                outputs={"prediction": outputs} if not isinstance(outputs, dict) else outputs,
                latency_ms=latency,
            ))

        return results

    async def metrics(self) -> Dict[str, float]:
        base = await super().metrics()
        avg_latency = (
            self._total_latency_ms / self._inference_count
            if self._inference_count > 0
            else 0.0
        )
        base.update({
            "inference_count": float(self._inference_count),
            "avg_latency_ms": avg_latency,
            "total_latency_ms": self._total_latency_ms,
        })
        return base

    # ── Loaders ──────────────────────────────────────────────────────

    @staticmethod
    def _load_pytorch(path: Path) -> Any:
        try:
            import torch
            model = torch.load(str(path), map_location="cpu", weights_only=False)
            if hasattr(model, "eval"):
                model.eval()
            return model
        except ImportError:
            raise ImportError("PyTorch required. Install with: pip install torch")

    @staticmethod
    def _load_pickle(path: Path) -> Any:
        if path.suffix == ".joblib":
            try:
                import joblib
                return joblib.load(str(path))
            except ImportError:
                pass
        with open(path, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def _load_python_module(path: Path) -> Any:
        spec = importlib.util.spec_from_file_location("_user_model", str(path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "predict"):
            return module
        raise AttributeError(f"Module {path} has no 'predict' function")

    def set_predict_fn(self, fn: Callable) -> None:
        """Set a custom prediction function."""
        self._predict_fn = fn
