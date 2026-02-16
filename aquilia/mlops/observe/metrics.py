"""
Prometheus-compatible metrics collector.

Exposes model serving metrics for scraping and emits
structured metric events.

Metrics exposed:
- ``aquilia_inference_latency_seconds`` (histogram)
- ``aquilia_inference_total`` (counter)
- ``aquilia_inference_errors_total`` (counter)
- ``aquilia_batch_size`` (histogram)
- ``aquilia_model_memory_bytes`` (gauge)
- ``aquilia_concurrency`` (gauge)
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .._structures import RingBuffer, AtomicCounter, ExponentialDecay, TopKHeap

logger = logging.getLogger("aquilia.mlops.observe.metrics")


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """
    In-process metrics collector with Prometheus text format export.

    Collects counters, gauges, histogram-style quantiles, and tracks
    the **top-K hot models** by request volume via :class:`TopKHeap`.
    """

    def __init__(
        self,
        model_name: str = "",
        model_version: str = "",
        histogram_capacity: int = 10_000,
        hot_k: int = 20,
    ):
        self.model_name = model_name
        self.model_version = model_version
        self._histogram_capacity = histogram_capacity

        # Counters (thread-safe)
        self._counters: Dict[str, AtomicCounter] = defaultdict(AtomicCounter)
        # Gauges
        self._gauges: Dict[str, float] = {}
        # Histograms — bounded ring buffers instead of unbounded lists
        self._histograms: Dict[str, RingBuffer[float]] = {}
        # EWMA smoothed latency tracker
        self._ewma: Dict[str, ExponentialDecay] = {}
        # Hot-model tracker
        self._hot_models = TopKHeap(k=hot_k)

    def inc(self, name: str, value: float = 1.0) -> None:
        """Increment a counter."""
        self._counters[name].inc(int(value))

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation (bounded ring buffer)."""
        if name not in self._histograms:
            self._histograms[name] = RingBuffer(self._histogram_capacity)
        self._histograms[name].append(value)
        # Also update EWMA
        if name not in self._ewma:
            self._ewma[name] = ExponentialDecay(alpha=0.1)
        self._ewma[name].update(value)

    def record_inference(
        self,
        latency_ms: float,
        batch_size: int = 1,
        error: bool = False,
        model_name: str = "",
    ) -> None:
        """Record an inference event (convenience method)."""
        self.inc("aquilia_inference_total")
        self.observe("aquilia_inference_latency_ms", latency_ms)
        self.observe("aquilia_batch_size", float(batch_size))
        if error:
            self.inc("aquilia_inference_errors_total")
        # Track hot models
        if model_name:
            self._hot_models.push(model_name, 1)

    def hot_models(self, k: int = 10) -> list:
        """Return the top-K most-active models."""
        return self._hot_models.top()[:k]

    def percentile(self, name: str, p: float) -> float:
        """Compute p-th percentile for a histogram metric."""
        rb = self._histograms.get(name)
        if not rb:
            return 0.0
        return rb.percentile(p)

    def ewma(self, name: str) -> float:
        """Return the EWMA-smoothed value for a metric."""
        e = self._ewma.get(name)
        return e.value if e else 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics as a dict."""
        result: Dict[str, Any] = {
            "model_name": self.model_name,
            "model_version": self.model_version,
        }

        # Counters
        for name, counter in self._counters.items():
            result[name] = counter.value

        # Gauges
        for name, value in self._gauges.items():
            result[name] = value

        # Histogram percentiles
        for name, rb in self._histograms.items():
            if rb:
                result[f"{name}_p50"] = self.percentile(name, 50)
                result[f"{name}_p90"] = self.percentile(name, 90)
                result[f"{name}_p95"] = self.percentile(name, 95)
                result[f"{name}_p99"] = self.percentile(name, 99)
                result[f"{name}_count"] = len(rb)
                result[f"{name}_ewma"] = self.ewma(name)

        return result

    def to_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text exposition format.

        Returns:
            String in Prometheus text format.
        """
        lines: List[str] = []
        labels = f'model="{self.model_name}",version="{self.model_version}"'

        # Counters
        for name, counter in sorted(self._counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{{{labels}}} {counter.value}")

        # Gauges
        for name, value in sorted(self._gauges.items()):
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{{{labels}}} {value}")

        # Histograms → expose as summary with quantiles
        for name in sorted(self._histograms.keys()):
            lines.append(f"# TYPE {name} summary")
            for p in (0.5, 0.9, 0.95, 0.99):
                val = self.percentile(name, p * 100)
                lines.append(f'{name}{{quantile="{p}",{labels}}} {val}')
            lines.append(f"{name}_count{{{labels}}} {len(self._histograms[name])}")

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._ewma.clear()
