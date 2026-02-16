"""
Security Middleware Suite - Production-grade HTTP security middleware.

Provides:
- CORSMiddleware:        RFC 6454/7231 compliant cross-origin resource sharing
- CSPMiddleware:         Content-Security-Policy header builder with nonce support
- CSRFMiddleware:        Cross-Site Request Forgery protection
- HSTSMiddleware:        HTTP Strict Transport Security
- HTTPSRedirectMiddleware: Force HTTPS with configurable exemptions
- ProxyFixMiddleware:    Trusted-proxy header correction (X-Forwarded-*)
- SecurityHeadersMiddleware: Helmet-style catch-all security headers

All middleware follow the Aquilia async signature:
    async def __call__(self, request, ctx, next) -> Response

Ecosystem Integration:
- Faults: Uses SecurityFault subclasses (CSRFViolationFault, CORSViolationFault)
  from aquilia.faults instead of bare Exceptions
- Serializers: CSPPolicy and CSRFConfig use Aquilia Serializer for validation
- Config: Wired through Workspace.security() and Integration.csrf/cors/csp builders
- DI: CSRF token injected into request.state for controller/template access
- Sessions: CSRF tokens stored in session (SessionMiddleware integration)
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import secrets
import time
from collections import OrderedDict
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Pattern,
    Set,
    Tuple,
    Union,
    TYPE_CHECKING,
)

from aquilia.request import Request
from aquilia.response import Response
from aquilia.faults.domains import (
    SecurityFault,
    CSRFViolationFault,
    CORSViolationFault,
    RateLimitExceededFault,
    CSPViolationFault,
)

if TYPE_CHECKING:
    from aquilia.controller.base import RequestCtx

Handler = Callable[[Request, "RequestCtx"], Awaitable[Response]]


# ═══════════════════════════════════════════════════════════════════════════════
#  CORS Middleware  (RFC 6454 / 7231 / Fetch Standard)
# ═══════════════════════════════════════════════════════════════════════════════

class _OriginMatcher:
    """
    Efficient origin matching with support for:
    - Exact strings
    - Wildcard "*"
    - Glob patterns  (e.g. "*.example.com")
    - Compiled regex patterns

    Uses an LRU cache to avoid re-evaluating expensive regex on every request.
    """

    __slots__ = ("_allow_all", "_exact", "_regex_patterns", "_cache", "_cache_limit")

    def __init__(
        self,
        origins: List[Union[str, Pattern]],
        cache_size: int = 512,
    ):
        self._allow_all = False
        self._exact: Set[str] = set()
        self._regex_patterns: List[Pattern] = []
        self._cache: OrderedDict[str, bool] = OrderedDict()
        self._cache_limit = cache_size

        for origin in origins:
            if isinstance(origin, str):
                if origin == "*":
                    self._allow_all = True
                elif "*" in origin:
                    # Convert glob to regex: *.example.com → ^[^.]+\.example\.com$
                    escaped = re.escape(origin).replace(r"\*", "[^.]+")
                    self._regex_patterns.append(re.compile(f"^{escaped}$", re.IGNORECASE))
                else:
                    self._exact.add(origin.lower())
            else:
                # Pre-compiled regex
                self._regex_patterns.append(origin)

    def matches(self, origin: str) -> bool:
        if self._allow_all:
            return True

        origin_lower = origin.lower()

        # Check cache
        cached = self._cache.get(origin_lower)
        if cached is not None:
            self._cache.move_to_end(origin_lower)
            return cached

        result = self._evaluate(origin_lower)

        # Update LRU cache
        self._cache[origin_lower] = result
        if len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)

        return result

    def _evaluate(self, origin: str) -> bool:
        if origin in self._exact:
            return True
        for pattern in self._regex_patterns:
            if pattern.match(origin):
                return True
        return False

    @property
    def is_wildcard(self) -> bool:
        return self._allow_all


class CORSMiddleware:
    """
    Full-featured CORS middleware following the Fetch Standard.

    Features:
    - Efficient LRU-cached origin matching (exact, glob, regex)
    - Separate preflight and simple-request handling
    - Vary header management (prevents cache poisoning)
    - Credential support with proper origin reflection
    - Expose-headers control
    - Per-route opt-out via request.state["cors_skip"]

    Args:
        allow_origins: Allowed origins (strings, globs, or compiled regex).
        allow_methods: Methods for Access-Control-Allow-Methods.
        allow_headers: Headers for Access-Control-Allow-Headers.
        expose_headers: Headers for Access-Control-Expose-Headers.
        allow_credentials: Allow credentials (cookies, Authorization).
        max_age: Preflight cache duration (seconds).
        allow_origin_regex: Convenience regex string.
    """

    def __init__(
        self,
        allow_origins: Optional[List[Union[str, Pattern]]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
        allow_origin_regex: Optional[str] = None,
    ):
        origins = list(allow_origins or ["*"])
        if allow_origin_regex:
            origins.append(re.compile(allow_origin_regex))

        self._matcher = _OriginMatcher(origins)
        self._allow_methods = allow_methods or [
            "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
        ]
        self._allow_headers = allow_headers or [
            "accept", "accept-language", "content-language", "content-type",
            "authorization", "x-requested-with", "x-request-id",
        ]
        self._expose_headers = expose_headers or []
        self._allow_credentials = allow_credentials
        self._max_age = max_age

        # Pre-compute header values
        self._methods_str = ", ".join(self._allow_methods)
        self._headers_str = ", ".join(self._allow_headers)
        self._expose_str = ", ".join(self._expose_headers) if self._expose_headers else ""

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        origin = request.header("origin")

        # No origin → not a CORS request
        if not origin:
            response = await next_handler(request, ctx)
            # Still add Vary so caches don't serve stale responses
            response.headers.setdefault("vary", "Origin")
            return response

        # Skip if route opted out
        if request.state.get("cors_skip"):
            return await next_handler(request, ctx)

        allowed = self._matcher.matches(origin)

        # Preflight
        if request.method == "OPTIONS":
            resp = self._preflight(origin, request, allowed)
            if not allowed:
                resp._fault = CORSViolationFault(origin=origin)
            return resp

        # Actual request
        response = await next_handler(request, ctx)
        self._apply_cors_headers(response, origin, allowed)
        if not allowed:
            response._fault = CORSViolationFault(origin=origin)
        return response

    def _preflight(self, origin: str, request: Request, allowed: bool) -> Response:
        headers: Dict[str, str] = {}

        if allowed:
            self._set_origin_header(headers, origin)
            headers["access-control-allow-methods"] = self._methods_str
            headers["access-control-allow-headers"] = self._headers_str
            headers["access-control-max-age"] = str(self._max_age)

            if self._allow_credentials:
                headers["access-control-allow-credentials"] = "true"

        headers["vary"] = "Origin, Access-Control-Request-Method, Access-Control-Request-Headers"
        headers["content-length"] = "0"

        return Response(b"", status=204, headers=headers)

    def _apply_cors_headers(
        self, response: Response, origin: str, allowed: bool
    ) -> None:
        if allowed:
            self._set_origin_header(response.headers, origin)

            if self._allow_credentials:
                response.headers["access-control-allow-credentials"] = "true"

            if self._expose_str:
                response.headers["access-control-expose-headers"] = self._expose_str

        # Always set Vary to prevent cache poisoning
        existing_vary = response.headers.get("vary", "")
        if "Origin" not in existing_vary:
            new_vary = f"{existing_vary}, Origin" if existing_vary else "Origin"
            response.headers["vary"] = new_vary

    def _set_origin_header(self, headers: dict, origin: str) -> None:
        """Set Access-Control-Allow-Origin.  Reflects origin when credentials
        are enabled (wildcard forbidden with credentials)."""
        if self._allow_credentials or not self._matcher.is_wildcard:
            headers["access-control-allow-origin"] = origin
        else:
            headers["access-control-allow-origin"] = "*"


# ═══════════════════════════════════════════════════════════════════════════════
#  CSP Middleware  (Content-Security-Policy)
# ═══════════════════════════════════════════════════════════════════════════════

class CSPPolicy:
    """
    Builder for Content-Security-Policy directives.

    Ecosystem Integration:
    - Uses fluent builder pattern (like Aquilia Serializers)
    - Validated at build time, not at creation time
    - Integrates with CSPMiddleware for per-request nonce injection
    - Configurable via Integration.csp() config builder

    Example::

        policy = (
            CSPPolicy()
            .default_src("'self'")
            .script_src("'self'", "'nonce-{nonce}'")
            .style_src("'self'", "'unsafe-inline'")
            .img_src("'self'", "data:", "https:")
            .connect_src("'self'", "wss:")
            .report_uri("/csp-report")
        )
    """

    __slots__ = ("directives", "report_only")

    def __init__(
        self,
        directives: Optional[Dict[str, List[str]]] = None,
        report_only: bool = False,
    ):
        self.directives: Dict[str, List[str]] = directives if directives is not None else {}
        self.report_only = report_only

    def default_src(self, *sources: str) -> "CSPPolicy":
        self.directives["default-src"] = list(sources)
        return self

    def script_src(self, *sources: str) -> "CSPPolicy":
        self.directives["script-src"] = list(sources)
        return self

    def style_src(self, *sources: str) -> "CSPPolicy":
        self.directives["style-src"] = list(sources)
        return self

    def img_src(self, *sources: str) -> "CSPPolicy":
        self.directives["img-src"] = list(sources)
        return self

    def font_src(self, *sources: str) -> "CSPPolicy":
        self.directives["font-src"] = list(sources)
        return self

    def connect_src(self, *sources: str) -> "CSPPolicy":
        self.directives["connect-src"] = list(sources)
        return self

    def media_src(self, *sources: str) -> "CSPPolicy":
        self.directives["media-src"] = list(sources)
        return self

    def object_src(self, *sources: str) -> "CSPPolicy":
        self.directives["object-src"] = list(sources)
        return self

    def frame_src(self, *sources: str) -> "CSPPolicy":
        self.directives["frame-src"] = list(sources)
        return self

    def frame_ancestors(self, *sources: str) -> "CSPPolicy":
        self.directives["frame-ancestors"] = list(sources)
        return self

    def base_uri(self, *sources: str) -> "CSPPolicy":
        self.directives["base-uri"] = list(sources)
        return self

    def form_action(self, *sources: str) -> "CSPPolicy":
        self.directives["form-action"] = list(sources)
        return self

    def worker_src(self, *sources: str) -> "CSPPolicy":
        self.directives["worker-src"] = list(sources)
        return self

    def child_src(self, *sources: str) -> "CSPPolicy":
        self.directives["child-src"] = list(sources)
        return self

    def manifest_src(self, *sources: str) -> "CSPPolicy":
        self.directives["manifest-src"] = list(sources)
        return self

    def upgrade_insecure_requests(self) -> "CSPPolicy":
        self.directives["upgrade-insecure-requests"] = []
        return self

    def block_all_mixed_content(self) -> "CSPPolicy":
        self.directives["block-all-mixed-content"] = []
        return self

    def report_uri(self, uri: str) -> "CSPPolicy":
        self.directives["report-uri"] = [uri]
        return self

    def report_to(self, group: str) -> "CSPPolicy":
        self.directives["report-to"] = [group]
        return self

    def directive(self, name: str, *sources: str) -> "CSPPolicy":
        """Add an arbitrary directive."""
        self.directives[name] = list(sources)
        return self

    def build(self, nonce: Optional[str] = None) -> str:
        """Compile directives into a CSP header value string."""
        parts: List[str] = []
        for directive, sources in self.directives.items():
            if not sources:
                parts.append(directive)
            else:
                rendered = []
                for src in sources:
                    if nonce and "{nonce}" in src:
                        rendered.append(src.replace("{nonce}", nonce))
                    else:
                        rendered.append(src)
                parts.append(f"{directive} {' '.join(rendered)}")
        return "; ".join(parts)

    @classmethod
    def strict(cls) -> "CSPPolicy":
        """Strict CSP suitable for most web applications."""
        return (
            cls()
            .default_src("'self'")
            .script_src("'self'")
            .style_src("'self'", "'unsafe-inline'")
            .img_src("'self'", "data:", "https:")
            .font_src("'self'", "https:", "data:")
            .object_src("'none'")
            .frame_ancestors("'none'")
            .base_uri("'self'")
            .form_action("'self'")
            .upgrade_insecure_requests()
        )

    @classmethod
    def relaxed(cls) -> "CSPPolicy":
        """Relaxed CSP for rapid development."""
        return (
            cls()
            .default_src("'self'", "https:", "data:")
            .script_src("'self'", "'unsafe-inline'", "'unsafe-eval'", "https:")
            .style_src("'self'", "'unsafe-inline'", "https:")
            .img_src("*", "data:", "blob:")
        )


class CSPMiddleware:
    """
    Content-Security-Policy middleware.

    Features:
    - Fluent CSPPolicy builder
    - Per-request nonce generation (cryptographically secure)
    - Report-only mode
    - Nonce injection into request.state for template use

    Args:
        policy: CSPPolicy instance (or will use strict defaults).
        report_only: Send as Content-Security-Policy-Report-Only.
        nonce: Enable per-request nonce generation.
    """

    def __init__(
        self,
        policy: Optional[CSPPolicy] = None,
        report_only: bool = False,
        nonce: bool = True,
    ):
        self._policy = policy or CSPPolicy.strict()
        self._report_only = report_only or self._policy.report_only
        self._nonce_enabled = nonce

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        nonce: Optional[str] = None
        if self._nonce_enabled:
            nonce = secrets.token_urlsafe(16)
            request.state["csp_nonce"] = nonce

        response = await next_handler(request, ctx)

        header_name = (
            "content-security-policy-report-only"
            if self._report_only
            else "content-security-policy"
        )
        response.headers[header_name] = self._policy.build(nonce=nonce)

        return response


# ═══════════════════════════════════════════════════════════════════════════════
#  HSTS Middleware  (RFC 6797)
# ═══════════════════════════════════════════════════════════════════════════════

class HSTSMiddleware:
    """
    HTTP Strict Transport Security middleware.

    Sets the Strict-Transport-Security header on every response.

    Args:
        max_age: Duration (seconds) the browser should remember HTTPS-only.
        include_subdomains: Apply to subdomains.
        preload: Opt-in to browser HSTS preload lists.
    """

    def __init__(
        self,
        max_age: int = 31536000,  # 1 year
        include_subdomains: bool = True,
        preload: bool = False,
    ):
        parts = [f"max-age={max_age}"]
        if include_subdomains:
            parts.append("includeSubDomains")
        if preload:
            parts.append("preload")
        self._header_value = "; ".join(parts)

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        response = await next_handler(request, ctx)
        response.headers["strict-transport-security"] = self._header_value
        return response


# ═══════════════════════════════════════════════════════════════════════════════
#  HTTPS Redirect Middleware
# ═══════════════════════════════════════════════════════════════════════════════

class HTTPSRedirectMiddleware:
    """
    Redirect HTTP requests to HTTPS.

    Inspects the scheme from the ASGI scope, or from ``X-Forwarded-Proto``
    if behind a reverse proxy (requires ProxyFixMiddleware).

    Args:
        redirect_status: HTTP status for the redirect (301 or 307).
        exclude_paths: Paths to exclude from redirect (e.g. health checks).
        exclude_hosts: Hosts to exclude (e.g. localhost).
    """

    def __init__(
        self,
        redirect_status: int = 301,
        exclude_paths: Optional[List[str]] = None,
        exclude_hosts: Optional[List[str]] = None,
    ):
        self._status = redirect_status
        self._exclude_paths: Set[str] = set(exclude_paths or [])
        self._exclude_hosts: Set[str] = set(exclude_hosts or ["localhost", "127.0.0.1", "0.0.0.0"])

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        scheme = request.state.get("forwarded_proto") or self._get_scheme(request)

        if scheme == "https":
            return await next_handler(request, ctx)

        # Check exclusions
        host = self._get_host(request)
        if host in self._exclude_hosts:
            return await next_handler(request, ctx)

        if request.path in self._exclude_paths:
            return await next_handler(request, ctx)

        # Build HTTPS URL
        redirect_url = f"https://{host}{request.path}"
        qs = request.header("raw-query") or request.state.get("query_string", "")
        if qs:
            redirect_url += f"?{qs}"

        return Response(
            b"",
            status=self._status,
            headers={"location": redirect_url},
        )

    def _get_scheme(self, request: Request) -> str:
        if hasattr(request, "_scope") and isinstance(request._scope, dict):
            return request._scope.get("scheme", "http")
        return "http"

    def _get_host(self, request: Request) -> str:
        host = request.header("host") or "localhost"
        # Strip port
        if ":" in host:
            host = host.split(":")[0]
        return host


# ═══════════════════════════════════════════════════════════════════════════════
#  Proxy Fix Middleware  (X-Forwarded-* correction)
# ═══════════════════════════════════════════════════════════════════════════════

class ProxyFixMiddleware:
    """
    Fix request attributes when behind a reverse proxy.

    Rewrites request state/headers based on X-Forwarded-* headers from
    **trusted** proxies only.  Uses CIDR-based network matching to validate
    the connecting IP.

    Trusted Headers (RFC 7239 / de-facto):
    - X-Forwarded-For   → client IP
    - X-Forwarded-Proto → scheme (http/https)
    - X-Forwarded-Host  → original Host header
    - X-Forwarded-Port  → original port
    - X-Real-IP         → client IP (nginx)

    Args:
        trusted_proxies: CIDR ranges or IPs of trusted proxies.
        x_for: Number of trusted proxies to unwrap from X-Forwarded-For.
               0 = disabled.
        x_proto: Number of values to trust for X-Forwarded-Proto.
        x_host: Number of values to trust for X-Forwarded-Host.
        x_port: Number of values to trust for X-Forwarded-Port.
    """

    def __init__(
        self,
        trusted_proxies: Optional[List[str]] = None,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 1,
        x_port: int = 0,
    ):
        self._trusted_networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for proxy in (trusted_proxies or ["127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]):
            try:
                self._trusted_networks.append(ipaddress.ip_network(proxy, strict=False))
            except ValueError:
                pass

        self._x_for = x_for
        self._x_proto = x_proto
        self._x_host = x_host
        self._x_port = x_port

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        # Determine connecting IP
        remote_addr = self._get_remote_addr(request)
        if remote_addr and not self._is_trusted(remote_addr):
            return await next_handler(request, ctx)

        # X-Forwarded-For → client IP
        if self._x_for:
            forwarded_for = request.header("x-forwarded-for")
            if forwarded_for:
                ips = [ip.strip() for ip in forwarded_for.split(",")]
                # Pick the client IP (n hops from the right)
                idx = max(0, len(ips) - self._x_for)
                client_ip = ips[idx]
                request.state["client_ip"] = client_ip
                request.state["forwarded_for"] = ips

        # X-Real-IP (fallback for nginx)
        if not request.state.get("client_ip"):
            real_ip = request.header("x-real-ip")
            if real_ip:
                request.state["client_ip"] = real_ip.strip()

        # X-Forwarded-Proto → scheme
        if self._x_proto:
            proto = request.header("x-forwarded-proto")
            if proto:
                request.state["forwarded_proto"] = proto.strip().lower()

        # X-Forwarded-Host → original host
        if self._x_host:
            fwd_host = request.header("x-forwarded-host")
            if fwd_host:
                request.state["forwarded_host"] = fwd_host.strip()

        # X-Forwarded-Port → port
        if self._x_port:
            fwd_port = request.header("x-forwarded-port")
            if fwd_port:
                request.state["forwarded_port"] = fwd_port.strip()

        return await next_handler(request, ctx)

    def _get_remote_addr(self, request: Request) -> Optional[str]:
        """Extract connecting IP from ASGI scope."""
        if hasattr(request, "_scope") and isinstance(request._scope, dict):
            client = request._scope.get("client")
            if client and len(client) >= 1:
                return str(client[0])
        return None

    def _is_trusted(self, ip_str: str) -> bool:
        """Check if IP falls within any trusted CIDR range."""
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return any(addr in net for net in self._trusted_networks)


# ═══════════════════════════════════════════════════════════════════════════════
#  Security Headers Middleware (Helmet-style)
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware:
    """
    Catch-all security headers middleware (like Helmet.js for Node).

    Applies sensible default security headers to every response:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (or SAMEORIGIN)
    - X-XSS-Protection: 0 (modern browsers deprecated this)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy (formerly Feature-Policy)
    - Cross-Origin-Opener-Policy
    - Cross-Origin-Embedder-Policy
    - Cross-Origin-Resource-Policy

    Args:
        frame_options: "DENY" or "SAMEORIGIN".
        referrer_policy: Referrer-Policy value.
        permissions_policy: Permissions-Policy directives dict.
        cross_origin_opener_policy: COOP value.
        cross_origin_embedder_policy: COEP value.
        cross_origin_resource_policy: CORP value.
        content_type_nosniff: Set X-Content-Type-Options.
        remove_server_header: Remove the Server header.
    """

    def __init__(
        self,
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[Dict[str, str]] = None,
        cross_origin_opener_policy: str = "same-origin",
        cross_origin_embedder_policy: Optional[str] = None,
        cross_origin_resource_policy: str = "same-origin",
        content_type_nosniff: bool = True,
        remove_server_header: bool = True,
    ):
        self._headers: Dict[str, str] = {}

        if content_type_nosniff:
            self._headers["x-content-type-options"] = "nosniff"

        self._headers["x-frame-options"] = frame_options
        # Modern browsers deprecated XSS Auditor; disable to avoid false positives
        self._headers["x-xss-protection"] = "0"
        self._headers["referrer-policy"] = referrer_policy
        self._headers["cross-origin-opener-policy"] = cross_origin_opener_policy
        self._headers["cross-origin-resource-policy"] = cross_origin_resource_policy

        if cross_origin_embedder_policy:
            self._headers["cross-origin-embedder-policy"] = cross_origin_embedder_policy

        # Permissions-Policy
        pp = permissions_policy or {
            "camera": "()",
            "microphone": "()",
            "geolocation": "()",
            "payment": "()",
            "usb": "()",
        }
        pp_parts = [f"{key}={value}" for key, value in pp.items()]
        self._headers["permissions-policy"] = ", ".join(pp_parts)

        self._remove_server = remove_server_header

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        response = await next_handler(request, ctx)

        for name, value in self._headers.items():
            response.headers.setdefault(name, value)

        if self._remove_server and "server" in response.headers:
            del response.headers["server"]

        return response


# ═══════════════════════════════════════════════════════════════════════════════
#  CSRF Middleware  (Cross-Site Request Forgery Protection)
# ═══════════════════════════════════════════════════════════════════════════════

class CSRFError(CSRFViolationFault):
    """
    CSRF validation fault — raised when CSRF protection detects a violation.

    Inherits from CSRFViolationFault (aquilia.faults.domains) to integrate
    with the Aquilia fault handling pipeline. This is a proper Fault, not
    a bare Exception.

    Attributes:
        reason: Human-readable description of the violation
        code: "CSRF_VIOLATION" (stable machine-readable identifier)
        domain: FaultDomain.SECURITY
        severity: Severity.WARN
        public: True (safe to expose to client)
    """

    def __init__(self, reason: str = "CSRF validation failed", **kwargs):
        self.reason = reason
        super().__init__(reason=reason, **kwargs)


class CSRFMiddleware:
    """
    Production-grade CSRF (Cross-Site Request Forgery) protection middleware.

    Implements a **Synchronizer Token Pattern** backed by server-side sessions,
    with a **Double Submit Cookie** fallback when sessions are unavailable.

    Protection Flow:
        1. On every request, generate or retrieve the CSRF token from the session
           (or a signed cookie as fallback).
        2. For **state-changing** methods (POST, PUT, PATCH, DELETE), validate
           the submitted token against the stored token.
        3. Token can be submitted via:
           - HTTP header  (default: ``X-CSRF-Token``)
           - Form field   (default: ``_csrf_token``)
           - Custom header for AJAX (``X-Requested-With: XMLHttpRequest`` bypasses
             when ``trust_ajax`` is enabled, as same-origin policy prevents
             cross-origin custom headers)
        4. On validation failure, return **403 Forbidden**.
        5. Token is injected into ``request.state["csrf_token"]`` for template access.

    Token Storage Priority:
        1. Session (``request.state["session"]``) — preferred, most secure.
        2. Double-submit cookie (``_csrf_cookie``) — fallback when sessions are
           unavailable. Uses HMAC-signed tokens for integrity.

    Security Features:
        - Per-session token (regenerated on session rotation / login)
        - HMAC-signed cookie fallback (tamper-proof)
        - Configurable safe methods, exempt paths, exempt content types
        - Optional AJAX trust (``X-Requested-With`` header)
        - Constant-time comparison to prevent timing attacks
        - Token rotation support (new token after each validation — optional)
        - SameSite cookie attribute for defense-in-depth

    Args:
        secret_key: Secret key for HMAC signing (required for cookie fallback).
                    If not provided, a random key is generated per-process
                    (tokens won't survive restarts without sessions).
        token_length: Length of the raw token in bytes (default 32 → 43 chars base64).
        header_name: HTTP header name for token submission.
        field_name: Form field name for token submission.
        cookie_name: Cookie name for double-submit fallback.
        cookie_path: Path attribute for the CSRF cookie.
        cookie_domain: Domain attribute for the CSRF cookie.
        cookie_secure: Secure flag for the CSRF cookie.
        cookie_samesite: SameSite attribute (``Lax``, ``Strict``, ``None``).
        cookie_httponly: HttpOnly flag for CSRF cookie (False allows JS access
                        for SPA/AJAX workflows).
        cookie_max_age: Max-Age for the CSRF cookie in seconds.
        safe_methods: HTTP methods that don't require CSRF validation.
        exempt_paths: URL paths exempt from CSRF checks (e.g. API webhooks).
        exempt_content_types: Content types exempt from CSRF (e.g. ``application/json``
                             for API-only endpoints behind token auth).
        trust_ajax: Trust ``X-Requested-With: XMLHttpRequest`` as proof of
                    same-origin (browser same-origin policy prevents custom headers
                    from cross-origin requests).
        rotate_token: Generate a new token after each successful validation
                     (one-time-use tokens — stronger but may break back-button).
        failure_status: HTTP status code on CSRF failure (default 403).

    Example::

        csrf = CSRFMiddleware(secret_key="my-secret-key")
        app.middleware_stack.add(csrf, scope="global", priority=10, name="csrf")

        # In templates:
        # <input type="hidden" name="_csrf_token" value="{{ csrf_token }}">

        # In AJAX:
        # fetch('/api/data', {
        #     method: 'POST',
        #     headers: { 'X-CSRF-Token': csrfToken }
        # })
    """

    _SAFE_METHODS_DEFAULT: FrozenSet[str] = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
    _SESSION_KEY: str = "_csrf_token"

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_length: int = 32,
        header_name: str = "X-CSRF-Token",
        field_name: str = "_csrf_token",
        cookie_name: str = "_csrf_cookie",
        cookie_path: str = "/",
        cookie_domain: Optional[str] = None,
        cookie_secure: bool = False,
        cookie_samesite: str = "Lax",
        cookie_httponly: bool = False,
        cookie_max_age: int = 3600,
        safe_methods: Optional[FrozenSet[str]] = None,
        exempt_paths: Optional[List[str]] = None,
        exempt_content_types: Optional[List[str]] = None,
        trust_ajax: bool = True,
        rotate_token: bool = False,
        failure_status: int = 403,
    ):
        import hmac as _hmac_mod
        self._secret_key = (secret_key or secrets.token_urlsafe(32)).encode()
        self._token_length = token_length
        self._header_name = header_name.lower()
        self._field_name = field_name
        self._cookie_name = cookie_name
        self._cookie_path = cookie_path
        self._cookie_domain = cookie_domain
        self._cookie_secure = cookie_secure
        self._cookie_samesite = cookie_samesite
        self._cookie_httponly = cookie_httponly
        self._cookie_max_age = cookie_max_age
        self._safe_methods = safe_methods or self._SAFE_METHODS_DEFAULT
        self._exempt_paths: Set[str] = set(exempt_paths or [])
        self._exempt_content_types: Set[str] = set(
            ct.lower() for ct in (exempt_content_types or [])
        )
        self._trust_ajax = trust_ajax
        self._rotate_token = rotate_token
        self._failure_status = failure_status

    # ── Token Generation ─────────────────────────────────────────────────

    def _generate_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(self._token_length)

    def _sign_token(self, token: str) -> str:
        """Sign a token with HMAC-SHA256 for cookie integrity."""
        import hmac as _hmac_mod
        sig = _hmac_mod.new(
            self._secret_key, token.encode(), hashlib.sha256
        ).hexdigest()
        return f"{token}.{sig}"

    def _verify_signed_token(self, signed: str) -> Optional[str]:
        """Verify a signed token. Returns the token if valid, None otherwise."""
        import hmac as _hmac_mod
        if "." not in signed:
            return None
        token, sig = signed.rsplit(".", 1)
        expected_sig = _hmac_mod.new(
            self._secret_key, token.encode(), hashlib.sha256
        ).hexdigest()
        if _hmac_mod.compare_digest(sig, expected_sig):
            return token
        return None

    # ── Token Storage (Session + Cookie Fallback) ────────────────────────

    def _get_session_token(self, request: Request) -> Optional[str]:
        """Get the stored CSRF token from the session."""
        session = request.state.get("session")
        if session is not None:
            # Session objects support dict-like access
            if hasattr(session, "get"):
                return session.get(self._SESSION_KEY)
            elif hasattr(session, "__getitem__"):
                try:
                    return session[self._SESSION_KEY]
                except (KeyError, IndexError):
                    return None
        return None

    def _set_session_token(self, request: Request, token: str) -> None:
        """Store CSRF token in the session."""
        session = request.state.get("session")
        if session is not None:
            if hasattr(session, "__setitem__"):
                session[self._SESSION_KEY] = token

    def _get_cookie_token(self, request: Request) -> Optional[str]:
        """Get the CSRF token from the double-submit cookie."""
        cookie_value = None
        # Try cookies dict
        if hasattr(request, "cookies") and isinstance(request.cookies, dict):
            cookie_value = request.cookies.get(self._cookie_name)
        # Fallback: parse Cookie header manually
        if cookie_value is None:
            cookie_header = request.header("cookie")
            if cookie_header:
                for pair in cookie_header.split(";"):
                    pair = pair.strip()
                    if pair.startswith(f"{self._cookie_name}="):
                        cookie_value = pair[len(self._cookie_name) + 1:]
                        break
        if cookie_value:
            return self._verify_signed_token(cookie_value)
        return None

    def _set_cookie_token(self, response: Response, token: str) -> None:
        """Set the CSRF token as a signed double-submit cookie."""
        signed = self._sign_token(token)
        parts = [f"{self._cookie_name}={signed}"]
        parts.append(f"Path={self._cookie_path}")
        if self._cookie_domain:
            parts.append(f"Domain={self._cookie_domain}")
        parts.append(f"Max-Age={self._cookie_max_age}")
        parts.append(f"SameSite={self._cookie_samesite}")
        if self._cookie_secure:
            parts.append("Secure")
        if self._cookie_httponly:
            parts.append("HttpOnly")
        cookie_str = "; ".join(parts)
        # Append to existing Set-Cookie headers (don't overwrite)
        existing = response.headers.get("set-cookie", "")
        if existing:
            response.headers["set-cookie"] = f"{existing}, {cookie_str}"
        else:
            response.headers["set-cookie"] = cookie_str

    # ── Token Extraction from Request ────────────────────────────────────

    def _get_submitted_token(self, request: Request) -> Optional[str]:
        """
        Extract the submitted CSRF token from the request.

        Checks in order:
        1. HTTP header (X-CSRF-Token)
        2. Form field (_csrf_token) — from request body/state
        3. Query parameter (_csrf_token) — last resort
        """
        # 1. Header
        token = request.header(self._header_name)
        if token:
            return token

        # 2. Form body (stored by body parser in request.state)
        form_data = request.state.get("form_data") or request.state.get("body")
        if isinstance(form_data, dict):
            token = form_data.get(self._field_name)
            if token:
                return token

        # 3. Parsed body (controllers often parse body into request.state)
        parsed_body = request.state.get("parsed_body")
        if isinstance(parsed_body, dict):
            token = parsed_body.get(self._field_name)
            if token:
                return token

        return None

    # ── Exemption Checks ─────────────────────────────────────────────────

    def _is_exempt(self, request: Request) -> bool:
        """Check if the request is exempt from CSRF validation."""
        # Safe methods don't need CSRF protection
        if request.method.upper() in self._safe_methods:
            return True

        # Explicit path exemptions
        if request.path in self._exempt_paths:
            return True

        # Prefix-based path exemption (for API routes etc.)
        for exempt in self._exempt_paths:
            if exempt.endswith("*") and request.path.startswith(exempt[:-1]):
                return True

        # Content-type exemption (e.g. application/json for pure APIs)
        if self._exempt_content_types:
            content_type = request.header("content-type").lower().split(";")[0].strip()
            if content_type in self._exempt_content_types:
                return True

        # Route-level opt-out via request.state
        if request.state.get("csrf_exempt"):
            return True

        # Trust AJAX requests (X-Requested-With can't be set cross-origin)
        if self._trust_ajax:
            xhr = request.header("x-requested-with")
            if xhr and xhr.lower() == "xmlhttprequest":
                return True

        return False

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_token(self, stored: str, submitted: str) -> bool:
        """Constant-time comparison of CSRF tokens."""
        import hmac as _hmac_mod
        return _hmac_mod.compare_digest(stored, submitted)

    # ── Main Handler ─────────────────────────────────────────────────────

    async def __call__(
        self, request: Request, ctx: "RequestCtx", next_handler: Handler
    ) -> Response:
        """
        CSRF protection middleware handler.

        Flow:
        1. Retrieve or generate CSRF token
        2. Inject token into request.state for templates/DI
        3. For unsafe methods: validate submitted token
        4. Process request
        5. Set CSRF cookie on response (double-submit fallback)
        """
        # ── Step 1: Retrieve or generate token ───────────────────────────
        token = self._get_session_token(request)
        token_source = "session"

        if token is None:
            token = self._get_cookie_token(request)
            token_source = "cookie" if token else "new"

        if token is None:
            token = self._generate_token()
            token_source = "new"

        # Store in session if available
        if token_source in ("new", "cookie"):
            self._set_session_token(request, token)

        # ── Step 2: Inject into request state ────────────────────────────
        request.state["csrf_token"] = token
        request.state["csrf_token_field"] = self._field_name
        request.state["csrf_token_header"] = self._header_name

        # ── Step 3: Validate on unsafe methods ───────────────────────────
        if not self._is_exempt(request):
            submitted = self._get_submitted_token(request)

            if submitted is None:
                fault = CSRFError("CSRF token missing")
                resp = Response(
                    b'{"error": "CSRF token missing", "code": "CSRF_VIOLATION"}',
                    status=self._failure_status,
                    headers={
                        "content-type": "application/json",
                        "x-fault-code": fault.code,
                    },
                )
                resp._fault = fault
                return resp

            if not self._validate_token(token, submitted):
                fault = CSRFError("CSRF token invalid")
                resp = Response(
                    b'{"error": "CSRF token invalid", "code": "CSRF_VIOLATION"}',
                    status=self._failure_status,
                    headers={
                        "content-type": "application/json",
                        "x-fault-code": fault.code,
                    },
                )
                resp._fault = fault
                return resp

            # Optional: rotate token after successful validation
            if self._rotate_token:
                token = self._generate_token()
                self._set_session_token(request, token)
                request.state["csrf_token"] = token

        # ── Step 4: Process request ──────────────────────────────────────
        response = await next_handler(request, ctx)

        # ── Step 5: Always set cookie (double-submit defense-in-depth) ───
        self._set_cookie_token(response, token)

        return response


def csrf_token_func(request: Request) -> str:
    """
    Extract the CSRF token from request state.

    This function is designed to be passed to TemplateMiddleware as
    the ``csrf_token_func`` parameter, bridging CSRFMiddleware tokens
    into template context.

    Usage::

        template_mw = TemplateMiddleware(
            csrf_token_func=csrf_token_func,
        )
    """
    return request.state.get("csrf_token", "")


def csrf_exempt(request: Request) -> None:
    """
    Mark a request as exempt from CSRF validation.

    Call this in a controller or guard to skip CSRF checks for
    a specific request (e.g. API webhooks with signature verification).

    Usage::

        async def webhook_handler(request, ctx):
            csrf_exempt(request)
            # ... process webhook
    """
    request.state["csrf_exempt"] = True


# ═══════════════════════════════════════════════════════════════════════════════
#  Exports
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "CORSMiddleware",
    "CSPMiddleware",
    "CSPPolicy",
    "CSRFError",
    "CSRFMiddleware",
    "HSTSMiddleware",
    "HTTPSRedirectMiddleware",
    "ProxyFixMiddleware",
    "SecurityHeadersMiddleware",
    "csrf_exempt",
    "csrf_token_func",
]
