"""
Python in-process runtime — loads and runs models natively in Python.

Supports PyTorch, scikit-learn, XGBoost, LightGBM, HuggingFace Transformers,
and custom callables.  Includes streaming inference for LLM/SLM models.
"""

from __future__ import annotations

import importlib
import logging
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .._types import (
    BatchRequest,
    Framework,
    InferenceRequest,
    InferenceResult,
    LLMConfig,
    ModelpackManifest,
    StreamChunk,
    TokenUsage,
)
from .base import BaseRuntime, BaseStreamingRuntime

logger = logging.getLogger("aquilia.mlops.runtime.python")


class PythonRuntime(BaseStreamingRuntime):
    """
    In-process Python runtime with LLM streaming support.

    Loads the model file and calls its ``predict`` / ``forward`` method
    (or a user-supplied callable).

    Supported formats:
    - ``.pt`` / ``.pth`` — PyTorch (``torch.load``)
    - ``.pkl`` / ``.joblib`` — pickle / joblib
    - ``.py`` — Python module with a ``predict(inputs)`` function
    - Custom callable via ``set_predict_fn``

    LLM support:
    - HuggingFace Transformers (AutoModelForCausalLM, pipeline)
    - Streaming token generation via ``stream_infer``
    - Device auto-detection (CUDA, MPS, CPU)
    """

    def __init__(self, predict_fn: Optional[Callable] = None) -> None:
        super().__init__()
        self._model: Any = None
        self._tokenizer: Any = None
        self._predict_fn: Optional[Callable] = predict_fn
        self._inference_count: int = 0
        self._total_latency_ms: float = 0.0
        self._llm_config: Optional[LLMConfig] = None
        self._is_llm: bool = False
        self._generation_kwargs: Dict[str, Any] = {}

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        self._manifest = manifest
        self._model_dir = model_dir
        self._is_llm = manifest.is_llm
        self._llm_config = manifest.llm_config
        self._device = self._detect_device()

        if self._llm_config:
            self._generation_kwargs = {
                "max_new_tokens": self._llm_config.max_new_tokens,
                "temperature": self._llm_config.temperature,
                "top_p": self._llm_config.top_p,
                "top_k": self._llm_config.top_k,
                "repetition_penalty": self._llm_config.repetition_penalty,
            }
            if self._llm_config.stop_sequences:
                self._generation_kwargs["stop_strings"] = self._llm_config.stop_sequences

        logger.info(
            "Prepared PythonRuntime: %s v%s (dir=%s, llm=%s, device=%s)",
            manifest.name, manifest.version, model_dir, self._is_llm, self._device,
        )

    async def load(self) -> None:
        if not self._manifest:
            raise RuntimeError("Runtime not prepared. Call prepare() first.")

        start = time.monotonic()

        if self._is_llm:
            await self._load_llm()
        else:
            await self._load_standard()

        self._loaded = True
        self._load_time_ms = (time.monotonic() - start) * 1000
        logger.info("Model loaded in %.1fms (device=%s)", self._load_time_ms, self._device)

    async def _load_standard(self) -> None:
        """Load a standard ML model (sklearn, PyTorch, etc.)."""
        model_path = Path(self._model_dir) / "model" / self._manifest.entrypoint

        if not model_path.exists():
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
            logger.warning("ONNX model detected in PythonRuntime; consider using ONNXRuntimeAdapter")
            self._model = None
        else:
            raise ValueError(f"Unsupported model format: {ext}")

    async def _load_llm(self) -> None:
        """Load an LLM/SLM model with HuggingFace Transformers."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError(
                "HuggingFace Transformers required for LLM support. "
                "Install with: pip install transformers torch"
            )

        model_path = self._manifest.entrypoint
        # If the entrypoint is a local path, resolve it
        local_path = Path(self._model_dir) / model_path
        if local_path.exists():
            model_path = str(local_path)

        cfg = self._llm_config or LLMConfig()
        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        torch_dtype = dtype_map.get(cfg.dtype, torch.float16)

        logger.info("Loading LLM: %s (dtype=%s, device=%s)", model_path, cfg.dtype, self._device)

        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=cfg.trust_remote_code,
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        load_kwargs: Dict[str, Any] = {
            "torch_dtype": torch_dtype,
            "trust_remote_code": cfg.trust_remote_code,
            "low_cpu_mem_usage": True,
        }
        if self._device == "cuda":
            load_kwargs["device_map"] = "auto"
        elif self._device == "mps":
            load_kwargs["device_map"] = "mps"

        self._model = AutoModelForCausalLM.from_pretrained(
            model_path, **load_kwargs,
        )
        if self._device not in ("cuda",) or "device_map" not in load_kwargs:
            try:
                self._model = self._model.to(self._device)
            except Exception:
                pass
        self._model.eval()

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        results: List[InferenceResult] = []

        for req in batch.requests:
            start = time.monotonic()

            if self._is_llm and self._tokenizer is not None:
                outputs = await self._infer_llm(req)
            elif self._predict_fn:
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
            self._total_infer_count += 1
            self._total_latency_ms += latency
            self._total_infer_time_ms += latency

            token_count = 0
            prompt_tokens = 0
            finish_reason = "stop"
            if isinstance(outputs, dict):
                token_count = outputs.pop("_token_count", 0)
                prompt_tokens = outputs.pop("_prompt_tokens", 0)
                finish_reason = outputs.pop("_finish_reason", "stop")

            results.append(InferenceResult(
                request_id=req.request_id,
                outputs={"prediction": outputs} if not isinstance(outputs, dict) else outputs,
                latency_ms=latency,
                token_count=token_count,
                prompt_tokens=prompt_tokens,
                finish_reason=finish_reason,
            ))

        return results

    async def _infer_llm(self, req: InferenceRequest) -> Dict[str, Any]:
        """Run LLM inference (non-streaming) for a single request."""
        import torch

        prompt = req.inputs.get("prompt", req.inputs.get("input", ""))
        if isinstance(prompt, list):
            # Chat-style messages
            prompt = self._tokenizer.apply_chat_template(
                prompt, tokenize=False, add_generation_prompt=True,
            )

        inputs = self._tokenizer(prompt, return_tensors="pt", padding=True)
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        prompt_len = inputs["input_ids"].shape[-1]

        gen_kwargs = dict(self._generation_kwargs)
        if req.max_tokens > 0:
            gen_kwargs["max_new_tokens"] = req.max_tokens
        gen_kwargs.update(req.parameters)

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, **gen_kwargs)

        new_tokens = output_ids[0][prompt_len:]
        text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        gen_count = len(new_tokens)

        self._total_tokens_generated += gen_count
        self._total_prompt_tokens += prompt_len

        return {
            "text": text,
            "_token_count": gen_count,
            "_prompt_tokens": prompt_len,
            "_finish_reason": "stop",
        }

    async def stream_infer(self, request: InferenceRequest) -> AsyncIterator[StreamChunk]:
        """Stream tokens one at a time for LLM inference."""
        if not self._is_llm or self._tokenizer is None:
            raise RuntimeError("Streaming inference requires an LLM model")

        import asyncio
        import torch

        self._total_stream_requests += 1
        prompt = request.inputs.get("prompt", request.inputs.get("input", ""))
        if isinstance(prompt, list):
            prompt = self._tokenizer.apply_chat_template(
                prompt, tokenize=False, add_generation_prompt=True,
            )

        inputs = self._tokenizer(prompt, return_tensors="pt", padding=True)
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        prompt_len = inputs["input_ids"].shape[-1]

        gen_kwargs = dict(self._generation_kwargs)
        if request.max_tokens > 0:
            gen_kwargs["max_new_tokens"] = request.max_tokens
        gen_kwargs.update(request.parameters)
        gen_kwargs["max_new_tokens"] = gen_kwargs.get("max_new_tokens", 512)

        max_new = gen_kwargs.pop("max_new_tokens", 512)
        input_ids = inputs["input_ids"]
        generated_tokens = 0
        start = time.monotonic()

        try:
            with torch.no_grad():
                for _ in range(max_new):
                    outputs = self._model(input_ids=input_ids)
                    next_logits = outputs.logits[:, -1, :]
                    temp = gen_kwargs.get("temperature", 1.0)
                    if temp > 0 and temp != 1.0:
                        next_logits = next_logits / temp

                    top_k_val = gen_kwargs.get("top_k", 50)
                    if top_k_val > 0:
                        indices_to_remove = next_logits < torch.topk(next_logits, top_k_val)[0][..., -1, None]
                        next_logits[indices_to_remove] = float("-inf")

                    probs = torch.softmax(next_logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)
                    next_id = next_token.item()

                    token_text = self._tokenizer.decode([next_id], skip_special_tokens=False)
                    generated_tokens += 1
                    self._total_tokens_generated += 1

                    is_eos = next_id == self._tokenizer.eos_token_id
                    elapsed = (time.monotonic() - start) * 1000

                    yield StreamChunk(
                        request_id=request.request_id,
                        token=token_text,
                        token_id=next_id,
                        is_finished=is_eos,
                        finish_reason="stop" if is_eos else "",
                        cumulative_tokens=generated_tokens,
                        latency_ms=elapsed,
                    )

                    if is_eos:
                        break

                    input_ids = torch.cat([input_ids, next_token], dim=-1)
                    await asyncio.sleep(0)  # yield control

            # If we exhausted max_new_tokens without EOS
            if generated_tokens >= max_new:
                yield StreamChunk(
                    request_id=request.request_id,
                    token="",
                    is_finished=True,
                    finish_reason="length",
                    cumulative_tokens=generated_tokens,
                    latency_ms=(time.monotonic() - start) * 1000,
                )
        finally:
            self._total_prompt_tokens += prompt_len

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

    async def memory_info(self) -> Dict[str, Any]:
        """Return GPU/CPU memory info."""
        info: Dict[str, Any] = {"device": self._device, "loaded": self._loaded}
        try:
            import torch
            if self._device == "cuda" and torch.cuda.is_available():
                info["gpu_memory_allocated_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
                info["gpu_memory_reserved_mb"] = torch.cuda.memory_reserved() / (1024 * 1024)
                info["gpu_memory_total_mb"] = torch.cuda.get_device_properties(0).total_mem / (1024 * 1024)
        except ImportError:
            pass
        return info

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
