"""
Traffic router — canary, A/B, shadow, sticky routing for model deployments.

Supports:
- Canary release (X% traffic to new version)
- A/B testing (deterministic split by request ID)
- Shadow traffic (duplicate to new version without returning results)
- **Sticky routing** via :class:`ConsistentHash` (same model key → same target)
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .._types import RolloutConfig, RolloutStrategy
from .._structures import ConsistentHash, TopKHeap

logger = logging.getLogger("aquilia.mlops.serving.router")


@dataclass
class RouteTarget:
    """A model version target with associated weight."""
    version: str
    weight: float  # 0.0 – 1.0
    handler: Optional[Callable] = None
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0


class TrafficRouter:
    """
    Routes inference requests across model version targets.

    Supports weighted routing (canary), deterministic hashing (A/B),
    shadow mode, and **sticky routing** via consistent hashing.

    The embedded :class:`TopKHeap` tracks the most-requested models
    (hot-model tracking) — accessible via :meth:`hot_models`.
    """

    def __init__(self, sticky_buckets: int = 64):
        self._targets: Dict[str, RouteTarget] = {}
        self._strategy: RolloutStrategy = RolloutStrategy.CANARY
        self._hasher = ConsistentHash(num_buckets=max(1, sticky_buckets))
        self._hot_tracker = TopKHeap(k=20)

    def add_target(
        self,
        version: str,
        weight: float,
        handler: Optional[Callable] = None,
    ) -> None:
        """Register a model version as a routing target."""
        self._targets[version] = RouteTarget(
            version=version, weight=weight, handler=handler
        )
        self._normalize_weights()
        logger.info("Added route target: %s (weight=%.2f)", version, weight)

    def remove_target(self, version: str) -> None:
        """Remove a routing target."""
        self._targets.pop(version, None)
        self._normalize_weights()

    def set_strategy(self, strategy: RolloutStrategy) -> None:
        """Set the routing strategy."""
        self._strategy = strategy

    def set_canary_percentage(self, version: str, percentage: int) -> None:
        """Set canary percentage for a specific version."""
        if version not in self._targets:
            raise KeyError(f"Unknown target: {version}")

        # Set weight for canary target
        for v, target in self._targets.items():
            if v == version:
                target.weight = percentage / 100.0
            else:
                target.weight = (100 - percentage) / 100.0

    def route(self, request_id: str = "") -> str:
        """
        Select a target version for the given request.

        Returns:
            The selected version string.
        """
        if not self._targets:
            raise RuntimeError("No routing targets configured")

        if len(self._targets) == 1:
            version = next(iter(self._targets))
            self._hot_tracker.push(version, 1)
            return version

        if self._strategy == RolloutStrategy.AB_TEST:
            chosen = self._ab_route(request_id)
        elif self._strategy == RolloutStrategy.SHADOW:
            # Shadow always routes to primary; secondary is called async
            chosen = self._primary_version()
        else:
            # Canary: weighted random
            chosen = self._weighted_route()

        self._hot_tracker.push(chosen, 1)
        return chosen

    def route_sticky(self, key: str) -> str:
        """
        Sticky routing via consistent hashing.

        The same ``key`` (e.g. user-id or model-name) always maps to
        the same target version, enabling cache locality and affinity.
        Adding/removing a target only redistributes ~1/n of keys.
        """
        if not self._targets:
            raise RuntimeError("No routing targets configured")
        targets = sorted(self._targets.keys())
        # Use ConsistentHash buckets mapped to target list
        bucket = self._hasher.bucket(key) % len(targets)
        chosen = targets[bucket]
        self._hot_tracker.push(chosen, 1)
        return chosen

    def record_result(
        self,
        version: str,
        latency_ms: float,
        error: bool = False,
    ) -> None:
        """Record a result for metrics tracking."""
        target = self._targets.get(version)
        if target:
            target.request_count += 1
            target.total_latency_ms += latency_ms
            if error:
                target.error_count += 1
            # Track hot models by request volume
            self._hot_tracker.push(version, target.request_count)

    def hot_models(self, k: int = 10) -> List[tuple]:
        """Return the top-K most-requested model versions."""
        return self._hot_tracker.top()[:k]

    def should_rollback(self, config: RolloutConfig) -> bool:
        """
        Check if rollback should be triggered based on metrics.

        Compares the canary version's performance against the threshold.
        """
        canary = self._targets.get(config.to_version)
        baseline = self._targets.get(config.from_version)

        if not canary or not baseline:
            return False

        if canary.request_count < 10:
            return False  # Not enough data

        canary_avg = canary.total_latency_ms / max(canary.request_count, 1)
        baseline_avg = baseline.total_latency_ms / max(baseline.request_count, 1)

        # Check if canary is significantly worse
        if config.metric == "latency_p95":
            if canary_avg > baseline_avg * (1.0 + abs(config.threshold)):
                return True

        canary_error_rate = canary.error_count / max(canary.request_count, 1)
        baseline_error_rate = baseline.error_count / max(baseline.request_count, 1)

        if canary_error_rate > baseline_error_rate + 0.05:
            return True

        return False

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get per-version metrics."""
        result = {}
        for version, target in self._targets.items():
            avg_latency = target.total_latency_ms / max(target.request_count, 1)
            error_rate = target.error_count / max(target.request_count, 1)
            result[version] = {
                "weight": target.weight,
                "request_count": float(target.request_count),
                "avg_latency_ms": avg_latency,
                "error_rate": error_rate,
            }
        return result

    # ── Internal ─────────────────────────────────────────────────────

    def _normalize_weights(self) -> None:
        total = sum(t.weight for t in self._targets.values())
        if total > 0:
            for t in self._targets.values():
                t.weight /= total

    def _weighted_route(self) -> str:
        targets = list(self._targets.keys())
        weights = [self._targets[v].weight for v in targets]
        return random.choices(targets, weights=weights, k=1)[0]

    def _ab_route(self, request_id: str) -> str:
        """Deterministic routing based on request ID hash."""
        h = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        targets = sorted(self._targets.keys())
        idx = h % len(targets)
        return targets[idx]

    def _primary_version(self) -> str:
        """Return the version with highest weight (primary)."""
        return max(self._targets.keys(), key=lambda v: self._targets[v].weight)
