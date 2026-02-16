"""
Feature and prediction logger.

Samples inference inputs/outputs at a configurable rate and writes
them to a sink (file, Kafka, or custom handler).
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .._types import InferenceRequest, InferenceResult

logger = logging.getLogger("aquilia.mlops.observe.logger")


class PredictionLogger:
    """
    Logs feature/prediction pairs for monitoring, debugging, and retraining.

    Default sink: JSONL file. Pluggable via ``set_sink()``.

    Usage::

        pred_logger = PredictionLogger(sample_rate=0.01)
        pred_logger.log(request, result)
    """

    def __init__(
        self,
        sample_rate: float = 0.01,
        log_dir: str = "prediction_logs",
        sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.log_dir = log_dir
        self._sink = sink
        self._log_count = 0

        if not self._sink:
            Path(log_dir).mkdir(parents=True, exist_ok=True)

    def set_sink(self, sink: Callable[[Dict[str, Any]], None]) -> None:
        """Set a custom log sink function."""
        self._sink = sink

    def log(
        self,
        request: InferenceRequest,
        result: InferenceResult,
        *,
        force: bool = False,
    ) -> bool:
        """
        Log a request/result pair (subject to sampling).

        Args:
            request: The inference request.
            result: The inference result.
            force: Force logging regardless of sample rate.

        Returns:
            True if the event was logged.
        """
        if not force and random.random() > self.sample_rate:
            return False

        event = {
            "timestamp": time.time(),
            "request_id": request.request_id,
            "inputs": _safe_serialize(request.inputs),
            "outputs": _safe_serialize(result.outputs),
            "latency_ms": result.latency_ms,
            "parameters": request.parameters,
        }

        if self._sink:
            self._sink(event)
        else:
            self._write_to_file(event)

        self._log_count += 1
        return True

    def get_log_count(self) -> int:
        return self._log_count

    def _write_to_file(self, event: Dict[str, Any]) -> None:
        """Write event as JSONL to log directory."""
        date_str = time.strftime("%Y-%m-%d")
        log_path = Path(self.log_dir) / f"predictions_{date_str}.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")


def _safe_serialize(obj: Any) -> Any:
    """Convert non-JSON-serializable objects to strings."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)
