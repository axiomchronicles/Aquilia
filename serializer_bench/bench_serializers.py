"""
Serializer Microbenchmarks — Measure hot-path performance.

Benchmarks:
- Serializer instantiation (shallow copy vs deepcopy)
- to_representation for small and large payloads
- run_validation for small and large payloads
- ListSerializer serialization (many items)
- StreamingSerializer throughput
- Buffer pool acquire/release
- Field attribute access (simple vs dotted)
- JSON backend comparison

Usage:
    python -m pytest serializer_bench/bench_serializers.py -v --tb=short
    python serializer_bench/bench_serializers.py  # standalone timeit mode

Standalone mode prints tabular before/after results.
"""

from __future__ import annotations

import copy
import datetime
import decimal
import json
import sys
import time
import uuid
from collections import OrderedDict
from typing import Any

# Allow running from repo root
sys.path.insert(0, ".")

from aquilia.serializers import (
    Serializer,
    ListSerializer,
    StreamingSerializer,
    BufferPool,
    SerializerConfig,
    get_buffer_pool,
)
from aquilia.serializers.fields import (
    CharField,
    IntegerField,
    FloatField,
    BooleanField,
    EmailField,
    DateTimeField,
    UUIDField,
    DecimalField,
    ListField,
    DictField,
    JSONField,
    ReadOnlyField,
    SerializerMethodField,
    empty,
)


# ============================================================================
# Test Serializers
# ============================================================================

class SmallSerializer(Serializer):
    """Small serializer — 4 fields (typical API response)."""
    id = IntegerField(read_only=True)
    name = CharField(max_length=100)
    email = EmailField()
    active = BooleanField()


class MediumSerializer(Serializer):
    """Medium serializer — 10 fields."""
    id = IntegerField(read_only=True)
    name = CharField(max_length=100)
    email = EmailField()
    age = IntegerField(min_value=0)
    score = FloatField()
    active = BooleanField()
    created_at = DateTimeField()
    uuid = UUIDField()
    bio = CharField(max_length=500, required=False, default="")
    balance = DecimalField(max_digits=10, decimal_places=2)


class LargeSerializer(Serializer):
    """Large serializer — 20 fields (heavy API response)."""
    id = IntegerField(read_only=True)
    name = CharField(max_length=100)
    email = EmailField()
    age = IntegerField(min_value=0)
    score = FloatField()
    active = BooleanField()
    created_at = DateTimeField()
    updated_at = DateTimeField()
    uuid = UUIDField()
    bio = CharField(max_length=500, required=False, default="")
    balance = DecimalField(max_digits=10, decimal_places=2)
    city = CharField(max_length=100)
    country = CharField(max_length=100)
    phone = CharField(max_length=20, required=False, default="")
    website = CharField(max_length=200, required=False, default="")
    company = CharField(max_length=200, required=False, default="")
    title = CharField(max_length=100, required=False, default="")
    department = CharField(max_length=100, required=False, default="")
    notes = CharField(max_length=1000, required=False, default="")
    tags = ListField(child=CharField(max_length=50), required=False, default=list)


class MethodFieldSerializer(Serializer):
    """Serializer with computed fields."""
    name = CharField()
    full_name = SerializerMethodField()
    display_name = SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_display_name(self, obj):
        return f"{obj.name} ({obj.email})"


# ============================================================================
# Test Data
# ============================================================================

class Obj:
    """Simple test object."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_small_obj(i=0):
    o = Obj()
    o.id = i
    o.name = f"User_{i}"
    o.email = f"user{i}@example.com"
    o.active = True
    return o


def make_medium_obj(i=0):
    o = make_small_obj(i)
    object.__setattr__(o, 'age', 25 + (i % 50))
    object.__setattr__(o, 'score', 95.5 + (i % 10) * 0.1)
    o.created_at = datetime.datetime(2024, 1, 1, 12, 0, 0)
    o.uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
    o.bio = f"Bio for user {i}"
    o.balance = decimal.Decimal("1234.56")
    return o


def make_large_obj(i=0):
    o = make_medium_obj(i)
    o.updated_at = datetime.datetime(2024, 6, 15, 14, 30, 0)
    o.city = "Tokyo"
    o.country = "Japan"
    o.phone = "+81-90-1234-5678"
    o.website = "https://example.com"
    o.company = "Aquilia Corp"
    o.title = "Engineer"
    o.department = "Platform"
    o.notes = "Some notes about this user"
    o.tags = ["admin", "premium", "beta"]
    return o


def make_method_obj(i=0):
    o = Obj()
    o.name = f"User_{i}"
    o.email = f"user{i}@example.com"
    o.first_name = "Kai"
    o.last_name = "Nakamura"
    return o


# ============================================================================
# Benchmark Harness
# ============================================================================

def bench(name: str, fn, iterations: int = 10000, warmup: int = 100):
    """Run a microbenchmark and return stats."""
    # Warmup
    for _ in range(warmup):
        fn()

    # Measure
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)

    times.sort()
    median_ns = times[len(times) // 2]
    p95_ns = times[int(len(times) * 0.95)]
    p99_ns = times[int(len(times) * 0.99)]
    mean_ns = sum(times) / len(times)
    total_ms = sum(times) / 1_000_000

    return {
        "name": name,
        "iterations": iterations,
        "median_ns": median_ns,
        "mean_ns": mean_ns,
        "p95_ns": p95_ns,
        "p99_ns": p99_ns,
        "total_ms": round(total_ms, 2),
        "ops_per_sec": round(iterations / (total_ms / 1000)) if total_ms > 0 else 0,
    }


def bench_old_deepcopy(name: str, serializer_cls, obj, iterations: int = 10000):
    """Simulate OLD behavior with deepcopy for comparison."""

    class OldStyleSerializer:
        """Simulates the old Serializer.__init__ with deepcopy."""
        def __init__(self, declared_fields):
            self.fields = OrderedDict()
            for fname, field in declared_fields.items():
                fc = copy.deepcopy(field)
                fc.bind(fname, self)
                self.fields[fname] = fc

    declared = serializer_cls._declared_fields

    def fn():
        OldStyleSerializer(declared)

    return bench(name, fn, iterations)


def bench_new_shallowcopy(name: str, serializer_cls, obj, iterations: int = 10000):
    """Measure NEW behavior with shallow copy."""
    def fn():
        serializer_cls(instance=obj)

    return bench(name, fn, iterations)


# ============================================================================
# Benchmark Suite
# ============================================================================

def run_all_benchmarks():
    """Run complete benchmark suite and print results."""
    results = []
    small_obj = make_small_obj()
    medium_obj = make_medium_obj()
    large_obj = make_large_obj()
    method_obj = make_method_obj()

    N = 50000
    N_large = 10000

    print("=" * 90)
    print("AQUILIA SERIALIZER BENCHMARK SUITE")
    print("=" * 90)
    print()

    # --- 1. Instantiation ---
    print("▸ Serializer Instantiation (shallow copy vs deepcopy)")
    print("-" * 70)

    r1 = bench_old_deepcopy("OLD deepcopy (small, 4 fields)", SmallSerializer, small_obj, N)
    r2 = bench_new_shallowcopy("NEW shallow (small, 4 fields)", SmallSerializer, small_obj, N)
    results.extend([r1, r2])
    speedup = r1["median_ns"] / r2["median_ns"] if r2["median_ns"] > 0 else 0
    print(f"  OLD deepcopy: {r1['median_ns']:>8} ns (median)  {r1['ops_per_sec']:>10} ops/s")
    print(f"  NEW shallow:  {r2['median_ns']:>8} ns (median)  {r2['ops_per_sec']:>10} ops/s")
    print(f"  Speedup: {speedup:.1f}×")
    print()

    r3 = bench_old_deepcopy("OLD deepcopy (medium, 10 fields)", MediumSerializer, medium_obj, N)
    r4 = bench_new_shallowcopy("NEW shallow (medium, 10 fields)", MediumSerializer, medium_obj, N)
    results.extend([r3, r4])
    speedup = r3["median_ns"] / r4["median_ns"] if r4["median_ns"] > 0 else 0
    print(f"  OLD deepcopy: {r3['median_ns']:>8} ns (median)  {r3['ops_per_sec']:>10} ops/s")
    print(f"  NEW shallow:  {r4['median_ns']:>8} ns (median)  {r4['ops_per_sec']:>10} ops/s")
    print(f"  Speedup: {speedup:.1f}×")
    print()

    r5 = bench_old_deepcopy("OLD deepcopy (large, 20 fields)", LargeSerializer, large_obj, N_large)
    r6 = bench_new_shallowcopy("NEW shallow (large, 20 fields)", LargeSerializer, large_obj, N_large)
    results.extend([r5, r6])
    speedup = r5["median_ns"] / r6["median_ns"] if r6["median_ns"] > 0 else 0
    print(f"  OLD deepcopy: {r5['median_ns']:>8} ns (median)  {r5['ops_per_sec']:>10} ops/s")
    print(f"  NEW shallow:  {r6['median_ns']:>8} ns (median)  {r6['ops_per_sec']:>10} ops/s")
    print(f"  Speedup: {speedup:.1f}×")
    print()

    # --- 2. Serialization (to_representation) ---
    print("▸ Serialization (to_representation)")
    print("-" * 70)

    s_small = SmallSerializer(instance=small_obj)
    r7 = bench("to_repr (small, 4 fields)", lambda: s_small.to_representation(small_obj), N)
    results.append(r7)
    print(f"  Small (4 fields):  {r7['median_ns']:>6} ns  {r7['ops_per_sec']:>10} ops/s")

    s_medium = MediumSerializer(instance=medium_obj)
    r8 = bench("to_repr (medium, 10 fields)", lambda: s_medium.to_representation(medium_obj), N)
    results.append(r8)
    print(f"  Medium (10 fields): {r8['median_ns']:>6} ns  {r8['ops_per_sec']:>10} ops/s")

    s_large = LargeSerializer(instance=large_obj)
    r9 = bench("to_repr (large, 20 fields)", lambda: s_large.to_representation(large_obj), N)
    results.append(r9)
    print(f"  Large (20 fields):  {r9['median_ns']:>6} ns  {r9['ops_per_sec']:>10} ops/s")

    s_method = MethodFieldSerializer(instance=method_obj)
    r10 = bench("to_repr (method fields)", lambda: s_method.to_representation(method_obj), N)
    results.append(r10)
    print(f"  Method fields:      {r10['median_ns']:>6} ns  {r10['ops_per_sec']:>10} ops/s")
    print()

    # --- 3. Deserialization (run_validation) ---
    print("▸ Deserialization (run_validation)")
    print("-" * 70)

    small_data = {"name": "Kai", "email": "kai@aq.dev", "active": True}
    r11 = bench("validate (small, 4 fields)",
                lambda: SmallSerializer(data=small_data).is_valid(), N)
    results.append(r11)
    print(f"  Small (4 fields):  {r11['median_ns']:>6} ns  {r11['ops_per_sec']:>10} ops/s")

    medium_data = {
        "name": "Kai", "email": "kai@aq.dev", "age": 25, "score": 95.5,
        "active": True, "created_at": "2024-01-01T12:00:00",
        "uuid": "12345678-1234-5678-1234-567812345678",
        "bio": "Hello", "balance": "1234.56",
    }
    r12 = bench("validate (medium, 10 fields)",
                lambda: MediumSerializer(data=medium_data).is_valid(), N)
    results.append(r12)
    print(f"  Medium (10 fields): {r12['median_ns']:>6} ns  {r12['ops_per_sec']:>10} ops/s")
    print()

    # --- 4. List Serialization ---
    print("▸ List Serialization (ListSerializer)")
    print("-" * 70)

    items_100 = [make_small_obj(i) for i in range(100)]
    items_1000 = [make_small_obj(i) for i in range(1000)]

    ls100 = ListSerializer(child=SmallSerializer(), instance=items_100)
    r13 = bench("list to_repr (100 items)", lambda: ls100.to_representation(items_100), 5000)
    results.append(r13)
    print(f"  100 items:  {r13['median_ns']:>8} ns  {r13['ops_per_sec']:>10} ops/s")

    ls1000 = ListSerializer(child=SmallSerializer(), instance=items_1000)
    r14 = bench("list to_repr (1000 items)", lambda: ls1000.to_representation(items_1000), 1000)
    results.append(r14)
    print(f"  1000 items: {r14['median_ns']:>8} ns  {r14['ops_per_sec']:>10} ops/s")
    print()

    # --- 5. Streaming Serializer ---
    print("▸ Streaming Serializer (1000 items)")
    print("-" * 70)

    streamer = StreamingSerializer(child=SmallSerializer(), instance=items_1000, chunk_size=32768)

    def stream_all():
        chunks = list(streamer.stream())
        return sum(len(c) for c in chunks)

    r15 = bench("streaming (1000 items)", stream_all, 500)
    results.append(r15)
    total_bytes = stream_all()
    print(f"  Streaming:  {r15['median_ns']:>8} ns  {r15['ops_per_sec']:>10} ops/s")
    print(f"  Output size: {total_bytes:,} bytes")
    print()

    # --- 6. Buffer Pool ---
    print("▸ Buffer Pool (acquire/release cycle)")
    print("-" * 70)

    pool = BufferPool(initial_size=4096, max_pool=8)

    def pool_cycle():
        b = pool.acquire()
        b.extend(b"test data " * 100)
        pool.release(b)

    r16 = bench("buffer pool cycle", pool_cycle, N)
    results.append(r16)
    print(f"  Acquire/release: {r16['median_ns']:>6} ns  {r16['ops_per_sec']:>10} ops/s")
    print()

    # --- 7. Field Attribute Access ---
    print("▸ Field Attribute Access (simple vs dotted)")
    print("-" * 70)

    from aquilia.serializers.fields import CharField as CF

    f_simple = CF()
    f_simple.bind("name", None)

    f_dotted = CF(source="author.name")
    f_dotted.bind("author_name", None)

    class NestedObj:
        class author:
            name = "Kai"
    nested = NestedObj()

    r17 = bench("get_attribute (simple)", lambda: f_simple.get_attribute(small_obj), N)
    results.append(r17)
    print(f"  Simple source:  {r17['median_ns']:>6} ns  {r17['ops_per_sec']:>10} ops/s")

    r18 = bench("get_attribute (dotted)", lambda: f_dotted.get_attribute(nested), N)
    results.append(r18)
    print(f"  Dotted source:  {r18['median_ns']:>6} ns  {r18['ops_per_sec']:>10} ops/s")
    print()

    # --- Summary ---
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"{'Benchmark':<45} {'Median (ns)':>12} {'Ops/sec':>12}")
    print("-" * 69)
    for r in results:
        print(f"  {r['name']:<43} {r['median_ns']:>12,} {r['ops_per_sec']:>12,}")

    return results


# ============================================================================
# Allocation Measurement
# ============================================================================

def measure_allocations():
    """Measure object allocations for before/after comparison."""
    import tracemalloc

    print()
    print("=" * 90)
    print("ALLOCATION MEASUREMENT")
    print("=" * 90)
    print()

    scenarios = [
        ("SmallSerializer × 1000", SmallSerializer, make_small_obj, 1000),
        ("MediumSerializer × 1000", MediumSerializer, make_medium_obj, 1000),
        ("LargeSerializer × 100", LargeSerializer, make_large_obj, 100),
        ("ListSerializer (1000 items)", None, make_small_obj, 1000),
    ]

    for name, ser_cls, obj_fn, count in scenarios:
        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        if ser_cls is not None:
            objs = [obj_fn(i) for i in range(count)]
            for obj in objs:
                s = ser_cls(instance=obj)
                _ = s.data
        else:
            items = [obj_fn(i) for i in range(count)]
            ls = ListSerializer(child=SmallSerializer(), instance=items)
            _ = ls.data

        snapshot2 = tracemalloc.take_snapshot()
        stats = snapshot2.compare_to(snapshot1, 'lineno')

        total_alloc = sum(s.size_diff for s in stats if s.size_diff > 0)
        total_blocks = sum(s.count_diff for s in stats if s.count_diff > 0)

        print(f"  {name}:")
        print(f"    Total allocated: {total_alloc:>10,} bytes")
        print(f"    Total blocks:    {total_blocks:>10,}")
        print(f"    Per-item:        {total_alloc // count:>10,} bytes/item")
        print()

        tracemalloc.stop()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    results = run_all_benchmarks()
    measure_allocations()

    # Save results to JSON
    import json
    with open("serializer_bench/bench_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to serializer_bench/bench_results.json")
