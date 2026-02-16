"""
AquilaCache — HTTP response caching middleware.

Integrates with Aquilia's middleware stack to provide:
- Automatic response caching for GET/HEAD requests
- ETag generation and validation
- Cache-Control header management
- Vary header support
- Namespace isolation per route pattern
- Stale-while-revalidate support
- Cache bypass via X-Cache-Bypass header
- Route-level TTL overrides via response headers
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from aquilia.response import Response

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.controller.base import RequestCtx
    from .service import CacheService

logger = logging.getLogger("aquilia.cache.middleware")


class CacheMiddleware:
    """
    HTTP response caching middleware.
    
    Caches response bodies for cacheable requests and serves them
    directly on subsequent identical requests, bypassing the handler.
    
    Features:
    - Only caches GET/HEAD by default
    - Respects Cache-Control: no-cache, no-store
    - Generates and validates ETags
    - Handles Vary headers
    - Stale-while-revalidate: serve stale content while refreshing
    - X-Cache-Bypass header to skip cache for debugging
    - X-Cache-TTL response header for route-level TTL overrides
    - Integrates with CacheService for backend flexibility
    
    Usage::
    
        server.middleware_stack.add(
            CacheMiddleware(cache_service, default_ttl=60),
            scope="global",
            priority=25,
            name="response_cache",
        )
    """
    
    def __init__(
        self,
        cache_service: "CacheService",
        default_ttl: int = 60,
        cacheable_methods: Tuple[str, ...] = ("GET", "HEAD"),
        vary_headers: Tuple[str, ...] = ("Accept", "Accept-Encoding"),
        namespace: str = "http_response",
        stale_while_revalidate: int = 0,
    ):
        self._cache = cache_service
        self._default_ttl = default_ttl
        self._cacheable_methods = cacheable_methods
        self._vary_headers = vary_headers
        self._namespace = namespace
        self._stale_while_revalidate = stale_while_revalidate
    
    async def __call__(
        self,
        request: "Request",
        ctx: "RequestCtx",
        next_handler: Any,
    ) -> "Response":
        """Middleware handler."""
        # Only cache allowed methods
        if request.method not in self._cacheable_methods:
            return await next_handler(request, ctx)
        
        # Check for cache bypass header
        bypass = ""
        if hasattr(request, "headers") and hasattr(request.headers, "get"):
            bypass = request.headers.get("x-cache-bypass", "") or ""
        if bypass.lower() in ("1", "true", "yes"):
            response = await next_handler(request, ctx)
            response.headers["X-Cache"] = "BYPASS"
            return response
        
        # Respect no-cache/no-store directives
        cache_control = ""
        if hasattr(request, "headers") and hasattr(request.headers, "get"):
            cache_control = request.headers.get("cache-control", "") or ""
        
        if "no-store" in cache_control:
            return await next_handler(request, ctx)
        
        # Build cache key from request
        cache_key = self._build_request_key(request)
        
        # Check for cached response
        cached_data = await self._cache.get(cache_key, namespace=self._namespace)
        
        if cached_data and isinstance(cached_data, dict):
            # Check if stale
            cached_at = cached_data.get("cached_at", 0)
            ttl_used = cached_data.get("ttl", self._default_ttl)
            age = time.time() - cached_at
            is_stale = age > ttl_used
            
            # Check ETag with If-None-Match
            etag = cached_data.get("etag", "")
            if_none_match = ""
            if hasattr(request, "headers") and hasattr(request.headers, "get"):
                if_none_match = request.headers.get("if-none-match", "") or ""
            
            if if_none_match and if_none_match == etag:
                return Response(content=b"", status=304, headers={"ETag": etag})
            
            # Handle no-cache: must revalidate but can serve stale during revalidation
            if "no-cache" in cache_control:
                # Must revalidate — go to handler
                pass
            elif is_stale and self._stale_while_revalidate > 0:
                # Stale-while-revalidate: serve stale, refresh in background
                stale_age = age - ttl_used
                if stale_age <= self._stale_while_revalidate:
                    # Serve stale content
                    headers = cached_data.get("headers", {})
                    headers["X-Cache"] = "STALE"
                    headers["ETag"] = etag
                    headers["Age"] = str(int(age))
                    
                    # Trigger background refresh
                    asyncio.ensure_future(
                        self._background_refresh(request, ctx, next_handler, cache_key)
                    )
                    
                    return Response(
                        content=cached_data.get("body", b""),
                        status=cached_data.get("status", 200),
                        headers=headers,
                    )
            elif not is_stale:
                # Fresh — serve from cache
                headers = cached_data.get("headers", {})
                headers["X-Cache"] = "HIT"
                headers["ETag"] = etag
                headers["Age"] = str(int(age))
                
                return Response(
                    content=cached_data.get("body", b""),
                    status=cached_data.get("status", 200),
                    headers=headers,
                )
        
        # Cache miss — call handler
        response = await next_handler(request, ctx)
        
        # Only cache successful responses
        if response.status < 200 or response.status >= 400:
            return response
        
        # Check response-level cache control
        resp_cache_control = ""
        if hasattr(response, "headers"):
            resp_cache_control = response.headers.get("Cache-Control", "") or ""
        if "no-store" in resp_cache_control or "private" in resp_cache_control:
            return response
        
        # Determine TTL (route-level override via X-Cache-TTL header)
        ttl = self._default_ttl
        if hasattr(response, "headers"):
            custom_ttl = response.headers.get("X-Cache-TTL", "")
            if custom_ttl and custom_ttl.isdigit():
                ttl = int(custom_ttl)
        
        # Generate ETag
        body = response.content if hasattr(response, "content") else b""
        if isinstance(body, str):
            body = body.encode("utf-8")
        etag = self._generate_etag(body)
        
        # Store in cache
        cache_data = {
            "body": body,
            "status": response.status,
            "headers": dict(response.headers) if hasattr(response, "headers") else {},
            "etag": etag,
            "cached_at": time.time(),
            "ttl": ttl,
        }
        
        await self._cache.set(
            cache_key,
            cache_data,
            ttl=ttl + self._stale_while_revalidate,  # Keep longer for stale serving
            namespace=self._namespace,
        )
        
        # Add cache headers to response
        response.headers["X-Cache"] = "MISS"
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = f"max-age={ttl}"
        if self._stale_while_revalidate > 0:
            response.headers["Cache-Control"] += f", stale-while-revalidate={self._stale_while_revalidate}"
        
        return response
    
    async def _background_refresh(
        self,
        request: "Request",
        ctx: "RequestCtx",
        next_handler: Any,
        cache_key: str,
    ) -> None:
        """Refresh cache entry in background (stale-while-revalidate)."""
        try:
            response = await next_handler(request, ctx)
            if 200 <= response.status < 400:
                body = response.content if hasattr(response, "content") else b""
                if isinstance(body, str):
                    body = body.encode("utf-8")
                
                etag = self._generate_etag(body)
                cache_data = {
                    "body": body,
                    "status": response.status,
                    "headers": dict(response.headers) if hasattr(response, "headers") else {},
                    "etag": etag,
                    "cached_at": time.time(),
                    "ttl": self._default_ttl,
                }
                await self._cache.set(
                    cache_key,
                    cache_data,
                    ttl=self._default_ttl + self._stale_while_revalidate,
                    namespace=self._namespace,
                )
                logger.debug(f"Background refresh completed for {cache_key}")
        except Exception as e:
            logger.warning(f"Background cache refresh failed: {e}")
    
    def _build_request_key(self, request: "Request") -> str:
        """Build a cache key from request attributes."""
        parts = [request.method, request.path]
        
        # Include query string
        if hasattr(request, "query_string") and request.query_string:
            parts.append(str(request.query_string))
        
        # Include Vary headers
        for header in self._vary_headers:
            if hasattr(request, "headers") and hasattr(request.headers, "get"):
                val = request.headers.get(header, "")
                if val:
                    parts.append(f"{header}={val}")
        
        return ":".join(parts)
    
    def _generate_etag(self, body: bytes) -> str:
        """Generate ETag from response body."""
        digest = hashlib.md5(body).hexdigest()[:16]
        return f'W/"{digest}"'
