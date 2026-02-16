"""
MLOps DI Integration — Wires all MLOps services into Aquilia's DI container.

Provides:
- ``register_mlops_providers(container, config)`` — one-call setup
- ``@service`` decorated singletons for each major subsystem
- Scoped providers for per-request inference context
- Factory providers for configurable components

Usage in ``aquilia.py``::

    workspace = (
        Workspace("my-ml-app")
        .integrate(Integration.mlops(
            registry_db="registry.db",
            blob_root="./blobs",
            drift_method="psi",
        ))
    )

Or manual DI wiring::

    from aquilia.mlops.di_providers import register_mlops_providers
    register_mlops_providers(container, config)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from aquilia.di import Container
from aquilia.di.providers import ValueProvider, FactoryProvider, ClassProvider

logger = logging.getLogger("aquilia.mlops.di")


class MLOpsConfig:
    """
    Typed configuration for MLOps DI registration.

    Populated from ``Integration.mlops(...)`` or ``Workspace.mlops(...)`` config.
    """

    __slots__ = (
        "enabled",
        "registry_db",
        "blob_root",
        "storage_backend",
        "drift_method",
        "drift_threshold",
        "drift_num_bins",
        "max_batch_size",
        "max_latency_ms",
        "batching_strategy",
        "sample_rate",
        "log_dir",
        "hmac_secret",
        "signing_private_key",
        "signing_public_key",
        "encryption_key",
        "plugin_auto_discover",
        "scaling_policy",
        "metrics_model_name",
        "metrics_model_version",
    )

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        d = config_dict or {}
        self.enabled: bool = d.get("enabled", True)
        self.registry_db: str = d.get("registry_db", "registry.db")
        self.blob_root: str = d.get("blob_root", ".aquilia-store")
        self.storage_backend: str = d.get("storage_backend", "filesystem")
        self.drift_method: str = d.get("drift_method", "psi")
        self.drift_threshold: float = d.get("drift_threshold", 0.2)
        self.drift_num_bins: int = d.get("drift_num_bins", 10)
        self.max_batch_size: int = d.get("max_batch_size", 16)
        self.max_latency_ms: float = d.get("max_latency_ms", 50.0)
        self.batching_strategy: str = d.get("batching_strategy", "hybrid")
        self.sample_rate: float = d.get("sample_rate", 0.01)
        self.log_dir: str = d.get("log_dir", "prediction_logs")
        self.hmac_secret: Optional[str] = d.get("hmac_secret")
        self.signing_private_key: Optional[str] = d.get("signing_private_key")
        self.signing_public_key: Optional[str] = d.get("signing_public_key")
        self.encryption_key: Optional[bytes] = d.get("encryption_key")
        self.plugin_auto_discover: bool = d.get("plugin_auto_discover", True)
        self.scaling_policy: Optional[Dict[str, Any]] = d.get("scaling_policy")
        self.metrics_model_name: str = d.get("metrics_model_name", "")
        self.metrics_model_version: str = d.get("metrics_model_version", "")


def register_mlops_providers(
    container: Container,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Register all MLOps services as DI providers.

    This is the main integration point — call once during app startup
    to wire the entire MLOps subsystem into Aquilia's DI.

    Registered services:
    - ``MLOpsConfig`` — typed config (singleton)
    - ``MetricsCollector`` — metrics (singleton)
    - ``DriftDetector`` — drift detection (singleton)
    - ``PredictionLogger`` — prediction logging (singleton)
    - ``RegistryService`` — model registry (singleton)
    - ``PluginHost`` — plugin manager (singleton)
    - ``TrafficRouter`` — traffic routing (singleton)
    - ``RolloutEngine`` — release management (singleton)
    - ``Autoscaler`` — autoscaling engine (singleton)
    - ``PlacementScheduler`` — placement (singleton)
    - ``RBACManager`` — access control (singleton)
    - ``ArtifactSigner`` — signing (singleton)
    - ``EncryptionManager`` — encryption (singleton)
    - ``BlobEncryptor`` — blob encryption (singleton)
    """
    from .observe.metrics import MetricsCollector
    from .observe.drift import DriftDetector
    from .observe.logger import PredictionLogger
    from .registry.service import RegistryService
    from .plugins.host import PluginHost
    from .serving.router import TrafficRouter
    from .release.rollout import RolloutEngine
    from .scheduler.autoscaler import Autoscaler, ScalingPolicy
    from .scheduler.placement import PlacementScheduler
    from .security.rbac import RBACManager
    from .security.signing import ArtifactSigner, EncryptionManager
    from .security.encryption import BlobEncryptor
    from ._types import DriftMethod, BatchingStrategy

    cfg = MLOpsConfig(config)

    # Config singleton
    container.register(ValueProvider(
        value=cfg,
        token=MLOpsConfig,
        scope="singleton",
    ))

    # Metrics Collector
    collector = MetricsCollector(
        model_name=cfg.metrics_model_name,
        model_version=cfg.metrics_model_version,
    )
    container.register(ValueProvider(
        value=collector,
        token=MetricsCollector,
        scope="singleton",
    ))

    # Drift Detector
    method = DriftMethod(cfg.drift_method)
    detector = DriftDetector(
        method=method,
        threshold=cfg.drift_threshold,
        num_bins=cfg.drift_num_bins,
    )
    container.register(ValueProvider(
        value=detector,
        token=DriftDetector,
        scope="singleton",
    ))

    # Prediction Logger
    pred_logger = PredictionLogger(
        sample_rate=cfg.sample_rate,
        log_dir=cfg.log_dir,
    )
    container.register(ValueProvider(
        value=pred_logger,
        token=PredictionLogger,
        scope="singleton",
    ))

    # Registry Service
    registry = RegistryService(
        db_path=cfg.registry_db,
        blob_root=cfg.blob_root,
    )
    container.register(ValueProvider(
        value=registry,
        token=RegistryService,
        scope="singleton",
    ))

    # Plugin Host
    host = PluginHost()
    if cfg.plugin_auto_discover:
        host.discover_entrypoints()
    container.register(ValueProvider(
        value=host,
        token=PluginHost,
        scope="singleton",
    ))

    # Traffic Router
    router = TrafficRouter()
    container.register(ValueProvider(
        value=router,
        token=TrafficRouter,
        scope="singleton",
    ))

    # Rollout Engine
    rollout_engine = RolloutEngine(router=router)
    container.register(ValueProvider(
        value=rollout_engine,
        token=RolloutEngine,
        scope="singleton",
    ))

    # Autoscaler
    policy = ScalingPolicy(**(cfg.scaling_policy or {}))
    autoscaler = Autoscaler(policy=policy)
    container.register(ValueProvider(
        value=autoscaler,
        token=Autoscaler,
        scope="singleton",
    ))

    # Placement Scheduler
    placement = PlacementScheduler()
    container.register(ValueProvider(
        value=placement,
        token=PlacementScheduler,
        scope="singleton",
    ))

    # RBAC Manager
    rbac = RBACManager()
    container.register(ValueProvider(
        value=rbac,
        token=RBACManager,
        scope="singleton",
    ))

    # Artifact Signer
    signer = ArtifactSigner(
        hmac_secret=cfg.hmac_secret,
        private_key_path=cfg.signing_private_key,
        public_key_path=cfg.signing_public_key,
    )
    container.register(ValueProvider(
        value=signer,
        token=ArtifactSigner,
        scope="singleton",
    ))

    # Encryption Manager
    enc_mgr = EncryptionManager(key=cfg.encryption_key)
    container.register(ValueProvider(
        value=enc_mgr,
        token=EncryptionManager,
        scope="singleton",
    ))

    # Blob Encryptor
    blob_enc = BlobEncryptor(key=cfg.encryption_key)
    container.register(ValueProvider(
        value=blob_enc,
        token=BlobEncryptor,
        scope="singleton",
    ))

    logger.info(
        "MLOps DI providers registered: %d services wired",
        14,
    )
