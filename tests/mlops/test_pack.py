"""
Tests for aquilia.mlops.pack - builder, content store, manifest schema, signer.
"""

import hashlib
import io
import json
import os
import tarfile
import tempfile
from pathlib import Path

import pytest

from aquilia.mlops.pack.builder import ModelpackBuilder
from aquilia.mlops.pack.content_store import ContentStore
from aquilia.mlops.pack.manifest_schema import validate_manifest, MANIFEST_SCHEMA
from aquilia.mlops.pack.signer import HMACSigner, verify_archive, sign_archive


class TestModelpackBuilder:
    @pytest.fixture
    def model_file(self, tmp_path):
        p = tmp_path / "model.pt"
        p.write_bytes(b"fake-model-bytes" * 100)
        return p

    @pytest.fixture
    def env_lock(self, tmp_path):
        p = tmp_path / "requirements.txt"
        p.write_text("torch==2.0\nnumpy>=1.24\n")
        return p

    async def test_build_and_save(self, model_file, env_lock, tmp_path):
        builder = ModelpackBuilder(name="test-model", version="v1.0.0")
        builder.add_model(str(model_file), framework="pytorch")
        builder.add_env_lock(str(env_lock))
        archive_path = await builder.save(str(tmp_path / "out"))
        assert Path(archive_path).exists()
        assert archive_path.endswith(".aquilia")
        with tarfile.open(archive_path, "r:gz") as tar:
            names = tar.getnames()
            assert "manifest.json" in names

    async def test_inspect(self, model_file, tmp_path):
        builder = ModelpackBuilder(name="inspect-test", version="v0.1.0")
        builder.add_model(str(model_file), framework="onnx")
        archive_path = await builder.save(str(tmp_path / "out"))
        manifest = await ModelpackBuilder.inspect(archive_path)
        assert manifest.name == "inspect-test"
        assert manifest.version == "v0.1.0"

    async def test_missing_model_raises(self, tmp_path):
        builder = ModelpackBuilder(name="empty", version="v0.0.1")
        with pytest.raises(Exception):
            await builder.save(str(tmp_path / "out"))


class TestContentStore:
    @pytest.fixture
    def store(self, tmp_path):
        return ContentStore(root=str(tmp_path / "cas"))

    async def test_store_and_retrieve(self, store):
        data = b"hello world"
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        await store.store(digest, data)
        assert await store.exists(digest)
        assert await store.retrieve(digest) == data

    async def test_store_is_idempotent(self, store):
        data = b"same content"
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        p1 = await store.store(digest, data)
        p2 = await store.store(digest, data)
        assert p1 == p2

    async def test_delete(self, store):
        data = b"delete me"
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        await store.store(digest, data)
        assert await store.exists(digest)
        await store.delete(digest)
        assert not await store.exists(digest)

    async def test_list_digests(self, store):
        d1 = "sha256:" + hashlib.sha256(b"aaa").hexdigest()
        d2 = "sha256:" + hashlib.sha256(b"bbb").hexdigest()
        await store.store(d1, b"aaa")
        await store.store(d2, b"bbb")
        digests = await store.list_digests()
        assert len(digests) == 2


class TestManifestSchema:
    def test_valid_manifest(self):
        manifest = {
            "name": "test",
            "version": "v1",
            "framework": "pytorch",
            "entrypoint": "model.pt",
            "inputs": [{"name": "x", "dtype": "float32", "shape": [-1]}],
            "outputs": [{"name": "y", "dtype": "float32", "shape": [-1]}],
            "blobs": [{"digest": "sha256:abc", "size": 100, "path": "model.pt"}],
        }
        errors = validate_manifest(manifest)
        assert errors == []

    def test_missing_required_fields(self):
        errors = validate_manifest({})
        assert len(errors) > 0

    def test_schema_has_required_fields(self):
        assert "name" in MANIFEST_SCHEMA["properties"]
        assert "version" in MANIFEST_SCHEMA["properties"]


class TestHMACSigner:
    def test_sign_and_verify(self):
        signer = HMACSigner(secret="my-secret-key")
        data = b"important data"
        sig = signer.sign(data)
        assert sig
        assert signer.verify(data, sig)

    def test_verify_wrong_key(self):
        s1 = HMACSigner(secret="key1")
        s2 = HMACSigner(secret="key2")
        sig = s1.sign(b"data")
        assert not s2.verify(b"data", sig)

    def test_verify_tampered_data(self):
        signer = HMACSigner(secret="key")
        sig = signer.sign(b"original")
        assert not signer.verify(b"tampered", sig)


class TestArchiveSigning:
    async def test_sign_and_verify_archive(self, tmp_path):
        archive = tmp_path / "test.aquilia"
        with tarfile.open(str(archive), "w:gz") as tar:
            info = tarfile.TarInfo(name="test.txt")
            data = b"hello"
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        signer = HMACSigner(secret="secret")
        sig_path = await sign_archive(str(archive), signer)
        assert Path(sig_path).exists()
        result = await verify_archive(str(archive), sig_path, signer)
        assert result is True
