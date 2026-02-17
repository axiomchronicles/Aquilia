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
    ModelType,
    InferenceMode,
    DeviceType,
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


# ── LLM / Streaming Serializers ─────────────────────────────────────────

class LLMConfigSerializer(Serializer):
    """Validates LLM configuration payloads."""
    max_tokens = IntegerField(min_value=1, required=False, default=512)
    temperature = FloatField(min_value=0.0, max_value=2.0, required=False, default=1.0)
    top_k = IntegerField(min_value=1, required=False, default=50)
    top_p = FloatField(min_value=0.0, max_value=1.0, required=False, default=1.0)
    repetition_penalty = FloatField(min_value=0.0, required=False, default=1.0)
    stop_sequences = ListField(required=False, default=list)
    context_length = IntegerField(min_value=1, required=False, default=2048)
    dtype = CharField(max_length=16, required=False, default="float16")
    device_map = CharField(max_length=32, required=False, default="auto")
    quantize = ChoiceField(
        choices=[q.value for q in QuantizePreset],
        required=False,
        default="none",
    )
    trust_remote_code = BooleanField(required=False, default=False)


class StreamChunkSerializer(Serializer):
    """Renders a single streaming token/chunk for SSE responses."""
    request_id = ReadOnlyField()
    token = CharField(required=False, default="")
    token_index = IntegerField(min_value=0)
    finish_reason = CharField(required=False, default="")
    logprob = FloatField(required=False)


class TokenUsageSerializer(Serializer):
    """Renders token usage statistics for LLM inference."""
    prompt_tokens = IntegerField(min_value=0)
    completion_tokens = IntegerField(min_value=0)
    total_tokens = IntegerField(min_value=0)


class LLMInferenceRequestSerializer(Serializer):
    """
    Validates incoming LLM inference request payloads.

    Extends InferenceRequestSerializer with LLM-specific fields.
    """
    request_id = CharField(max_length=128)
    inputs = DictField(required=True)
    parameters = DictField(required=False, default=dict)
    # LLM-specific
    priority = IntegerField(min_value=0, max_value=10, required=False, default=5)
    stream = BooleanField(required=False, default=False)
    max_tokens = IntegerField(min_value=1, required=False, default=512)
    timeout_ms = FloatField(min_value=0.0, required=False, default=30000.0)
    temperature = FloatField(min_value=0.0, max_value=2.0, required=False, default=1.0)
    top_k = IntegerField(min_value=1, required=False, default=50)


class LLMInferenceResultSerializer(Serializer):
    """Renders LLM inference results including token metrics."""
    request_id = ReadOnlyField()
    outputs = DictField()
    latency_ms = FloatField(min_value=0.0)
    token_count = IntegerField(min_value=0, required=False, default=0)
    prompt_tokens = IntegerField(min_value=0, required=False, default=0)
    finish_reason = CharField(required=False, default="")
    metadata = DictField(required=False, default=dict)
    usage = DictField(required=False, default=dict)


class ChatMessageSerializer(Serializer):
    """Validates a single chat message."""
    role = ChoiceField(choices=["system", "user", "assistant", "function"], required=True)
    content = CharField(required=True)
    name = CharField(max_length=64, required=False, default="")


class ChatRequestSerializer(Serializer):
    """
    Validates chat-style LLM request payloads.

    Compatible with OpenAI-style chat completions API.
    """
    messages = ListField(required=True)
    model = CharField(max_length=256, required=False, default="")
    stream = BooleanField(required=False, default=False)
    max_tokens = IntegerField(min_value=1, required=False, default=512)
    temperature = FloatField(min_value=0.0, max_value=2.0, required=False, default=1.0)
    top_k = IntegerField(min_value=1, required=False, default=50)
    top_p = FloatField(min_value=0.0, max_value=1.0, required=False, default=1.0)
    stop = ListField(required=False, default=list)


class ChatResponseSerializer(Serializer):
    """Renders chat-style LLM response."""
    id = ReadOnlyField()
    model = ReadOnlyField()
    choices = ListField()
    usage = DictField(required=False, default=dict)
    created = FloatField(required=False)


class CircuitBreakerStatusSerializer(Serializer):
    """Renders circuit breaker state for API responses."""
    state = ChoiceField(choices=["closed", "open", "half_open"])
    failure_count = IntegerField(min_value=0)
    success_count = IntegerField(min_value=0)
    total_requests = IntegerField(min_value=0)
    total_rejections = IntegerField(min_value=0)
    last_failure_time = FloatField(required=False, default=0.0)


class RateLimiterStatusSerializer(Serializer):
    """Renders rate limiter state for API responses."""
    rate_rps = FloatField(min_value=0.0)
    capacity = IntegerField(min_value=0)
    available_tokens = FloatField(min_value=0.0)


class MemoryStatusSerializer(Serializer):
    """Renders memory tracker state for API responses."""
    current_mb = FloatField(min_value=0.0)
    soft_limit_mb = FloatField(min_value=0.0)
    hard_limit_mb = FloatField(min_value=0.0)
    utilization_pct = FloatField(min_value=0.0, max_value=100.0)
    exceeds_soft = BooleanField()
    exceeds_hard = BooleanField()


class ModelCapabilitiesSerializer(Serializer):
    """Renders model capabilities for API responses."""
    model_name = ReadOnlyField()
    model_type = ChoiceField(choices=[t.value for t in ModelType], required=False, default="SLM")
    supports_streaming = BooleanField(required=False, default=False)
    supports_chat = BooleanField(required=False, default=False)
    inference_modes = ListField(required=False, default=list)
    device = CharField(required=False, default="cpu")
    max_context_length = IntegerField(min_value=0, required=False, default=0)
