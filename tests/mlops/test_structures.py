"""
Tests for MLOps data structures, model lineage, and A/B experiments.
"""

import math
import time
import threading

import pytest

from aquilia.mlops._structures import (
    RingBuffer,
    LRUCache,
    AtomicCounter,
    ExponentialDecay,
    SlidingWindow,
    TopKHeap,
    BloomFilter,
    ConsistentHash,
    ModelLineageDAG,
    LineageNode,
    ExperimentLedger,
    Experiment,
    ExperimentArm,
)


# ═══════════════════════════════════════════════════════════════════════════
# Ring Buffer
# ═══════════════════════════════════════════════════════════════════════════


class TestRingBuffer:
    def test_basic_append_and_read(self):
        rb = RingBuffer(4)
        rb.append(10)
        rb.append(20)
        assert list(rb) == [10, 20]
        assert len(rb) == 2

    def test_wrap_around(self):
        rb = RingBuffer(3)
        for v in range(5):
            rb.append(v)
        assert list(rb) == [2, 3, 4]
        assert len(rb) == 3

    def test_capacity(self):
        rb = RingBuffer(100)
        assert rb.capacity == 100

    def test_last(self):
        rb = RingBuffer(5)
        rb.append(1)
        rb.append(2)
        rb.append(3)
        assert rb.last() == 3

    def test_last_empty_raises(self):
        rb = RingBuffer(5)
        with pytest.raises(IndexError):
            rb.last()

    def test_getitem(self):
        rb = RingBuffer(3)
        rb.extend([10, 20, 30, 40, 50])
        assert rb[0] == 30
        assert rb[1] == 40
        assert rb[2] == 50
        assert rb[-1] == 50

    def test_getitem_out_of_range(self):
        rb = RingBuffer(3)
        rb.append(1)
        with pytest.raises(IndexError):
            rb[5]

    def test_percentile(self):
        rb = RingBuffer(100)
        for i in range(100):
            rb.append(float(i))
        p50 = rb.percentile(50)
        assert 40 <= p50 <= 60

    def test_clear(self):
        rb = RingBuffer(5)
        rb.extend([1, 2, 3])
        rb.clear()
        assert len(rb) == 0
        assert list(rb) == []

    def test_bool(self):
        rb = RingBuffer(5)
        assert not rb
        rb.append(1)
        assert rb

    def test_to_list(self):
        rb = RingBuffer(3)
        rb.extend([10, 20, 30, 40])
        assert rb.to_list() == [20, 30, 40]

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            RingBuffer(0)


# ═══════════════════════════════════════════════════════════════════════════
# LRU Cache
# ═══════════════════════════════════════════════════════════════════════════


class TestLRUCache:
    def test_basic_put_get(self):
        c = LRUCache(3)
        c.put("a", 1)
        c.put("b", 2)
        assert c.get("a") == 1
        assert c.get("b") == 2

    def test_eviction(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)  # evicts "a"
        assert c.get("a") is None
        assert c.get("b") == 2
        assert c.get("c") == 3

    def test_lru_order(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")      # "a" is now most recently used
        c.put("c", 3)   # evicts "b", not "a"
        assert c.get("a") == 1
        assert c.get("b") is None

    def test_update_existing(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("a", 10)
        assert c.get("a") == 10
        assert len(c) == 1

    def test_invalidate(self):
        c = LRUCache(3)
        c.put("a", 1)
        assert c.invalidate("a") is True
        assert c.get("a") is None
        assert c.invalidate("nonexistent") is False

    def test_contains(self):
        c = LRUCache(3)
        c.put("x", 42)
        assert "x" in c
        assert "y" not in c

    def test_clear(self):
        c = LRUCache(3)
        c.put("a", 1)
        c.put("b", 2)
        c.clear()
        assert len(c) == 0
        assert c.get("a") is None

    def test_hit_rate(self):
        c = LRUCache(3)
        c.put("a", 1)
        c.get("a")       # hit
        c.get("b")       # miss
        assert c.hit_rate == 0.5

    def test_stats(self):
        c = LRUCache(10)
        c.put("a", 1)
        s = c.stats
        assert s["capacity"] == 10
        assert s["size"] == 1

    def test_thread_safety(self):
        c = LRUCache(100)
        errors = []

        def writer(start):
            for i in range(100):
                c.put(f"k{start + i}", i)

        def reader():
            for i in range(100):
                c.get(f"k{i}")

        threads = [
            threading.Thread(target=writer, args=(0,)),
            threading.Thread(target=writer, args=(100,)),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No crash = success
        assert len(c) <= 100

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            LRUCache(0)


# ═══════════════════════════════════════════════════════════════════════════
# Atomic Counter
# ═══════════════════════════════════════════════════════════════════════════


class TestAtomicCounter:
    def test_inc(self):
        c = AtomicCounter()
        c.inc()
        c.inc(5)
        assert c.value == 6

    def test_dec(self):
        c = AtomicCounter(10)
        c.dec(3)
        assert c.value == 7

    def test_reset(self):
        c = AtomicCounter(42)
        c.reset()
        assert c.value == 0

    def test_thread_safety(self):
        c = AtomicCounter()
        threads = [
            threading.Thread(target=lambda: [c.inc() for _ in range(1000)])
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert c.value == 10_000

    def test_repr(self):
        c = AtomicCounter(42)
        assert "42" in repr(c)


# ═══════════════════════════════════════════════════════════════════════════
# Exponential Decay (EWMA)
# ═══════════════════════════════════════════════════════════════════════════


class TestExponentialDecay:
    def test_first_sample(self):
        e = ExponentialDecay(alpha=0.5)
        e.update(10.0)
        assert e.value == 10.0

    def test_smoothing(self):
        e = ExponentialDecay(alpha=0.3)
        values = [10, 12, 11, 13, 12]
        for v in values:
            e.update(v)
        # EWMA should be close to mean but biased toward recent
        assert 10 < e.value < 14

    def test_reset(self):
        e = ExponentialDecay(alpha=0.1)
        e.update(100)
        e.reset()
        assert e.value == 0.0

    def test_invalid_alpha(self):
        with pytest.raises(ValueError):
            ExponentialDecay(alpha=0.0)
        with pytest.raises(ValueError):
            ExponentialDecay(alpha=1.5)


# ═══════════════════════════════════════════════════════════════════════════
# Sliding Window
# ═══════════════════════════════════════════════════════════════════════════


class TestSlidingWindow:
    def test_add_and_count(self):
        w = SlidingWindow(window_seconds=60, bucket_width=1.0)
        now = time.monotonic()
        w.add(1.0, ts=now)
        w.add(1.0, ts=now)
        w.add(1.0, ts=now + 0.5)
        assert w.count(ts=now + 1) == 3

    def test_expiration(self):
        w = SlidingWindow(window_seconds=10, bucket_width=1.0)
        now = time.monotonic()
        w.add(1.0, ts=now)
        # After 15 seconds, the entry should be expired
        assert w.count(ts=now + 15) == 0

    def test_rate(self):
        w = SlidingWindow(window_seconds=10, bucket_width=1.0)
        now = time.monotonic()
        for i in range(20):
            w.add(1.0, ts=now + i * 0.1)
        rate = w.rate(ts=now + 2)
        assert rate > 0

    def test_mean(self):
        w = SlidingWindow(window_seconds=60, bucket_width=1.0)
        now = time.monotonic()
        w.add(10.0, ts=now)
        w.add(20.0, ts=now)
        assert w.mean(ts=now + 0.5) == 15.0

    def test_total(self):
        w = SlidingWindow(window_seconds=60, bucket_width=1.0)
        now = time.monotonic()
        w.add(5.0, ts=now)
        w.add(3.0, ts=now)
        assert w.total(ts=now + 0.5) == 8.0

    def test_clear(self):
        w = SlidingWindow(window_seconds=60, bucket_width=1.0)
        w.add(1.0)
        w.clear()
        assert w.count() == 0

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            SlidingWindow(window_seconds=0, bucket_width=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Top-K Heap
# ═══════════════════════════════════════════════════════════════════════════


class TestTopKHeap:
    def test_basic(self):
        t = TopKHeap(3)
        for model, score in [("a", 5), ("b", 3), ("c", 8), ("d", 1), ("e", 9)]:
            t.push(model, score)
        top = t.top()
        names = [x for x, _ in top]
        assert names == ["e", "c", "a"]

    def test_update_existing(self):
        t = TopKHeap(3)
        t.push("a", 5)
        t.push("a", 10)  # should update to max
        assert t.top()[0] == ("a", 10)

    def test_contains(self):
        t = TopKHeap(5)
        t.push("model-v1", 1.0)
        assert "model-v1" in t
        assert "model-v2" not in t

    def test_len(self):
        t = TopKHeap(2)
        t.push("a", 1)
        t.push("b", 2)
        t.push("c", 3)
        assert len(t) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Bloom Filter
# ═══════════════════════════════════════════════════════════════════════════


class TestBloomFilter:
    def test_membership(self):
        bf = BloomFilter(expected_items=100, fp_rate=0.01)
        bf.add("hello")
        bf.add("world")
        assert "hello" in bf
        assert "world" in bf
        assert "missing" not in bf  # very likely not in

    def test_no_false_negatives(self):
        bf = BloomFilter(expected_items=1000, fp_rate=0.01)
        items = [f"item-{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert item in bf

    def test_false_positive_rate(self):
        bf = BloomFilter(expected_items=1000, fp_rate=0.01)
        for i in range(1000):
            bf.add(f"present-{i}")
        # Check 1000 items that were NOT added
        false_positives = sum(
            1 for i in range(1000)
            if f"absent-{i}" in bf
        )
        # Should be ~1% = ~10, give some margin
        assert false_positives < 50

    def test_clear(self):
        bf = BloomFilter(expected_items=10)
        bf.add("x")
        bf.clear()
        assert "x" not in bf

    def test_size_bytes(self):
        bf = BloomFilter(expected_items=10000, fp_rate=0.01)
        assert bf.size_bytes > 0


# ═══════════════════════════════════════════════════════════════════════════
# Consistent Hash
# ═══════════════════════════════════════════════════════════════════════════


class TestConsistentHash:
    def test_deterministic(self):
        ch = ConsistentHash(4)
        b1 = ch.bucket("model-v1")
        b2 = ch.bucket("model-v1")
        assert b1 == b2

    def test_distribution(self):
        ch = ConsistentHash(4)
        buckets = set()
        for i in range(100):
            buckets.add(ch.bucket(f"model-{i}"))
        # Should use multiple buckets
        assert len(buckets) >= 2

    def test_add_bucket_minimal_redistribution(self):
        ch = ConsistentHash(4)
        keys = [f"key-{i}" for i in range(100)]
        before = {k: ch.bucket(k) for k in keys}
        ch.add_bucket()
        after = {k: ch.bucket(k) for k in keys}
        # Most keys should stay in same bucket
        unchanged = sum(1 for k in keys if before[k] == after[k])
        assert unchanged > 50  # majority unchanged

    def test_remove_bucket(self):
        ch = ConsistentHash(3)
        ch.remove_bucket()
        assert ch.num_buckets == 2

    def test_remove_last_bucket_raises(self):
        ch = ConsistentHash(1)
        with pytest.raises(ValueError):
            ch.remove_bucket()

    def test_invalid_init(self):
        with pytest.raises(ValueError):
            ConsistentHash(0)


# ═══════════════════════════════════════════════════════════════════════════
# Model Lineage DAG
# ═══════════════════════════════════════════════════════════════════════════


class TestModelLineageDAG:
    def test_add_model(self):
        dag = ModelLineageDAG()
        node = dag.add_model("base-v1", "v1", framework="pytorch")
        assert node.model_id == "base-v1"
        assert len(dag) == 1

    def test_parent_child(self):
        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("fine-tuned", "v1", parents=["base"])
        assert "fine-tuned" in dag.get("base").children
        assert "base" in dag.get("fine-tuned").parents

    def test_ancestors(self):
        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("mid", "v1", parents=["base"])
        dag.add_model("leaf", "v1", parents=["mid"])
        ancestors = dag.ancestors("leaf")
        assert "mid" in ancestors
        assert "base" in ancestors

    def test_descendants(self):
        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("child1", "v1", parents=["base"])
        dag.add_model("child2", "v1", parents=["base"])
        dag.add_model("grandchild", "v1", parents=["child1"])
        desc = dag.descendants("base")
        assert "child1" in desc
        assert "child2" in desc
        assert "grandchild" in desc

    def test_path(self):
        dag = ModelLineageDAG()
        dag.add_model("base", "v1")
        dag.add_model("mid", "v1", parents=["base"])
        dag.add_model("leaf", "v1", parents=["mid"])
        path = dag.path("base", "leaf")
        assert path == ["base", "mid", "leaf"]

    def test_path_not_found(self):
        dag = ModelLineageDAG()
        dag.add_model("a", "v1")
        dag.add_model("b", "v1")  # no edge
        assert dag.path("a", "b") is None

    def test_roots_and_leaves(self):
        dag = ModelLineageDAG()
        dag.add_model("root", "v1")
        dag.add_model("child", "v1", parents=["root"])
        dag.add_model("leaf", "v1", parents=["child"])
        assert "root" in dag.roots()
        assert "leaf" in dag.leaves()

    def test_contains(self):
        dag = ModelLineageDAG()
        dag.add_model("x", "v1")
        assert "x" in dag
        assert "y" not in dag

    def test_duplicate_raises(self):
        dag = ModelLineageDAG()
        dag.add_model("x", "v1")
        with pytest.raises(ValueError, match="already exists"):
            dag.add_model("x", "v1")

    def test_missing_parent_raises(self):
        dag = ModelLineageDAG()
        with pytest.raises(ValueError, match="not found"):
            dag.add_model("child", "v1", parents=["nonexistent"])

    def test_to_dict(self):
        dag = ModelLineageDAG()
        dag.add_model("base", "v1", metadata={"acc": 0.95})
        dag.add_model("child", "v1", parents=["base"])
        d = dag.to_dict()
        assert "base" in d
        assert "child" in d
        assert d["base"]["metadata"]["acc"] == 0.95

    def test_metadata(self):
        dag = ModelLineageDAG()
        node = dag.add_model("m", "v1", metadata={"dataset": "cifar10"})
        assert node.metadata["dataset"] == "cifar10"


# ═══════════════════════════════════════════════════════════════════════════
# A/B Experiment Ledger
# ═══════════════════════════════════════════════════════════════════════════


class TestExperimentLedger:
    def test_create_experiment(self):
        ledger = ExperimentLedger()
        exp = ledger.create("test-exp", arms=[
            {"name": "control", "model_version": "v1", "weight": 0.5},
            {"name": "treatment", "model_version": "v2", "weight": 0.5},
        ])
        assert exp.experiment_id == "test-exp"
        assert len(exp.arms) == 2

    def test_deterministic_assignment(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[
            {"name": "a", "weight": 0.5},
            {"name": "b", "weight": 0.5},
        ])
        # Same request_id → same arm
        arm1 = ledger.assign("exp", "req-001")
        arm2 = ledger.assign("exp", "req-001")
        assert arm1 == arm2

    def test_assignment_distribution(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[
            {"name": "a", "weight": 0.5},
            {"name": "b", "weight": 0.5},
        ])
        counts = {"a": 0, "b": 0}
        for i in range(1000):
            arm = ledger.assign("exp", f"req-{i}")
            counts[arm] += 1
        # Roughly 50/50
        assert 300 < counts["a"] < 700
        assert 300 < counts["b"] < 700

    def test_record_metric(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[
            {"name": "a", "weight": 1.0},
        ])
        ledger.assign("exp", "req-001")
        ledger.record("exp", "a", "latency_ms", 10.0)
        summary = ledger.summary("exp")
        assert "latency_ms" in summary["arms"][0]["metrics"]

    def test_conclude_experiment(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[
            {"name": "a", "weight": 0.5},
            {"name": "b", "weight": 0.5},
        ])
        ledger.conclude("exp", winner="a")
        exp = ledger.get("exp")
        assert exp.status == "completed"
        assert exp.metadata["winner"] == "a"

    def test_pause_resume(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[{"name": "a", "weight": 1.0}])
        ledger.pause("exp")
        assert ledger.get("exp").status == "paused"
        # Paused experiment returns empty assignment
        assert ledger.assign("exp", "req-001") == ""
        ledger.resume("exp")
        assert ledger.get("exp").status == "active"

    def test_list_active(self):
        ledger = ExperimentLedger()
        ledger.create("exp1", arms=[{"name": "a", "weight": 1.0}])
        ledger.create("exp2", arms=[{"name": "b", "weight": 1.0}])
        ledger.conclude("exp1")
        active = ledger.list_active()
        assert len(active) == 1
        assert active[0].experiment_id == "exp2"

    def test_duplicate_raises(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[{"name": "a", "weight": 1.0}])
        with pytest.raises(ValueError, match="already exists"):
            ledger.create("exp", arms=[{"name": "b", "weight": 1.0}])

    def test_assign_nonexistent(self):
        ledger = ExperimentLedger()
        assert ledger.assign("nonexistent", "req-001") == ""

    def test_summary_nonexistent(self):
        ledger = ExperimentLedger()
        assert ledger.summary("nonexistent") == {}

    def test_to_dict(self):
        ledger = ExperimentLedger()
        ledger.create("exp", arms=[{"name": "a", "weight": 1.0}])
        d = ledger.to_dict()
        assert "exp" in d

    def test_len(self):
        ledger = ExperimentLedger()
        ledger.create("e1", arms=[{"name": "a", "weight": 1.0}])
        ledger.create("e2", arms=[{"name": "b", "weight": 1.0}])
        assert len(ledger) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Module & Aquilary Registration
# ═══════════════════════════════════════════════════════════════════════════


class TestMLOpsModule:
    def test_manifest_attributes(self):
        from aquilia.mlops.module import MLOpsManifest

        assert MLOpsManifest.name == "mlops"
        assert MLOpsManifest.version == "0.2.0"
        assert len(MLOpsManifest.controllers) == 1
        assert len(MLOpsManifest.services) >= 10
        assert len(MLOpsManifest.middleware) == 2

    def test_manifest_depends_on(self):
        from aquilia.mlops.module import MLOpsManifest

        assert MLOpsManifest.depends_on == []

    async def test_manifest_on_startup(self):
        from aquilia.mlops.module import MLOpsManifest

        # Should not raise
        await MLOpsManifest.on_startup(config={"plugins": {"auto_discover": False}})

    async def test_manifest_on_shutdown(self):
        from aquilia.mlops.module import MLOpsManifest

        await MLOpsManifest.on_shutdown()


# ═══════════════════════════════════════════════════════════════════════════
# Enhanced Metrics (RingBuffer + EWMA integration)
# ═══════════════════════════════════════════════════════════════════════════


class TestMetricsEnhanced:
    def test_metrics_collector_uses_ring_buffer(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector(histogram_capacity=100)
        for i in range(200):
            mc.observe("lat", float(i))
        # Only last 100 observations kept
        assert mc._histograms["lat"].capacity == 100
        assert len(mc._histograms["lat"]) == 100

    def test_metrics_ewma(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector()
        for v in [10, 12, 11, 13, 12]:
            mc.observe("latency", v)
        ewma = mc.ewma("latency")
        assert 10 < ewma < 14

    def test_metrics_atomic_counters(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.inc("requests", 5)
        mc.inc("requests", 3)
        summary = mc.get_summary()
        assert summary["requests"] == 8

    def test_metrics_reset_clears_ewma(self):
        from aquilia.mlops.observe.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.observe("lat", 10.0)
        mc.reset()
        assert mc.ewma("lat") == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Registry LRU Cache Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistryCache:
    def test_registry_has_cache(self):
        from aquilia.mlops.registry.service import RegistryService

        rs = RegistryService(db_path=":memory:")
        assert hasattr(rs, "_cache")
        assert rs._cache._cap == 256

    def test_registry_custom_cache_capacity(self):
        from aquilia.mlops.registry.service import RegistryService

        rs = RegistryService(db_path=":memory:", cache_capacity=50)
        assert rs._cache._cap == 50

    def test_registry_cache_stats(self):
        from aquilia.mlops.registry.service import RegistryService

        rs = RegistryService(db_path=":memory:")
        stats = rs.cache_stats
        assert "capacity" in stats
        assert "hits" in stats
        assert "misses" in stats

    async def test_registry_fetch_caches(self):
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops._types import ModelpackManifest

        rs = RegistryService(db_path=":memory:")
        await rs.initialize()

        manifest = ModelpackManifest(
            name="test-model",
            version="v1",
            framework="pytorch",
            entrypoint="model.pt",
        )
        await rs.publish(manifest)

        # publish() populates cache, so first fetch is a hit
        m1 = await rs.fetch("test-model", "v1")
        assert rs.cache_stats["hits"] >= 1

        # Clear cache to test miss → cache scenario
        rs._cache.clear()
        m2 = await rs.fetch("test-model", "v1")
        assert rs.cache_stats["misses"] == 1

        # Second fetch after DB lookup should now hit cache
        m3 = await rs.fetch("test-model", "v1")
        assert rs.cache_stats["hits"] >= 1
        assert m1.name == m2.name == m3.name

        await rs.close()

    async def test_registry_delete_invalidates_cache(self):
        from aquilia.mlops.registry.service import RegistryService
        from aquilia.mlops._types import ModelpackManifest

        rs = RegistryService(db_path=":memory:")
        await rs.initialize()

        manifest = ModelpackManifest(
            name="del-model",
            version="v1",
            framework="pytorch",
            entrypoint="model.pt",
        )
        await rs.publish(manifest)

        # Populate cache
        await rs.fetch("del-model", "v1")
        assert "del-model:v1" in rs._cache

        # Delete invalidates cache
        await rs.delete("del-model", "v1")
        assert "del-model:v1" not in rs._cache

        await rs.close()


# ═══════════════════════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════════════════════


class TestStructureExports:
    def test_all_structures_exported(self):
        from aquilia.mlops import (
            RingBuffer,
            LRUCache,
            AtomicCounter,
            ExponentialDecay,
            SlidingWindow,
            TopKHeap,
            BloomFilter,
            ConsistentHash,
            ModelLineageDAG,
            LineageNode,
            ExperimentLedger,
            Experiment,
            ExperimentArm,
        )
        assert RingBuffer is not None
        assert ModelLineageDAG is not None
        assert ExperimentLedger is not None

    def test_module_exported(self):
        from aquilia.mlops.module import MLOpsManifest
        assert MLOpsManifest is not None
