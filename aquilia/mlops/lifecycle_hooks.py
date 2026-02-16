"""
MLOps Lifecycle Hooks — Startup / shutdown integration with Aquilia's
LifecycleCoordinator.

Hooks registered:
- **Startup**: Initialize registry DB, start batcher, discover plugins,
  wire DI providers.
- **Shutdown**: Stop batcher, flush metrics, deactivate plugins, close
  registry connections.

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

    # 1. Deactivate plugins
    try:
        if di_container is not None:
            from .plugins.host import PluginHost

            host = di_container.resolve(PluginHost) if hasattr(di_container, "resolve") else None
            if host:
                host.deactivate_all()
                logger.info("  ✓ Plugins deactivated")
    except Exception as exc:
        logger.debug("  Plugin shutdown: %s", exc)

    # 2. Close registry
    try:
        if di_container is not None:
            from .registry.service import RegistryService

            registry = di_container.resolve(RegistryService) if hasattr(di_container, "resolve") else None
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

    return flat
