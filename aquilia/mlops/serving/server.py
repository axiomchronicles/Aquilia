"""
Model Serving Server — dev and production serving with typed endpoints.

Integrates with Aquilia's ASGI + controller architecture and provides:
- Auto-generated ``/predict``, ``/health``, ``/metrics`` endpoints
- Hot-reload in dev mode
- Runtime selection and lifecycle management
- **BloomFilter** request deduplication (reject duplicate request IDs)
- **Health probes** — K8s ``/healthz`` (liveness) and ``/readyz`` (readiness)
- **Warm-up** — pre-inference warmup with synthetic payloads on ``start()``
- **Streaming** — async generator streaming for LLM token-by-token output
- **Circuit Breaker** — fail-fast protection against cascading failures
- **Rate Limiting** — token-bucket throttling per endpoint
- **Memory Management** — GPU/CPU memory tracking with soft/hard limits
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from .._types import (
    BatchRequest,
    CircuitBreakerConfig,
    InferenceRequest,
    InferenceResult,
    LLMConfig,
    ModelpackManifest,
    RuntimeKind,
    StreamChunk,
    TokenUsage,
)
from .._structures import (
    BloomFilter,
    CircuitBreaker,
    MemoryTracker,
    TokenBucketRateLimiter,
)
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
    probes, warm-up, circuit breaker, rate limiting, streaming,
    and memory management into a single entry point.

    Usage::

        server = ModelServingServer(manifest=manifest, model_dir="./unpacked")
        await server.start()
        result = await server.predict({"features": [1.0, 2.0, 3.0]})
        await server.stop()

    Streaming (LLM)::

        async for chunk in server.stream_predict({"prompt": "Hello"}):
            print(chunk.token, end="", flush=True)
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
        # Circuit breaker
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        # Rate limiter
        rate_limit_rps: float = 0.0,
        rate_limit_capacity: int = 0,
        # Memory management
        memory_soft_limit_mb: int = 0,
        memory_hard_limit_mb: int = 0,
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

        # Circuit Breaker
        cb_cfg = circuit_breaker_config or CircuitBreakerConfig()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=cb_cfg.failure_threshold,
            success_threshold=cb_cfg.success_threshold,
            timeout_seconds=cb_cfg.timeout_seconds,
            half_open_max_calls=cb_cfg.half_open_max_calls,
        )

        # Rate Limiter (disabled if rps == 0)
        self._rate_limiter: Optional[TokenBucketRateLimiter] = None
        if rate_limit_rps > 0:
            cap = rate_limit_capacity or int(rate_limit_rps * 10)
            self._rate_limiter = TokenBucketRateLimiter(
                rate=rate_limit_rps, capacity=cap,
            )

        # Memory Tracker (disabled if limits == 0)
        self._memory_tracker: Optional[MemoryTracker] = None
        if memory_hard_limit_mb > 0:
            self._memory_tracker = MemoryTracker(
                soft_limit_mb=memory_soft_limit_mb or memory_hard_limit_mb,
                hard_limit_mb=memory_hard_limit_mb,
            )

        self._started = False
        self._ready = False
        self._start_time = 0.0
        self._request_count = 0
        self._stream_count = 0
        self._total_latency_ms = 0.0
        self._total_tokens_generated = 0

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
        priority: int = 0,
        max_tokens: int = 0,
        timeout_ms: float = 0.0,
    ) -> InferenceResult:
        """
        Submit a single prediction request.

        Applies circuit breaker, rate limiting, and dedup checks before
        forwarding to the batcher.
        """
        if not self._started:
            raise InferenceFault(
                "_server",
                reason="Server not started — call start() first",
                metadata={"model": self.manifest.name},
            )

        # Circuit breaker check
        if not self._circuit_breaker.allow_request():
            raise InferenceFault(
                "_circuit_breaker",
                reason="Circuit breaker OPEN — service degraded",
                metadata={"state": self._circuit_breaker.state},
            )

        # Rate limiting check
        if self._rate_limiter and not self._rate_limiter.acquire():
            raise InferenceFault(
                "_rate_limit",
                reason="Rate limit exceeded",
                metadata=self._rate_limiter.stats,
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
            priority=priority,
            max_tokens=max_tokens,
            timeout_ms=timeout_ms,
        )

        try:
            result = await self._batcher.submit(request)
            self._circuit_breaker.record_success()
            self._request_count += 1
            self._total_latency_ms += result.latency_ms
            self._total_tokens_generated += result.token_count
            return result
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise

    async def stream_predict(
        self,
        inputs: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        max_tokens: int = 0,
    ) -> AsyncIterator[StreamChunk]:
        """
        Submit a streaming prediction request (LLM token-by-token output).

        Yields :class:`StreamChunk` objects as tokens are generated.
        Requires the runtime to implement ``stream_infer``.
        """
        if not self._started:
            raise InferenceFault(
                "_server",
                reason="Server not started — call start() first",
                metadata={"model": self.manifest.name},
            )

        if not self._circuit_breaker.allow_request():
            raise InferenceFault(
                "_circuit_breaker",
                reason="Circuit breaker OPEN — service degraded",
                metadata={"state": self._circuit_breaker.state},
            )

        if self._rate_limiter and not self._rate_limiter.acquire():
            raise InferenceFault(
                "_rate_limit",
                reason="Rate limit exceeded",
                metadata=self._rate_limiter.stats,
            )

        rid = request_id or str(uuid.uuid4())

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
            stream=True,
            max_tokens=max_tokens,
        )

        # Check if runtime supports streaming
        if not hasattr(self._runtime, "stream_infer"):
            raise InferenceFault(
                rid,
                reason="Runtime does not support streaming inference",
                metadata={"runtime": type(self._runtime).__name__},
            )

        try:
            self._stream_count += 1
            total_tokens = 0
            async for chunk in self._runtime.stream_infer(request):
                total_tokens += 1
                yield chunk
                if chunk.is_finished:
                    break
            self._circuit_breaker.record_success()
            self._total_tokens_generated += total_tokens
        except Exception:
            self._circuit_breaker.record_failure()
            raise

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
            "model_type": self.manifest.model_type,
            "is_llm": self.manifest.is_llm,
            "runtime": runtime_health,
            "request_count": self._request_count,
            "stream_count": self._stream_count,
            "dedup_hits": self._dedup_hits,
            "circuit_breaker": self._circuit_breaker.stats,
            "rate_limiter": self._rate_limiter.stats if self._rate_limiter else None,
            "memory": self._memory_tracker.stats if self._memory_tracker else None,
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
        m: Dict[str, float] = {
            "aquilia_request_count": float(self._request_count),
            "aquilia_stream_count": float(self._stream_count),
            "aquilia_avg_latency_ms": avg_latency,
            "aquilia_dedup_hits": float(self._dedup_hits),
            "aquilia_total_tokens_generated": float(self._total_tokens_generated),
            "aquilia_circuit_breaker_state": (
                0.0 if self._circuit_breaker.state == "closed"
                else 1.0 if self._circuit_breaker.state == "open"
                else 0.5
            ),
            **{f"runtime_{k}": v for k, v in runtime_metrics.items()},
            **{f"batcher_{k}": v for k, v in batcher_metrics.items()},
        }
        if self._rate_limiter:
            rl = self._rate_limiter.stats
            m["aquilia_rate_limit_allowed"] = float(rl["total_allowed"])
            m["aquilia_rate_limit_rejected"] = float(rl["total_rejected"])
        if self._memory_tracker:
            ms = self._memory_tracker.stats
            m["aquilia_memory_usage_mb"] = float(ms["current_usage_mb"])
            m["aquilia_memory_model_count"] = float(ms["model_count"])
        return m

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Access the circuit breaker for external inspection."""
        return self._circuit_breaker

    @property
    def rate_limiter(self) -> Optional[TokenBucketRateLimiter]:
        """Access the rate limiter for external inspection."""
        return self._rate_limiter

    @property
    def memory_tracker(self) -> Optional[MemoryTracker]:
        """Access the memory tracker for external inspection."""
        return self._memory_tracker
