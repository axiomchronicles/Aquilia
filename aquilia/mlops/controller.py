"""
MLOps Controller — HTTP endpoints for model serving, registry, and observability.

Integrates with Aquilia's Controller architecture and DI system.

Endpoints::

    GET  /mlops/health           — platform health check
    GET  /mlops/healthz          — K8s liveness probe
    GET  /mlops/readyz           — K8s readiness probe
    POST /mlops/predict           — single inference request
    GET  /mlops/metrics           — Prometheus metrics export
    GET  /mlops/models            — list registered models
    GET  /mlops/models/{name}     — get model details
    POST /mlops/models/{name}/rollout — start a rollout
    GET  /mlops/drift             — drift report
    GET  /mlops/plugins           — list loaded plugins
    GET  /mlops/lineage           — model lineage DAG
    GET  /mlops/experiments       — list A/B experiments
    POST /mlops/experiments       — create experiment
    GET  /mlops/hot-models        — top-K hot models
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("aquilia.mlops.controller")


class MLOpsController:
    """
    Controller for MLOps HTTP API.

    Designed to work standalone (no Aquilia server required) or to be
    wired into an AquiliaServer via the controller system.

    All methods return dicts that can be serialized to JSON responses.
    In a full Aquilia setup, the controller decorators handle serialization.
    """

    prefix = "/mlops"

    def __init__(
        self,
        registry=None,
        serving_server=None,
        metrics_collector=None,
        drift_detector=None,
        rollout_engine=None,
        plugin_host=None,
        rbac_manager=None,
        lineage_dag=None,
        experiment_ledger=None,
    ):
        self._registry = registry
        self._server = serving_server
        self._metrics = metrics_collector
        self._drift = drift_detector
        self._rollout = rollout_engine
        self._plugins = plugin_host
        self._rbac = rbac_manager
        self._lineage = lineage_dag
        self._experiments = experiment_ledger

    # ── Health ───────────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Platform health check — ``GET /mlops/health``."""
        result: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {},
        }

        if self._registry:
            try:
                result["components"]["registry"] = {
                    "status": "up",
                    "initialized": getattr(self._registry, "_initialized", False),
                }
            except Exception as exc:
                result["components"]["registry"] = {"status": "error", "error": str(exc)}

        if self._server:
            try:
                health_data = await self._server.health()
                result["components"]["serving"] = health_data
            except Exception as exc:
                result["components"]["serving"] = {"status": "error", "error": str(exc)}

        if self._plugins:
            result["components"]["plugins"] = {
                "total": len(self._plugins.list_plugins()),
                "active": len(self._plugins.active_plugins),
            }

        return result

    # ── Predict ──────────────────────────────────────────────────────

    async def predict(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Single inference — ``POST /mlops/predict``.

        Body::

            {
              "inputs": {"feature_1": 1.0, ...},
              "parameters": {}
            }
        """
        from ._types import InferenceRequest

        if not self._server:
            return {"error": "No serving server configured", "status": 503}

        inputs = body.get("inputs", {})
        parameters = body.get("parameters", {})

        result = await self._server.predict(inputs, parameters)
        return {
            "request_id": result.request_id,
            "outputs": result.outputs,
            "latency_ms": result.latency_ms,
            "metadata": result.metadata,
        }

    # ── Metrics ──────────────────────────────────────────────────────

    async def metrics(self, fmt: str = "json") -> Any:
        """Metrics export — ``GET /mlops/metrics``."""
        if not self._metrics:
            return {"error": "Metrics collector not configured"}

        if fmt == "prometheus":
            return self._metrics.to_prometheus()
        return self._metrics.get_summary()

    # ── Registry ─────────────────────────────────────────────────────

    async def list_models(
        self, limit: int = 100, offset: int = 0,
    ) -> Dict[str, Any]:
        """List registered models — ``GET /mlops/models``."""
        if not self._registry:
            return {"error": "Registry not configured", "models": []}

        packs = await self._registry.list_packs(limit=limit, offset=offset)
        return {"models": packs, "count": len(packs)}

    async def get_model(self, name: str, tag: str = "latest") -> Dict[str, Any]:
        """Get model details — ``GET /mlops/models/{name}``."""
        if not self._registry:
            return {"error": "Registry not configured"}

        manifest = await self._registry.fetch(name, tag)
        return manifest.to_dict()

    # ── Rollout ──────────────────────────────────────────────────────

    async def start_rollout(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a rollout — ``POST /mlops/models/{name}/rollout``.

        Body::

            {
              "from_version": "v1",
              "to_version": "v2",
              "strategy": "canary",
              "percentage": 10,
              "auto_rollback": true
            }
        """
        from ._types import RolloutConfig, RolloutStrategy

        if not self._rollout:
            return {"error": "Rollout engine not configured"}

        config = RolloutConfig(
            from_version=body["from_version"],
            to_version=body["to_version"],
            strategy=RolloutStrategy(body.get("strategy", "canary")),
            percentage=body.get("percentage", 10),
            auto_rollback=body.get("auto_rollback", True),
        )
        state = await self._rollout.start(config)
        return {
            "rollout_id": state.id,
            "phase": state.phase.value,
            "percentage": state.current_percentage,
        }

    async def list_rollouts(self) -> Dict[str, Any]:
        """List rollouts — ``GET /mlops/rollouts``."""
        if not self._rollout:
            return {"error": "Rollout engine not configured", "rollouts": []}

        rollouts = self._rollout.list_rollouts()
        return {
            "rollouts": [
                {
                    "id": r.id,
                    "phase": r.phase.value,
                    "percentage": r.current_percentage,
                    "from": r.config.from_version,
                    "to": r.config.to_version,
                }
                for r in rollouts
            ],
        }

    # ── Drift ────────────────────────────────────────────────────────

    async def drift_status(self) -> Dict[str, Any]:
        """Drift detection status — ``GET /mlops/drift``."""
        if not self._drift:
            return {"error": "Drift detector not configured"}

        return {
            "method": self._drift.method.value,
            "threshold": self._drift.threshold,
            "reference_set": self._drift._reference is not None,
        }

    # ── Plugins ──────────────────────────────────────────────────────

    async def list_plugins(self) -> Dict[str, Any]:
        """List plugins — ``GET /mlops/plugins``."""
        if not self._plugins:
            return {"plugins": []}

        return {
            "plugins": [
                {
                    "name": p.name,
                    "version": p.version,
                    "state": p.state.value,
                    "module": p.module,
                }
                for p in self._plugins.list_plugins()
            ],
        }

    # ── Health Probes ────────────────────────────────────────────────

    async def liveness(self) -> Dict[str, Any]:
        """K8s liveness probe — ``GET /mlops/healthz``."""
        if self._server and hasattr(self._server, "liveness"):
            return await self._server.liveness()
        return {"status": "alive", "timestamp": time.time()}

    async def readiness(self) -> Dict[str, Any]:
        """K8s readiness probe — ``GET /mlops/readyz``."""
        if self._server and hasattr(self._server, "readiness"):
            return await self._server.readiness()
        return {"status": "ready", "timestamp": time.time()}

    # ── Lineage ──────────────────────────────────────────────────────

    async def lineage(self) -> Dict[str, Any]:
        """Model lineage DAG — ``GET /mlops/lineage``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured", "nodes": {}}

        return {
            "total": len(self._lineage),
            "roots": self._lineage.roots(),
            "leaves": self._lineage.leaves(),
            "graph": self._lineage.to_dict(),
        }

    async def lineage_ancestors(self, model_id: str) -> Dict[str, Any]:
        """Ancestors of a model — ``GET /mlops/lineage/{model_id}/ancestors``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured"}
        return {
            "model_id": model_id,
            "ancestors": self._lineage.ancestors(model_id),
        }

    async def lineage_descendants(self, model_id: str) -> Dict[str, Any]:
        """Descendants of a model — ``GET /mlops/lineage/{model_id}/descendants``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured"}
        return {
            "model_id": model_id,
            "descendants": self._lineage.descendants(model_id),
        }

    # ── Experiments ──────────────────────────────────────────────────

    async def list_experiments(self) -> Dict[str, Any]:
        """List experiments — ``GET /mlops/experiments``."""
        if self._experiments is None:
            return {"experiments": []}

        return {
            "total": len(self._experiments),
            "active": [
                self._experiments.summary(e.experiment_id)
                for e in self._experiments.list_active()
            ],
            "all": self._experiments.to_dict(),
        }

    async def create_experiment(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Create experiment — ``POST /mlops/experiments``."""
        if self._experiments is None:
            return {"error": "Experiment ledger not configured"}

        exp = self._experiments.create(
            experiment_id=body["experiment_id"],
            description=body.get("description", ""),
            arms=body.get("arms", []),
            metadata=body.get("metadata"),
        )
        return self._experiments.summary(exp.experiment_id)

    async def conclude_experiment(
        self, experiment_id: str, winner: str = "",
    ) -> Dict[str, Any]:
        """Conclude experiment — ``POST /mlops/experiments/{id}/conclude``."""
        if self._experiments is None:
            return {"error": "Experiment ledger not configured"}
        self._experiments.conclude(experiment_id, winner)
        return self._experiments.summary(experiment_id)

    # ── Hot Models ───────────────────────────────────────────────────

    async def hot_models(self, k: int = 10) -> Dict[str, Any]:
        """Top-K hot models — ``GET /mlops/hot-models``."""
        if self._metrics and hasattr(self._metrics, "hot_models"):
            return {"hot_models": self._metrics.hot_models(k)}
        return {"hot_models": []}

    # ── Artifacts ────────────────────────────────────────────────────

    async def list_artifacts(
        self,
        kind: str = "",
        store_dir: str = "artifacts",
    ) -> Dict[str, Any]:
        """List artifacts — ``GET /mlops/artifacts``."""
        try:
            from aquilia.artifacts import FilesystemArtifactStore

            store = FilesystemArtifactStore(store_dir)
            artifacts = store.list_artifacts(kind=kind)
            return {
                "total": len(artifacts),
                "artifacts": [
                    {
                        "name": a.name,
                        "version": a.version,
                        "kind": a.kind,
                        "digest": a.digest,
                        "created_at": a.created_at,
                    }
                    for a in artifacts
                ],
            }
        except Exception as exc:
            return {"error": str(exc), "artifacts": []}

    async def inspect_artifact(
        self,
        name: str,
        version: str = "",
        store_dir: str = "artifacts",
    ) -> Dict[str, Any]:
        """Inspect artifact — ``GET /mlops/artifacts/{name}``."""
        try:
            from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

            store = FilesystemArtifactStore(store_dir)
            reader = ArtifactReader(store)
            artifact = reader.load_or_fail(name, version=version)
            return reader.inspect(artifact)
        except FileNotFoundError:
            return {"error": f"Artifact not found: {name}"}
        except Exception as exc:
            return {"error": str(exc)}
