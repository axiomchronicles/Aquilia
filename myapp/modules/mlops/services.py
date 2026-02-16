"""
Mlops module services — real MLOps pipeline integration.

Wraps the full Aquilia MLOps stack:
  train → pack → serve → predict → lineage → experiments → health

Uses sklearn model trained via ``train.py``.
"""

from __future__ import annotations

import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aquilia.di import service
from aquilia.mlops import (
    ModelpackBuilder,
    ModelpackManifest,
    ModelServingServer,
    PythonRuntime,
    TensorSpec,
    WarmupStrategy,
    MetricsCollector,
    ModelLineageDAG,
    ExperimentLedger,
)

logger = logging.getLogger("myapp.mlops.services")

# ── Paths ──────────────────────────────────────────────────────────────

_BASE = Path(__file__).resolve().parent.parent.parent          # myapp/
ARTIFACTS_DIR = _BASE / "artifacts" / "mlops"
PACKS_DIR = _BASE / "artifacts" / "packs"
UNPACK_DIR = _BASE / "artifacts" / "unpacked"


@service(scope="app")
class MlopsService:
    """
    Full-lifecycle MLOps service.

    Manages model training, packaging, serving, inference, lineage,
    and A/B experiments — all via the Aquilia MLOps platform.
    """

    def __init__(self):
        # ── State ────────────────────────────────────────────────────
        self._server: Optional[ModelServingServer] = None
        self._runtime: Optional[PythonRuntime] = None
        self._manifest: Optional[ModelpackManifest] = None
        self._metrics = MetricsCollector()
        self._lineage = ModelLineageDAG()
        self._experiments = ExperimentLedger()

        # Training results (populated by train())
        self._train_metrics: Dict[str, Any] = {}
        self._model_path: Optional[Path] = None
        self._pack_path: Optional[str] = None
        self._is_serving = False

    # ── Training ─────────────────────────────────────────────────────

    async def train(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 5,
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """Train the Iris classifier and return evaluation metrics."""
        from .train import train_iris_model

        model, metrics, path = train_iris_model(
            n_estimators=n_estimators,
            max_depth=max_depth,
            test_size=test_size,
        )
        self._train_metrics = metrics
        self._model_path = path
        logger.info("Training complete: accuracy=%.4f", metrics["accuracy"])
        return metrics

    # ── Packaging ────────────────────────────────────────────────────

    async def pack(self, version: str = "v1.0.0") -> Dict[str, Any]:
        """Build an ``.aquilia`` modelpack from the trained model."""
        if not self._model_path or not self._model_path.exists():
            return {"error": "No trained model found. Call train() first."}

        builder = ModelpackBuilder(
            name="iris-classifier",
            version=version,
            framework="sklearn",
        )
        builder.add_model(str(self._model_path), framework="sklearn")
        builder.set_signature(
            inputs=[TensorSpec(name="features", dtype="float64", shape=[None, 4])],
            outputs=[TensorSpec(name="prediction", dtype="int64", shape=[None])],
        )
        builder.set_provenance(
            git_sha=os.popen("git rev-parse --short HEAD 2>/dev/null").read().strip() or "unknown",
        )
        builder.set_metadata(
            accuracy=self._train_metrics.get("accuracy", 0),
            f1=self._train_metrics.get("f1_weighted", 0),
            n_estimators=self._train_metrics.get("n_estimators", 100),
        )

        PACKS_DIR.mkdir(parents=True, exist_ok=True)
        self._pack_path = await builder.save(str(PACKS_DIR))
        logger.info("Modelpack built → %s", self._pack_path)

        # Record lineage: training → packed model
        self._lineage.add_model("iris-dataset", "1.0", framework="dataset")
        self._lineage.add_model(
            f"iris-classifier:{version}", version,
            framework="sklearn", parents=["iris-dataset"],
        )

        return {
            "pack_path": self._pack_path,
            "name": "iris-classifier",
            "version": version,
            "framework": "sklearn",
        }

    # ── Deployment / Serving ─────────────────────────────────────────

    async def deploy(self, version: str = "v1.0.0") -> Dict[str, Any]:
        """
        Unpack and deploy the modelpack for live serving.

        Creates a ``ModelServingServer`` with ``PythonRuntime`` + warm-up.
        """
        if not self._pack_path:
            return {"error": "No modelpack found. Call pack() first."}

        # Stop previous server if running
        if self._server and self._is_serving:
            await self.undeploy()

        # Unpack
        UNPACK_DIR.mkdir(parents=True, exist_ok=True)
        manifest = await ModelpackBuilder.unpack(self._pack_path, str(UNPACK_DIR))
        self._manifest = manifest

        # Sklearn predict expects 2-D array — wrap with custom predict_fn
        model_file = UNPACK_DIR / "model" / manifest.entrypoint
        with open(model_file, "rb") as f:
            sklearn_model = pickle.load(f)

        def predict_fn(inputs):
            """Adapter: convert dict/list inputs → sklearn 2-D array."""
            import numpy as np
            if isinstance(inputs, dict):
                data = inputs.get("features") or inputs.get("input") or list(inputs.values())[0]
            elif isinstance(inputs, (list, tuple)):
                data = inputs
            else:
                data = inputs
            arr = np.array(data)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            preds = sklearn_model.predict(arr)
            probas = sklearn_model.predict_proba(arr)
            target_names = ["setosa", "versicolor", "virginica"]
            labels = [target_names[int(p)] for p in preds]
            return {
                "classes": labels,
                "predictions": preds.tolist(),
                "probabilities": probas.tolist(),
            }

        # Create runtime with custom predict_fn
        self._runtime = PythonRuntime(predict_fn=predict_fn)
        self._runtime._manifest = manifest
        self._runtime._model_dir = str(UNPACK_DIR)
        self._runtime._loaded = True

        # Create server with warm-up
        warmup_payload = {"features": [5.1, 3.5, 1.4, 0.2]}
        self._server = ModelServingServer(
            manifest=manifest,
            model_dir=str(UNPACK_DIR),
            runtime=self._runtime,
            warmup=WarmupStrategy(num_requests=2, synthetic_payload=warmup_payload),
        )

        # Bootstrap server (runtime already loaded)
        await self._server._batcher.start()
        self._server._started = True
        self._server._start_time = time.time()
        await self._server._run_warmup()
        self._server._ready = True
        self._is_serving = True

        # Lineage: packed → deployed
        self._lineage.add_model(
            f"deployment:{version}", version,
            framework="serving", parents=[f"iris-classifier:{version}"],
        )

        logger.info("Deployed iris-classifier %s", version)
        return {
            "status": "deployed",
            "model": manifest.name,
            "version": manifest.version,
            "framework": manifest.framework,
            "ready": True,
        }

    async def undeploy(self) -> Dict[str, Any]:
        """Stop the serving server."""
        if self._server:
            await self._server._batcher.stop()
            self._server._started = False
            self._server._ready = False
        self._is_serving = False
        return {"status": "undeployed"}

    # ── Inference ────────────────────────────────────────────────────

    async def predict(self, features: List[float]) -> Dict[str, Any]:
        """
        Run inference on a single sample.

        Args:
            features: List of 4 floats [sepal_l, sepal_w, petal_l, petal_w].

        Returns:
            Prediction dict with class, probabilities, latency.
        """
        if not self._server or not self._is_serving:
            return {"error": "Model not deployed. Call deploy() first."}

        result = await self._server.predict(
            inputs={"features": features},
        )

        self._metrics.record_inference(
            latency_ms=result.latency_ms,
            model_name="iris-classifier",
        )

        return {
            "request_id": result.request_id,
            "prediction": result.outputs,
            "latency_ms": round(result.latency_ms, 3),
        }

    async def predict_batch(self, samples: List[List[float]]) -> List[Dict[str, Any]]:
        """Run inference on multiple samples."""
        results = []
        for features in samples:
            r = await self.predict(features)
            results.append(r)
        return results

    # ── Observability ────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Health status of the serving stack."""
        if not self._server:
            return {"status": "no_server", "serving": False}
        return await self._server.health()

    async def liveness(self) -> Dict[str, Any]:
        """K8s liveness probe."""
        if not self._server:
            return {"status": "dead"}
        return await self._server.liveness()

    async def readiness(self) -> Dict[str, Any]:
        """K8s readiness probe."""
        if not self._server:
            return {"status": "not_ready"}
        return await self._server.readiness()

    async def get_metrics(self) -> Dict[str, Any]:
        """Collected metrics."""
        server_metrics = await self._server.metrics() if self._server else {}
        return {
            "server": server_metrics,
            "collector": self._metrics.get_summary(),
            "hot_models": self._metrics.hot_models(5),
        }

    # ── Lineage ──────────────────────────────────────────────────────

    async def lineage(self) -> Dict[str, Any]:
        """Full lineage DAG."""
        return {
            "total_nodes": len(self._lineage),
            "roots": self._lineage.roots(),
            "leaves": self._lineage.leaves(),
            "graph": self._lineage.to_dict(),
        }

    # ── Experiments ──────────────────────────────────────────────────

    async def create_experiment(
        self,
        experiment_id: str,
        arms: List[Dict[str, Any]],
        description: str = "",
    ) -> Dict[str, Any]:
        """Create an A/B experiment."""
        self._experiments.create(experiment_id, arms=arms, description=description)
        return self._experiments.summary(experiment_id)

    async def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments."""
        return [
            self._experiments.summary(e.experiment_id)
            for e in self._experiments.list_active()
        ]

    async def conclude_experiment(
        self, experiment_id: str, winner: str
    ) -> Dict[str, Any]:
        """Conclude an experiment with a winner."""
        self._experiments.conclude(experiment_id, winner)
        return self._experiments.summary(experiment_id)

    # ── Convenience ──────────────────────────────────────────────────

    @property
    def is_serving(self) -> bool:
        return self._is_serving

    @property
    def train_metrics(self) -> Dict[str, Any]:
        return self._train_metrics