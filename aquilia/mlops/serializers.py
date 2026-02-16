"""
MLOps Serializers — Aquilia DRF-style serializers for all MLOps data types.

Uses ``aquilia.serializers`` for declarative validation, coercion,
and output rendering across the entire ML pipeline.

Serializers::

    ModelpackManifestSerializer  — validate / render manifest JSON
    InferenceRequestSerializer   — validate incoming inference payloads
    InferenceResultSerializer    — render inference results
    DriftReportSerializer        — render drift detection reports
    RolloutConfigSerializer      — validate rollout configuration
    RolloutStateSerializer       — render rollout state
    ScalingPolicySerializer      — validate autoscaler policy
    PluginDescriptorSerializer   — render plugin metadata
    NodeInfoSerializer           — validate node registration
    PlacementRequestSerializer   — validate placement requests
    ProvenanceSerializer         — validate provenance metadata
"""

from __future__ import annotations

from aquilia.serializers import (
    Serializer,
    ListSerializer,
)
from aquilia.serializers.fields import (
    CharField,
    IntegerField,
    FloatField,
    BooleanField,
    ListField,
    DictField,
    ChoiceField,
    DateTimeField,
    JSONField,
    ReadOnlyField,
    SerializerField,
)
from aquilia.serializers.validators import (
    MinValueValidator,
    MaxValueValidator,
    RangeValidator,
    RegexValidator,
)

from ._types import (
    Framework,
    RuntimeKind,
    BatchingStrategy,
    RolloutStrategy,
    DriftMethod,
    QuantizePreset,
)


# ── TensorSpec ───────────────────────────────────────────────────────────

class TensorSpecSerializer(Serializer):
    """Validates and renders tensor specifications."""
    name = CharField(max_length=128)
    dtype = CharField(max_length=32)
    shape = ListField(required=True)


# ── BlobRef ──────────────────────────────────────────────────────────────

class BlobRefSerializer(Serializer):
    """Validates blob references."""
    path = CharField(max_length=512)
    digest = CharField(max_length=128)
    size = IntegerField(min_value=0)


# ── Provenance ───────────────────────────────────────────────────────────

class ProvenanceSerializer(Serializer):
    """Validates provenance metadata."""
    git_sha = CharField(max_length=64, required=False, default="")
    dataset_snapshot = CharField(max_length=256, required=False, default="")
    dockerfile = CharField(max_length=256, required=False, default="")
    build_timestamp = CharField(max_length=64, required=False, default="")


# ── ModelpackManifest ────────────────────────────────────────────────────

class ModelpackManifestSerializer(Serializer):
    """
    Full manifest serializer with deep validation.

    Usage::

        s = ModelpackManifestSerializer(data=manifest_dict)
        if s.is_valid():
            manifest = s.validated_data
        else:
            raise PackBuildFault(str(s.errors))
    """
    name = CharField(max_length=256)
    version = CharField(max_length=64)
    framework = ChoiceField(
        choices=[f.value for f in Framework],
        required=False,
        default="custom",
    )
    entrypoint = CharField(max_length=256, required=False, default="")
    env_lock = CharField(max_length=128, required=False, default="env.lock")
    created_at = CharField(required=False, default="")
    signed_by = CharField(max_length=256, required=False, default="")
    metadata = DictField(required=False, default=dict)


# ── InferenceRequest ─────────────────────────────────────────────────────

class InferenceRequestSerializer(Serializer):
    """
    Validates incoming inference request payloads.

    Used by the serving controller to validate HTTP request bodies
    before dispatching to the batcher.
    """
    request_id = CharField(max_length=128)
    inputs = DictField(required=True)
    parameters = DictField(required=False, default=dict)


# ── InferenceResult ──────────────────────────────────────────────────────

class InferenceResultSerializer(Serializer):
    """Renders inference results for API responses."""
    request_id = ReadOnlyField()
    outputs = DictField()
    latency_ms = FloatField(min_value=0.0)
    metadata = DictField(required=False, default=dict)


# ── DriftReport ──────────────────────────────────────────────────────────

class DriftReportSerializer(Serializer):
    """Renders drift detection reports."""
    method = ChoiceField(choices=[m.value for m in DriftMethod])
    score = FloatField()
    threshold = FloatField()
    is_drifted = BooleanField()
    feature_scores = DictField(required=False, default=dict)
    window_start = CharField(required=False, default="")
    window_end = CharField(required=False, default="")


# ── RolloutConfig ────────────────────────────────────────────────────────

class RolloutConfigSerializer(Serializer):
    """Validates rollout configuration payloads."""
    from_version = CharField(max_length=64)
    to_version = CharField(max_length=64)
    strategy = ChoiceField(
        choices=[s.value for s in RolloutStrategy],
        required=False,
        default="canary",
    )
    percentage = IntegerField(min_value=0, max_value=100, required=False, default=10)
    metric = CharField(max_length=64, required=False, default="latency_p95")
    threshold = FloatField(required=False, default=0.0)
    auto_rollback = BooleanField(required=False, default=True)
    step_interval_seconds = IntegerField(min_value=1, required=False, default=300)


# ── RolloutState ─────────────────────────────────────────────────────────

class RolloutStateSerializer(Serializer):
    """Renders rollout state for API responses."""
    id = ReadOnlyField()
    phase = ReadOnlyField()
    current_percentage = IntegerField()
    steps_completed = IntegerField()
    started_at = FloatField()
    completed_at = FloatField()
    error = CharField(required=False, default="")


# ── ScalingPolicy ────────────────────────────────────────────────────────

class ScalingPolicySerializer(Serializer):
    """Validates autoscaler policy configuration."""
    min_replicas = IntegerField(min_value=0, required=False, default=1)
    max_replicas = IntegerField(min_value=1, required=False, default=10)
    target_concurrency = FloatField(min_value=0.1, required=False, default=10.0)
    target_latency_p95_ms = FloatField(min_value=0.0, required=False, default=100.0)
    scale_up_threshold = FloatField(min_value=0.0, max_value=1.0, required=False, default=0.8)
    scale_down_threshold = FloatField(min_value=0.0, max_value=1.0, required=False, default=0.3)
    cooldown_seconds = IntegerField(min_value=0, required=False, default=60)


# ── NodeInfo ─────────────────────────────────────────────────────────────

class NodeInfoSerializer(Serializer):
    """Validates compute node registration payloads."""
    node_id = CharField(max_length=128)
    device_type = ChoiceField(choices=["cpu", "gpu", "npu"], required=False, default="cpu")
    total_memory_mb = FloatField(min_value=0.0, required=False, default=0.0)
    available_memory_mb = FloatField(min_value=0.0, required=False, default=0.0)
    current_load = FloatField(min_value=0.0, max_value=1.0, required=False, default=0.0)
    gpu_available = BooleanField(required=False, default=False)


# ── PlacementRequest ────────────────────────────────────────────────────

class PlacementRequestSerializer(Serializer):
    """Validates model placement request payloads."""
    model_name = CharField(max_length=256)
    model_size_mb = FloatField(min_value=0.0)
    preferred_device = ChoiceField(
        choices=["cpu", "gpu", "npu", "any"],
        required=False,
        default="any",
    )
    gpu_required = BooleanField(required=False, default=False)


# ── Plugin ───────────────────────────────────────────────────────────────

class PluginDescriptorSerializer(Serializer):
    """Renders plugin descriptor for API responses."""
    name = ReadOnlyField()
    version = ReadOnlyField()
    module = ReadOnlyField()
    state = ReadOnlyField()
    error = CharField(required=False, default="")
    metadata = DictField(required=False, default=dict)


# ── Metrics ──────────────────────────────────────────────────────────────

class MetricsSummarySerializer(Serializer):
    """Renders metrics summary for API responses."""
    model_name = ReadOnlyField()
    model_version = ReadOnlyField()
    # All other metrics are dynamic, rendered via DictField
