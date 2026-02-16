"""
Edge export utilities — TFLite, CoreML, quantized ONNX.

Provides ``aquilia export`` CLI target implementations.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._types import ExportTarget

logger = logging.getLogger("aquilia.mlops.optimizer.export")


@dataclass
class ExportResult:
    """Result of an edge export."""
    target: str
    output_path: str
    size_bytes: int
    notes: List[str]


class EdgeExporter:
    """
    Export models to edge-friendly formats.

    Usage::

        exporter = EdgeExporter()
        result = await exporter.export(
            model_path="model.onnx",
            target=ExportTarget.TFLITE,
            output_dir="./edge",
        )
    """

    async def export(
        self,
        model_path: str,
        target: ExportTarget,
        output_dir: str = ".",
        optimize: bool = True,
    ) -> ExportResult:
        """Export model to edge target format."""
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if target == ExportTarget.TFLITE:
            return await self._to_tflite(path, out, optimize)
        elif target == ExportTarget.COREML:
            return await self._to_coreml(path, out, optimize)
        elif target == ExportTarget.ONNX_QUANTIZED:
            return await self._to_quantized_onnx(path, out)
        elif target == ExportTarget.TENSORRT:
            return await self._to_tensorrt(path, out)
        else:
            raise ValueError(f"Unsupported export target: {target}")

    async def _to_tflite(
        self, path: Path, out: Path, optimize: bool
    ) -> ExportResult:
        """Convert to TFLite format."""
        dest = out / f"{path.stem}.tflite"
        notes = []

        try:
            import tensorflow as tf

            if path.suffix == ".onnx":
                notes.append("Converting ONNX → TF → TFLite")
                import onnx
                from onnx_tf.backend import prepare
                onnx_model = onnx.load(str(path))
                tf_rep = prepare(onnx_model)
                tf_rep.export_graph(str(out / "tf_model"))
                converter = tf.lite.TFLiteConverter.from_saved_model(str(out / "tf_model"))
            else:
                converter = tf.lite.TFLiteConverter.from_saved_model(str(path))

            if optimize:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                notes.append("Default optimization applied")

            tflite_model = converter.convert()
            dest.write_bytes(tflite_model)
        except ImportError:
            notes.append("TensorFlow not available; model copied as-is")
            shutil.copy2(str(path), str(dest))

        return ExportResult(
            target="tflite",
            output_path=str(dest),
            size_bytes=dest.stat().st_size if dest.exists() else 0,
            notes=notes,
        )

    async def _to_coreml(
        self, path: Path, out: Path, optimize: bool
    ) -> ExportResult:
        """Convert to CoreML format."""
        dest = out / f"{path.stem}.mlmodel"
        notes = []

        try:
            import coremltools as ct

            if path.suffix in (".pt", ".pth"):
                import torch
                model = torch.load(str(path), map_location="cpu", weights_only=False)
                model.eval()
                traced = torch.jit.trace(model, torch.randn(1, 64))
                mlmodel = ct.convert(traced)
                notes.append("PyTorch → CoreML conversion")
            elif path.suffix == ".onnx":
                mlmodel = ct.converters.onnx.convert(model=str(path))
                notes.append("ONNX → CoreML conversion")
            else:
                raise ValueError(f"Cannot convert {path.suffix} to CoreML")

            mlmodel.save(str(dest))
        except ImportError:
            notes.append("coremltools not available; model copied as-is")
            shutil.copy2(str(path), str(dest))

        return ExportResult(
            target="coreml",
            output_path=str(dest),
            size_bytes=dest.stat().st_size if dest.exists() else 0,
            notes=notes,
        )

    async def _to_quantized_onnx(self, path: Path, out: Path) -> ExportResult:
        """Quantize ONNX model."""
        from .pipeline import OptimizationPipeline
        from .._types import QuantizePreset

        pipeline = OptimizationPipeline()
        result = await pipeline.run(
            str(path), preset=QuantizePreset.INT8, output_dir=str(out)
        )
        return ExportResult(
            target="onnx-quantized",
            output_path=result.optimized_path,
            size_bytes=result.optimized_size_bytes,
            notes=result.notes or [],
        )

    async def _to_tensorrt(self, path: Path, out: Path) -> ExportResult:
        """Convert to TensorRT format."""
        dest = out / f"{path.stem}.trt"
        notes = ["TensorRT export placeholder"]
        shutil.copy2(str(path), str(dest))
        return ExportResult(
            target="tensorrt",
            output_path=str(dest),
            size_bytes=dest.stat().st_size,
            notes=notes,
        )


async def profile_model(
    model_path: str,
    target_device: str = "cpu",
) -> Dict[str, Any]:
    """
    Estimate latency and memory for a model on a target device.

    Returns dict with estimated metrics.
    """
    path = Path(model_path)
    size = path.stat().st_size

    # Heuristic estimation
    return {
        "model_size_bytes": size,
        "model_size_mb": size / (1024 * 1024),
        "target_device": target_device,
        "estimated_latency_ms": size / (1024 * 1024) * 2.0,  # rough estimate
        "estimated_memory_mb": size / (1024 * 1024) * 1.5,
    }
