"""
MLOps Aquilary Module — register MLOps as an Aquilary application module.

Provides an ``MLOpsManifest`` that the Aquilary registry can discover,
validate, and load alongside other application manifests.

Usage::

    from aquilia.aquilary import Aquilary
    from aquilia.mlops.module import MLOpsManifest

    registry = Aquilary.from_manifests(
        [MyAppManifest, MLOpsManifest],
        config=my_config,
    )
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MLOpsManifest:
    """
    Aquilary-compatible manifest for the MLOps subsystem.

    Declares the MLOps module as an Aquilary application with its own
    controllers, services, lifecycle hooks, and middleware.
    """

    name = "mlops"
    version = "0.2.0"
    description = "Aquilia MLOps Platform — model packaging, registry, serving & observability"
    depends_on: list[str] = []

    # Controller import paths (lazy-loaded by Aquilary)
    controllers: list[str] = [
        "aquilia.mlops.controller.MLOpsController",
    ]

    # Service import paths (wired into DI)
    services: list[str] = [
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
    ]

    # Middleware (registered in order)
    middleware: list[tuple[str, dict]] = [
        ("aquilia.mlops.middleware.mlops_metrics_middleware", {}),
        ("aquilia.mlops.middleware.mlops_request_id_middleware", {}),
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
