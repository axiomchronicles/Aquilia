"""
Enhanced Logging Middleware - Structured access logging.

Features:
- Apache/nginx Combined Log Format (CLF) support
- Structured JSON logging (for log aggregation services)
- Request/response timing with microsecond precision
- Configurable log fields and format
- Slow request warning threshold
- Request body size tracking
- User agent and referer logging
- Color-coded terminal output (dev mode)
- Log filtering by path pattern (skip health checks)

Follows the Aquilia async middleware signature:
    async def __call__(self, request, ctx, next) -> Response
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TYPE_CHECKING,
)

from aquilia.request import Request
from aquilia.response import Response

if TYPE_CHECKING:
    from aquilia.controller.base import RequestCtx

Handler = Callable[[Request, "RequestCtx"], Awaitable[Response]]

# ─── ANSI color codes for dev mode ────────────────────────────────────────────

_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "blue": "\033[34m",
    "white": "\033[37m",
}


def _status_color(status: int) -> str:
    """Pick ANSI color for HTTP status code."""
    if status < 300:
        return _COLORS["green"]
    elif status < 400:
        return _COLORS["cyan"]
    elif status < 500:
        return _COLORS["yellow"]
    return _COLORS["red"]


def _method_color(method: str) -> str:
    """Pick ANSI color for HTTP method."""
    mapping = {
        "GET": _COLORS["green"],
        "POST": _COLORS["blue"],
        "PUT": _COLORS["yellow"],
        "PATCH": _COLORS["yellow"],
        "DELETE": _COLORS["red"],
        "OPTIONS": _COLORS["dim"],
        "HEAD": _COLORS["dim"],
    }
    return mapping.get(method, _COLORS["white"])


# ─── Log Format Builders ─────────────────────────────────────────────────────

class _LogFormatter:
    """Pluggable formatter for access log lines."""

    def format_request(
        self,
        *,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        content_length: int,
        client_ip: str,
        user_agent: str,
        referer: str,
        request_id: str,
        extras: Dict[str, Any],
    ) -> str:
        raise NotImplementedError


class CombinedLogFormatter(_LogFormatter):
    """Apache Combined Log Format."""

    def format_request(self, **kwargs: Any) -> str:
        now = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S %z")
        return (
            f'{kwargs["client_ip"]} - - [{now}] '
            f'"{kwargs["method"]} {kwargs["path"]} HTTP/1.1" '
            f'{kwargs["status"]} {kwargs["content_length"]} '
            f'"{kwargs["referer"]}" "{kwargs["user_agent"]}" '
            f'{kwargs["duration_ms"]:.1f}ms'
        )


class StructuredLogFormatter(_LogFormatter):
    """JSON-structured log output."""

    def format_request(self, **kwargs: Any) -> str:
        import json

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": kwargs["method"],
            "path": kwargs["path"],
            "status": kwargs["status"],
            "duration_ms": round(kwargs["duration_ms"], 2),
            "content_length": kwargs["content_length"],
            "client_ip": kwargs["client_ip"],
            "request_id": kwargs["request_id"],
        }
        if kwargs["user_agent"]:
            record["user_agent"] = kwargs["user_agent"]
        if kwargs["referer"]:
            record["referer"] = kwargs["referer"]
        record.update(kwargs.get("extras", {}))
        return json.dumps(record, default=str)


class DevLogFormatter(_LogFormatter):
    """Color-coded developer-friendly format."""

    def format_request(self, **kwargs: Any) -> str:
        m = kwargs["method"]
        s = kwargs["status"]
        mc = _method_color(m)
        sc = _status_color(s)
        r = _COLORS["reset"]
        d = _COLORS["dim"]

        duration = kwargs["duration_ms"]
        if duration > 1000:
            dur_str = f'{_COLORS["red"]}{duration:.0f}ms{r}'
        elif duration > 200:
            dur_str = f'{_COLORS["yellow"]}{duration:.0f}ms{r}'
        else:
            dur_str = f'{d}{duration:.0f}ms{r}'

        return (
            f'{mc}{m:7}{r} {kwargs["path"]:40} '
            f'{sc}{s}{r} {dur_str}'
        )


# ─── Enhanced Logging Middleware ──────────────────────────────────────────────

class LoggingMiddleware:
    """
    Enhanced HTTP access logging middleware.

    Args:
        logger_name: Logger name (default "aquilia.access").
        format: Log format - "combined", "structured", "dev", or custom formatter.
        level: Log level for successful requests.
        error_level: Log level for 5xx responses.
        slow_threshold_ms: Warn on requests slower than this (ms).
        skip_paths: Paths to skip logging (e.g. health checks).
        log_request_body: Log request body size.
        include_headers: List of request headers to include in log.
    """

    def __init__(
        self,
        logger_name: str = "aquilia.access",
        format: str = "dev",
        level: int = logging.INFO,
        error_level: int = logging.ERROR,
        slow_threshold_ms: float = 1000.0,
        skip_paths: Optional[Set[str]] = None,
        log_request_body: bool = False,
        include_headers: Optional[List[str]] = None,
    ):
        self.logger = logging.getLogger(logger_name)
        self._level = level
        self._error_level = error_level
        self._slow_threshold = slow_threshold_ms
        self._skip_paths = skip_paths or {"/health", "/healthz", "/ready", "/favicon.ico"}
        self._log_body = log_request_body
        self._include_headers = include_headers or []

        # Select formatter
        if isinstance(format, str):
            self._formatter = {
                "combined": CombinedLogFormatter,
                "structured": StructuredLogFormatter,
                "dev": DevLogFormatter,
            }.get(format, DevLogFormatter)()
        else:
            self._formatter = format

    async def __call__(
        self,
        request: Request,
        ctx: "RequestCtx",
        next_handler: Handler,
    ) -> Response:
        # Skip filtered paths
        if request.path in self._skip_paths:
            return await next_handler(request, ctx)

        start = time.perf_counter()

        # Process request
        try:
            response = await next_handler(request, ctx)
        except Exception:
            # Log the error and re-raise (ExceptionMiddleware will handle it)
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.error(
                f"{request.method} {request.path} - EXCEPTION ({duration_ms:.1f}ms)",
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        # Collect fields
        client_ip = request.state.get("client_ip", "-")
        if client_ip == "-" and hasattr(request, "_scope") and isinstance(request._scope, dict):
            client = request._scope.get("client")
            if client:
                client_ip = str(client[0])

        extras: Dict[str, Any] = {}
        for header in self._include_headers:
            val = request.header(header)
            if val:
                extras[f"header_{header}"] = val

        content_length = 0
        cl_header = response.headers.get("content-length", "0")
        try:
            content_length = int(cl_header)
        except (ValueError, TypeError):
            pass

        log_line = self._formatter.format_request(
            method=request.method,
            path=request.path,
            status=response.status,
            duration_ms=duration_ms,
            content_length=content_length,
            client_ip=client_ip,
            user_agent=request.header("user-agent") or "-",
            referer=request.header("referer") or "-",
            request_id=getattr(ctx, "request_id", "-"),
            extras=extras,
        )

        # Choose log level
        if response.status >= 500:
            self.logger.log(self._error_level, log_line)
        elif duration_ms > self._slow_threshold:
            self.logger.warning(f"SLOW {log_line}")
        else:
            self.logger.log(self._level, log_line)

        return response


__all__ = [
    "LoggingMiddleware",
    "CombinedLogFormatter",
    "StructuredLogFormatter",
    "DevLogFormatter",
]
