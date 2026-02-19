"""
MLOps Aquilary Module — register MLOps as an Aquilary application module.

Provides an ``MLOpsManifest`` that the Aquilary registry can discover,
validate, and load alongside other application manifests.

Ecosystem integration:
- **Effects** — declares ``CacheEffect("mlops")`` so that the effect
  middleware acquires a cache handle for every MLOps request.
- **Fault domains** — imports ``faults`` to register all MLOps fault
  domains with the FaultEngine at import time.
- **Middleware** — uses :func:`register_mlops_middleware` to add
  middleware via ``MiddlewareDescriptor`` with scoped ordering.

Usage::

    from aquilia.aquilary import Aquilary
    from aquilia.mlops.module import MLOpsManifest

    registry = Aquilary.from_manifests(
        [MyAppManifest, MLOpsManifest],
        config=my_config,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MLOpsManifest:
    """
    Aquilary-compatible manifest for the MLOps subsystem.

    Declares the MLOps module as an Aquilary application with its own
    controllers, services, lifecycle hooks, middleware, effects, and
    ecosystem bindings.
    """

    name = "mlops"
    version = "1.0.0"
    description = "Aquilia MLOps Platform — model packaging, registry, serving & observability"
    depends_on: List[str] = []

    # Controller import paths (lazy-loaded by Aquilary)
    controllers: List[str] = [
        "aquilia.mlops.controller.MLOpsController",
    ]

    # Service import paths (wired into DI)
    services: List[str] = [
        "aquilia.mlops.registry.service.RegistryService",
        "aquilia.mlops.observe.metrics.MetricsCollector",
        "aquilia.mlops.observe.drift.DriftDetector",
        "aquilia.mlops.observe.logger.PredictionLogger",
        "aquilia.mlops.serving.server.ModelServingServer",
        "aquilia.mlops.serving.batching.DynamicBatcher",
        "aquilia.mlops.plugins.host.PluginHost",
        "aquilia.mlops.release.rollout.RolloutEngine",
        "aquilia.mlops.scheduler.autoscaler.Autoscaler",
        "aquilia.mlops.scheduler.placement.PlacementScheduler",
        "aquilia.mlops.security.rbac.RBACManager",
        "aquilia.mlops.security.signing.ArtifactSigner",
        "aquilia.mlops.security.encryption.EncryptionManager",
        # Resilience / LLM infrastructure
        "aquilia.mlops._structures.CircuitBreaker",
        "aquilia.mlops._structures.TokenBucketRateLimiter",
        "aquilia.mlops._structures.MemoryTracker",
    ]

    # Effects declared by this module
    effects: List[str] = [
        "CacheEffect:mlops",
        "CacheEffect:mlops.registry",
    ]

    # Fault domains registered by this module
    fault_domains: List[str] = [
        "mlops",
        "mlops.pack",
        "mlops.registry",
        "mlops.serving",
        "mlops.observe",
        "mlops.release",
        "mlops.scheduler",
        "mlops.security",
        "mlops.plugin",
        "mlops.resilience",
        "mlops.streaming",
        "mlops.memory",
    ]

    # Middleware (registered in order via MiddlewareDescriptor)
    middleware: List[tuple[str, dict]] = [
        ("aquilia.mlops.middleware.mlops_request_id_middleware", {"scope": "app:mlops", "priority": 5}),
        ("aquilia.mlops.middleware.mlops_rate_limit_middleware", {"scope": "app:mlops", "priority": 10}),
        ("aquilia.mlops.middleware.mlops_circuit_breaker_middleware", {"scope": "app:mlops", "priority": 20}),
        ("aquilia.mlops.middleware.mlops_metrics_middleware", {"scope": "app:mlops", "priority": 30}),
    ]

    # Lifecycle hooks
    @staticmethod
    async def on_startup(config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        from .lifecycle_hooks import mlops_on_startup
        await mlops_on_startup(config=config, **kwargs)

    @staticmethod
    async def on_shutdown(**kwargs: Any) -> None:
        from .lifecycle_hooks import mlops_on_shutdown
        await mlops_on_shutdown(**kwargs)
