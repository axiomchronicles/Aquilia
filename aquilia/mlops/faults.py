"""
MLOps Fault Domain — Structured error handling for the entire ML pipeline.

Integrates with Aquilia's FaultEngine for unified error propagation,
recovery strategies, observability, and HTTP response mapping.

Fault Taxonomy::

    MLOpsFault (base)
    ├── PackFault
    │   ├── PackBuildFault
    │   ├── PackIntegrityFault
    │   └── PackSignatureFault
    ├── RegistryFault
    │   ├── RegistryConnectionFault
    │   ├── PackNotFoundFault
    │   └── ImmutabilityViolationFault
    ├── ServingFault
    │   ├── RuntimeLoadFault
    │   ├── InferenceFault
    │   ├── BatchTimeoutFault
    │   └── WarmupFault
    ├── ObserveFault
    │   ├── DriftDetectionFault
    │   └── MetricsExportFault
    ├── RolloutFault
    │   ├── RolloutAdvanceFault
    │   └── AutoRollbackFault
    ├── SchedulerFault
    │   ├── PlacementFault
    │   └── ScalingFault
    ├── SecurityFault
    │   ├── SigningFault
    │   ├── PermissionDeniedFault
    │   └── EncryptionFault
    └── PluginFault
        ├── PluginLoadFault
        └── PluginHookFault
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aquilia.faults.core import (
    Fault,
    FaultDomain,
    Severity,
    RecoveryStrategy,
)

# ── Register MLOps fault domain ──────────────────────────────────────────

FaultDomain.MLOPS = FaultDomain("mlops", "MLOps pipeline faults")
FaultDomain.MLOPS_PACK = FaultDomain("mlops.pack", "Model packaging faults")
FaultDomain.MLOPS_REGISTRY = FaultDomain("mlops.registry", "Model registry faults")
FaultDomain.MLOPS_SERVING = FaultDomain("mlops.serving", "Model serving faults")
FaultDomain.MLOPS_OBSERVE = FaultDomain("mlops.observe", "Observability faults")
FaultDomain.MLOPS_RELEASE = FaultDomain("mlops.release", "Release/rollout faults")
FaultDomain.MLOPS_SCHEDULER = FaultDomain("mlops.scheduler", "Scheduler faults")
FaultDomain.MLOPS_SECURITY = FaultDomain("mlops.security", "MLOps security faults")
FaultDomain.MLOPS_PLUGIN = FaultDomain("mlops.plugin", "Plugin lifecycle faults")


# ── Base ─────────────────────────────────────────────────────────────────

class MLOpsFault(Fault):
    """Base fault for all MLOps operations."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        domain: FaultDomain = FaultDomain.MLOPS,
        severity: Severity = Severity.ERROR,
        retryable: bool = False,
        public: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            domain=domain,
            severity=severity,
            retryable=retryable,
            public=public,
            metadata=metadata,
        )


# ── Pack Faults ──────────────────────────────────────────────────────────

class PackFault(MLOpsFault):
    """Base fault for model packaging."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_PACK)
        super().__init__(code=code, message=message, **kwargs)


class PackBuildFault(PackFault):
    """Model pack build failed."""

    def __init__(self, reason: str, model_name: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"model_name": model_name, "reason": reason, **extra_meta}
        super().__init__(
            code="PACK_BUILD_FAILED",
            message=f"Failed to build modelpack '{model_name}': {reason}",
            metadata=meta,
            **kwargs,
        )


class PackIntegrityFault(PackFault):
    """Blob integrity check failed (SHA-256 mismatch) or structural issue."""

    def __init__(self, reason: str, expected: str = "", actual: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"reason": reason, **extra_meta}
        if expected:
            meta["expected"] = expected
            meta["actual"] = actual
            msg = f"Integrity check failed: expected {expected[:16]}…, got {actual[:16]}…"
        else:
            msg = f"Integrity check failed: {reason}"
        super().__init__(
            code="PACK_INTEGRITY_FAILED",
            message=msg,
            severity=Severity.FATAL,
            metadata=meta,
            **kwargs,
        )


class PackSignatureFault(PackFault):
    """Artifact signature verification failed."""

    def __init__(self, archive_path: str, reason: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"archive_path": archive_path, "reason": reason, **extra_meta}
        super().__init__(
            code="PACK_SIGNATURE_INVALID",
            message=f"Signature verification failed for '{archive_path}': {reason}",
            severity=Severity.FATAL,
            metadata=meta,
            **kwargs,
        )


# ── Registry Faults ─────────────────────────────────────────────────────

class RegistryFault(MLOpsFault):
    """Base fault for registry operations."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_REGISTRY)
        super().__init__(code=code, message=message, **kwargs)


class RegistryConnectionFault(RegistryFault):
    """Cannot connect to registry backend."""

    def __init__(self, backend: str = "sqlite", reason: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"backend": backend, "reason": reason, **extra_meta}
        super().__init__(
            code="REGISTRY_CONNECTION_FAILED",
            message=f"Registry connection failed ({backend}): {reason}",
            retryable=True,
            metadata=meta,
            **kwargs,
        )


class PackNotFoundFault(RegistryFault):
    """Requested modelpack not found in registry."""

    def __init__(self, name: str, tag: str = "latest", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"name": name, "tag": tag, **extra_meta}
        super().__init__(
            code="PACK_NOT_FOUND",
            message=f"Modelpack '{name}:{tag}' not found in registry",
            severity=Severity.WARN,
            metadata=meta,
            **kwargs,
        )


class ImmutabilityViolationFault(RegistryFault):
    """Attempted to overwrite an immutable artifact."""

    def __init__(self, digest: str, **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"digest": digest, **extra_meta}
        super().__init__(
            code="IMMUTABILITY_VIOLATION",
            message=f"Cannot overwrite immutable artifact: {digest[:24]}…",
            severity=Severity.ERROR,
            metadata=meta,
            **kwargs,
        )


# ── Serving Faults ──────────────────────────────────────────────────────

class ServingFault(MLOpsFault):
    """Base fault for model serving."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_SERVING)
        super().__init__(code=code, message=message, **kwargs)


class RuntimeLoadFault(ServingFault):
    """Model failed to load into runtime."""

    def __init__(self, model_name: str, runtime: str = "", reason: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"model_name": model_name, "runtime": runtime, "reason": reason, **extra_meta}
        super().__init__(
            code="RUNTIME_LOAD_FAILED",
            message=f"Failed to load '{model_name}' into {runtime} runtime: {reason}",
            severity=Severity.FATAL,
            metadata=meta,
            **kwargs,
        )


class InferenceFault(ServingFault):
    """Inference failed for a request."""

    def __init__(self, request_id: str, reason: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"request_id": request_id, "reason": reason, **extra_meta}
        super().__init__(
            code="INFERENCE_FAILED",
            message=f"Inference failed for request {request_id}: {reason}",
            retryable=True,
            metadata=meta,
            **kwargs,
        )


class BatchTimeoutFault(ServingFault):
    """Batch processing exceeded deadline."""

    def __init__(self, batch_id: str, deadline_ms: float = 0, **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"batch_id": batch_id, "deadline_ms": deadline_ms, **extra_meta}
        super().__init__(
            code="BATCH_TIMEOUT",
            message=f"Batch {batch_id} exceeded deadline ({deadline_ms:.0f}ms)",
            retryable=True,
            severity=Severity.WARN,
            metadata=meta,
            **kwargs,
        )


class WarmupFault(ServingFault):
    """Model warm-up failed."""

    def __init__(self, model_name: str, reason: str = "", **kwargs: Any):
        extra_meta = kwargs.pop("metadata", {})
        meta = {"model_name": model_name, "reason": reason, **extra_meta}
        super().__init__(
            code="WARMUP_FAILED",
            message=f"Warm-up failed for '{model_name}': {reason}",
            severity=Severity.WARN,
            retryable=True,
            metadata=meta,
            **kwargs,
        )


# ── Observe Faults ──────────────────────────────────────────────────────

class ObserveFault(MLOpsFault):
    """Base fault for observability."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_OBSERVE)
        super().__init__(code=code, message=message, **kwargs)


class DriftDetectionFault(ObserveFault):
    """Drift detection computation failed."""

    def __init__(self, feature: str = "", reason: str = "", **kwargs: Any):
        super().__init__(
            code="DRIFT_DETECTION_FAILED",
            message=f"Drift detection failed for feature '{feature}': {reason}",
            severity=Severity.WARN,
            metadata={"feature": feature, "reason": reason},
            **kwargs,
        )


class MetricsExportFault(ObserveFault):
    """Metrics export/scrape failed."""

    def __init__(self, target: str = "prometheus", reason: str = "", **kwargs: Any):
        super().__init__(
            code="METRICS_EXPORT_FAILED",
            message=f"Metrics export to {target} failed: {reason}",
            retryable=True,
            severity=Severity.WARN,
            metadata={"target": target, "reason": reason},
            **kwargs,
        )


# ── Rollout Faults ──────────────────────────────────────────────────────

class RolloutFault(MLOpsFault):
    """Base fault for release management."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_RELEASE)
        super().__init__(code=code, message=message, **kwargs)


class RolloutAdvanceFault(RolloutFault):
    """Rollout advancement failed due to metric degradation."""

    def __init__(self, rollout_id: str, metric: str = "", value: float = 0, **kwargs: Any):
        super().__init__(
            code="ROLLOUT_ADVANCE_FAILED",
            message=f"Rollout {rollout_id} halted: {metric}={value:.4f} exceeded threshold",
            metadata={"rollout_id": rollout_id, "metric": metric, "value": value},
            **kwargs,
        )


class AutoRollbackFault(RolloutFault):
    """Automatic rollback triggered."""

    def __init__(self, rollout_id: str, reason: str = "", **kwargs: Any):
        super().__init__(
            code="AUTO_ROLLBACK",
            message=f"Auto-rollback triggered for {rollout_id}: {reason}",
            severity=Severity.WARN,
            metadata={"rollout_id": rollout_id, "reason": reason},
            **kwargs,
        )


# ── Scheduler Faults ────────────────────────────────────────────────────

class SchedulerFault(MLOpsFault):
    """Base fault for scheduling."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_SCHEDULER)
        super().__init__(code=code, message=message, **kwargs)


class PlacementFault(SchedulerFault):
    """No suitable node found for model placement."""

    def __init__(self, model_name: str, reason: str = "", **kwargs: Any):
        super().__init__(
            code="PLACEMENT_FAILED",
            message=f"No suitable node for '{model_name}': {reason}",
            retryable=True,
            metadata={"model_name": model_name, "reason": reason},
            **kwargs,
        )


class ScalingFault(SchedulerFault):
    """Scaling operation failed."""

    def __init__(self, deployment: str = "", reason: str = "", **kwargs: Any):
        super().__init__(
            code="SCALING_FAILED",
            message=f"Scaling failed for {deployment}: {reason}",
            retryable=True,
            metadata={"deployment": deployment, "reason": reason},
            **kwargs,
        )


# ── Security Faults ─────────────────────────────────────────────────────

class MLOpsSecurityFault(MLOpsFault):
    """Base fault for MLOps security."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_SECURITY)
        super().__init__(code=code, message=message, **kwargs)


class SigningFault(MLOpsSecurityFault):
    """Artifact signing failed."""

    def __init__(self, reason: str = "", **kwargs: Any):
        super().__init__(
            code="SIGNING_FAILED",
            message=f"Artifact signing failed: {reason}",
            metadata={"reason": reason},
            **kwargs,
        )


class PermissionDeniedFault(MLOpsSecurityFault):
    """User lacks required RBAC permission."""

    def __init__(self, user_id: str, permission: str, **kwargs: Any):
        super().__init__(
            code="PERMISSION_DENIED",
            message=f"User '{user_id}' lacks permission '{permission}'",
            severity=Severity.WARN,
            public=True,
            metadata={"user_id": user_id, "permission": permission},
            **kwargs,
        )


class EncryptionFault(MLOpsSecurityFault):
    """Encryption / decryption operation failed."""

    def __init__(self, operation: str = "encrypt", reason: str = "", **kwargs: Any):
        super().__init__(
            code="ENCRYPTION_FAILED",
            message=f"{operation.capitalize()} failed: {reason}",
            severity=Severity.FATAL,
            metadata={"operation": operation, "reason": reason},
            **kwargs,
        )


# ── Plugin Faults ───────────────────────────────────────────────────────

class PluginFault(MLOpsFault):
    """Base fault for plugin operations."""

    def __init__(self, code: str, message: str, **kwargs: Any):
        kwargs.setdefault("domain", FaultDomain.MLOPS_PLUGIN)
        super().__init__(code=code, message=message, **kwargs)


class PluginLoadFault(PluginFault):
    """Plugin failed to load."""

    def __init__(self, plugin_name: str, reason: str = "", **kwargs: Any):
        super().__init__(
            code="PLUGIN_LOAD_FAILED",
            message=f"Plugin '{plugin_name}' failed to load: {reason}",
            metadata={"plugin_name": plugin_name, "reason": reason},
            **kwargs,
        )


class PluginHookFault(PluginFault):
    """Plugin hook execution failed."""

    def __init__(self, plugin_name: str, hook: str, reason: str = "", **kwargs: Any):
        super().__init__(
            code="PLUGIN_HOOK_FAILED",
            message=f"Plugin '{plugin_name}' hook '{hook}' failed: {reason}",
            severity=Severity.WARN,
            retryable=True,
            metadata={"plugin_name": plugin_name, "hook": hook, "reason": reason},
            **kwargs,
        )
