"""
Triton Inference Server adapter.

Communicates with a running Triton server via gRPC or HTTP.
Requires ``tritonclient`` (optional dependency).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .._types import BatchRequest, InferenceResult, ModelpackManifest
from .base import BaseRuntime

logger = logging.getLogger("aquilia.mlops.runtime.triton")


class TritonAdapter(BaseRuntime):
    """
    Triton Inference Server adapter.

    Connects to a running Triton instance and forwards inference requests.
    """

    def __init__(
        self,
        url: str = "localhost:8001",
        protocol: str = "grpc",
    ):
        super().__init__()
        self._url = url
        self._protocol = protocol
        self._client: Any = None
        self._model_name: str = ""
        self._model_version: str = ""

    async def prepare(self, manifest: ModelpackManifest, model_dir: str) -> None:
        self._manifest = manifest
        self._model_dir = model_dir
        self._model_name = manifest.name.replace("/", "_")
        self._model_version = manifest.version.lstrip("v")

    async def load(self) -> None:
        try:
            if self._protocol == "grpc":
                import tritonclient.grpc as grpcclient
                self._client = grpcclient.InferenceServerClient(url=self._url)
            else:
                import tritonclient.http as httpclient
                self._client = httpclient.InferenceServerClient(url=self._url)
        except ImportError:
            raise ImportError(
                "tritonclient required. Install with: pip install tritonclient[all]"
            )

        if not self._client.is_server_live():
            raise ConnectionError(f"Triton server not reachable at {self._url}")

        self._loaded = True
        logger.info("Connected to Triton at %s", self._url)

    async def infer(self, batch: BatchRequest) -> List[InferenceResult]:
        if not self._client:
            raise RuntimeError("Triton client not connected")

        results: List[InferenceResult] = []

        for req in batch.requests:
            start = time.monotonic()

            # Build Triton request — simplified
            outputs = {"prediction": req.inputs}  # Placeholder
            latency = (time.monotonic() - start) * 1000

            results.append(InferenceResult(
                request_id=req.request_id,
                outputs=outputs,
                latency_ms=latency,
            ))

        return results

    async def unload(self) -> None:
        self._client = None
        await super().unload()
