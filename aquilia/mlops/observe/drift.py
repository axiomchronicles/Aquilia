"""
Drift detection — PSI, KS-test, and distribution tracking.

Monitors feature and prediction distributions over time to detect
model staleness and trigger retrain alerts.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .._types import DriftMethod, DriftReport
from ..faults import DriftDetectionFault

logger = logging.getLogger("aquilia.mlops.observe.drift")


class DriftDetector:
    """
    Model drift detection engine.

    Supports:
    - PSI (Population Stability Index)
    - KS (Kolmogorov-Smirnov) test
    - Distribution comparison

    Usage::

        detector = DriftDetector(method=DriftMethod.PSI, threshold=0.2)
        detector.set_reference(reference_data)
        report = detector.detect(current_data)
        if report.is_drifted:
            trigger_retrain()
    """

    def __init__(
        self,
        method: DriftMethod = DriftMethod.PSI,
        threshold: float = 0.2,
        num_bins: int = 10,
    ):
        self.method = method
        self.threshold = threshold
        self.num_bins = num_bins
        self._reference: Optional[Dict[str, List[float]]] = None

    def set_reference(self, data: Dict[str, Sequence[float]]) -> None:
        """
        Set the reference (training) distribution.

        Args:
            data: Dict mapping feature names to value sequences.
        """
        self._reference = {k: list(v) for k, v in data.items()}
        logger.info("Reference distribution set (%d features)", len(self._reference))

    def detect(
        self,
        current: Dict[str, Sequence[float]],
        window_start: str = "",
        window_end: str = "",
    ) -> DriftReport:
        """
        Run drift detection against the reference distribution.

        Args:
            current: Dict mapping feature names to current value sequences.
            window_start: ISO timestamp for reporting.
            window_end: ISO timestamp for reporting.

        Returns:
            ``DriftReport`` with scores and drift flag.
        """
        if self._reference is None:
            raise DriftDetectionFault(
                "Reference distribution not set. Call set_reference() first.",
            )

        feature_scores: Dict[str, float] = {}

        for feature in self._reference:
            ref_values = self._reference[feature]
            cur_values = list(current.get(feature, []))

            if not cur_values:
                continue

            if self.method == DriftMethod.PSI:
                score = self._compute_psi(ref_values, cur_values)
            elif self.method == DriftMethod.KS_TEST:
                score = self._compute_ks(ref_values, cur_values)
            else:
                score = self._compute_distribution_diff(ref_values, cur_values)

            feature_scores[feature] = score

        if feature_scores:
            overall_score = sum(feature_scores.values()) / len(feature_scores)
        else:
            overall_score = 0.0

        is_drifted = overall_score > self.threshold

        report = DriftReport(
            method=self.method,
            score=overall_score,
            threshold=self.threshold,
            is_drifted=is_drifted,
            feature_scores=feature_scores,
            window_start=window_start,
            window_end=window_end,
        )

        if is_drifted:
            logger.warning(
                "Drift detected! score=%.4f threshold=%.4f method=%s",
                overall_score, self.threshold, self.method.value,
            )

        return report

    # ── PSI ──────────────────────────────────────────────────────────

    def _compute_psi(
        self, reference: List[float], current: List[float]
    ) -> float:
        """
        Compute Population Stability Index.

        PSI = Σ (p_i - q_i) * ln(p_i / q_i)

        Where p = reference proportions, q = current proportions.
        Uses a **common** range for binning both distributions.
        """
        eps = 1e-10
        # Use common range so distributions are compared in the same space
        lo = min(min(reference), min(current))
        hi = max(max(reference), max(current))
        ref_hist = self._histogram(reference, self.num_bins, lo=lo, hi=hi)
        cur_hist = self._histogram(current, self.num_bins, lo=lo, hi=hi)

        psi = 0.0
        for p, q in zip(ref_hist, cur_hist):
            p = max(p, eps)
            q = max(q, eps)
            psi += (p - q) * math.log(p / q)

        return psi

    # ── KS Test ──────────────────────────────────────────────────────

    def _compute_ks(
        self, reference: List[float], current: List[float]
    ) -> float:
        """
        Compute Kolmogorov-Smirnov statistic (max CDF difference).
        """
        ref_sorted = sorted(reference)
        cur_sorted = sorted(current)
        n_ref = len(ref_sorted)
        n_cur = len(cur_sorted)

        if n_ref == 0 or n_cur == 0:
            return 0.0

        all_values = sorted(set(ref_sorted + cur_sorted))
        max_diff = 0.0

        for val in all_values:
            ref_cdf = sum(1 for x in ref_sorted if x <= val) / n_ref
            cur_cdf = sum(1 for x in cur_sorted if x <= val) / n_cur
            max_diff = max(max_diff, abs(ref_cdf - cur_cdf))

        return max_diff

    # ── Distribution Diff ────────────────────────────────────────────

    def _compute_distribution_diff(
        self, reference: List[float], current: List[float]
    ) -> float:
        """Mean absolute difference between histograms."""
        ref_hist = self._histogram(reference, self.num_bins)
        cur_hist = self._histogram(current, self.num_bins)

        return sum(abs(p - q) for p, q in zip(ref_hist, cur_hist)) / self.num_bins

    # ── Helpers ──────────────────────────────────────────────────────

    def _histogram(
        self, values: List[float], num_bins: int,
        lo: Optional[float] = None, hi: Optional[float] = None,
    ) -> List[float]:
        """Compute normalized histogram (proportions)."""
        if not values:
            return [0.0] * num_bins

        if lo is None:
            lo = min(values)
        if hi is None:
            hi = max(values)
        if lo == hi:
            result = [0.0] * num_bins
            result[0] = 1.0
            return result

        bin_width = (hi - lo) / num_bins
        counts = [0] * num_bins

        for v in values:
            idx = min(int((v - lo) / bin_width), num_bins - 1)
            idx = max(idx, 0)  # clamp to valid range
            counts[idx] += 1

        total = len(values)
        return [c / total for c in counts]

    # ── Convenience ──────────────────────────────────────────────────

    def check(
        self,
        reference: Sequence[float],
        current: Sequence[float],
        feature_name: str = "feature",
    ) -> DriftReport:
        """
        Quick single-feature drift check (no need to set reference first).

        Returns a :class:`DriftReport` for the single feature.
        """
        ref = list(reference)
        cur = list(current)

        if self.method == DriftMethod.PSI:
            score = self._compute_psi(ref, cur)
        elif self.method == DriftMethod.KS_TEST:
            score = self._compute_ks(ref, cur)
        else:
            score = self._compute_distribution_diff(ref, cur)

        is_drifted = score > self.threshold

        return DriftReport(
            method=self.method,
            score=score,
            threshold=self.threshold,
            is_drifted=is_drifted,
            feature_scores={feature_name: score},
        )
