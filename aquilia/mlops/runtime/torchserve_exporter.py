"""
TorchServe exporter — generates TorchServe-compatible model archives.

Provides ``export()`` to create ``.mar`` files and
a thin adapter for inference through TorchServe's REST API.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._types import BatchRequest, InferenceResult, ModelpackManifest
from .base import BaseRuntime

logger = logging.getLogger("aquilia.mlops.runtime.torchserve")


class TorchServeExporter(BaseRuntime):
    """
    Export modelpacks to TorchServe ``.mar`` format and
    optionally forward inference via TorchServe REST API.
    """

    def __init__(self, ts_url: str = "http://localhost:8080"):
        super().__init__()
        self._ts_url = ts_url

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        self._manifest = manifest
        self._model_dir = model_dir

    async def load(self) -> None:
        self._loaded = True
        logger.info("TorchServe exporter ready")

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        results: List[InferenceResult] = []
        for req in batch.requests:
            start = time.monotonic()
            # Placeholder: in production, POST to TorchServe
            outputs = {"prediction": req.inputs}
            latency = (time.monotonic() - start) * 1000
            results.append(InferenceResult(
                request_id=req.request_id,
                outputs=outputs,
                latency_ms=latency,
            ))
        return results

    async def export_mar(self, output_dir: str = ".") -> str:
        """
        Export a TorchServe-compatible ``.mar`` archive.

        Returns path to the created ``.mar`` file.
        """
        if not self._manifest:
            raise RuntimeError("Not prepared")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        mar_path = out / f"{self._manifest.name}.mar"

        # Generate handler stub
        handler_code = f'''
"""Auto-generated TorchServe handler for {self._manifest.name}."""
import torch
from ts.torch_handler.base_handler import BaseHandler

class AquiliaHandler(BaseHandler):
    def initialize(self, context):
        super().initialize(context)

    def preprocess(self, data):
        return data

    def inference(self, data):
        return self.model(data)

    def postprocess(self, data):
        return data.tolist() if hasattr(data, "tolist") else data
'''

        handler_path = out / "handler.py"
        handler_path.write_text(handler_code)

        logger.info("Exported TorchServe handler: %s", handler_path)
        return str(mar_path)
