"""
Release rollout engine — canary, A/B, shadow traffic management.

Orchestrates progressive rollouts with metric-gated advancement
and automatic rollback.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .._types import RolloutConfig, RolloutStrategy
from ..serving.router import TrafficRouter

logger = logging.getLogger("aquilia.mlops.release.rollout")


class RolloutPhase(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class RolloutState:
    """Current state of a rollout."""
    id: str
    config: RolloutConfig
    phase: RolloutPhase = RolloutPhase.PENDING
    current_percentage: int = 0
    steps_completed: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    metrics_history: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""


class RolloutEngine:
    """
    Manages progressive rollouts with metric-based gating.

    Usage::

        engine = RolloutEngine(router=traffic_router)
        rollout = await engine.start(RolloutConfig(
            from_version="v1", to_version="v2",
            percentage=10, auto_rollback=True,
        ))
        await engine.advance(rollout.id, percentage=50)
        await engine.complete(rollout.id)
    """

    def __init__(
        self,
        router: Optional[TrafficRouter] = None,
        metrics_fn: Optional[Callable[[], Dict[str, float]]] = None,
    ):
        self._router = router or TrafficRouter()
        self._metrics_fn = metrics_fn
        self._rollouts: Dict[str, RolloutState] = {}
        self._counter = 0

    async def start(self, config: RolloutConfig) -> RolloutState:
        """Start a new rollout."""
        self._counter += 1
        rollout_id = f"rollout-{self._counter}"

        state = RolloutState(
            id=rollout_id,
            config=config,
            phase=RolloutPhase.IN_PROGRESS,
            current_percentage=config.percentage,
            started_at=time.time(),
        )
        self._rollouts[rollout_id] = state

        # Configure router
        self._router.add_target(config.from_version, weight=(100 - config.percentage) / 100.0)
        self._router.add_target(config.to_version, weight=config.percentage / 100.0)

        logger.info(
            "Started rollout %s: %s → %s (canary=%d%%)",
            rollout_id, config.from_version, config.to_version, config.percentage,
        )
        return state

    async def advance(
        self,
        rollout_id: str,
        percentage: Optional[int] = None,
    ) -> RolloutState:
        """Advance a rollout to a higher canary percentage."""
        state = self._rollouts.get(rollout_id)
        if not state:
            raise KeyError(f"Rollout not found: {rollout_id}")

        if state.phase != RolloutPhase.IN_PROGRESS:
            raise RuntimeError(f"Cannot advance rollout in phase: {state.phase.value}")

        # Check for auto-rollback
        if state.config.auto_rollback and self._router.should_rollback(state.config):
            return await self.rollback(rollout_id, reason="Auto-rollback triggered by metric degradation")

        new_pct = percentage or min(state.current_percentage + 10, 100)
        state.current_percentage = new_pct
        state.steps_completed += 1

        # Capture metrics
        if self._metrics_fn:
            metrics = self._metrics_fn()
            state.metrics_history.append({
                "step": state.steps_completed,
                "percentage": new_pct,
                "timestamp": time.time(),
                "metrics": metrics,
            })

        # Update router weights
        self._router.set_canary_percentage(state.config.to_version, new_pct)

        if new_pct >= 100:
            return await self.complete(rollout_id)

        logger.info("Advanced rollout %s to %d%%", rollout_id, new_pct)
        return state

    async def complete(self, rollout_id: str) -> RolloutState:
        """Complete a rollout (100% traffic to new version)."""
        state = self._rollouts.get(rollout_id)
        if not state:
            raise KeyError(f"Rollout not found: {rollout_id}")

        state.phase = RolloutPhase.COMPLETED
        state.current_percentage = 100
        state.completed_at = time.time()

        # Remove old version from router
        self._router.remove_target(state.config.from_version)

        logger.info("Completed rollout %s", rollout_id)
        return state

    async def rollback(
        self,
        rollout_id: str,
        reason: str = "",
    ) -> RolloutState:
        """Rollback a rollout to the original version."""
        state = self._rollouts.get(rollout_id)
        if not state:
            raise KeyError(f"Rollout not found: {rollout_id}")

        state.phase = RolloutPhase.ROLLED_BACK
        state.current_percentage = 0
        state.completed_at = time.time()
        state.error = reason

        # Route all traffic back
        self._router.remove_target(state.config.to_version)
        self._router.add_target(state.config.from_version, weight=1.0)

        logger.warning("Rolled back %s: %s", rollout_id, reason)
        return state

    def get_rollout(self, rollout_id: str) -> Optional[RolloutState]:
        return self._rollouts.get(rollout_id)

    def list_rollouts(self) -> List[RolloutState]:
        return list(self._rollouts.values())
