"""
Hardware-aware placement scheduler.

Scores candidate nodes and assigns model replicas using a weighted
scoring algorithm with periodic rebalancing.

Score = w1·device_affinity + w2·memory_fit + w3·(1-load) + w4·(1-cold_start)
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .._types import PlacementScore

logger = logging.getLogger("aquilia.mlops.scheduler.placement")


@dataclass
class NodeInfo:
    """Information about a compute node."""
    node_id: str
    device_type: str = "cpu"        # "cpu", "gpu", "npu"
    total_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    current_load: float = 0.0       # 0.0 – 1.0
    gpu_available: bool = False
    models_loaded: List[str] = field(default_factory=list)
    # GPU-specific metrics
    gpu_memory_total_mb: float = 0.0
    gpu_memory_available_mb: float = 0.0
    gpu_utilization: float = 0.0    # 0.0 – 1.0
    gpu_name: str = ""
    compute_capability: str = ""     # e.g. "8.6"


@dataclass
class PlacementRequest:
    """Request for model placement."""
    model_name: str
    model_size_mb: float
    preferred_device: str = "any"   # "cpu", "gpu", "npu", "any"
    gpu_required: bool = False
    # LLM-specific placement hints
    gpu_memory_required_mb: float = 0.0
    model_type: str = "SLM"        # "SLM", "LLM", "VISION", "MULTIMODAL"
    quantized: bool = False
    min_compute_capability: str = ""  # e.g. "7.0" for Tensor Cores


class PlacementScheduler:
    """
    Greedy placement scheduler with soft device affinity.

    Scores all candidate nodes and picks the best one.
    Supports periodic rebalancing.
    """

    def __init__(
        self,
        w_affinity: float = 0.25,
        w_memory: float = 0.25,
        w_load: float = 0.20,
        w_coldstart: float = 0.10,
        w_gpu_memory: float = 0.20,
    ):
        self._weights = (w_affinity, w_memory, w_load, w_coldstart, w_gpu_memory)
        self._nodes: Dict[str, NodeInfo] = {}

    def register_node(self, node: NodeInfo) -> None:
        """Register a compute node."""
        self._nodes[node.node_id] = node
        logger.info("Registered node: %s (%s)", node.node_id, node.device_type)

    def unregister_node(self, node_id: str) -> None:
        """Remove a node."""
        self._nodes.pop(node_id, None)

    def update_node(self, node_id: str, **kwargs: Any) -> None:
        """Update node metrics."""
        node = self._nodes.get(node_id)
        if node:
            for k, v in kwargs.items():
                if hasattr(node, k):
                    setattr(node, k, v)

    def place(self, request: PlacementRequest) -> Optional[PlacementScore]:
        """
        Find the best node for a model placement request.

        Considers device affinity, system memory, GPU memory, load,
        cold-start cost, and compute capability requirements.

        Returns the highest-scoring PlacementScore, or None if no node fits.
        """
        if not self._nodes:
            return None

        w1, w2, w3, w4, w5 = self._weights
        scores: List[PlacementScore] = []

        for node in self._nodes.values():
            # Hard constraint: GPU required but not available
            if request.gpu_required and not node.gpu_available:
                continue

            # Hard constraint: GPU memory insufficient for LLM
            if request.gpu_memory_required_mb > 0 and node.gpu_memory_available_mb < request.gpu_memory_required_mb:
                continue

            # Hard constraint: compute capability check
            if request.min_compute_capability and node.compute_capability:
                try:
                    req_cc = tuple(int(x) for x in request.min_compute_capability.split("."))
                    node_cc = tuple(int(x) for x in node.compute_capability.split("."))
                    if node_cc < req_cc:
                        continue
                except (ValueError, IndexError):
                    pass

            # Device affinity
            if request.preferred_device == "any":
                affinity = 1.0
            elif request.preferred_device == node.device_type:
                affinity = 1.0
            else:
                affinity = 0.3

            # For LLM workloads, strongly prefer GPU nodes
            if request.model_type in ("LLM", "MULTIMODAL") and node.gpu_available:
                affinity = min(affinity + 0.3, 1.0)

            # System memory fit
            if node.available_memory_mb <= 0:
                memory_fit = 0.0
            elif request.model_size_mb > node.available_memory_mb:
                memory_fit = 0.0
            else:
                memory_fit = 1.0 - (request.model_size_mb / node.available_memory_mb)

            # GPU memory fit (for LLM/GPU workloads)
            gpu_mem_fit = 0.0
            if node.gpu_available and node.gpu_memory_total_mb > 0:
                if request.gpu_memory_required_mb > 0:
                    if node.gpu_memory_available_mb >= request.gpu_memory_required_mb:
                        gpu_mem_fit = 1.0 - (request.gpu_memory_required_mb / node.gpu_memory_available_mb)
                else:
                    gpu_mem_fit = node.gpu_memory_available_mb / node.gpu_memory_total_mb
            elif not node.gpu_available:
                # CPU-only node: gpu memory score is neutral
                gpu_mem_fit = 0.5

            # Cold start cost
            cold_start = 0.0 if request.model_name in node.models_loaded else 1.0

            score = PlacementScore(
                node_id=node.node_id,
                device_affinity=affinity,
                memory_fit=memory_fit,
                current_load=node.current_load,
                cold_start_cost=cold_start,
            )
            # Extended scoring: combine original + GPU memory
            base_score = w1 * affinity + w2 * memory_fit + w3 * (1.0 - node.current_load) + w4 * (1.0 - cold_start)
            gpu_score = w5 * gpu_mem_fit
            score.total = base_score + gpu_score
            scores.append(score)

        if not scores:
            return None

        best = max(scores, key=lambda s: s.total)
        logger.info(
            "Placement: %s → %s (score=%.3f)",
            request.model_name, best.node_id, best.total,
        )
        return best

    def rebalance(self) -> List[Dict[str, Any]]:
        """
        Suggest rebalancing moves to improve load distribution.

        Returns a list of suggested moves (from_node, to_node, model).
        """
        moves: List[Dict[str, Any]] = []

        overloaded = [n for n in self._nodes.values() if n.current_load > 0.8]
        underloaded = [n for n in self._nodes.values() if n.current_load < 0.3]

        for over in overloaded:
            if not over.models_loaded or not underloaded:
                continue
            model = over.models_loaded[-1]
            target = min(underloaded, key=lambda n: n.current_load)
            moves.append({
                "model": model,
                "from_node": over.node_id,
                "to_node": target.node_id,
                "reason": f"Rebalance: {over.node_id} overloaded ({over.current_load:.1%})",
            })

        return moves
