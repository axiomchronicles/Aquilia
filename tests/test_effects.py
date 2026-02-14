"""
Test 9: Effects System (effects.py)

Tests Effect, EffectKind, EffectProvider, EffectRegistry,
DBTx, CacheEffect, CacheHandle, CacheProvider, DBTxProvider.
"""

import pytest

from aquilia.effects import (
    Effect,
    EffectKind,
    EffectProvider,
    EffectRegistry,
    DBTx,
    CacheEffect,
    CacheHandle,
    CacheProvider,
    DBTxProvider,
)


class TestEffectKind:

    def test_values(self):
        assert EffectKind.DB.value == "db"
        assert EffectKind.CACHE.value == "cache"
        assert EffectKind.QUEUE.value == "queue"
        assert EffectKind.HTTP.value == "http"
        assert EffectKind.STORAGE.value == "storage"
        assert EffectKind.CUSTOM.value == "custom"


class TestEffect:

    def test_init(self):
        eff = Effect(name="test_effect", kind=EffectKind.CUSTOM)
        assert eff.name == "test_effect"
        assert eff.kind == EffectKind.CUSTOM

    def test_init_with_mode(self):
        eff = Effect(name="db", mode="read", kind=EffectKind.DB)
        assert eff.mode == "read"

    def test_repr_with_mode(self):
        eff = Effect(name="db", mode="write", kind=EffectKind.DB)
        assert "write" in repr(eff)

    def test_repr_without_mode(self):
        eff = Effect(name="test", kind=EffectKind.CUSTOM)
        assert "test" in repr(eff)


class TestEffectProvider:

    def test_is_abstract(self):
        with pytest.raises(TypeError):
            EffectProvider()

    def test_subclass(self):
        class MyProvider(EffectProvider):
            async def initialize(self): pass
            async def acquire(self, mode=None): return "resource"
            async def release(self, resource, success=True): pass
            async def finalize(self): pass

        p = MyProvider()
        assert isinstance(p, EffectProvider)


class TestDBTx:

    def test_create(self):
        tx = DBTx()
        assert isinstance(tx, Effect)
        assert tx.kind == EffectKind.DB

    def test_name(self):
        tx = DBTx()
        assert tx.name == "DBTx"


class TestDBTxProvider:

    def test_create(self):
        p = DBTxProvider(connection_string="sqlite://")
        assert isinstance(p, EffectProvider)

    @pytest.mark.asyncio
    async def test_initialize_acquire_release(self):
        p = DBTxProvider(connection_string="sqlite://")
        await p.initialize()
        resource = await p.acquire(mode="read")
        assert resource["mode"] == "read"
        await p.release(resource, success=True)


class TestCacheEffect:

    def test_create(self):
        cache = CacheEffect()
        assert isinstance(cache, Effect)
        assert cache.kind == EffectKind.CACHE

    def test_create_with_namespace(self):
        cache = CacheEffect(namespace="users")
        assert cache.mode == "users"


class TestCacheHandle:

    def test_create(self):
        handle = CacheHandle(cache={}, namespace="test")
        assert handle is not None

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        handle = CacheHandle(cache={}, namespace="test")
        await handle.set("key1", "value1")
        result = await handle.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_delete(self):
        handle = CacheHandle(cache={}, namespace="test")
        await handle.set("key1", "value1")
        await handle.delete("key1")
        result = await handle.get("key1")
        assert result is None


class TestCacheProvider:

    def test_create(self):
        p = CacheProvider()
        assert isinstance(p, EffectProvider)

    @pytest.mark.asyncio
    async def test_initialize_acquire_release(self):
        p = CacheProvider(backend="memory")
        await p.initialize()
        handle = await p.acquire(mode="users")
        assert isinstance(handle, CacheHandle)
        await p.release(handle)


class TestEffectRegistry:

    def test_init(self):
        reg = EffectRegistry()
        assert reg is not None

    def test_register_provider(self):
        reg = EffectRegistry()
        p = CacheProvider()
        reg.register("cache", p)
        assert reg.has_effect("cache")
        assert reg.get_provider("cache") is p

    def test_has_effect_missing(self):
        reg = EffectRegistry()
        assert reg.has_effect("nonexistent") is False

    def test_get_provider_missing(self):
        reg = EffectRegistry()
        with pytest.raises(KeyError):
            reg.get_provider("nonexistent")

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        reg = EffectRegistry()
        p = CacheProvider()
        reg.register("cache", p)
        await reg.initialize_all()
        assert reg._initialized is True

    @pytest.mark.asyncio
    async def test_finalize_all(self):
        reg = EffectRegistry()
        p = CacheProvider()
        reg.register("cache", p)
        await reg.initialize_all()
        await reg.finalize_all()
        assert reg._initialized is False

    @pytest.mark.asyncio
    async def test_startup_shutdown_aliases(self):
        reg = EffectRegistry()
        p = CacheProvider()
        reg.register("cache", p)
        await reg.startup()
        assert reg._initialized is True
        await reg.shutdown()
        assert reg._initialized is False
