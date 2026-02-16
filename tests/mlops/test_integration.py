"""
Tests for MLOps deep integration with Aquilia internals.

Covers:
- Fault domain integration
- Serializer integration
- DI provider registration
- Config builder integration (Integration.mlops, Workspace.mlops)
- Controller integration
- Middleware integration
- Lifecycle hooks integration
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Fault Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsFaults:
    """Test MLOps fault domain integration with Aquilia FaultEngine."""

    def test_mlops_fault_domain_registered(self):
        # Import faults first to trigger domain registration
        from aquilia.mlops.faults import MLOpsFault  # noqa: F401
        from aquilia.faults.core import FaultDomain

        assert hasattr(FaultDomain, "MLOPS")
        assert FaultDomain.MLOPS.name == "mlops"

    def test_mlops_sub_domains_registered(self):
        from aquilia.mlops.faults import MLOpsFault  # noqa: F401
        from aquilia.faults.core import FaultDomain

        for sub in ("PACK", "REGISTRY", "SERVING", "OBSERVE", "RELEASE",
                     "SCHEDULER", "SECURITY", "PLUGIN"):
            attr = f"MLOPS_{sub}"
            assert hasattr(FaultDomain, attr), f"Missing FaultDomain.{attr}"

    def test_mlops_fault_base(self):
        from aquilia.mlops.faults import MLOpsFault
        from aquilia.faults.core import FaultDomain, Severity

        fault = MLOpsFault(
            code="MLOPS_TEST",
            message="test fault",
            severity=Severity.WARN,
            metadata={"key": "value"},
        )
        assert fault.code == "MLOPS_TEST"
        assert fault.message == "test fault"
        assert fault.domain == FaultDomain.MLOPS
        assert fault.severity == Severity.WARN
        assert fault.metadata == {"key": "value"}
        assert isinstance(fault, Exception)

    def test_pack_build_fault(self):
        from aquilia.mlops.faults import PackBuildFault
        from aquilia.faults.core import FaultDomain

        f = PackBuildFault("No model files added")
        assert f.domain == FaultDomain.MLOPS_PACK
        assert "PACK_BUILD" in f.code

    def test_registry_faults(self):
        from aquilia.mlops.faults import (
            RegistryConnectionFault,
            PackNotFoundFault,
            ImmutabilityViolationFault,
        )

        f1 = RegistryConnectionFault("DB not ready")
        assert f1.retryable is True  # connection faults are retryable

        f2 = PackNotFoundFault("my-model:v1")
        assert "NOT_FOUND" in f2.code

        f3 = ImmutabilityViolationFault("sha256:abc already exists")
        assert f3.retryable is False

    def test_serving_faults(self):
        from aquilia.mlops.faults import InferenceFault, BatchTimeoutFault

        f1 = InferenceFault("prediction failed")
        assert "INFERENCE" in f1.code

        f2 = BatchTimeoutFault("batch deadline exceeded")
        assert f2.retryable is True

    def test_security_faults(self):
        from aquilia.mlops.faults import (
            SigningFault, PermissionDeniedFault, EncryptionFault,
        )
        from aquilia.faults.core import FaultDomain

        f = PermissionDeniedFault("user-1", "pack:write")
        assert f.domain == FaultDomain.MLOPS_SECURITY

    def test_plugin_faults(self):
        from aquilia.mlops.faults import PluginLoadFault, PluginHookFault
        from aquilia.faults.core import FaultDomain

        f = PluginLoadFault("my-plugin", "bad module path")
        assert f.domain == FaultDomain.MLOPS_PLUGIN

    def test_fault_inheritance_chain(self):
        from aquilia.mlops.faults import PackBuildFault, MLOpsFault
        from aquilia.faults.core import Fault

        f = PackBuildFault("test")
        assert isinstance(f, MLOpsFault)
        assert isinstance(f, Fault)
        assert isinstance(f, Exception)


# ═══════════════════════════════════════════════════════════════════════════
# Serializer Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsSerializers:
    """Test MLOps serializers using Aquilia serializer framework."""

    def test_tensor_spec_serializer(self):
        from aquilia.mlops.serializers import TensorSpecSerializer

        ser = TensorSpecSerializer(data={
            "name": "input",
            "dtype": "float32",
            "shape": [-1, 64],
        })
        assert ser.is_valid()
        assert ser.validated_data["name"] == "input"
        assert ser.validated_data["dtype"] == "float32"

    def test_tensor_spec_serializer_invalid(self):
        from aquilia.mlops.serializers import TensorSpecSerializer

        ser = TensorSpecSerializer(data={"name": "", "dtype": ""})
        # CharField with min_length constraint makes empty string invalid
        assert not ser.is_valid()

    def test_blob_ref_serializer(self):
        from aquilia.mlops.serializers import BlobRefSerializer

        ser = BlobRefSerializer(data={
            "path": "model.pt",
            "digest": "sha256:abc123",
            "size": 1024,
        })
        assert ser.is_valid()

    def test_modelpack_manifest_serializer(self):
        from aquilia.mlops.serializers import ModelpackManifestSerializer

        data = {
            "name": "my-model",
            "version": "v1.0.0",
            "framework": "pytorch",
            "entrypoint": "model.pt",
        }
        ser = ModelpackManifestSerializer(data=data)
        assert ser.is_valid()
        assert ser.validated_data["name"] == "my-model"

    def test_inference_request_serializer(self):
        from aquilia.mlops.serializers import InferenceRequestSerializer

        ser = InferenceRequestSerializer(data={
            "request_id": "req-001",
            "inputs": {"features": [1.0, 2.0]},
        })
        assert ser.is_valid()

    def test_inference_result_serializer(self):
        from aquilia.mlops.serializers import InferenceResultSerializer

        ser = InferenceResultSerializer(data={
            "request_id": "req-001",
            "outputs": {"prediction": 0.95},
            "latency_ms": 12.5,
        })
        assert ser.is_valid()

    def test_drift_report_serializer(self):
        from aquilia.mlops.serializers import DriftReportSerializer

        ser = DriftReportSerializer(data={
            "method": "psi",
            "score": 0.15,
            "threshold": 0.2,
            "is_drifted": False,
        })
        assert ser.is_valid()

    def test_rollout_config_serializer(self):
        from aquilia.mlops.serializers import RolloutConfigSerializer

        ser = RolloutConfigSerializer(data={
            "from_version": "v1",
            "to_version": "v2",
            "strategy": "canary",
            "percentage": 10,
            "auto_rollback": True,
        })
        assert ser.is_valid()

    def test_scaling_policy_serializer(self):
        from aquilia.mlops.serializers import ScalingPolicySerializer

        ser = ScalingPolicySerializer(data={
            "min_replicas": 1,
            "max_replicas": 10,
            "target_concurrency": 15.0,
        })
        assert ser.is_valid()

    def test_plugin_descriptor_serializer(self):
        from aquilia.mlops.serializers import PluginDescriptorSerializer

        ser = PluginDescriptorSerializer(data={
            "name": "my-plugin",
            "version": "1.0.0",
            "module": "my_plugin.main",
            "state": "activated",
        })
        assert ser.is_valid()

    def test_metrics_summary_serializer(self):
        from aquilia.mlops.serializers import MetricsSummarySerializer

        ser = MetricsSummarySerializer(data={
            "model_name": "test-model",
            "model_version": "v1",
            "counters": {"requests": 100},
            "gauges": {"memory": 512.0},
        })
        assert ser.is_valid()


# ═══════════════════════════════════════════════════════════════════════════
# DI Provider Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsDIProviders:
    """Test MLOps DI provider registration."""

    def test_mlops_config_defaults(self):
        from aquilia.mlops.di_providers import MLOpsConfig

        cfg = MLOpsConfig()
        assert cfg.enabled is True
        assert cfg.registry_db == "registry.db"
        assert cfg.blob_root == ".aquilia-store"
        assert cfg.drift_method == "psi"
        assert cfg.drift_threshold == 0.2
        assert cfg.max_batch_size == 16
        assert cfg.sample_rate == 0.01
        assert cfg.plugin_auto_discover is True

    def test_mlops_config_from_dict(self):
        from aquilia.mlops.di_providers import MLOpsConfig

        cfg = MLOpsConfig({
            "registry_db": "custom.db",
            "drift_method": "ks_test",
            "max_batch_size": 32,
            "metrics_model_name": "my-model",
        })
        assert cfg.registry_db == "custom.db"
        assert cfg.drift_method == "ks_test"
        assert cfg.max_batch_size == 32
        assert cfg.metrics_model_name == "my-model"

    def test_mlops_config_slots(self):
        from aquilia.mlops.di_providers import MLOpsConfig

        cfg = MLOpsConfig()
        assert hasattr(cfg, "__slots__")
        with pytest.raises(AttributeError):
            cfg.nonexistent_attr = "should fail"

    def test_register_mlops_providers(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers, MLOpsConfig

        container = Container()
        register_mlops_providers(container, {"drift_method": "psi"})

        # Verify services were registered
        cfg = container.resolve(MLOpsConfig)
        assert cfg is not None
        assert isinstance(cfg, MLOpsConfig)
        assert cfg.drift_method == "psi"

    def test_register_metrics_collector(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.observe.metrics import MetricsCollector

        container = Container()
        register_mlops_providers(container, {
            "metrics_model_name": "test-model",
            "metrics_model_version": "v1",
        })

        collector = container.resolve(MetricsCollector)
        assert collector is not None
        assert collector.model_name == "test-model"

    def test_register_drift_detector(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.observe.drift import DriftDetector

        container = Container()
        register_mlops_providers(container, {
            "drift_method": "ks_test",
            "drift_threshold": 0.3,
        })

        detector = container.resolve(DriftDetector)
        assert detector is not None
        assert detector.threshold == 0.3

    def test_register_registry_service(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.registry.service import RegistryService

        container = Container()
        register_mlops_providers(container, {
            "registry_db": ":memory:",
            "blob_root": "/tmp/test-blobs",
        })

        registry = container.resolve(RegistryService)
        assert registry is not None

    def test_register_plugin_host(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.plugins.host import PluginHost

        container = Container()
        register_mlops_providers(container, {"plugin_auto_discover": False})

        host = container.resolve(PluginHost)
        assert host is not None

    def test_register_rollout_engine(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.release.rollout import RolloutEngine

        container = Container()
        register_mlops_providers(container)

        engine = container.resolve(RolloutEngine)
        assert engine is not None

    def test_register_autoscaler(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.scheduler.autoscaler import Autoscaler

        container = Container()
        register_mlops_providers(container)

        scaler = container.resolve(Autoscaler)
        assert scaler is not None

    def test_register_rbac(self):
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers
        from aquilia.mlops.security.rbac import RBACManager

        container = Container()
        register_mlops_providers(container)

        rbac = container.resolve(RBACManager)
        assert rbac is not None

    def test_register_all_providers_count(self):
        """14 providers should be registered."""
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers, MLOpsConfig
        from aquilia.mlops.observe.metrics import MetricsCollector
        from aquilia.mlops.observe.drift import DriftDetector
        from aquilia.mlops.observe.logger import PredictionLogger
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops.plugins.host import PluginHost
        from aquilia.mlops.serving.router import TrafficRouter
        from aquilia.mlops.release.rollout import RolloutEngine
        from aquilia.mlops.scheduler.autoscaler import Autoscaler
        from aquilia.mlops.scheduler.placement import PlacementScheduler
        from aquilia.mlops.security.rbac import RBACManager
        from aquilia.mlops.security.signing import ArtifactSigner, EncryptionManager
        from aquilia.mlops.security.encryption import BlobEncryptor

        container = Container()
        register_mlops_providers(container)

        services = [
            MLOpsConfig, MetricsCollector, DriftDetector, PredictionLogger,
            RegistryService, PluginHost, TrafficRouter, RolloutEngine,
            Autoscaler, PlacementScheduler, RBACManager, ArtifactSigner,
            EncryptionManager, BlobEncryptor,
        ]
        for svc in services:
            assert container.resolve(svc) is not None, f"Missing: {svc.__name__}"


# ═══════════════════════════════════════════════════════════════════════════
# Config Builder Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsConfigIntegration:
    """Test Integration.mlops() and Workspace.mlops() config builders."""

    def test_integration_mlops_defaults(self):
        from aquilia.config_builders import Integration

        cfg = Integration.mlops()
        assert cfg["_integration_type"] == "mlops"
        assert cfg["enabled"] is True
        assert cfg["registry"]["db_path"] == "registry.db"
        assert cfg["registry"]["blob_root"] == ".aquilia-store"
        assert cfg["serving"]["max_batch_size"] == 16
        assert cfg["observe"]["drift_method"] == "psi"
        assert cfg["release"]["auto_rollback"] is True
        assert cfg["plugins"]["auto_discover"] is True

    def test_integration_mlops_custom(self):
        from aquilia.config_builders import Integration

        cfg = Integration.mlops(
            registry_db="custom.db",
            blob_root="/data/blobs",
            drift_method="ks_test",
            drift_threshold=0.3,
            max_batch_size=64,
            hmac_secret="my-secret",
            plugin_auto_discover=False,
        )
        assert cfg["registry"]["db_path"] == "custom.db"
        assert cfg["registry"]["blob_root"] == "/data/blobs"
        assert cfg["observe"]["drift_method"] == "ks_test"
        assert cfg["observe"]["drift_threshold"] == 0.3
        assert cfg["serving"]["max_batch_size"] == 64
        assert cfg["security"]["hmac_secret"] == "my-secret"
        assert cfg["plugins"]["auto_discover"] is False

    def test_workspace_mlops(self):
        from aquilia.config_builders import Workspace

        ws = (
            Workspace("ml-app", version="1.0.0")
            .mlops(
                registry_db="models.db",
                drift_method="psi",
                max_batch_size=32,
            )
        )
        d = ws.to_dict()

        assert "mlops" in d
        assert d["mlops"]["registry"]["db_path"] == "models.db"
        assert d["mlops"]["serving"]["max_batch_size"] == 32
        assert d["mlops"]["observe"]["drift_method"] == "psi"

    def test_workspace_integrate_mlops(self):
        from aquilia.config_builders import Workspace, Integration

        ws = (
            Workspace("ml-app")
            .integrate(Integration.mlops(registry_db="reg.db"))
        )
        d = ws.to_dict()

        assert "mlops" in d["integrations"]
        assert d["integrations"]["mlops"]["registry"]["db_path"] == "reg.db"
        assert "mlops" in d  # Also at top level
        assert d["mlops"]["registry"]["db_path"] == "reg.db"

    def test_workspace_mlops_with_other_integrations(self):
        from aquilia.config_builders import Workspace, Integration

        ws = (
            Workspace("ml-app")
            .runtime(mode="prod", port=8000)
            .integrate(Integration.mlops(drift_threshold=0.25))
            .integrate(Integration.cors(allow_origins=["*"]))
            .database(url="sqlite:///app.db")
        )
        d = ws.to_dict()

        # MLOps config
        assert d["mlops"]["observe"]["drift_threshold"] == 0.25
        # CORS still works
        assert d["integrations"]["cors"]["allow_origins"] == ["*"]
        # Database still works
        assert d["database"]["url"] == "sqlite:///app.db"
        # Runtime
        assert d["runtime"]["mode"] == "prod"

    def test_integration_mlops_kwargs_passthrough(self):
        from aquilia.config_builders import Integration

        cfg = Integration.mlops(custom_field="custom_value")
        assert cfg["custom_field"] == "custom_value"


# ═══════════════════════════════════════════════════════════════════════════
# Controller Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsController:
    """Test MLOps HTTP controller."""

    async def test_health_no_components(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.health()
        assert result["status"] == "healthy"
        assert "timestamp" in result

    async def test_health_with_registry(self):
        from aquilia.mlops.controller import MLOpsController

        mock_registry = MagicMock()
        mock_registry._initialized = True

        ctrl = MLOpsController(registry=mock_registry)
        result = await ctrl.health()
        assert result["components"]["registry"]["status"] == "up"
        assert result["components"]["registry"]["initialized"] is True

    async def test_health_with_serving(self):
        from aquilia.mlops.controller import MLOpsController

        mock_server = AsyncMock()
        mock_server.health.return_value = {
            "status": "serving",
            "model": "test",
        }

        ctrl = MLOpsController(serving_server=mock_server)
        result = await ctrl.health()
        assert result["components"]["serving"]["status"] == "serving"

    async def test_predict(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._types import InferenceResult

        mock_server = AsyncMock()
        mock_server.predict.return_value = InferenceResult(
            request_id="req-001",
            outputs={"pred": 0.95},
            latency_ms=5.0,
        )

        ctrl = MLOpsController(serving_server=mock_server)
        result = await ctrl.predict({
            "inputs": {"x": [1.0, 2.0]},
        })
        assert result["request_id"] == "req-001"
        assert result["outputs"]["pred"] == 0.95
        assert result["latency_ms"] == 5.0

    async def test_predict_no_server(self):
        from aquilia.mlops.controller import MLOpsController

        ctrl = MLOpsController()
        result = await ctrl.predict({"inputs": {}})
        assert result["status"] == 503

    async def test_metrics_json(self):
        from aquilia.mlops.controller import MLOpsController

        mock_metrics = MagicMock()
        mock_metrics.get_summary.return_value = {
            "aquilia_inference_total": 100,
        }

        ctrl = MLOpsController(metrics_collector=mock_metrics)
        result = await ctrl.metrics(fmt="json")
        assert result["aquilia_inference_total"] == 100

    async def test_metrics_prometheus(self):
        from aquilia.mlops.controller import MLOpsController

        mock_metrics = MagicMock()
        mock_metrics.to_prometheus.return_value = "# TYPE counter\n"

        ctrl = MLOpsController(metrics_collector=mock_metrics)
        result = await ctrl.metrics(fmt="prometheus")
        assert "TYPE" in result

    async def test_list_models(self):
        from aquilia.mlops.controller import MLOpsController

        mock_registry = AsyncMock()
        mock_registry.list_packs.return_value = [
            {"name": "model-a", "tag": "v1"},
        ]

        ctrl = MLOpsController(registry=mock_registry)
        result = await ctrl.list_models()
        assert result["count"] == 1
        assert result["models"][0]["name"] == "model-a"

    async def test_drift_status(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops._types import DriftMethod

        mock_drift = MagicMock()
        mock_drift.method = DriftMethod.PSI
        mock_drift.threshold = 0.2
        mock_drift._reference = {"feature_1": [1.0, 2.0]}

        ctrl = MLOpsController(drift_detector=mock_drift)
        result = await ctrl.drift_status()
        assert result["method"] == "psi"
        assert result["reference_set"] is True

    async def test_list_plugins(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops.plugins.host import PluginDescriptor, PluginState

        mock_host = MagicMock()
        mock_host.list_plugins.return_value = [
            PluginDescriptor(
                name="test-plugin",
                version="1.0",
                module="test_mod",
                state=PluginState.ACTIVATED,
            ),
        ]

        ctrl = MLOpsController(plugin_host=mock_host)
        result = await ctrl.list_plugins()
        assert len(result["plugins"]) == 1
        assert result["plugins"][0]["name"] == "test-plugin"
        assert result["plugins"][0]["state"] == "activated"

    async def test_start_rollout(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops.release.rollout import RolloutState, RolloutPhase
        from aquilia.mlops._types import RolloutConfig, RolloutStrategy

        mock_rollout = AsyncMock()
        mock_rollout.start.return_value = RolloutState(
            id="rollout-1",
            config=RolloutConfig(from_version="v1", to_version="v2"),
            phase=RolloutPhase.IN_PROGRESS,
            current_percentage=10,
        )

        ctrl = MLOpsController(rollout_engine=mock_rollout)
        result = await ctrl.start_rollout({
            "from_version": "v1",
            "to_version": "v2",
            "percentage": 10,
        })
        assert result["rollout_id"] == "rollout-1"
        assert result["phase"] == "in_progress"

    async def test_list_rollouts(self):
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops.release.rollout import RolloutState, RolloutPhase
        from aquilia.mlops._types import RolloutConfig

        mock_rollout = MagicMock()
        mock_rollout.list_rollouts.return_value = [
            RolloutState(
                id="r-1",
                config=RolloutConfig(from_version="v1", to_version="v2"),
                phase=RolloutPhase.COMPLETED,
                current_percentage=100,
            ),
        ]

        ctrl = MLOpsController(rollout_engine=mock_rollout)
        result = await ctrl.list_rollouts()
        assert len(result["rollouts"]) == 1
        assert result["rollouts"][0]["phase"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════
# Middleware Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsMiddleware:
    """Test MLOps metrics middleware."""

    async def test_metrics_middleware_instruments_mlops_paths(self):
        from aquilia.mlops.middleware import mlops_metrics_middleware
        from aquilia.mlops.observe.metrics import MetricsCollector

        collector = MetricsCollector(model_name="test")
        mw = mlops_metrics_middleware(collector)

        # Mock request and handler
        request = MagicMock()
        request.path = "/mlops/predict"
        ctx = MagicMock()

        response = MagicMock()
        response.status_code = 200

        async def handler(req, c):
            return response

        result = await mw(request, ctx, handler)
        assert result == response
        assert collector._counters["aquilia_inference_total"].value == 1

    async def test_metrics_middleware_skips_non_mlops_paths(self):
        from aquilia.mlops.middleware import mlops_metrics_middleware
        from aquilia.mlops.observe.metrics import MetricsCollector

        collector = MetricsCollector()
        mw = mlops_metrics_middleware(collector)

        request = MagicMock()
        request.path = "/api/users"
        ctx = MagicMock()

        async def handler(req, c):
            return MagicMock(status_code=200)

        await mw(request, ctx, handler)
        # No metrics recorded for non-MLOps paths
        c = collector._counters.get("aquilia_inference_total")
        assert c is None or c.value == 0

    async def test_metrics_middleware_records_errors(self):
        from aquilia.mlops.middleware import mlops_metrics_middleware
        from aquilia.mlops.observe.metrics import MetricsCollector

        collector = MetricsCollector()
        mw = mlops_metrics_middleware(collector)

        request = MagicMock()
        request.path = "/mlops/predict"
        ctx = MagicMock()

        async def handler(req, c):
            raise RuntimeError("inference failed")

        with pytest.raises(RuntimeError):
            await mw(request, ctx, handler)

        assert collector._counters["aquilia_inference_total"].value == 1
        assert collector._counters["aquilia_inference_errors_total"].value == 1

    async def test_request_id_middleware(self):
        from aquilia.mlops.middleware import mlops_request_id_middleware

        mw = mlops_request_id_middleware()

        request = MagicMock()
        ctx = MagicMock(spec=["__setattr__", "mlops_request_id"])
        ctx.mlops_request_id = None

        async def handler(req, c):
            return MagicMock()

        await mw(request, ctx, handler)
        # request_id was set (UUID format)
        assert ctx.mlops_request_id is not None

    async def test_request_id_middleware_dict_ctx(self):
        from aquilia.mlops.middleware import mlops_request_id_middleware

        mw = mlops_request_id_middleware()
        request = MagicMock()
        ctx = {}

        async def handler(req, c):
            return MagicMock()

        await mw(request, ctx, handler)
        assert "mlops_request_id" in ctx
        assert len(ctx["mlops_request_id"]) == 36  # UUID length


# ═══════════════════════════════════════════════════════════════════════════
# Lifecycle Hooks Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsLifecycleHooks:
    """Test MLOps lifecycle startup/shutdown hooks."""

    async def test_startup_hook_basic(self):
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup

        # Should not raise even with no config
        await mlops_on_startup()

    async def test_startup_hook_with_config(self):
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup

        config = {
            "registry": {"db_path": ":memory:"},
            "plugins": {"auto_discover": False},
        }
        await mlops_on_startup(config=config)

    async def test_startup_hook_registers_di(self):
        from aquilia.di import Container
        from aquilia.mlops.lifecycle_hooks import mlops_on_startup
        from aquilia.mlops.di_providers import MLOpsConfig

        container = Container()
        config = {
            "registry": {"db_path": ":memory:"},
            "observe": {"drift_method": "psi"},
            "plugins": {"auto_discover": False},
        }
        await mlops_on_startup(config=config, di_container=container)

        # DI providers should be registered
        cfg = await container.resolve_async(MLOpsConfig)
        assert cfg is not None

    async def test_shutdown_hook_basic(self):
        from aquilia.mlops.lifecycle_hooks import mlops_on_shutdown

        # Should not raise even with no args
        await mlops_on_shutdown()

    async def test_shutdown_hook_with_container(self):
        from aquilia.mlops.lifecycle_hooks import mlops_on_shutdown

        # Mock container that doesn't have our services
        container = MagicMock()
        container.resolve.side_effect = KeyError("not found")

        await mlops_on_shutdown(di_container=container)

    def test_flatten_config(self):
        from aquilia.mlops.lifecycle_hooks import _flatten_mlops_config

        cfg = {
            "enabled": True,
            "registry": {"db_path": "custom.db", "blob_root": "/blobs"},
            "serving": {"max_batch_size": 32},
            "observe": {"drift_method": "ks_test", "drift_threshold": 0.3},
            "security": {"hmac_secret": "secret"},
            "plugins": {"auto_discover": False},
        }
        flat = _flatten_mlops_config(cfg)

        assert flat["registry_db"] == "custom.db"
        assert flat["blob_root"] == "/blobs"
        assert flat["max_batch_size"] == 32
        assert flat["drift_method"] == "ks_test"
        assert flat["drift_threshold"] == 0.3
        assert flat["hmac_secret"] == "secret"
        assert flat["plugin_auto_discover"] is False


# ═══════════════════════════════════════════════════════════════════════════
# Fault Wiring Tests (pack builder, registry, serving)
# ═══════════════════════════════════════════════════════════════════════════


class TestFaultWiring:
    """Test that existing modules raise faults instead of bare exceptions."""

    async def test_pack_builder_raises_pack_build_fault(self):
        from aquilia.mlops.pack.builder import ModelpackBuilder
        from aquilia.mlops.faults import PackBuildFault

        builder = ModelpackBuilder(name="test", version="v1")
        # No model files added
        with pytest.raises(PackBuildFault, match="No model files"):
            await builder.save("/tmp")

    async def test_pack_builder_raises_build_fault_file_not_found(self, tmp_path):
        from aquilia.mlops.pack.builder import ModelpackBuilder
        from aquilia.mlops.faults import PackBuildFault

        builder = ModelpackBuilder(name="test", version="v1")
        builder.add_model("/nonexistent/model.pt")

        with pytest.raises(PackBuildFault, match="Model file not found"):
            await builder.save(str(tmp_path))

    async def test_registry_raises_connection_fault(self):
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops.faults import RegistryConnectionFault

        svc = RegistryService()
        with pytest.raises(RegistryConnectionFault, match="not initialized"):
            await svc.fetch("model", "v1")

    async def test_registry_raises_not_found_fault(self, tmp_path):
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops.faults import PackNotFoundFault

        svc = RegistryService(db_path=str(tmp_path / "test.db"))
        await svc.initialize()

        with pytest.raises(PackNotFoundFault, match="not found"):
            await svc.fetch("nonexistent", "v1")

        await svc.close()

    def test_drift_raises_fault(self):
        from aquilia.mlops.observe.drift import DriftDetector
        from aquilia.mlops.faults import DriftDetectionFault

        detector = DriftDetector()
        with pytest.raises(DriftDetectionFault, match="Reference distribution"):
            detector.detect({"f1": [1.0, 2.0]})


# ═══════════════════════════════════════════════════════════════════════════
# Export / Import Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsExports:
    """Test that all new modules are properly exported from __init__."""

    def test_fault_exports(self):
        from aquilia.mlops import (
            MLOpsFault, PackBuildFault, PackIntegrityFault,
            RegistryConnectionFault, PackNotFoundFault,
            InferenceFault, BatchTimeoutFault,
            DriftDetectionFault, MetricsExportFault,
            RolloutAdvanceFault, AutoRollbackFault,
            PlacementFault, ScalingFault,
            SigningFault, PermissionDeniedFault, EncryptionFault,
            PluginLoadFault, PluginHookFault,
        )
        assert MLOpsFault is not None

    def test_di_exports(self):
        from aquilia.mlops import register_mlops_providers, MLOpsConfig

        assert callable(register_mlops_providers)
        assert MLOpsConfig is not None

    def test_controller_exports(self):
        from aquilia.mlops import MLOpsController

        assert MLOpsController is not None

    def test_middleware_exports(self):
        from aquilia.mlops import mlops_metrics_middleware, mlops_request_id_middleware

        assert callable(mlops_metrics_middleware)
        assert callable(mlops_request_id_middleware)

    def test_lifecycle_exports(self):
        from aquilia.mlops import mlops_on_startup, mlops_on_shutdown

        assert callable(mlops_on_startup)
        assert callable(mlops_on_shutdown)

    def test_all_exports_listed(self):
        import aquilia.mlops as mlops_mod

        for name in mlops_mod.__all__:
            assert hasattr(mlops_mod, name), f"__all__ lists '{name}' but it's not exported"


# ═══════════════════════════════════════════════════════════════════════════
# End-to-End Integration Test
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsEndToEnd:
    """End-to-end integration: config → DI → controller → middleware."""

    async def test_full_integration_flow(self, tmp_path):
        """Wire entire MLOps stack: config → DI → controller."""
        from aquilia.config_builders import Integration
        from aquilia.di import Container
        from aquilia.mlops.di_providers import register_mlops_providers, MLOpsConfig
        from aquilia.mlops.controller import MLOpsController
        from aquilia.mlops.lifecycle_hooks import _flatten_mlops_config

        # 1. Build config
        config = Integration.mlops(
            registry_db=str(tmp_path / "test.db"),
            blob_root=str(tmp_path / "blobs"),
            drift_method="psi",
            metrics_model_name="e2e-test",
            plugin_auto_discover=False,
        )

        # 2. Register DI providers
        container = Container()
        flat = _flatten_mlops_config(config)
        register_mlops_providers(container, flat)

        # 3. Resolve services
        cfg = await container.resolve_async(MLOpsConfig)
        assert cfg.metrics_model_name == "e2e-test"

        from aquilia.mlops.observe.metrics import MetricsCollector
        from aquilia.mlops.observe.drift import DriftDetector
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops.plugins.host import PluginHost
        from aquilia.mlops.release.rollout import RolloutEngine

        collector = await container.resolve_async(MetricsCollector)
        detector = await container.resolve_async(DriftDetector)
        registry = await container.resolve_async(RegistryService)
        host = await container.resolve_async(PluginHost)
        engine = await container.resolve_async(RolloutEngine)

        # 4. Wire controller with DI-resolved services
        ctrl = MLOpsController(
            registry=registry,
            metrics_collector=collector,
            drift_detector=detector,
            plugin_host=host,
            rollout_engine=engine,
        )

        # 5. Test controller endpoints
        health = await ctrl.health()
        assert health["status"] == "healthy"
        assert "registry" in health["components"]

        drift = await ctrl.drift_status()
        assert drift["method"] == "psi"

        plugins = await ctrl.list_plugins()
        assert "plugins" in plugins
