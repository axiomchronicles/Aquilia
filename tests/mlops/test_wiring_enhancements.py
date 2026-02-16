"""
Tests for Phase 3 enhancements:

1. __slots__ on _types.py dataclasses
2. SlidingWindow → Autoscaler wiring
3. BloomFilter → ModelServingServer request dedup
4. ConsistentHash → TrafficRouter sticky routing
5. TopKHeap → MetricsCollector hot-model tracking
6. Health probes (liveness / readiness)
7. Warm-up strategies
8. CLI lineage / experiment commands
9. Controller lineage / experiment / health endpoints
"""

import asyncio
import math
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════════════
# 1. __slots__ on dataclasses
# ═══════════════════════════════════════════════════════════════════════════


class TestSlotsOptimization:
    """Verify that mutable dataclasses in _types.py use __slots__."""

    def test_provenance_has_slots(self):
        from aquilia.mlops._types import Provenance
        p = Provenance(git_sha="abc")
        assert hasattr(Provenance, "__slots__")
        with pytest.raises(AttributeError):
            p.arbitrary_attr = 42

    def test_modelpack_manifest_has_slots(self):
        from aquilia.mlops._types import ModelpackManifest
        m = ModelpackManifest(name="x", version="v1", framework="custom", entrypoint="m.pkl")
        assert hasattr(ModelpackManifest, "__slots__")
        with pytest.raises(AttributeError):
            m.not_a_field = True

    def test_inference_request_has_slots(self):
        from aquilia.mlops._types import InferenceRequest
        r = InferenceRequest(request_id="1", inputs={})
        assert hasattr(InferenceRequest, "__slots__")
        with pytest.raises(AttributeError):
            r.rogue = 99

    def test_inference_result_has_slots(self):
        from aquilia.mlops._types import InferenceResult
        r = InferenceResult(request_id="1", outputs={})
        assert hasattr(InferenceResult, "__slots__")
        with pytest.raises(AttributeError):
            r.rogue = 99

    def test_batch_request_has_slots(self):
        from aquilia.mlops._types import BatchRequest
        b = BatchRequest(requests=[])
        assert hasattr(BatchRequest, "__slots__")
        with pytest.raises(AttributeError):
            b.rogue = 99

    def test_placement_score_has_slots(self):
        from aquilia.mlops._types import PlacementScore
        p = PlacementScore(node_id="n1")
        assert hasattr(PlacementScore, "__slots__")
        with pytest.raises(AttributeError):
            p.rogue = 99

    def test_rollout_config_has_slots(self):
        from aquilia.mlops._types import RolloutConfig
        r = RolloutConfig(from_version="v1", to_version="v2")
        assert hasattr(RolloutConfig, "__slots__")
        with pytest.raises(AttributeError):
            r.rogue = 99

    def test_drift_report_has_slots(self):
        from aquilia.mlops._types import DriftReport, DriftMethod
        d = DriftReport(method=DriftMethod.PSI, score=0.1, threshold=0.2, is_drifted=False)
        assert hasattr(DriftReport, "__slots__")
        with pytest.raises(AttributeError):
            d.rogue = 99

    def test_frozen_dataclasses_still_work(self):
        """TensorSpec / BlobRef are frozen=True — ensure they still work."""
        from aquilia.mlops._types import TensorSpec, BlobRef
        t = TensorSpec(name="x", dtype="float32", shape=[1, 64])
        assert t.name == "x"
        b = BlobRef(path="/a", digest="sha256:abc", size=100)
        assert b.size == 100


# ═══════════════════════════════════════════════════════════════════════════
# 2. SlidingWindow → Autoscaler
# ═══════════════════════════════════════════════════════════════════════════


class TestAutoscalerSlidingWindow:
    """Verify the autoscaler uses sliding-window data for decisions."""

    def test_record_request_feeds_window(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler, ScalingPolicy

        scaler = Autoscaler(ScalingPolicy(
            window_seconds=10.0, bucket_width=1.0,
        ))
        for _ in range(50):
            scaler.record_request(latency_ms=5.0)

        assert scaler.window_rps > 0
        assert scaler.window_avg_latency > 0

    def test_window_stats_populated(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler

        scaler = Autoscaler()
        scaler.record_request(latency_ms=10.0, error=True)
        stats = scaler.window_stats
        assert "rps" in stats
        assert "avg_latency_ms" in stats
        assert "error_rate" in stats
        assert stats["request_count"] >= 1

    def test_evaluate_uses_window_data_when_no_metrics_given(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler, ScalingPolicy

        scaler = Autoscaler(ScalingPolicy(target_concurrency=5.0))
        # Feed enough data to trigger a decision
        for _ in range(100):
            scaler.record_request(latency_ms=2.0)

        decision = scaler.evaluate()  # no metrics dict passed
        assert decision.current_replicas == 1
        assert decision.reason  # non-empty reason

    def test_evaluate_merges_with_explicit_metrics(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler

        scaler = Autoscaler()
        decision = scaler.evaluate({"aquilia_concurrency": 50.0})
        assert decision.reason.startswith("High concurrency")

    def test_cooldown_prevents_rapid_scaling(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler, ScalingPolicy

        scaler = Autoscaler(ScalingPolicy(
            cooldown_seconds=9999,  # very long cooldown
            target_concurrency=5.0,
        ))
        d1 = scaler.evaluate({"aquilia_concurrency": 100})
        scaler.apply(d1)  # sets _last_scale_time

        d2 = scaler.evaluate({"aquilia_concurrency": 100})
        # Should NOT scale again during cooldown
        assert d2.desired_replicas == d1.desired_replicas

    def test_error_window_tracked(self):
        from aquilia.mlops.scheduler.autoscaler import Autoscaler

        scaler = Autoscaler()
        scaler.record_request(latency_ms=1.0, error=False)
        scaler.record_request(latency_ms=1.0, error=True)
        assert scaler.window_error_rate == 0.5


# ═══════════════════════════════════════════════════════════════════════════
# 3. BloomFilter → ModelServingServer (request dedup)
# ═══════════════════════════════════════════════════════════════════════════


class TestServingServerDedup:
    """Verify request deduplication via BloomFilter."""

    async def test_dedup_rejects_duplicate_request_id(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import (
            ModelpackManifest, InferenceResult, BatchRequest,
        )
        from aquilia.mlops.faults import InferenceFault

        manifest = ModelpackManifest(
            name="test", version="v1", framework="custom", entrypoint="m.pkl",
        )

        async def mock_infer(batch: BatchRequest):
            return [
                InferenceResult(request_id=r.request_id, outputs={"p": 1}, latency_ms=1.0)
                for r in batch.requests
            ]

        runtime = AsyncMock()
        runtime.is_loaded = True
        runtime.infer = mock_infer
        runtime.health = AsyncMock(return_value={"status": "ok"})
        runtime.metrics = AsyncMock(return_value={})
        runtime.prepare = AsyncMock()
        runtime.load = AsyncMock()
        runtime.unload = AsyncMock()

        server = ModelServingServer(
            manifest=manifest,
            model_dir="/tmp",
            runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )
        await server.start()

        # First request succeeds
        result = await server.predict({"x": 1}, request_id="req-001")
        assert result.request_id == "req-001"

        # Same request ID → dedup fault
        with pytest.raises(InferenceFault, match="Duplicate"):
            await server.predict({"x": 1}, request_id="req-001")

        # Different request ID works
        result2 = await server.predict({"x": 2}, request_id="req-002")
        assert result2.request_id == "req-002"

        await server.stop()

    async def test_dedup_counter_increments(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import (
            ModelpackManifest, InferenceResult, BatchRequest,
        )
        from aquilia.mlops.faults import InferenceFault

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )

        async def mock_infer(batch):
            return [InferenceResult(request_id=r.request_id, outputs={}, latency_ms=0.5)
                    for r in batch.requests]

        runtime = AsyncMock()
        runtime.is_loaded = True
        runtime.infer = mock_infer
        runtime.prepare = AsyncMock()
        runtime.load = AsyncMock()
        runtime.unload = AsyncMock()

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )
        await server.start()

        await server.predict({"x": 1}, request_id="dedup-1")
        for _ in range(3):
            with pytest.raises(InferenceFault):
                await server.predict({"x": 1}, request_id="dedup-1")

        assert server._dedup_hits == 3
        await server.stop()


# ═══════════════════════════════════════════════════════════════════════════
# 4. ConsistentHash → TrafficRouter (sticky routing)
# ═══════════════════════════════════════════════════════════════════════════


class TestRouterStickyAndHotModels:
    """Verify sticky routing and hot-model tracking in TrafficRouter."""

    def test_sticky_routing_deterministic(self):
        from aquilia.mlops.serving.router import TrafficRouter

        router = TrafficRouter(sticky_buckets=32)
        router.add_target("v1", 0.5)
        router.add_target("v2", 0.5)

        choices = [router.route_sticky("user-123") for _ in range(10)]
        # All same — consistent hashing is deterministic
        assert len(set(choices)) == 1

    def test_sticky_routing_different_keys_may_differ(self):
        from aquilia.mlops.serving.router import TrafficRouter

        router = TrafficRouter()
        router.add_target("v1", 0.5)
        router.add_target("v2", 0.5)

        results = {router.route_sticky(f"user-{i}") for i in range(100)}
        # With 100 different keys and 2 targets, both should appear
        assert len(results) == 2

    def test_hot_models_tracking(self):
        from aquilia.mlops.serving.router import TrafficRouter

        router = TrafficRouter()
        router.add_target("v1", 0.7)
        router.add_target("v2", 0.3)

        for _ in range(50):
            router.record_result("v1", latency_ms=5.0)
        for _ in range(10):
            router.record_result("v2", latency_ms=5.0)

        hot = router.hot_models(k=5)
        assert len(hot) >= 1
        # v1 should be the hottest
        assert hot[0][0] == "v1"

    def test_route_populates_hot_tracker(self):
        from aquilia.mlops.serving.router import TrafficRouter

        router = TrafficRouter()
        router.add_target("v1", 1.0)

        for _ in range(10):
            router.route("req-x")

        hot = router.hot_models()
        assert any(name == "v1" for name, _ in hot)

    def test_sticky_raises_when_no_targets(self):
        from aquilia.mlops.serving.router import TrafficRouter

        router = TrafficRouter()
        with pytest.raises(RuntimeError):
            router.route_sticky("key")


# ═══════════════════════════════════════════════════════════════════════════
# 5. TopKHeap → MetricsCollector (hot-model tracking)
# ═══════════════════════════════════════════════════════════════════════════


class TestMetricsHotModels:
    """Verify hot-model tracking in MetricsCollector."""

    def test_record_inference_with_model_name(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector(model_name="main")
        mc.record_inference(latency_ms=5.0, model_name="model-a")
        mc.record_inference(latency_ms=3.0, model_name="model-a")
        mc.record_inference(latency_ms=4.0, model_name="model-b")

        hot = mc.hot_models(k=5)
        assert len(hot) >= 1
        # model-a was pushed twice → higher
        assert hot[0][0] == "model-a"

    def test_record_inference_without_model_name(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.record_inference(latency_ms=5.0)  # no model_name
        assert mc.hot_models() == []  # nothing tracked

    def test_hot_k_limit(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector(hot_k=3)
        for i in range(10):
            mc.record_inference(latency_ms=1.0, model_name=f"m-{i}")

        hot = mc.hot_models(k=3)
        assert len(hot) <= 3


# ═══════════════════════════════════════════════════════════════════════════
# 6. Health Probes (liveness / readiness)
# ═══════════════════════════════════════════════════════════════════════════


class TestHealthProbes:
    """Test K8s liveness and readiness probes."""

    async def test_liveness_when_running(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest, InferenceResult, BatchRequest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )

        async def mock_infer(batch):
            return [InferenceResult(request_id=r.request_id, outputs={}, latency_ms=0.5)
                    for r in batch.requests]

        runtime = AsyncMock()
        runtime.is_loaded = True
        runtime.infer = mock_infer
        runtime.prepare = AsyncMock()
        runtime.load = AsyncMock()
        runtime.unload = AsyncMock()

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )
        await server.start()

        live = await server.liveness()
        assert live["status"] == "alive"
        assert live["uptime_s"] >= 0

        ready = await server.readiness()
        assert ready["status"] == "ready"
        assert ready["model"] == "t"

        await server.stop()

    async def test_liveness_when_stopped(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )
        runtime = AsyncMock()
        runtime.is_loaded = False

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )

        live = await server.liveness()
        assert live["status"] == "dead"

    async def test_readiness_not_ready_before_start(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )
        runtime = AsyncMock()

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )

        ready = await server.readiness()
        assert ready["status"] == "not_ready"

    async def test_health_includes_dedup_hits(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest, InferenceResult, BatchRequest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )

        async def mock_infer(batch):
            return [InferenceResult(request_id=r.request_id, outputs={}, latency_ms=0.5)
                    for r in batch.requests]

        runtime = AsyncMock()
        runtime.is_loaded = True
        runtime.infer = mock_infer
        runtime.prepare = AsyncMock()
        runtime.load = AsyncMock()
        runtime.unload = AsyncMock()
        runtime.health = AsyncMock(return_value={"status": "ok"})

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=0),
        )
        await server.start()

        health = await server.health()
        assert "dedup_hits" in health
        assert health["ready"] is True
        await server.stop()


# ═══════════════════════════════════════════════════════════════════════════
# 7. Warm-up Strategies
# ═══════════════════════════════════════════════════════════════════════════


class TestWarmupStrategy:
    """Test pre-inference warm-up."""

    def test_generate_payload_from_manifest(self):
        from aquilia.mlops.serving.server import WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest, TensorSpec

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
            inputs=[
                TensorSpec(name="features", dtype="float32", shape=[1, 10]),
                TensorSpec(name="ids", dtype="int64", shape=[1, 5]),
            ],
        )

        warmup = WarmupStrategy(num_requests=3)
        payload = warmup.generate_payload(manifest)

        assert "features" in payload
        assert len(payload["features"]) == 10
        assert "ids" in payload
        assert len(payload["ids"]) == 5

    def test_custom_payload_overrides(self):
        from aquilia.mlops.serving.server import WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )

        custom = {"my_input": [1, 2, 3]}
        warmup = WarmupStrategy(num_requests=1, synthetic_payload=custom)
        payload = warmup.generate_payload(manifest)
        assert payload == custom

    def test_generate_payload_empty_inputs(self):
        from aquilia.mlops.serving.server import WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )
        warmup = WarmupStrategy()
        payload = warmup.generate_payload(manifest)
        assert payload == {"input": [0.0]}

    async def test_warmup_runs_on_start(self):
        from aquilia.mlops.serving.server import ModelServingServer, WarmupStrategy
        from aquilia.mlops._types import ModelpackManifest, InferenceResult, BatchRequest

        manifest = ModelpackManifest(
            name="t", version="v1", framework="custom", entrypoint="m.pkl",
        )

        infer_calls = []

        async def mock_infer(batch):
            infer_calls.append(batch)
            return [InferenceResult(request_id=r.request_id, outputs={}, latency_ms=0.1)
                    for r in batch.requests]

        runtime = AsyncMock()
        runtime.is_loaded = True
        runtime.infer = mock_infer
        runtime.prepare = AsyncMock()
        runtime.load = AsyncMock()
        runtime.unload = AsyncMock()

        server = ModelServingServer(
            manifest=manifest, model_dir="/tmp", runtime=runtime,
            warmup=WarmupStrategy(num_requests=5),
        )
        await server.start()

        # 5 warmup infer calls should have happened
        assert len(infer_calls) == 5
        assert server._ready is True
        await server.stop()


# ═══════════════════════════════════════════════════════════════════════════
# 8. CLI lineage / experiment commands
# ═══════════════════════════════════════════════════════════════════════════


class TestCLILineageCommands:
    """Test aq lineage CLI commands."""

    def test_lineage_show_group_exists(self):
        from aquilia.cli.commands.mlops_cmds import lineage_group
        assert lineage_group.name == "lineage"

    def test_lineage_has_subcommands(self):
        from aquilia.cli.commands.mlops_cmds import lineage_group

        cmds = {c.name for c in lineage_group.commands.values()}
        assert "show" in cmds
        assert "ancestors" in cmds
        assert "descendants" in cmds
        assert "path" in cmds


class TestCLIExperimentCommands:
    """Test aq experiment CLI commands."""

    def test_experiment_group_exists(self):
        from aquilia.cli.commands.mlops_cmds import experiment_group
        assert experiment_group.name == "experiment"

    def test_experiment_has_subcommands(self):
        from aquilia.cli.commands.mlops_cmds import experiment_group

        cmds = {c.name for c in experiment_group.commands.values()}
        assert "create" in cmds
        assert "list" in cmds
        assert "conclude" in cmds
        assert "summary" in cmds


# ═══════════════════════════════════════════════════════════════════════════
# 9. Controller lineage / experiment / health endpoints
# ═══════════════════════════════════════════════════════════════════════════


class TestControllerEnhancements:
    """Test new controller endpoints."""

    async def test_liveness_endpoint(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.liveness()
        assert result["status"] == "alive"

    async def test_readiness_endpoint(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.readiness()
        assert result["status"] == "ready"

    async def test_liveness_delegates_to_server(self):
        from aquilia.mlops.controller import MLOpsController

        server = AsyncMock()
        server.liveness = AsyncMock(return_value={"status": "alive", "uptime_s": 42})
        ctrl = MLOpsController(serving_server=server)
        result = await ctrl.liveness()
        assert result["status"] == "alive"
        assert result["uptime_s"] == 42

    async def test_lineage_endpoint_no_dag(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.lineage()
        assert "error" in result

    async def test_lineage_endpoint_with_dag(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._structures import ModelLineageDAG

        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("fine", "v1", parents=["base"])

        ctrl = MLOpsController(lineage_dag=dag)
        result = await ctrl.lineage()
        assert result["total"] == 2
        assert "base" in result["roots"]
        assert "fine" in result["leaves"]

    async def test_lineage_ancestors_endpoint(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._structures import ModelLineageDAG

        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("fine", "v1", parents=["base"])

        ctrl = MLOpsController(lineage_dag=dag)
        result = await ctrl.lineage_ancestors("fine")
        assert "base" in result["ancestors"]

    async def test_experiments_endpoint_empty(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.list_experiments()
        assert result["experiments"] == []

    async def test_create_experiment_endpoint(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._structures import ExperimentLedger

        ledger = ExperimentLedger()
        ctrl = MLOpsController(experiment_ledger=ledger)

        result = await ctrl.create_experiment({
            "experiment_id": "test-exp",
            "description": "Test",
            "arms": [
                {"name": "ctrl", "model_version": "v1", "weight": 0.5},
                {"name": "treat", "model_version": "v2", "weight": 0.5},
            ],
        })
        # summary() returns a dict with these keys
        assert "arms" in result
        assert len(result["arms"]) == 2
        assert result["status"] == "active"

    async def test_conclude_experiment_endpoint(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._structures import ExperimentLedger

        ledger = ExperimentLedger()
        ledger.create("exp1", arms=[
            {"name": "a", "model_version": "v1"},
        ])
        ctrl = MLOpsController(experiment_ledger=ledger)

        result = await ctrl.conclude_experiment("exp1", winner="a")
        assert result["status"] == "completed"
        assert result["metadata"]["winner"] == "a"

    async def test_hot_models_endpoint(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.record_inference(5.0, model_name="fast-model")

        ctrl = MLOpsController(metrics_collector=mc)
        result = await ctrl.hot_models(k=5)
        assert len(result["hot_models"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 10. Export verification
# ═══════════════════════════════════════════════════════════════════════════


class TestExports:
    def test_warmup_strategy_exported(self):
        from aquilia.mlops import WarmupStrategy
        assert WarmupStrategy is not None

    def test_all_slots_classes_importable(self):
        from aquilia.mlops import (
            Provenance, ModelpackManifest, InferenceRequest,
            InferenceResult, BatchRequest, PlacementScore,
            RolloutConfig, DriftReport,
        )
        # Smoke — all importable
        assert Provenance is not None
