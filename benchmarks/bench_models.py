"""
Models subsystem microbenchmarks.

Measures: Model.__init__, from_row, _build_filter_clause, Q chain building,
          generate_create_table_sql, field iteration patterns.

Run:
    python benchmarks/bench_models.py
"""

import sys, os, time, statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Set up a minimal model ──────────────────────────────────────────────

from aquilia.models.base import Model
from aquilia.models.fields_module import (
    CharField, IntegerField, TextField, DateTimeField, BooleanField,
    AutoField, EmailField, FloatField,
)


class BenchUser(Model):
    table = "bench_users"

    id = AutoField(primary_key=True)
    name = CharField(max_length=100)
    email = EmailField(max_length=255, unique=True)
    age = IntegerField(null=True)
    bio = TextField(blank=True, default="")
    score = FloatField(null=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class BenchPost(Model):
    table = "bench_posts"

    id = AutoField(primary_key=True)
    title = CharField(max_length=200)
    body = TextField(blank=True, default="")
    views = IntegerField(default=0)
    published = BooleanField(default=False)


# ── Helpers ──────────────────────────────────────────────────────────────

WARMUP = 200
ITERS = 2000
ROUNDS = 7


def _bench(label, fn, iters=ITERS, rounds=ROUNDS, warmup=WARMUP):
    """Run fn() iters times per round, return per-call stats."""
    for _ in range(warmup):
        fn()
    round_medians = []
    for _ in range(rounds):
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            fn()
        elapsed_ns = time.perf_counter_ns() - t0
        per_call = elapsed_ns / iters / 1000  # µs
        round_medians.append(per_call)
    med = statistics.median(round_medians)
    p95 = sorted(round_medians)[int(len(round_medians) * 0.95)]
    p99 = sorted(round_medians)[int(len(round_medians) * 0.99)]
    mn = min(round_medians)
    avg = statistics.mean(round_medians)
    print(
        f"  {label:<55s} median={med:8.2f}µs  p95={p95:8.2f}µs  p99={p99:8.2f}µs  "
        f"min={mn:8.2f}µs  avg={avg:8.2f}µs"
    )
    return med


def _banner(text):
    print(f"\n── {text} ──")


# ── Benchmarks ───────────────────────────────────────────────────────────

def main():
    sep = "=" * 92
    print(sep)
    print("Models Subsystem Microbenchmarks".center(92))
    print(sep)

    # ── Model.__init__ ──
    _banner("Model.__init__")

    _bench(
        "BenchUser(name, email)",
        lambda: BenchUser(name="Alice", email="alice@test.com"),
    )

    _bench(
        "BenchUser(name, email, age, bio, score, active)",
        lambda: BenchUser(
            name="Alice", email="alice@test.com", age=30,
            bio="Hello", score=9.5, active=True,
        ),
    )

    _bench(
        "BenchPost(title, body)",
        lambda: BenchPost(title="Hello", body="World"),
    )

    # ── from_row ──
    _banner("Model.from_row (dict-based)")

    row_small = {"id": 1, "name": "Alice", "email": "alice@test.com",
                 "age": None, "bio": "", "score": None, "active": 1,
                 "created_at": None}
    _bench(
        "BenchUser.from_row(8 cols)",
        lambda: BenchUser.from_row(row_small),
    )

    row_post = {"id": 1, "title": "Hello", "body": "World",
                "views": 42, "published": 1}
    _bench(
        "BenchPost.from_row(5 cols)",
        lambda: BenchPost.from_row(row_post),
    )

    # from_row with attr_name keys (fallback path)
    row_attr = {"id": 1, "name": "Alice", "email": "alice@test.com",
                "age": 30, "bio": "Hi", "score": 8.5, "active": True,
                "created_at": None}
    _bench(
        "BenchUser.from_row(attr-name keys)",
        lambda: BenchUser.from_row(row_attr),
    )

    # ── generate_create_table_sql ──
    _banner("generate_create_table_sql")

    _bench(
        "BenchUser.generate_create_table_sql()",
        lambda: BenchUser.generate_create_table_sql(),
    )

    _bench(
        "BenchPost.generate_create_table_sql()",
        lambda: BenchPost.generate_create_table_sql(),
    )

    # ── Q chain building (no DB execution) ──
    _banner("Q chain building (construction only)")

    from aquilia.models.query import Q

    class _FakeDB:
        """Stub to avoid needing real DB for query building benchmarks."""
        pass

    _bench(
        "Q(table, cls, db).filter(active=True)",
        lambda: Q("bench_users", BenchUser, _FakeDB()).filter(active=True),
    )

    _bench(
        "Q().filter(age__gt=18, active=True).order_by('-name').limit(10)",
        lambda: (
            Q("bench_users", BenchUser, _FakeDB())
            .filter(age__gt=18, active=True)
            .order_by("-name")
            .limit(10)
        ),
    )

    _bench(
        "Q().filter(name__contains='Alice').exclude(age__lt=18)",
        lambda: (
            Q("bench_users", BenchUser, _FakeDB())
            .filter(name__contains="Alice")
            .exclude(age__lt=18)
        ),
    )

    # ── Field iteration patterns ──
    _banner("Field iteration patterns")

    _bench(
        "iterate _non_m2m_fields (BenchUser, 8 fields)",
        lambda: [f for f in BenchUser._non_m2m_fields],
    )

    _bench(
        "_col_to_attr lookup (8 keys)",
        lambda: [BenchUser._col_to_attr.get(k) for k in row_small],
    )

    print(sep)
    print("Done.")


if __name__ == "__main__":
    main()
