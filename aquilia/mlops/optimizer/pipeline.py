"""
Optimization Pipeline — orchestrates quantization, pruning, fusion, compilation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._types import QuantizePreset

logger = logging.getLogger("aquilia.mlops.optimizer")


@dataclass
class OptimizationResult:
    """Result of an optimization pass."""
    original_size_bytes: int
    optimized_size_bytes: int
    original_path: str
    optimized_path: str
    preset: str
    compression_ratio: float = 0.0
    notes: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.notes is None:
            self.notes = []
        if self.original_size_bytes > 0:
            self.compression_ratio = 1.0 - (
                self.optimized_size_bytes / self.original_size_bytes
            )


class OptimizationPipeline:
    """
    Runs a sequence of optimization passes on model files.

    Usage::

        pipeline = OptimizationPipeline()
        result = await pipeline.run(
            model_path="model.onnx",
            preset=QuantizePreset.INT8,
            output_dir="./optimized",
        )
    """

    async def run(
        self,
        model_path: str,
        preset: QuantizePreset = QuantizePreset.DYNAMIC,
        output_dir: str = ".",
    ) -> OptimizationResult:
        """Run optimization pipeline."""
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        original_size = path.stat().st_size

        ext = path.suffix.lower()
        if ext == ".onnx":
            result = await self._quantize_onnx(path, preset, out)
        elif ext in (".pt", ".pth"):
            result = await self._quantize_pytorch(path, preset, out)
        else:
            # Passthrough
            import shutil
            dest = out / path.name
            shutil.copy2(str(path), str(dest))
            result = OptimizationResult(
                original_size_bytes=original_size,
                optimized_size_bytes=dest.stat().st_size,
                original_path=str(path),
                optimized_path=str(dest),
                preset=preset.value,
                notes=["No optimization applied (unsupported format)"],
            )

        logger.info(
            "Optimized %s: %.1f%% reduction (preset=%s)",
            path.name, result.compression_ratio * 100, preset.value,
        )
        return result

    async def _quantize_onnx(
        self, path: Path, preset: QuantizePreset, out: Path
    ) -> OptimizationResult:
        """Quantize ONNX model."""
        original_size = path.stat().st_size
        dest = out / f"{path.stem}_quantized.onnx"

        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType

            if preset in (QuantizePreset.INT8, QuantizePreset.DYNAMIC, QuantizePreset.EDGE):
                quantize_dynamic(
                    str(path), str(dest),
                    weight_type=QuantType.QInt8,
                )
            elif preset == QuantizePreset.FP16:
                # FP16 conversion
                import onnx
                from onnxruntime.transformers.float16 import convert_float_to_float16
                model = onnx.load(str(path))
                model_fp16 = convert_float_to_float16(model)
                onnx.save(model_fp16, str(dest))
            else:
                quantize_dynamic(str(path), str(dest))

            return OptimizationResult(
                original_size_bytes=original_size,
                optimized_size_bytes=dest.stat().st_size,
                original_path=str(path),
                optimized_path=str(dest),
                preset=preset.value,
                notes=["ONNX Runtime quantization applied"],
            )
        except ImportError:
            # Fallback: copy without quantization
            import shutil
            shutil.copy2(str(path), str(dest))
            return OptimizationResult(
                original_size_bytes=original_size,
                optimized_size_bytes=dest.stat().st_size,
                original_path=str(path),
                optimized_path=str(dest),
                preset=preset.value,
                notes=["onnxruntime.quantization not available; model copied without quantization"],
            )

    async def _quantize_pytorch(
        self, path: Path, preset: QuantizePreset, out: Path
    ) -> OptimizationResult:
        """Quantize PyTorch model."""
        original_size = path.stat().st_size
        dest = out / f"{path.stem}_quantized{path.suffix}"

        try:
            import torch

            model = torch.load(str(path), map_location="cpu", weights_only=False)

            if preset in (QuantizePreset.INT8, QuantizePreset.DYNAMIC):
                model = torch.quantization.quantize_dynamic(
                    model, {torch.nn.Linear}, dtype=torch.qint8
                )
            elif preset == QuantizePreset.FP16:
                model = model.half()

            torch.save(model, str(dest))

            return OptimizationResult(
                original_size_bytes=original_size,
                optimized_size_bytes=dest.stat().st_size,
                original_path=str(path),
                optimized_path=str(dest),
                preset=preset.value,
                notes=["PyTorch quantization applied"],
            )
        except ImportError:
            import shutil
            shutil.copy2(str(path), str(dest))
            return OptimizationResult(
                original_size_bytes=original_size,
                optimized_size_bytes=dest.stat().st_size,
                original_path=str(path),
                optimized_path=str(dest),
                preset=preset.value,
                notes=["torch not available; model copied without quantization"],
            )
