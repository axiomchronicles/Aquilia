"""
MLOps Middleware — Inference metrics collection as Aquilia middleware.

Integrates with Aquilia's MiddlewareStack to automatically record
latency, error rates, and request counts for serving endpoints.

Usage::

    from aquilia.mlops.middleware import mlops_metrics_middleware
    stack.use(mlops_metrics_middleware(collector))

Or via DI integration (auto-registered during lifecycle startup).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("aquilia.mlops.middleware")


def mlops_metrics_middleware(
    metrics_collector: Any,
    path_prefix: str = "/mlops",
) -> Callable:
    """
    Create an inference metrics middleware.

    Records request latency, counts, and errors for paths matching
    ``path_prefix``.

    Args:
        metrics_collector: A ``MetricsCollector`` instance.
        path_prefix: URL prefix to match (default ``"/mlops"``).

    Returns:
        An Aquilia-compatible middleware callable.
    """

    async def middleware(request: Any, ctx: Any, next_handler: Callable) -> Any:
        # Only instrument MLOps paths
        path = getattr(request, "path", "")
        if not path.startswith(path_prefix):
            return await next_handler(request, ctx)

        start = time.monotonic()
        error = False

        try:
            response = await next_handler(request, ctx)
            status = getattr(response, "status_code", 200)
            if status >= 400:
                error = True
            return response
        except Exception:
            error = True
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            metrics_collector.record_inference(
                latency_ms=latency_ms,
                batch_size=1,
                error=error,
            )

    return middleware


def mlops_request_id_middleware() -> Callable:
    """
    Middleware that injects a unique request ID into the context.

    Useful for tracing inference requests through the pipeline.
    """
    import uuid

    async def middleware(request: Any, ctx: Any, next_handler: Callable) -> Any:
        rid = str(uuid.uuid4())
        if isinstance(ctx, dict):
            ctx["mlops_request_id"] = rid
        else:
            ctx.mlops_request_id = rid
        return await next_handler(request, ctx)

    return middleware
