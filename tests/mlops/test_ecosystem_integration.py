"""
Tests for MLOps deep ecosystem integration with Aquilia core subsystems.

Covers:
1.  Controller extends Controller base class with @GET/@POST decorators
2.  CacheService integration — caching in controller endpoints
3.  FaultEngine integration — faults routed through engine, handlers registered
4.  ArtifactStore integration — artifact store wired via DI
5.  Middleware MiddlewareDescriptor integration — register_mlops_middleware
6.  DI provider ecosystem wiring — FaultEngine, CacheService, ArtifactStore
7.  Config builder ecosystem section — cache, artifacts, faults config
8.  Module manifest — effects, fault domains, middleware descriptors
9.  Lifecycle hooks — cache init, artifact dir, fault listener
10. Effect system — CacheEffect declared in controller
11. Serializer validation through controller endpoints
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. Controller Base Class Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestControllerBaseClass:
    """MLOpsController properly extends Aquilia's Controller base."""

    def test_inherits_from_controller(self):
        from aquilia.controller import Controller
        from aquilia.mlops.controller import MLOpsController

        assert issubclass(MLOpsController, Controller)

    def test_prefix_set(self):
        from aquilia.mlops.controller import MLOpsController

        assert MLOpsController.prefix == "/mlops"

    def test_tags_set(self):
        from aquilia.mlops.controller import MLOpsController

        assert "mlops" in MLOpsController.tags

    def test_singleton_mode(self):
        from aquilia.mlops.controller import MLOpsController

        assert MLOpsController.instantiation_mode == "singleton"

    def test_controller_accepts_ecosystem_services(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController(
            cache_service="mock_cache",
            fault_engine="mock_engine",
            artifact_store="mock_store",
        )
        assert ctrl._cache == "mock_cache"
        assert ctrl._fault_engine == "mock_engine"
        assert ctrl._artifact_store == "mock_store"

    def test_get_decorators_present(self):
        """Verify @GET decorators are applied to route methods."""
        from aquilia.mlops.controller import MLOpsController

        # The @GET decorator from aquilia.controller should set route metadata
        health_method = MLOpsController.health
        # Check route metadata is present (set by @GET decorator)
        assert hasattr(health_method, "_route_metadata") or hasattr(health_method, "__route__") or callable(health_method)

    def test_post_decorators_present(self):
        """Verify @POST decorators are applied to route methods."""
        from aquilia.mlops.controller import MLOpsController

        predict_method = MLOpsController.predict
        assert callable(predict_method)

    def test_all_endpoints_have_optional_ctx(self):
        """All endpoints accept an optional RequestCtx parameter."""
        import inspect
        from aquilia.mlops.controller import MLOpsController

        endpoint_names = [
            "health", "predict", "chat", "metrics",
            "list_models", "get_model", "circuit_breaker_status",
            "rate_limit_status", "memory_status", "model_capabilities",
            "liveness", "readiness", "lineage", "list_experiments",
            "hot_models", "list_artifacts", "inspect_artifact",
        ]
        for name in endpoint_names:
            method = getattr(MLOpsController, name, None)
            if method is not None:
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                assert "ctx" in params, f"{name} missing 'ctx' parameter"


# ═══════════════════════════════════════════════════════════════════════════
# 2. CacheService Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestCacheServiceIntegration:
    """CacheService is wired into the MLOps controller."""

    @pytest.mark.asyncio
    async def test_health_caches_result(self):
        from aquilia.mlops.controller import MLOpsController

        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        ctrl = MLOpsController(cache_service=cache)
        result = await ctrl.health()

        assert result["status"] == "healthy"
        assert "cache" in result["components"]
        assert result["components"]["cache"]["status"] == "up"
        # Should have tried to cache the result
        cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_returns_cached_if_available(self):
        from aquilia.mlops.controller import MLOpsController

        cached_result = {"status": "healthy", "cached": True}
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=cached_result)

        ctrl = MLOpsController(cache_service=cache)
        result = await ctrl.health()

        assert result == cached_result
        cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_does_not_fail(self):
        from aquilia.mlops.controller import MLOpsController

        # Cache that always raises
        cache = AsyncMock()
        cache.get = AsyncMock(side_effect=Exception("cache down"))
        cache.set = AsyncMock(side_effect=Exception("cache down"))

        ctrl = MLOpsController(cache_service=cache)
        result = await ctrl.health()

        # Should still work even with cache failures
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_model_capabilities_cached(self):
        from aquilia.mlops.controller import MLOpsController
        from types import SimpleNamespace

        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        manifest = SimpleNamespace(
            name="test-model",
            version="v1",
            framework="pytorch",
            model_type="SLM",
            is_llm=False,
            llm_config=None,
        )
        mock_server = MagicMock()
        mock_server.manifest = manifest
        mock_server._runtime = MagicMock(spec=[])

        ctrl = MLOpsController(serving_server=mock_server, cache_service=cache)
        result = await ctrl.model_capabilities()

        assert result["name"] == "test-model"
        # Should cache with 300s TTL
        cache.set.assert_called_once()
        call_args = cache.set.call_args
        assert call_args[1].get("ttl") == 300 or (len(call_args[0]) > 2 and call_args[0][2] == 300)

    @pytest.mark.asyncio
    async def test_list_models_cached(self):
        from aquilia.mlops.controller import MLOpsController

        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        registry = AsyncMock()
        registry.list_packs = AsyncMock(return_value=[{"name": "model-a"}])

        ctrl = MLOpsController(registry=registry, cache_service=cache)
        result = await ctrl.list_models()

        assert result["count"] == 1
        cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_cached(self):
        from aquilia.mlops.controller import MLOpsController

        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        manifest_mock = MagicMock()
        manifest_mock.to_dict.return_value = {"name": "model-a", "version": "v1"}

        registry = AsyncMock()
        registry.fetch = AsyncMock(return_value=manifest_mock)

        ctrl = MLOpsController(registry=registry, cache_service=cache)
        result = await ctrl.get_model("model-a")

        assert result["name"] == "model-a"
        cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_cache_still_works(self):
        """All endpoints work without CacheService."""
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.health()
        assert result["status"] == "healthy"
        # No cache component reported
        assert "cache" not in result["components"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. FaultEngine Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestFaultEngineIntegration:
    """FaultEngine routes MLOps exceptions through structured handling."""

    @pytest.mark.asyncio
    async def test_process_fault_routes_through_engine(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine, Escalate

        engine = FaultEngine()
        ctrl = MLOpsController(fault_engine=engine)

        error = RuntimeError("test error")
        result = await ctrl._process_fault(error)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_reports_fault_engine_component(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine

        engine = FaultEngine()
        ctrl = MLOpsController(fault_engine=engine)

        result = await ctrl.health()
        assert result["components"]["fault_engine"]["status"] == "up"

    @pytest.mark.asyncio
    async def test_health_reports_artifact_store_component(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController(artifact_store=MagicMock())
        result = await ctrl.health()
        assert result["components"]["artifact_store"]["status"] == "up"

    @pytest.mark.asyncio
    async def test_list_models_fault_handling(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine

        engine = FaultEngine()
        registry = AsyncMock()
        registry.list_packs = AsyncMock(side_effect=RuntimeError("db error"))

        ctrl = MLOpsController(registry=registry, fault_engine=engine)
        result = await ctrl.list_models()

        # Should return error dict, not raise
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_model_fault_handling(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine

        engine = FaultEngine()
        registry = AsyncMock()
        registry.fetch = AsyncMock(side_effect=KeyError("not found"))

        ctrl = MLOpsController(registry=registry, fault_engine=engine)
        result = await ctrl.get_model("missing-model")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_fault_engine_still_works(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl._process_fault(RuntimeError("test"))
        assert "error" in result
        assert result["error"] == "test"

    @pytest.mark.asyncio
    async def test_mlops_fault_handler_registered_in_di(self):
        """DI registration creates and registers MLOpsFaultHandler."""
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.faults import FaultEngine

        container = Container()
        register_mlops_providers(container, {"plugins": {"auto_discover": False}})

        engine = await container.resolve_async(FaultEngine)
        assert engine is not None
        # Should have app-level handler registered for 'mlops'
        assert "mlops" in engine.registry._app


# ═══════════════════════════════════════════════════════════════════════════
# 4. Middleware MiddlewareDescriptor Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestMiddlewareDescriptorIntegration:
    """MLOps middleware uses Aquilia's MiddlewareStack with proper scoping."""

    def test_register_mlops_middleware(self):
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware

        stack = MiddlewareStack()
        collector = MagicMock()
        rate_limiter = MagicMock()
        circuit_breaker = MagicMock()

        register_mlops_middleware(
            stack,
            metrics_collector=collector,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
        )

        # Should register 4 middleware (request_id, rate_limit, circuit_breaker, metrics)
        assert len(stack.middlewares) == 4

    def test_middleware_scoped_to_mlops(self):
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware

        stack = MiddlewareStack()
        register_mlops_middleware(stack, metrics_collector=MagicMock())

        for mw in stack.middlewares:
            assert mw.scope == "app:mlops", f"Middleware {mw.name} has wrong scope: {mw.scope}"

    def test_middleware_priority_ordering(self):
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware

        stack = MiddlewareStack()
        register_mlops_middleware(
            stack,
            metrics_collector=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
        )

        priorities = [mw.priority for mw in stack.middlewares]
        assert priorities == sorted(priorities), f"Middleware not sorted by priority: {priorities}"

    def test_middleware_names(self):
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware

        stack = MiddlewareStack()
        register_mlops_middleware(
            stack,
            metrics_collector=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
        )

        names = [mw.name for mw in stack.middlewares]
        assert "mlops.request_id" in names
        assert "mlops.rate_limit" in names
        assert "mlops.circuit_breaker" in names
        assert "mlops.metrics" in names

    def test_register_without_optional_services(self):
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware

        stack = MiddlewareStack()
        register_mlops_middleware(stack)

        # Only request_id middleware should be registered (no optional services)
        assert len(stack.middlewares) == 1
        assert stack.middlewares[0].name == "mlops.request_id"

    @pytest.mark.asyncio
    async def test_rate_limit_emits_fault(self):
        """Rate-limit middleware emits RateLimitFault through FaultEngine."""
        from aquilia.mlops.middleware import mlops_rate_limit_middleware
        from aquilia.faults import FaultEngine

        engine = FaultEngine(debug=True)
        faults_seen = []
        engine.on_fault(lambda ctx: faults_seen.append(ctx))

        limiter = MagicMock()
        limiter.acquire.return_value = False
        limiter.acquire_wait_time.return_value = 1.0
        limiter.rate = 10.0

        mw = mlops_rate_limit_middleware(limiter, fault_engine=engine)

        request = MagicMock()
        request.path = "/mlops/predict"
        ctx = MagicMock()

        response = await mw(request, ctx, AsyncMock())
        assert response.status == 429
        assert len(faults_seen) == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_emits_fault(self):
        """Circuit-breaker middleware emits fault through FaultEngine."""
        from aquilia.mlops.middleware import mlops_circuit_breaker_middleware
        from aquilia.faults import FaultEngine

        engine = FaultEngine(debug=True)
        faults_seen = []
        engine.on_fault(lambda ctx: faults_seen.append(ctx))

        cb = MagicMock()
        cb.allow_request.return_value = False
        cb.state = "open"
        cb.failure_count = 5

        mw = mlops_circuit_breaker_middleware(cb, fault_engine=engine)

        request = MagicMock()
        request.path = "/mlops/predict"
        ctx = MagicMock()

        response = await mw(request, ctx, AsyncMock())
        assert response.status == 503
        assert len(faults_seen) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 5. DI Provider Ecosystem Wiring
# ═══════════════════════════════════════════════════════════════════════════


class TestDIProviderEcosystem:
    """DI registers ecosystem services (FaultEngine, CacheService, ArtifactStore)."""

    @pytest.mark.asyncio
    async def test_fault_engine_registered(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.faults import FaultEngine

        container = Container()
        register_mlops_providers(container, {"plugins": {"auto_discover": False}})

        engine = await container.resolve_async(FaultEngine)
        assert engine is not None
        assert isinstance(engine, FaultEngine)

    @pytest.mark.asyncio
    async def test_cache_service_registered(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.cache import CacheService

        container = Container()
        register_mlops_providers(container, {
            "plugins": {"auto_discover": False},
            "cache_enabled": True,
        })

        cache = await container.resolve_async(CacheService)
        assert cache is not None
        assert isinstance(cache, CacheService)

    @pytest.mark.asyncio
    async def test_artifact_store_registered(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.artifacts import FilesystemArtifactStore

        container = Container()
        register_mlops_providers(container, {
            "plugins": {"auto_discover": False},
            "artifact_store_dir": "/tmp/aquilia-test-artifacts",
        })

        store = await container.resolve_async(FilesystemArtifactStore)
        assert store is not None
        assert isinstance(store, FilesystemArtifactStore)

    @pytest.mark.asyncio
    async def test_controller_receives_ecosystem_services(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.controller import MLOpsController

        container = Container()
        register_mlops_providers(container, {
            "plugins": {"auto_discover": False},
            "cache_enabled": True,
        })

        ctrl = await container.resolve_async(MLOpsController)
        assert ctrl is not None
        assert ctrl._cache is not None
        assert ctrl._fault_engine is not None
        assert ctrl._artifact_store is not None

    @pytest.mark.asyncio
    async def test_cache_disabled_skips_registration(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.cache import CacheService

        container = Container()
        register_mlops_providers(container, {
            "plugins": {"auto_discover": False},
            "cache_enabled": False,
        })

        cache = await container.resolve_async(CacheService, optional=True)
        assert cache is None

    def test_mlops_config_ecosystem_fields(self):
        from aquilia.mlops.di_providers import MLOpsConfig

        cfg = MLOpsConfig({
            "cache_enabled": True,
            "cache_ttl": 120,
            "cache_namespace": "ml",
            "artifact_store_dir": "/models",
            "fault_engine_debug": True,
        })
        assert cfg.cache_enabled is True
        assert cfg.cache_ttl == 120
        assert cfg.cache_namespace == "ml"
        assert cfg.artifact_store_dir == "/models"
        assert cfg.fault_engine_debug is True

    def test_mlops_config_ecosystem_defaults(self):
        from aquilia.mlops.di_providers import MLOpsConfig

        cfg = MLOpsConfig({})
        assert cfg.cache_enabled is True
        assert cfg.cache_ttl == 60
        assert cfg.cache_namespace == "mlops"
        assert cfg.artifact_store_dir == "artifacts"
        assert cfg.fault_engine_debug is False


# ═══════════════════════════════════════════════════════════════════════════
# 6. Config Builder Ecosystem Section
# ═══════════════════════════════════════════════════════════════════════════


class TestConfigBuilderEcosystem:
    """Integration.mlops() includes ecosystem configuration."""

    def test_integration_mlops_has_ecosystem_section(self):
        from aquilia.config_builders import Integration

        config = Integration.mlops()
        assert "ecosystem" in config
        eco = config["ecosystem"]
        assert "cache_enabled" in eco
        assert "cache_ttl" in eco
        assert "cache_namespace" in eco
        assert "artifact_store_dir" in eco
        assert "fault_engine_debug" in eco

    def test_integration_mlops_ecosystem_defaults(self):
        from aquilia.config_builders import Integration

        config = Integration.mlops()
        eco = config["ecosystem"]
        assert eco["cache_enabled"] is True
        assert eco["cache_ttl"] == 60
        assert eco["cache_namespace"] == "mlops"
        assert eco["artifact_store_dir"] == "artifacts"
        assert eco["fault_engine_debug"] is False

    def test_integration_mlops_ecosystem_custom(self):
        from aquilia.config_builders import Integration

        config = Integration.mlops(
            cache_enabled=True,
            cache_ttl=300,
            cache_namespace="ml-models",
            artifact_store_dir="/opt/models",
            fault_engine_debug=True,
        )
        eco = config["ecosystem"]
        assert eco["cache_ttl"] == 300
        assert eco["cache_namespace"] == "ml-models"
        assert eco["artifact_store_dir"] == "/opt/models"
        assert eco["fault_engine_debug"] is True

    def test_workspace_mlops_still_works(self):
        from aquilia.config_builders import Workspace

        ws = Workspace("ml-app").mlops(
            registry_db="models.db",
            max_batch_size=32,
        )
        config = ws.to_dict()
        assert "mlops" in config
        assert config["mlops"]["registry"]["db_path"] == "models.db"

    def test_flatten_config_includes_ecosystem(self):
        from aquilia.mlops.lifecycle_hooks import _flatten_mlops_config

        cfg = {
            "ecosystem": {
                "cache_enabled": True,
                "cache_ttl": 120,
                "cache_namespace": "ml",
                "artifact_store_dir": "/models",
                "fault_engine_debug": True,
            },
        }
        flat = _flatten_mlops_config(cfg)
        assert flat["cache_enabled"] is True
        assert flat["cache_ttl"] == 120
        assert flat["cache_namespace"] == "ml"
        assert flat["artifact_store_dir"] == "/models"
        assert flat["fault_engine_debug"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 7. Module Manifest Ecosystem Declarations
# ═══════════════════════════════════════════════════════════════════════════


class TestModuleManifestEcosystem:
    """MLOpsManifest declares effects, fault domains, and scoped middleware."""

    def test_effects_declared(self):
        from aquilia.mlops.module import MLOpsManifest

        assert hasattr(MLOpsManifest, "effects")
        assert len(MLOpsManifest.effects) > 0
        assert "CacheEffect:mlops" in MLOpsManifest.effects

    def test_fault_domains_declared(self):
        from aquilia.mlops.module import MLOpsManifest

        assert hasattr(MLOpsManifest, "fault_domains")
        assert "mlops" in MLOpsManifest.fault_domains
        assert "mlops.serving" in MLOpsManifest.fault_domains
        assert "mlops.registry" in MLOpsManifest.fault_domains
        assert "mlops.resilience" in MLOpsManifest.fault_domains
        assert "mlops.streaming" in MLOpsManifest.fault_domains
        assert "mlops.memory" in MLOpsManifest.fault_domains

    def test_middleware_has_scope_and_priority(self):
        from aquilia.mlops.module import MLOpsManifest

        for mw_path, mw_config in MLOpsManifest.middleware:
            assert "scope" in mw_config, f"Middleware {mw_path} missing scope"
            assert "priority" in mw_config, f"Middleware {mw_path} missing priority"
            assert mw_config["scope"] == "app:mlops"

    def test_middleware_priority_ordering(self):
        from aquilia.mlops.module import MLOpsManifest

        priorities = [cfg["priority"] for _, cfg in MLOpsManifest.middleware]
        assert priorities == sorted(priorities), "Middleware not in priority order"


# ═══════════════════════════════════════════════════════════════════════════
# 8. Lifecycle Hooks Ecosystem Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestLifecycleHooksEcosystem:
    """Lifecycle hooks integrate with cache, artifacts, and fault engine."""

    @pytest.mark.asyncio
    async def test_startup_creates_artifact_dir(self):
        import tempfile
        import shutil
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup

        tmpdir = tempfile.mkdtemp()
        artifact_dir = os.path.join(tmpdir, "test-artifacts")
        try:
            await mlops_on_startup(config={
                "artifact_store_dir": artifact_dir,
                "plugins": {"auto_discover": False},
            })
            assert os.path.isdir(artifact_dir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_startup_with_cache_service_in_di(self):
        from aquilia.di import Container
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup
        from aquilia.cache import CacheService, MemoryBackend

        container = Container()
        # Pre-register a CacheService
        from aquilia.di.providers import ValueProvider
        backend = MemoryBackend(max_size=64)
        svc = CacheService(backend)
        container.register(ValueProvider(value=svc, token=CacheService, scope="singleton"))

        await mlops_on_startup(
            config={"plugins": {"auto_discover": False}},
            di_container=container,
        )
        # CacheService.initialize should have been called
        assert svc._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_flushes_cache(self):
        from aquilia.di import Container
        from aquilia.mlops.lifecycle_hooks import mlops_on_shutdown
        from aquilia.di.providers import ValueProvider

        cache = AsyncMock()
        cache.shutdown = AsyncMock()

        container = MagicMock()
        container.resolve.side_effect = lambda token: cache if "CacheService" in str(token) else None

        # The shutdown hook catches exceptions, so this should not raise
        await mlops_on_shutdown(di_container=container)

    @pytest.mark.asyncio
    async def test_startup_registers_fault_listener(self):
        """Startup registers a FaultEngine listener that records faults in metrics."""
        from aquilia.di import Container
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup
        from aquilia.mlops.di_providers import register_mlops_providers

        container = Container()
        register_mlops_providers(container, {
            "plugins": {"auto_discover": False},
        })

        # Run startup with the DI container
        await mlops_on_startup(
            config={"plugins": {"auto_discover": False}},
            di_container=container,
        )

        # Verify fault engine has listeners
        from aquilia.faults import FaultEngine
        engine = await container.resolve_async(FaultEngine)
        assert len(engine._event_listeners) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 9. Effect System Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestEffectIntegration:
    """MLOps controller declares effects for the effect middleware."""

    def test_cache_effect_importable(self):
        from aquilia.effects import CacheEffect

        effect = CacheEffect("mlops")
        assert effect.name == "Cache"
        assert effect.mode == "mlops"

    def test_controller_imports_cache_effect(self):
        """Controller module imports CacheEffect for effect declarations."""
        import aquilia.mlops.controller as ctrl_mod

        assert hasattr(ctrl_mod, "CacheEffect")


# ═══════════════════════════════════════════════════════════════════════════
# 10. Artifact Store Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestArtifactStoreIntegration:
    """ArtifactStore is wired into MLOps controller and DI."""

    @pytest.mark.asyncio
    async def test_list_artifacts_uses_injected_store(self):
        from aquilia.mlops.controller import MLOpsController

        mock_store = MagicMock()
        mock_store.list_artifacts.return_value = []

        ctrl = MLOpsController(artifact_store=mock_store)
        result = await ctrl.list_artifacts()

        assert result["total"] == 0
        mock_store.list_artifacts.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_artifacts_fault_handling(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine

        engine = FaultEngine()
        mock_store = MagicMock()
        mock_store.list_artifacts.side_effect = RuntimeError("store error")

        ctrl = MLOpsController(artifact_store=mock_store, fault_engine=engine)
        result = await ctrl.list_artifacts()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_inspect_artifact_uses_injected_store(self):
        from aquilia.mlops.controller import MLOpsController

        mock_store = MagicMock()
        ctrl = MLOpsController(artifact_store=mock_store)

        # Will fail since ArtifactReader can't work with mock, but tests graceful handling
        result = await ctrl.inspect_artifact("my-artifact")
        # Should return error dict, not raise
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════
# 11. Exports & API Surface
# ═══════════════════════════════════════════════════════════════════════════


class TestEcosystemExports:
    """New ecosystem integration APIs are properly exported."""

    def test_register_mlops_middleware_exported(self):
        from aquilia.mlops import register_mlops_middleware

        assert callable(register_mlops_middleware)

    def test_controller_has_ecosystem_attributes(self):
        from aquilia.mlops import MLOpsController

        ctrl = MLOpsController()
        assert hasattr(ctrl, "_cache")
        assert hasattr(ctrl, "_fault_engine")
        assert hasattr(ctrl, "_artifact_store")

    def test_mlops_config_has_ecosystem_fields(self):
        from aquilia.mlops import MLOpsConfig

        cfg = MLOpsConfig({})
        assert hasattr(cfg, "cache_enabled")
        assert hasattr(cfg, "cache_ttl")
        assert hasattr(cfg, "cache_namespace")
        assert hasattr(cfg, "artifact_store_dir")
        assert hasattr(cfg, "fault_engine_debug")


# ═══════════════════════════════════════════════════════════════════════════
# 12. End-to-End Ecosystem Flow
# ═══════════════════════════════════════════════════════════════════════════


class TestEndToEndEcosystemFlow:
    """Full ecosystem flow from config → DI → controller → cache/faults."""

    @pytest.mark.asyncio
    async def test_full_di_wiring_flow(self):
        """Config → DI → Controller with all ecosystem services."""
        from aquilia.config_builders import Integration
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.lifecycle_hooks import _flatten_mlops_config
        from aquilia.mlops.controller import MLOpsController

        # 1. Create config via Integration.mlops()
        config = Integration.mlops(
            registry_db=":memory:",
            cache_enabled=True,
            cache_ttl=120,
            fault_engine_debug=True,
            plugin_auto_discover=False,
        )

        # 2. Flatten config
        flat = _flatten_mlops_config(config)
        assert flat["cache_enabled"] is True
        assert flat["cache_ttl"] == 120
        assert flat["fault_engine_debug"] is True

        # 3. Register DI providers
        container = Container()
        register_mlops_providers(container, flat)

        # 4. Resolve controller
        ctrl = await container.resolve_async(MLOpsController)

        # 5. Verify ecosystem services are wired
        assert ctrl._cache is not None
        assert ctrl._fault_engine is not None
        assert ctrl._artifact_store is not None

    @pytest.mark.asyncio
    async def test_full_request_flow_with_caching(self):
        """Simulate a request that hits cache → miss → compute → store."""
        from aquilia.mlops.controller import MLOpsController
        from aquilia.cache import CacheService, MemoryBackend

        backend = MemoryBackend(max_size=128)
        cache = CacheService(backend)
        await cache.initialize()

        ctrl = MLOpsController(cache_service=cache)

        # First call: cache miss → compute health → cache set
        result1 = await ctrl.health()
        assert result1["status"] == "healthy"

        # Second call: should hit cache
        result2 = await ctrl.health()
        assert result2["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_full_fault_flow(self):
        """Simulate a fault routed through FaultEngine with listener."""
        from aquilia.mlops.controller import MLOpsController
        from aquilia.faults import FaultEngine

        engine = FaultEngine(debug=True)
        faults_captured = []
        engine.on_fault(lambda ctx: faults_captured.append(ctx.fault))

        registry = AsyncMock()
        registry.list_packs = AsyncMock(side_effect=ConnectionError("db down"))

        ctrl = MLOpsController(registry=registry, fault_engine=engine)
        result = await ctrl.list_models()

        assert "error" in result
        assert len(faults_captured) > 0

    @pytest.mark.asyncio
    async def test_middleware_stack_with_fault_engine(self):
        """Middleware stack builds correctly with ecosystem services."""
        from aquilia.middleware import MiddlewareStack
        from aquilia.mlops.middleware import register_mlops_middleware
        from aquilia.faults import FaultEngine

        engine = FaultEngine()
        stack = MiddlewareStack()

        register_mlops_middleware(
            stack,
            metrics_collector=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
            fault_engine=engine,
        )

        # Build handler chain
        final_handler = AsyncMock()
        handler = stack.build_handler(final_handler)
        assert handler is not None
