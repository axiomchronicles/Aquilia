"""
Tests for aquilia.mlops._types — enums, dataclasses, protocols.
"""

import hashlib
import json

import pytest

from aquilia.mlops._types import (
    BatchingStrategy,
    BatchRequest,
    BlobRef,
    DriftMethod,
    DriftReport,
    ExportTarget,
    Framework,
    InferenceRequest,
    InferenceResult,
    ModelpackManifest,
    PlacementScore,
    Provenance,
    QuantizePreset,
    RolloutConfig,
    RolloutStrategy,
    RuntimeKind,
    TensorSpec,
)


# ── Enums ────────────────────────────────────────────────────────────────

class TestEnums:
    def test_framework_values(self):
        assert Framework.PYTORCH == "pytorch"
        assert Framework.TENSORFLOW == "tensorflow"
        assert Framework.SKLEARN == "sklearn"
        assert Framework.ONNX == "onnx"

    def test_runtime_kind(self):
        assert RuntimeKind.PYTHON == "python"
        assert RuntimeKind.ONNXRUNTIME == "onnxruntime"
        assert RuntimeKind.TRITON == "triton"

    def test_quantize_preset(self):
        assert QuantizePreset.INT8 == "int8"
        assert QuantizePreset.FP16 == "fp16"

    def test_export_target(self):
        assert ExportTarget.TFLITE == "tflite"
        assert ExportTarget.COREML == "coreml"

    def test_batching_strategy(self):
        assert BatchingStrategy.HYBRID == "hybrid"

    def test_rollout_strategy(self):
        assert RolloutStrategy.CANARY == "canary"
        assert RolloutStrategy.BLUE_GREEN == "blue_green"

    def test_drift_method(self):
        assert DriftMethod.PSI == "psi"
        assert DriftMethod.KS_TEST == "ks_test"


# ── TensorSpec ───────────────────────────────────────────────────────────

class TestTensorSpec:
    def test_create(self):
        spec = TensorSpec(name="x", dtype="float32", shape=[1, 3, 224, 224])
        assert spec.name == "x"
        assert spec.dtype == "float32"
        assert spec.shape == [1, 3, 224, 224]

    def test_frozen(self):
        spec = TensorSpec(name="x", dtype="float32", shape=[1])
        with pytest.raises(AttributeError):
            spec.name = "y"


# ── BlobRef ──────────────────────────────────────────────────────────────

class TestBlobRef:
    def test_create(self):
        ref = BlobRef(digest="sha256:abc123", size=4096, path="model.pt")
        assert ref.digest == "sha256:abc123"
        assert ref.size == 4096


# ── Provenance ───────────────────────────────────────────────────────────

class TestProvenance:
    def test_defaults(self):
        p = Provenance()
        assert p.git_sha == ""
        assert p.dataset_snapshot == ""
        assert p.build_timestamp == ""


# ── ModelpackManifest ────────────────────────────────────────────────────

class TestModelpackManifest:
    def _make_manifest(self):
        return ModelpackManifest(
            name="test-model",
            version="v1.0.0",
            framework=Framework.PYTORCH,
            entrypoint="model.pt",
            inputs=[TensorSpec(name="x", dtype="float32", shape=[-1, 10])],
            outputs=[TensorSpec(name="y", dtype="float32", shape=[-1, 1])],
            blobs=[BlobRef(digest="sha256:aaa", size=100, path="model.pt")],
        )

    def test_content_digest_deterministic(self):
        m = self._make_manifest()
        d1 = m.content_digest()
        d2 = m.content_digest()
        assert d1 == d2
        assert d1.startswith("sha256:")

    def test_content_digest_changes_with_version(self):
        m1 = self._make_manifest()
        m2 = ModelpackManifest(
            name="test-model",
            version="v2.0.0",
            framework=Framework.PYTORCH,
            entrypoint="model.pt",
            inputs=[TensorSpec(name="x", dtype="float32", shape=[-1, 10])],
            outputs=[TensorSpec(name="y", dtype="float32", shape=[-1, 1])],
            blobs=[BlobRef(digest="sha256:aaa", size=100, path="model.pt")],
        )
        assert m1.content_digest() != m2.content_digest()


# ── InferenceRequest / Result ────────────────────────────────────────────

class TestInferenceRequestResult:
    def test_request(self):
        req = InferenceRequest(request_id="test-1", inputs={"x": [1.0, 2.0]})
        assert req.request_id == "test-1"
        assert req.inputs == {"x": [1.0, 2.0]}

    def test_result(self):
        res = InferenceResult(
            request_id="abc",
            outputs={"y": [0.5]},
            latency_ms=12.3,
        )
        assert res.latency_ms == 12.3


# ── RolloutConfig ────────────────────────────────────────────────────────

class TestRolloutConfig:
    def test_defaults(self):
        cfg = RolloutConfig(
            from_version="v1",
            to_version="v2",
            strategy=RolloutStrategy.CANARY,
        )
        assert cfg.percentage == 10
        assert cfg.auto_rollback is True
        assert cfg.from_version == "v1"
        assert cfg.to_version == "v2"


# ── DriftReport ──────────────────────────────────────────────────────────

class TestDriftReport:
    def test_create(self):
        r = DriftReport(
            method=DriftMethod.PSI,
            score=0.15,
            threshold=0.2,
            is_drifted=False,
        )
        assert r.is_drifted is False
