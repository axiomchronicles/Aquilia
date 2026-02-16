"""
Tests for aquilia.mlops.registry - models, storage adapters.
"""

import json
import tempfile
from pathlib import Path

import pytest

from aquilia.mlops.registry.models import RegistryDB
from aquilia.mlops.registry.storage.filesystem import FilesystemStorageAdapter


class TestRegistryDB:
    @pytest.fixture
    async def db(self, tmp_path):
        _db = RegistryDB(db_path=str(tmp_path / "test.db"))
        await _db.initialize()
        yield _db
        await _db.close()

    async def test_insert_and_get_pack(self, db):
        await db.insert_pack(
            name="test-model",
            tag="v1.0.0",
            digest="sha256:abc123",
            manifest_json='{"name":"test-model","version":"v1.0.0"}',
        )
        await db.upsert_tag("test-model", "v1.0.0", "sha256:abc123")
        pack = await db.get_pack("test-model", "v1.0.0")
        assert pack is not None
        assert pack["digest"] == "sha256:abc123"

    async def test_get_pack_not_found(self, db):
        pack = await db.get_pack("nonexistent", "v0")
        assert pack is None

    async def test_list_versions(self, db):
        await db.insert_pack("model", "v1", "sha256:aaa", '{}')
        await db.insert_pack("model", "v2", "sha256:bbb", '{}')
        await db.insert_pack("other", "v1", "sha256:ccc", '{}')
        await db.upsert_tag("model", "v1", "sha256:aaa")
        await db.upsert_tag("model", "v2", "sha256:bbb")
        versions = await db.list_versions("model")
        assert len(versions) == 2

    async def test_list_packs(self, db):
        await db.insert_pack("model-a", "v1", "sha256:aaa", '{}')
        await db.insert_pack("model-b", "v1", "sha256:bbb", '{}')
        packs = await db.list_packs()
        names = {p["name"] for p in packs}
        assert "model-a" in names
        assert "model-b" in names

    async def test_upsert_tag(self, db):
        await db.insert_pack("model", "v1", "sha256:aaa", '{}')
        await db.upsert_tag("model", "latest", "sha256:aaa")
        pack = await db.get_pack_by_digest("sha256:aaa")
        assert pack is not None

    async def test_get_pack_by_digest(self, db):
        await db.insert_pack("model", "v1", "sha256:xyz", '{}')
        pack = await db.get_pack_by_digest("sha256:xyz")
        assert pack is not None
        assert pack["name"] == "model"

    async def test_delete_tag(self, db):
        await db.insert_pack("model", "v1", "sha256:del", '{}')
        await db.upsert_tag("model", "latest", "sha256:del")
        await db.delete_tag("model", "latest")
        pack = await db.get_pack_by_digest("sha256:del")
        assert pack is not None


class TestFilesystemStorage:
    @pytest.fixture
    def adapter(self, tmp_path):
        return FilesystemStorageAdapter(root=str(tmp_path / "storage"))

    async def test_put_and_get_blob(self, adapter):
        await adapter.put_blob("sha256:test123", b"model data")
        data = await adapter.get_blob("sha256:test123")
        assert data == b"model data"

    async def test_has_blob(self, adapter):
        assert not await adapter.has_blob("sha256:missing")
        await adapter.put_blob("sha256:exists", b"data")
        assert await adapter.has_blob("sha256:exists")

    async def test_delete_blob(self, adapter):
        await adapter.put_blob("sha256:del", b"data")
        await adapter.delete_blob("sha256:del")
        assert not await adapter.has_blob("sha256:del")

    async def test_get_blob_not_found(self, adapter):
        with pytest.raises(FileNotFoundError):
            await adapter.get_blob("sha256:nonexistent")

    async def test_list_blobs(self, adapter):
        await adapter.put_blob("sha256:aaa", b"data1")
        await adapter.put_blob("sha256:bbb", b"data2")
        blobs = await adapter.list_blobs()
        assert len(blobs) == 2
