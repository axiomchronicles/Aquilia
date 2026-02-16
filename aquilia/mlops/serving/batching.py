"""
Dynamic Batching Scheduler.

Collects incoming inference requests and groups them into batches
using configurable strategies: size-triggered, time-triggered, or hybrid.

Algorithm::

    loop:
        collect requests from queue
        if len(batch) >= max_batch_size OR elapsed >= max_latency_ms:
            yield batch
        else:
            wait(remaining time)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from .._types import (
    BatchRequest,
    BatchingStrategy,
    InferenceRequest,
    InferenceResult,
)

logger = logging.getLogger("aquilia.mlops.serving.batching")


class _PendingRequest:
    """Internal wrapper for a queued request."""

    __slots__ = ("request", "future", "enqueue_time")

    def __init__(self, request: InferenceRequest):
        self.request = request
        self.future: asyncio.Future[InferenceResult] = asyncio.get_running_loop().create_future()
        self.enqueue_time = time.monotonic()


class DynamicBatcher:
    """
    Async dynamic batching scheduler.

    Aggregates individual inference requests into batches and dispatches
    them to the runtime's ``infer()`` method.

    Parameters:
        infer_fn: Async callable that processes a ``BatchRequest``.
        max_batch_size: Maximum number of requests per batch.
        max_latency_ms: Maximum time (ms) to wait before dispatching.
        strategy: Batching strategy (size, time, or hybrid).
    """

    def __init__(
        self,
        infer_fn: Callable[[BatchRequest], Any],
        max_batch_size: int = 16,
        max_latency_ms: float = 50.0,
        strategy: BatchingStrategy = BatchingStrategy.HYBRID,
    ):
        self._infer_fn = infer_fn
        self.max_batch_size = max_batch_size
        self.max_latency_ms = max_latency_ms
        self.strategy = strategy

        self._queue: asyncio.Queue[_PendingRequest] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._batches_processed = 0
        self._total_batch_size = 0
        self._total_wait_ms = 0.0

    async def start(self) -> None:
        """Start the background batcher coroutine."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._batch_loop())
        logger.info(
            "Batcher started (max_batch=%d, max_latency=%.1fms, strategy=%s)",
            self.max_batch_size, self.max_latency_ms, self.strategy.value,
        )

    async def stop(self) -> None:
        """Stop the batcher."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def submit(self, request: InferenceRequest) -> InferenceResult:
        """
        Submit a single request and wait for its result.

        The request is enqueued into the batcher and will be processed
        in the next batch.
        """
        pending = _PendingRequest(request)
        await self._queue.put(pending)
        return await pending.future

    def metrics(self) -> Dict[str, float]:
        """Return batcher metrics."""
        avg_batch = (
            self._total_batch_size / self._batches_processed
            if self._batches_processed > 0
            else 0.0
        )
        avg_wait = (
            self._total_wait_ms / self._batches_processed
            if self._batches_processed > 0
            else 0.0
        )
        return {
            "batches_processed": float(self._batches_processed),
            "avg_batch_size": avg_batch,
            "avg_wait_ms": avg_wait,
            "queue_size": float(self._queue.qsize()),
        }

    # ── Internal ─────────────────────────────────────────────────────

    async def _batch_loop(self) -> None:
        """Main batching loop."""
        while self._running:
            batch: List[_PendingRequest] = []
            deadline = time.monotonic() + (self.max_latency_ms / 1000.0)

            try:
                # Wait for the first request
                first = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,  # wake up periodically
                )
                batch.append(first)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                continue

            # Collect more requests up to batch size or deadline
            while len(batch) < self.max_batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break

                try:
                    item = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=remaining,
                    )
                    batch.append(item)
                except asyncio.TimeoutError:
                    break
                except asyncio.CancelledError:
                    break

            if not batch:
                continue

            # Dispatch batch
            await self._dispatch(batch)

    async def _dispatch(self, pending: List[_PendingRequest]) -> None:
        """Dispatch a batch of requests to the runtime."""
        batch_id = str(uuid.uuid4())[:8]
        requests = [p.request for p in pending]
        batch = BatchRequest(requests=requests, batch_id=batch_id)

        wait_ms = (time.monotonic() - pending[0].enqueue_time) * 1000

        try:
            results = await self._infer_fn(batch)

            # Map results back to futures
            result_map = {r.request_id: r for r in results}
            for p in pending:
                result = result_map.get(p.request.request_id)
                if result and not p.future.done():
                    p.future.set_result(result)
                elif not p.future.done():
                    p.future.set_exception(
                        RuntimeError(f"No result for request {p.request.request_id}")
                    )

            self._batches_processed += 1
            self._total_batch_size += len(pending)
            self._total_wait_ms += wait_ms

        except Exception as e:
            logger.error("Batch inference failed: %s", e)
            for p in pending:
                if not p.future.done():
                    p.future.set_exception(e)
