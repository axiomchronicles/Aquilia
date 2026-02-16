"""
Tests for aquilia.mlops.observe - metrics, drift, logger.
"""

import json
import tempfile
from pathlib import Path

import pytest

from aquilia.mlops.observe.metrics import MetricsCollector
from aquilia.mlops.observe.drift import DriftDetector
from aquilia.mlops.observe.logger import PredictionLogger
from aquilia.mlops._types import DriftMethod, InferenceRequest, InferenceResult


class TestMetricsCollector:
    def test_counter(self):
        mc = MetricsCollector()
        mc.inc("requests_total")
        mc.inc("requests_total")
        mc.inc("requests_total", 5)
        snap = mc.get_summary()
        assert snap["requests_total"] == 7

    def test_gauge(self):
        mc = MetricsCollector()
        mc.set_gauge("active_models", 3)
        snap = mc.get_summary()
        assert snap["active_models"] == 3

    def test_histogram(self):
        mc = MetricsCollector()
        for v in [10, 20, 30, 40, 50]:
            mc.observe("latency_ms", v)
        snap = mc.get_summary()
        assert snap["latency_ms_count"] == 5

    def test_prometheus_format(self):
        mc = MetricsCollector()
        mc.inc("req_total")
        mc.set_gauge("mem_mb", 512)
        mc.observe("lat", 10)
        text = mc.to_prometheus()
        assert "req_total" in text
        assert "mem_mb" in text

    def test_percentile_computation(self):
        mc = MetricsCollector()
        for i in range(100):
            mc.observe("lat", float(i))
        p50 = mc.percentile("lat", 50)
        p99 = mc.percentile("lat", 99)
        assert 40 <= p50 <= 60
        assert p99 >= 90


class TestDriftDetector:
    def test_no_drift_same_distribution(self):
        import random
        random.seed(42)
        ref = [random.gauss(0, 1) for _ in range(1000)]
        cur = [random.gauss(0, 1) for _ in range(1000)]
        detector = DriftDetector(method=DriftMethod.PSI, threshold=0.2)
        report = detector.check(ref, cur, feature_name="x")
        assert report.is_drifted is False
        assert report.score < 0.2

    def test_drift_shifted_distribution(self):
        import random
        random.seed(42)
        ref = [random.gauss(0, 1) for _ in range(1000)]
        cur = [random.gauss(5, 1) for _ in range(1000)]
        detector = DriftDetector(method=DriftMethod.PSI, threshold=0.2)
        report = detector.check(ref, cur, feature_name="x")
        assert report.is_drifted is True
        assert report.score > 0.2

    def test_ks_method(self):
        import random
        random.seed(42)
        ref = [random.gauss(0, 1) for _ in range(500)]
        cur = [random.gauss(3, 1) for _ in range(500)]
        detector = DriftDetector(method=DriftMethod.KS_TEST, threshold=0.1)
        report = detector.check(ref, cur, feature_name="age")
        assert report.method == DriftMethod.KS_TEST
        assert report.is_drifted is True

    def test_ks_no_drift(self):
        import random
        random.seed(42)
        ref = [random.gauss(0, 1) for _ in range(500)]
        cur = [random.gauss(0, 1) for _ in range(500)]
        detector = DriftDetector(method=DriftMethod.KS_TEST, threshold=0.1)
        report = detector.check(ref, cur, feature_name="age")
        assert report.score < 0.15


class TestPredictionLogger:
    def test_log_with_custom_sink(self):
        collected = []
        logger = PredictionLogger(sample_rate=1.0, sink=collected.append)
        req = InferenceRequest(request_id="req-1", inputs={"x": [1.0]})
        res = InferenceResult(request_id="req-1", outputs={"y": [0.5]}, latency_ms=10.0)
        logged = logger.log(req, res)
        assert logged is True
        assert len(collected) == 1
        assert collected[0]["request_id"] == "req-1"

    def test_sampling_rate_zero(self):
        collected = []
        logger = PredictionLogger(sample_rate=0.0, sink=collected.append)
        for i in range(100):
            req = InferenceRequest(request_id=f"r{i}", inputs={"x": [float(i)]})
            res = InferenceResult(request_id=f"r{i}", outputs={}, latency_ms=1.0)
            logger.log(req, res)
        assert len(collected) == 0

    def test_force_log(self):
        collected = []
        logger = PredictionLogger(sample_rate=0.0, sink=collected.append)
        req = InferenceRequest(request_id="f1", inputs={"x": [1.0]})
        res = InferenceResult(request_id="f1", outputs={}, latency_ms=5.0)
        logger.log(req, res, force=True)
        assert len(collected) == 1

    def test_log_to_file(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger = PredictionLogger(sample_rate=1.0, log_dir=log_dir)
        req = InferenceRequest(request_id="file-1", inputs={"x": [1.0]})
        res = InferenceResult(request_id="file-1", outputs={"y": [0.5]}, latency_ms=10.0)
        logger.log(req, res)
        files = list(Path(log_dir).glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["request_id"] == "file-1"

    def test_log_count(self):
        collected = []
        logger = PredictionLogger(sample_rate=1.0, sink=collected.append)
        for i in range(5):
            req = InferenceRequest(request_id=f"c{i}", inputs={"x": [float(i)]})
            res = InferenceResult(request_id=f"c{i}", outputs={}, latency_ms=1.0)
            logger.log(req, res)
        assert logger.get_log_count() == 5
