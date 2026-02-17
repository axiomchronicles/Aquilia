#!/usr/bin/env python3
"""
Aquilia Micro-Benchmark Harness
================================
Profiles the critical hot-paths of the framework:

1. Route matching (PatternMatcher._try_match)
2. Middleware chain build & invocation
3. DI container resolve_async (cached + uncached)
4. Request object construction & property access
5. Response JSON serialization & send_asgi
6. Header preparation (_prepare_headers)
7. QuerySet clone & filter chain
8. Request-scope container creation

Run:
    python benchmarks/bench_hotpaths.py

Output: table of operations with ops/sec, mean latency, p99, memory.
"""

import asyncio
import gc
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_time(ns: float) -> str:
    if ns < 1_000:
        return f"{ns:.0f} ns"
    elif ns < 1_000_000:
        return f"{ns / 1_000:.2f} µs"
    elif ns < 1_000_000_000:
        return f"{ns / 1_000_000:.2f} ms"
    else:
        return f"{ns / 1_000_000_000:.3f} s"


async def _bench_async(name: str, coro_factory, *, warmup=100, iters=10_000):
    """Benchmark an async callable, return stats dict."""
    # Warmup
    for _ in range(warmup):
        await coro_factory()
    
    gc.disable()
    tracemalloc.start()
    mem_before = tracemalloc.get_traced_memory()[0]
    
    times = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        await coro_factory()
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)
    
    mem_after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    gc.enable()
    
    times.sort()
    mean_ns = statistics.mean(times)
    p50_ns = times[len(times) // 2]
    p99_ns = times[int(len(times) * 0.99)]
    p999_ns = times[int(len(times) * 0.999)]
    mem_delta = mem_after - mem_before
    
    return {
        "name": name,
        "iters": iters,
        "mean": mean_ns,
        "p50": p50_ns,
        "p99": p99_ns,
        "p999": p999_ns,
        "ops_sec": 1_000_000_000 / mean_ns if mean_ns > 0 else float("inf"),
        "mem_delta_bytes": mem_delta,
    }


def _bench_sync(name: str, fn, *, warmup=100, iters=10_000):
    """Benchmark a sync callable."""
    for _ in range(warmup):
        fn()
    
    gc.disable()
    tracemalloc.start()
    mem_before = tracemalloc.get_traced_memory()[0]
    
    times = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)
    
    mem_after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    gc.enable()
    
    times.sort()
    mean_ns = statistics.mean(times)
    p50_ns = times[len(times) // 2]
    p99_ns = times[int(len(times) * 0.99)]
    p999_ns = times[int(len(times) * 0.999)]
    mem_delta = mem_after - mem_before
    
    return {
        "name": name,
        "iters": iters,
        "mean": mean_ns,
        "p50": p50_ns,
        "p99": p99_ns,
        "p999": p999_ns,
        "ops_sec": 1_000_000_000 / mean_ns if mean_ns > 0 else float("inf"),
        "mem_delta_bytes": mem_delta,
    }


def _print_results(results: list[dict]):
    print("\n" + "=" * 100)
    print(f"{'Benchmark':<45} {'ops/sec':>12} {'mean':>12} {'p50':>12} {'p99':>12} {'p999':>12} {'mem Δ':>10}")
    print("-" * 100)
    for r in results:
        print(
            f"{r['name']:<45} "
            f"{r['ops_sec']:>10,.0f}  "
            f"{_format_time(r['mean']):>12} "
            f"{_format_time(r['p50']):>12} "
            f"{_format_time(r['p99']):>12} "
            f"{_format_time(r['p999']):>12} "
            f"{r['mem_delta_bytes']:>8,}B"
        )
    print("=" * 100)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_scope(path="/users/42", method="GET"):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"page=1&limit=20",
        "headers": [
            (b"host", b"localhost:8000"),
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"authorization", b"Bearer tok123"),
            (b"x-request-id", b"req-abc-123"),
            (b"cookie", b"session=abc123; theme=dark"),
            (b"user-agent", b"BenchBot/1.0"),
        ],
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 54321),
        "root_path": "",
    }


async def _dummy_receive():
    return {"type": "http.request", "body": b'{"name":"test"}', "more_body": False}


_sent_messages = []

async def _dummy_send(msg):
    _sent_messages.append(msg)


# ── Benchmark Suites ─────────────────────────────────────────────────────────

async def bench_request_construction():
    """Benchmark Request object creation."""
    from aquilia.request import Request
    scope = _make_scope()
    
    return _bench_sync(
        "Request.__init__",
        lambda: Request(scope, _dummy_receive),
        iters=50_000,
    )


async def bench_request_properties():
    """Benchmark Request property access (headers, query, cookies)."""
    from aquilia.request import Request
    scope = _make_scope()
    req = Request(scope, _dummy_receive)
    
    def access_props():
        _ = req.method
        _ = req.path
        _ = req.headers
        _ = req.query_params
        _ = req.cookies
        _ = req.client_ip()
        _ = req.content_type()
    
    return _bench_sync(
        "Request property access (7 props)",
        access_props,
        iters=50_000,
    )


async def bench_headers_construction():
    """Benchmark Headers construction from raw ASGI headers."""
    from aquilia._datastructures import Headers
    raw = [
        (b"host", b"localhost:8000"),
        (b"accept", b"application/json"),
        (b"content-type", b"application/json"),
        (b"authorization", b"Bearer tok123"),
        (b"x-request-id", b"req-abc-123"),
        (b"cookie", b"session=abc123; theme=dark"),
        (b"user-agent", b"BenchBot/1.0"),
        (b"accept-encoding", b"gzip, br"),
        (b"accept-language", b"en-US,en;q=0.9"),
        (b"cache-control", b"no-cache"),
    ]
    
    return _bench_sync(
        "Headers.__init__ (10 headers)",
        lambda: Headers(raw=raw),
        iters=50_000,
    )


async def bench_response_json():
    """Benchmark Response.json() creation."""
    from aquilia.response import Response
    data = {
        "users": [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com", "active": True}
            for i in range(10)
        ],
        "total": 10,
        "page": 1,
    }
    
    return _bench_sync(
        "Response.json() (10 items)",
        lambda: Response.json(data),
        iters=20_000,
    )


async def bench_response_send_asgi():
    """Benchmark full Response.send_asgi cycle."""
    from aquilia.response import Response
    data = {"message": "Hello, World!", "status": "ok"}
    
    async def run():
        global _sent_messages
        _sent_messages = []
        resp = Response.json(data)
        await resp.send_asgi(_dummy_send)
    
    return await _bench_async(
        "Response.send_asgi (JSON)",
        run,
        iters=10_000,
    )


async def bench_response_prepare_headers():
    """Benchmark _prepare_headers conversion."""
    from aquilia.response import Response
    resp = Response.json({"test": True})
    resp.headers["x-request-id"] = "abc123"
    resp.headers["x-custom"] = "value"
    resp.headers["set-cookie"] = ["a=1", "b=2"]
    
    return _bench_sync(
        "Response._prepare_headers",
        resp._prepare_headers,
        iters=50_000,
    )


async def bench_middleware_chain_build():
    """Benchmark middleware chain building."""
    from aquilia.middleware import MiddlewareStack, RequestIdMiddleware, LoggingMiddleware
    
    stack = MiddlewareStack()
    stack.add(RequestIdMiddleware(), scope="global", priority=1, name="rid")
    stack.add(LoggingMiddleware(), scope="global", priority=2, name="log")
    
    async def final_handler(req, ctx):
        from aquilia.response import Response
        return Response.json({"ok": True})
    
    return _bench_sync(
        "MiddlewareStack.build_handler (2 mw)",
        lambda: stack.build_handler(final_handler),
        iters=50_000,
    )


async def bench_middleware_sort():
    """Benchmark middleware sorting after add."""
    from aquilia.middleware import MiddlewareStack
    
    async def noop(req, ctx, next_handler):
        return await next_handler(req, ctx)
    
    def build_stack():
        stack = MiddlewareStack()
        for i in range(10):
            stack.add(noop, scope="global", priority=i, name=f"mw{i}")
    
    return _bench_sync(
        "MiddlewareStack.add + sort (10 mw)",
        build_stack,
        iters=5_000,
    )


async def bench_di_resolve_cached():
    """Benchmark DI container cached resolution."""
    from aquilia.di.core import Container
    from aquilia.di.providers import ValueProvider
    
    container = Container(scope="app")
    container.register(ValueProvider(value="hello", token="greeting", scope="singleton"))
    # Pre-cache
    await container.resolve_async("greeting")
    
    return await _bench_async(
        "Container.resolve_async (cached)",
        lambda: container.resolve_async("greeting"),
        iters=50_000,
    )


async def bench_di_resolve_uncached():
    """Benchmark DI container uncached resolution (transient)."""
    from aquilia.di.core import Container
    from aquilia.di.providers import ValueProvider
    
    container = Container(scope="app")
    container.register(ValueProvider(value="hello", token="greeting", scope="singleton"))
    
    async def resolve():
        container._cache.clear()
        return await container.resolve_async("greeting")
    
    return await _bench_async(
        "Container.resolve_async (uncached)",
        resolve,
        iters=10_000,
    )


async def bench_di_request_scope_create():
    """Benchmark creating a request-scoped child container."""
    from aquilia.di.core import Container
    from aquilia.di.providers import ValueProvider
    
    parent = Container(scope="app")
    for i in range(20):
        parent.register(ValueProvider(value=f"val{i}", token=f"tok{i}", scope="singleton"))
    
    return _bench_sync(
        "Container.create_request_scope (20 providers)",
        parent.create_request_scope,
        iters=20_000,
    )


async def bench_route_matching():
    """Benchmark route matching via PatternMatcher."""
    from aquilia.patterns.cache import compile_pattern
    from aquilia.patterns.matcher import PatternMatcher
    
    matcher = PatternMatcher()
    
    patterns_raw = [
        "/users",
        "/users/\u00abid:int\u00bb",
        "/users/\u00abid:int\u00bb/posts",
        "/users/\u00abid:int\u00bb/posts/\u00abpost_id:int\u00bb",
        "/products",
        "/products/\u00abslug:str\u00bb",
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/orders/\u00abid:int\u00bb/items",
    ]
    for raw in patterns_raw:
        compiled = compile_pattern(raw, use_cache=False)
        matcher.add_pattern(compiled)
    
    return await _bench_async(
        "PatternMatcher.match (10 routes, hit)",
        lambda: matcher.match("/users/42", {}),
        iters=20_000,
    )


async def bench_route_matching_miss():
    """Benchmark route matching – miss case (worst case scan)."""
    from aquilia.patterns.cache import compile_pattern
    from aquilia.patterns.matcher import PatternMatcher
    
    matcher = PatternMatcher()
    
    patterns_raw = [
        "/users",
        "/users/\u00abid:int\u00bb",
        "/users/\u00abid:int\u00bb/posts",
        "/products",
        "/products/\u00abslug:str\u00bb",
        "/api/v1/health",
    ]
    for raw in patterns_raw:
        compiled = compile_pattern(raw, use_cache=False)
        matcher.add_pattern(compiled)
    
    return await _bench_async(
        "PatternMatcher.match (6 routes, miss)",
        lambda: matcher.match("/nonexistent/path", {}),
        iters=20_000,
    )


async def bench_query_clone():
    """Benchmark QuerySet cloning (immutable chain)."""
    from aquilia.models.query import Q as QuerySet
    
    # We need a mock model & db to test Q
    class FakeDB:
        dialect = "sqlite"
    
    class FakeModel:
        _pk_attr = "id"
        _table_name = "users"
    
    qs = QuerySet("users", FakeModel, FakeDB())
    
    def chain():
        qs.filter(active=True).filter(age__gt=18).order("-created_at").limit(10)
    
    return _bench_sync(
        "Q.filter().filter().order().limit()",
        chain,
        iters=20_000,
    )


async def bench_multidict_operations():
    """Benchmark MultiDict creation and access."""
    from aquilia._datastructures import MultiDict
    
    items = [(f"key{i}", f"value{i}") for i in range(20)]
    
    def ops():
        md = MultiDict(items)
        _ = md.get("key5")
        _ = md.get_all("key10")
        _ = md.items_list()
    
    return _bench_sync(
        "MultiDict create + access (20 items)",
        ops,
        iters=20_000,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("Aquilia Micro-Benchmark Suite")
    print(f"Python {sys.version}")
    print(f"Platform: {sys.platform}")
    print()
    
    results = []
    
    benchmarks = [
        bench_request_construction,
        bench_request_properties,
        bench_headers_construction,
        bench_response_json,
        bench_response_send_asgi,
        bench_response_prepare_headers,
        bench_middleware_chain_build,
        bench_middleware_sort,
        bench_di_resolve_cached,
        bench_di_resolve_uncached,
        bench_di_request_scope_create,
        bench_route_matching,
        bench_route_matching_miss,
        bench_query_clone,
        bench_multidict_operations,
    ]
    
    for bench_fn in benchmarks:
        try:
            result = await bench_fn()
            results.append(result)
            print(f"  ✓ {result['name']}")
        except Exception as e:
            print(f"  ✗ {bench_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    _print_results(results)
    return results


if __name__ == "__main__":
    asyncio.run(main())
