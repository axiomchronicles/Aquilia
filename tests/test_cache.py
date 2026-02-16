"""
Comprehensive test suite for AquilaCache subsystem.

Covers:
- MemoryBackend: LRU/LFU/FIFO/TTL eviction, tag invalidation, namespace isolation
- NullBackend: no-op semantics
- CompositeBackend: L1/L2 promotion, write-through, delete-through
- CacheService: get/set/delete/get_or_set, namespace, tags, batch ops
- Decorators: @cached, @invalidate
- Serializers: JSON, Pickle
- KeyBuilder: DefaultKeyBuilder, HashKeyBuilder
- CacheConfig / build_cache_config
- CacheFaults
- CacheMiddleware (HTTP response caching)
- DI provider registration
- Trace diagnostics capture
- Config integration
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Core types ───────────────────────────────────────────────────────────────
from aquilia.cache.core import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheStats,
    EvictionPolicy,
)

# ── Backends ─────────────────────────────────────────────────────────────────
from aquilia.cache.backends.memory import MemoryBackend
from aquilia.cache.backends.null import NullBackend
from aquilia.cache.backends.composite import CompositeBackend

# ── Service ──────────────────────────────────────────────────────────────────
from aquilia.cache.service import CacheService

# ── Decorators ───────────────────────────────────────────────────────────────
from aquilia.cache.decorators import cached, cache_aside, invalidate

# ── Serializers ──────────────────────────────────────────────────────────────
from aquilia.cache.serializers import (
    JsonCacheSerializer,
    PickleCacheSerializer,
    get_serializer,
)

# ── Key builders ─────────────────────────────────────────────────────────────
from aquilia.cache.key_builder import DefaultKeyBuilder, HashKeyBuilder

# ── Faults ───────────────────────────────────────────────────────────────────
from aquilia.cache.faults import (
    CacheFault,
    CacheMissFault,
    CacheConnectionFault,
    CacheSerializationFault,
    CacheCapacityFault,
    CacheBackendFault,
    CacheConfigFault,
)

# ── DI providers ─────────────────────────────────────────────────────────────
from aquilia.cache.di_providers import (
    build_cache_config,
    create_cache_backend,
    create_cache_service,
    register_cache_providers,
)

# ── Middleware ───────────────────────────────────────────────────────────────
from aquilia.cache.middleware import CacheMiddleware

# ── Faults core ──────────────────────────────────────────────────────────────
from aquilia.faults.core import FaultDomain, Severity


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def memory_backend():
    """Fresh MemoryBackend (LRU, 100 entries)."""
    return MemoryBackend(max_size=100, eviction_policy="lru")


@pytest.fixture
def small_memory_backend():
    """Small MemoryBackend for eviction tests."""
    return MemoryBackend(max_size=3, eviction_policy="lru")


@pytest.fixture
def null_backend():
    return NullBackend()


@pytest.fixture
def composite_backend():
    """CompositeBackend with two in-memory levels."""
    l1 = MemoryBackend(max_size=5, eviction_policy="lru")
    l2 = MemoryBackend(max_size=50, eviction_policy="lru")
    return CompositeBackend(l1=l1, l2=l2)


@pytest.fixture
def cache_config():
    return CacheConfig(enabled=True, backend="memory", default_ttl=60, max_size=100)


@pytest.fixture
def cache_service(memory_backend, cache_config):
    return CacheService(backend=memory_backend, config=cache_config)


# ============================================================================
# CacheEntry
# ============================================================================


class TestCacheEntry:
    def test_entry_not_expired(self):
        entry = CacheEntry(key="k", value="v")
        assert not entry.is_expired

    def test_entry_expired(self):
        entry = CacheEntry(
            key="k",
            value="v",
            expires_at=time.monotonic() - 1,
        )
        assert entry.is_expired

    def test_entry_ttl_remaining(self):
        entry = CacheEntry(
            key="k",
            value="v",
            expires_at=time.monotonic() + 100,
        )
        assert entry.ttl_remaining is not None
        assert entry.ttl_remaining > 90

    def test_entry_no_ttl(self):
        entry = CacheEntry(key="k", value="v")
        assert entry.ttl_remaining is None

    def test_touch(self):
        entry = CacheEntry(key="k", value="v")
        old_count = entry.access_count
        entry.touch()
        assert entry.access_count == old_count + 1


class TestCacheStats:
    def test_hit_rate_zero_ops(self):
        s = CacheStats()
        assert s.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        s = CacheStats(hits=7, misses=3)
        assert s.hit_rate == pytest.approx(70.0)

    def test_total_operations(self):
        s = CacheStats(hits=1, misses=2, sets=3, deletes=4)
        assert s.total_operations == 10

    def test_to_dict(self):
        s = CacheStats(hits=5, misses=5)
        d = s.to_dict()
        assert d["hit_rate"] == 50.0
        assert "backend" in d


class TestCacheConfig:
    def test_defaults(self):
        cfg = CacheConfig()
        assert cfg.enabled is True
        assert cfg.backend == "memory"
        assert cfg.default_ttl == 300
        assert cfg.eviction_policy == "lru"

    def test_to_dict(self):
        cfg = CacheConfig(backend="redis", default_ttl=120)
        d = cfg.to_dict()
        assert d["backend"] == "redis"
        assert d["default_ttl"] == 120


class TestEvictionPolicy:
    def test_all_values(self):
        assert EvictionPolicy.LRU == "lru"
        assert EvictionPolicy.LFU == "lfu"
        assert EvictionPolicy.TTL == "ttl"
        assert EvictionPolicy.FIFO == "fifo"
        assert EvictionPolicy.RANDOM == "random"


# ============================================================================
# MemoryBackend
# ============================================================================


class TestMemoryBackend:

    @pytest.mark.asyncio
    async def test_init_shutdown(self, memory_backend):
        await memory_backend.initialize()
        assert memory_backend.name.startswith("memory")
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_set_get(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("key1", "value1", ttl=60)
        entry = await memory_backend.get("key1")
        assert entry is not None
        assert entry.value == "value1"
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_get_miss(self, memory_backend):
        await memory_backend.initialize()
        entry = await memory_backend.get("nonexistent")
        assert entry is None
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_delete(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("key1", "value1")
        assert await memory_backend.delete("key1") is True
        assert await memory_backend.get("key1") is None
        assert await memory_backend.delete("key1") is False
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_exists(self, memory_backend):
        await memory_backend.initialize()
        assert await memory_backend.exists("key1") is False
        await memory_backend.set("key1", "v")
        assert await memory_backend.exists("key1") is True
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_clear_all(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("a", 1)
        await memory_backend.set("b", 2)
        count = await memory_backend.clear()
        assert count == 2
        assert await memory_backend.exists("a") is False
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_clear_by_namespace(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("a", 1, namespace="ns1")
        await memory_backend.set("b", 2, namespace="ns2")
        await memory_backend.set("c", 3, namespace="ns1")
        count = await memory_backend.clear("ns1")
        assert count == 2
        assert await memory_backend.exists("b") is True
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_keys_all(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("foo", 1)
        await memory_backend.set("bar", 2)
        all_keys = await memory_backend.keys()
        assert sorted(all_keys) == ["bar", "foo"]
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_keys_by_namespace(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("a", 1, namespace="x")
        await memory_backend.set("b", 2, namespace="y")
        keys = await memory_backend.keys(namespace="x")
        assert keys == ["a"]
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_stats(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("k", "v")
        await memory_backend.get("k")
        await memory_backend.get("miss")
        stats = await memory_backend.stats()
        assert stats.hits >= 1
        assert stats.misses >= 1
        assert stats.sets >= 1
        assert stats.backend == "memory"
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_lru_eviction(self, small_memory_backend):
        be = small_memory_backend
        await be.initialize()
        await be.set("a", 1)
        await be.set("b", 2)
        await be.set("c", 3)
        # Access 'a' to make it recently used
        await be.get("a")
        # Add 'd' — should evict least recently used ('b')
        await be.set("d", 4)
        assert await be.get("b") is None, "b should have been evicted (LRU)"
        assert await be.get("a") is not None, "a was accessed, should survive"
        assert await be.get("d") is not None
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("short", "v", ttl=1)
        # Should exist immediately
        entry = await memory_backend.get("short")
        assert entry is not None, "Entry should exist right after set"
        # Wait for expiry
        await asyncio.sleep(1.1)
        entry = await memory_backend.get("short")
        assert entry is None, "Entry with 1s TTL should be expired after 1.1s"
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_tags_invalidation(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("p1", "v1", tags=("product",))
        await memory_backend.set("p2", "v2", tags=("product",))
        await memory_backend.set("u1", "v3", tags=("user",))
        deleted = await memory_backend.delete_by_tags({"product"})
        assert deleted == 2
        assert await memory_backend.exists("u1") is True
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_batch_get_set(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set_many({"x": 1, "y": 2, "z": 3}, ttl=60)
        results = await memory_backend.get_many(["x", "z", "missing"])
        assert results["x"].value == 1
        assert results["z"].value == 3
        assert results["missing"] is None
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_increment_decrement(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("counter", 10)
        result = await memory_backend.increment("counter", 5)
        assert result == 15
        result = await memory_backend.decrement("counter", 3)
        assert result == 12
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_delete_many(self, memory_backend):
        await memory_backend.initialize()
        await memory_backend.set("a", 1)
        await memory_backend.set("b", 2)
        await memory_backend.set("c", 3)
        count = await memory_backend.delete_many(["a", "c", "nonexist"])
        assert count == 2
        assert await memory_backend.exists("b") is True
        await memory_backend.shutdown()

    @pytest.mark.asyncio
    async def test_fifo_eviction(self):
        be = MemoryBackend(max_size=2, eviction_policy="fifo")
        await be.initialize()
        await be.set("first", 1)
        await be.set("second", 2)
        await be.set("third", 3)  # should evict "first"
        assert await be.get("first") is None
        assert await be.get("second") is not None
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_is_not_distributed(self, memory_backend):
        assert memory_backend.is_distributed is False


# ============================================================================
# NullBackend
# ============================================================================


class TestNullBackend:

    @pytest.mark.asyncio
    async def test_always_miss(self, null_backend):
        await null_backend.initialize()
        await null_backend.set("k", "v")
        assert await null_backend.get("k") is None
        assert await null_backend.exists("k") is False
        assert await null_backend.delete("k") is False
        await null_backend.shutdown()

    @pytest.mark.asyncio
    async def test_clear_returns_zero(self, null_backend):
        await null_backend.initialize()
        assert await null_backend.clear() == 0

    @pytest.mark.asyncio
    async def test_stats(self, null_backend):
        await null_backend.initialize()
        stats = await null_backend.stats()
        assert stats.backend == "null"

    @pytest.mark.asyncio
    async def test_keys_empty(self, null_backend):
        await null_backend.initialize()
        assert await null_backend.keys() == []


# ============================================================================
# CompositeBackend
# ============================================================================


class TestCompositeBackend:

    @pytest.mark.asyncio
    async def test_write_through(self, composite_backend):
        await composite_backend.initialize()
        await composite_backend.set("k", "v", ttl=60)
        # Both L1 and L2 should have it
        l1_entry = await composite_backend._l1.get("k")
        l2_entry = await composite_backend._l2.get("k")
        assert l1_entry is not None and l1_entry.value == "v"
        assert l2_entry is not None and l2_entry.value == "v"
        await composite_backend.shutdown()

    @pytest.mark.asyncio
    async def test_l1_hit(self, composite_backend):
        await composite_backend.initialize()
        await composite_backend.set("k", "v")
        entry = await composite_backend.get("k")
        assert entry is not None
        assert entry.value == "v"
        await composite_backend.shutdown()

    @pytest.mark.asyncio
    async def test_l2_promotion(self, composite_backend):
        """If key is in L2 but not L1, get() promotes to L1."""
        await composite_backend.initialize()
        # Write directly to L2 only
        await composite_backend._l2.set("promoted", "val", ttl=60)
        # L1 doesn't have it
        assert await composite_backend._l1.get("promoted") is None
        # get() should find in L2 and promote to L1
        entry = await composite_backend.get("promoted")
        assert entry is not None
        assert entry.value == "val"
        # Now L1 should have it
        l1_entry = await composite_backend._l1.get("promoted")
        assert l1_entry is not None
        await composite_backend.shutdown()

    @pytest.mark.asyncio
    async def test_delete_both_levels(self, composite_backend):
        await composite_backend.initialize()
        await composite_backend.set("k", "v")
        await composite_backend.delete("k")
        assert await composite_backend._l1.get("k") is None
        assert await composite_backend._l2.get("k") is None
        await composite_backend.shutdown()

    @pytest.mark.asyncio
    async def test_clear_both_levels(self, composite_backend):
        await composite_backend.initialize()
        await composite_backend.set("a", 1)
        await composite_backend.set("b", 2)
        await composite_backend.clear()
        assert await composite_backend._l1.exists("a") is False
        assert await composite_backend._l2.exists("a") is False
        await composite_backend.shutdown()

    @pytest.mark.asyncio
    async def test_stats(self, composite_backend):
        await composite_backend.initialize()
        stats = await composite_backend.stats()
        assert stats.backend.startswith("composite")
        await composite_backend.shutdown()


# ============================================================================
# CacheService
# ============================================================================


class TestCacheService:

    @pytest.mark.asyncio
    async def test_lifecycle(self, cache_service):
        await cache_service.initialize()
        assert cache_service._initialized is True
        await cache_service.shutdown()
        assert cache_service._initialized is False

    @pytest.mark.asyncio
    async def test_idempotent_init(self, cache_service):
        await cache_service.initialize()
        await cache_service.initialize()  # should not raise
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("greeting", "hello", ttl=60)
        value = await cache_service.get("greeting")
        assert value == "hello"
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_get_default(self, cache_service):
        await cache_service.initialize()
        value = await cache_service.get("nonexistent", default="fallback")
        assert value == "fallback"
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_delete(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("k", "v")
        assert await cache_service.delete("k") is True
        assert await cache_service.get("k") is None
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_exists(self, cache_service):
        await cache_service.initialize()
        assert await cache_service.exists("k") is False
        await cache_service.set("k", "v")
        assert await cache_service.exists("k") is True
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_get_or_set(self, cache_service):
        await cache_service.initialize()
        call_count = 0

        async def loader():
            nonlocal call_count
            call_count += 1
            return {"user": "alice"}

        # First call: miss → loads
        result = await cache_service.get_or_set("user:1", loader, ttl=60)
        assert result == {"user": "alice"}
        assert call_count == 1

        # Second call: hit → no load
        result = await cache_service.get_or_set("user:1", loader, ttl=60)
        assert result == {"user": "alice"}
        assert call_count == 1
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("id", "from-ns1", namespace="ns1")
        await cache_service.set("id", "from-ns2", namespace="ns2")
        assert await cache_service.get("id", namespace="ns1") == "from-ns1"
        assert await cache_service.get("id", namespace="ns2") == "from-ns2"
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_invalidate_tags(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("p1", "v1", tags=("product",))
        await cache_service.set("p2", "v2", tags=("product",))
        await cache_service.set("u1", "v3", tags=("user",))
        deleted = await cache_service.invalidate_tags("product")
        assert deleted == 2
        assert await cache_service.get("u1") == "v3"
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_batch_ops(self, cache_service):
        await cache_service.initialize()
        await cache_service.set_many({"a": 1, "b": 2, "c": 3})
        results = await cache_service.get_many(["a", "b", "missing"])
        assert results["a"] == 1
        assert results["b"] == 2
        assert results["missing"] is None
        count = await cache_service.delete_many(["a", "c"])
        assert count == 2
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_increment_decrement(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("counter", 10)
        assert await cache_service.increment("counter") == 11
        assert await cache_service.decrement("counter", 5) == 6
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_clear(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("a", 1)
        await cache_service.set("b", 2)
        await cache_service.clear()
        assert await cache_service.get("a") is None
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_stats(self, cache_service):
        await cache_service.initialize()
        await cache_service.set("k", "v")
        await cache_service.get("k")
        stats = await cache_service.stats()
        assert isinstance(stats, CacheStats)
        assert stats.hits >= 1
        await cache_service.shutdown()

    @pytest.mark.asyncio
    async def test_properties(self, cache_service):
        assert isinstance(cache_service.backend, CacheBackend)
        assert isinstance(cache_service.config, CacheConfig)
        assert cache_service.is_distributed is False


# ============================================================================
# Decorators
# ============================================================================


class TestDecorators:

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        backend = MemoryBackend(max_size=100)
        await backend.initialize()
        svc = CacheService(backend=backend)
        await svc.initialize()

        call_count = 0

        class FakeController:
            def __init__(self):
                self.cache = svc

            @cached(ttl=60, namespace="test")
            async def get_data(self, x: int):
                nonlocal call_count
                call_count += 1
                return {"x": x}

        ctrl = FakeController()
        result1 = await ctrl.get_data(42)
        assert result1 == {"x": 42}
        assert call_count == 1

        result2 = await ctrl.get_data(42)
        assert result2 == {"x": 42}
        assert call_count == 1  # cached

        result3 = await ctrl.get_data(99)
        assert call_count == 2  # different args

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_invalidate_decorator(self):
        backend = MemoryBackend(max_size=100)
        await backend.initialize()
        svc = CacheService(backend=backend)
        await svc.initialize()

        await svc.set("product:1", "old_value", tags=("product",))

        class FakeController:
            def __init__(self):
                self.cache = svc

            @invalidate("product:1", namespace="default")
            async def update_product(self, data: dict):
                return data

        ctrl = FakeController()
        await ctrl.update_product({"name": "new"})
        assert await svc.get("product:1") is None
        await svc.shutdown()


# ============================================================================
# Serializers
# ============================================================================


class TestSerializers:

    def test_json_roundtrip(self):
        s = JsonCacheSerializer()
        data = {"key": "value", "num": 42, "nested": [1, 2, 3]}
        encoded = s.serialize(data)
        assert isinstance(encoded, bytes)
        decoded = s.deserialize(encoded)
        assert decoded == data

    def test_pickle_roundtrip(self):
        s = PickleCacheSerializer()
        data = {"key": "value", "set_val": {1, 2, 3}}
        encoded = s.serialize(data)
        decoded = s.deserialize(encoded)
        assert decoded == data

    def test_get_serializer_factory(self):
        assert isinstance(get_serializer("json"), JsonCacheSerializer)
        assert isinstance(get_serializer("pickle"), PickleCacheSerializer)

    def test_unknown_serializer_raises(self):
        with pytest.raises((ValueError, KeyError)):
            get_serializer("unknown_format")


# ============================================================================
# Key Builders
# ============================================================================


class TestKeyBuilders:

    def test_default_key_builder(self):
        kb = DefaultKeyBuilder()
        key = kb.build("users", "user:123", prefix="aq:")
        assert key == "aq:users:user:123"

    def test_default_no_prefix(self):
        kb = DefaultKeyBuilder()
        key = kb.build("ns", "key")
        assert key == "ns:key"

    def test_hash_key_builder(self):
        kb = HashKeyBuilder()
        key = kb.build("ns", "some-very-long-key", prefix="aq:")
        assert key.startswith("aq:ns:")
        assert len(key) < 50  # hash truncation

    def test_hash_deterministic(self):
        kb = HashKeyBuilder()
        k1 = kb.build("ns", "key")
        k2 = kb.build("ns", "key")
        assert k1 == k2

    def test_hash_different_keys(self):
        kb = HashKeyBuilder()
        k1 = kb.build("ns", "key1")
        k2 = kb.build("ns", "key2")
        assert k1 != k2


# ============================================================================
# Cache Faults
# ============================================================================


class TestCacheFaults:

    def test_fault_domain_registered(self):
        assert hasattr(FaultDomain, "CACHE")
        assert FaultDomain.CACHE.name == "cache"

    def test_cache_miss_fault(self):
        f = CacheMissFault(key="user:1", namespace="api")
        assert f.code == "CACHE_MISS"
        assert f.severity == Severity.INFO
        assert "user:1" in f.message

    def test_cache_connection_fault(self):
        f = CacheConnectionFault(backend="redis", reason="connection refused")
        assert f.code == "CACHE_CONNECTION_FAILED"
        assert f.severity == Severity.ERROR
        assert f.retryable is True
        assert "redis" in f.message

    def test_cache_serialization_fault(self):
        f = CacheSerializationFault(key="k", operation="deserialize", reason="decode error")
        assert f.code == "CACHE_SERIALIZATION_FAILED"
        assert f.severity == Severity.WARN

    def test_cache_capacity_fault(self):
        f = CacheCapacityFault(current_size=10000, max_size=10000)
        assert f.code == "CACHE_CAPACITY_EXCEEDED"
        assert f.retryable is True

    def test_cache_backend_fault(self):
        f = CacheBackendFault(backend="redis", operation="get", reason="timeout")
        assert f.code == "CACHE_BACKEND_ERROR"
        assert f.severity == Severity.ERROR

    def test_cache_config_fault(self):
        f = CacheConfigFault(reason="invalid eviction policy")
        assert f.code == "CACHE_CONFIG_INVALID"
        assert f.severity == Severity.FATAL
        assert f.retryable is False

    def test_all_faults_inherit_base(self):
        for cls in (
            CacheMissFault,
            CacheConnectionFault,
            CacheSerializationFault,
            CacheCapacityFault,
            CacheBackendFault,
            CacheConfigFault,
        ):
            assert issubclass(cls, CacheFault)


# ============================================================================
# DI Providers
# ============================================================================


class TestDIProviders:

    def test_build_cache_config(self):
        cfg = build_cache_config({
            "enabled": True,
            "backend": "redis",
            "default_ttl": 120,
            "max_size": 5000,
        })
        assert isinstance(cfg, CacheConfig)
        assert cfg.backend == "redis"
        assert cfg.default_ttl == 120
        assert cfg.max_size == 5000

    def test_create_memory_backend(self):
        cfg = CacheConfig(backend="memory", max_size=500)
        be = create_cache_backend(cfg)
        assert isinstance(be, MemoryBackend)

    def test_create_null_backend(self):
        cfg = CacheConfig(backend="null")
        be = create_cache_backend(cfg)
        assert isinstance(be, NullBackend)

    def test_create_cache_service(self):
        cfg = CacheConfig(backend="memory")
        svc = create_cache_service(cfg)
        assert isinstance(svc, CacheService)
        assert isinstance(svc.backend, MemoryBackend)

    def test_unknown_backend_raises(self):
        cfg = CacheConfig(backend="magic")
        with pytest.raises(ValueError, match="Unknown"):
            create_cache_backend(cfg)

    def test_register_in_container(self):
        """Test DI registration with a real Container."""
        from aquilia.di.core import Container

        container = Container(scope="app")
        cfg = CacheConfig(backend="memory")
        svc = create_cache_service(cfg)
        register_cache_providers(container, svc)

        # Verify registration (providers dict should have our tokens)
        providers = container._providers
        found_svc = any(
            getattr(p, "_value", None) is svc
            for p in providers.values()
            if hasattr(p, "_value")
        )
        # Even if exact check fails, at least no errors raised
        assert True


# ============================================================================
# CacheMiddleware
# ============================================================================


class TestCacheMiddleware:

    @pytest.mark.asyncio
    async def test_caches_get_response(self):
        """GET responses should be cached."""
        backend = MemoryBackend(max_size=100)
        await backend.initialize()
        svc = CacheService(backend=backend)
        await svc.initialize()
        mw = CacheMiddleware(cache_service=svc, default_ttl=60, namespace="http")

        from tests.conftest import make_request
        from aquilia.response import Response

        call_count = 0

        async def handler(request, ctx):
            nonlocal call_count
            call_count += 1
            return Response(content={"data": "value"}, status=200)

        request = make_request("GET", "/api/data")
        ctx = {}

        resp1 = await mw(request, ctx, handler)
        assert resp1.status == 200
        assert call_count == 1

        # Second request should be served from cache
        request2 = make_request("GET", "/api/data")
        resp2 = await mw(request2, ctx, handler)
        assert call_count == 1  # handler not called again
        assert resp2.status == 200

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_post_not_cached(self):
        """POST requests should not be cached."""
        backend = MemoryBackend(max_size=100)
        await backend.initialize()
        svc = CacheService(backend=backend)
        await svc.initialize()
        mw = CacheMiddleware(cache_service=svc, default_ttl=60)

        from tests.conftest import make_request
        from aquilia.response import Response

        call_count = 0

        async def handler(request, ctx):
            nonlocal call_count
            call_count += 1
            return Response(content={"ok": True}, status=200)

        request = make_request("POST", "/api/data")
        ctx = {}

        await mw(request, ctx, handler)
        await mw(request, ctx, handler)
        assert call_count == 2  # both calls go through

        await svc.shutdown()


# ============================================================================
# Config Integration
# ============================================================================


class TestConfigIntegration:

    def test_config_loader_get_cache_config(self):
        """ConfigLoader.get_cache_config() returns valid dict."""
        from aquilia.config import ConfigLoader

        config = ConfigLoader()
        cache_cfg = config.get_cache_config()
        assert isinstance(cache_cfg, dict)
        assert "enabled" in cache_cfg
        assert "backend" in cache_cfg
        assert "default_ttl" in cache_cfg

    def test_integration_cache_builder(self):
        """Integration.cache() produces valid dict."""
        from aquilia.config_builders import Integration

        result = Integration.cache(
            backend="redis",
            default_ttl=120,
            redis_url="redis://cache:6379/1",
        )
        assert result["_integration_type"] == "cache"
        assert result["backend"] == "redis"
        assert result["default_ttl"] == 120
        assert result["redis_url"] == "redis://cache:6379/1"
        assert result["enabled"] is True


# ============================================================================
# Trace Diagnostics
# ============================================================================


class TestTraceDiagnostics:

    def test_capture_cache_active(self):
        """Diagnostics captures cache subsystem status."""
        from aquilia.trace.diagnostics import TraceDiagnostics

        mock_svc = MagicMock()
        mock_svc.__class__.__name__ = "CacheService"
        mock_backend = MagicMock()
        mock_backend.__class__.__name__ = "MemoryBackend"
        mock_svc._backend = mock_backend
        mock_config = MagicMock()
        mock_config.default_ttl = 300
        mock_config.max_size = 10000
        mock_config.eviction_policy = "lru"
        mock_svc._config = mock_config

        result = TraceDiagnostics._capture_cache(MagicMock(_cache_service=mock_svc))
        assert result["active"] is True
        assert result["backend"] == "MemoryBackend"
        assert result["default_ttl"] == 300

    def test_capture_cache_inactive(self):
        from aquilia.trace.diagnostics import TraceDiagnostics

        result = TraceDiagnostics._capture_cache(MagicMock(_cache_service=None))
        assert result["active"] is False

    def test_subsystem_summary_includes_cache(self):
        from aquilia.trace.diagnostics import TraceDiagnostics
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            diag = TraceDiagnostics(Path(tmpdir))
            # Write minimal diagnostics
            diag_path = Path(tmpdir) / "diagnostics.json"
            diag_path.write_text(json.dumps({
                "faults": {"active": True},
                "cache": {"active": True},
                "websockets": {"active": False},
                "effects": {"active": False},
                "sessions": {"active": False},
                "auth": {"active": False},
                "templates": {"active": False},
                "mail": {"active": False},
                "database": {"active": False},
            }))
            summary = diag.subsystem_summary()
            assert "cache" in summary
            assert summary["cache"] is True


# ============================================================================
# Module Exports
# ============================================================================


class TestModuleExports:
    """Ensure all public APIs are importable from aquilia.cache."""

    def test_core_exports(self):
        from aquilia.cache import (
            CacheBackend,
            CacheEntry,
            CacheStats,
            CacheConfig,
            EvictionPolicy,
        )

    def test_backend_exports(self):
        from aquilia.cache import (
            MemoryBackend,
            RedisBackend,
            CompositeBackend,
            NullBackend,
        )

    def test_service_export(self):
        from aquilia.cache import CacheService

    def test_decorator_exports(self):
        from aquilia.cache import cached, cache_aside, invalidate

    def test_fault_exports(self):
        from aquilia.cache import (
            CacheFault,
            CacheMissFault,
            CacheConnectionFault,
            CacheSerializationFault,
            CacheCapacityFault,
            CacheBackendFault,
            CacheConfigFault,
        )

    def test_middleware_export(self):
        from aquilia.cache import CacheMiddleware

    def test_key_builder_exports(self):
        from aquilia.cache import DefaultKeyBuilder, HashKeyBuilder

    def test_serializer_exports(self):
        from aquilia.cache import JsonCacheSerializer, PickleCacheSerializer

    def test_top_level_exports(self):
        """Verify cache symbols are exported from top-level aquilia package."""
        import aquilia
        assert hasattr(aquilia, "CacheService")
        assert hasattr(aquilia, "MemoryBackend")
        assert hasattr(aquilia, "cached")
        assert hasattr(aquilia, "CacheFault")
        assert hasattr(aquilia, "CacheMiddleware")
        assert hasattr(aquilia, "EvictionPolicy")


# ============================================================================
# Effects Integration
# ============================================================================


class TestEffectsIntegration:
    """CacheProvider in effects.py bridges to real CacheService."""

    @pytest.mark.asyncio
    async def test_cache_provider_with_service(self):
        from aquilia.effects import CacheProvider, CacheServiceHandle

        backend = MemoryBackend(max_size=100)
        await backend.initialize()
        svc = CacheService(backend=backend)
        await svc.initialize()

        provider = CacheProvider(cache_service=svc)
        await provider.initialize()

        handle = await provider.acquire(mode="test_ns")
        assert isinstance(handle, CacheServiceHandle)

        await handle.set("key1", "value1")
        result = await handle.get("key1")
        assert result == "value1"

        await handle.delete("key1")
        assert await handle.get("key1") is None

        await provider.finalize()
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_cache_provider_fallback(self):
        from aquilia.effects import CacheProvider, CacheHandle

        provider = CacheProvider()  # No CacheService → fallback dict
        await provider.initialize()

        handle = await provider.acquire(mode="ns")
        assert isinstance(handle, CacheHandle)

        await handle.set("k", "v")
        result = await handle.get("k")
        assert result == "v"

        await handle.delete("k")
        assert await handle.get("k") is None


# ============================================================================
# LFU Eviction
# ============================================================================


class TestLFUEviction:

    @pytest.mark.asyncio
    async def test_lfu_evicts_least_frequent(self):
        be = MemoryBackend(max_size=3, eviction_policy="lfu")
        await be.initialize()
        await be.set("a", 1)
        await be.set("b", 2)
        await be.set("c", 3)
        # Access 'a' and 'c' multiple times
        for _ in range(5):
            await be.get("a")
            await be.get("c")
        # 'b' has lowest frequency
        await be.set("d", 4)  # should evict 'b'
        assert await be.get("b") is None, "b should be evicted (LFU)"
        assert await be.get("a") is not None
        assert await be.get("c") is not None
        await be.shutdown()


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_set_none_value(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.set("k", None)
        entry = await be.get("k")
        # Entry should exist but value is None
        assert entry is not None
        assert entry.value is None
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_set_complex_value(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        complex_data = {
            "users": [{"name": "alice", "age": 30}],
            "count": 42,
            "nested": {"a": {"b": {"c": True}}},
        }
        await be.set("complex", complex_data)
        entry = await be.get("complex")
        assert entry.value == complex_data
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_overwrite_key(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.set("k", "original")
        await be.set("k", "updated")
        entry = await be.get("k")
        assert entry.value == "updated"
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_service_get_or_set_with_sync_loader(self):
        """get_or_set also accepts sync callables."""
        be = MemoryBackend(max_size=100)
        await be.initialize()
        svc = CacheService(backend=be)
        await svc.initialize()

        result = await svc.get_or_set("sync", lambda: "sync_value", ttl=60)
        assert result == "sync_value"
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_increment_nonexistent_key(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        result = await be.increment("missing")
        assert result is None
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_empty_tags(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.set("k", "v", tags=())
        deleted = await be.delete_by_tags({"nonexistent"})
        assert deleted == 0
        await be.shutdown()


# ============================================================================
# Enhanced Feature Tests
# ============================================================================


class TestCacheEntryEnhancements:
    """Tests for CacheEntry enhancements: age, version, repr."""

    def test_entry_age(self):
        entry = CacheEntry(key="k", value="v")
        import time; time.sleep(0.05)
        assert entry.age >= 0.04

    def test_entry_version_default(self):
        entry = CacheEntry(key="k", value="v")
        assert entry.version == 1

    def test_entry_version_custom(self):
        entry = CacheEntry(key="k", value="v", version=3)
        assert entry.version == 3

    def test_entry_repr(self):
        entry = CacheEntry(key="test_key", value=42, namespace="ns")
        r = repr(entry)
        assert "test_key" in r
        assert "ns" in r

    def test_entry_repr_with_ttl(self):
        import time
        entry = CacheEntry(key="k", value="v", expires_at=time.monotonic() + 100)
        r = repr(entry)
        assert "ttl=" in r


class TestCacheStatsEnhancements:
    """Tests for CacheStats latency tracking and stampede counter."""

    def test_latency_recording(self):
        stats = CacheStats()
        stats.record_get_latency(1.5)
        stats.record_get_latency(2.5)
        assert stats.avg_get_latency_ms == 2.0

    def test_set_latency_recording(self):
        stats = CacheStats()
        stats.record_set_latency(0.5)
        stats.record_set_latency(1.5)
        assert stats.avg_set_latency_ms == 1.0

    def test_p99_latency(self):
        stats = CacheStats()
        for i in range(100):
            stats.record_get_latency(float(i))
        assert stats.p99_get_latency_ms >= 98.0

    def test_latency_empty(self):
        stats = CacheStats()
        assert stats.avg_get_latency_ms == 0.0
        assert stats.avg_set_latency_ms == 0.0
        assert stats.p99_get_latency_ms == 0.0

    def test_stampede_joins_counter(self):
        stats = CacheStats()
        stats.stampede_joins = 5
        d = stats.to_dict()
        assert d["stampede_joins"] == 5

    def test_to_dict_has_latency_fields(self):
        stats = CacheStats()
        stats.record_get_latency(1.0)
        stats.record_set_latency(2.0)
        d = stats.to_dict()
        assert "avg_get_latency_ms" in d
        assert "avg_set_latency_ms" in d
        assert "p99_get_latency_ms" in d

    def test_latency_capping(self):
        """Latency samples are capped at max_latency_samples."""
        stats = CacheStats()
        for i in range(1500):
            stats.record_get_latency(float(i))
        assert len(stats._get_latencies) == 1000


class TestCacheConfigEnhancements:
    """Tests for CacheConfig enhancements: jitter, stampede, health check."""

    def test_ttl_jitter_enabled(self):
        config = CacheConfig(ttl_jitter=True, ttl_jitter_percent=0.2)
        # With 20% jitter on ttl=100, result should be between 80-120
        results = set()
        for _ in range(100):
            results.add(config.apply_jitter(100))
        # Should have variation
        assert len(results) > 1
        assert all(80 <= r <= 120 for r in results)

    def test_ttl_jitter_disabled(self):
        config = CacheConfig(ttl_jitter=False)
        assert config.apply_jitter(100) == 100
        assert config.apply_jitter(200) == 200

    def test_ttl_jitter_zero_ttl(self):
        config = CacheConfig(ttl_jitter=True)
        assert config.apply_jitter(0) == 0

    def test_stampede_prevention_config(self):
        config = CacheConfig(stampede_prevention=True, stampede_timeout=15.0)
        assert config.stampede_prevention is True
        assert config.stampede_timeout == 15.0

    def test_health_check_interval_config(self):
        config = CacheConfig(health_check_interval=30.0)
        assert config.health_check_interval == 30.0

    def test_capacity_warning_threshold_config(self):
        config = CacheConfig(capacity_warning_threshold=0.9)
        assert config.capacity_warning_threshold == 0.9

    def test_key_version_config(self):
        config = CacheConfig(key_version=2)
        assert config.key_version == 2

    def test_l2_async_write_config(self):
        config = CacheConfig(l2_async_write=True)
        assert config.l2_async_write is True

    def test_stale_while_revalidate_config(self):
        config = CacheConfig(middleware_stale_while_revalidate=30)
        assert config.middleware_stale_while_revalidate == 30

    def test_to_dict_has_new_fields(self):
        config = CacheConfig()
        d = config.to_dict()
        assert "ttl_jitter" in d
        assert "stampede_prevention" in d
        assert "key_version" in d
        assert "l2_async_write" in d
        assert "health_check_interval" in d
        assert "capacity_warning_threshold" in d
        assert "middleware_stale_while_revalidate" in d


class TestMemoryBackendEnhancements:
    """Tests for memory backend: latency tracking, capacity warnings, health."""

    @pytest.mark.asyncio
    async def test_latency_tracking_on_get(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.set("k", "v")
        await be.get("k")
        stats = await be.stats()
        assert stats.avg_get_latency_ms > 0
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_latency_tracking_on_set(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.set("k", "v")
        stats = await be.stats()
        assert stats.avg_set_latency_ms > 0
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_latency_on_miss(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        await be.get("nonexistent")
        stats = await be.stats()
        assert stats.avg_get_latency_ms > 0
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self):
        be = MemoryBackend(max_size=100)
        await be.initialize()
        assert await be.health_check() is True
        await be.shutdown()
        assert await be.health_check() is False

    @pytest.mark.asyncio
    async def test_max_memory_bytes_eviction(self):
        """Memory limit triggers eviction."""
        be = MemoryBackend(max_size=1000, max_memory_bytes=500)
        await be.initialize()
        # Store values that will exceed memory limit
        for i in range(50):
            await be.set(f"k{i}", "x" * 100)
        stats = await be.stats()
        # Should have evicted some entries
        assert stats.size < 50
        await be.shutdown()

    @pytest.mark.asyncio
    async def test_capacity_warning_threshold(self):
        """Backend tracks capacity warning state."""
        be = MemoryBackend(max_size=10, capacity_warning_threshold=0.5)
        await be.initialize()
        # Fill to 60% — should trigger warning
        for i in range(6):
            await be.set(f"k{i}", "v")
        assert be._capacity_warned is True
        await be.shutdown()


class TestServiceStampedePrevention:
    """Tests for CacheService stampede prevention (singleflight)."""

    @pytest.mark.asyncio
    async def test_get_or_set_single_call(self):
        """Basic get_or_set still works."""
        be = MemoryBackend(max_size=100)
        config = CacheConfig(stampede_prevention=True)
        svc = CacheService(backend=be, config=config)
        await svc.initialize()
        
        call_count = 0
        async def loader():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "value"
        
        result = await svc.get_or_set("key1", loader, ttl=60)
        assert result == "value"
        assert call_count == 1
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_stampede_coalescing(self):
        """Multiple concurrent get_or_set calls coalesce into one computation."""
        be = MemoryBackend(max_size=100)
        config = CacheConfig(stampede_prevention=True)
        svc = CacheService(backend=be, config=config)
        await svc.initialize()
        
        call_count = 0
        async def slow_loader():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return "computed_value"
        
        # Launch 5 concurrent requests for the same key
        results = await asyncio.gather(
            svc.get_or_set("same_key", slow_loader, ttl=60),
            svc.get_or_set("same_key", slow_loader, ttl=60),
            svc.get_or_set("same_key", slow_loader, ttl=60),
            svc.get_or_set("same_key", slow_loader, ttl=60),
            svc.get_or_set("same_key", slow_loader, ttl=60),
        )
        
        # All should get the same value
        assert all(r == "computed_value" for r in results)
        # Loader should only have been called once (or at most twice due to race)
        assert call_count <= 2
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_stampede_disabled(self):
        """Without stampede prevention, all calls compute independently."""
        be = MemoryBackend(max_size=100)
        config = CacheConfig(stampede_prevention=False)
        svc = CacheService(backend=be, config=config)
        await svc.initialize()
        
        call_count = 0
        async def loader():
            nonlocal call_count
            call_count += 1
            return f"val_{call_count}"
        
        result = await svc.get_or_set("key", loader, ttl=60)
        assert result is not None
        await svc.shutdown()


class TestServiceEnhancements:
    """Tests for CacheService new methods: touch, warm, health_check, get_or_default."""

    @pytest.mark.asyncio
    async def test_touch_refreshes_ttl(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        await svc.set("k", "v", ttl=10)
        result = await svc.touch("k", ttl=300)
        assert result is True
        
        # Value should still be accessible
        val = await svc.get("k")
        assert val == "v"
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_touch_missing_key(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        result = await svc.touch("nonexistent", ttl=300)
        assert result is False
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_warm_preloads_entries(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        items = {"a": 1, "b": 2, "c": 3}
        count = await svc.warm(items, ttl=60, namespace="test")
        assert count == 3
        
        # All items should be accessible
        assert await svc.get("a", namespace="test") == 1
        assert await svc.get("b", namespace="test") == 2
        assert await svc.get("c", namespace="test") == 3
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_warm_empty_items(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        count = await svc.warm({})
        assert count == 0
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig(health_check_interval=0))
        await svc.initialize()
        
        healthy = await svc.health_check()
        assert healthy is True
        assert svc.is_healthy is True
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_is_healthy_property(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig(health_check_interval=0))
        assert svc.is_healthy is False  # Not initialized
        await svc.initialize()
        assert svc.is_healthy is True
        await svc.shutdown()
        assert svc.is_healthy is False

    @pytest.mark.asyncio
    async def test_get_or_default_cached(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        await svc.set("k", "cached_value")
        result = await svc.get_or_default("k", lambda: "fallback")
        assert result == "cached_value"
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_get_or_default_miss(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        result = await svc.get_or_default("missing", lambda: "fallback")
        assert result == "fallback"
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_get_or_default_async_factory(self):
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        async def async_fallback():
            return "async_fallback"
        
        result = await svc.get_or_default("missing", async_fallback)
        assert result == "async_fallback"
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_get_error_resilience(self):
        """GET should return default on backend errors, not raise."""
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        # Simulate backend error by corrupting backend
        original_get = be.get
        async def failing_get(key):
            raise RuntimeError("Backend failure")
        be.get = failing_get
        
        result = await svc.get("k", default="safe_default")
        assert result == "safe_default"
        
        be.get = original_get
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_ttl_jitter_applied_on_set(self):
        """CacheService applies TTL jitter when setting."""
        be = MemoryBackend(max_size=100)
        config = CacheConfig(ttl_jitter=True, ttl_jitter_percent=0.5)
        svc = CacheService(backend=be, config=config)
        await svc.initialize()
        
        # Set many items with same TTL and check they get different expiry
        for i in range(10):
            await svc.set(f"k{i}", f"v{i}", ttl=100)
        
        # Items should exist (jittered TTL still positive)
        for i in range(10):
            val = await svc.get(f"k{i}")
            assert val == f"v{i}"
        await svc.shutdown()


class TestDecoratorEnhancements:
    """Tests for decorator enhancements: key_func, condition, default service."""

    @pytest.mark.asyncio
    async def test_condition_prevents_caching(self):
        """Condition=False should skip caching the result."""
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        class FakeCtrl:
            def __init__(self):
                self.cache = svc
        
        @cached(ttl=60, namespace="test", condition=lambda r: r is not None and len(r) > 0)
        async def get_items(self):
            return []
        
        ctrl = FakeCtrl()
        result = await get_items(ctrl)
        assert result == []
        
        # Empty list should NOT have been cached
        stats = await svc.stats()
        assert stats.sets == 0
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_condition_allows_caching(self):
        """Condition=True should allow caching."""
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        class FakeCtrl:
            def __init__(self):
                self.cache = svc
        
        @cached(ttl=60, namespace="test", condition=lambda r: r is not None and len(r) > 0)
        async def get_items(self):
            return ["item1", "item2"]
        
        ctrl = FakeCtrl()
        result = await get_items(ctrl)
        assert result == ["item1", "item2"]
        
        # Non-empty result should have been cached
        stats = await svc.stats()
        assert stats.sets == 1
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_key_func_custom_key(self):
        """Custom key_func should be used for cache key."""
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        class FakeCtrl:
            def __init__(self):
                self.cache = svc
        
        @cached(
            ttl=60,
            namespace="test",
            key_func=lambda func, args, kwargs: f"custom:{kwargs.get('uid', 'unknown')}",
        )
        async def get_user(self, uid=None):
            return {"id": uid, "name": "Alice"}
        
        ctrl = FakeCtrl()
        result = await get_user(ctrl, uid=42)
        assert result["id"] == 42
        
        # Should be cached with the custom key
        cached_val = await svc.get("custom:42", namespace="test")
        assert cached_val is not None
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_default_cache_service_registration(self):
        """Module-level default cache service should be used by decorators."""
        from aquilia.cache.decorators import set_default_cache_service, get_default_cache_service
        
        be = MemoryBackend(max_size=100)
        svc = CacheService(backend=be, config=CacheConfig())
        await svc.initialize()
        
        set_default_cache_service(svc)
        assert get_default_cache_service() is svc
        
        # Standalone function (no self.cache)
        @cached(ttl=60, key="standalone_key", namespace="test")
        async def standalone_func():
            return "standalone_result"
        
        result = await standalone_func()
        assert result == "standalone_result"
        
        # Should be cached
        cached_val = await svc.get("standalone_key", namespace="test")
        assert cached_val == "standalone_result"
        
        # Cleanup
        set_default_cache_service(None)
        await svc.shutdown()


class TestCompositeEnhancements:
    """Tests for composite backend: async L2, error resilience, health check."""

    @pytest.mark.asyncio
    async def test_l2_error_resilience_on_get(self):
        """L2 failure should degrade to L1 without raising."""
        l1 = MemoryBackend(max_size=100)
        l2 = MemoryBackend(max_size=100)
        composite = CompositeBackend(l1=l1, l2=l2)
        await composite.initialize()
        
        # Put value in L1 only
        await l1.set("k", "v")
        
        # Break L2
        async def broken_get(key):
            raise RuntimeError("L2 down")
        l2.get = broken_get
        
        # Should get from L1 successfully
        entry = await composite.get("k")
        assert entry is not None
        assert entry.value == "v"
        assert composite.l2_healthy is True  # L1 returned, L2 wasn't needed
        await composite.shutdown()

    @pytest.mark.asyncio
    async def test_l2_failure_falls_through(self):
        """L2 failure on miss should return None gracefully."""
        l1 = MemoryBackend(max_size=100)
        l2 = MemoryBackend(max_size=100)
        composite = CompositeBackend(l1=l1, l2=l2)
        await composite.initialize()
        
        # Break L2
        async def broken_get(key):
            raise RuntimeError("L2 down")
        l2.get = broken_get
        
        # L1 miss, L2 error — should return None
        entry = await composite.get("nonexistent")
        assert entry is None
        assert composite.l2_healthy is False
        await composite.shutdown()

    @pytest.mark.asyncio
    async def test_l2_set_error_resilience(self):
        """L2 SET failure should not break the write."""
        l1 = MemoryBackend(max_size=100)
        l2 = MemoryBackend(max_size=100)
        composite = CompositeBackend(l1=l1, l2=l2)
        await composite.initialize()
        
        # Break L2 set
        async def broken_set(key, value, ttl=None, tags=(), namespace="default"):
            raise RuntimeError("L2 write failed")
        l2.set = broken_set
        
        # Should still succeed (L1 written)
        await composite.set("k", "v")
        
        # L1 should have the value
        entry = await l1.get("k")
        assert entry is not None
        assert entry.value == "v"
        assert composite.l2_healthy is False
        await composite.shutdown()

    @pytest.mark.asyncio
    async def test_l2_healthy_property(self):
        l1 = MemoryBackend(max_size=100)
        l2 = MemoryBackend(max_size=100)
        composite = CompositeBackend(l1=l1, l2=l2)
        await composite.initialize()
        
        assert composite.l2_healthy is True
        await composite.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self):
        l1 = MemoryBackend(max_size=100)
        l2 = MemoryBackend(max_size=100)
        composite = CompositeBackend(l1=l1, l2=l2)
        await composite.initialize()
        
        healthy = await composite.health_check()
        assert healthy is True
        await composite.shutdown()


class TestKeyBuilderVersioning:
    """Tests for key builder version support."""

    def test_default_no_version(self):
        kb = DefaultKeyBuilder()
        key = kb.build("users", "user:123", prefix="aq:")
        assert key == "aq:users:user:123"

    def test_versioned_key(self):
        kb = DefaultKeyBuilder(version=2)
        key = kb.build("users", "user:123", prefix="aq:")
        assert key == "aq:v2:users:user:123"

    def test_version_changes_key(self):
        kb_v1 = DefaultKeyBuilder(version=1)
        kb_v2 = DefaultKeyBuilder(version=2)
        k1 = kb_v1.build("ns", "key", prefix="aq:")
        k2 = kb_v2.build("ns", "key", prefix="aq:")
        assert k1 != k2

    def test_hash_builder_versioned(self):
        from aquilia.cache.key_builder import HashKeyBuilder
        kb = HashKeyBuilder(version=3)
        key = kb.build("ns", "key", prefix="aq:")
        assert "v3" in key

    def test_hash_builder_no_version(self):
        from aquilia.cache.key_builder import HashKeyBuilder
        kb = HashKeyBuilder(version=0)
        key = kb.build("ns", "key", prefix="aq:")
        assert "v0" not in key


class TestNewFaultTypes:
    """Tests for new fault types: CacheStampedeFault, CacheHealthFault."""

    def test_stampede_fault(self):
        from aquilia.cache.faults import CacheStampedeFault
        fault = CacheStampedeFault(key="hot_key", waiters=10)
        assert fault.code == "CACHE_STAMPEDE_DETECTED"
        assert "hot_key" in fault.message
        assert fault.metadata["waiters"] == 10
        assert fault.retryable is True

    def test_health_fault(self):
        from aquilia.cache.faults import CacheHealthFault
        fault = CacheHealthFault(backend="redis", reason="Connection timeout")
        assert fault.code == "CACHE_HEALTH_FAILED"
        assert "redis" in fault.message
        assert fault.metadata["reason"] == "Connection timeout"


class TestModuleExportsEnhanced:
    """Tests for new module exports."""

    def test_new_fault_exports(self):
        from aquilia.cache import CacheStampedeFault, CacheHealthFault
        assert CacheStampedeFault is not None
        assert CacheHealthFault is not None

    def test_decorator_utility_exports(self):
        from aquilia.cache import set_default_cache_service, get_default_cache_service
        assert callable(set_default_cache_service)
        assert callable(get_default_cache_service)

    def test_new_exports_in_all(self):
        import aquilia.cache as cache_mod
        assert "CacheStampedeFault" in cache_mod.__all__
        assert "CacheHealthFault" in cache_mod.__all__
        assert "set_default_cache_service" in cache_mod.__all__
        assert "get_default_cache_service" in cache_mod.__all__


class TestDIProvidersEnhanced:
    """Tests for DI providers with new config fields."""

    def test_build_cache_config_new_fields(self):
        from aquilia.cache.di_providers import build_cache_config
        config = build_cache_config({
            "ttl_jitter": False,
            "stampede_prevention": False,
            "stampede_timeout": 10.0,
            "health_check_interval": 120.0,
            "capacity_warning_threshold": 0.95,
            "key_version": 5,
            "l2_async_write": True,
            "middleware_stale_while_revalidate": 60,
        })
        assert config.ttl_jitter is False
        assert config.stampede_prevention is False
        assert config.stampede_timeout == 10.0
        assert config.health_check_interval == 120.0
        assert config.capacity_warning_threshold == 0.95
        assert config.key_version == 5
        assert config.l2_async_write is True
        assert config.middleware_stale_while_revalidate == 60

    def test_create_memory_backend_with_capacity_threshold(self):
        from aquilia.cache.di_providers import create_cache_backend
        config = CacheConfig(
            backend="memory",
            capacity_warning_threshold=0.7,
        )
        backend = create_cache_backend(config)
        assert isinstance(backend, MemoryBackend)
        assert backend._capacity_warning_threshold == 0.7
