"""
Tests for the unified artifact system.

Covers:
- Core types: Artifact, ArtifactEnvelope, ArtifactKind, ArtifactIntegrity, ArtifactProvenance
- Builder API: ArtifactBuilder fluent interface
- Stores: MemoryArtifactStore, FilesystemArtifactStore
- Reader: ArtifactReader (load, inspect, verify, diff, history, search)
- Typed Kinds: all 9 subclasses (CodeArtifact, ModelArtifact, …)
- Integration: workspace compiler artifact output
- Enhanced: evolve, from_artifact, sorting, typed deserialization, batch_verify,
            stats, import_bundle, count, iter/contains, validation
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from aquilia.artifacts import (
    # Core
    Artifact,
    ArtifactEnvelope,
    ArtifactKind,
    ArtifactProvenance,
    ArtifactIntegrity,
    register_artifact_kind,
    # Builder
    ArtifactBuilder,
    # Store
    ArtifactStore,
    MemoryArtifactStore,
    FilesystemArtifactStore,
    # Reader
    ArtifactReader,
    # Typed Kinds
    CodeArtifact,
    ModelArtifact,
    ConfigArtifact,
    TemplateArtifact,
    MigrationArtifact,
    RegistryArtifact,
    RouteArtifact,
    DIGraphArtifact,
    BundleArtifact,
)


# ════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════


@pytest.fixture
def memory_store():
    return MemoryArtifactStore()


@pytest.fixture
def fs_store(tmp_path):
    return FilesystemArtifactStore(str(tmp_path / "aq-store"))


@pytest.fixture
def sample_artifact():
    return (
        ArtifactBuilder("test-config", kind="config", version="1.0.0")
        .set_payload({"database": {"url": "sqlite:///test.db"}})
        .tag("env", "test")
        .set_metadata(author="tester")
        .auto_provenance()
        .build()
    )


@pytest.fixture
def sample_artifact_v2():
    return (
        ArtifactBuilder("test-config", kind="config", version="2.0.0")
        .set_payload({"database": {"url": "postgres://localhost/prod"}})
        .tag("env", "production")
        .set_metadata(author="deployer")
        .auto_provenance()
        .build()
    )


# ════════════════════════════════════════════════════════════════════════
# Core: ArtifactKind
# ════════════════════════════════════════════════════════════════════════


class TestArtifactKind:
    def test_enum_values(self):
        assert ArtifactKind.CONFIG == "config"
        assert ArtifactKind.CODE == "code"
        assert ArtifactKind.MODEL == "model"
        assert ArtifactKind.TEMPLATE == "template"
        assert ArtifactKind.MIGRATION == "migration"
        assert ArtifactKind.REGISTRY == "registry"
        assert ArtifactKind.ROUTE == "route"
        assert ArtifactKind.DI_GRAPH == "di_graph"
        assert ArtifactKind.BUNDLE == "bundle"
        assert ArtifactKind.CUSTOM == "custom"

    def test_is_str_enum(self):
        assert isinstance(ArtifactKind.CONFIG, str)
        assert ArtifactKind.CONFIG == "config"


# ════════════════════════════════════════════════════════════════════════
# Core: ArtifactIntegrity
# ════════════════════════════════════════════════════════════════════════


class TestArtifactIntegrity:
    def test_compute(self):
        data = b"hello world"
        integrity = ArtifactIntegrity.compute(data)
        assert integrity.algorithm == "sha256"
        assert len(integrity.digest) == 64

    def test_verify_pass(self):
        data = b"hello world"
        integrity = ArtifactIntegrity.compute(data)
        assert integrity.verify(data) is True

    def test_verify_fail(self):
        data = b"hello world"
        integrity = ArtifactIntegrity.compute(data)
        assert integrity.verify(b"goodbye world") is False

    def test_to_dict_from_dict(self):
        integrity = ArtifactIntegrity.compute(b"test")
        d = integrity.to_dict()
        assert "algorithm" in d
        assert "digest" in d
        restored = ArtifactIntegrity.from_dict(d)
        assert restored.algorithm == integrity.algorithm
        assert restored.digest == integrity.digest

    def test_frozen(self):
        integrity = ArtifactIntegrity.compute(b"test")
        with pytest.raises(AttributeError):
            integrity.digest = "tampered"


# ════════════════════════════════════════════════════════════════════════
# Core: ArtifactProvenance
# ════════════════════════════════════════════════════════════════════════


class TestArtifactProvenance:
    def test_auto(self):
        prov = ArtifactProvenance.auto("/some/path")
        assert prov.created_at != ""
        assert prov.created_by != ""
        assert prov.hostname != ""
        assert prov.source_path == "/some/path"
        assert prov.build_tool == "aquilia"

    def test_to_dict_from_dict(self):
        prov = ArtifactProvenance.auto()
        d = prov.to_dict()
        restored = ArtifactProvenance.from_dict(d)
        assert restored.created_at == prov.created_at
        assert restored.created_by == prov.created_by
        assert restored.hostname == prov.hostname

    def test_frozen(self):
        prov = ArtifactProvenance.auto()
        with pytest.raises(AttributeError):
            prov.created_by = "tampered"


# ════════════════════════════════════════════════════════════════════════
# Core: ArtifactEnvelope
# ════════════════════════════════════════════════════════════════════════


class TestArtifactEnvelope:
    def test_to_dict_format(self):
        env = ArtifactEnvelope(kind="config", name="x", version="1.0.0")
        d = env.to_dict()
        assert d["__format__"] == "aquilia-artifact"
        assert d["schema_version"] == "1.0"
        assert d["kind"] == "config"
        assert d["name"] == "x"

    def test_roundtrip(self):
        env = ArtifactEnvelope(
            kind="model",
            name="my-model",
            version="2.0.0",
            metadata={"key": "value"},
            tags={"env": "prod"},
            payload={"framework": "pytorch"},
        )
        d = env.to_dict()
        restored = ArtifactEnvelope.from_dict(d)
        assert restored.kind == "model"
        assert restored.name == "my-model"
        assert restored.version == "2.0.0"
        assert restored.metadata == {"key": "value"}
        assert restored.tags == {"env": "prod"}
        assert restored.payload == {"framework": "pytorch"}


# ════════════════════════════════════════════════════════════════════════
# Core: Artifact
# ════════════════════════════════════════════════════════════════════════


class TestArtifact:
    def test_basic_properties(self, sample_artifact):
        a = sample_artifact
        assert a.name == "test-config"
        assert a.version == "1.0.0"
        assert a.kind == "config"
        assert a.qualified_name == "test-config:1.0.0"
        assert a.digest.startswith("sha256:")
        assert a.created_at != ""
        assert a.tags == {"env": "test"}
        assert a.metadata == {"author": "tester"}

    def test_verify_passes(self, sample_artifact):
        assert sample_artifact.verify() is True

    def test_to_json_from_json(self, sample_artifact):
        raw = sample_artifact.to_json()
        restored = Artifact.from_json(raw)
        assert restored.name == sample_artifact.name
        assert restored.version == sample_artifact.version
        assert restored.digest == sample_artifact.digest

    def test_to_bytes_from_bytes(self, sample_artifact):
        data = sample_artifact.to_bytes()
        restored = Artifact.from_bytes(data)
        assert restored.name == sample_artifact.name
        assert restored.digest == sample_artifact.digest

    def test_to_dict_from_dict(self, sample_artifact):
        d = sample_artifact.to_dict()
        assert d["__format__"] == "aquilia-artifact"
        restored = Artifact.from_dict(d)
        assert restored.digest == sample_artifact.digest

    def test_equality(self, sample_artifact):
        # Same build parameters → same digest
        a2 = (
            ArtifactBuilder("test-config", kind="config", version="1.0.0")
            .set_payload({"database": {"url": "sqlite:///test.db"}})
            .tag("env", "test")
            .set_metadata(author="tester")
            .auto_provenance()
            .build()
        )
        # Digests match because payloads are the same
        assert sample_artifact.digest == a2.digest

    def test_hash(self, sample_artifact):
        s = {sample_artifact}
        assert sample_artifact in s

    def test_repr(self, sample_artifact):
        r = repr(sample_artifact)
        assert "Artifact" in r
        assert "test-config" in r


# ════════════════════════════════════════════════════════════════════════
# Builder: ArtifactBuilder
# ════════════════════════════════════════════════════════════════════════


class TestArtifactBuilder:
    def test_simple_build(self):
        a = ArtifactBuilder("x", kind="config", version="1.0.0").set_payload({"k": "v"}).build()
        assert a.name == "x"
        assert a.kind == "config"
        assert a.version == "1.0.0"
        assert a.payload == {"k": "v"}
        assert a.digest.startswith("sha256:")

    def test_chaining(self):
        a = (
            ArtifactBuilder("x")
            .set_payload({"a": 1})
            .merge_payload({"b": 2})
            .tag("env", "test")
            .tags(team="platform")
            .set_metadata(author="bot")
            .set_version("3.0.0")
            .auto_provenance()
            .build()
        )
        assert a.payload == {"a": 1, "b": 2}
        assert a.tags == {"env": "test", "team": "platform"}
        assert a.metadata == {"author": "bot"}
        assert a.version == "3.0.0"

    def test_set_provenance(self):
        a = (
            ArtifactBuilder("x")
            .set_payload({})
            .set_provenance(git_sha="abc123", source_path="/foo")
            .build()
        )
        assert a.provenance.git_sha == "abc123"
        assert a.provenance.source_path == "/foo"

    def test_add_file(self):
        a = (
            ArtifactBuilder("x")
            .set_payload({})
            .add_file("model.pt", role="model", digest="sha256:abc", size=1024)
            .build()
        )
        assert "_files" in a.payload
        assert a.payload["_files"][0]["path"] == "model.pt"

    def test_auto_provenance_fills(self):
        a = ArtifactBuilder("x").set_payload({}).build()
        assert a.provenance.created_at != ""
        assert a.provenance.build_tool == "aquilia"

    def test_integrity_computed(self):
        a = ArtifactBuilder("x").set_payload({"key": "value"}).build()
        assert a.integrity.digest != ""
        assert a.integrity.algorithm == "sha256"

    def test_verify_after_build(self):
        a = ArtifactBuilder("x").set_payload({"k": "v"}).build()
        assert a.verify() is True


# ════════════════════════════════════════════════════════════════════════
# Store: MemoryArtifactStore
# ════════════════════════════════════════════════════════════════════════


class TestMemoryArtifactStore:
    def test_save_and_load(self, memory_store, sample_artifact):
        digest = memory_store.save(sample_artifact)
        assert digest == sample_artifact.digest
        loaded = memory_store.load("test-config", version="1.0.0")
        assert loaded is not None
        assert loaded.digest == sample_artifact.digest

    def test_load_latest(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        latest = memory_store.load("test-config")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_load_not_found(self, memory_store):
        assert memory_store.load("nonexistent") is None

    def test_load_by_digest(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        loaded = memory_store.load_by_digest(sample_artifact.digest)
        assert loaded is not None
        assert loaded.name == "test-config"

    def test_list_artifacts(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        all_artifacts = memory_store.list_artifacts()
        assert len(all_artifacts) == 2

    def test_list_by_kind(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        result = memory_store.list_artifacts(kind="config")
        assert len(result) == 1
        result = memory_store.list_artifacts(kind="model")
        assert len(result) == 0

    def test_list_by_tag(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        result = memory_store.list_artifacts(tag_key="env", tag_value="production")
        assert len(result) == 1
        assert result[0].version == "2.0.0"

    def test_delete(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        assert memory_store.exists("test-config")
        removed = memory_store.delete("test-config")
        assert removed == 1
        assert not memory_store.exists("test-config")

    def test_delete_specific_version(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        removed = memory_store.delete("test-config", version="1.0.0")
        assert removed == 1
        assert not memory_store.exists("test-config", version="1.0.0")
        assert memory_store.exists("test-config", version="2.0.0")

    def test_exists(self, memory_store, sample_artifact):
        assert not memory_store.exists("test-config")
        memory_store.save(sample_artifact)
        assert memory_store.exists("test-config")
        assert memory_store.exists("test-config", version="1.0.0")
        assert not memory_store.exists("test-config", version="9.9.9")

    def test_gc(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        # Keep only v1's digest
        removed = memory_store.gc({sample_artifact.digest})
        assert removed == 1
        assert len(memory_store) == 1

    def test_clear(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        assert len(memory_store) == 1
        memory_store.clear()
        assert len(memory_store) == 0

    def test_len(self, memory_store, sample_artifact):
        assert len(memory_store) == 0
        memory_store.save(sample_artifact)
        assert len(memory_store) == 1


# ════════════════════════════════════════════════════════════════════════
# Store: FilesystemArtifactStore
# ════════════════════════════════════════════════════════════════════════


class TestFilesystemArtifactStore:
    def test_save_creates_file(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        files = list(fs_store.root.glob("*.aq.json"))
        assert len(files) == 1
        assert "test-config-1.0.0" in files[0].name

    def test_save_and_load(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        loaded = fs_store.load("test-config", version="1.0.0")
        assert loaded is not None
        assert loaded.digest == sample_artifact.digest
        assert loaded.name == "test-config"
        assert loaded.payload == sample_artifact.payload

    def test_load_latest(self, fs_store, sample_artifact, sample_artifact_v2):
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact_v2)
        latest = fs_store.load("test-config")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_load_not_found(self, fs_store):
        assert fs_store.load("nonexistent") is None
        assert fs_store.load("nonexistent", version="1.0.0") is None

    def test_load_by_digest(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        loaded = fs_store.load_by_digest(sample_artifact.digest)
        assert loaded is not None
        assert loaded.name == "test-config"

    def test_list_artifacts(self, fs_store, sample_artifact, sample_artifact_v2):
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact_v2)
        all_artifacts = fs_store.list_artifacts()
        assert len(all_artifacts) == 2

    def test_list_by_kind(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        assert len(fs_store.list_artifacts(kind="config")) == 1
        assert len(fs_store.list_artifacts(kind="model")) == 0

    def test_delete(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        assert fs_store.exists("test-config", version="1.0.0")
        removed = fs_store.delete("test-config", version="1.0.0")
        assert removed == 1
        assert not fs_store.exists("test-config", version="1.0.0")

    def test_exists(self, fs_store, sample_artifact):
        assert not fs_store.exists("test-config")
        fs_store.save(sample_artifact)
        assert fs_store.exists("test-config")
        assert fs_store.exists("test-config", version="1.0.0")

    def test_gc(self, fs_store, sample_artifact, sample_artifact_v2):
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact_v2)
        removed = fs_store.gc({sample_artifact.digest})
        assert removed == 1
        assert fs_store.exists("test-config", version="1.0.0")
        assert not fs_store.exists("test-config", version="2.0.0")

    def test_export_bundle(self, fs_store, sample_artifact, sample_artifact_v2, tmp_path):
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact_v2)
        bundle_path = str(tmp_path / "export.aq.json")
        result = fs_store.export_bundle(["test-config"], bundle_path)
        assert Path(result).exists()
        with open(result) as f:
            data = json.load(f)
        assert data["__format__"] == "aquilia-artifact"
        assert data["kind"] == "bundle"

    def test_atomic_write(self, fs_store, sample_artifact):
        # Save twice — should not leave .tmp files
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact)
        tmps = list(fs_store.root.glob("*.tmp"))
        assert len(tmps) == 0

    def test_file_content_is_valid_json(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        files = list(fs_store.root.glob("*.aq.json"))
        with open(files[0]) as f:
            data = json.load(f)
        assert data["__format__"] == "aquilia-artifact"
        assert data["name"] == "test-config"


# ════════════════════════════════════════════════════════════════════════
# Store: ArtifactStore factory
# ════════════════════════════════════════════════════════════════════════


class TestArtifactStoreFactory:
    def test_returns_filesystem_store(self, tmp_path):
        store = ArtifactStore(str(tmp_path / "factory-store"))
        assert isinstance(store, FilesystemArtifactStore)


# ════════════════════════════════════════════════════════════════════════
# Reader: ArtifactReader
# ════════════════════════════════════════════════════════════════════════


class TestArtifactReader:
    def test_load(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        a = reader.load("test-config", version="1.0.0")
        assert a is not None
        assert a.name == "test-config"

    def test_load_or_fail_found(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        a = reader.load_or_fail("test-config", version="1.0.0")
        assert a.name == "test-config"

    def test_load_or_fail_not_found(self, memory_store):
        reader = ArtifactReader(memory_store)
        with pytest.raises(FileNotFoundError):
            reader.load_or_fail("ghost")

    def test_load_by_digest(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        a = reader.load_by_digest(sample_artifact.digest)
        assert a is not None

    def test_list_all(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        reader = ArtifactReader(memory_store)
        assert len(reader.list_all()) == 2
        assert len(reader.list_all(kind="config")) == 2
        assert len(reader.list_all(kind="model")) == 0

    def test_history(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        reader = ArtifactReader(memory_store)
        versions = reader.history("test-config")
        assert len(versions) == 2

    def test_search_by_kind(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        results = reader.search(kind="config")
        assert len(results) == 1

    def test_search_by_tag(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        results = reader.search(tag_key="env", tag_value="test")
        assert len(results) == 1
        results = reader.search(tag_key="env", tag_value="production")
        assert len(results) == 0

    def test_search_by_name_prefix(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        results = reader.search(name_prefix="test-")
        assert len(results) == 1
        results = reader.search(name_prefix="other-")
        assert len(results) == 0

    def test_verify(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        assert reader.verify(sample_artifact) is True

    def test_verify_by_name(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        assert reader.verify_by_name("test-config", version="1.0.0") is True

    def test_inspect(self, sample_artifact):
        info = ArtifactReader.inspect(sample_artifact)
        assert info["name"] == "test-config"
        assert info["version"] == "1.0.0"
        assert info["kind"] == "config"
        assert info["verified"] is True
        assert info["payload_size"] > 0
        assert "payload_preview" in info
        assert "digest" in info

    def test_diff_identical(self, sample_artifact):
        diff = ArtifactReader.diff(sample_artifact, sample_artifact)
        assert diff["digest_match"] is True
        assert diff["changed_keys"] == []

    def test_diff_different(self, sample_artifact, sample_artifact_v2):
        diff = ArtifactReader.diff(sample_artifact, sample_artifact_v2)
        assert diff["digest_match"] is False
        assert diff["name_match"] is True
        assert diff["kind_match"] is True
        assert diff["version_a"] == "1.0.0"
        assert diff["version_b"] == "2.0.0"
        assert "changed_keys" in diff


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: ConfigArtifact
# ════════════════════════════════════════════════════════════════════════


class TestConfigArtifact:
    def test_build(self):
        a = ConfigArtifact.build(
            name="app-config",
            version="1.0.0",
            config={"database": "sqlite:///test.db", "debug": True},
        )
        assert isinstance(a, ConfigArtifact)
        assert a.kind == "config"
        assert a.config == {"database": "sqlite:///test.db", "debug": True}
        assert a.get("database") == "sqlite:///test.db"
        assert a.get("missing", "default") == "default"

    def test_verify(self):
        a = ConfigArtifact.build(
            name="x", version="1.0.0",
            config={"key": "value"},
        )
        assert a.verify() is True

    def test_is_artifact_subclass(self):
        a = ConfigArtifact.build(name="x", version="1.0.0", config={})
        assert isinstance(a, Artifact)
        assert isinstance(a, ConfigArtifact)


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: CodeArtifact
# ════════════════════════════════════════════════════════════════════════


class TestCodeArtifact:
    def test_build(self):
        a = CodeArtifact.build(
            name="users-module",
            version="1.0.0",
            controllers=["UserController"],
            services=["UserService"],
            route_prefix="/users",
            fault_domain="USERS",
            depends_on=["auth"],
        )
        assert isinstance(a, CodeArtifact)
        assert a.kind == "code"
        assert a.controllers == ["UserController"]
        assert a.services == ["UserService"]
        assert a.route_prefix == "/users"
        assert a.fault_domain == "USERS"
        assert a.depends_on == ["auth"]

    def test_defaults(self):
        a = CodeArtifact.build(name="x", version="1.0.0")
        assert a.controllers == []
        assert a.services == []
        assert a.route_prefix == "/"
        assert a.fault_domain == "GENERIC"
        assert a.depends_on == []


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: ModelArtifact
# ════════════════════════════════════════════════════════════════════════


class TestModelArtifact:
    def test_build(self):
        a = ModelArtifact.build(
            name="my-model",
            version="v1.0.0",
            framework="pytorch",
            entrypoint="model.pt",
            accuracy=0.95,
            files=[{"path": "model.pt", "digest": "sha256:abc", "size": 1024}],
        )
        assert isinstance(a, ModelArtifact)
        assert a.kind == "model"
        assert a.framework == "pytorch"
        assert a.entrypoint == "model.pt"
        assert a.accuracy == 0.95
        assert len(a.files) == 1

    def test_defaults(self):
        a = ModelArtifact.build(name="x", version="1.0.0")
        assert a.framework == "custom"
        assert a.entrypoint == ""
        assert a.accuracy == 0.0
        assert a.files == []


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: TemplateArtifact
# ════════════════════════════════════════════════════════════════════════


class TestTemplateArtifact:
    def test_build(self):
        a = TemplateArtifact.build(
            name="app-templates",
            version="1.0.0",
            templates={"index.html": {"hash": "abc"}, "base.html": {"hash": "def"}},
        )
        assert isinstance(a, TemplateArtifact)
        assert a.kind == "template"
        assert a.template_count == 2
        assert "index.html" in a.templates


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: MigrationArtifact
# ════════════════════════════════════════════════════════════════════════


class TestMigrationArtifact:
    def test_build(self):
        a = MigrationArtifact.build(
            name="db-migrations",
            version="1.0.0",
            migrations_applied=["0001_initial", "0002_add_users"],
            head="0002_add_users",
            schema_hash="sha256:schema123",
        )
        assert isinstance(a, MigrationArtifact)
        assert a.kind == "migration"
        assert a.head == "0002_add_users"
        assert len(a.migrations_applied) == 2
        assert a.schema_hash == "sha256:schema123"


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: RegistryArtifact
# ════════════════════════════════════════════════════════════════════════


class TestRegistryArtifact:
    def test_build(self):
        a = RegistryArtifact.build(
            name="workspace-registry",
            version="1.0.0",
            modules=[
                {"name": "users", "version": "1.0.0"},
                {"name": "orders", "version": "2.0.0"},
            ],
        )
        assert isinstance(a, RegistryArtifact)
        assert a.kind == "registry"
        assert len(a.modules) == 2


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: RouteArtifact
# ════════════════════════════════════════════════════════════════════════


class TestRouteArtifact:
    def test_build(self):
        a = RouteArtifact.build(
            name="app-routes",
            version="1.0.0",
            routes=[
                {"module": "users", "controller": "UserCtrl", "prefix": "/users"},
                {"module": "orders", "controller": "OrderCtrl", "prefix": "/orders"},
            ],
        )
        assert isinstance(a, RouteArtifact)
        assert a.kind == "route"
        assert len(a.routes) == 2


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: DIGraphArtifact
# ════════════════════════════════════════════════════════════════════════


class TestDIGraphArtifact:
    def test_build(self):
        a = DIGraphArtifact.build(
            name="app-di",
            version="1.0.0",
            providers=[
                {"module": "users", "class": "UserService", "scope": "app"},
            ],
        )
        assert isinstance(a, DIGraphArtifact)
        assert a.kind == "di_graph"
        assert len(a.providers) == 1


# ════════════════════════════════════════════════════════════════════════
# Typed Kinds: BundleArtifact
# ════════════════════════════════════════════════════════════════════════


class TestBundleArtifact:
    def test_build(self):
        inner = (
            ArtifactBuilder("inner", kind="config", version="1.0.0")
            .set_payload({"k": "v"})
            .build()
        )
        a = BundleArtifact.build(
            name="release-bundle",
            version="1.0.0",
            artifacts=[inner.to_dict()],
        )
        assert isinstance(a, BundleArtifact)
        assert a.kind == "bundle"
        assert a.artifact_count == 1

    def test_unpack(self):
        inner1 = ArtifactBuilder("a", kind="config", version="1.0.0").set_payload({"x": 1}).build()
        inner2 = ArtifactBuilder("b", kind="model", version="2.0.0").set_payload({"y": 2}).build()
        bundle = BundleArtifact.build(
            name="bundle",
            version="1.0.0",
            artifacts=[inner1.to_dict(), inner2.to_dict()],
        )
        unpacked = bundle.unpack()
        assert len(unpacked) == 2
        assert unpacked[0].name == "a"
        assert unpacked[1].name == "b"


# ════════════════════════════════════════════════════════════════════════
# Integration: Store + Reader roundtrip
# ════════════════════════════════════════════════════════════════════════


class TestStoreReaderIntegration:
    def test_memory_roundtrip(self, memory_store):
        a = ConfigArtifact.build(
            name="cfg", version="1.0.0", config={"key": "value"}
        )
        memory_store.save(a)
        reader = ArtifactReader(memory_store)
        loaded = reader.load_or_fail("cfg", version="1.0.0")
        assert loaded.name == "cfg"
        assert loaded.verify() is True

    def test_filesystem_roundtrip(self, fs_store):
        a = ModelArtifact.build(
            name="model",
            version="v1",
            framework="sklearn",
            entrypoint="model.pkl",
        )
        fs_store.save(a)
        reader = ArtifactReader(fs_store)
        loaded = reader.load_or_fail("model", version="v1")
        assert loaded.name == "model"
        assert loaded.verify() is True
        info = reader.inspect(loaded)
        assert info["kind"] == "model"
        assert info["verified"] is True

    def test_search_and_verify(self, memory_store):
        for i in range(5):
            a = ArtifactBuilder(
                f"item-{i}", kind="config" if i % 2 == 0 else "code",
                version=f"1.{i}.0"
            ).set_payload({"index": i}).tag("batch", "test").build()
            memory_store.save(a)

        reader = ArtifactReader(memory_store)
        configs = reader.search(kind="config")
        assert len(configs) == 3  # indices 0, 2, 4
        codes = reader.search(kind="code")
        assert len(codes) == 2  # indices 1, 3
        all_tagged = reader.search(tag_key="batch", tag_value="test")
        assert len(all_tagged) == 5


# ════════════════════════════════════════════════════════════════════════
# Integration: Exports from aquilia.__init__
# ════════════════════════════════════════════════════════════════════════


class TestExportsFromMain:
    def test_import_from_aquilia(self):
        from aquilia import (
            Artifact,
            ArtifactBuilder,
            ArtifactStore,
            ArtifactReader,
            MemoryArtifactStore,
            FilesystemArtifactStore,
            ArtifactKind,
            ArtifactProvenance,
            ArtifactIntegrity,
            ArtifactEnvelope,
            CodeArtifact,
            ModelArtifact,
            ConfigArtifact,
            TemplateArtifact,
            MigrationArtifact,
            RegistryArtifact,
            RouteArtifact,
            DIGraphArtifact,
            BundleArtifact,
        )
        # All should be importable
        assert Artifact is not None
        assert ArtifactBuilder is not None
        assert ArtifactStore is not None


# ════════════════════════════════════════════════════════════════════════
# Integration: CLI commands import
# ════════════════════════════════════════════════════════════════════════


class TestCLIArtifactCommands:
    def test_artifact_group_importable(self):
        from aquilia.cli.commands.artifacts import artifact_group
        assert artifact_group is not None
        assert artifact_group.name == "artifact"

    def test_commands_registered(self):
        from aquilia.cli.commands.artifacts import artifact_group
        command_names = [cmd for cmd in artifact_group.commands]
        assert "list" in command_names
        assert "inspect" in command_names
        assert "verify" in command_names
        assert "verify-all" in command_names
        assert "gc" in command_names
        assert "export" in command_names
        assert "import" in command_names
        assert "diff" in command_names
        assert "history" in command_names
        assert "count" in command_names
        assert "stats" in command_names


# ════════════════════════════════════════════════════════════════════════
# Edge cases
# ════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_empty_payload(self):
        a = ArtifactBuilder("x").set_payload(None).build()
        assert a.payload is None
        assert a.digest.startswith("sha256:")

    def test_list_payload(self):
        a = ArtifactBuilder("x").set_payload([1, 2, 3]).build()
        assert a.payload == [1, 2, 3]
        assert a.verify() is True

    def test_string_payload(self):
        a = ArtifactBuilder("x").set_payload("hello world").build()
        assert a.payload == "hello world"
        assert a.verify() is True

    def test_nested_dict_payload(self):
        payload = {
            "a": {"b": {"c": [1, 2, {"d": True}]}},
            "e": None,
        }
        a = ArtifactBuilder("x").set_payload(payload).build()
        assert a.payload == payload
        assert a.verify() is True

    def test_special_chars_in_name(self, fs_store):
        a = ArtifactBuilder("my/special:name", version="1.0.0").set_payload({}).build()
        fs_store.save(a)
        loaded = fs_store.load("my/special:name", version="1.0.0")
        assert loaded is not None

    def test_overwrite_in_store(self, memory_store):
        a1 = ArtifactBuilder("x", version="1.0.0").set_payload({"v": 1}).build()
        a2 = ArtifactBuilder("x", version="1.0.0").set_payload({"v": 2}).build()
        memory_store.save(a1)
        memory_store.save(a2)
        loaded = memory_store.load("x", version="1.0.0")
        # Last save wins
        assert loaded.payload == {"v": 2}

    def test_gc_empty_referenced_removes_all(self, memory_store):
        a = ArtifactBuilder("x", version="1.0.0").set_payload({}).build()
        memory_store.save(a)
        removed = memory_store.gc(set())
        assert removed == 1
        assert len(memory_store) == 0

    def test_gc_all_referenced_removes_none(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        removed = memory_store.gc({sample_artifact.digest})
        assert removed == 0
        assert len(memory_store) == 1


# ════════════════════════════════════════════════════════════════════════
# Enhanced Core: age_seconds, size_bytes, evolve, sorting, typed deser
# ════════════════════════════════════════════════════════════════════════


class TestArtifactEnhancements:
    def test_age_seconds(self, sample_artifact):
        age = sample_artifact.age_seconds
        assert isinstance(age, float)
        assert age >= 0.0

    def test_size_bytes(self, sample_artifact):
        sz = sample_artifact.size_bytes
        assert isinstance(sz, int)
        assert sz > 0

    def test_size_bytes_none_payload(self):
        a = ArtifactBuilder("x").set_payload(None).build()
        assert a.size_bytes == 0

    def test_evolve_creates_new_version(self, sample_artifact):
        v2 = sample_artifact.evolve(version="2.0.0")
        assert v2.version == "2.0.0"
        assert v2.name == sample_artifact.name
        assert v2.kind == sample_artifact.kind
        assert v2.tags.get("derived_from") == sample_artifact.digest
        # Same payload → same digest (content-addressed)
        assert v2.payload == sample_artifact.payload

    def test_evolve_payload_override(self, sample_artifact):
        v2 = sample_artifact.evolve(version="2.0.0", database={"url": "pg://x"})
        assert v2.payload["database"] == {"url": "pg://x"}

    def test_evolve_preserves_tags(self):
        a = (
            ArtifactBuilder("x", version="1.0.0")
            .set_payload({"k": 1})
            .tag("env", "prod")
            .build()
        )
        v2 = a.evolve(version="2.0.0")
        assert v2.tags["env"] == "prod"
        assert "derived_from" in v2.tags

    def test_sorting_lt(self):
        a = ArtifactBuilder("alpha", version="1.0.0").set_payload({}).build()
        b = ArtifactBuilder("beta", version="1.0.0").set_payload({}).build()
        assert a < b
        assert a <= b
        assert not b < a

    def test_sorting_same_name_version(self):
        a = ArtifactBuilder("x", version="1.0.0").set_payload({}).build()
        b = ArtifactBuilder("x", version="2.0.0").set_payload({}).build()
        assert a < b

    def test_sorting_list(self):
        arts = [
            ArtifactBuilder("c", version="1").set_payload({}).build(),
            ArtifactBuilder("a", version="1").set_payload({}).build(),
            ArtifactBuilder("b", version="1").set_payload({}).build(),
        ]
        names = [a.name for a in sorted(arts)]
        assert names == ["a", "b", "c"]

    def test_repr_empty_digest(self):
        a = ArtifactBuilder("x").set_payload({}).build()
        r = repr(a)
        assert "x" in r

    def test_is_known_kind_on_envelope(self, sample_artifact):
        assert sample_artifact.envelope.is_known_kind is True

    def test_is_unknown_kind_on_envelope(self):
        a = ArtifactBuilder("x", kind="alien").set_payload({}).build()
        assert a.envelope.is_known_kind is False


# ════════════════════════════════════════════════════════════════════════
# Typed Deserialization via _KIND_REGISTRY
# ════════════════════════════════════════════════════════════════════════


class TestTypedDeserialization:
    def test_config_artifact_from_dict(self):
        orig = ConfigArtifact.build("cfg", "1.0.0", {"key": "val"})
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, ConfigArtifact)
        assert restored.config == {"key": "val"}

    def test_code_artifact_from_dict(self):
        orig = CodeArtifact.build("mod", "1.0.0", controllers=["A"])
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, CodeArtifact)
        assert restored.controllers == ["A"]

    def test_model_artifact_from_dict(self):
        orig = ModelArtifact.build("mdl", "1.0.0", framework="sklearn")
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, ModelArtifact)
        assert restored.framework == "sklearn"

    def test_template_artifact_from_dict(self):
        orig = TemplateArtifact.build("tpl", "1.0.0", templates={"a": "b"})
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, TemplateArtifact)
        assert restored.templates == {"a": "b"}

    def test_migration_artifact_from_dict(self):
        orig = MigrationArtifact.build("mig", "1.0.0", head="abc")
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, MigrationArtifact)
        assert restored.head == "abc"

    def test_registry_artifact_from_dict(self):
        orig = RegistryArtifact.build("reg", "1.0.0", modules=[{"name": "m1"}])
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, RegistryArtifact)

    def test_route_artifact_from_dict(self):
        orig = RouteArtifact.build("rt", "1.0.0", routes=[{"path": "/"}])
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, RouteArtifact)

    def test_di_graph_artifact_from_dict(self):
        orig = DIGraphArtifact.build("di", "1.0.0", providers=[{"cls": "Svc"}])
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, DIGraphArtifact)

    def test_bundle_artifact_from_dict(self):
        orig = BundleArtifact.build("bnd", "1.0.0")
        d = orig.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, BundleArtifact)

    def test_unknown_kind_returns_base_artifact(self):
        a = ArtifactBuilder("x", kind="alien").set_payload({}).build()
        d = a.to_dict()
        restored = Artifact.from_dict(d)
        assert type(restored) is Artifact

    def test_register_custom_kind(self):
        class CustomArtifact(Artifact):
            pass

        register_artifact_kind("custom_test_xyz", CustomArtifact)
        a = ArtifactBuilder("x", kind="custom_test_xyz").set_payload({}).build()
        d = a.to_dict()
        restored = Artifact.from_dict(d)
        assert isinstance(restored, CustomArtifact)


# ════════════════════════════════════════════════════════════════════════
# Enhanced Builder: from_artifact, validation
# ════════════════════════════════════════════════════════════════════════


class TestBuilderEnhancements:
    def test_from_artifact(self, sample_artifact):
        b = ArtifactBuilder.from_artifact(sample_artifact, version="3.0.0")
        v3 = b.build()
        assert v3.name == sample_artifact.name
        assert v3.version == "3.0.0"
        assert v3.kind == sample_artifact.kind
        assert v3.payload == sample_artifact.payload
        assert v3.tags.get("derived_from") == sample_artifact.digest

    def test_from_artifact_preserves_metadata(self, sample_artifact):
        v2 = ArtifactBuilder.from_artifact(sample_artifact).build()
        assert v2.metadata.get("author") == "tester"

    def test_from_artifact_preserves_tags(self):
        a = (
            ArtifactBuilder("x", version="1.0.0")
            .set_payload({})
            .tag("env", "staging")
            .build()
        )
        v2 = ArtifactBuilder.from_artifact(a, version="2.0.0").build()
        assert v2.tags["env"] == "staging"

    def test_build_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            ArtifactBuilder("").set_payload({}).build()

    def test_build_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            ArtifactBuilder("  ").set_payload({}).build()


# ════════════════════════════════════════════════════════════════════════
# Enhanced Store: iter, contains, count, import_bundle
# ════════════════════════════════════════════════════════════════════════


class TestStoreEnhancements:
    # ── MemoryArtifactStore ──────────────────────────────────────────

    def test_memory_iter(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        items = list(memory_store)
        assert len(items) == 1
        assert items[0].name == sample_artifact.name

    def test_memory_contains_by_name(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        assert sample_artifact.name in memory_store

    def test_memory_contains_by_digest(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        assert sample_artifact.digest in memory_store

    def test_memory_not_contains(self, memory_store):
        assert "nonexistent" not in memory_store

    def test_memory_count(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        assert memory_store.count() == 2

    def test_memory_count_by_kind(self, memory_store):
        a1 = ArtifactBuilder("x", kind="config").set_payload({}).build()
        a2 = ArtifactBuilder("y", kind="model").set_payload({}).build()
        memory_store.save(a1)
        memory_store.save(a2)
        assert memory_store.count(kind="config") == 1
        assert memory_store.count(kind="model") == 1
        assert memory_store.count() == 2

    # ── FilesystemArtifactStore ──────────────────────────────────────

    def test_fs_iter(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        items = list(fs_store)
        assert len(items) == 1

    def test_fs_contains_by_name(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        assert sample_artifact.name in fs_store

    def test_fs_contains_by_digest(self, fs_store, sample_artifact):
        fs_store.save(sample_artifact)
        assert sample_artifact.digest in fs_store

    def test_fs_not_contains(self, fs_store):
        assert "nonexistent" not in fs_store

    def test_fs_count(self, fs_store, sample_artifact, sample_artifact_v2):
        fs_store.save(sample_artifact)
        fs_store.save(sample_artifact_v2)
        assert fs_store.count() == 2

    def test_fs_count_by_kind(self, fs_store):
        a1 = ArtifactBuilder("x", kind="config").set_payload({}).build()
        a2 = ArtifactBuilder("y", kind="model").set_payload({}).build()
        fs_store.save(a1)
        fs_store.save(a2)
        assert fs_store.count(kind="config") == 1
        assert fs_store.count(kind="model") == 1

    def test_fs_import_bundle(self, fs_store, tmp_path):
        # Build a bundle file
        a1 = ArtifactBuilder("imp-a", kind="config", version="1.0").set_payload({"k": 1}).build()
        a2 = ArtifactBuilder("imp-b", kind="model", version="1.0").set_payload({"k": 2}).build()
        bundle = {
            "name": "test-bundle",
            "version": "1.0.0",
            "payload": {
                "artifacts": [a1.to_dict(), a2.to_dict()],
            },
        }
        bundle_path = tmp_path / "test-bundle.aq.json"
        bundle_path.write_text(json.dumps(bundle, default=str))

        count = fs_store.import_bundle(bundle_path)
        assert count == 2
        assert fs_store.count() == 2
        loaded = fs_store.load("imp-a", version="1.0")
        assert loaded is not None
        assert loaded.payload == {"k": 1}

    def test_fs_import_bundle_missing_file(self, fs_store, tmp_path):
        with pytest.raises(FileNotFoundError):
            fs_store.import_bundle(tmp_path / "does-not-exist.json")


# ════════════════════════════════════════════════════════════════════════
# Enhanced Reader: batch_verify, stats, names, latest, verify_by_name
# ════════════════════════════════════════════════════════════════════════


class TestReaderEnhancements:
    def test_batch_verify_all_pass(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        reader = ArtifactReader(memory_store)
        passed, failed, failed_names = reader.batch_verify()
        assert passed == 2
        assert failed == 0
        assert failed_names == []

    def test_batch_verify_empty_store(self, memory_store):
        reader = ArtifactReader(memory_store)
        passed, failed, failed_names = reader.batch_verify()
        assert passed == 0
        assert failed == 0

    def test_stats_empty(self, memory_store):
        reader = ArtifactReader(memory_store)
        info = reader.stats()
        assert info["total"] == 0
        assert info["unique_names"] == 0
        assert info["total_size_bytes"] == 0
        assert info["by_kind"] == {}

    def test_stats_with_data(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        reader = ArtifactReader(memory_store)
        info = reader.stats()
        assert info["total"] == 2
        assert info["unique_names"] == 1  # same name, two versions
        assert info["by_kind"].get("config") == 2
        assert info["total_size_bytes"] > 0
        assert info["oldest"] != ""
        assert info["newest"] != ""

    def test_stats_multi_kind(self, memory_store):
        a1 = ArtifactBuilder("x", kind="config").set_payload({}).build()
        a2 = ArtifactBuilder("y", kind="model").set_payload({}).build()
        a3 = ArtifactBuilder("z", kind="config").set_payload({}).build()
        for a in (a1, a2, a3):
            memory_store.save(a)
        reader = ArtifactReader(memory_store)
        info = reader.stats()
        assert info["by_kind"]["config"] == 2
        assert info["by_kind"]["model"] == 1
        assert info["unique_names"] == 3

    def test_names(self, memory_store, sample_artifact):
        a2 = ArtifactBuilder("another", kind="code").set_payload({}).build()
        memory_store.save(sample_artifact)
        memory_store.save(a2)
        reader = ArtifactReader(memory_store)
        names = reader.names()
        assert names == ["another", "test-config"]

    def test_latest(self, memory_store, sample_artifact, sample_artifact_v2):
        memory_store.save(sample_artifact)
        memory_store.save(sample_artifact_v2)
        reader = ArtifactReader(memory_store)
        latest = reader.latest("test-config")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_latest_not_found(self, memory_store):
        reader = ArtifactReader(memory_store)
        assert reader.latest("nonexistent") is None

    def test_verify_by_name_returns_none(self, memory_store):
        reader = ArtifactReader(memory_store)
        result = reader.verify_by_name("missing")
        assert result is None

    def test_verify_by_name_returns_true(self, memory_store, sample_artifact):
        memory_store.save(sample_artifact)
        reader = ArtifactReader(memory_store)
        result = reader.verify_by_name("test-config")
        assert result is True

    def test_store_property(self, memory_store):
        reader = ArtifactReader(memory_store)
        assert reader.store is memory_store

    def test_inspect_has_size_bytes(self, sample_artifact):
        info = ArtifactReader.inspect(sample_artifact)
        assert "size_bytes" in info
        assert info["size_bytes"] > 0

    def test_inspect_has_source_path(self, sample_artifact):
        info = ArtifactReader.inspect(sample_artifact)
        assert "source_path" in info

    def test_diff_provenance_changed(self, sample_artifact, sample_artifact_v2):
        d = ArtifactReader.diff(sample_artifact, sample_artifact_v2)
        assert "provenance_changed" in d
        assert "tags_changed" in d
        assert "metadata_changed" in d
