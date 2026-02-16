"""
Tests for the myapp sklearn MLOps demo — verifies the full lifecycle
(train → pack → deploy → predict → health → lineage → experiments → metrics → undeploy)
using the real Aquilia MLOps platform with an actual sklearn model.
"""

from __future__ import annotations

import asyncio
import os
import pickle
import sys
from pathlib import Path

import pytest

# Ensure myapp is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    """Fresh MlopsService instance per test."""
    from modules.mlops.services import MlopsService
    return MlopsService()


@pytest.fixture
async def deployed_svc(svc):
    """Service with a trained + packed + deployed model."""
    await svc.train()
    await svc.pack()
    await svc.deploy()
    yield svc
    await svc.undeploy()


# ── Training ────────────────────────────────────────────────────────────

class TestTraining:

    async def test_train_returns_metrics(self, svc):
        metrics = await svc.train()
        assert "accuracy" in metrics
        assert "f1_weighted" in metrics
        assert "feature_names" in metrics
        assert "target_names" in metrics
        assert metrics["accuracy"] > 0.7
        assert metrics["n_train"] > 0

    async def test_train_creates_pkl_file(self, svc):
        await svc.train()
        assert svc._model_path is not None
        assert svc._model_path.exists()
        assert svc._model_path.suffix == ".pkl"

    async def test_train_custom_hyperparams(self, svc):
        metrics = await svc.train(n_estimators=50, max_depth=3, test_size=0.3)
        assert metrics["n_estimators"] == 50
        assert metrics["max_depth"] == 3

    async def test_trained_model_is_valid_sklearn(self, svc):
        await svc.train()
        with open(svc._model_path, "rb") as f:
            model = pickle.load(f)
        assert hasattr(model, "predict")
        assert hasattr(model, "predict_proba")


# ── Packaging ───────────────────────────────────────────────────────────

class TestPackaging:

    async def test_pack_without_training_returns_error(self, svc):
        result = await svc.pack()
        assert "error" in result

    async def test_pack_creates_aquilia_archive(self, svc):
        await svc.train()
        result = await svc.pack(version="v0.1.0")
        assert "pack_path" in result
        assert result["name"] == "iris-classifier"
        assert result["version"] == "v0.1.0"
        assert result["framework"] == "sklearn"
        assert Path(result["pack_path"]).exists()
        assert result["pack_path"].endswith(".aquilia")

    async def test_pack_records_lineage(self, svc):
        await svc.train()
        await svc.pack(version="v1.0.0")
        lin = await svc.lineage()
        assert lin["total_nodes"] == 2
        assert "iris-dataset" in lin["roots"]


# ── Deployment ──────────────────────────────────────────────────────────

class TestDeployment:

    async def test_deploy_without_pack_returns_error(self, svc):
        result = await svc.deploy()
        assert "error" in result

    async def test_deploy_success(self, svc):
        await svc.train()
        await svc.pack()
        result = await svc.deploy()
        assert result["status"] == "deployed"
        assert result["ready"] is True
        assert result["model"] == "iris-classifier"
        assert svc.is_serving is True
        await svc.undeploy()

    async def test_undeploy(self, svc):
        await svc.train()
        await svc.pack()
        await svc.deploy()
        result = await svc.undeploy()
        assert result["status"] == "undeployed"
        assert svc.is_serving is False

    async def test_deploy_adds_lineage_node(self, svc):
        await svc.train()
        await svc.pack()
        await svc.deploy()
        lin = await svc.lineage()
        assert lin["total_nodes"] == 3
        assert "deployment:v1.0.0" in lin["leaves"]
        await svc.undeploy()


# ── Inference ───────────────────────────────────────────────────────────

class TestInference:

    async def test_predict_without_deploy_returns_error(self, svc):
        result = await svc.predict([5.1, 3.5, 1.4, 0.2])
        assert "error" in result

    async def test_predict_single_setosa(self, deployed_svc):
        result = await deployed_svc.predict([5.1, 3.5, 1.4, 0.2])
        assert "prediction" in result
        assert "request_id" in result
        assert "latency_ms" in result
        pred = result["prediction"]
        assert pred["classes"][0] == "setosa"

    async def test_predict_single_versicolor(self, deployed_svc):
        result = await deployed_svc.predict([7.0, 3.2, 4.7, 1.4])
        pred = result["prediction"]
        assert pred["classes"][0] == "versicolor"

    async def test_predict_single_virginica(self, deployed_svc):
        result = await deployed_svc.predict([6.3, 3.3, 6.0, 2.5])
        pred = result["prediction"]
        assert pred["classes"][0] == "virginica"

    async def test_predict_returns_probabilities(self, deployed_svc):
        result = await deployed_svc.predict([5.1, 3.5, 1.4, 0.2])
        probas = result["prediction"]["probabilities"]
        assert len(probas) == 1  # one sample
        assert len(probas[0]) == 3  # three classes
        assert abs(sum(probas[0]) - 1.0) < 1e-6

    async def test_predict_batch(self, deployed_svc):
        samples = [
            [5.1, 3.5, 1.4, 0.2],
            [7.0, 3.2, 4.7, 1.4],
            [6.3, 3.3, 6.0, 2.5],
        ]
        results = await deployed_svc.predict_batch(samples)
        assert len(results) == 3
        assert all("prediction" in r for r in results)


# ── Health Probes ───────────────────────────────────────────────────────

class TestHealthProbes:

    async def test_liveness_no_server(self, svc):
        result = await svc.liveness()
        assert result["status"] == "dead"

    async def test_readiness_no_server(self, svc):
        result = await svc.readiness()
        assert result["status"] == "not_ready"

    async def test_liveness_deployed(self, deployed_svc):
        result = await deployed_svc.liveness()
        assert result["status"] == "alive"
        assert result["uptime_s"] >= 0

    async def test_readiness_deployed(self, deployed_svc):
        result = await deployed_svc.readiness()
        assert result["status"] == "ready"

    async def test_health_deployed(self, deployed_svc):
        result = await deployed_svc.health()
        assert result["status"] == "serving"
        assert result["ready"] is True
        assert result["model"] == "iris-classifier"


# ── Lineage ─────────────────────────────────────────────────────────────

class TestLineage:

    async def test_lineage_empty(self, svc):
        lin = await svc.lineage()
        assert lin["total_nodes"] == 0

    async def test_lineage_after_full_pipeline(self, deployed_svc):
        lin = await deployed_svc.lineage()
        assert lin["total_nodes"] == 3
        graph = lin["graph"]
        assert "iris-dataset" in graph
        assert "iris-classifier:v1.0.0" in graph
        assert "deployment:v1.0.0" in graph
        # Check edges
        assert "iris-classifier:v1.0.0" in graph["iris-dataset"]["children"]
        assert "iris-dataset" in graph["iris-classifier:v1.0.0"]["parents"]


# ── Experiments ─────────────────────────────────────────────────────────

class TestExperiments:

    async def test_create_experiment(self, svc):
        result = await svc.create_experiment(
            experiment_id="test-exp",
            arms=[
                {"name": "a", "model_version": "v1"},
                {"name": "b", "model_version": "v2"},
            ],
        )
        assert result["experiment_id"] == "test-exp"
        assert result["status"] == "active"
        assert len(result["arms"]) == 2

    async def test_list_experiments(self, svc):
        await svc.create_experiment("e1", arms=[{"name": "a", "model_version": "v1"}])
        exps = await svc.list_experiments()
        assert len(exps) == 1
        assert exps[0]["experiment_id"] == "e1"

    async def test_conclude_experiment(self, svc):
        await svc.create_experiment(
            "e2",
            arms=[
                {"name": "ctrl", "model_version": "v1"},
                {"name": "treat", "model_version": "v2"},
            ],
        )
        result = await svc.conclude_experiment("e2", winner="treat")
        assert result["status"] == "completed"
        assert result["metadata"]["winner"] == "treat"


# ── Metrics ─────────────────────────────────────────────────────────────

class TestMetrics:

    async def test_metrics_after_inference(self, deployed_svc):
        await deployed_svc.predict([5.1, 3.5, 1.4, 0.2])
        await deployed_svc.predict([7.0, 3.2, 4.7, 1.4])
        m = await deployed_svc.get_metrics()
        assert m["server"]["aquilia_request_count"] >= 2
        assert m["hot_models"] is not None


# ── Full Pipeline (integration) ─────────────────────────────────────────

class TestFullPipeline:

    async def test_train_pack_deploy_predict_undeploy(self, svc):
        """End-to-end lifecycle in one test."""
        # Train
        metrics = await svc.train(n_estimators=50, max_depth=3)
        assert metrics["accuracy"] > 0.7

        # Pack
        pack = await svc.pack(version="v0.9.0")
        assert Path(pack["pack_path"]).exists()

        # Deploy
        deploy = await svc.deploy(version="v0.9.0")
        assert deploy["status"] == "deployed"
        assert deploy["ready"] is True

        # Predict all 3 classes correctly
        for features, expected in [
            ([5.1, 3.5, 1.4, 0.2], "setosa"),
            ([7.0, 3.2, 4.7, 1.4], "versicolor"),
            ([6.3, 3.3, 6.0, 2.5], "virginica"),
        ]:
            r = await svc.predict(features)
            assert r["prediction"]["classes"][0] == expected

        # Health
        assert (await svc.liveness())["status"] == "alive"
        assert (await svc.readiness())["status"] == "ready"

        # Lineage
        lin = await svc.lineage()
        assert lin["total_nodes"] == 3

        # Undeploy
        ud = await svc.undeploy()
        assert ud["status"] == "undeployed"
        assert svc.is_serving is False
