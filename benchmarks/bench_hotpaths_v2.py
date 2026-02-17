"""
Micro-benchmarks for optimized hot paths.
Run with: python benchmarks/bench_hotpaths_v2.py
"""
import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def bench(label, fn, n=100_000):
    """Synchronous benchmark."""
    start = time.perf_counter()
    for _ in range(n):
        fn()
    elapsed = time.perf_counter() - start
    print(f"  {label}: {n/elapsed:,.0f} ops/s ({elapsed*1e6/n:.1f} µs/op)")


async def abench(label, fn, n=100_000):
    """Async benchmark."""
    start = time.perf_counter()
    for _ in range(n):
        await fn()
    elapsed = time.perf_counter() - start
    print(f"  {label}: {n/elapsed:,.0f} ops/s ({elapsed*1e6/n:.1f} µs/op)")


async def main():
    print("=" * 60)
    print("Aquilia Hot Path Micro-Benchmarks (post-optimization)")
    print("=" * 60)

    # 1. Route matching
    print("\n📍 Route Matching:")
    from aquilia.controller.router import ControllerRouter
    from aquilia.controller.compiler import CompiledRoute
    from unittest.mock import MagicMock

    router = ControllerRouter()
    # Add a static route
    mock_route = MagicMock(spec=CompiledRoute)
    mock_route.http_method = "GET"
    mock_route.full_path = "/ping"
    mock_route.compiled_pattern = MagicMock()
    mock_route.compiled_pattern.match = MagicMock(return_value={"_matched": True})
    router._static_routes = {"/ping": {"GET": (mock_route, {})}}
    router._dynamic_routes = {"GET": []}

    bench("Static match /ping", lambda: router.match_sync("/ping", "GET"))

    # 2. Request construction
    print("\n📦 Request Construction:")
    from aquilia.request import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/ping",
        "query_string": b"",
        "headers": [(b"host", b"localhost")],
    }

    async def noop_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    bench("Request(scope, receive)", lambda: Request(scope, noop_receive), n=200_000)

    # 3. Response.json
    print("\n📤 Response.json:")
    from aquilia.response import Response

    obj = {"message": "hello", "ts": "2026-01-01T00:00:00"}
    bench("Response.json(dict)", lambda: Response.json(obj), n=200_000)

    # 4. Response(bytes)
    print("\n📤 Response(bytes):")
    bench("Response(b'pong')", lambda: Response(content=b"pong", headers={"content-type": "text/plain"}), n=200_000)

    # 5. RequestId generation
    print("\n🆔 Request ID Generation:")
    _urandom = os.urandom
    bench("os.urandom(16).hex()", lambda: _urandom(16).hex(), n=500_000)

    # 6. DI container create_request_scope
    print("\n🏗️  DI Container:")
    from aquilia.di import Container
    app_container = Container(scope="app")

    bench("create_request_scope()", lambda: app_container.create_request_scope(), n=100_000)

    # 7. send_asgi simulation
    print("\n📡 send_asgi:")
    response = Response.json({"message": "hello"})

    async def fake_send(msg):
        pass

    await abench("send_asgi(bytes)", lambda: response.send_asgi(fake_send), n=100_000)

    # 8. Full middleware chain (just wrappers)
    print("\n⛓️  Middleware Chain:")
    from aquilia.middleware import MiddlewareStack

    stack = MiddlewareStack()

    async def final_handler(request, ctx):
        return Response(content=b"ok")

    chain = stack.build_handler(final_handler)

    from aquilia.controller.base import RequestCtx
    req = Request(scope, noop_receive)
    ctx = RequestCtx(request=req, identity=None, session=None, container=None)

    await abench("Empty middleware chain", lambda: chain(req, ctx), n=100_000)

    # 9. RequestCtx construction
    print("\n🏷️  RequestCtx Construction:")
    bench("RequestCtx(request, None, None, None)", lambda: RequestCtx(request=req, identity=None, session=None, container=None), n=500_000)

    # 10. Full simulated request (route + Request + ctx + middleware + send)
    print("\n🔥 Full Simulated Request (no real I/O):")
    from aquilia.controller.router import ControllerRouter as CR2

    router2 = CR2()
    mr = MagicMock(spec=CompiledRoute)
    mr.http_method = "GET"
    mr.full_path = "/json"
    mr.compiled_pattern = MagicMock()
    mr.compiled_pattern.match = MagicMock(return_value={"_matched": True})
    router2._static_routes = {"GET": {"/json": (mr, {}, {})}}
    router2._dynamic_routes = {"GET": []}
    router2._initialized = True

    async def full_sim():
        r = Request(scope, noop_receive)
        m = router2.match_sync("/json", "GET")
        c = app_container.create_request_scope()
        ct = RequestCtx(request=r, identity=None, session=None, container=c)
        resp = Response.json({"message": "hello"})
        await resp.send_asgi(fake_send)

    await abench("Full simulated request", full_sim, n=50_000)

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
