"""
Tests for aquilia.mlops.serving - batching, router.
"""

import pytest

from aquilia.mlops.serving.batching import DynamicBatcher
from aquilia.mlops.serving.router import TrafficRouter
from aquilia.mlops._types import (
    BatchingStrategy,
    BatchRequest,
    InferenceRequest,
    InferenceResult,
    RolloutStrategy,
)


class TestDynamicBatcher:
    @staticmethod
    async def _predict(batch: BatchRequest):
        results = []
        for req in batch.requests:
            results.append(
                InferenceResult(
                    request_id=req.request_id,
                    outputs=req.inputs,
                    latency_ms=1.0,
                )
            )
        return results

    async def test_single_request(self):
        import asyncio
        batcher = DynamicBatcher(
            infer_fn=TestDynamicBatcher._predict,
            max_batch_size=4,
            max_latency_ms=100,
        )
        await batcher.start()
        try:
            req = InferenceRequest(request_id="r1", inputs={"x": [1.0, 2.0]})
            result = await batcher.submit(req)
            assert result.request_id == req.request_id
            assert result.outputs == {"x": [1.0, 2.0]}
        finally:
            await batcher.stop()

    async def test_batch_collects_multiple(self):
        import asyncio
        batcher = DynamicBatcher(
            infer_fn=TestDynamicBatcher._predict,
            max_batch_size=4,
            max_latency_ms=200,
        )
        await batcher.start()
        try:
            reqs = [InferenceRequest(request_id=f"r{i}", inputs={"x": [float(i)]}) for i in range(3)]
            results = await asyncio.gather(*[batcher.submit(r) for r in reqs])
            assert len(results) == 3
            ids = {r.request_id for r in results}
            assert len(ids) == 3
        finally:
            await batcher.stop()


class TestTrafficRouter:
    def test_canary_routing_single_target(self):
        router = TrafficRouter()
        router.add_target("v1", weight=1.0)
        versions = {router.route(f"req-{i}") for i in range(50)}
        assert versions == {"v1"}

    def test_canary_routing_100pct(self):
        router = TrafficRouter()
        router.add_target("v1", weight=0.0)
        router.add_target("v2", weight=1.0)
        router.set_strategy(RolloutStrategy.CANARY)
        versions = {router.route(f"req-{i}") for i in range(50)}
        assert versions == {"v2"}

    def test_shadow_routing(self):
        router = TrafficRouter()
        router.add_target("v1", weight=0.8)
        router.add_target("v2", weight=0.2)
        router.set_strategy(RolloutStrategy.SHADOW)
        version = router.route("req-1")
        assert version == "v1"

    def test_record_result_and_metrics(self):
        router = TrafficRouter()
        router.add_target("v1", weight=0.5)
        router.add_target("v2", weight=0.5)
        router.record_result("v1", latency_ms=10.0, error=False)
        router.record_result("v1", latency_ms=20.0, error=False)
        router.record_result("v2", latency_ms=15.0, error=True)
        metrics = router.get_metrics()
        assert "v1" in metrics
        assert "v2" in metrics
        assert metrics["v1"]["request_count"] == 2
        assert metrics["v2"]["error_rate"] == 1.0
