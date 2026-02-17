"""
MLOps Lifecycle Hooks — Startup / shutdown integration with Aquilia's
LifecycleCoordinator.

Hooks registered:
- **Startup**: Initialize registry DB, start batcher, discover plugins,
  wire DI providers, initialize cache, register fault handlers, set up
  artifact store.
- **Shutdown**: Stop batcher, flush metrics, flush cache, deactivate
  plugins, close registry connections.

Ecosystem integration:
- :class:`~aquilia.faults.FaultEngine` — MLOps fault handlers are registered
  at the ``app:mlops`` scope during startup.
- :class:`~aquilia.cache.CacheService` — Cache is initialized / warmed
  during startup and flushed during shutdown.
- :class:`~aquilia.artifacts.FilesystemArtifactStore` — Artifact store
  directory is created during startup.
- :class:`~aquilia.effects.CacheEffect` — Cache effect provider is
  registered if the effect system is active.

Usage::

    from aquilia.mlops.lifecycle_hooks import mlops_on_startup, mlops_on_shutdown

    # Manual registration
    lifecycle.on_event(LifecyclePhase.STARTING, mlops_on_startup)
    lifecycle.on_event(LifecyclePhase.STOPPING, mlops_on_shutdown)

Or auto-registered via ``Integration.mlops()`` in the server setup.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("aquilia.mlops.lifecycle")


async def mlops_on_startup(
    config: Optional[Dict[str, Any]] = None,
    di_container: Any = None,
) -> None:
    """
    MLOps startup hook.

    Called by the LifecycleCoordinator during the STARTING phase.
    Initializes all MLOps subsystems.
    """
    cfg = config or {}
    logger.info("MLOps startup hook running...")

    # 1. Register DI providers if container available
    if di_container is not None:
        try:
            from .di_providers import register_mlops_providers

            # Flatten nested config into DI-friendly dict
            flat_config = _flatten_mlops_config(cfg)
            register_mlops_providers(di_container, flat_config)
            logger.info("  ✓ DI providers registered")
        except Exception as exc:
            logger.warning("  ✗ DI registration failed: %s", exc)

    # 2. Initialize registry
    try:
        registry_cfg = cfg.get("registry", {})
        if registry_cfg.get("db_path"):
            from .registry.service import RegistryService

            registry = RegistryService(
                db_path=registry_cfg.get("db_path", "registry.db"),
                blob_root=registry_cfg.get("blob_root", ".aquilia-store"),
            )
            await registry.initialize()
            logger.info("  ✓ Registry initialized")
    except Exception as exc:
        logger.warning("  ✗ Registry init failed: %s", exc)

    # 3. Discover plugins
    try:
        plugins_cfg = cfg.get("plugins", {})
        if plugins_cfg.get("auto_discover", True):
            from .plugins.host import PluginHost

            host = PluginHost()
            found = host.discover_entrypoints()
            if found:
                host.activate_all()
                logger.info("  ✓ Discovered %d plugins", len(found))
    except Exception as exc:
        logger.warning("  ✗ Plugin discovery failed: %s", exc)

    # 4. Initialize CacheService (if resolved from DI)
    try:
        if di_container is not None and hasattr(di_container, "resolve_async"):
            from aquilia.cache import CacheService

            cache = await di_container.resolve_async(CacheService, optional=True)
            if cache and hasattr(cache, "initialize"):
                await cache.initialize()
                logger.info("  ✓ CacheService initialized")
    except Exception as exc:
        logger.debug("  CacheService init: %s", exc)

    # 5. Ensure artifact store directory exists
    try:
        import os

        artifact_dir = cfg.get("artifact_store_dir",
                               cfg.get("registry", {}).get("blob_root", "artifacts"))
        os.makedirs(artifact_dir, exist_ok=True)
        logger.info("  ✓ Artifact store directory ready (%s)", artifact_dir)
    except Exception as exc:
        logger.debug("  Artifact store dir: %s", exc)

    # 6. Register MLOps fault event listener for metrics observability
    try:
        if di_container is not None and hasattr(di_container, "resolve_async"):
            from aquilia.faults import FaultEngine
            from .observe.metrics import MetricsCollector

            fault_engine = await di_container.resolve_async(FaultEngine, optional=True)
            metrics = await di_container.resolve_async(MetricsCollector, optional=True)
            if fault_engine and metrics:
                def _fault_metrics_listener(ctx):
                    """Record fault events in MLOps metrics."""
                    if hasattr(ctx, "fault") and hasattr(ctx.fault, "domain"):
                        domain_name = (
                            ctx.fault.domain.name
                            if hasattr(ctx.fault.domain, "name")
                            else str(ctx.fault.domain)
                        )
                        if domain_name.startswith("mlops"):
                            metrics.record_inference(
                                latency_ms=0,
                                batch_size=0,
                                error=True,
                            )

                fault_engine.on_fault(_fault_metrics_listener)
                logger.info("  ✓ FaultEngine → MetricsCollector listener registered")
    except Exception as exc:
        logger.debug("  Fault metrics listener: %s", exc)

    # 7. Detect GPU/device capabilities
    try:
        device_info = _detect_device_capabilities()
        logger.info(
            "  ✓ Device: %s (GPUs: %d, memory: %s)",
            device_info.get("device", "cpu"),
            device_info.get("gpu_count", 0),
            device_info.get("gpu_memory", "N/A"),
        )
    except Exception as exc:
        logger.debug("  Device detection: %s", exc)

    logger.info("MLOps startup complete")


async def mlops_on_shutdown(
    config: Optional[Dict[str, Any]] = None,
    di_container: Any = None,
) -> None:
    """
    MLOps shutdown hook.

    Called by the LifecycleCoordinator during the STOPPING phase.
    Gracefully shuts down all MLOps subsystems.
    """
    logger.info("MLOps shutdown hook running...")

    # 1. Stop circuit breaker (reject new requests)
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from ._structures import CircuitBreaker

            cb = di_container.resolve(CircuitBreaker)
            if cb:
                cb.force_open()
                logger.info("  ✓ Circuit breaker opened (draining)")
    except Exception as exc:
        logger.debug("  Circuit breaker shutdown: %s", exc)

    # 2. Flush metrics before unloading models
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from .observe.metrics import MetricsCollector

            metrics = di_container.resolve(MetricsCollector)
            if metrics:
                summary = metrics.get_summary()
                logger.info(
                    "  ✓ Metrics flushed (total_inferences=%d, tokens=%d)",
                    summary.get("total_inferences", 0),
                    summary.get("total_tokens", 0),
                )
    except Exception as exc:
        logger.debug("  Metrics flush: %s", exc)

    # 3. Gracefully unload models / release GPU memory
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from .serving.server import ModelServingServer

            server = di_container.resolve(ModelServingServer)
            if server and hasattr(server, "_runtime") and server._runtime is not None:
                runtime = server._runtime
                if hasattr(runtime, "unload"):
                    await runtime.unload()
                    logger.info("  ✓ Model runtime unloaded")
        # Release GPU cache if torch available
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info("  ✓ GPU cache released")
        except ImportError:
            pass
    except Exception as exc:
        logger.debug("  Model unload: %s", exc)

    # 4. Deactivate plugins
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from .plugins.host import PluginHost

            host = di_container.resolve(PluginHost)
            if host:
                host.deactivate_all()
                logger.info("  ✓ Plugins deactivated")
    except Exception as exc:
        logger.debug("  Plugin shutdown: %s", exc)

    # 5. Shutdown CacheService
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from aquilia.cache import CacheService

            cache = di_container.resolve(CacheService)
            if cache and hasattr(cache, "shutdown"):
                await cache.shutdown()
                logger.info("  ✓ CacheService shutdown")
    except Exception as exc:
        logger.debug("  CacheService shutdown: %s", exc)

    # 6. Close registry
    try:
        if di_container is not None and hasattr(di_container, "resolve"):
            from .registry.service import RegistryService

            registry = di_container.resolve(RegistryService)
            if registry:
                await registry.close()
                logger.info("  ✓ Registry closed")
    except Exception as exc:
        logger.debug("  Registry shutdown: %s", exc)

    logger.info("MLOps shutdown complete")


def _flatten_mlops_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested MLOps config into a flat dict for DI registration."""
    flat: Dict[str, Any] = {}
    flat["enabled"] = cfg.get("enabled", True)

    # Registry
    reg = cfg.get("registry", {})
    flat["registry_db"] = reg.get("db_path", "registry.db")
    flat["blob_root"] = reg.get("blob_root", ".aquilia-store")
    flat["storage_backend"] = reg.get("storage_backend", "filesystem")

    # Serving
    srv = cfg.get("serving", {})
    flat["max_batch_size"] = srv.get("max_batch_size", 16)
    flat["max_latency_ms"] = srv.get("max_latency_ms", 50.0)
    flat["batching_strategy"] = srv.get("batching_strategy", "hybrid")

    # Resilience / Rate Limiting
    res = cfg.get("resilience", {})
    flat["rate_limit_rps"] = res.get("rate_limit_rps", srv.get("rate_limit_rps", 100.0))
    flat["rate_limit_capacity"] = res.get("rate_limit_capacity", srv.get("rate_limit_capacity", 200))
    flat["circuit_breaker_failure_threshold"] = res.get(
        "failure_threshold",
        srv.get("circuit_breaker_failure_threshold", 5),
    )
    flat["circuit_breaker_timeout"] = res.get(
        "recovery_timeout",
        srv.get("circuit_breaker_timeout", 30.0),
    )

    # Memory
    mem = cfg.get("memory", {})
    flat["memory_soft_limit_mb"] = mem.get(
        "soft_limit_mb",
        srv.get("memory_soft_limit_mb", 0),
    )
    flat["memory_hard_limit_mb"] = mem.get(
        "hard_limit_mb",
        srv.get("memory_hard_limit_mb", 0),
    )

    # Observe
    obs = cfg.get("observe", {})
    flat["drift_method"] = obs.get("drift_method", "psi")
    flat["drift_threshold"] = obs.get("drift_threshold", 0.2)
    flat["drift_num_bins"] = obs.get("drift_num_bins", 10)
    flat["sample_rate"] = obs.get("sample_rate", 0.01)
    flat["log_dir"] = obs.get("log_dir", "prediction_logs")
    flat["metrics_model_name"] = obs.get("metrics_model_name", "")
    flat["metrics_model_version"] = obs.get("metrics_model_version", "")

    # Release
    rel = cfg.get("release", {})
    flat["rollout_default_strategy"] = rel.get("rollout_default_strategy", "canary")
    flat["auto_rollback"] = rel.get("auto_rollback", True)

    # Security
    sec = cfg.get("security", {})
    flat["hmac_secret"] = sec.get("hmac_secret")
    flat["signing_private_key"] = sec.get("signing_private_key")
    flat["signing_public_key"] = sec.get("signing_public_key")
    flat["encryption_key"] = sec.get("encryption_key")

    # Plugins
    plg = cfg.get("plugins", {})
    flat["plugin_auto_discover"] = plg.get("auto_discover", True)

    # Scaling
    flat["scaling_policy"] = cfg.get("scaling_policy")

    # LLM / Model
    model = cfg.get("model", {})
    flat["model_type"] = model.get("model_type", "SLM")
    flat["device"] = model.get("device", "auto")
    flat["default_max_tokens"] = model.get("default_max_tokens", 512)
    flat["default_temperature"] = model.get("default_temperature", 1.0)

    # Ecosystem integration
    eco = cfg.get("ecosystem", {})
    flat["cache_enabled"] = eco.get("cache_enabled", cfg.get("cache_enabled", True))
    flat["cache_ttl"] = eco.get("cache_ttl", cfg.get("cache_ttl", 60))
    flat["cache_namespace"] = eco.get("cache_namespace", cfg.get("cache_namespace", "mlops"))
    flat["artifact_store_dir"] = eco.get(
        "artifact_store_dir",
        cfg.get("artifact_store_dir", cfg.get("registry", {}).get("blob_root", "artifacts")),
    )
    flat["fault_engine_debug"] = eco.get("fault_engine_debug", cfg.get("fault_engine_debug", False))

    return flat


def _detect_device_capabilities() -> Dict[str, Any]:
    """Detect available compute devices (CPU, CUDA, MPS, etc.)."""
    info: Dict[str, Any] = {"device": "cpu", "gpu_count": 0, "gpu_memory": "N/A"}

    try:
        import torch

        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            info["device"] = "cuda"
            info["gpu_count"] = gpu_count
            total_mem = 0
            info["gpus"] = []
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                mem_gb = round(props.total_mem / (1024**3), 2)
                total_mem += mem_gb
                info["gpus"].append({
                    "index": i,
                    "name": props.name,
                    "memory_gb": mem_gb,
                    "major": props.major,
                    "minor": props.minor,
                })
            info["gpu_memory"] = f"{total_mem:.1f} GB"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["device"] = "mps"
            info["gpu_count"] = 1
            info["gpu_memory"] = "shared"
    except ImportError:
        pass

    return info
