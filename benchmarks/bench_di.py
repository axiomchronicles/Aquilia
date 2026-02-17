"""
DI Subsystem Microbenchmarks — before/after optimization.

Measures:
1. Container creation (bare, request-scope child)
2. resolve_async — cached hit
3. resolve_async — cold miss (ClassProvider instantiation)
4. resolve_async — FactoryProvider
5. create_request_scope() cost
6. shutdown() cost (empty request container)
7. Full request lifecycle (create_scope → resolve → shutdown)
8. _token_to_key / _make_cache_key overhead
9. ClassProvider dep extraction (inspect.signature) cold
"""

import asyncio
import time
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ClassProvider, FactoryProvider, ValueProvider


# ── Fixture services ─────────────────────────────────────────────────────────

class Config:
    def __init__(self):
        self.debug = False

class Logger:
    def __init__(self, config: Config):
        self.config = config

class Database:
    def __init__(self, config: Config):
        self.config = config

class UserRepo:
    def __init__(self, db: Database):
        self.db = db

class UserService:
    def __init__(self, repo: UserRepo, logger: Logger):
        self.repo = repo
        self.logger = logger

class OrderService:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

class NotificationService:
    def __init__(self, config: Config):
        self.config = config

class PaymentService:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger


def build_container() -> Container:
    """Build a container with a realistic provider graph."""
    c = Container(scope="app")
    c.register(ClassProvider(Config, scope="singleton"))
    c.register(ClassProvider(Logger, scope="singleton"))
    c.register(ClassProvider(Database, scope="singleton"))
    c.register(ClassProvider(UserRepo, scope="app"))
    c.register(ClassProvider(UserService, scope="app"))
    c.register(ClassProvider(OrderService, scope="app"))
    c.register(ClassProvider(NotificationService, scope="app"))
    c.register(ClassProvider(PaymentService, scope="app"))
    c.register(ValueProvider(42, "magic_number"))
    c.register(ValueProvider("v1.0", "app_version"))
    return c


def bench(name: str, times: list[float], unit: str = "µs"):
    """Print benchmark results."""
    factor = 1_000_000 if unit == "µs" else 1_000 if unit == "ms" else 1
    vals = [t * factor for t in times]
    med = statistics.median(vals)
    p95 = sorted(vals)[int(len(vals) * 0.95)]
    p99 = sorted(vals)[int(len(vals) * 0.99)]
    avg = statistics.mean(vals)
    mn = min(vals)
    print(f"  {name:45s}  median={med:8.2f}{unit}  p95={p95:8.2f}{unit}  "
          f"p99={p99:8.2f}{unit}  min={mn:8.2f}{unit}  avg={avg:8.2f}{unit}")


async def main():
    WARM = 500
    N = 10_000

    print("=" * 100)
    print("DI Subsystem Microbenchmarks")
    print("=" * 100)

    # ── 1. Container creation ────────────────────────────────────────
    print("\n── Container creation ──")
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        c = Container(scope="app")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("Container(scope='app')", times)

    # ── 2. create_request_scope ──────────────────────────────────────
    print("\n── create_request_scope ──")
    app = build_container()
    # warm
    for _ in range(WARM):
        app.create_request_scope()
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        child = app.create_request_scope()
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("create_request_scope()", times)

    # ── 3. resolve_async — cached hit ────────────────────────────────
    print("\n── resolve_async (cached hit) ──")
    app = build_container()
    # Pre-populate cache
    await app.resolve_async(Config)
    await app.resolve_async(Logger)
    await app.resolve_async(Database)
    await app.resolve_async(UserRepo)
    await app.resolve_async(UserService)
    # warm
    for _ in range(WARM):
        await app.resolve_async(Config)
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        await app.resolve_async(Config)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(Config) [cached]", times)

    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        await app.resolve_async(UserService)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(UserService) [cached]", times)

    # ValueProvider cached
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        await app.resolve_async("magic_number")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async('magic_number') [ValueProvider cached]", times)

    # ── 4. resolve_async — cold miss (ClassProvider) ─────────────────
    print("\n── resolve_async (cold miss — ClassProvider instantiation) ──")
    times = []
    for _ in range(N):
        fresh = Container(scope="app")
        fresh.register(ClassProvider(Config, scope="singleton"))
        t0 = time.perf_counter_ns()
        await fresh.resolve_async(Config)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(Config) [cold, no deps]", times)

    times = []
    for _ in range(N):
        fresh = Container(scope="app")
        fresh.register(ClassProvider(Config, scope="singleton"))
        fresh.register(ClassProvider(Logger, scope="singleton"))
        t0 = time.perf_counter_ns()
        await fresh.resolve_async(Logger)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(Logger) [cold, 1 dep]", times)

    # ── 5. resolve_async — FactoryProvider ───────────────────────────
    print("\n── resolve_async (FactoryProvider) ──")
    async def make_config():
        return Config()
    fp = FactoryProvider(make_config, scope="singleton", name="config_factory")
    fc = Container(scope="app")
    fc.register(fp)
    await fc.resolve_async("config_factory")  # prime cache
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        await fc.resolve_async("config_factory")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(FactoryProvider) [cached]", times)

    # Cold factory
    times = []
    for _ in range(N):
        fc2 = Container(scope="app")
        fp2 = FactoryProvider(make_config, scope="singleton", name="config_factory")
        fc2.register(fp2)
        t0 = time.perf_counter_ns()
        await fc2.resolve_async("config_factory")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("resolve_async(FactoryProvider) [cold]", times)

    # ── 6. shutdown() — empty request container ──────────────────────
    print("\n── shutdown (request scope) ──")
    app = build_container()
    # warm
    for _ in range(WARM):
        child = app.create_request_scope()
        await child.shutdown()
    times = []
    for _ in range(N):
        child = app.create_request_scope()
        t0 = time.perf_counter_ns()
        await child.shutdown()
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("shutdown() [empty request scope]", times)

    # ── 7. Full request lifecycle ────────────────────────────────────
    print("\n── Full request lifecycle ──")
    app = build_container()
    # Pre-populate app-level cache
    await app.resolve_async(Config)
    await app.resolve_async(Logger)
    await app.resolve_async(Database)
    await app.resolve_async(UserRepo)
    await app.resolve_async(UserService)
    # warm
    for _ in range(WARM):
        child = app.create_request_scope()
        await child.resolve_async(UserService)
        await child.shutdown()
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        child = app.create_request_scope()
        await child.resolve_async(UserService)
        await child.shutdown()
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("scope() → resolve(UserService) → shutdown()", times)

    # Multiple resolves in one request
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        child = app.create_request_scope()
        await child.resolve_async(UserService)
        await child.resolve_async(OrderService)
        await child.resolve_async(NotificationService)
        await child.shutdown()
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("scope() → 3×resolve → shutdown()", times)

    # ── 8. _token_to_key overhead ────────────────────────────────────
    print("\n── _token_to_key / _make_cache_key ──")
    c = Container(scope="app")
    # String token
    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        k = c._token_to_key("my_service")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("_token_to_key(str)", times)

    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        k = c._token_to_key(Config)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("_token_to_key(type)", times)

    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        k = c._make_cache_key("bench_di.Config", None)
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("_make_cache_key(str, None)", times)

    times = []
    for _ in range(N):
        t0 = time.perf_counter_ns()
        k = c._make_cache_key("bench_di.Config", "primary")
        t1 = time.perf_counter_ns()
        times.append((t1 - t0) / 1e9)
    bench("_make_cache_key(str, tag)", times)

    print("\n" + "=" * 100)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
