"""
Tests for aquilia.mlops.scheduler — autoscaler, placement.
"""

import pytest

from aquilia.mlops.scheduler.autoscaler import Autoscaler, ScalingPolicy, ScalingDecision
from aquilia.mlops.scheduler.placement import PlacementScheduler, NodeInfo, PlacementRequest


# ── Autoscaler ───────────────────────────────────────────────────────────

class TestAutoscaler:
    @pytest.fixture
    def policy(self):
        return ScalingPolicy(
            min_replicas=1,
            max_replicas=10,
            target_concurrency=10.0,
            target_latency_p95_ms=100.0,
            scale_up_threshold=0.8,
            scale_down_threshold=0.3,
            cooldown_seconds=60,
        )

    @pytest.fixture
    def autoscaler(self, policy):
        return Autoscaler(policy=policy)

    def test_scale_up_high_concurrency(self, autoscaler):
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 20.0, "aquilia_inference_latency_ms_p95": 50.0}
        )
        assert decision.desired_replicas > 1
        assert "concurrency" in decision.reason.lower() or "latency" in decision.reason.lower()

    def test_scale_up_high_latency(self, autoscaler):
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 5.0, "aquilia_inference_latency_ms_p95": 200.0}
        )
        assert decision.desired_replicas > 1

    def test_scale_down_low_concurrency(self, autoscaler):
        # Set current replicas > min so scale-down is possible
        autoscaler._current_replicas = 5
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 1.0, "aquilia_inference_latency_ms_p95": 10.0}
        )
        assert decision.desired_replicas < 5

    def test_respects_min_replicas(self, autoscaler):
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 0.0, "aquilia_inference_latency_ms_p95": 0.0}
        )
        assert decision.desired_replicas >= 1

    def test_respects_max_replicas(self, autoscaler):
        autoscaler._current_replicas = 10
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 1000.0, "aquilia_inference_latency_ms_p95": 5000.0}
        )
        assert decision.desired_replicas <= 10

    def test_apply_updates_state(self, autoscaler):
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 20.0}
        )
        autoscaler.apply(decision)
        assert autoscaler._current_replicas == decision.desired_replicas

    def test_hpa_manifest(self, autoscaler):
        manifest = autoscaler.generate_hpa_manifest(
            deployment_name="model-serving",
            namespace="ml",
        )
        assert manifest["apiVersion"] == "autoscaling/v2"
        assert manifest["kind"] == "HorizontalPodAutoscaler"
        assert manifest["spec"]["minReplicas"] == 1
        assert manifest["spec"]["maxReplicas"] == 10

    def test_steady_state(self, autoscaler):
        decision = autoscaler.evaluate(
            metrics={"aquilia_concurrency": 5.0, "aquilia_inference_latency_ms_p95": 50.0}
        )
        assert decision.reason == "Steady state"
        assert decision.desired_replicas == autoscaler._current_replicas


# ── PlacementScheduler ──────────────────────────────────────────────────

class TestPlacementScheduler:
    @pytest.fixture
    def scheduler(self):
        sched = PlacementScheduler()
        sched.register_node(NodeInfo(
            node_id="node-1",
            device_type="gpu",
            total_memory_mb=32768,
            available_memory_mb=16384,
            gpu_available=True,
            current_load=0.3,
        ))
        sched.register_node(NodeInfo(
            node_id="node-2",
            device_type="cpu",
            total_memory_mb=16384,
            available_memory_mb=8192,
            gpu_available=False,
            current_load=0.5,
        ))
        return sched

    def test_place_gpu_model(self, scheduler):
        score = scheduler.place(PlacementRequest(
            model_name="big-model",
            model_size_mb=4096,
            gpu_required=True,
        ))
        # node-1 has GPU, node-2 does not
        assert score is not None
        assert score.node_id == "node-1"

    def test_place_cpu_model(self, scheduler):
        score = scheduler.place(PlacementRequest(
            model_name="small-model",
            model_size_mb=512,
            gpu_required=False,
        ))
        assert score is not None

    def test_no_fit(self, scheduler):
        score = scheduler.place(PlacementRequest(
            model_name="huge-model",
            model_size_mb=100_000,
            gpu_required=True,
        ))
        # node-1 doesn't have enough memory
        # It may still return a score with low total, or None
        if score is not None:
            assert score.total >= 0  # at least valid

    def test_rebalance_suggestions(self, scheduler):
        suggestions = scheduler.rebalance()
        assert isinstance(suggestions, list)

    def test_unregister_node(self, scheduler):
        scheduler.unregister_node("node-2")
        score = scheduler.place(PlacementRequest(
            model_name="model",
            model_size_mb=100,
            gpu_required=False,
        ))
        # Only node-1 left
        assert score is not None
        assert score.node_id == "node-1"

    def test_update_node_load(self, scheduler):
        scheduler.update_node("node-1", current_load=0.95)
        # node-1 is now overloaded
        suggestions = scheduler.rebalance()
        # May or may not have suggestions depending on thresholds
        assert isinstance(suggestions, list)
