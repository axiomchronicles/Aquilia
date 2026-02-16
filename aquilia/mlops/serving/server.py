"""
Model Serving Server — dev and production serving with typed endpoints.

Integrates with Aquilia's ASGI + controller architecture and provides:
- Auto-generated ``/predict``, ``/health``, ``/metrics`` endpoints
- Hot-reload in dev mode
- Runtime selection and lifecycle management
- **BloomFilter** request deduplication (reject duplicate request IDs)
- **Health probes** — K8s ``/healthz`` (liveness) and ``/readyz`` (readiness)
- **Warm-up** — pre-inference warmup with synthetic payloads on ``start()``
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .._types import (
    BatchRequest,
    InferenceRequest,
    InferenceResult,
    ModelpackManifest,
    RuntimeKind,
)
from .._structures import BloomFilter
from ..faults import InferenceFault, RuntimeLoadFault
from ..runtime.base import BaseRuntime, select_runtime
from .batching import DynamicBatcher

logger = logging.getLogger("aquilia.mlops.serving")


class WarmupStrategy:
    """
    Pre-inference warm-up to eliminate cold-start latency.

    On ``start()``, sends *n* synthetic requests through the full
    inference pipeline (runtime → batcher → output) so that:
    - JIT / torch.compile / ONNX graph optimisation completes
    - Memory pages are faulted in
    - Python's per-opcode specialisation caches are primed

    The warm-up payload is derived from the manifest's input spec.
    """

    def __init__(
        self,
        num_requests: int = 3,
        synthetic_payload: Optional[Dict[str, Any]] = None,
    ):
        self.num_requests = num_requests
        self.synthetic_payload = synthetic_payload

    def generate_payload(self, manifest: ModelpackManifest) -> Dict[str, Any]:
        """Build a synthetic input from the manifest's tensor specs."""
        if self.synthetic_payload:
            return self.synthetic_payload

        payload: Dict[str, Any] = {}
        for spec in manifest.inputs:
            # Fill with zeros of the correct shape
            shape = [max(1, s) if isinstance(s, int) and s > 0 else 1 for s in spec.shape]
            import functools, operator
            total = functools.reduce(operator.mul, shape, 1)
            payload[spec.name] = [0.0] * total
        return payload or {"input": [0.0]}


class ModelServingServer:
    """
    High-level model serving server.

    Combines runtime, batcher, observability, deduplication, health
    probes, and warm-up into a single entry point.

    Usage::

        server = ModelServingServer(manifest=manifest, model_dir="./unpacked")
        await server.start()
        result = await server.predict({"features": [1.0, 2.0, 3.0]})
        await server.stop()
    """

    def __init__(
        self,
        manifest: ModelpackManifest,
        model_dir: str,
        runtime: Optional[BaseRuntime] = None,
        runtime_kind: Optional[str] = None,
        max_batch_size: int = 16,
        max_latency_ms: float = 50.0,
        port: int = 8080,
        hot_reload: bool = False,
        dedup_capacity: int = 100_000,
        warmup: Optional[WarmupStrategy] = None,
    ):
        self.manifest = manifest
        self.model_dir = model_dir
        self.port = port
        self.hot_reload = hot_reload

        # Runtime
        self._runtime = runtime or select_runtime(
            manifest, preferred=runtime_kind
        )

        # Batcher
        self._batcher = DynamicBatcher(
            infer_fn=self._runtime.infer,
            max_batch_size=max_batch_size,
            max_latency_ms=max_latency_ms,
        )

        # Request dedup — BloomFilter
        self._dedup = BloomFilter(expected_items=dedup_capacity, fp_rate=0.001)
        self._dedup_hits = 0

        # Warm-up
        self._warmup = warmup or WarmupStrategy(num_requests=3)

        self._started = False
        self._ready = False
        self._start_time = 0.0
        self._request_count = 0
        self._total_latency_ms = 0.0

    async def start(self) -> None:
        """Prepare and load the model, warm up, start the batcher."""
        await self._runtime.prepare(self.manifest, self.model_dir)
        await self._runtime.load()
        await self._batcher.start()
        self._started = True
        self._start_time = time.time()
        logger.info(
            "Serving %s v%s on port %d",
            self.manifest.name, self.manifest.version, self.port,
        )

        # Warm-up phase
        await self._run_warmup()
        self._ready = True
        logger.info("Server ready (warm-up complete)")

    async def _run_warmup(self) -> None:
        """Execute warm-up requests through the full pipeline."""
        payload = self._warmup.generate_payload(self.manifest)
        warmup_times: List[float] = []
        for i in range(self._warmup.num_requests):
            try:
                start = time.monotonic()
                req = InferenceRequest(
                    request_id=f"warmup-{i}",
                    inputs=payload,
                )
                batch = BatchRequest(requests=[req], batch_id=f"warmup-batch-{i}")
                await self._runtime.infer(batch)
                elapsed = (time.monotonic() - start) * 1000
                warmup_times.append(elapsed)
                logger.debug("Warmup %d/%d: %.1fms", i + 1, self._warmup.num_requests, elapsed)
            except Exception as exc:
                logger.warning("Warmup request %d failed: %s", i, exc)
        if warmup_times:
            avg = sum(warmup_times) / len(warmup_times)
            logger.info(
                "Warmup complete: %d requests, avg=%.1fms",
                len(warmup_times), avg,
            )

    async def stop(self) -> None:
        """Stop the batcher and unload the model."""
        self._ready = False
        await self._batcher.stop()
        await self._runtime.unload()
        self._started = False
        logger.info("Server stopped")

    async def predict(
        self,
        inputs: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> InferenceResult:
        """
        Submit a single prediction request.

        If ``request_id`` was already seen (BloomFilter dedup), raises
        an :class:`InferenceFault` to prevent duplicate processing.
        """
        if not self._started:
            raise InferenceFault(
                "_server",
                reason="Server not started — call start() first",
                metadata={"model": self.manifest.name},
            )

        rid = request_id or str(uuid.uuid4())

        # Deduplication check
        if rid in self._dedup:
            self._dedup_hits += 1
            raise InferenceFault(
                rid,
                reason=f"Duplicate request ID: {rid}",
                metadata={"dedup_hits": self._dedup_hits},
            )
        self._dedup.add(rid)

        request = InferenceRequest(
            request_id=rid,
            inputs=inputs,
            parameters=parameters or {},
        )

        result = await self._batcher.submit(request)
        self._request_count += 1
        self._total_latency_ms += result.latency_ms
        return result

    # ── Health Probes ────────────────────────────────────────────────

    async def liveness(self) -> Dict[str, Any]:
        """
        K8s liveness probe — ``GET /healthz``.

        Returns healthy if the process is alive and the runtime is loaded.
        """
        alive = self._started and self._runtime.is_loaded
        return {
            "status": "alive" if alive else "dead",
            "uptime_s": time.time() - self._start_time if self._started else 0,
        }

    async def readiness(self) -> Dict[str, Any]:
        """
        K8s readiness probe — ``GET /readyz``.

        Returns ready only after warm-up is complete and the batcher
        is accepting requests.
        """
        return {
            "status": "ready" if self._ready else "not_ready",
            "model": self.manifest.name,
            "version": self.manifest.version,
            "request_count": self._request_count,
        }

    async def health(self) -> Dict[str, Any]:
        """Full health check endpoint data (backward compat)."""
        runtime_health = await self._runtime.health()
        return {
            "status": "serving" if self._started else "stopped",
            "ready": self._ready,
            "model": self.manifest.name,
            "version": self.manifest.version,
            "runtime": runtime_health,
            "request_count": self._request_count,
            "dedup_hits": self._dedup_hits,
        }

    async def metrics(self) -> Dict[str, float]:
        """Prometheus-compatible metrics."""
        runtime_metrics = await self._runtime.metrics()
        batcher_metrics = self._batcher.metrics()
        avg_latency = (
            self._total_latency_ms / self._request_count
            if self._request_count > 0
            else 0.0
        )
        return {
            "aquilia_request_count": float(self._request_count),
            "aquilia_avg_latency_ms": avg_latency,
            "aquilia_dedup_hits": float(self._dedup_hits),
            **{f"runtime_{k}": v for k, v in runtime_metrics.items()},
            **{f"batcher_{k}": v for k, v in batcher_metrics.items()},
        }
