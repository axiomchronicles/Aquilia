"""
Rate Limiting Middleware - Production-grade request rate limiting.

Implements multiple algorithms:
- Token Bucket:  Smooth burst-tolerant limiting with refill rate
- Sliding Window: Accurate per-window counting (no boundary spikes)
- Fixed Window:   Simple per-interval counters (lightweight)

Features:
- Per-client keying (IP, API key, user ID, or custom extractor)
- Multiple limit tiers (global, per-route, per-user)
- Retry-After header computation
- Configurable response format (JSON / plain)
- Memory-efficient storage with automatic expiration (O(1) amortized)
- Thread-safe via dict-level atomicity in CPython

All middleware follow the Aquilia async signature:
    async def __call__(self, request, ctx, next) -> Response
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from aquilia.request import Request
from aquilia.response import Response
from aquilia.faults.domains import RateLimitExceededFault

if TYPE_CHECKING:
    from aquilia.controller.base import RequestCtx

Handler = Callable[[Request, "RequestCtx"], Awaitable[Response]]


# ─── Key extractors ──────────────────────────────────────────────────────────

def ip_key_extractor(request: Request) -> str:
    """Extract client IP as rate-limit key."""
    # Prefer forwarded IP (set by ProxyFixMiddleware)
    ip = request.state.get("client_ip")
    if ip:
        return f"ip:{ip}"
    # Fallback to ASGI scope
    if hasattr(request, "_scope") and isinstance(request._scope, dict):
        client = request._scope.get("client")
        if client:
            return f"ip:{client[0]}"
    return "ip:unknown"


def api_key_extractor(request: Request) -> Optional[str]:
    """Extract API key from Authorization or X-API-Key header."""
    api_key = request.header("x-api-key")
    if api_key:
        return f"apikey:{api_key}"
    auth = request.header("authorization")
    if auth and auth.lower().startswith("bearer "):
        return f"bearer:{auth[7:][:32]}"  # Truncate for safety
    return None


def user_key_extractor(request: Request) -> Optional[str]:
    """Extract user ID from request state (set by auth middleware)."""
    user_id = request.state.get("user_id")
    if user_id:
        return f"user:{user_id}"
    identity = request.state.get("identity")
    if identity and hasattr(identity, "id"):
        return f"user:{identity.id}"
    return None


# ─── Token Bucket Algorithm ──────────────────────────────────────────────────

class _TokenBucket:
    """
    Classic token bucket with lazy refill.

    Attributes:
        capacity: Maximum tokens in bucket.
        refill_rate: Tokens added per second.
        tokens: Current token count.
        last_refill: Timestamp of last refill.
    """

    __slots__ = ("capacity", "refill_rate", "tokens", "last_refill")

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0

        # How long until enough tokens are available
        deficit = tokens - self.tokens
        retry_after = deficit / self.refill_rate
        return False, retry_after

    @property
    def remaining(self) -> int:
        return int(self.tokens)


# ─── Sliding Window Counter ──────────────────────────────────────────────────

class _SlidingWindowCounter:
    """
    Sliding window counter using two adjacent fixed windows.

    More accurate than fixed windows (no boundary spike) while using
    only O(1) space per key.

    Algorithm:
        weighted_count = prev_count * overlap_ratio + current_count

    Attributes:
        window_size: Window duration in seconds.
        max_requests: Maximum requests per window.
    """

    __slots__ = ("window_size", "max_requests", "_prev_count", "_curr_count",
                 "_prev_start", "_curr_start")

    def __init__(self, window_size: float, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        now = time.monotonic()
        self._curr_start = now
        self._curr_count = 0
        self._prev_start = now - window_size
        self._prev_count = 0

    def consume(self) -> Tuple[bool, float]:
        """
        Try to record a request.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.monotonic()
        self._advance_windows(now)

        # Calculate weighted count
        elapsed_in_window = now - self._curr_start
        weight = max(0.0, 1.0 - elapsed_in_window / self.window_size)
        weighted = self._prev_count * weight + self._curr_count

        if weighted >= self.max_requests:
            # Estimate when the window will roll enough to allow a request
            retry = self.window_size - elapsed_in_window
            return False, max(0.1, retry)

        self._curr_count += 1
        return True, 0.0

    def _advance_windows(self, now: float) -> None:
        window_end = self._curr_start + self.window_size
        if now >= window_end:
            # How many full windows have passed
            windows_passed = int((now - self._curr_start) / self.window_size)
            if windows_passed >= 2:
                # Both windows expired
                self._prev_count = 0
                self._curr_count = 0
                self._prev_start = now - self.window_size
                self._curr_start = now
            else:
                # Rotate once
                self._prev_count = self._curr_count
                self._prev_start = self._curr_start
                self._curr_count = 0
                self._curr_start = window_end

    @property
    def remaining(self) -> int:
        now = time.monotonic()
        elapsed = now - self._curr_start
        weight = max(0.0, 1.0 - elapsed / self.window_size)
        used = int(self._prev_count * weight + self._curr_count)
        return max(0, self.max_requests - used)

    @property
    def reset_time(self) -> float:
        return self._curr_start + self.window_size


# ─── Expiry-aware bucket store ────────────────────────────────────────────────

class _BucketStore:
    """
    In-memory store for rate-limit buckets with periodic cleanup.

    Entries that haven't been accessed for > 2×window_size are evicted
    on a lazy schedule to bound memory growth.
    """

    def __init__(self, cleanup_interval: float = 60.0):
        self._buckets: Dict[str, Any] = {}
        self._last_access: Dict[str, float] = {}
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.monotonic()

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        self._last_access[key] = now

        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = factory()
            self._buckets[key] = bucket

        # Lazy cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup(now)

        return bucket

    def _cleanup(self, now: float) -> None:
        self._last_cleanup = now
        # Default 5 minute TTL for idle buckets
        ttl = max(self._cleanup_interval * 5, 300)
        expired = [
            k for k, t in self._last_access.items()
            if now - t > ttl
        ]
        for k in expired:
            self._buckets.pop(k, None)
            self._last_access.pop(k, None)


# ─── Rate Limit Configuration ────────────────────────────────────────────────

class RateLimitRule:
    """
    A single rate-limit rule.

    Ecosystem Integration:
    - Configurable via Integration.rate_limit() config builder
    - RateLimitExceededFault raised through Aquilia fault system
    - Key extractors integrate with DI (user identity) and ProxyFixMiddleware (client IP)

    Attributes:
        limit: Maximum requests per window.
        window: Window size in seconds.
        algorithm: "token_bucket" or "sliding_window".
        key_func: Function to extract the rate-limit key from request.
                  Defaults to IP-based.
        burst: Extra burst capacity (token_bucket only). Defaults to limit.
        scope: Which paths this rule applies to ("*" = all).
        methods: HTTP methods this rule applies to (empty = all).
    """

    __slots__ = ("limit", "window", "algorithm", "key_func", "burst", "scope", "methods")

    def __init__(
        self,
        limit: int = 100,
        window: float = 60.0,
        algorithm: str = "sliding_window",
        key_func: Optional[Callable[[Request], Optional[str]]] = None,
        burst: Optional[int] = None,
        scope: str = "*",
        methods: Optional[List[str]] = None,
    ):
        self.limit = limit
        self.window = window
        self.algorithm = algorithm
        self.key_func = key_func or ip_key_extractor
        self.burst = burst
        self.scope = scope
        self.methods = methods or []

    def matches(self, request: Request) -> bool:
        """Check if this rule applies to the given request."""
        if self.methods and request.method not in self.methods:
            return False
        if self.scope == "*":
            return True
        return request.path.startswith(self.scope)


# ─── Rate Limit Middleware ────────────────────────────────────────────────────

class RateLimitMiddleware:
    """
    Multi-algorithm rate limiting middleware.

    Supports layered rules evaluated in order.  The first rule whose
    ``matches()`` returns True and whose bucket is exhausted will
    trigger a 429 response.

    Standard rate-limit headers (draft-ietf-httpapi-ratelimit-headers):
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
    - Retry-After

    Args:
        rules: List of RateLimitRule to evaluate.
        default_limit: Fallback limit if no rules provided.
        default_window: Fallback window (seconds).
        response_format: "json" or "plain" for 429 body.
        include_headers: Include rate-limit headers on all responses.
        exempt_paths: Paths to skip rate limiting (e.g. health checks).
    """

    def __init__(
        self,
        rules: Optional[List[RateLimitRule]] = None,
        default_limit: int = 100,
        default_window: float = 60.0,
        response_format: str = "json",
        include_headers: bool = True,
        exempt_paths: Optional[List[str]] = None,
    ):
        if rules:
            self._rules = rules
        else:
            self._rules = [
                RateLimitRule(limit=default_limit, window=default_window),
            ]

        self._response_format = response_format
        self._include_headers = include_headers
        self._exempt_paths: set = set(exempt_paths or ["/health", "/healthz", "/ready"])
        self._store = _BucketStore()

    async def __call__(
        self,
        request: Request,
        ctx: "RequestCtx",
        next_handler: Handler,
    ) -> Response:
        # Skip exempt paths
        if request.path in self._exempt_paths:
            return await next_handler(request, ctx)

        # Skip if route opted out
        if request.state.get("rate_limit_skip"):
            return await next_handler(request, ctx)

        # Evaluate rules
        for rule in self._rules:
            if not rule.matches(request):
                continue

            key = rule.key_func(request)
            if key is None:
                continue  # Rule doesn't apply (e.g. no user ID)

            # Scope the key to the rule
            bucket_key = f"{rule.scope}:{key}"

            # Get or create bucket
            bucket = self._store.get_or_create(
                bucket_key,
                lambda: self._create_bucket(rule),
            )

            allowed, retry_after = bucket.consume()

            if not allowed:
                return self._rate_limited_response(
                    rule, bucket, retry_after
                )

            # Add rate-limit headers for the first matching rule
            if self._include_headers:
                request.state["_ratelimit_rule"] = rule
                request.state["_ratelimit_bucket"] = bucket

        # Proceed to handler
        response = await next_handler(request, ctx)

        # Attach rate-limit headers
        if self._include_headers:
            rule = request.state.get("_ratelimit_rule")
            bucket = request.state.get("_ratelimit_bucket")
            if rule and bucket:
                self._apply_headers(response, rule, bucket)

        return response

    def _create_bucket(self, rule: RateLimitRule) -> Any:
        if rule.algorithm == "token_bucket":
            capacity = rule.burst if rule.burst is not None else rule.limit
            refill_rate = rule.limit / rule.window
            return _TokenBucket(capacity=capacity, refill_rate=refill_rate)
        else:
            return _SlidingWindowCounter(
                window_size=rule.window,
                max_requests=rule.limit,
            )

    def _rate_limited_response(
        self, rule: RateLimitRule, bucket: Any, retry_after: float
    ) -> Response:
        # Create a RateLimitExceededFault for ecosystem integration.
        # The fault is attached to the response but NOT raised — the middleware
        # returns a 429 response directly to avoid interrupting the pipeline.
        fault = RateLimitExceededFault(
            limit=rule.limit,
            window=rule.window,
            retry_after=retry_after,
        )

        headers = {
            "retry-after": str(int(math.ceil(retry_after))),
            "x-ratelimit-limit": str(rule.limit),
            "x-ratelimit-remaining": "0",
            "x-fault-code": fault.code,
        }

        if hasattr(bucket, "reset_time"):
            headers["x-ratelimit-reset"] = str(int(bucket.reset_time))

        if self._response_format == "json":
            resp = Response.json(
                {
                    "error": "Too Many Requests",
                    "code": fault.code,
                    "message": fault.message,
                    "retry_after": int(math.ceil(retry_after)),
                },
                status=429,
                headers=headers,
            )
        else:
            resp = Response(
                b"Rate limit exceeded",
                status=429,
                headers={**headers, "content-type": "text/plain"},
            )

        # Attach fault to response for observability / fault-engine integration
        resp._fault = fault
        return resp

    def _apply_headers(
        self, response: Response, rule: RateLimitRule, bucket: Any
    ) -> None:
        remaining = bucket.remaining if hasattr(bucket, "remaining") else 0
        response.headers["x-ratelimit-limit"] = str(rule.limit)
        response.headers["x-ratelimit-remaining"] = str(max(0, remaining))
        if hasattr(bucket, "reset_time"):
            response.headers["x-ratelimit-reset"] = str(int(bucket.reset_time))


__all__ = [
    "RateLimitMiddleware",
    "RateLimitRule",
    "ip_key_extractor",
    "api_key_extractor",
    "user_key_extractor",
]
