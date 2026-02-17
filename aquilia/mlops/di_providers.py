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
        # LLM/SLM settings
        "rate_limit_rps",
        "rate_limit_capacity",
        "circuit_breaker_failure_threshold",
        "circuit_breaker_timeout",
        "memory_soft_limit_mb",
        "memory_hard_limit_mb",
        # Ecosystem integration
        "cache_enabled",
        "cache_ttl",
        "cache_namespace",
        "artifact_store_dir",
        "fault_engine_debug",
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
        # LLM/SLM
        self.rate_limit_rps: float = d.get("rate_limit_rps", 0.0)
        self.rate_limit_capacity: int = d.get("rate_limit_capacity", 0)
        self.circuit_breaker_failure_threshold: int = d.get("circuit_breaker_failure_threshold", 5)
        self.circuit_breaker_timeout: float = d.get("circuit_breaker_timeout", 30.0)
        self.memory_soft_limit_mb: int = d.get("memory_soft_limit_mb", 0)
        self.memory_hard_limit_mb: int = d.get("memory_hard_limit_mb", 0)
        # Ecosystem integration
        self.cache_enabled: bool = d.get("cache_enabled", True)
        self.cache_ttl: int = d.get("cache_ttl", 60)
        self.cache_namespace: str = d.get("cache_namespace", "mlops")
        self.artifact_store_dir: str = d.get("artifact_store_dir", "artifacts")
        self.fault_engine_debug: bool = d.get("fault_engine_debug", False)


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
    - ``CircuitBreaker`` — circuit breaker (singleton)
    - ``TokenBucketRateLimiter`` — rate limiter (singleton)
    - ``MemoryTracker`` — memory management (singleton)
    - ``ModelLineageDAG`` — lineage tracking (singleton)
    - ``ExperimentLedger`` — A/B experiments (singleton)
    - ``MLOpsController`` — HTTP controller (singleton)

    Ecosystem services (from Aquilia core, shared or created):
    - ``FaultEngine`` — fault processing (resolve from container or create)
    - ``CacheService`` — caching layer (resolve from container or skip)
    - ``FilesystemArtifactStore`` — artifact storage (singleton)
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
    from ._structures import (
        CircuitBreaker,
        ExperimentLedger,
        MemoryTracker,
        ModelLineageDAG,
        TokenBucketRateLimiter,
    )
    from .controller import MLOpsController

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

    # Circuit Breaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=cfg.circuit_breaker_failure_threshold,
        timeout_seconds=cfg.circuit_breaker_timeout,
    )
    container.register(ValueProvider(
        value=circuit_breaker,
        token=CircuitBreaker,
        scope="singleton",
    ))

    # Rate Limiter (only if rps > 0)
    rate_limiter: Optional[TokenBucketRateLimiter] = None
    if cfg.rate_limit_rps > 0:
        cap = cfg.rate_limit_capacity or int(cfg.rate_limit_rps * 10)
        rate_limiter = TokenBucketRateLimiter(rate=cfg.rate_limit_rps, capacity=cap)
    container.register(ValueProvider(
        value=rate_limiter,
        token=TokenBucketRateLimiter,
        scope="singleton",
    ))

    # Memory Tracker (only if hard limit > 0)
    memory_tracker: Optional[MemoryTracker] = None
    if cfg.memory_hard_limit_mb > 0:
        memory_tracker = MemoryTracker(
            soft_limit_mb=cfg.memory_soft_limit_mb or cfg.memory_hard_limit_mb,
            hard_limit_mb=cfg.memory_hard_limit_mb,
        )
    container.register(ValueProvider(
        value=memory_tracker,
        token=MemoryTracker,
        scope="singleton",
    ))

    # Model Lineage DAG
    lineage_dag = ModelLineageDAG()
    container.register(ValueProvider(
        value=lineage_dag,
        token=ModelLineageDAG,
        scope="singleton",
    ))

    # Experiment Ledger
    experiment_ledger = ExperimentLedger()
    container.register(ValueProvider(
        value=experiment_ledger,
        token=ExperimentLedger,
        scope="singleton",
    ))

    # ── Aquilia Ecosystem Services ───────────────────────────────────

    # FaultEngine — resolve from container or create dedicated instance
    fault_engine = None
    try:
        from aquilia.faults import FaultEngine
        # Check if FaultEngine was pre-registered (e.g. by the app)
        token_key = container._token_to_key(FaultEngine) if hasattr(container, '_token_to_key') else None
        cached = container._cache.get(token_key) if token_key and hasattr(container, '_cache') else None
        if cached is not None:
            fault_engine = cached
        else:
            fault_engine = FaultEngine(debug=cfg.fault_engine_debug)
            container.register(ValueProvider(
                value=fault_engine,
                token=FaultEngine,
                scope="singleton",
            ))

        # Register MLOps-specific fault handler
        from .faults import MLOpsFault
        from aquilia.faults.handlers import FaultHandler
        from aquilia.faults.core import FaultContext, Escalate

        class MLOpsFaultHandler(FaultHandler):
            """Handler that logs MLOps-domain faults with structured metadata."""

            async def handle(self, ctx: FaultContext):
                if isinstance(ctx.fault, MLOpsFault):
                    logger.warning(
                        "MLOps fault [%s/%s]: %s",
                        ctx.fault.domain.name if hasattr(ctx.fault.domain, "name") else ctx.fault.domain,
                        ctx.fault.code,
                        ctx.fault.message,
                    )
                return Escalate()

        fault_engine.register_app("mlops", MLOpsFaultHandler())
        logger.info("  ✓ FaultEngine wired with MLOps handler")
    except Exception as exc:
        logger.debug("  FaultEngine integration skipped: %s", exc)

    # CacheService — resolve from container if available
    cache_service = None
    try:
        from aquilia.cache import CacheService
        # Check if CacheService was pre-registered
        token_key = container._token_to_key(CacheService) if hasattr(container, '_token_to_key') else None
        cached = container._cache.get(token_key) if token_key and hasattr(container, '_cache') else None
        if cached is not None:
            cache_service = cached
            logger.info("  ✓ CacheService resolved from DI container")
        elif cfg.cache_enabled:
            from aquilia.cache import MemoryBackend, CacheConfig
            backend = MemoryBackend(max_size=1024)
            cache_config = CacheConfig(
                default_ttl=cfg.cache_ttl,
                namespace=cfg.cache_namespace,
            )
            cache_service = CacheService(backend, cache_config)
            container.register(ValueProvider(
                value=cache_service,
                token=CacheService,
                scope="singleton",
            ))
            logger.info("  ✓ CacheService created (memory backend)")
    except Exception as exc:
        logger.debug("  CacheService integration skipped: %s", exc)

    # ArtifactStore — for model artifact management
    artifact_store = None
    try:
        from aquilia.artifacts import FilesystemArtifactStore
        artifact_store = FilesystemArtifactStore(cfg.artifact_store_dir)
        container.register(ValueProvider(
            value=artifact_store,
            token=FilesystemArtifactStore,
            scope="singleton",
        ))
        logger.info("  ✓ ArtifactStore registered (%s)", cfg.artifact_store_dir)
    except Exception as exc:
        logger.debug("  ArtifactStore integration skipped: %s", exc)

    # MLOps Controller (with ecosystem services injected)
    controller = MLOpsController(
        registry=registry,
        metrics_collector=collector,
        drift_detector=detector,
        rollout_engine=rollout_engine,
        plugin_host=host,
        rbac_manager=rbac,
        lineage_dag=lineage_dag,
        experiment_ledger=experiment_ledger,
        cache_service=cache_service,
        fault_engine=fault_engine,
        artifact_store=artifact_store,
    )
    container.register(ValueProvider(
        value=controller,
        token=MLOpsController,
        scope="singleton",
    ))

    logger.info(
        "MLOps DI providers registered: %d+ services wired (ecosystem: cache=%s, faults=%s, artifacts=%s)",
        20,
        cache_service is not None,
        fault_engine is not None,
        artifact_store is not None,
    )
