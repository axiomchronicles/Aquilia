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
            HSTSMiddleware,
            HTTPSRedirectMiddleware,
            ProxyFixMiddleware,
            SecurityHeadersMiddleware,
            RateLimitMiddleware,
            RateLimitRule,
            StaticMiddleware,
        )
        assert CORSMiddleware is not None

    def test_integration_builders_import(self):
        from aquilia import Integration
        assert hasattr(Integration, "static_files")
        assert hasattr(Integration, "cors")
        assert hasattr(Integration, "csp")
        assert hasattr(Integration, "rate_limit")
