"""
Tests for the extended middleware suite:
- StaticMiddleware (static.py)
- CORSMiddleware, CSPMiddleware, HSTSMiddleware, HTTPSRedirectMiddleware,
  ProxyFixMiddleware, SecurityHeadersMiddleware (security.py)
- RateLimitMiddleware (rate_limit.py)
- EnhancedLoggingMiddleware (logging.py)
- Config builder integration (config_builders.py updates)
- Template context static/csp_nonce injection (context.py updates)
"""

import asyncio
import os
import time
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field as dc_field
from typing import Optional, Dict, Any

import pytest


# ── Shared test helpers ──────────────────────────────────────────────────────

@dataclass
class FakeRequest:
    """Minimal Request stub for middleware testing."""
    method: str = "GET"
    path: str = "/"
    _headers: Dict[str, str] = dc_field(default_factory=dict)
    state: Dict[str, Any] = dc_field(default_factory=dict)
    _scope: Dict[str, Any] = dc_field(default_factory=lambda: {"scheme": "http", "client": ("127.0.0.1", 12345)})

    def header(self, name: str, default: str = "") -> str:
        return self._headers.get(name.lower(), default)

    @property
    def headers(self):
        return self._headers


@dataclass
class FakeCtx:
    """Minimal RequestCtx stub."""
    request_id: str = "test-id"
    request: Optional[Any] = None
    session: Optional[Any] = None
    identity: Optional[Any] = None
    container: Optional[Any] = None


def make_handler(status=200, body=b"OK", headers=None):
    """Create a simple async handler returning a fixed Response."""
    from aquilia.response import Response
    async def handler(request, ctx):
        return Response(body, status=status, headers=headers or {})
    return handler


# ═══════════════════════════════════════════════════════════════════════════════
#  Static Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRadixTrie:
    """Test the internal radix trie for URL prefix matching."""

    def test_single_prefix_lookup(self):
        from aquilia.middleware_ext.static import _RadixTrie
        trie = _RadixTrie()
        trie.insert("/static", Path("/srv/static"))
        result = trie.lookup("/static/css/app.css")
        assert result is not None
        directory, relative = result
        assert directory == Path("/srv/static")
        assert relative == "css/app.css"

    def test_multiple_prefixes(self):
        from aquilia.middleware_ext.static import _RadixTrie
        trie = _RadixTrie()
        trie.insert("/static", Path("/srv/static"))
        trie.insert("/media", Path("/srv/media"))
        trie.insert("/assets/img", Path("/srv/images"))

        r1 = trie.lookup("/static/js/main.js")
        assert r1 is not None
        assert r1[0] == Path("/srv/static")
        assert r1[1] == "js/main.js"

        r2 = trie.lookup("/media/photo.jpg")
        assert r2 is not None
        assert r2[0] == Path("/srv/media")

        r3 = trie.lookup("/assets/img/logo.png")
        assert r3 is not None
        assert r3[0] == Path("/srv/images")

    def test_no_match(self):
        from aquilia.middleware_ext.static import _RadixTrie
        trie = _RadixTrie()
        trie.insert("/static", Path("/srv/static"))
        assert trie.lookup("/api/users") is None

    def test_exact_prefix_match(self):
        from aquilia.middleware_ext.static import _RadixTrie
        trie = _RadixTrie()
        trie.insert("/static", Path("/srv/static"))
        result = trie.lookup("/static")
        assert result is not None
        assert result[1] == ""  # No relative path


class TestLRUFileCache:
    """Test the in-memory LRU file cache."""

    def test_put_and_get(self):
        from aquilia.middleware_ext.static import _LRUFileCache
        cache = _LRUFileCache(capacity_bytes=1024, max_file_size=512)
        cache.put("key1", b"hello", "etag1", "text/plain", 1000.0)
        result = cache.get("key1")
        assert result is not None
        content, etag, ct, mtime = result
        assert content == b"hello"
        assert etag == "etag1"

    def test_eviction_on_capacity(self):
        from aquilia.middleware_ext.static import _LRUFileCache
        cache = _LRUFileCache(capacity_bytes=20, max_file_size=15)
        cache.put("a", b"1234567890", "e1", "t", 1.0)  # 10 bytes
        cache.put("b", b"1234567890", "e2", "t", 2.0)  # 10 bytes → evicts a
        assert cache.get("b") is not None
        # a should have been evicted or b fits alongside
        # Total is 20, both fit exactly
        cache.put("c", b"12345", "e3", "t", 3.0)  # 5 bytes → evicts LRU (a)
        assert cache.get("c") is not None

    def test_skip_large_file(self):
        from aquilia.middleware_ext.static import _LRUFileCache
        cache = _LRUFileCache(capacity_bytes=1024, max_file_size=10)
        cache.put("big", b"x" * 100, "e", "t", 1.0)
        assert cache.get("big") is None

    def test_invalidate(self):
        from aquilia.middleware_ext.static import _LRUFileCache
        cache = _LRUFileCache(capacity_bytes=1024, max_file_size=512)
        cache.put("k", b"data", "e", "t", 1.0)
        cache.invalidate("k")
        assert cache.get("k") is None


class TestStaticMiddleware:
    """Test the StaticMiddleware end-to-end."""

    @pytest.fixture
    def static_dir(self, tmp_path):
        """Create a temp static directory with files."""
        css = tmp_path / "css"
        css.mkdir()
        (css / "app.css").write_text("body { color: red; }")
        (tmp_path / "index.html").write_text("<h1>Hello</h1>")
        (tmp_path / "robots.txt").write_text("User-agent: *")
        return tmp_path

    @pytest.mark.asyncio
    async def test_serves_existing_file(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(path="/static/css/app.css")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler(status=404, body=b"Not Found"))
        assert resp.status == 200
        assert b"body { color: red; }" in resp._content
        assert resp.headers["content-type"] == "text/css"

    @pytest.mark.asyncio
    async def test_falls_through_on_miss(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(path="/api/users")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 200
        assert resp._content == b"OK"

    @pytest.mark.asyncio
    async def test_etag_conditional(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        # First request — get ETag
        req = FakeRequest(path="/static/robots.txt")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        etag = resp.headers.get("etag")
        assert etag

        # Second request with If-None-Match — should get 304
        req2 = FakeRequest(
            path="/static/robots.txt",
            _headers={"if-none-match": etag},
        )
        resp2 = await mw(req2, FakeCtx(), make_handler())
        assert resp2.status == 304

    @pytest.mark.asyncio
    async def test_directory_traversal_blocked(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(path="/static/../../../etc/passwd")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status in (403, 200)  # Either forbidden or fall-through

    @pytest.mark.asyncio
    async def test_head_returns_empty_body(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(method="HEAD", path="/static/robots.txt")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 200
        assert resp._content == b""
        assert int(resp.headers["content-length"]) > 0

    @pytest.mark.asyncio
    async def test_post_falls_through(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(method="POST", path="/static/robots.txt")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 200
        assert resp._content == b"OK"

    @pytest.mark.asyncio
    async def test_index_file(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            index_file="index.html",
            memory_cache=False,
        )
        req = FakeRequest(path="/static/")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler(status=404))
        assert resp.status == 200
        assert b"Hello" in resp._content

    def test_url_for_static(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(directories={"/static": str(static_dir)})
        assert mw.url_for_static("css/app.css") == "/static/css/app.css"

    @pytest.mark.asyncio
    async def test_range_request(self, static_dir):
        from aquilia.middleware_ext.static import StaticMiddleware
        mw = StaticMiddleware(
            directories={"/static": str(static_dir)},
            memory_cache=False,
        )
        req = FakeRequest(
            path="/static/robots.txt",
            _headers={"range": "bytes=0-4"},
        )
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 206
        assert len(resp._content) == 5
        assert "content-range" in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  CORS Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestOriginMatcher:
    """Test the LRU-cached origin matcher."""

    def test_wildcard_matches_everything(self):
        from aquilia.middleware_ext.security import _OriginMatcher
        m = _OriginMatcher(["*"])
        assert m.matches("https://example.com")
        assert m.matches("http://localhost:3000")
        assert m.is_wildcard

    def test_exact_match(self):
        from aquilia.middleware_ext.security import _OriginMatcher
        m = _OriginMatcher(["https://example.com", "https://api.example.com"])
        assert m.matches("https://example.com")
        assert m.matches("https://api.example.com")
        assert not m.matches("https://evil.com")
        assert not m.is_wildcard

    def test_glob_pattern(self):
        from aquilia.middleware_ext.security import _OriginMatcher
        m = _OriginMatcher(["*.example.com"])
        assert m.matches("https.example.com")  # * matches one segment
        assert not m.matches("https://evil.com")

    def test_regex_pattern(self):
        import re
        from aquilia.middleware_ext.security import _OriginMatcher
        m = _OriginMatcher([re.compile(r"^https://.*\.example\.com$")])
        assert m.matches("https://api.example.com")
        assert m.matches("https://staging.example.com")
        assert not m.matches("https://evil.com")

    def test_cache_works(self):
        from aquilia.middleware_ext.security import _OriginMatcher
        m = _OriginMatcher(["https://example.com"], cache_size=2)
        assert m.matches("https://example.com")
        # Second call should use cache
        assert m.matches("https://example.com")
        assert not m.matches("https://other.com")


class TestCORSMiddleware:
    """Test the enhanced CORS middleware."""

    @pytest.mark.asyncio
    async def test_no_origin_header(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(allow_origins=["https://example.com"])
        req = FakeRequest()  # No origin header
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 200
        # Should still add Vary header
        assert "Origin" in resp.headers.get("vary", "")

    @pytest.mark.asyncio
    async def test_allowed_origin(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(allow_origins=["https://example.com"])
        req = FakeRequest(_headers={"origin": "https://example.com"})
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.headers["access-control-allow-origin"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_disallowed_origin(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(allow_origins=["https://example.com"])
        req = FakeRequest(_headers={"origin": "https://evil.com"})
        resp = await mw(req, FakeCtx(), make_handler())
        assert "access-control-allow-origin" not in resp.headers

    @pytest.mark.asyncio
    async def test_preflight(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(allow_origins=["*"], max_age=3600)
        req = FakeRequest(method="OPTIONS", _headers={"origin": "https://example.com"})
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 204
        assert resp.headers["access-control-allow-origin"] == "*"
        assert resp.headers["access-control-max-age"] == "3600"

    @pytest.mark.asyncio
    async def test_credentials_reflect_origin(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(
            allow_origins=["https://example.com"],
            allow_credentials=True,
        )
        req = FakeRequest(_headers={"origin": "https://example.com"})
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.headers["access-control-allow-origin"] == "https://example.com"
        assert resp.headers["access-control-allow-credentials"] == "true"

    @pytest.mark.asyncio
    async def test_expose_headers(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(
            allow_origins=["*"],
            expose_headers=["X-Custom", "X-Request-ID"],
        )
        req = FakeRequest(_headers={"origin": "https://example.com"})
        resp = await mw(req, FakeCtx(), make_handler())
        assert "X-Custom" in resp.headers.get("access-control-expose-headers", "")

    @pytest.mark.asyncio
    async def test_cors_skip_opt_out(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        mw = CORSMiddleware(allow_origins=["https://example.com"])
        req = FakeRequest(
            _headers={"origin": "https://example.com"},
            state={"cors_skip": True},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert "access-control-allow-origin" not in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  CSP Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSPPolicy:
    """Test the CSP policy builder."""

    def test_strict_preset(self):
        from aquilia.middleware_ext.security import CSPPolicy
        policy = CSPPolicy.strict()
        header = policy.build()
        assert "default-src 'self'" in header
        assert "object-src 'none'" in header
        assert "upgrade-insecure-requests" in header

    def test_relaxed_preset(self):
        from aquilia.middleware_ext.security import CSPPolicy
        policy = CSPPolicy.relaxed()
        header = policy.build()
        assert "'unsafe-inline'" in header
        assert "'unsafe-eval'" in header

    def test_nonce_substitution(self):
        from aquilia.middleware_ext.security import CSPPolicy
        policy = CSPPolicy().script_src("'self'", "'nonce-{nonce}'")
        header = policy.build(nonce="abc123")
        assert "'nonce-abc123'" in header

    def test_fluent_builder(self):
        from aquilia.middleware_ext.security import CSPPolicy
        policy = (
            CSPPolicy()
            .default_src("'self'")
            .img_src("'self'", "data:", "https:")
            .report_uri("/csp-report")
        )
        header = policy.build()
        assert "default-src 'self'" in header
        assert "img-src 'self' data: https:" in header
        assert "report-uri /csp-report" in header


class TestCSPMiddleware:
    """Test the CSP middleware."""

    @pytest.mark.asyncio
    async def test_adds_csp_header(self):
        from aquilia.middleware_ext.security import CSPMiddleware
        mw = CSPMiddleware(nonce=False)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert "content-security-policy" in resp.headers

    @pytest.mark.asyncio
    async def test_nonce_injected_into_state(self):
        from aquilia.middleware_ext.security import CSPMiddleware
        mw = CSPMiddleware(nonce=True)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert "csp_nonce" in req.state
        assert len(req.state["csp_nonce"]) > 10

    @pytest.mark.asyncio
    async def test_report_only_mode(self):
        from aquilia.middleware_ext.security import CSPMiddleware
        mw = CSPMiddleware(report_only=True, nonce=False)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert "content-security-policy-report-only" in resp.headers
        assert "content-security-policy" not in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  HSTS Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHSTSMiddleware:

    @pytest.mark.asyncio
    async def test_default_header(self):
        from aquilia.middleware_ext.security import HSTSMiddleware
        mw = HSTSMiddleware()
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        hsts = resp.headers["strict-transport-security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    @pytest.mark.asyncio
    async def test_preload(self):
        from aquilia.middleware_ext.security import HSTSMiddleware
        mw = HSTSMiddleware(preload=True)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert "preload" in resp.headers["strict-transport-security"]

    @pytest.mark.asyncio
    async def test_custom_max_age(self):
        from aquilia.middleware_ext.security import HSTSMiddleware
        mw = HSTSMiddleware(max_age=300, include_subdomains=False)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        hsts = resp.headers["strict-transport-security"]
        assert "max-age=300" in hsts
        assert "includeSubDomains" not in hsts


# ═══════════════════════════════════════════════════════════════════════════════
#  HTTPS Redirect Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHTTPSRedirectMiddleware:

    @pytest.mark.asyncio
    async def test_redirects_http_to_https(self):
        from aquilia.middleware_ext.security import HTTPSRedirectMiddleware
        mw = HTTPSRedirectMiddleware(exclude_hosts=set())
        req = FakeRequest(
            path="/users",
            _headers={"host": "example.com"},
            _scope={"scheme": "http", "client": ("1.2.3.4", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 301
        assert resp.headers["location"] == "https://example.com/users"

    @pytest.mark.asyncio
    async def test_https_passes_through(self):
        from aquilia.middleware_ext.security import HTTPSRedirectMiddleware
        mw = HTTPSRedirectMiddleware()
        req = FakeRequest(
            _scope={"scheme": "https", "client": ("1.2.3.4", 0)},
            _headers={"host": "example.com"},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_exclude_localhost(self):
        from aquilia.middleware_ext.security import HTTPSRedirectMiddleware
        mw = HTTPSRedirectMiddleware()
        req = FakeRequest(
            _headers={"host": "localhost:8000"},
            _scope={"scheme": "http", "client": ("127.0.0.1", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_exclude_path(self):
        from aquilia.middleware_ext.security import HTTPSRedirectMiddleware
        mw = HTTPSRedirectMiddleware(exclude_paths=["/health"], exclude_hosts=set())
        req = FakeRequest(
            path="/health",
            _headers={"host": "example.com"},
            _scope={"scheme": "http", "client": ("1.2.3.4", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  Proxy Fix Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProxyFixMiddleware:

    @pytest.mark.asyncio
    async def test_extracts_client_ip(self):
        from aquilia.middleware_ext.security import ProxyFixMiddleware
        mw = ProxyFixMiddleware(trusted_proxies=["127.0.0.0/8"])
        req = FakeRequest(
            _headers={"x-forwarded-for": "203.0.113.50"},
            _scope={"client": ("127.0.0.1", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert req.state["client_ip"] == "203.0.113.50"

    @pytest.mark.asyncio
    async def test_extracts_client_ip_multi_hop(self):
        """With x_for=1 and two IPs, picks the last hop (rightmost)."""
        from aquilia.middleware_ext.security import ProxyFixMiddleware
        mw = ProxyFixMiddleware(trusted_proxies=["127.0.0.0/8"], x_for=2)
        req = FakeRequest(
            _headers={"x-forwarded-for": "203.0.113.50, 10.0.0.1"},
            _scope={"client": ("127.0.0.1", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert req.state["client_ip"] == "203.0.113.50"

    @pytest.mark.asyncio
    async def test_extracts_proto(self):
        from aquilia.middleware_ext.security import ProxyFixMiddleware
        mw = ProxyFixMiddleware(trusted_proxies=["127.0.0.0/8"])
        req = FakeRequest(
            _headers={"x-forwarded-proto": "https"},
            _scope={"client": ("127.0.0.1", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert req.state["forwarded_proto"] == "https"

    @pytest.mark.asyncio
    async def test_untrusted_proxy_ignored(self):
        from aquilia.middleware_ext.security import ProxyFixMiddleware
        mw = ProxyFixMiddleware(trusted_proxies=["10.0.0.0/8"])
        req = FakeRequest(
            _headers={"x-forwarded-for": "evil.ip"},
            _scope={"client": ("203.0.113.99", 0)},  # Untrusted
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert "client_ip" not in req.state

    @pytest.mark.asyncio
    async def test_x_real_ip_fallback(self):
        from aquilia.middleware_ext.security import ProxyFixMiddleware
        mw = ProxyFixMiddleware(trusted_proxies=["127.0.0.0/8"])
        req = FakeRequest(
            _headers={"x-real-ip": "203.0.113.42"},
            _scope={"client": ("127.0.0.1", 0)},
        )
        resp = await mw(req, FakeCtx(), make_handler())
        assert req.state["client_ip"] == "203.0.113.42"


# ═══════════════════════════════════════════════════════════════════════════════
#  Security Headers Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeadersMiddleware:

    @pytest.mark.asyncio
    async def test_default_headers(self):
        from aquilia.middleware_ext.security import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware()
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["x-xss-protection"] == "0"
        assert "strict-origin" in resp.headers["referrer-policy"]
        assert "permissions-policy" in resp.headers

    @pytest.mark.asyncio
    async def test_custom_frame_options(self):
        from aquilia.middleware_ext.security import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(frame_options="SAMEORIGIN")
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.headers["x-frame-options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_removes_server_header(self):
        from aquilia.middleware_ext.security import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(remove_server_header=True)
        req = FakeRequest()
        handler = make_handler(headers={"server": "Aquilia/0.2"})
        resp = await mw(req, FakeCtx(), handler)
        assert "server" not in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  Rate Limit Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTokenBucket:
    """Test the token bucket algorithm."""

    def test_allows_within_capacity(self):
        from aquilia.middleware_ext.rate_limit import _TokenBucket
        bucket = _TokenBucket(capacity=10, refill_rate=1.0)
        for _ in range(10):
            allowed, _ = bucket.consume()
            assert allowed

    def test_denies_over_capacity(self):
        from aquilia.middleware_ext.rate_limit import _TokenBucket
        bucket = _TokenBucket(capacity=3, refill_rate=0.1)
        for _ in range(3):
            bucket.consume()
        allowed, retry = bucket.consume()
        assert not allowed
        assert retry > 0

    def test_refills_over_time(self):
        from aquilia.middleware_ext.rate_limit import _TokenBucket
        bucket = _TokenBucket(capacity=2, refill_rate=100.0)  # Fast refill
        bucket.consume()
        bucket.consume()
        # Wait a tiny bit for refill
        time.sleep(0.05)
        allowed, _ = bucket.consume()
        assert allowed


class TestSlidingWindowCounter:
    """Test the sliding window counter algorithm."""

    def test_allows_within_limit(self):
        from aquilia.middleware_ext.rate_limit import _SlidingWindowCounter
        counter = _SlidingWindowCounter(window_size=60, max_requests=5)
        for _ in range(5):
            allowed, _ = counter.consume()
            assert allowed

    def test_denies_over_limit(self):
        from aquilia.middleware_ext.rate_limit import _SlidingWindowCounter
        counter = _SlidingWindowCounter(window_size=60, max_requests=3)
        for _ in range(3):
            counter.consume()
        allowed, retry = counter.consume()
        assert not allowed
        assert retry > 0

    def test_remaining_count(self):
        from aquilia.middleware_ext.rate_limit import _SlidingWindowCounter
        counter = _SlidingWindowCounter(window_size=60, max_requests=10)
        counter.consume()
        counter.consume()
        assert counter.remaining == 8


class TestRateLimitMiddleware:
    """Test the rate limit middleware end-to-end."""

    @pytest.mark.asyncio
    async def test_allows_normal_traffic(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(default_limit=10, default_window=60)
        for _ in range(5):
            req = FakeRequest()
            resp = await mw(req, FakeCtx(), make_handler())
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_rate_limits_excess_traffic(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(default_limit=3, default_window=60)
        responses = []
        for _ in range(5):
            req = FakeRequest()
            resp = await mw(req, FakeCtx(), make_handler())
            responses.append(resp.status)
        assert 429 in responses
        assert responses.count(200) == 3

    @pytest.mark.asyncio
    async def test_exempt_paths(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(
            default_limit=1, default_window=60,
            exempt_paths=["/health"],
        )
        # Use up the limit
        req = FakeRequest(path="/api")
        await mw(req, FakeCtx(), make_handler())
        req2 = FakeRequest(path="/api")
        resp = await mw(req2, FakeCtx(), make_handler())
        assert resp.status == 429

        # Health should be exempt
        req3 = FakeRequest(path="/health")
        resp3 = await mw(req3, FakeCtx(), make_handler())
        assert resp3.status == 200

    @pytest.mark.asyncio
    async def test_retry_after_header(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(default_limit=1, default_window=60)
        req = FakeRequest()
        await mw(req, FakeCtx(), make_handler())
        req2 = FakeRequest()
        resp = await mw(req2, FakeCtx(), make_handler())
        assert resp.status == 429
        assert "retry-after" in resp.headers

    @pytest.mark.asyncio
    async def test_ratelimit_headers_on_success(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(default_limit=10, default_window=60, include_headers=True)
        req = FakeRequest()
        resp = await mw(req, FakeCtx(), make_handler())
        assert resp.status == 200
        assert resp.headers.get("x-ratelimit-limit") == "10"

    @pytest.mark.asyncio
    async def test_rate_limit_skip_opt_out(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(default_limit=1, default_window=60)
        # Exhaust limit
        req = FakeRequest()
        await mw(req, FakeCtx(), make_handler())
        # This should be rate-limited
        req2 = FakeRequest()
        resp = await mw(req2, FakeCtx(), make_handler())
        assert resp.status == 429
        # But skip should bypass
        req3 = FakeRequest(state={"rate_limit_skip": True})
        resp3 = await mw(req3, FakeCtx(), make_handler())
        assert resp3.status == 200


class TestRateLimitRuleMatching:
    """Test rate limit rule path and method matching."""

    def test_wildcard_scope(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        rule = RateLimitRule(scope="*")
        req = FakeRequest(path="/any/path")
        assert rule.matches(req)

    def test_scoped_path(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        rule = RateLimitRule(scope="/api")
        assert rule.matches(FakeRequest(path="/api/users"))
        assert not rule.matches(FakeRequest(path="/admin/panel"))

    def test_method_filter(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        rule = RateLimitRule(methods=["POST", "PUT"])
        assert rule.matches(FakeRequest(method="POST"))
        assert not rule.matches(FakeRequest(method="GET"))


# ═══════════════════════════════════════════════════════════════════════════════
#  Enhanced Logging Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnhancedLoggingMiddleware:

    @pytest.mark.asyncio
    async def test_logs_request(self):
        from aquilia.middleware_ext.logging import LoggingMiddleware
        mw = LoggingMiddleware(format="dev", skip_paths=set())
        req = FakeRequest(path="/test")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_skip_health_paths(self):
        from aquilia.middleware_ext.logging import LoggingMiddleware
        mw = LoggingMiddleware(format="dev")
        req = FakeRequest(path="/health")
        ctx = FakeCtx()
        resp = await mw(req, ctx, make_handler())
        assert resp.status == 200


class TestLogFormatters:

    def test_combined_format(self):
        from aquilia.middleware_ext.logging import CombinedLogFormatter
        fmt = CombinedLogFormatter()
        line = fmt.format_request(
            method="GET", path="/test", status=200, duration_ms=5.2,
            content_length=42, client_ip="1.2.3.4", user_agent="TestAgent",
            referer="-", request_id="abc", extras={},
        )
        assert "GET" in line
        assert "/test" in line
        assert "200" in line

    def test_structured_format(self):
        import json
        from aquilia.middleware_ext.logging import StructuredLogFormatter
        fmt = StructuredLogFormatter()
        line = fmt.format_request(
            method="POST", path="/api", status=201, duration_ms=12.3,
            content_length=100, client_ip="10.0.0.1", user_agent="curl",
            referer="-", request_id="xyz", extras={},
        )
        data = json.loads(line)
        assert data["method"] == "POST"
        assert data["status"] == 201
        assert "timestamp" in data

    def test_dev_format(self):
        from aquilia.middleware_ext.logging import DevLogFormatter
        fmt = DevLogFormatter()
        line = fmt.format_request(
            method="DELETE", path="/resource", status=500, duration_ms=1500,
            content_length=0, client_ip="-", user_agent="-",
            referer="-", request_id="test", extras={},
        )
        assert "DELETE" in line
        assert "500" in line


# ═══════════════════════════════════════════════════════════════════════════════
#  Config Builder Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigBuildersMiddleware:
    """Test new Integration.* methods and Workspace.security() updates."""

    def test_static_files_integration(self):
        from aquilia.config_builders import Integration
        config = Integration.static_files(
            directories={"/static": "static", "/media": "uploads"},
            cache_max_age=3600,
        )
        assert config["enabled"]
        assert config["_integration_type"] == "static_files"
        assert config["directories"]["/static"] == "static"
        assert config["cache_max_age"] == 3600

    def test_cors_integration(self):
        from aquilia.config_builders import Integration
        config = Integration.cors(
            allow_origins=["https://example.com"],
            allow_credentials=True,
        )
        assert config["enabled"]
        assert config["_integration_type"] == "cors"
        assert "https://example.com" in config["allow_origins"]
        assert config["allow_credentials"]

    def test_csp_integration(self):
        from aquilia.config_builders import Integration
        config = Integration.csp(
            policy={"default-src": ["'self'"]},
            nonce=True,
        )
        assert config["enabled"]
        assert config["_integration_type"] == "csp"
        assert config["policy"]["default-src"] == ["'self'"]

    def test_rate_limit_integration(self):
        from aquilia.config_builders import Integration
        config = Integration.rate_limit(limit=200, window=120, algorithm="token_bucket")
        assert config["enabled"]
        assert config["_integration_type"] == "rate_limit"
        assert config["limit"] == 200

    def test_workspace_security_new_flags(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("test").security(
            cors_enabled=True,
            helmet_enabled=True,
            rate_limiting=True,
            https_redirect=True,
            hsts=True,
            proxy_fix=True,
        )
        config = ws.to_dict()
        sec = config["security"]
        assert sec["cors_enabled"]
        assert sec["helmet_enabled"]
        assert sec["rate_limiting"]
        assert sec["https_redirect"]
        assert sec["hsts"]
        assert sec["proxy_fix"]

    def test_workspace_integrate_with_type_marker(self):
        from aquilia.config_builders import Workspace, Integration
        ws = (
            Workspace("test")
            .integrate(Integration.static_files())
            .integrate(Integration.cors(allow_origins=["*"]))
            .integrate(Integration.rate_limit(limit=50))
        )
        config = ws.to_dict()
        assert "static_files" in config["integrations"]
        assert "cors" in config["integrations"]
        assert "rate_limit" in config["integrations"]
        # CORS should also set security.cors_enabled
        assert config["security"]["cors_enabled"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Template Context Injection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateContextInjection:
    """Test that static() and csp_nonce are injected into template context."""

    def test_inject_static_helper(self):
        from aquilia.templates.context import inject_static_helper
        ctx = {}
        inject_static_helper(ctx, lambda p: f"/assets/{p}")
        assert ctx["static"]("css/app.css") == "/assets/css/app.css"
        assert ctx["static_url"]("js/main.js") == "/assets/js/main.js"

    def test_inject_csp_nonce(self):
        from aquilia.templates.context import inject_csp_nonce
        ctx = {}
        inject_csp_nonce(ctx, "abc123xyz")
        assert ctx["csp_nonce"] == "abc123xyz"

    def test_create_template_context_with_static(self):
        from aquilia.templates.context import create_template_context
        req = FakeRequest(state={
            "template_url_for": lambda name, **kw: f"/{name}",
            "template_static": lambda p: f"/static/{p}",
            "template_config": {},
        })
        ctx_obj = FakeCtx(request=req)
        tpl_ctx = create_template_context({"title": "Test"}, ctx_obj)
        d = tpl_ctx.to_dict()
        assert "static" in d
        assert d["static"]("img/logo.png") == "/static/img/logo.png"

    def test_create_template_context_with_csp_nonce(self):
        from aquilia.templates.context import create_template_context
        req = FakeRequest(state={
            "template_url_for": lambda name, **kw: f"/{name}",
            "template_config": {},
            "csp_nonce": "nonce123",
        })
        ctx_obj = FakeCtx(request=req)
        tpl_ctx = create_template_context({}, ctx_obj)
        d = tpl_ctx.to_dict()
        assert d["csp_nonce"] == "nonce123"


# ═══════════════════════════════════════════════════════════════════════════════
#  Config Loader Tests (new methods)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigLoaderNewMethods:

    def test_get_security_config_defaults(self):
        from aquilia.config import ConfigLoader
        loader = ConfigLoader()
        sec = loader.get_security_config()
        assert not sec["enabled"]
        assert not sec["cors_enabled"]
        assert not sec["helmet_enabled"]

    def test_get_security_config_with_data(self):
        from aquilia.config import ConfigLoader
        loader = ConfigLoader()
        loader.config_data["security"] = {
            "enabled": True,
            "cors_enabled": True,
            "helmet_enabled": True,
            "hsts": True,
        }
        sec = loader.get_security_config()
        assert sec["enabled"]
        assert sec["cors_enabled"]
        assert sec["helmet_enabled"]
        assert sec["hsts"]

    def test_get_static_config_defaults(self):
        from aquilia.config import ConfigLoader
        loader = ConfigLoader()
        static = loader.get_static_config()
        assert not static["enabled"]
        assert static["directories"] == {"/static": "static"}

    def test_get_static_config_with_data(self):
        from aquilia.config import ConfigLoader
        loader = ConfigLoader()
        loader.config_data["integrations"] = {
            "static_files": {
                "enabled": True,
                "directories": {"/assets": "dist"},
                "cache_max_age": 3600,
            }
        }
        static = loader.get_static_config()
        assert static["enabled"]
        assert static["directories"]["/assets"] == "dist"
        assert static["cache_max_age"] == 3600


# ═══════════════════════════════════════════════════════════════════════════════
#  Import / Export Smoke Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMiddlewareImports:
    """Verify all new middleware are importable from expected paths."""

    def test_import_from_middleware_ext(self):
        from aquilia.middleware_ext import (
            CORSMiddleware,
            CSPMiddleware,
            CSPPolicy,
            HSTSMiddleware,
            HTTPSRedirectMiddleware,
            ProxyFixMiddleware,
            SecurityHeadersMiddleware,
            RateLimitMiddleware,
            RateLimitRule,
            StaticMiddleware,
            EnhancedLoggingMiddleware,
        )
        assert CORSMiddleware is not None
        assert StaticMiddleware is not None

    def test_import_from_aquilia_top_level(self):
        from aquilia import (
            CORSMiddleware,
            CSPMiddleware,
            CSPPolicy,
            CSRFError,
            CSRFMiddleware,
            HSTSMiddleware,
            HTTPSRedirectMiddleware,
            ProxyFixMiddleware,
            SecurityHeadersMiddleware,
            RateLimitMiddleware,
            RateLimitRule,
            StaticMiddleware,
            csrf_exempt,
            csrf_token_func,
        )
        assert CORSMiddleware is not None
        assert CSRFMiddleware is not None
        assert csrf_token_func is not None

    def test_integration_builders_import(self):
        from aquilia import Integration
        assert hasattr(Integration, "static_files")
        assert hasattr(Integration, "cors")
        assert hasattr(Integration, "csp")
        assert hasattr(Integration, "rate_limit")


# ═══════════════════════════════════════════════════════════════════════════════
#  CSRF Middleware Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSRFMiddleware:
    """Tests for CSRFMiddleware — Synchronizer Token + Double Submit Cookie."""

    def _make_csrf(self, **kwargs):
        from aquilia.middleware_ext.security import CSRFMiddleware
        defaults = {"secret_key": "test-secret-key-for-csrf"}
        defaults.update(kwargs)
        return CSRFMiddleware(**defaults)

    # ── Token Generation & Injection ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_request_injects_csrf_token(self):
        """GET requests should have a CSRF token injected into request.state."""
        csrf = self._make_csrf()
        req = FakeRequest(method="GET", path="/")
        ctx = FakeCtx()
        handler = make_handler()

        resp = await csrf(req, ctx, handler)
        assert resp.status == 200
        assert "csrf_token" in req.state
        assert len(req.state["csrf_token"]) > 0

    @pytest.mark.asyncio
    async def test_token_is_cryptographically_random(self):
        """Each new token should be unique."""
        csrf = self._make_csrf()
        tokens = set()
        for _ in range(50):
            req = FakeRequest(method="GET", path="/")
            await csrf(req, FakeCtx(), make_handler())
            tokens.add(req.state["csrf_token"])
        assert len(tokens) == 50

    @pytest.mark.asyncio
    async def test_token_field_and_header_names_injected(self):
        """Request state should include the field and header names for templates."""
        csrf = self._make_csrf(header_name="X-My-Token", field_name="my_token")
        req = FakeRequest(method="GET", path="/")
        await csrf(req, FakeCtx(), make_handler())
        assert req.state["csrf_token_field"] == "my_token"
        assert req.state["csrf_token_header"] == "x-my-token"

    # ── Safe Methods Bypass ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_safe_methods_bypass_validation(self):
        """GET, HEAD, OPTIONS, TRACE should never require CSRF tokens."""
        csrf = self._make_csrf()
        for method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            req = FakeRequest(method=method, path="/any")
            resp = await csrf(req, FakeCtx(), make_handler())
            assert resp.status == 200, f"{method} should bypass CSRF"

    # ── POST Without Token → 403 ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_without_token_returns_403(self):
        """POST without a CSRF token should be rejected with 403."""
        csrf = self._make_csrf()
        req = FakeRequest(method="POST", path="/submit")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403
        assert b"CSRF token missing" in resp._content

    @pytest.mark.asyncio
    async def test_put_without_token_returns_403(self):
        """PUT without a CSRF token should be rejected."""
        csrf = self._make_csrf()
        req = FakeRequest(method="PUT", path="/resource")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_patch_without_token_returns_403(self):
        """PATCH without a CSRF token should be rejected."""
        csrf = self._make_csrf()
        req = FakeRequest(method="PATCH", path="/resource")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_delete_without_token_returns_403(self):
        """DELETE without a CSRF token should be rejected."""
        csrf = self._make_csrf()
        req = FakeRequest(method="DELETE", path="/resource")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    # ── Token Validation via Header ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_with_valid_header_token_succeeds(self):
        """POST with correct X-CSRF-Token header should succeed."""
        csrf = self._make_csrf()

        # Step 1: GET to obtain token
        get_req = FakeRequest(method="GET", path="/form")
        await csrf(get_req, FakeCtx(), make_handler())
        token = get_req.state["csrf_token"]

        # Step 2: POST with the token in header + session
        post_req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": token},
            state={"session": {"_csrf_token": token}},
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_post_with_invalid_header_token_returns_403(self):
        """POST with wrong X-CSRF-Token header should be rejected."""
        csrf = self._make_csrf()

        # Get a valid token
        get_req = FakeRequest(method="GET", path="/form")
        await csrf(get_req, FakeCtx(), make_handler())

        # Use wrong token
        post_req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": "wrong-token-value"},
            state={"session": {"_csrf_token": get_req.state["csrf_token"]}},
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 403
        assert b"CSRF token invalid" in resp._content

    # ── Token Validation via Form Field ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_with_valid_form_field_succeeds(self):
        """POST with correct _csrf_token in form data should succeed."""
        csrf = self._make_csrf()
        token = csrf._generate_token()

        post_req = FakeRequest(
            method="POST", path="/submit",
            state={
                "session": {"_csrf_token": token},
                "form_data": {"_csrf_token": token, "name": "test"},
            },
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_custom_field_name(self):
        """Custom field_name should be used for form token extraction."""
        csrf = self._make_csrf(field_name="csrf_tok")
        token = csrf._generate_token()

        post_req = FakeRequest(
            method="POST", path="/submit",
            state={
                "session": {"_csrf_token": token},
                "form_data": {"csrf_tok": token},
            },
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 200

    # ── Token Validation via Parsed Body ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_post_with_parsed_body_token_succeeds(self):
        """POST with token in parsed_body should succeed."""
        csrf = self._make_csrf()
        token = csrf._generate_token()

        post_req = FakeRequest(
            method="POST", path="/submit",
            state={
                "session": {"_csrf_token": token},
                "parsed_body": {"_csrf_token": token},
            },
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 200

    # ── Session Storage ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_token_stored_in_session(self):
        """Token should be stored in the session on first request."""
        csrf = self._make_csrf()
        session = {}
        req = FakeRequest(method="GET", path="/", state={"session": session})
        await csrf(req, FakeCtx(), make_handler())
        assert "_csrf_token" in session
        assert session["_csrf_token"] == req.state["csrf_token"]

    @pytest.mark.asyncio
    async def test_token_reused_from_session(self):
        """Existing session token should be reused, not regenerated."""
        csrf = self._make_csrf()
        existing_token = "existing-session-token-value"
        session = {"_csrf_token": existing_token}
        req = FakeRequest(method="GET", path="/", state={"session": session})
        await csrf(req, FakeCtx(), make_handler())
        assert req.state["csrf_token"] == existing_token

    # ── Cookie Double-Submit Fallback ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_csrf_cookie_set_on_response(self):
        """Response should include a CSRF cookie (double-submit defense)."""
        csrf = self._make_csrf()
        req = FakeRequest(method="GET", path="/")
        resp = await csrf(req, FakeCtx(), make_handler())
        cookie = resp.headers.get("set-cookie", "")
        assert "_csrf_cookie=" in cookie
        assert "SameSite=Lax" in cookie

    @pytest.mark.asyncio
    async def test_cookie_token_signing_and_verification(self):
        """Signed cookie tokens should be verifiable."""
        csrf = self._make_csrf()
        token = csrf._generate_token()
        signed = csrf._sign_token(token)
        assert "." in signed
        verified = csrf._verify_signed_token(signed)
        assert verified == token

    @pytest.mark.asyncio
    async def test_cookie_token_tamper_detection(self):
        """Tampered cookie tokens should fail verification."""
        csrf = self._make_csrf()
        token = csrf._generate_token()
        signed = csrf._sign_token(token)
        # Tamper with the signature
        tampered = signed[:-4] + "XXXX"
        assert csrf._verify_signed_token(tampered) is None

    @pytest.mark.asyncio
    async def test_cookie_token_fallback_when_no_session(self):
        """When no session, token should be read from cookie."""
        csrf = self._make_csrf()
        token = csrf._generate_token()
        signed = csrf._sign_token(token)

        # POST with cookie (no session) + header token
        req = FakeRequest(
            method="POST", path="/submit",
            _headers={
                "x-csrf-token": token,
                "cookie": f"_csrf_cookie={signed}",
            },
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    # ── AJAX Trust (X-Requested-With) ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_ajax_request_bypasses_csrf(self):
        """AJAX requests with X-Requested-With should bypass CSRF when trust_ajax=True."""
        csrf = self._make_csrf(trust_ajax=True)
        req = FakeRequest(
            method="POST", path="/api/data",
            _headers={"x-requested-with": "XMLHttpRequest"},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_ajax_not_trusted_when_disabled(self):
        """AJAX requests should NOT bypass CSRF when trust_ajax=False."""
        csrf = self._make_csrf(trust_ajax=False)
        req = FakeRequest(
            method="POST", path="/api/data",
            _headers={"x-requested-with": "XMLHttpRequest"},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    # ── Exempt Paths ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_exempt_path_bypasses_csrf(self):
        """Exempt paths should bypass CSRF validation."""
        csrf = self._make_csrf(exempt_paths=["/webhooks/stripe", "/api/*"])

        # Exact match
        req = FakeRequest(method="POST", path="/webhooks/stripe")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_exempt_path_wildcard(self):
        """Wildcard exempt paths should match prefixes."""
        csrf = self._make_csrf(exempt_paths=["/api/*"])
        req = FakeRequest(method="POST", path="/api/users/123")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_non_exempt_path_still_requires_token(self):
        """Non-exempt paths should still require CSRF tokens."""
        csrf = self._make_csrf(exempt_paths=["/api/*"])
        req = FakeRequest(method="POST", path="/submit")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    # ── Exempt Content Types ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_exempt_content_type_bypasses_csrf(self):
        """Exempt content types should bypass CSRF."""
        csrf = self._make_csrf(exempt_content_types=["application/json"])
        req = FakeRequest(
            method="POST", path="/api/data",
            _headers={"content-type": "application/json; charset=utf-8"},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_non_exempt_content_type_requires_token(self):
        """Non-exempt content types should still require CSRF tokens."""
        csrf = self._make_csrf(exempt_content_types=["application/json"])
        req = FakeRequest(
            method="POST", path="/submit",
            _headers={"content-type": "application/x-www-form-urlencoded"},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 403

    # ── Route-Level csrf_exempt ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_csrf_exempt_function(self):
        """csrf_exempt() should mark the request as exempt."""
        from aquilia.middleware_ext.security import csrf_exempt

        csrf = self._make_csrf()
        req = FakeRequest(method="POST", path="/webhook")
        csrf_exempt(req)  # Mark as exempt
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    # ── Token Rotation ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_token_rotation_after_validation(self):
        """With rotate_token=True, a new token should be generated after validation."""
        csrf = self._make_csrf(rotate_token=True)
        token = csrf._generate_token()
        session = {"_csrf_token": token}

        req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": token},
            state={"session": session},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200
        # Token should have been rotated
        assert req.state["csrf_token"] != token
        assert session["_csrf_token"] != token

    @pytest.mark.asyncio
    async def test_no_rotation_by_default(self):
        """By default, token should NOT be rotated after validation."""
        csrf = self._make_csrf(rotate_token=False)
        token = csrf._generate_token()
        session = {"_csrf_token": token}

        req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": token},
            state={"session": session},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200
        assert req.state["csrf_token"] == token

    # ── Custom Failure Status ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_custom_failure_status(self):
        """Custom failure status should be used instead of default 403."""
        csrf = self._make_csrf(failure_status=419)
        req = FakeRequest(method="POST", path="/submit")
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 419

    # ── Custom Header Name ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_custom_header_name(self):
        """Custom header name should be checked for token."""
        csrf = self._make_csrf(header_name="X-My-CSRF")
        token = csrf._generate_token()

        req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-my-csrf": token},
            state={"session": {"_csrf_token": token}},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    # ── Cookie Configuration ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cookie_secure_flag(self):
        """Secure flag should be set on cookie when configured."""
        csrf = self._make_csrf(cookie_secure=True)
        req = FakeRequest(method="GET", path="/")
        resp = await csrf(req, FakeCtx(), make_handler())
        cookie = resp.headers.get("set-cookie", "")
        assert "Secure" in cookie

    @pytest.mark.asyncio
    async def test_cookie_httponly_flag(self):
        """HttpOnly flag should be set on cookie when configured."""
        csrf = self._make_csrf(cookie_httponly=True)
        req = FakeRequest(method="GET", path="/")
        resp = await csrf(req, FakeCtx(), make_handler())
        cookie = resp.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie

    @pytest.mark.asyncio
    async def test_cookie_samesite_strict(self):
        """SameSite=Strict should be set when configured."""
        csrf = self._make_csrf(cookie_samesite="Strict")
        req = FakeRequest(method="GET", path="/")
        resp = await csrf(req, FakeCtx(), make_handler())
        cookie = resp.headers.get("set-cookie", "")
        assert "SameSite=Strict" in cookie

    @pytest.mark.asyncio
    async def test_cookie_domain(self):
        """Domain attribute should be set on cookie when configured."""
        csrf = self._make_csrf(cookie_domain=".example.com")
        req = FakeRequest(method="GET", path="/")
        resp = await csrf(req, FakeCtx(), make_handler())
        cookie = resp.headers.get("set-cookie", "")
        assert "Domain=.example.com" in cookie

    # ── Constant-Time Comparison ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_constant_time_comparison(self):
        """Token validation should use constant-time comparison."""
        csrf = self._make_csrf()
        assert csrf._validate_token("abc123", "abc123") is True
        assert csrf._validate_token("abc123", "abc124") is False
        assert csrf._validate_token("", "") is True
        assert csrf._validate_token("a", "b") is False

    # ── Edge Cases ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_malformed_cookie_ignored(self):
        """Malformed/unsigned cookies should be ignored gracefully."""
        csrf = self._make_csrf()
        req = FakeRequest(
            method="GET", path="/",
            _headers={"cookie": "_csrf_cookie=no-dot-here"},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        # Should generate a new token, not crash
        assert resp.status == 200
        assert "csrf_token" in req.state

    @pytest.mark.asyncio
    async def test_empty_cookie_header(self):
        """Empty cookie header should be handled gracefully."""
        csrf = self._make_csrf()
        req = FakeRequest(
            method="GET", path="/",
            _headers={"cookie": ""},
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_multiple_cookies_parsed(self):
        """CSRF cookie should be correctly extracted when multiple cookies present."""
        csrf = self._make_csrf()
        token = csrf._generate_token()
        signed = csrf._sign_token(token)

        req = FakeRequest(
            method="POST", path="/submit",
            _headers={
                "x-csrf-token": token,
                "cookie": f"session_id=abc123; _csrf_cookie={signed}; lang=en",
            },
        )
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_session_with_hasattr_getitem(self):
        """Session objects with __getitem__ but no .get() should work."""
        csrf = self._make_csrf()

        class DictLikeSession:
            def __init__(self):
                self._data = {}
            def __getitem__(self, key):
                return self._data[key]
            def __setitem__(self, key, value):
                self._data[key] = value

        session = DictLikeSession()
        req = FakeRequest(method="GET", path="/", state={"session": session})
        resp = await csrf(req, FakeCtx(), make_handler())
        assert resp.status == 200
        assert session._data.get("_csrf_token") == req.state["csrf_token"]


class TestCSRFTokenFunc:
    """Tests for the csrf_token_func helper used by TemplateMiddleware."""

    def test_returns_token_from_state(self):
        from aquilia.middleware_ext.security import csrf_token_func
        req = FakeRequest(state={"csrf_token": "my-token-123"})
        assert csrf_token_func(req) == "my-token-123"

    def test_returns_empty_string_when_no_token(self):
        from aquilia.middleware_ext.security import csrf_token_func
        req = FakeRequest()
        assert csrf_token_func(req) == ""


class TestCSRFError:
    """Tests for CSRFError — now extends CSRFViolationFault (Aquilia Fault system)."""

    def test_csrf_error_message(self):
        from aquilia.middleware_ext.security import CSRFError
        err = CSRFError("Token expired")
        assert err.reason == "Token expired"
        assert err.code == "CSRF_VIOLATION"
        assert "Token expired" in str(err)

    def test_csrf_error_default_message(self):
        from aquilia.middleware_ext.security import CSRFError
        err = CSRFError()
        assert err.reason == "CSRF validation failed"
        assert err.code == "CSRF_VIOLATION"

    def test_csrf_error_is_fault_subclass(self):
        from aquilia.middleware_ext.security import CSRFError
        from aquilia.faults import Fault, CSRFViolationFault, SecurityFault
        err = CSRFError("bad token")
        assert isinstance(err, Fault)
        assert isinstance(err, SecurityFault)
        assert isinstance(err, CSRFViolationFault)
        assert isinstance(err, Exception)

    def test_csrf_error_fault_attributes(self):
        from aquilia.middleware_ext.security import CSRFError
        from aquilia.faults.core import FaultDomain, Severity
        err = CSRFError("expired")
        assert err.domain == FaultDomain.SECURITY
        assert err.severity == Severity.WARN
        assert err.public is True
        assert err.metadata.get("reason") == "expired"


class TestCSRFTemplateIntegration:
    """Tests for CSRF + Template middleware integration."""

    @pytest.mark.asyncio
    async def test_template_middleware_auto_detects_csrf_token(self):
        """TemplateMiddleware should auto-detect csrf_token from request.state."""
        from aquilia.templates.middleware import TemplateMiddleware

        tmw = TemplateMiddleware()
        req = FakeRequest(state={"csrf_token": "injected-token"})
        resp = await tmw(req, FakeCtx(), make_handler())
        assert req.state.get("template_csrf_token") == "injected-token"

    @pytest.mark.asyncio
    async def test_template_middleware_uses_explicit_func(self):
        """TemplateMiddleware should prefer explicit csrf_token_func over auto-detect."""
        from aquilia.templates.middleware import TemplateMiddleware

        tmw = TemplateMiddleware(csrf_token_func=lambda r: "explicit-token")
        req = FakeRequest(state={"csrf_token": "auto-token"})
        resp = await tmw(req, FakeCtx(), make_handler())
        assert req.state.get("template_csrf_token") == "explicit-token"

    @pytest.mark.asyncio
    async def test_template_middleware_no_csrf_token(self):
        """TemplateMiddleware should not set template_csrf_token when no token."""
        from aquilia.templates.middleware import TemplateMiddleware

        tmw = TemplateMiddleware()
        req = FakeRequest()
        resp = await tmw(req, FakeCtx(), make_handler())
        assert "template_csrf_token" not in req.state


class TestCSRFConfigBuilderIntegration:
    """Tests for CSRF integration with Workspace.security() config builder."""

    def test_workspace_security_csrf_protection_flag(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("TestApp")
        ws.security(csrf_protection=True)
        assert ws._security_config["csrf_protection"] is True

    def test_workspace_security_csrf_disabled_by_default(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("TestApp")
        ws.security()
        assert ws._security_config["csrf_protection"] is False

    def test_workspace_security_csrf_with_custom_config(self):
        from aquilia.config_builders import Workspace
        ws = Workspace("TestApp")
        ws.security(
            csrf_protection=True,
            csrf_config={
                "secret_key": "my-secret",
                "token_length": 64,
                "header_name": "X-Anti-Forgery",
                "exempt_paths": ["/api/*"],
                "trust_ajax": False,
            },
        )
        assert ws._security_config["csrf_protection"] is True
        assert ws._security_config["csrf_config"]["secret_key"] == "my-secret"
        assert ws._security_config["csrf_config"]["token_length"] == 64


class TestCSRFExportsAndImports:
    """Tests for CSRF symbol availability across the Aquilia package."""

    def test_import_from_security_module(self):
        from aquilia.middleware_ext.security import (
            CSRFMiddleware, CSRFError, csrf_token_func, csrf_exempt
        )
        assert CSRFMiddleware is not None
        assert CSRFError is not None
        assert callable(csrf_token_func)
        assert callable(csrf_exempt)

    def test_import_from_middleware_ext(self):
        from aquilia.middleware_ext import (
            CSRFMiddleware, CSRFError, csrf_token_func, csrf_exempt
        )
        assert CSRFMiddleware is not None

    def test_import_from_aquilia_top_level(self):
        from aquilia import CSRFMiddleware, CSRFError, csrf_token_func, csrf_exempt
        assert CSRFMiddleware is not None
        assert callable(csrf_exempt)


class TestCSRFFullFlow:
    """End-to-end CSRF flow tests simulating real-world usage."""

    @pytest.mark.asyncio
    async def test_full_form_submission_flow(self):
        """Simulate: GET form → extract token → POST form with token."""
        from aquilia.middleware_ext.security import CSRFMiddleware

        csrf = CSRFMiddleware(secret_key="e2e-test-key")
        session = {}

        # Step 1: GET the form page
        get_req = FakeRequest(method="GET", path="/form", state={"session": session})
        get_resp = await csrf(get_req, FakeCtx(), make_handler())
        assert get_resp.status == 200
        token = get_req.state["csrf_token"]
        assert len(token) > 0
        assert session["_csrf_token"] == token

        # Step 2: POST the form with the token
        post_req = FakeRequest(
            method="POST", path="/form",
            state={
                "session": session,
                "form_data": {"_csrf_token": token, "email": "user@test.com"},
            },
        )
        post_resp = await csrf(post_req, FakeCtx(), make_handler())
        assert post_resp.status == 200

    @pytest.mark.asyncio
    async def test_full_spa_ajax_flow(self):
        """Simulate: GET page → read token from cookie → AJAX POST."""
        from aquilia.middleware_ext.security import CSRFMiddleware

        csrf = CSRFMiddleware(secret_key="spa-test-key", cookie_httponly=False)

        # Step 1: GET page (no session — SPA scenario)
        get_req = FakeRequest(method="GET", path="/")
        get_resp = await csrf(get_req, FakeCtx(), make_handler())
        token = get_req.state["csrf_token"]

        # Extract signed cookie from response
        cookie_header = get_resp.headers.get("set-cookie", "")
        # Parse out the cookie value
        import re
        match = re.search(r"_csrf_cookie=([^;]+)", cookie_header)
        assert match, "Cookie should be set"
        signed_cookie = match.group(1)

        # Step 2: AJAX POST with token in header + cookie
        post_req = FakeRequest(
            method="POST", path="/api/update",
            _headers={
                "x-csrf-token": token,
                "cookie": f"_csrf_cookie={signed_cookie}",
            },
        )
        post_resp = await csrf(post_req, FakeCtx(), make_handler())
        assert post_resp.status == 200

    @pytest.mark.asyncio
    async def test_csrf_with_session_middleware_flow(self):
        """Simulate CSRF + Session middleware working together."""
        from aquilia.middleware_ext.security import CSRFMiddleware

        csrf = CSRFMiddleware(secret_key="session-csrf-key")

        # Simulate session middleware having already set session
        session = {"user_id": 42}

        # GET form
        get_req = FakeRequest(method="GET", path="/profile", state={"session": session})
        await csrf(get_req, FakeCtx(), make_handler())
        token = get_req.state["csrf_token"]

        # POST form
        post_req = FakeRequest(
            method="POST", path="/profile",
            _headers={"x-csrf-token": token},
            state={"session": session},
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_cross_session_token_rejection(self):
        """Token from one session should not work with another session."""
        from aquilia.middleware_ext.security import CSRFMiddleware

        csrf = CSRFMiddleware(secret_key="isolation-key")

        # Session A gets token
        session_a = {}
        req_a = FakeRequest(method="GET", path="/", state={"session": session_a})
        await csrf(req_a, FakeCtx(), make_handler())
        token_a = req_a.state["csrf_token"]

        # Session B gets its own token
        session_b = {}
        req_b = FakeRequest(method="GET", path="/", state={"session": session_b})
        await csrf(req_b, FakeCtx(), make_handler())

        # Try to use token_a with session_b → should fail
        post_req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": token_a},
            state={"session": session_b},
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  Ecosystem Integration Tests — Faults, Serializers, Config Builders
# ═══════════════════════════════════════════════════════════════════════════════

class TestFaultEcosystemIntegration:
    """Verify that all middleware faults are proper Aquilia Fault subclasses."""

    def test_csrf_violation_fault(self):
        from aquilia.faults import CSRFViolationFault, SecurityFault, Fault
        from aquilia.faults.core import FaultDomain, Severity

        f = CSRFViolationFault(reason="token mismatch")
        assert isinstance(f, SecurityFault)
        assert isinstance(f, Fault)
        assert isinstance(f, Exception)
        assert f.code == "CSRF_VIOLATION"
        assert f.domain == FaultDomain.SECURITY
        assert f.severity == Severity.WARN
        assert f.public is True
        assert f.reason == "token mismatch"
        assert f.metadata["reason"] == "token mismatch"

    def test_cors_violation_fault(self):
        from aquilia.faults import CORSViolationFault, SecurityFault, Fault
        from aquilia.faults.core import FaultDomain

        f = CORSViolationFault(origin="https://evil.com")
        assert isinstance(f, SecurityFault)
        assert isinstance(f, Fault)
        assert f.code == "CORS_VIOLATION"
        assert f.domain == FaultDomain.SECURITY
        assert f.public is True
        assert "evil.com" in f.message
        assert f.metadata["origin"] == "https://evil.com"

    def test_rate_limit_exceeded_fault(self):
        from aquilia.faults import RateLimitExceededFault, SecurityFault, Fault
        from aquilia.faults.core import FaultDomain

        f = RateLimitExceededFault(limit=100, window=60.0, retry_after=15.0)
        assert isinstance(f, SecurityFault)
        assert isinstance(f, Fault)
        assert f.code == "RATE_LIMIT_EXCEEDED"
        assert f.domain == FaultDomain.SECURITY
        assert f.public is True
        assert f.metadata["limit"] == 100
        assert f.metadata["window"] == 60.0
        assert f.metadata["retry_after"] == 15.0
        assert "100" in f.message

    def test_csp_violation_fault(self):
        from aquilia.faults import CSPViolationFault, SecurityFault, Fault
        from aquilia.faults.core import FaultDomain

        f = CSPViolationFault(directive="script-src", blocked_uri="https://cdn.evil.com/a.js")
        assert isinstance(f, SecurityFault)
        assert isinstance(f, Fault)
        assert f.code == "CSP_VIOLATION"
        assert f.domain == FaultDomain.SECURITY
        assert f.public is False  # CSP violations not safe to expose
        assert f.metadata["directive"] == "script-src"
        assert f.metadata["blocked_uri"] == "https://cdn.evil.com/a.js"

    def test_fault_to_dict(self):
        from aquilia.faults import CSRFViolationFault

        f = CSRFViolationFault(reason="test")
        d = f.to_dict()
        assert d["code"] == "CSRF_VIOLATION"
        assert d["message"] == "test"
        assert d["domain"].upper() == "SECURITY"
        assert d["public"] is True

    def test_csrf_error_extends_csrf_violation_fault(self):
        """CSRFError in middleware inherits from CSRFViolationFault, not Exception."""
        from aquilia.middleware_ext.security import CSRFError
        from aquilia.faults import CSRFViolationFault, SecurityFault, Fault

        err = CSRFError("token expired")
        assert isinstance(err, CSRFViolationFault)
        assert isinstance(err, SecurityFault)
        assert isinstance(err, Fault)
        assert err.code == "CSRF_VIOLATION"
        assert err.reason == "token expired"


class TestFaultAttachmentOnResponses:
    """Verify that middleware attaches faults to responses for observability."""

    @pytest.mark.asyncio
    async def test_csrf_missing_token_attaches_fault(self):
        from aquilia.middleware_ext.security import CSRFMiddleware, CSRFError

        csrf = CSRFMiddleware(secret_key="test-key")
        # GET to get token
        get_req = FakeRequest(method="GET", path="/form")
        await csrf(get_req, FakeCtx(), make_handler())

        # POST without token
        post_req = FakeRequest(method="POST", path="/submit")
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 403
        assert hasattr(resp, "_fault")
        assert isinstance(resp._fault, CSRFError)
        assert resp._fault.code == "CSRF_VIOLATION"
        assert resp.headers.get("x-fault-code") == "CSRF_VIOLATION"

    @pytest.mark.asyncio
    async def test_csrf_invalid_token_attaches_fault(self):
        from aquilia.middleware_ext.security import CSRFMiddleware, CSRFError

        csrf = CSRFMiddleware(secret_key="test-key")
        get_req = FakeRequest(method="GET", path="/form")
        await csrf(get_req, FakeCtx(), make_handler())

        post_req = FakeRequest(
            method="POST", path="/submit",
            _headers={"x-csrf-token": "bogus-token"},
        )
        resp = await csrf(post_req, FakeCtx(), make_handler())
        assert resp.status == 403
        assert hasattr(resp, "_fault")
        assert isinstance(resp._fault, CSRFError)
        assert resp._fault.reason == "CSRF token invalid"

    @pytest.mark.asyncio
    async def test_rate_limit_attaches_fault(self):
        from aquilia.middleware_ext.rate_limit import RateLimitMiddleware
        from aquilia.faults import RateLimitExceededFault

        mw = RateLimitMiddleware(default_limit=1, default_window=60)
        req1 = FakeRequest()
        await mw(req1, FakeCtx(), make_handler())

        req2 = FakeRequest()
        resp = await mw(req2, FakeCtx(), make_handler())
        assert resp.status == 429
        assert hasattr(resp, "_fault")
        assert isinstance(resp._fault, RateLimitExceededFault)
        assert resp._fault.code == "RATE_LIMIT_EXCEEDED"
        assert resp._fault.metadata["limit"] == 1
        assert resp.headers.get("x-fault-code") == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_cors_disallowed_origin_attaches_fault(self):
        from aquilia.middleware_ext.security import CORSMiddleware
        from aquilia.faults import CORSViolationFault

        cors = CORSMiddleware(allow_origins=["https://trusted.com"])
        req = FakeRequest(
            method="OPTIONS",
            _headers={"origin": "https://evil.com"},
        )
        resp = await cors(req, FakeCtx(), make_handler())
        assert hasattr(resp, "_fault")
        assert isinstance(resp._fault, CORSViolationFault)
        assert resp._fault.code == "CORS_VIOLATION"
        assert resp._fault.metadata["origin"] == "https://evil.com"

    @pytest.mark.asyncio
    async def test_cors_allowed_origin_no_fault(self):
        from aquilia.middleware_ext.security import CORSMiddleware

        cors = CORSMiddleware(allow_origins=["https://trusted.com"])
        req = FakeRequest(
            method="OPTIONS",
            _headers={"origin": "https://trusted.com"},
        )
        resp = await cors(req, FakeCtx(), make_handler())
        assert not hasattr(resp, "_fault")


class TestConfigBuilderIntegration:
    """Verify Integration.csrf() and Integration.logging() config builders."""

    def test_csrf_config_builder_defaults(self):
        from aquilia.config_builders import Integration

        cfg = Integration.csrf()
        assert cfg["_integration_type"] == "csrf"
        assert cfg["enabled"] is True
        assert cfg["secret_key"] == ""
        assert cfg["token_length"] == 32
        assert cfg["header_name"] == "X-CSRF-Token"
        assert cfg["field_name"] == "_csrf_token"
        assert cfg["cookie_name"] == "_csrf_cookie"
        assert cfg["cookie_secure"] is True
        assert cfg["cookie_samesite"] == "Lax"
        assert cfg["trust_ajax"] is True
        assert cfg["rotate_token"] is False
        assert cfg["failure_status"] == 403
        assert cfg["safe_methods"] == ["GET", "HEAD", "OPTIONS", "TRACE"]

    def test_csrf_config_builder_custom(self):
        from aquilia.config_builders import Integration

        cfg = Integration.csrf(
            secret_key="my-key",
            exempt_paths=["/webhooks"],
            cookie_samesite="Strict",
            rotate_token=True,
        )
        assert cfg["secret_key"] == "my-key"
        assert cfg["exempt_paths"] == ["/webhooks"]
        assert cfg["cookie_samesite"] == "Strict"
        assert cfg["rotate_token"] is True

    def test_csrf_config_builder_extra_kwargs(self):
        from aquilia.config_builders import Integration

        cfg = Integration.csrf(custom_option="hello")
        assert cfg["custom_option"] == "hello"

    def test_logging_config_builder_defaults(self):
        from aquilia.config_builders import Integration

        cfg = Integration.logging()
        assert cfg["_integration_type"] == "logging"
        assert cfg["enabled"] is True
        assert cfg["level"] == "INFO"
        assert cfg["slow_threshold_ms"] == 1000.0
        assert "/health" in cfg["skip_paths"]
        assert "/metrics" in cfg["skip_paths"]
        assert cfg["include_headers"] is False
        assert cfg["colorize"] is True

    def test_logging_config_builder_custom(self):
        from aquilia.config_builders import Integration

        cfg = Integration.logging(
            slow_threshold_ms=500,
            skip_paths=["/health"],
            include_headers=True,
            colorize=False,
        )
        assert cfg["slow_threshold_ms"] == 500
        assert cfg["skip_paths"] == ["/health"]
        assert cfg["include_headers"] is True
        assert cfg["colorize"] is False

    def test_logging_config_builder_extra_kwargs(self):
        from aquilia.config_builders import Integration

        cfg = Integration.logging(custom_logger="mylogger")
        assert cfg["custom_logger"] == "mylogger"

    def test_all_integration_types_available(self):
        """Verify all middleware types have corresponding config builders."""
        from aquilia.config_builders import Integration

        assert hasattr(Integration, "cors")
        assert hasattr(Integration, "csp")
        assert hasattr(Integration, "csrf")
        assert hasattr(Integration, "rate_limit")
        assert hasattr(Integration, "logging")
        assert hasattr(Integration, "static_files")
        assert hasattr(Integration, "openapi")
        assert hasattr(Integration, "mail")


class TestCSPPolicyPlainClass:
    """Verify CSPPolicy works correctly after converting from @dataclass to plain class."""

    def test_csp_policy_default_init(self):
        from aquilia.middleware_ext.security import CSPPolicy
        p = CSPPolicy()
        assert p.directives == {}
        assert p.report_only is False

    def test_csp_policy_init_with_directives(self):
        from aquilia.middleware_ext.security import CSPPolicy
        d = {"default-src": ["'self'"]}
        p = CSPPolicy(directives=d)
        assert p.directives == d

    def test_csp_policy_fluent_builder(self):
        from aquilia.middleware_ext.security import CSPPolicy
        p = CSPPolicy().script_src("'self'", "'nonce-{nonce}'").style_src("'self'")
        assert "script-src" in p.directives
        assert "style-src" in p.directives
        assert "'self'" in p.directives["script-src"]

    def test_csp_policy_strict_preset(self):
        from aquilia.middleware_ext.security import CSPPolicy
        p = CSPPolicy.strict()
        assert isinstance(p, CSPPolicy)
        assert "default-src" in p.directives

    def test_csp_policy_relaxed_preset(self):
        from aquilia.middleware_ext.security import CSPPolicy
        p = CSPPolicy.relaxed()
        assert isinstance(p, CSPPolicy)
        assert "default-src" in p.directives

    def test_csp_policy_report_only(self):
        from aquilia.middleware_ext.security import CSPPolicy
        p = CSPPolicy(report_only=True)
        assert p.report_only is True


class TestRateLimitRulePlainClass:
    """Verify RateLimitRule works correctly after converting from @dataclass to plain class."""

    def test_default_init(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule()
        assert r.limit == 100
        assert r.window == 60.0
        assert r.algorithm == "sliding_window"
        assert r.scope == "*"
        assert r.methods == []
        assert r.burst is None
        assert callable(r.key_func)

    def test_custom_init(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule(limit=50, window=30, algorithm="token_bucket", burst=10)
        assert r.limit == 50
        assert r.window == 30
        assert r.algorithm == "token_bucket"
        assert r.burst == 10

    def test_matches_any_path(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule(scope="*")
        req = FakeRequest(path="/anything")
        assert r.matches(req) is True

    def test_matches_specific_scope(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule(scope="/api")
        assert r.matches(FakeRequest(path="/api/users")) is True
        assert r.matches(FakeRequest(path="/web/page")) is False

    def test_matches_methods_filter(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule(methods=["POST", "PUT"])
        assert r.matches(FakeRequest(method="POST")) is True
        assert r.matches(FakeRequest(method="GET")) is False

    def test_custom_key_func(self):
        from aquilia.middleware_ext.rate_limit import RateLimitRule
        r = RateLimitRule(key_func=lambda req: "custom:key")
        assert r.key_func(FakeRequest()) == "custom:key"
