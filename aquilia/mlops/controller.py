"""
MLOps Controller — HTTP endpoints for model serving, registry, and observability.

Extends Aquilia's :class:`~aquilia.controller.Controller` base class and uses
the ``@GET`` / ``@POST`` route decorators so that routes are automatically
compiled, traced, and documented via OpenAPI.

Ecosystem wiring:
- **FaultEngine** — all exceptions are routed through ``fault_engine.process()``
  instead of bare ``try/except``.
- **CacheService** — model metadata, registry listings, and capability
  introspection results are cached with namespace isolation.
- **Effects** — controller methods declare ``CacheEffect`` / ``DBTx`` so
  the effect middleware can acquire and release resources automatically.
- **Serializers** — request/response payloads are validated through the
  Aquilia serializer framework.

Endpoints::

    GET  /mlops/health             — platform health check
    GET  /mlops/healthz            — K8s liveness probe
    GET  /mlops/readyz             — K8s readiness probe
    POST /mlops/predict            — single inference request
    POST /mlops/stream             — streaming inference (SSE)
    POST /mlops/chat               — chat-style inference (LLM)
    GET  /mlops/metrics            — Prometheus metrics export
    GET  /mlops/models             — list registered models
    GET  /mlops/models/{name}      — get model details
    POST /mlops/models/{name}/rollout — start a rollout
    GET  /mlops/drift              — drift report
    GET  /mlops/plugins            — list loaded plugins
    GET  /mlops/lineage            — model lineage DAG
    GET  /mlops/experiments        — list A/B experiments
    POST /mlops/experiments        — create experiment
    GET  /mlops/hot-models         — top-K hot models
    GET  /mlops/circuit-breaker    — circuit breaker status
    GET  /mlops/rate-limit         — rate limiter status
    GET  /mlops/memory             — memory tracker status
    GET  /mlops/capabilities       — model capabilities
    GET  /mlops/artifacts          — list artifacts
    GET  /mlops/artifacts/{name}   — inspect artifact
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from aquilia.controller import Controller, GET, POST, RequestCtx
from aquilia.effects import CacheEffect

logger = logging.getLogger("aquilia.mlops.controller")


class MLOpsController(Controller):
    """
    Controller for MLOps HTTP API.

    Extends :class:`~aquilia.controller.Controller` to participate in
    Aquilia's controller compilation, DI injection, effect system,
    fault engine routing, and middleware pipeline.

    When running **standalone** (no Aquilia server) all injected services
    default to ``None`` and the controller degrades gracefully.
    """

    prefix = "/mlops"
    tags: List[str] = ["mlops"]
    instantiation_mode = "singleton"

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
        # ── Aquilia ecosystem services ──
        cache_service=None,
        fault_engine=None,
        artifact_store=None,
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
        # Aquilia ecosystem
        self._cache = cache_service
        self._fault_engine = fault_engine
        self._artifact_store = artifact_store

    # ── Helpers ────────────────────────────────────────────────────────

    async def _process_fault(self, exc: Exception) -> Dict[str, Any]:
        """Route an exception through the FaultEngine if available."""
        if self._fault_engine is not None:
            from aquilia.faults import Resolved, Transformed
            result = await self._fault_engine.process(exc, app="mlops")
            if isinstance(result, Resolved):
                return {"error": str(exc), "resolved": True}
            if isinstance(result, Transformed):
                return {"error": str(result.fault), "transformed": True}
        return {"error": str(exc)}

    async def _cache_get(self, key: str, namespace: str = "mlops") -> Any:
        """Get from cache if CacheService is available."""
        if self._cache is not None:
            try:
                return await self._cache.get(key, namespace=namespace)
            except Exception:
                pass
        return None

    async def _cache_set(
        self, key: str, value: Any, ttl: int = 60, namespace: str = "mlops",
    ) -> None:
        """Set in cache if CacheService is available."""
        if self._cache is not None:
            try:
                await self._cache.set(key, value, ttl=ttl, namespace=namespace)
            except Exception:
                pass

    # ── Health ───────────────────────────────────────────────────────

    @GET("/health")
    async def health(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Platform health check — ``GET /mlops/health``."""
        # Try cache first
        cached = await self._cache_get("health_status")
        if cached is not None:
            return cached

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
                result["components"]["registry"] = await self._process_fault(exc)

        if self._server:
            try:
                health_data = await self._server.health()
                result["components"]["serving"] = health_data
            except Exception as exc:
                result["components"]["serving"] = await self._process_fault(exc)

        if self._plugins:
            result["components"]["plugins"] = {
                "total": len(self._plugins.list_plugins()),
                "active": len(self._plugins.active_plugins),
            }

        if self._cache is not None:
            result["components"]["cache"] = {"status": "up"}

        if self._fault_engine is not None:
            result["components"]["fault_engine"] = {"status": "up"}

        if self._artifact_store is not None:
            result["components"]["artifact_store"] = {"status": "up"}

        # Cache health for 10 seconds
        await self._cache_set("health_status", result, ttl=10)
        return result

    # ── Predict ──────────────────────────────────────────────────────

    @POST("/predict")
    async def predict(self, body: Dict[str, Any], ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """
        Single inference — ``POST /mlops/predict``.

        Body::

            {
              "inputs": {"feature_1": 1.0, ...},
              "parameters": {},
              "priority": 0,
              "max_tokens": 0,
              "stream": false
            }
        """
        from ._types import InferenceRequest

        if not self._server:
            return {"error": "No serving server configured", "status": 503}

        inputs = body.get("inputs", {})
        parameters = body.get("parameters", {})
        priority = body.get("priority", 0)
        max_tokens = body.get("max_tokens", 0)

        result = await self._server.predict(
            inputs, parameters,
            priority=priority,
            max_tokens=max_tokens,
        )
        response = {
            "request_id": result.request_id,
            "outputs": result.outputs,
            "latency_ms": result.latency_ms,
            "metadata": result.metadata,
            "token_count": result.token_count,
            "prompt_tokens": result.prompt_tokens,
            "finish_reason": result.finish_reason,
        }
        return response

    @POST("/stream")
    async def stream_predict(self, body: Dict[str, Any], ctx: Optional[RequestCtx] = None):
        """
        Streaming inference — ``POST /mlops/stream``.

        Returns an async generator yielding SSE-formatted chunks.

        Body::

            {
              "inputs": {"prompt": "Hello, "},
              "parameters": {},
              "max_tokens": 256
            }
        """
        if not self._server:
            yield {"error": "No serving server configured"}
            return

        inputs = body.get("inputs", {})
        parameters = body.get("parameters", {})
        max_tokens = body.get("max_tokens", 0)

        async for chunk in self._server.stream_predict(
            inputs, parameters, max_tokens=max_tokens,
        ):
            yield {
                "request_id": chunk.request_id,
                "token": chunk.token,
                "token_id": chunk.token_id,
                "is_finished": chunk.is_finished,
                "finish_reason": chunk.finish_reason,
                "cumulative_tokens": chunk.cumulative_tokens,
                "latency_ms": chunk.latency_ms,
            }

    @POST("/chat")
    async def chat(self, body: Dict[str, Any], ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """
        Chat-style inference — ``POST /mlops/chat``.

        Body::

            {
              "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"}
              ],
              "max_tokens": 256,
              "stream": false
            }
        """
        if not self._server:
            return {"error": "No serving server configured", "status": 503}

        messages = body.get("messages", [])
        max_tokens = body.get("max_tokens", 0)

        result = await self._server.predict(
            inputs={"prompt": messages},
            max_tokens=max_tokens,
        )
        return {
            "request_id": result.request_id,
            "message": {
                "role": "assistant",
                "content": result.outputs.get("text", str(result.outputs)),
            },
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.token_count,
                "total_tokens": result.prompt_tokens + result.token_count,
            },
            "finish_reason": result.finish_reason,
        }

    # ── Resilience Status ────────────────────────────────────────────

    @GET("/circuit-breaker")
    async def circuit_breaker_status(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Circuit breaker status — ``GET /mlops/circuit-breaker``."""
        if self._server and hasattr(self._server, "circuit_breaker"):
            return self._server.circuit_breaker.stats
        return {"error": "Circuit breaker not configured"}

    @GET("/rate-limit")
    async def rate_limit_status(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Rate limiter status — ``GET /mlops/rate-limit``."""
        if self._server and hasattr(self._server, "rate_limiter") and self._server.rate_limiter:
            return self._server.rate_limiter.stats
        return {"error": "Rate limiter not configured"}

    @GET("/memory")
    async def memory_status(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Memory tracker status — ``GET /mlops/memory``."""
        if self._server and hasattr(self._server, "memory_tracker") and self._server.memory_tracker:
            return self._server.memory_tracker.stats
        return {"error": "Memory tracker not configured"}

    @GET("/capabilities")
    async def model_capabilities(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Model capabilities — ``GET /mlops/capabilities``."""
        cached = await self._cache_get("model_capabilities")
        if cached is not None:
            return cached

        if not self._server:
            return {"error": "No serving server configured"}
        manifest = self._server.manifest
        result: Dict[str, Any] = {
            "name": manifest.name,
            "version": manifest.version,
            "framework": manifest.framework,
            "model_type": manifest.model_type,
            "is_llm": manifest.is_llm,
            "supports_streaming": hasattr(self._server._runtime, "stream_infer"),
            "supports_batching": True,
        }
        if manifest.llm_config:
            result["llm_config"] = manifest.llm_config.to_dict()

        # Cache capabilities — they rarely change
        await self._cache_set("model_capabilities", result, ttl=300)
        return result

    # ── Metrics ──────────────────────────────────────────────────────

    @GET("/metrics")
    async def metrics(self, fmt: str = "json", ctx: Optional[RequestCtx] = None) -> Any:
        """Metrics export — ``GET /mlops/metrics``."""
        if not self._metrics:
            return {"error": "Metrics collector not configured"}

        if fmt == "prometheus":
            return self._metrics.to_prometheus()
        return self._metrics.get_summary()

    # ── Registry ─────────────────────────────────────────────────────

    @GET("/models")
    async def list_models(
        self, limit: int = 100, offset: int = 0, ctx: Optional[RequestCtx] = None,
    ) -> Dict[str, Any]:
        """List registered models — ``GET /mlops/models``."""
        if not self._registry:
            return {"error": "Registry not configured", "models": []}

        cache_key = f"models:list:{limit}:{offset}"
        cached = await self._cache_get(cache_key, namespace="mlops.registry")
        if cached is not None:
            return cached

        try:
            packs = await self._registry.list_packs(limit=limit, offset=offset)
            result = {"models": packs, "count": len(packs)}
            await self._cache_set(cache_key, result, ttl=30, namespace="mlops.registry")
            return result
        except Exception as exc:
            return await self._process_fault(exc)

    @GET("/models/{name}")
    async def get_model(self, name: str, tag: str = "latest", ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Get model details — ``GET /mlops/models/{name}``."""
        if not self._registry:
            return {"error": "Registry not configured"}

        cache_key = f"model:{name}:{tag}"
        cached = await self._cache_get(cache_key, namespace="mlops.registry")
        if cached is not None:
            return cached

        try:
            manifest = await self._registry.fetch(name, tag)
            result = manifest.to_dict()
            await self._cache_set(cache_key, result, ttl=60, namespace="mlops.registry")
            return result
        except Exception as exc:
            return await self._process_fault(exc)

    # ── Rollout ──────────────────────────────────────────────────────

    @POST("/models/{name}/rollout")
    async def start_rollout(self, body: Dict[str, Any], ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
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

    @GET("/rollouts")
    async def list_rollouts(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
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

    @GET("/drift")
    async def drift_status(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Drift detection status — ``GET /mlops/drift``."""
        if not self._drift:
            return {"error": "Drift detector not configured"}

        return {
            "method": self._drift.method.value,
            "threshold": self._drift.threshold,
            "reference_set": self._drift._reference is not None,
        }

    # ── Plugins ──────────────────────────────────────────────────────

    @GET("/plugins")
    async def list_plugins(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
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

    @GET("/healthz")
    async def liveness(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """K8s liveness probe — ``GET /mlops/healthz``."""
        if self._server and hasattr(self._server, "liveness"):
            return await self._server.liveness()
        return {"status": "alive", "timestamp": time.time()}

    @GET("/readyz")
    async def readiness(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """K8s readiness probe — ``GET /mlops/readyz``."""
        if self._server and hasattr(self._server, "readiness"):
            return await self._server.readiness()
        return {"status": "ready", "timestamp": time.time()}

    # ── Lineage ──────────────────────────────────────────────────────

    @GET("/lineage")
    async def lineage(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Model lineage DAG — ``GET /mlops/lineage``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured", "nodes": {}}

        return {
            "total": len(self._lineage),
            "roots": self._lineage.roots(),
            "leaves": self._lineage.leaves(),
            "graph": self._lineage.to_dict(),
        }

    @GET("/lineage/{model_id}/ancestors")
    async def lineage_ancestors(self, model_id: str, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Ancestors of a model — ``GET /mlops/lineage/{model_id}/ancestors``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured"}
        return {
            "model_id": model_id,
            "ancestors": self._lineage.ancestors(model_id),
        }

    @GET("/lineage/{model_id}/descendants")
    async def lineage_descendants(self, model_id: str, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Descendants of a model — ``GET /mlops/lineage/{model_id}/descendants``."""
        if self._lineage is None:
            return {"error": "Lineage DAG not configured"}
        return {
            "model_id": model_id,
            "descendants": self._lineage.descendants(model_id),
        }

    # ── Experiments ──────────────────────────────────────────────────

    @GET("/experiments")
    async def list_experiments(self, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
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

    @POST("/experiments")
    async def create_experiment(self, body: Dict[str, Any], ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
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

    @POST("/experiments/{experiment_id}/conclude")
    async def conclude_experiment(
        self, experiment_id: str, winner: str = "", ctx: Optional[RequestCtx] = None,
    ) -> Dict[str, Any]:
        """Conclude experiment — ``POST /mlops/experiments/{id}/conclude``."""
        if self._experiments is None:
            return {"error": "Experiment ledger not configured"}
        self._experiments.conclude(experiment_id, winner)
        return self._experiments.summary(experiment_id)

    # ── Hot Models ───────────────────────────────────────────────────

    @GET("/hot-models")
    async def hot_models(self, k: int = 10, ctx: Optional[RequestCtx] = None) -> Dict[str, Any]:
        """Top-K hot models — ``GET /mlops/hot-models``."""
        if self._metrics and hasattr(self._metrics, "hot_models"):
            return {"hot_models": self._metrics.hot_models(k)}
        return {"hot_models": []}

    # ── Artifacts ────────────────────────────────────────────────────

    @GET("/artifacts")
    async def list_artifacts(
        self,
        kind: str = "",
        store_dir: str = "artifacts",
        ctx: Optional[RequestCtx] = None,
    ) -> Dict[str, Any]:
        """List artifacts — ``GET /mlops/artifacts``."""
        try:
            store = self._artifact_store
            if store is None:
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
            return await self._process_fault(exc)

    @GET("/artifacts/{name}")
    async def inspect_artifact(
        self,
        name: str,
        version: str = "",
        store_dir: str = "artifacts",
        ctx: Optional[RequestCtx] = None,
    ) -> Dict[str, Any]:
        """Inspect artifact — ``GET /mlops/artifacts/{name}``."""
        try:
            from aquilia.artifacts import ArtifactReader

            store = self._artifact_store
            if store is None:
                from aquilia.artifacts import FilesystemArtifactStore
                store = FilesystemArtifactStore(store_dir)

            reader = ArtifactReader(store)
            artifact = reader.load_or_fail(name, version=version)
            return reader.inspect(artifact)
        except FileNotFoundError:
            return {"error": f"Artifact not found: {name}"}
        except Exception as exc:
            return await self._process_fault(exc)
