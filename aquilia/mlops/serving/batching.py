"""
Dynamic Batching Scheduler.

Collects incoming inference requests and groups them into batches
using configurable strategies: size-triggered, time-triggered, or hybrid.

Supports:
- Standard SLM batching (size / time / hybrid triggers)
- Continuous batching for LLM serving (token-budget-aware draining)
- Priority-based request ordering (higher priority first)
- Adaptive batch sizing based on latency feedback

Algorithm::

    loop:
        collect requests from queue
        if len(batch) >= max_batch_size OR elapsed >= max_latency_ms:
            yield batch
        else:
            wait(remaining time)

For continuous batching::

    loop:
        drain requests up to token_budget from priority queue
        dispatch batch
        incoming requests join next iteration (no head-of-line blocking)
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .._types import (
    BatchRequest,
    BatchingStrategy,
    InferenceRequest,
    InferenceResult,
    StreamChunk,
)

logger = logging.getLogger("aquilia.mlops.serving.batching")


class _PendingRequest:
    """Internal wrapper for a queued request with priority ordering."""

    __slots__ = ("request", "future", "enqueue_time", "priority", "estimated_tokens")

    def __init__(self, request: InferenceRequest):
        self.request = request
        self.future: asyncio.Future[InferenceResult] = asyncio.get_running_loop().create_future()
        self.enqueue_time = time.monotonic()
        self.priority: int = getattr(request, "priority", 5)
        # Estimate token count from input length (rough heuristic for LLMs)
        self.estimated_tokens: int = getattr(request, "max_tokens", 0) or self._estimate_tokens()

    def _estimate_tokens(self) -> int:
        """Rough token estimation from input data size."""
        inputs = self.request.inputs
        if isinstance(inputs, dict):
            text = inputs.get("text", inputs.get("prompt", inputs.get("input", "")))
            if isinstance(text, str):
                # ~4 chars per token is a reasonable average for English
                return max(1, len(text) // 4)
        return 1

    def __lt__(self, other: "_PendingRequest") -> bool:
        """Higher priority (lower number) sorts first; ties broken by arrival."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.enqueue_time < other.enqueue_time


class DynamicBatcher:
    """
    Async dynamic batching scheduler.

    Aggregates individual inference requests into batches and dispatches
    them to the runtime's ``infer()`` method.

    Supports two modes:
    - **Standard**: Size/time/hybrid triggered batching for SLMs.
    - **Continuous**: Token-budget-aware draining with priority ordering
      for LLM workloads where request sizes vary dramatically.

    Parameters:
        infer_fn: Async callable that processes a ``BatchRequest``.
        max_batch_size: Maximum number of requests per batch.
        max_latency_ms: Maximum time (ms) to wait before dispatching.
        strategy: Batching strategy (size, time, or hybrid).
        token_budget: Max total tokens per batch (0 = unlimited, for continuous batching).
        continuous: Enable continuous batching mode (priority queue + token budget).
    """

    def __init__(
        self,
        infer_fn: Callable[[BatchRequest], Any],
        max_batch_size: int = 16,
        max_latency_ms: float = 50.0,
        strategy: BatchingStrategy = BatchingStrategy.HYBRID,
        token_budget: int = 0,
        continuous: bool = False,
    ):
        self._infer_fn = infer_fn
        self.max_batch_size = max_batch_size
        self.max_latency_ms = max_latency_ms
        self.strategy = strategy
        self._token_budget = token_budget
        self._continuous = continuous

        self._queue: asyncio.Queue[_PendingRequest] = asyncio.Queue()
        # Priority heap for continuous batching
        self._priority_heap: List[_PendingRequest] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Adaptive sizing: track recent batch latencies for feedback
        self._recent_latencies: List[float] = []
        self._adaptive_max: int = max_batch_size

        # Metrics
        self._batches_processed = 0
        self._total_batch_size = 0
        self._total_wait_ms = 0.0
        self._total_tokens_processed = 0
        self._priority_dispatches = 0

    async def start(self) -> None:
        """Start the background batcher coroutine."""
        if self._running:
            return
        self._running = True
        if self._continuous:
            self._task = asyncio.create_task(self._continuous_batch_loop())
            mode = "continuous"
        else:
            self._task = asyncio.create_task(self._batch_loop())
            mode = self.strategy.value
        logger.info(
            "Batcher started (max_batch=%d, max_latency=%.1fms, mode=%s, token_budget=%d)",
            self.max_batch_size, self.max_latency_ms, mode, self._token_budget,
        )

    async def stop(self) -> None:
        """Stop the batcher and drain remaining requests."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # Fail remaining queued requests
        while not self._queue.empty():
            try:
                pending = self._queue.get_nowait()
                if not pending.future.done():
                    pending.future.set_exception(RuntimeError("Batcher stopped"))
            except asyncio.QueueEmpty:
                break
        for pending in self._priority_heap:
            if not pending.future.done():
                pending.future.set_exception(RuntimeError("Batcher stopped"))
        self._priority_heap.clear()

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
            "heap_size": float(len(self._priority_heap)),
            "total_tokens_processed": float(self._total_tokens_processed),
            "priority_dispatches": float(self._priority_dispatches),
            "adaptive_max_batch": float(self._adaptive_max),
            "continuous_mode": float(self._continuous),
        }

    # ── Internal: Standard batching ──────────────────────────────────

    async def _batch_loop(self) -> None:
        """Main batching loop (standard mode)."""
        while self._running:
            batch: List[_PendingRequest] = []
            deadline = time.monotonic() + (self.max_latency_ms / 1000.0)

            try:
                first = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
                batch.append(first)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                continue

            # Collect more requests up to adaptive batch size or deadline
            effective_max = self._adaptive_max
            while len(batch) < effective_max:
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

            await self._dispatch(batch)

    # ── Internal: Continuous batching ────────────────────────────────

    async def _continuous_batch_loop(self) -> None:
        """
        Continuous batching loop for LLM workloads.

        Drains requests from a priority heap respecting the token budget.
        New requests arriving mid-batch join the next iteration — no
        head-of-line blocking.
        """
        while self._running:
            # Move all queued requests into the priority heap
            await self._drain_queue_to_heap()

            if not self._priority_heap:
                # Wait for at least one request
                try:
                    first = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    heapq.heappush(self._priority_heap, first)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    continue

            # Build batch from heap respecting token budget
            batch: List[_PendingRequest] = []
            tokens_in_batch = 0
            remaining_heap: List[_PendingRequest] = []

            while self._priority_heap and len(batch) < self._adaptive_max:
                candidate = heapq.heappop(self._priority_heap)
                candidate_tokens = candidate.estimated_tokens

                if self._token_budget > 0 and tokens_in_batch + candidate_tokens > self._token_budget:
                    # Over budget — push back
                    remaining_heap.append(candidate)
                    continue

                batch.append(candidate)
                tokens_in_batch += candidate_tokens

            # Restore un-batched items
            for item in remaining_heap:
                heapq.heappush(self._priority_heap, item)

            if batch:
                self._total_tokens_processed += tokens_in_batch
                self._priority_dispatches += 1
                await self._dispatch(batch)

    async def _drain_queue_to_heap(self) -> None:
        """Move all queued requests into the priority heap."""
        while not self._queue.empty():
            try:
                pending = self._queue.get_nowait()
                heapq.heappush(self._priority_heap, pending)
            except asyncio.QueueEmpty:
                break

    # ── Internal: Dispatch ───────────────────────────────────────────

    async def _dispatch(self, pending: List[_PendingRequest]) -> None:
        """Dispatch a batch of requests to the runtime."""
        batch_id = str(uuid.uuid4())[:8]
        requests = [p.request for p in pending]
        batch = BatchRequest(requests=requests, batch_id=batch_id)

        wait_ms = (time.monotonic() - pending[0].enqueue_time) * 1000
        dispatch_start = time.monotonic()

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

            # Adaptive sizing: if latency is low, try larger batches; if high, shrink
            dispatch_ms = (time.monotonic() - dispatch_start) * 1000
            self._adapt_batch_size(dispatch_ms)

        except Exception as e:
            logger.error("Batch inference failed: %s", e)
            for p in pending:
                if not p.future.done():
                    p.future.set_exception(e)

    # ── Internal: Adaptive sizing ────────────────────────────────────

    def _adapt_batch_size(self, latency_ms: float) -> None:
        """Adjust max batch size based on recent dispatch latencies."""
        self._recent_latencies.append(latency_ms)
        # Keep a window of last 20 batches
        if len(self._recent_latencies) > 20:
            self._recent_latencies = self._recent_latencies[-20:]

        if len(self._recent_latencies) < 5:
            return  # not enough data

        avg = sum(self._recent_latencies) / len(self._recent_latencies)

        # If avg latency < 60% of budget, try larger batches
        if avg < self.max_latency_ms * 0.6:
            self._adaptive_max = min(self._adaptive_max + 1, self.max_batch_size * 2)
        # If avg latency > 90% of budget, shrink
        elif avg > self.max_latency_ms * 0.9:
            self._adaptive_max = max(self._adaptive_max - 1, 1)
