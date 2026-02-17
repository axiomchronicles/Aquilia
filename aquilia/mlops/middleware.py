"""
MLOps Middleware — Inference metrics, rate limiting, and circuit breaker
integration as Aquilia middleware.

Integrates with Aquilia's :class:`~aquilia.middleware.MiddlewareStack` using
:class:`~aquilia.middleware.MiddlewareDescriptor` for deterministic ordering.
Faults are routed through the :class:`~aquilia.faults.FaultEngine` instead of
bare ``try/except`` blocks.

Usage::

    from aquilia.mlops.middleware import (
        mlops_metrics_middleware,
        mlops_rate_limit_middleware,
        mlops_circuit_breaker_middleware,
        register_mlops_middleware,
    )

    # Register all MLOps middleware with proper scoping:
    register_mlops_middleware(stack, collector, rate_limiter, circuit_breaker)

    # Or individually:
    stack.add(
        mlops_metrics_middleware(collector),
        scope="app:mlops",
        priority=10,
        name="mlops.metrics",
    )

Or via DI integration (auto-registered during lifecycle startup).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

from aquilia.middleware import MiddlewareStack

logger = logging.getLogger("aquilia.mlops.middleware")


def register_mlops_middleware(
    stack: MiddlewareStack,
    metrics_collector: Any = None,
    rate_limiter: Any = None,
    circuit_breaker: Any = None,
    fault_engine: Any = None,
    path_prefix: str = "/mlops",
) -> None:
    """
    Register all MLOps middleware with proper scope and priority
    on an Aquilia :class:`~aquilia.middleware.MiddlewareStack`.

    Uses ``MiddlewareDescriptor`` with ``scope="app:mlops"`` so that
    the middleware only activates for MLOps routes, and ``priority``
    values ensure correct ordering (request-id → rate-limit →
    circuit-breaker → metrics).

    Args:
        stack: Aquilia middleware stack.
        metrics_collector: Optional ``MetricsCollector`` instance.
        rate_limiter: Optional ``TokenBucketRateLimiter`` instance.
        circuit_breaker: Optional ``CircuitBreaker`` instance.
        fault_engine: Optional ``FaultEngine`` for structured error handling.
        path_prefix: URL prefix filter.
    """
    # Outermost — always add request-id
    stack.add(
        mlops_request_id_middleware(),
        scope="app:mlops",
        priority=5,
        name="mlops.request_id",
    )

    if rate_limiter is not None:
        stack.add(
            mlops_rate_limit_middleware(rate_limiter, path_prefix=path_prefix, fault_engine=fault_engine),
            scope="app:mlops",
            priority=10,
            name="mlops.rate_limit",
        )

    if circuit_breaker is not None:
        stack.add(
            mlops_circuit_breaker_middleware(circuit_breaker, fault_engine=fault_engine),
            scope="app:mlops",
            priority=20,
            name="mlops.circuit_breaker",
        )

    if metrics_collector is not None:
        stack.add(
            mlops_metrics_middleware(metrics_collector, path_prefix=path_prefix),
            scope="app:mlops",
            priority=30,
            name="mlops.metrics",
        )


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


def mlops_rate_limit_middleware(
    rate_limiter: Any,
    path_prefix: str = "/mlops",
    status_code: int = 429,
    fault_engine: Any = None,
) -> Callable:
    """
    Rate-limiting middleware using a token-bucket rate limiter.

    When a ``FaultEngine`` is provided, rate-limit violations are routed
    through it as :class:`~aquilia.mlops.faults.RateLimitFault` so that
    fault listeners (metrics, tracing) can observe the event.

    Args:
        rate_limiter: A ``TokenBucketRateLimiter`` instance.
        path_prefix: URL prefix to match.
        status_code: HTTP status code to return when rate-limited.
        fault_engine: Optional Aquilia ``FaultEngine``.
    """

    async def middleware(request: Any, ctx: Any, next_handler: Callable) -> Any:
        path = getattr(request, "path", "")
        if not path.startswith(path_prefix):
            return await next_handler(request, ctx)

        if rate_limiter is None:
            return await next_handler(request, ctx)

        if not rate_limiter.acquire():
            from aquilia.response import Response
            wait_time = rate_limiter.acquire_wait_time()

            # Emit through FaultEngine if available
            if fault_engine is not None:
                try:
                    from .faults import RateLimitFault
                    await fault_engine.process(
                        RateLimitFault(limit_rps=rate_limiter.rate, retry_after=wait_time),
                        app="mlops",
                    )
                except Exception:
                    pass

            return Response(
                {"error": "Rate limit exceeded", "retry_after_seconds": round(wait_time, 2)},
                status=status_code,
                headers={"Retry-After": str(int(wait_time) + 1)},
            )

        return await next_handler(request, ctx)

    return middleware


def mlops_circuit_breaker_middleware(
    circuit_breaker: Any,
    path_prefix: str = "/mlops/predict",
    status_code: int = 503,
    fault_engine: Any = None,
) -> Callable:
    """
    Circuit-breaker middleware for inference endpoints.

    Returns HTTP 503 when the circuit is open (fail-fast).
    Records successes and failures to transition the circuit state.
    Faults are routed through the ``FaultEngine`` when available.

    Args:
        circuit_breaker: A ``CircuitBreaker`` instance.
        path_prefix: URL prefix to protect.
        status_code: HTTP status code to return when circuit is open.
        fault_engine: Optional Aquilia ``FaultEngine``.
    """

    async def middleware(request: Any, ctx: Any, next_handler: Callable) -> Any:
        path = getattr(request, "path", "")
        if not path.startswith(path_prefix):
            return await next_handler(request, ctx)

        if circuit_breaker is None:
            return await next_handler(request, ctx)

        if not circuit_breaker.allow_request():
            from aquilia.response import Response

            # Emit through FaultEngine
            if fault_engine is not None:
                try:
                    from .faults import CircuitBreakerOpenFault
                    await fault_engine.process(
                        CircuitBreakerOpenFault(
                            failure_count=circuit_breaker.failure_count
                            if hasattr(circuit_breaker, "failure_count") else 0,
                        ),
                        app="mlops",
                    )
                except Exception:
                    pass

            return Response(
                {
                    "error": "Service unavailable — circuit breaker open",
                    "circuit_state": circuit_breaker.state,
                },
                status=status_code,
            )

        try:
            response = await next_handler(request, ctx)
            status = getattr(response, "status_code", 200)
            if status < 500:
                circuit_breaker.record_success()
            else:
                circuit_breaker.record_failure()
            return response
        except Exception as exc:
            circuit_breaker.record_failure()
            # Route serving failures through FaultEngine
            if fault_engine is not None:
                try:
                    await fault_engine.process(exc, app="mlops")
                except Exception:
                    pass
            raise

    return middleware
