#!/usr/bin/env python3
"""
Performance smoke test for CI.

Ensures critical hot-paths don't regress beyond acceptable thresholds.
Exit code 0 = pass, 1 = regression detected.

Run:
    python benchmarks/perf_smoke.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Thresholds: minimum ops/sec for each benchmark.
# Set conservatively (50% of measured optimized performance on CI hardware).
THRESHOLDS = {
    "route_match_hit": 50_000,    # Optimized: ~500k; old was 5.6k
    "route_match_miss": 200_000,  # ~1.2M measured
    "di_request_scope": 200_000,  # ~2M measured
    "mw_add_sort_10": 50_000,     # ~440k measured
    "response_json": 200_000,     # ~2M measured
    "q_chain_4ops": 50_000,       # ~300k measured
}

N = 2000  # Enough to get stable measurements; fast enough for CI


def _measure(name, fn, n=N):
    """Measure sync callable."""
    for _ in range(50):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    dt = time.perf_counter() - t0
    ops = n / dt
    return name, ops


async def _measure_async(name, coro_factory, n=N):
    """Measure async callable."""
    for _ in range(50):
        await coro_factory()
    t0 = time.perf_counter()
    for _ in range(n):
        await coro_factory()
    dt = time.perf_counter() - t0
    ops = n / dt
    return name, ops


async def main():
    results = {}
    failures = []

    # 1. Route matching (hit)
    from aquilia.patterns.cache import compile_pattern
    from aquilia.patterns.matcher import PatternMatcher
    matcher = PatternMatcher()
    for raw in ['/users', '/users/\u00abid:int\u00bb', '/users/\u00abid:int\u00bb/posts',
                '/users/\u00abid:int\u00bb/posts/\u00abpost_id:int\u00bb', '/products',
                '/products/\u00abslug:str\u00bb', '/api/v1/health',
                '/api/v1/auth/login', '/api/v1/auth/register',
                '/api/v1/orders/\u00abid:int\u00bb/items']:
        matcher.add_pattern(compile_pattern(raw, use_cache=False))

    name, ops = await _measure_async("route_match_hit",
                                      lambda: matcher.match('/users/42', {}))
    results[name] = ops

    # 2. Route matching (miss)
    name, ops = await _measure_async("route_match_miss",
                                      lambda: matcher.match('/nonexistent/path', {}))
    results[name] = ops

    # 3. DI request scope
    from aquilia.di.core import Container
    from aquilia.di.providers import ValueProvider
    parent = Container(scope="app")
    for i in range(20):
        parent.register(ValueProvider(value=f"v{i}", token=f"t{i}", scope="singleton"))
    name, ops = _measure("di_request_scope", parent.create_request_scope)
    results[name] = ops

    # 4. Middleware add+sort
    from aquilia.middleware import MiddlewareStack
    async def noop(r, c, n):
        return await n(r, c)
    def build():
        s = MiddlewareStack()
        for i in range(10):
            s.add(noop, scope="global", priority=i, name=f"m{i}")
    name, ops = _measure("mw_add_sort_10", build)
    results[name] = ops

    # 5. Response.json
    from aquilia.response import Response
    data = {"users": [{"id": i} for i in range(10)], "total": 10}
    name, ops = _measure("response_json", lambda: Response.json(data))
    results[name] = ops

    # 6. Q chain
    from aquilia.models.query import Q
    class FDB:
        dialect = "sqlite"
    class FM:
        _pk_attr = "id"
        _table_name = "users"
    qs = Q("users", FM, FDB())
    def chain():
        qs.filter(active=True).filter(age__gt=18).order("-created_at").limit(10)
    name, ops = _measure("q_chain_4ops", chain)
    results[name] = ops

    # ── Report ──
    print("\nPerformance Smoke Test Results")
    print("=" * 65)
    print(f"{'Benchmark':<25} {'ops/sec':>12} {'threshold':>12} {'status':>8}")
    print("-" * 65)

    for key, threshold in THRESHOLDS.items():
        ops = results.get(key, 0)
        passed = ops >= threshold
        status = "PASS" if passed else "FAIL"
        if not passed:
            failures.append((key, ops, threshold))
        print(f"{key:<25} {ops:>10,.0f}  {threshold:>10,.0f}  {status:>8}")

    print("=" * 65)

    if failures:
        print(f"\n{len(failures)} REGRESSION(S) DETECTED:")
        for key, ops, threshold in failures:
            pct = (1 - ops / threshold) * 100
            print(f"  {key}: {ops:,.0f} ops/s < {threshold:,.0f} threshold ({pct:.1f}% below)")
        sys.exit(1)
    else:
        print("\nAll benchmarks PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
