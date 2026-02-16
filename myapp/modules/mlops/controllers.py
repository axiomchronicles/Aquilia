"""
Mlops module controllers — real MLOps endpoints.

Provides HTTP endpoints for the full Aquilia MLOps lifecycle:
  POST /mlops/train      — train the Iris model
  POST /mlops/pack       — build .aquilia modelpack
  POST /mlops/deploy     — deploy model for serving
  POST /mlops/undeploy   — stop serving
  POST /mlops/predict    — single inference
  POST /mlops/predict/batch — batch inference
  GET  /mlops/health     — server health
  GET  /mlops/healthz    — K8s liveness
  GET  /mlops/readyz     — K8s readiness
  GET  /mlops/metrics    — Prometheus metrics
  GET  /mlops/lineage    — model lineage DAG
  POST /mlops/experiments            — create experiment
  GET  /mlops/experiments            — list experiments
  POST /mlops/experiments/conclude   — conclude experiment
"""

from aquilia import Controller, GET, POST, RequestCtx, Response
from .services import MlopsService


class MlopsController(Controller):
    """Full-lifecycle MLOps controller with train → deploy → predict → observe."""

    prefix = "/"
    tags = ["mlops"]

    def __init__(self, service: "MlopsService" = None):
        self.service = service or MlopsService()

    # ── Training & Packaging ─────────────────────────────────────────

    @POST("/train")
    async def train(self, ctx: RequestCtx):
        """Train the Iris classifier."""
        body = {}
        try:
            body = await ctx.json()
        except Exception:
            pass
        metrics = await self.service.train(
            n_estimators=body.get("n_estimators", 100),
            max_depth=body.get("max_depth", 5),
            test_size=body.get("test_size", 0.2),
        )
        return Response.json(metrics)

    @POST("/pack")
    async def pack(self, ctx: RequestCtx):
        """Build .aquilia modelpack."""
        body = {}
        try:
            body = await ctx.json()
        except Exception:
            pass
        result = await self.service.pack(version=body.get("version", "v1.0.0"))
        if "error" in result:
            return Response.json(result, status=400)
        return Response.json(result, status=201)

    # ── Deployment ───────────────────────────────────────────────────

    @POST("/deploy")
    async def deploy(self, ctx: RequestCtx):
        """Deploy modelpack for live serving."""
        body = {}
        try:
            body = await ctx.json()
        except Exception:
            pass
        result = await self.service.deploy(version=body.get("version", "v1.0.0"))
        if "error" in result:
            return Response.json(result, status=400)
        return Response.json(result)

    @POST("/undeploy")
    async def undeploy(self, ctx: RequestCtx):
        """Stop serving."""
        result = await self.service.undeploy()
        return Response.json(result)

    # ── Inference ────────────────────────────────────────────────────

    @POST("/predict")
    async def predict(self, ctx: RequestCtx):
        """Single-sample prediction."""
        body = await ctx.json()
        features = body.get("features", [])
        result = await self.service.predict(features)
        if "error" in result:
            return Response.json(result, status=400)
        return Response.json(result)

    @POST("/predict/batch")
    async def predict_batch(self, ctx: RequestCtx):
        """Batch prediction."""
        body = await ctx.json()
        samples = body.get("samples", [])
        results = await self.service.predict_batch(samples)
        return Response.json({"results": results, "total": len(results)})

    # ── Observability ────────────────────────────────────────────────

    @GET("/health")
    async def health(self, ctx: RequestCtx):
        """Full health check."""
        return Response.json(await self.service.health())

    @GET("/healthz")
    async def healthz(self, ctx: RequestCtx):
        """K8s liveness probe."""
        result = await self.service.liveness()
        status = 200 if result.get("status") == "alive" else 503
        return Response.json(result, status=status)

    @GET("/readyz")
    async def readyz(self, ctx: RequestCtx):
        """K8s readiness probe."""
        result = await self.service.readiness()
        status = 200 if result.get("status") == "ready" else 503
        return Response.json(result, status=status)

    @GET("/metrics")
    async def metrics(self, ctx: RequestCtx):
        """Prometheus-compatible metrics."""
        return Response.json(await self.service.get_metrics())

    # ── Lineage ──────────────────────────────────────────────────────

    @GET("/lineage")
    async def lineage(self, ctx: RequestCtx):
        """Model lineage DAG."""
        return Response.json(await self.service.lineage())

    # ── Experiments ──────────────────────────────────────────────────

    @POST("/experiments")
    async def create_experiment(self, ctx: RequestCtx):
        """Create an A/B experiment."""
        body = await ctx.json()
        result = await self.service.create_experiment(
            experiment_id=body["experiment_id"],
            arms=body.get("arms", []),
            description=body.get("description", ""),
        )
        return Response.json(result, status=201)

    @GET("/experiments")
    async def list_experiments(self, ctx: RequestCtx):
        """List active experiments."""
        exps = await self.service.list_experiments()
        return Response.json({"experiments": exps, "total": len(exps)})

    @POST("/experiments/conclude")
    async def conclude_experiment(self, ctx: RequestCtx):
        """Conclude an experiment."""
        body = await ctx.json()
        result = await self.service.conclude_experiment(
            experiment_id=body["experiment_id"],
            winner=body.get("winner", ""),
        )
        return Response.json(result)