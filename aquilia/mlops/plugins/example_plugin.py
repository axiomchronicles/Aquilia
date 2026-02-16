"""
Example Aquilia MLOps plugin — demonstrates how to write a plugin.

This plugin adds a simple *model-health-check* hook that prints basic
statistics when the ``post_inference`` event fires.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger("aquilia.mlops.plugins.example")


class HealthCheckPlugin:
    """
    Minimal example plugin implementing the ``PluginHook`` protocol.

    Register this plugin::

        from aquilia.mlops.plugins.host import PluginHost
        from aquilia.mlops.plugins.example_plugin import HealthCheckPlugin

        host = PluginHost()
        host.register(HealthCheckPlugin())
        host.activate("health-check")
    """

    name = "health-check"
    version = "0.1.0"

    def __init__(self) -> None:
        self._start_time: float = 0.0
        self._inference_count: int = 0
        self._total_latency: float = 0.0

    # ── lifecycle ────────────────────────────────────────────────────────

    def activate(self, ctx: Dict[str, Any]) -> None:
        self._start_time = time.monotonic()
        logger.info("[health-check] activated")

        # If a PluginHost reference is in the context, subscribe to events
        host = ctx.get("host")
        if host is not None:
            host.on("post_inference", self._on_inference)

    def deactivate(self) -> None:
        uptime = time.monotonic() - self._start_time
        logger.info(
            "[health-check] deactivated — served %d inferences in %.1fs",
            self._inference_count,
            uptime,
        )

    # ── hooks ────────────────────────────────────────────────────────────

    def _on_inference(self, *, latency_ms: float = 0.0, **kwargs: Any) -> None:
        self._inference_count += 1
        self._total_latency += latency_ms

    # ── utility ──────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        avg = (
            self._total_latency / self._inference_count
            if self._inference_count > 0
            else 0.0
        )
        return {
            "inference_count": self._inference_count,
            "avg_latency_ms": round(avg, 2),
            "uptime_s": round(time.monotonic() - self._start_time, 1),
        }
