"""
BentoML exporter — generates BentoML-compatible service bundles.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._types import BatchRequest, InferenceResult, ModelpackManifest
from .base import BaseRuntime

logger = logging.getLogger("aquilia.mlops.runtime.bento")


class BentoExporter(BaseRuntime):
    """
    Export modelpacks to BentoML service format.
    """

    def __init__(self):
        super().__init__()

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        self._manifest = manifest
        self._model_dir = model_dir

    async def load(self) -> None:
        self._loaded = True
        logger.info("BentoML exporter ready")

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        results: List[InferenceResult] = []
        for req in batch.requests:
            start = time.monotonic()
            outputs = {"prediction": req.inputs}
            latency = (time.monotonic() - start) * 1000
            results.append(InferenceResult(
                request_id=req.request_id,
                outputs=outputs,
                latency_ms=latency,
            ))
        return results

    async def export_bento(self, output_dir: str = ".") -> str:
        """
        Export a BentoML-compatible service file.

        Returns path to the created ``service.py``.
        """
        if not self._manifest:
            raise RuntimeError("Not prepared")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        service_code = f'''
"""Auto-generated BentoML service for {self._manifest.name}."""
import bentoml
from bentoml.io import JSON

svc = bentoml.Service("{self._manifest.name}")

@svc.api(input=JSON(), output=JSON())
def predict(input_data):
    # Load and run model
    return {{"prediction": input_data}}
'''
        service_path = out / "service.py"
        service_path.write_text(service_code)
        logger.info("Exported BentoML service: %s", service_path)
        return str(service_path)
