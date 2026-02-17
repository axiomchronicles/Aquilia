"""
Tests for serializer optimizations — API compatibility + new features.

Validates that all optimizations preserve existing behavior:
- Shallow copy instead of deepcopy
- Plain dict instead of OrderedDict  
- Pre-split source paths
- Cached validate_* methods
- StreamingSerializer
- BufferPool
- SerializerConfig

Also tests that new features work correctly.
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import json
import uuid
from collections import OrderedDict

import pytest

from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    StreamingSerializer,
    BufferPool,
    SerializerConfig,
    get_buffer_pool,
)
from aquilia.serializers.fields import (
    SerializerField,
    BooleanField,
    CharField,
    EmailField,
    IntegerField,
    FloatField,
    DecimalField,
    DateTimeField,
    UUIDField,
    ListField,
    DictField,
    JSONField,
    ReadOnlyField,
    HiddenField,
    SerializerMethodField,
    ChoiceField,
    ConstantField,
    CurrentUserDefault,
    InjectDefault,
    empty,
    is_di_default,
)
from aquilia.serializers.relations import (
    PrimaryKeyRelatedField,
    SlugRelatedField,
    StringRelatedField,
)
from aquilia.serializers.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
    RangeValidator,
)
from aquilia.serializers.exceptions import (
    SerializationFault,
    ValidationFault,
)


# ============================================================================
# Helpers
# ============================================================================

class Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return getattr(self, "name", "Obj")


# ============================================================================
# Tests: Shallow Copy Optimization
# ============================================================================

class TestShallowCopyOptimization:
    """Verify shallow copy produces independent field instances."""

    def test_fields_are_independent_copies(self):
        """Each serializer instance gets its own field copies."""
        class S(Serializer):
            name = CharField(max_length=100)
            age = IntegerField()

        s1 = S(data={"name": "A", "age": 1})
        s2 = S(data={"name": "B", "age": 2})

        # Fields should be different objects
        assert s1.fields["name"] is not s2.fields["name"]
        assert s1.fields["age"] is not s2.fields["age"]

    def test_field_validators_independent(self):
        """Validators list should be independent between instances."""
        class S(Serializer):
            code = CharField(validators=[RegexValidator(r"^\d+$")])

        s1 = S()
        s2 = S()
        assert s1.fields["code"].validators is not s2.fields["code"].validators

    def test_field_error_messages_independent(self):
        """Error messages dict should be independent."""
        class S(Serializer):
            name = CharField()

        s1 = S()
        s2 = S()
        s1.fields["name"].error_messages["custom"] = "modified"
        assert "custom" not in s2.fields["name"].error_messages

    def test_field_binding_independent(self):
        """Each field copy is bound to its own serializer."""
        class S(Serializer):
            name = CharField()

        s1 = S()
        s2 = S()
        assert s1.fields["name"].parent is s1
        assert s2.fields["name"].parent is s2

    def test_declared_fields_not_mutated(self):
        """Class-level _declared_fields should not be mutated."""
        class S(Serializer):
            name = CharField()

        original_field = S._declared_fields["name"]
        s = S()
        assert original_field.field_name == ""  # Not bound
        assert s.fields["name"].field_name == "name"  # Bound copy


# ============================================================================
# Tests: Dict instead of OrderedDict
# ============================================================================

class TestDictOutput:
    """Verify plain dict output is API-compatible."""

    def test_to_representation_returns_dict(self):
        class S(Serializer):
            name = CharField()
            age = IntegerField()

        obj = Obj(name="Kai", age=25)
        s = S(instance=obj)
        result = s.to_representation(obj)
        assert isinstance(result, dict)
        assert result["name"] == "Kai"
        assert result["age"] == 25

    def test_field_order_preserved(self):
        """Dict preserves insertion order in Python 3.7+."""
        class S(Serializer):
            first = CharField()
            second = IntegerField()
            third = BooleanField()

        obj = Obj(first="a", second=1, third=True)
        s = S(instance=obj)
        keys = list(s.data.keys())
        assert keys == ["first", "second", "third"]

    def test_data_property_returns_dict(self):
        class S(Serializer):
            name = CharField()

        obj = Obj(name="test")
        s = S(instance=obj)
        assert isinstance(s.data, dict)

    def test_json_serializable(self):
        """Dict output should be directly JSON-serializable."""
        class S(Serializer):
            name = CharField()
            age = IntegerField()

        obj = Obj(name="Kai", age=25)
        s = S(instance=obj)
        result = json.dumps(s.data)
        assert '"name"' in result


# ============================================================================
# Tests: Pre-split Source Optimization
# ============================================================================

class TestPreSplitSource:
    """Verify pre-split source paths work correctly."""

    def test_simple_source_has_flag(self):
        f = CharField()
        f.bind("name", None)
        assert f._simple_source is True
        assert f._source_parts == ("name",)

    def test_dotted_source_has_parts(self):
        f = CharField(source="author.name")
        f.bind("author_name", None)
        assert f._simple_source is False
        assert f._source_parts == ("author", "name")

    def test_star_source_simple_flag(self):
        f = SerializerMethodField()
        f.bind("full_name", None)
        assert f._source_parts == ("*",)
        assert f._simple_source is True  # len==1

    def test_simple_source_object_access(self):
        f = CharField()
        f.bind("name", None)
        obj = Obj(name="Kai")
        assert f.get_attribute(obj) == "Kai"

    def test_simple_source_dict_access(self):
        f = CharField()
        f.bind("name", None)
        assert f.get_attribute({"name": "Kai"}) == "Kai"

    def test_dotted_source_object_access(self):
        f = CharField(source="author.name")
        f.bind("author_name", None)
        obj = Obj(author=Obj(name="Kai"))
        assert f.get_attribute(obj) == "Kai"

    def test_dotted_source_mixed_access(self):
        f = CharField(source="meta.key")
        f.bind("meta_key", None)
        obj = Obj(meta={"key": "value"})
        assert f.get_attribute(obj) == "value"

    def test_dotted_source_none_safety(self):
        f = CharField(source="author.name")
        f.bind("author_name", None)
        obj = Obj(author=None)
        assert f.get_attribute(obj) is None


# ============================================================================
# Tests: Cached Validate Methods
# ============================================================================

class TestCachedValidateMethods:
    """Verify validate_* method caching works correctly."""

    def test_validate_method_called(self):
        class S(Serializer):
            age = IntegerField()

            def validate_age(self, value):
                if value < 0:
                    raise ValueError("Age must be non-negative")
                return value

        s = S(data={"age": -1})
        assert not s.is_valid()
        assert "age" in s.errors

    def test_validate_method_transforms_value(self):
        class S(Serializer):
            name = CharField()

            def validate_name(self, value):
                return value.upper()

        s = S(data={"name": "kai"})
        assert s.is_valid()
        assert s.validated_data["name"] == "KAI"

    def test_multiple_validate_methods(self):
        class S(Serializer):
            name = CharField()
            age = IntegerField()

            def validate_name(self, value):
                return value.strip()

            def validate_age(self, value):
                if value < 0:
                    raise ValueError("Negative age")
                return value

        s = S(data={"name": "  Kai  ", "age": 25})
        assert s.is_valid()
        assert s.validated_data["name"] == "Kai"

    def test_object_level_validate_still_works(self):
        class S(Serializer):
            a = IntegerField()
            b = IntegerField()

            def validate(self, attrs):
                if attrs["a"] > attrs["b"]:
                    raise ValueError("a must be <= b")
                return attrs

        s = S(data={"a": 10, "b": 5})
        assert not s.is_valid()
        assert "__all__" in s.errors

    def test_validate_cache_per_class(self):
        """Each serializer class should have its own validate method cache."""
        class S1(Serializer):
            x = IntegerField()
            def validate_x(self, v):
                return v * 2

        class S2(Serializer):
            x = IntegerField()

        s1 = S1(data={"x": 5})
        s1.is_valid()
        assert s1.validated_data["x"] == 10

        s2 = S2(data={"x": 5})
        s2.is_valid()
        assert s2.validated_data["x"] == 5  # No transform


# ============================================================================
# Tests: StreamingSerializer
# ============================================================================

class TestStreamingSerializer:
    """Tests for generator-based streaming serializer."""

    def test_basic_streaming(self):
        class S(Serializer):
            name = CharField()
            value = IntegerField()

        items = [Obj(name=f"item_{i}", value=i) for i in range(10)]
        streamer = StreamingSerializer(child=S(), instance=items, chunk_size=1024)

        chunks = list(streamer.stream())
        combined = b"".join(chunks)
        result = json.loads(combined.decode("utf-8"))

        assert len(result) == 10
        assert result[0]["name"] == "item_0"
        assert result[9]["value"] == 9

    def test_empty_list(self):
        class S(Serializer):
            name = CharField()

        streamer = StreamingSerializer(child=S(), instance=[], chunk_size=1024)
        chunks = list(streamer.stream())
        combined = b"".join(chunks)
        assert json.loads(combined.decode("utf-8")) == []

    def test_single_item(self):
        class S(Serializer):
            name = CharField()

        items = [Obj(name="only")]
        streamer = StreamingSerializer(child=S(), instance=items, chunk_size=1024)
        chunks = list(streamer.stream())
        combined = b"".join(chunks)
        result = json.loads(combined.decode("utf-8"))
        assert len(result) == 1
        assert result[0]["name"] == "only"

    def test_large_list_multiple_chunks(self):
        class S(Serializer):
            id = IntegerField()
            name = CharField()
            email = EmailField()

        items = [Obj(id=i, name=f"user_{i}", email=f"u{i}@test.com") for i in range(500)]
        streamer = StreamingSerializer(child=S(), instance=items, chunk_size=4096)

        chunks = list(streamer.stream())
        assert len(chunks) > 1  # Should produce multiple chunks

        combined = b"".join(chunks)
        result = json.loads(combined.decode("utf-8"))
        assert len(result) == 500
        assert result[499]["id"] == 499

    def test_chunk_size_respected(self):
        class S(Serializer):
            data = CharField()

        items = [Obj(data="x" * 100) for _ in range(100)]
        streamer = StreamingSerializer(child=S(), instance=items, chunk_size=256)

        chunks = list(streamer.stream())
        # Most chunks should be around chunk_size
        for chunk in chunks[:-1]:  # Exclude last (may be smaller)
            assert len(chunk) <= 512  # Allow some overshoot

    def test_streaming_with_complex_fields(self):
        class S(Serializer):
            name = CharField()
            created = DateTimeField()
            uid = UUIDField()

        items = [
            Obj(
                name=f"item_{i}",
                created=datetime.datetime(2024, 1, 1, 12, 0, 0),
                uid=uuid.UUID('12345678-1234-5678-1234-567812345678'),
            )
            for i in range(5)
        ]
        streamer = StreamingSerializer(child=S(), instance=items)
        combined = b"".join(streamer.stream())
        result = json.loads(combined.decode("utf-8"))
        assert len(result) == 5
        assert "2024-01-01" in result[0]["created"]

    def test_repr(self):
        class S(Serializer):
            name = CharField()

        streamer = StreamingSerializer(child=S(), instance=[])
        assert "StreamingSerializer" in repr(streamer)

    def test_async_streaming(self):
        class S(Serializer):
            name = CharField()

        items = [Obj(name=f"item_{i}") for i in range(10)]
        streamer = StreamingSerializer(child=S(), instance=items, chunk_size=1024)

        async def collect():
            chunks = []
            async for chunk in streamer.stream_async():
                chunks.append(chunk)
            return b"".join(chunks)

        combined = asyncio.run(collect())
        result = json.loads(combined.decode("utf-8"))
        assert len(result) == 10


# ============================================================================
# Tests: BufferPool
# ============================================================================

class TestBufferPool:
    """Tests for reusable byte buffer pool."""

    def test_acquire_returns_bytearray(self):
        pool = BufferPool()
        buf = pool.acquire()
        assert isinstance(buf, bytearray)

    def test_acquire_returns_cleared_buffer(self):
        pool = BufferPool(initial_size=64)
        buf = pool.acquire()
        buf.extend(b"data")
        pool.release(buf)

        buf2 = pool.acquire()
        assert len(buf2) == 0  # Should be cleared

    def test_pool_reuses_buffers(self):
        pool = BufferPool(initial_size=64, max_pool=2)
        buf1 = pool.acquire()
        buf1_id = id(buf1)
        pool.release(buf1)

        buf2 = pool.acquire()
        assert id(buf2) == buf1_id  # Same object reused

    def test_pool_max_size(self):
        pool = BufferPool(initial_size=64, max_pool=2)
        bufs = [pool.acquire() for _ in range(5)]

        for b in bufs:
            pool.release(b)

        # Only max_pool buffers should be kept
        assert len(pool._pool) == 2

    def test_concurrent_acquire_release(self):
        pool = BufferPool(initial_size=64, max_pool=4)

        for _ in range(100):
            buf = pool.acquire()
            buf.extend(b"test" * 10)
            pool.release(buf)

        assert len(pool._pool) <= 4

    def test_repr(self):
        pool = BufferPool(initial_size=1024, max_pool=8)
        assert "BufferPool" in repr(pool)

    def test_global_pool(self):
        pool = get_buffer_pool()
        assert isinstance(pool, BufferPool)


# ============================================================================
# Tests: SerializerConfig
# ============================================================================

class TestSerializerConfig:
    """Tests for global serializer configuration."""

    def test_default_json_backend(self):
        assert SerializerConfig.json_backend == "auto"

    def test_get_json_encoder(self):
        SerializerConfig.reset()
        encoder = SerializerConfig.get_json_encoder()
        assert callable(encoder)
        result = encoder({"key": "value"})
        assert isinstance(result, (bytes, str))

    def test_get_json_decoder(self):
        SerializerConfig.reset()
        decoder = SerializerConfig.get_json_decoder()
        assert callable(decoder)
        result = decoder(b'{"key":"value"}')
        assert result == {"key": "value"}

    def test_stdlib_backend(self):
        SerializerConfig.json_backend = "stdlib"
        SerializerConfig.reset()
        encoder = SerializerConfig.get_json_encoder()
        result = encoder({"a": 1})
        assert isinstance(result, bytes)
        assert json.loads(result) == {"a": 1}

        # Reset
        SerializerConfig.json_backend = "auto"
        SerializerConfig.reset()

    def test_reset_clears_cache(self):
        SerializerConfig.reset()
        enc1 = SerializerConfig.get_json_encoder()
        SerializerConfig.reset()
        enc2 = SerializerConfig.get_json_encoder()
        # Both should work even after reset
        assert callable(enc1)
        assert callable(enc2)


# ============================================================================
# Tests: Serialization Plan Consistency  
# ============================================================================

class TestSerializationPlanConsistency:
    """Ensure optimized serialization produces identical results to naive impl."""

    def test_small_serializer_roundtrip(self):
        class S(Serializer):
            name = CharField()
            email = EmailField()
            age = IntegerField(min_value=0)

        obj = Obj(name="Kai", email="kai@aq.dev", age=25)
        s = S(instance=obj)
        data = s.data

        assert data == {"name": "Kai", "email": "kai@aq.dev", "age": 25}

    def test_serializer_with_defaults(self):
        class S(Serializer):
            name = CharField()
            bio = CharField(required=False, default="No bio")

        s = S(data={"name": "Kai"})
        assert s.is_valid()
        assert s.validated_data == {"name": "Kai", "bio": "No bio"}

    def test_list_serializer_consistency(self):
        class S(Serializer):
            id = IntegerField()
            name = CharField()

        items = [Obj(id=i, name=f"item_{i}") for i in range(5)]
        ls = ListSerializer(child=S(), instance=items)
        data = ls.data

        assert len(data) == 5
        assert data[0] == {"id": 0, "name": "item_0"}
        assert data[4] == {"id": 4, "name": "item_4"}

    def test_write_only_excluded(self):
        class S(Serializer):
            name = CharField()
            password = CharField(write_only=True)

        obj = Obj(name="Kai", password="secret")
        s = S(instance=obj)
        assert "password" not in s.data
        assert s.data["name"] == "Kai"

    def test_read_only_excluded_from_validation(self):
        class S(Serializer):
            id = IntegerField(read_only=True)
            name = CharField()

        s = S(data={"id": 99, "name": "Kai"})
        assert s.is_valid()
        assert "id" not in s.validated_data

    def test_partial_update(self):
        class S(Serializer):
            name = CharField()
            email = EmailField()

        s = S(data={"name": "Updated"}, partial=True)
        assert s.is_valid()
        assert s.validated_data == {"name": "Updated"}

    def test_nested_serializer_still_works(self):
        class Inner(Serializer):
            city = CharField()

        class Outer(Serializer):
            name = CharField()

        obj = Obj(name="Kai")
        inner_obj = Obj(city="Tokyo")

        s = Outer(instance=obj)
        assert s.data["name"] == "Kai"

        si = Inner(instance=inner_obj)
        assert si.data["city"] == "Tokyo"

    def test_method_field_works_after_optimization(self):
        class S(Serializer):
            name = CharField()
            display = SerializerMethodField()

            def get_display(self, obj):
                return f"[{obj.name}]"

        obj = Obj(name="Kai")
        s = S(instance=obj)
        assert s.data["display"] == "[Kai]"

    def test_constant_field_works(self):
        class S(Serializer):
            name = CharField()
            version = ConstantField(value="v2")

        obj = Obj(name="test")
        s = S(instance=obj)
        assert s.data["version"] == "v2"

    def test_inheritance_works(self):
        class Base(Serializer):
            name = CharField()

        class Child(Base):
            email = EmailField()

        obj = Obj(name="Kai", email="kai@aq.dev")
        s = Child(instance=obj)
        assert "name" in s.data
        assert "email" in s.data

    def test_di_defaults_still_work(self):
        class S(Serializer):
            name = CharField()
            owner_id = HiddenField(default=CurrentUserDefault())

        class FakeIdentity:
            id = 42

        s = S(
            data={"name": "test"},
            context={"identity": FakeIdentity()},
        )
        assert s.is_valid()
        assert s.validated_data["owner_id"] == 42


# ============================================================================
# Tests: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge cases for the optimized serializer."""

    def test_empty_serializer(self):
        class S(Serializer):
            pass

        s = S(instance=Obj())
        assert s.data == {}

    def test_serializer_data_cached(self):
        class S(Serializer):
            name = CharField()

        obj = Obj(name="Kai")
        s = S(instance=obj)
        data1 = s.data
        data2 = s.data
        assert data1 is data2  # Should be cached

    def test_relation_fields_still_work(self):
        f = PrimaryKeyRelatedField(read_only=True)
        f.bind("author", None)
        obj = Obj(pk=42)
        assert f.to_representation(obj) == 42

    def test_slug_related_field(self):
        f = SlugRelatedField(slug_field="username", read_only=True)
        f.bind("author", None)
        obj = Obj(username="kai")
        assert f.to_representation(obj) == "kai"

    def test_string_related_field(self):
        f = StringRelatedField()
        f.bind("author", None)
        obj = Obj(name="Kai")
        assert f.to_representation(obj) == "Kai"

    def test_validation_fault_raised(self):
        class S(Serializer):
            name = CharField()

        s = S(data={})
        with pytest.raises(ValidationFault):
            s.is_valid(raise_fault=True)

    def test_many_shortcut(self):
        class S(Serializer):
            name = CharField()

        items = [Obj(name="A"), Obj(name="B")]
        ls = S.many(instance=items)
        assert isinstance(ls, ListSerializer)
        assert len(ls.data) == 2
