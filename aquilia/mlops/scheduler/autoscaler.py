"""
Autoscaler — K8s HPA metrics exporter and scaling policy engine.

Exposes custom metrics that Kubernetes HPA can use to scale deployments.
Also provides an in-process fallback for non-K8s environments.

Uses :class:`SlidingWindow` for time-windowed metric aggregation so
that scaling decisions are based on recent trends, not stale snapshots.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .._structures import SlidingWindow

logger = logging.getLogger("aquilia.mlops.scheduler.autoscaler")


@dataclass
class ScalingPolicy:
    """Autoscaling policy definition."""
    min_replicas: int = 1
    max_replicas: int = 10
    target_concurrency: float = 10.0
    target_latency_p95_ms: float = 100.0
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3
    cooldown_seconds: int = 60
    window_seconds: float = 60.0
    bucket_width: float = 5.0


@dataclass
class ScalingDecision:
    """Output of a scaling evaluation."""
    current_replicas: int
    desired_replicas: int
    reason: str
    metrics: Dict[str, float] = field(default_factory=dict)


class Autoscaler:
    """
    Autoscaling engine for model serving deployments.

    Evaluates current metrics against a policy and emits scaling decisions.

    Uses a :class:`SlidingWindow` to track request rate and latency
    over a configurable time window, producing stable scaling signals
    rather than reacting to momentary spikes.
    """

    def __init__(self, policy: Optional[ScalingPolicy] = None):
        self.policy = policy or ScalingPolicy()
        self._current_replicas = 1
        self._last_scale_time = 0.0

        # Time-windowed metric trackers
        self._request_window = SlidingWindow(
            window_seconds=self.policy.window_seconds,
            bucket_width=self.policy.bucket_width,
        )
        self._latency_window = SlidingWindow(
            window_seconds=self.policy.window_seconds,
            bucket_width=self.policy.bucket_width,
        )
        self._error_window = SlidingWindow(
            window_seconds=self.policy.window_seconds,
            bucket_width=self.policy.bucket_width,
        )

    # ── Feed metrics into sliding windows ─────────────────────────────

    def record_request(self, latency_ms: float = 0.0, error: bool = False) -> None:
        """Record a single request into the sliding windows."""
        now = time.monotonic()
        self._request_window.add(1.0, ts=now)
        self._latency_window.add(latency_ms, ts=now)
        if error:
            self._error_window.add(1.0, ts=now)

    @property
    def window_rps(self) -> float:
        """Current requests-per-second from the sliding window."""
        return self._request_window.rate()

    @property
    def window_avg_latency(self) -> float:
        """Average latency across the current window."""
        return self._latency_window.mean()

    @property
    def window_error_rate(self) -> float:
        """Error rate in the current window."""
        total = self._request_window.count()
        errors = self._error_window.count()
        return errors / total if total > 0 else 0.0

    @property
    def window_stats(self) -> Dict[str, float]:
        """Summary of windowed metrics."""
        return {
            "rps": self.window_rps,
            "avg_latency_ms": self.window_avg_latency,
            "error_rate": self.window_error_rate,
            "request_count": float(self._request_window.count()),
        }

    # ── Core evaluate ─────────────────────────────────────────────────

    def evaluate(
        self,
        metrics: Optional[Dict[str, float]] = None,
    ) -> ScalingDecision:
        """
        Evaluate current metrics and decide on scaling.

        If called without ``metrics``, uses the internal sliding-window
        data.  Otherwise merges the provided snapshot with window data.

        Args:
            metrics: Optional dict with keys like ``concurrency``, ``latency_p95``, etc.

        Returns:
            Scaling decision.
        """
        m = dict(metrics or {})

        # Enrich with window data if not already present
        if "aquilia_concurrency" not in m:
            m["aquilia_concurrency"] = self.window_rps * self._current_replicas
        if "aquilia_inference_latency_ms_p95" not in m:
            m["aquilia_inference_latency_ms_p95"] = self.window_avg_latency

        concurrency = m.get("aquilia_concurrency", 0)
        latency_p95 = m.get("aquilia_inference_latency_ms_p95", 0)

        desired = self._current_replicas

        # Cooldown guard
        now = time.monotonic()
        in_cooldown = (now - self._last_scale_time) < self.policy.cooldown_seconds

        # Scale up
        if concurrency > self.policy.target_concurrency * self.policy.scale_up_threshold:
            if not in_cooldown:
                desired = min(
                    self._current_replicas + 1,
                    self.policy.max_replicas,
                )
            reason = f"High concurrency: {concurrency:.1f}"
        elif latency_p95 > self.policy.target_latency_p95_ms:
            if not in_cooldown:
                desired = min(
                    self._current_replicas + 1,
                    self.policy.max_replicas,
                )
            reason = f"High latency p95: {latency_p95:.1f}ms"
        # Scale down
        elif (
            concurrency < self.policy.target_concurrency * self.policy.scale_down_threshold
            and self._current_replicas > self.policy.min_replicas
        ):
            if not in_cooldown:
                desired = max(
                    self._current_replicas - 1,
                    self.policy.min_replicas,
                )
            reason = f"Low concurrency: {concurrency:.1f}"
        else:
            reason = "Steady state"

        return ScalingDecision(
            current_replicas=self._current_replicas,
            desired_replicas=desired,
            reason=reason,
            metrics=m,
        )

    def apply(self, decision: ScalingDecision) -> None:
        """Apply a scaling decision (update internal state)."""
        if decision.desired_replicas != self._current_replicas:
            self._last_scale_time = time.monotonic()
        self._current_replicas = decision.desired_replicas
        logger.info(
            "Scaling: %d → %d (%s)",
            decision.current_replicas,
            decision.desired_replicas,
            decision.reason,
        )

    def generate_hpa_manifest(
        self,
        deployment_name: str,
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """
        Generate a Kubernetes HorizontalPodAutoscaler manifest.

        Returns a dict that can be serialized to YAML/JSON.
        """
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{deployment_name}-hpa",
                "namespace": namespace,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": deployment_name,
                },
                "minReplicas": self.policy.min_replicas,
                "maxReplicas": self.policy.max_replicas,
                "metrics": [
                    {
                        "type": "Pods",
                        "pods": {
                            "metric": {"name": "aquilia_concurrency"},
                            "target": {
                                "type": "AverageValue",
                                "averageValue": str(int(self.policy.target_concurrency)),
                            },
                        },
                    },
                    {
                        "type": "Pods",
                        "pods": {
                            "metric": {"name": "aquilia_inference_latency_p95"},
                            "target": {
                                "type": "AverageValue",
                                "averageValue": f"{int(self.policy.target_latency_p95_ms)}m",
                            },
                        },
                    },
                ],
            },
        }
