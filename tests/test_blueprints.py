"""
Comprehensive test suite for the Aquilia Blueprint system.

Tests cover:
    - BlueprintMeta metaclass (facet collection, Spec parsing, derivation)
    - Facet types (cast, mold, seal for every facet type)
    - Projections (named subsets, default, exclusion, __all__)
    - Lenses (nested relations, depth control, cycle detection, PK fallback)
    - Validation pipeline (cast → field seal → cross-field seal → validate)
    - Async seals
    - Imprint operations (create, update, partial)
    - Schema generation
    - Integration utilities
    - Edge cases (partial, many, no model, inheritance)
"""

from __future__ import annotations

import uuid
import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers: Mock Model system ───────────────────────────────────────────

class MockField:
    """Minimal mock of aquilia.models.fields_module.Field."""
    _creation_counter = 0

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = False,
        max_length: int | None = None,
        help_text: str = "",
        editable: bool = True,
        auto_now: bool = False,
        auto_now_add: bool = False,
        default: Any = None,
        choices: list | None = None,
        max_digits: int | None = None,
        decimal_places: int | None = None,
        min_value: Any = None,
        max_value: Any = None,
    ):
        MockField._creation_counter += 1
        self._creation_counter = MockField._creation_counter
        self.primary_key = primary_key
        self.null = null
        self.blank = blank
        self.max_length = max_length
        self.help_text = help_text
        self.editable = editable
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.default = default
        self.choices = choices
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.min_value = min_value
        self.max_value = max_value

    def has_default(self) -> bool:
        return self.default is not None


class MockCharField(MockField):
    pass
class MockTextField(MockField):
    pass
class MockIntegerField(MockField):
    pass
class MockBigAutoField(MockField):
    pass
class MockBooleanField(MockField):
    pass
class MockDateTimeField(MockField):
    pass
class MockDecimalField(MockField):
    pass
class MockEmailField(MockField):
    pass
class MockFloatField(MockField):
    pass
class MockUUIDField(MockField):
    pass
class MockSlugField(MockField):
    pass
class MockJSONField(MockField):
    pass


class MockOptions:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockModel:
    """Minimal mock Model for testing."""
    _fields = {}
    _meta = MockOptions(table_name="mock_table")
    _table_name = "mock_table"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def save(self, update_fields=None):
        pass


def make_model(name: str, fields: Dict[str, MockField]) -> type:
    """Create a mock model class with given fields."""
    attrs = {
        "_fields": fields,
        "_meta": MockOptions(table_name=name.lower()),
        "_table_name": name.lower(),
        "__name__": name,
    }

    async def save(self, update_fields=None):
        pass

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    attrs["save"] = save
    attrs["__init__"] = __init__
    cls = type(name, (), attrs)
    return cls


# ── Imports ──────────────────────────────────────────────────────────────

from aquilia.blueprints import (
    Blueprint,
    BlueprintMeta,
    Facet,
    UNSET,
    TextFacet,
    IntFacet,
    FloatFacet,
    DecimalFacet,
    BoolFacet,
    DateFacet,
    TimeFacet,
    DateTimeFacet,
    DurationFacet,
    UUIDFacet,
    EmailFacet,
    URLFacet,
    SlugFacet,
    IPFacet,
    ListFacet,
    DictFacet,
    JSONFacet,
    FileFacet,
    ChoiceFacet,
    Computed,
    Constant,
    WriteOnly,
    ReadOnly,
    Hidden,
    Inject,
    Lens,
    ProjectionRegistry,
    BlueprintFault,
    CastFault,
    SealFault,
    ImprintFault,
    ProjectionFault,
    LensDepthFault,
    LensCycleFault,
    is_blueprint_class,
    is_projected_blueprint,
    resolve_blueprint_from_annotation,
    render_blueprint_response,
    generate_schema,
    generate_component_schemas,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. FACET TESTS — Cast, Mold, Seal for every Facet type
# ═══════════════════════════════════════════════════════════════════════

class TestTextFacet:
    def test_cast_string(self):
        f = TextFacet()
        f.bind("name", MagicMock())
        assert f.cast("hello") == "hello"

    def test_cast_strips_whitespace(self):
        f = TextFacet()
        f.bind("name", MagicMock())
        assert f.cast("  hello  ") == "hello"

    def test_cast_no_trim(self):
        f = TextFacet(trim=False)
        f.bind("name", MagicMock())
        assert f.cast("  hello  ") == "  hello  "

    def test_cast_non_string(self):
        f = TextFacet()
        f.bind("name", MagicMock())
        assert f.cast(42) == "42"

    def test_seal_min_length(self):
        f = TextFacet(min_length=3)
        f.bind("name", MagicMock())
        with pytest.raises(CastFault):
            f.seal("ab")

    def test_seal_max_length(self):
        f = TextFacet(max_length=5)
        f.bind("name", MagicMock())
        with pytest.raises(CastFault):
            f.seal("toolong")

    def test_seal_valid_length(self):
        f = TextFacet(min_length=2, max_length=10)
        f.bind("name", MagicMock())
        assert f.seal("hello") == "hello"

    def test_seal_blank_not_allowed(self):
        f = TextFacet()
        f.bind("name", MagicMock())
        with pytest.raises(CastFault):
            f.seal("")

    def test_seal_blank_allowed(self):
        f = TextFacet(allow_blank=True)
        f.bind("name", MagicMock())
        assert f.seal("") == ""

    def test_seal_pattern(self):
        f = TextFacet(pattern=r"^\d{3}-\d{4}$")
        f.bind("phone", MagicMock())
        assert f.seal("123-4567") == "123-4567"
        with pytest.raises(CastFault):
            f.seal("abc")

    def test_schema(self):
        f = TextFacet(max_length=100, label="Name", help_text="Your name")
        schema = f.to_schema()
        assert schema["type"] == "string"
        assert schema["maxLength"] == 100
        assert schema["title"] == "Name"
        assert schema["description"] == "Your name"


class TestEmailFacet:
    def test_cast_lowercase(self):
        f = EmailFacet()
        f.bind("email", MagicMock())
        assert f.cast("TEST@EXAMPLE.COM") == "test@example.com"

    def test_seal_valid(self):
        f = EmailFacet()
        f.bind("email", MagicMock())
        assert f.seal("user@example.com") == "user@example.com"

    def test_seal_invalid(self):
        f = EmailFacet()
        f.bind("email", MagicMock())
        with pytest.raises(CastFault):
            f.seal("not-an-email")

    def test_schema_format(self):
        f = EmailFacet()
        assert f.to_schema()["format"] == "email"


class TestURLFacet:
    def test_seal_valid(self):
        f = URLFacet()
        f.bind("url", MagicMock())
        assert f.seal("https://example.com") == "https://example.com"

    def test_seal_invalid(self):
        f = URLFacet()
        f.bind("url", MagicMock())
        with pytest.raises(CastFault):
            f.seal("not-a-url")


class TestSlugFacet:
    def test_cast_lowercase(self):
        f = SlugFacet()
        f.bind("slug", MagicMock())
        assert f.cast("My-Slug") == "my-slug"

    def test_seal_valid(self):
        f = SlugFacet()
        f.bind("slug", MagicMock())
        assert f.seal("my-slug-123") == "my-slug-123"

    def test_seal_invalid(self):
        f = SlugFacet()
        f.bind("slug", MagicMock())
        with pytest.raises(CastFault):
            f.seal("invalid slug!")


class TestIPFacet:
    def test_seal_valid_ipv4(self):
        f = IPFacet()
        f.bind("ip", MagicMock())
        assert f.seal("192.168.1.1") == "192.168.1.1"

    def test_seal_valid_ipv6(self):
        f = IPFacet()
        f.bind("ip", MagicMock())
        assert f.seal("::1") == "::1"

    def test_seal_invalid(self):
        f = IPFacet()
        f.bind("ip", MagicMock())
        with pytest.raises(CastFault):
            f.seal("999.999.999.999")


class TestIntFacet:
    def test_cast_string(self):
        f = IntFacet()
        f.bind("age", MagicMock())
        assert f.cast("42") == 42

    def test_cast_bool_rejected(self):
        f = IntFacet()
        f.bind("age", MagicMock())
        with pytest.raises(CastFault):
            f.cast(True)

    def test_cast_invalid(self):
        f = IntFacet()
        f.bind("age", MagicMock())
        with pytest.raises(CastFault):
            f.cast("abc")

    def test_seal_range(self):
        f = IntFacet(min_value=0, max_value=100)
        f.bind("age", MagicMock())
        assert f.seal(50) == 50
        with pytest.raises(CastFault):
            f.seal(-1)
        with pytest.raises(CastFault):
            f.seal(101)

    def test_schema(self):
        f = IntFacet(min_value=0, max_value=100)
        schema = f.to_schema()
        assert schema["type"] == "integer"
        assert schema["minimum"] == 0
        assert schema["maximum"] == 100


class TestFloatFacet:
    def test_cast(self):
        f = FloatFacet()
        f.bind("price", MagicMock())
        assert f.cast("3.14") == pytest.approx(3.14)

    def test_seal_range(self):
        f = FloatFacet(min_value=0.0)
        f.bind("price", MagicMock())
        with pytest.raises(CastFault):
            f.seal(-0.01)


class TestDecimalFacet:
    def test_cast(self):
        f = DecimalFacet()
        f.bind("price", MagicMock())
        result = f.cast("9.99")
        assert result == Decimal("9.99")

    def test_cast_from_float(self):
        f = DecimalFacet()
        f.bind("price", MagicMock())
        result = f.cast(9.99)
        assert isinstance(result, Decimal)

    def test_seal_digits(self):
        f = DecimalFacet(max_digits=5, decimal_places=2)
        f.bind("price", MagicMock())
        assert f.seal(Decimal("999.99")) == Decimal("999.99")
        with pytest.raises(CastFault):
            f.seal(Decimal("9.999"))  # too many decimal places

    def test_mold_to_string(self):
        f = DecimalFacet()
        assert f.mold(Decimal("9.99")) == "9.99"
        assert f.mold(None) is None


class TestBoolFacet:
    def test_cast_true_values(self):
        f = BoolFacet()
        f.bind("active", MagicMock())
        assert f.cast(True) is True
        assert f.cast("true") is True
        assert f.cast("1") is True
        assert f.cast("yes") is True
        assert f.cast(1) is True

    def test_cast_false_values(self):
        f = BoolFacet()
        f.bind("active", MagicMock())
        assert f.cast(False) is False
        assert f.cast("false") is False
        assert f.cast("0") is False
        assert f.cast("no") is False
        assert f.cast(0) is False

    def test_cast_invalid(self):
        f = BoolFacet()
        f.bind("active", MagicMock())
        with pytest.raises(CastFault):
            f.cast([])


class TestDateFacet:
    def test_cast_iso(self):
        f = DateFacet()
        f.bind("d", MagicMock())
        assert f.cast("2024-01-15") == date(2024, 1, 15)

    def test_cast_datetime(self):
        f = DateFacet()
        f.bind("d", MagicMock())
        assert f.cast(datetime(2024, 1, 15, 10, 30)) == date(2024, 1, 15)

    def test_cast_invalid(self):
        f = DateFacet()
        f.bind("d", MagicMock())
        with pytest.raises(CastFault):
            f.cast("not-a-date")

    def test_mold(self):
        f = DateFacet()
        assert f.mold(date(2024, 1, 15)) == "2024-01-15"
        assert f.mold(None) is None


class TestTimeFacet:
    def test_cast_iso(self):
        f = TimeFacet()
        f.bind("t", MagicMock())
        assert f.cast("14:30:00") == time(14, 30, 0)

    def test_mold(self):
        f = TimeFacet()
        assert f.mold(time(14, 30, 0)) == "14:30:00"


class TestDateTimeFacet:
    def test_cast_iso(self):
        f = DateTimeFacet()
        f.bind("dt", MagicMock())
        result = f.cast("2024-01-15T14:30:00")
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_mold(self):
        f = DateTimeFacet()
        result = f.mold(datetime(2024, 1, 15, 14, 30))
        assert "2024-01-15" in result


class TestDurationFacet:
    def test_cast_seconds(self):
        f = DurationFacet()
        f.bind("dur", MagicMock())
        assert f.cast(3600) == timedelta(hours=1)

    def test_cast_hms(self):
        f = DurationFacet()
        f.bind("dur", MagicMock())
        assert f.cast("1:30:00") == timedelta(hours=1, minutes=30)

    def test_mold(self):
        f = DurationFacet()
        assert f.mold(timedelta(hours=1)) == 3600.0


class TestUUIDFacet:
    def test_cast(self):
        f = UUIDFacet()
        f.bind("uid", MagicMock())
        val = "12345678-1234-5678-1234-567812345678"
        result = f.cast(val)
        assert isinstance(result, uuid.UUID)
        assert str(result) == val

    def test_cast_invalid(self):
        f = UUIDFacet()
        f.bind("uid", MagicMock())
        with pytest.raises(CastFault):
            f.cast("not-a-uuid")

    def test_mold(self):
        f = UUIDFacet()
        uid = uuid.uuid4()
        assert f.mold(uid) == str(uid)


class TestListFacet:
    def test_cast(self):
        f = ListFacet()
        f.bind("tags", MagicMock())
        assert f.cast(["a", "b"]) == ["a", "b"]

    def test_cast_with_child(self):
        child = IntFacet()
        child.bind("item", MagicMock())
        f = ListFacet(child=child)
        f.bind("ids", MagicMock())
        assert f.cast(["1", "2", "3"]) == [1, 2, 3]

    def test_cast_not_list(self):
        f = ListFacet()
        f.bind("tags", MagicMock())
        with pytest.raises(CastFault):
            f.cast("not a list")

    def test_seal_item_count(self):
        f = ListFacet(min_items=1, max_items=3)
        f.bind("tags", MagicMock())
        assert f.seal(["a", "b"]) == ["a", "b"]
        with pytest.raises(CastFault):
            f.seal([])
        with pytest.raises(CastFault):
            f.seal(["a", "b", "c", "d"])


class TestDictFacet:
    def test_cast(self):
        f = DictFacet()
        f.bind("meta", MagicMock())
        assert f.cast({"key": "value"}) == {"key": "value"}

    def test_cast_not_dict(self):
        f = DictFacet()
        f.bind("meta", MagicMock())
        with pytest.raises(CastFault):
            f.cast("not a dict")


class TestChoiceFacet:
    def test_seal_valid(self):
        f = ChoiceFacet(choices=["red", "green", "blue"])
        f.bind("color", MagicMock())
        assert f.seal("red") == "red"

    def test_seal_invalid(self):
        f = ChoiceFacet(choices=["red", "green", "blue"])
        f.bind("color", MagicMock())
        with pytest.raises(CastFault):
            f.seal("purple")

    def test_tuple_choices(self):
        f = ChoiceFacet(choices=[("A", "Active"), ("I", "Inactive")])
        f.bind("status", MagicMock())
        assert f.seal("A") == "A"
        with pytest.raises(CastFault):
            f.seal("Active")


class TestSpecialFacets:
    def test_computed_lambda(self):
        f = Computed(lambda obj: f"{obj.first} {obj.last}")
        f.bind("full_name", MagicMock())
        obj = MagicMock()
        obj.first = "John"
        obj.last = "Doe"
        assert f.extract(obj) == "John Doe"
        assert f.read_only is True

    def test_computed_method_name(self):
        class MyBP:
            def get_total(self, obj):
                return obj.price * obj.qty

        f = Computed("get_total")
        bp = MyBP()
        f.bind("total", bp)
        obj = MagicMock()
        obj.price = 10
        obj.qty = 3
        assert f.extract(obj) == 30

    def test_constant(self):
        f = Constant("v2")
        f.bind("version", MagicMock())
        assert f.extract(None) == "v2"
        assert f.mold(None) == "v2"
        assert f.read_only is True

    def test_write_only(self):
        f = WriteOnly(min_length=8)
        f.bind("password", MagicMock())
        assert f.write_only is True
        assert f.seal("password123") == "password123"
        with pytest.raises(CastFault):
            f.seal("short")

    def test_read_only_auto_serialize(self):
        f = ReadOnly()
        f.bind("created_at", MagicMock())
        assert f.read_only is True
        dt = datetime(2024, 1, 15, 10, 30)
        assert f.mold(dt) == "2024-01-15T10:30:00"
        uid = uuid.uuid4()
        assert f.mold(uid) == str(uid)
        assert f.mold(Decimal("9.99")) == "9.99"

    def test_hidden(self):
        f = Hidden(default=42)
        f.bind("audit_id", MagicMock())
        assert f.write_only is True
        assert f.default == 42


class TestFacetBase:
    def test_required_default(self):
        f = Facet()
        assert f.required is True

    def test_required_with_default(self):
        f = Facet(default=42)
        assert f.required is False

    def test_required_read_only(self):
        f = Facet(read_only=True)
        assert f.required is False

    def test_required_allow_null(self):
        f = Facet(allow_null=True)
        assert f.required is False

    def test_required_explicit(self):
        f = Facet(required=False)
        assert f.required is False

    def test_clone(self):
        f = TextFacet(max_length=100, label="Name")
        f.bind("name", MagicMock())
        c = f.clone()
        assert c.max_length == 100
        assert c.label == "Name"
        assert c._bound is False
        assert c.name is None

    def test_extract_simple(self):
        f = Facet(source="name")
        f.bind("name", MagicMock())
        obj = MagicMock()
        obj.name = "test"
        assert f.extract(obj) == "test"

    def test_extract_dotted(self):
        f = Facet(source="category.name")
        f.bind("cat_name", MagicMock())
        obj = MagicMock()
        obj.category = MagicMock()
        obj.category.name = "Electronics"
        assert f.extract(obj) == "Electronics"

    def test_extract_dict(self):
        f = Facet(source="name")
        f.bind("name", MagicMock())
        assert f.extract({"name": "test"}) == "test"

    def test_extract_star(self):
        f = Facet(source="*")
        f.bind("self", MagicMock())
        obj = MagicMock()
        assert f.extract(obj) is obj

    def test_validators(self):
        def no_spaces(value):
            if " " in value:
                raise ValueError("No spaces allowed")

        f = TextFacet(validators=[no_spaces])
        f.bind("slug", MagicMock())
        assert f.seal("hello") == "hello"
        with pytest.raises(CastFault):
            f.seal("hello world")


# ═══════════════════════════════════════════════════════════════════════
# 2. BLUEPRINT TESTS — Core Blueprint functionality
# ═══════════════════════════════════════════════════════════════════════

class TestBlueprintMeta:
    def test_declared_facets_collected(self):
        class TestBP(Blueprint):
            name = TextFacet(max_length=100)
            age = IntFacet(min_value=0)

        assert "name" in TestBP._all_facets
        assert "age" in TestBP._all_facets
        assert isinstance(TestBP._all_facets["name"], TextFacet)
        assert isinstance(TestBP._all_facets["age"], IntFacet)

    def test_inherited_facets(self):
        class BaseBP(Blueprint):
            name = TextFacet()

        class ChildBP(BaseBP):
            age = IntFacet()

        assert "name" in ChildBP._all_facets
        assert "age" in ChildBP._all_facets

    def test_child_overrides_parent(self):
        class BaseBP(Blueprint):
            name = TextFacet(max_length=50)

        class ChildBP(BaseBP):
            name = TextFacet(max_length=200)

        assert ChildBP._all_facets["name"].max_length == 200

    def test_spec_parsing(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "price": MockFloatField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product

        assert ProductBP._spec.model is Product
        assert "id" in ProductBP._all_facets
        assert "name" in ProductBP._all_facets
        assert "price" in ProductBP._all_facets

    def test_spec_fields_filter(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "price": MockFloatField(),
            "internal": MockTextField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product
                fields = ["id", "name", "price"]

        assert "internal" not in ProductBP._all_facets

    def test_spec_exclude(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "internal": MockTextField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product
                exclude = ["internal"]

        assert "internal" not in ProductBP._all_facets
        assert "name" in ProductBP._all_facets

    def test_spec_read_only_fields(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "created_at": MockDateTimeField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product
                read_only_fields = ["created_at"]

        assert ProductBP._all_facets["created_at"].read_only is True

    def test_subscript_syntax(self):
        class TestBP(Blueprint):
            name = TextFacet()

            class Spec:
                projections = {"summary": ["name"]}

        ref = TestBP["summary"]
        assert is_projected_blueprint(ref)
        assert ref.blueprint_cls is TestBP
        assert ref.projection == "summary"

    def test_seal_method_discovery(self):
        class TestBP(Blueprint):
            name = TextFacet()

            def seal_name_valid(self, data):
                pass

            async def async_seal_unique(self, data):
                pass

        assert "seal_name_valid" in TestBP._seal_methods
        assert "async_seal_unique" in TestBP._async_seal_methods


# ═══════════════════════════════════════════════════════════════════════
# 3. PROJECTION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestProjections:
    def test_default_all_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        assert "__all__" in TestBP._projections.available

    def test_named_projections(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()
            bio = TextFacet()

            class Spec:
                projections = {
                    "summary": ["name"],
                    "detail": ["name", "age", "bio"],
                }

        fields = TestBP._projections.resolve("summary")
        assert fields == frozenset(["name"])
        fields = TestBP._projections.resolve("detail")
        assert fields == frozenset(["name", "age", "bio"])

    def test_all_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

            class Spec:
                projections = {"full": "__all__"}

        fields = TestBP._projections.resolve("full")
        assert "name" in fields
        assert "age" in fields

    def test_exclusion_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()
            secret = TextFacet()

            class Spec:
                projections = {
                    "public": ["-secret"],
                }

        fields = TestBP._projections.resolve("public")
        assert "name" in fields
        assert "age" in fields
        assert "secret" not in fields

    def test_invalid_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()

            class Spec:
                projections = {"summary": ["name"]}

        with pytest.raises(ProjectionFault):
            TestBP._projections.resolve("nonexistent")

    def test_default_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

            class Spec:
                projections = {
                    "summary": ["name"],
                    "detail": ["name", "age"],
                }
                default_projection = "detail"

        assert TestBP._projections.default_name == "detail"

    def test_write_only_excluded_from_projections(self):
        class TestBP(Blueprint):
            name = TextFacet()
            password = WriteOnly()

            class Spec:
                projections = {"full": "__all__"}

        fields = TestBP._projections.resolve("full")
        assert "password" not in fields

    def test_projection_in_output(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()
            bio = TextFacet()

            class Spec:
                projections = {
                    "summary": ["name"],
                    "detail": ["name", "age", "bio"],
                }

        obj = MagicMock()
        obj.name = "Alice"
        obj.age = 30
        obj.bio = "Hello"

        bp = TestBP(instance=obj, projection="summary")
        data = bp.data
        assert "name" in data
        assert "age" not in data
        assert "bio" not in data


# ═══════════════════════════════════════════════════════════════════════
# 4. VALIDATION PIPELINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestValidationPipeline:
    def test_basic_validation(self):
        class TestBP(Blueprint):
            name = TextFacet(max_length=50)
            age = IntFacet(min_value=0)

        bp = TestBP(data={"name": "Alice", "age": 25})
        assert bp.is_sealed() is True
        assert bp.validated_data == {"name": "Alice", "age": 25}

    def test_cast_failure(self):
        class TestBP(Blueprint):
            age = IntFacet()

        bp = TestBP(data={"age": "not-a-number"})
        assert bp.is_sealed() is False
        assert "age" in bp.errors

    def test_seal_failure(self):
        class TestBP(Blueprint):
            age = IntFacet(min_value=0)

        bp = TestBP(data={"age": -5})
        assert bp.is_sealed() is False
        assert "age" in bp.errors

    def test_required_field_missing(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is False
        assert "age" in bp.errors

    def test_optional_field(self):
        class TestBP(Blueprint):
            name = TextFacet()
            bio = TextFacet(required=False)

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is True
        assert "bio" not in bp.validated_data

    def test_default_value(self):
        class TestBP(Blueprint):
            name = TextFacet()
            role = TextFacet(default="user")

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is True
        assert bp.validated_data["role"] == "user"

    def test_callable_default(self):
        class TestBP(Blueprint):
            name = TextFacet()
            uid = UUIDFacet(default=uuid.uuid4)

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is True
        assert isinstance(bp.validated_data["uid"], uuid.UUID)

    def test_null_handling(self):
        class TestBP(Blueprint):
            name = TextFacet()
            bio = TextFacet(allow_null=True)

        bp = TestBP(data={"name": "Alice", "bio": None})
        assert bp.is_sealed() is True
        assert bp.validated_data["bio"] is None

    def test_null_rejected(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": None})
        assert bp.is_sealed() is False
        assert "name" in bp.errors

    def test_read_only_ignored(self):
        class TestBP(Blueprint):
            id = IntFacet(read_only=True)
            name = TextFacet()

        bp = TestBP(data={"id": 999, "name": "Alice"})
        assert bp.is_sealed() is True
        assert "id" not in bp.validated_data

    def test_cross_field_seal(self):
        class TestBP(Blueprint):
            password = TextFacet()
            password_confirm = TextFacet()

            def seal_passwords_match(self, data):
                if data.get("password") != data.get("password_confirm"):
                    self.reject("password_confirm", "Passwords do not match")

        bp = TestBP(data={"password": "abc123", "password_confirm": "abc123"})
        assert bp.is_sealed() is True

        bp = TestBP(data={"password": "abc123", "password_confirm": "xyz"})
        assert bp.is_sealed() is False
        assert "password_confirm" in bp.errors

    def test_validate_hook(self):
        class TestBP(Blueprint):
            age = IntFacet()

            def validate(self, data):
                if data.get("age", 0) < 13:
                    self.reject("age", "Must be at least 13")
                return data

        bp = TestBP(data={"age": 10})
        assert bp.is_sealed() is False
        assert "age" in bp.errors

        bp = TestBP(data={"age": 18})
        assert bp.is_sealed() is True

    def test_validate_transforms_data(self):
        class TestBP(Blueprint):
            name = TextFacet()

            def validate(self, data):
                data["name"] = data["name"].upper()
                return data

        bp = TestBP(data={"name": "alice"})
        assert bp.is_sealed() is True
        assert bp.validated_data["name"] == "ALICE"

    def test_raise_fault(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={})
        with pytest.raises(SealFault) as exc_info:
            bp.is_sealed(raise_fault=True)
        assert "name" in exc_info.value.field_errors

    def test_no_data_provided(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP()
        assert bp.is_sealed() is False
        assert "__all__" in bp.errors

    def test_partial_mode(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        bp = TestBP(data={"name": "Alice"}, partial=True)
        assert bp.is_sealed() is True
        assert "age" not in bp.validated_data

    def test_many_mode(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        bp = TestBP(
            data=[
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30},
            ],
            many=True,
        )
        assert bp.is_sealed() is True
        assert len(bp.validated_data) == 2
        assert bp.validated_data[0]["name"] == "Alice"
        assert bp.validated_data[1]["name"] == "Bob"

    def test_many_mode_validation_error(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet(min_value=0)

        bp = TestBP(
            data=[
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": -1},
            ],
            many=True,
        )
        assert bp.is_sealed() is False
        assert "1" in bp.errors  # Second item failed

    def test_many_not_list(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "not a list"}, many=True)
        assert bp.is_sealed() is False


class TestAsyncValidation:
    @pytest.mark.asyncio
    async def test_async_seal(self):
        class TestBP(Blueprint):
            email = EmailFacet()

            async def async_seal_unique_email(self, data):
                # Simulate async DB check
                if data.get("email") == "taken@example.com":
                    self.reject("email", "Already registered")

        bp = TestBP(data={"email": "new@example.com"})
        result = await bp.is_sealed_async()
        assert result is True

        bp = TestBP(data={"email": "taken@example.com"})
        result = await bp.is_sealed_async()
        assert result is False
        assert "email" in bp.errors


# ═══════════════════════════════════════════════════════════════════════
# 5. OUTPUT (MOLD) TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestMoldOutput:
    def test_basic_output(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        obj = MagicMock()
        obj.name = "Alice"
        obj.age = 30

        bp = TestBP(instance=obj)
        data = bp.data
        assert data == {"name": "Alice", "age": 30}

    def test_computed_in_output(self):
        class TestBP(Blueprint):
            first = TextFacet()
            last = TextFacet()
            full = Computed(lambda obj: f"{obj.first} {obj.last}")

        obj = MagicMock()
        obj.first = "John"
        obj.last = "Doe"

        bp = TestBP(instance=obj)
        data = bp.data
        assert data["full"] == "John Doe"

    def test_constant_in_output(self):
        class TestBP(Blueprint):
            name = TextFacet()
            version = Constant("v2")

        obj = MagicMock()
        obj.name = "test"

        bp = TestBP(instance=obj)
        data = bp.data
        assert data["version"] == "v2"

    def test_write_only_excluded(self):
        class TestBP(Blueprint):
            name = TextFacet()
            password = WriteOnly()

        obj = MagicMock()
        obj.name = "Alice"
        obj.password = "secret"

        bp = TestBP(instance=obj)
        data = bp.data
        assert "name" in data
        assert "password" not in data

    def test_many_output(self):
        class TestBP(Blueprint):
            name = TextFacet()

        obj1 = MagicMock()
        obj1.name = "Alice"
        obj2 = MagicMock()
        obj2.name = "Bob"

        bp = TestBP(instance=[obj1, obj2], many=True)
        data = bp.data
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[1]["name"] == "Bob"

    def test_datetime_molding(self):
        class TestBP(Blueprint):
            created = DateTimeFacet()

        obj = MagicMock()
        obj.created = datetime(2024, 1, 15, 10, 30)

        bp = TestBP(instance=obj)
        data = bp.data
        assert "2024-01-15" in data["created"]

    def test_none_nullable_in_output(self):
        class TestBP(Blueprint):
            name = TextFacet()
            bio = TextFacet(allow_null=True)

        obj = MagicMock()
        obj.name = "Alice"
        obj.bio = None

        bp = TestBP(instance=obj)
        data = bp.data
        assert data["bio"] is None

    def test_source_override(self):
        class TestBP(Blueprint):
            display = TextFacet(source="internal_name")

        obj = MagicMock()
        obj.internal_name = "secret_name"

        bp = TestBP(instance=obj)
        data = bp.data
        assert data["display"] == "secret_name"


# ═══════════════════════════════════════════════════════════════════════
# 6. LENS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestLens:
    def test_basic_lens(self):
        class AuthorBP(Blueprint):
            name = TextFacet()

        class BookBP(Blueprint):
            title = TextFacet()
            author = Lens(AuthorBP)

        author = MagicMock()
        author.name = "Tolkien"

        book = MagicMock()
        book.title = "The Hobbit"
        book.author = author

        bp = BookBP(instance=book)
        data = bp.data
        assert data["title"] == "The Hobbit"
        assert data["author"] == {"name": "Tolkien"}

    def test_lens_many(self):
        class TagBP(Blueprint):
            name = TextFacet()

        class PostBP(Blueprint):
            title = TextFacet()
            tags = Lens(TagBP, many=True)

        tag1 = MagicMock()
        tag1.name = "python"
        tag2 = MagicMock()
        tag2.name = "web"

        post = MagicMock()
        post.title = "Hello"
        post.tags = [tag1, tag2]

        bp = PostBP(instance=post)
        data = bp.data
        assert len(data["tags"]) == 2
        assert data["tags"][0]["name"] == "python"

    def test_lens_with_projection(self):
        class UserBP(Blueprint):
            name = TextFacet()
            email = EmailFacet()
            bio = TextFacet()

            class Spec:
                projections = {
                    "public": ["name"],
                    "full": "__all__",
                }

        class PostBP(Blueprint):
            title = TextFacet()
            author = Lens(UserBP["public"])

        author = MagicMock()
        author.name = "Alice"
        author.email = "alice@test.com"
        author.bio = "Developer"

        post = MagicMock()
        post.title = "Hello"
        post.author = author

        bp = PostBP(instance=post)
        data = bp.data
        assert data["author"] == {"name": "Alice"}
        assert "email" not in data["author"]

    def test_lens_depth_limit(self):
        class InnerBP(Blueprint):
            name = TextFacet()

        class SelfRefBP(Blueprint):
            name = TextFacet()
            parent = Lens(InnerBP, depth=1)

        grandparent = MagicMock()
        grandparent.name = "G"
        grandparent.pk = 1
        grandparent.parent = None

        parent = MagicMock()
        parent.name = "P"
        parent.pk = 2
        parent.parent = grandparent

        child = MagicMock()
        child.name = "C"
        child.parent = parent

        bp = SelfRefBP(instance=child)
        data = bp.to_dict()
        # At depth 0: child → full render with Lens
        # Lens depth=1: parent gets full render at depth 1
        # No deeper nesting since InnerBP has no Lens
        assert data["name"] == "C"
        assert data["parent"]["name"] == "P"

    def test_lens_none(self):
        class AuthorBP(Blueprint):
            name = TextFacet()

        class BookBP(Blueprint):
            title = TextFacet()
            author = Lens(AuthorBP, allow_null=True)

        book = MagicMock()
        book.title = "Orphan"
        book.author = None

        bp = BookBP(instance=book)
        data = bp.data
        assert data["author"] is None

    def test_lens_pk_fallback(self):
        result = Lens._pk_fallback(MagicMock(pk=42))
        assert result == 42

        result = Lens._pk_fallback({"id": 7})
        assert result == 7

        assert Lens._pk_fallback(None) is None

    def test_lens_read_only_default(self):
        class TargetBP(Blueprint):
            name = TextFacet()

        lens = Lens(TargetBP)
        assert lens.read_only is True


# ═══════════════════════════════════════════════════════════════════════
# 7. IMPRINT TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestImprint:
    @pytest.mark.asyncio
    async def test_imprint_create(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "price": MockFloatField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product

        bp = ProductBP(data={"name": "Widget", "price": 9.99})
        assert bp.is_sealed()

        product = await bp.imprint()
        assert product.name == "Widget"
        assert product.price == pytest.approx(9.99)

    @pytest.mark.asyncio
    async def test_imprint_update(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "price": MockFloatField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product

        existing = Product()
        existing.id = 1
        existing.name = "Old"
        existing.price = 5.00

        bp = ProductBP(data={"name": "New", "price": 9.99})
        assert bp.is_sealed()

        updated = await bp.imprint(existing)
        assert updated.name == "New"
        assert updated.price == pytest.approx(9.99)

    @pytest.mark.asyncio
    async def test_imprint_partial(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
            "price": MockFloatField(),
        })

        class ProductBP(Blueprint):
            class Spec:
                model = Product

        existing = Product()
        existing.id = 1
        existing.name = "Old"
        existing.price = 5.00

        bp = ProductBP(data={"price": 12.99}, partial=True)
        assert bp.is_sealed()

        updated = await bp.imprint(existing)
        assert updated.name == "Old"  # unchanged
        assert updated.price == pytest.approx(12.99)

    @pytest.mark.asyncio
    async def test_imprint_without_seal(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "test"})
        # Don't call is_sealed()
        with pytest.raises(ImprintFault):
            await bp.imprint()

    @pytest.mark.asyncio
    async def test_imprint_filters_computed(self):
        Product = make_model("Product", {
            "id": MockBigAutoField(primary_key=True),
            "name": MockCharField(max_length=200),
        })

        class ProductBP(Blueprint):
            display_name = Computed(lambda p: p.name.upper())

            class Spec:
                model = Product

        bp = ProductBP(data={"name": "Widget"})
        assert bp.is_sealed()
        product = await bp.imprint()
        assert product.name == "Widget"
        assert not hasattr(product, "display_name")


# ═══════════════════════════════════════════════════════════════════════
# 8. SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSchema:
    def test_basic_schema(self):
        class TestBP(Blueprint):
            name = TextFacet(max_length=100)
            age = IntFacet(min_value=0)

        schema = TestBP.to_schema()
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

    def test_input_schema(self):
        class TestBP(Blueprint):
            id = IntFacet(read_only=True)
            name = TextFacet()

        schema = TestBP.to_schema(mode="input")
        assert "id" not in schema["properties"]
        assert "name" in schema["properties"]
        assert "name" in schema.get("required", [])

    def test_output_schema(self):
        class TestBP(Blueprint):
            name = TextFacet()
            password = WriteOnly()

        schema = TestBP.to_schema(mode="output")
        assert "password" not in schema["properties"]
        assert "name" in schema["properties"]

    def test_projection_schema(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()
            bio = TextFacet()

            class Spec:
                projections = {"summary": ["name", "age"]}

        schema = TestBP.to_schema(projection="summary")
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "bio" not in schema["properties"]

    def test_generate_component_schemas(self):
        class UserBP(Blueprint):
            name = TextFacet()

            class Spec:
                projections = {"public": ["name"]}

        schemas = generate_component_schemas(UserBP)
        assert "UserBP" in schemas
        assert "UserBP_Input" in schemas
        assert "UserBP_public" in schemas

    def test_constant_in_schema(self):
        class TestBP(Blueprint):
            version = Constant("v2")

        schema = TestBP.to_schema()
        assert schema["properties"]["version"]["const"] == "v2"

    def test_choice_in_schema(self):
        class TestBP(Blueprint):
            color = ChoiceFacet(choices=["red", "green", "blue"])

        schema = TestBP.to_schema()
        assert "enum" in schema["properties"]["color"]

    def test_lens_in_schema(self):
        class AuthorBP(Blueprint):
            name = TextFacet()

        class BookBP(Blueprint):
            title = TextFacet()
            author = Lens(AuthorBP)

        schema = BookBP.to_schema()
        assert "$ref" in schema["properties"]["author"]

    def test_lens_many_in_schema(self):
        class TagBP(Blueprint):
            name = TextFacet()

        class PostBP(Blueprint):
            title = TextFacet()
            tags = Lens(TagBP, many=True)

        schema = PostBP.to_schema()
        assert schema["properties"]["tags"]["type"] == "array"
        assert "$ref" in schema["properties"]["tags"]["items"]


# ═══════════════════════════════════════════════════════════════════════
# 9. INTEGRATION UTILITY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestIntegrationUtils:
    def test_is_blueprint_class(self):
        class TestBP(Blueprint):
            name = TextFacet()

        assert is_blueprint_class(TestBP) is True
        assert is_blueprint_class(Blueprint) is False
        assert is_blueprint_class("not a class") is False
        assert is_blueprint_class(TestBP(instance=None)) is False

    def test_is_projected_blueprint(self):
        class TestBP(Blueprint):
            name = TextFacet()

            class Spec:
                projections = {"summary": ["name"]}

        assert is_projected_blueprint(TestBP["summary"]) is True
        assert is_projected_blueprint(TestBP) is False

    def test_resolve_annotation_blueprint(self):
        class TestBP(Blueprint):
            name = TextFacet()

        cls, proj = resolve_blueprint_from_annotation(TestBP)
        assert cls is TestBP
        assert proj is None

    def test_resolve_annotation_projected(self):
        class TestBP(Blueprint):
            name = TextFacet()

            class Spec:
                projections = {"summary": ["name"]}

        cls, proj = resolve_blueprint_from_annotation(TestBP["summary"])
        assert cls is TestBP
        assert proj == "summary"

    def test_resolve_annotation_non_blueprint(self):
        cls, proj = resolve_blueprint_from_annotation(int)
        assert cls is None
        assert proj is None

    def test_render_blueprint_response(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        obj = MagicMock()
        obj.name = "Alice"
        obj.age = 30

        result = render_blueprint_response(TestBP, obj)
        assert result == {"name": "Alice", "age": 30}

    def test_render_many(self):
        class TestBP(Blueprint):
            name = TextFacet()

        obj1 = MagicMock()
        obj1.name = "Alice"
        obj2 = MagicMock()
        obj2.name = "Bob"

        result = render_blueprint_response(TestBP, [obj1, obj2], many=True)
        assert len(result) == 2

    def test_render_with_projection(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

            class Spec:
                projections = {"summary": ["name"]}

        obj = MagicMock()
        obj.name = "Alice"
        obj.age = 30

        result = render_blueprint_response(TestBP["summary"], obj)
        assert "name" in result
        assert "age" not in result


# ═══════════════════════════════════════════════════════════════════════
# 10. EXCEPTIONS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_blueprint_fault_base(self):
        f = BlueprintFault(message="test", errors={"name": ["required"]})
        body = f.as_response_body()
        assert body["fault"] == "BP000"
        assert body["errors"]["name"] == ["required"]

    def test_cast_fault(self):
        f = CastFault("email", "Invalid format")
        assert f.field == "email"
        assert "email" in f.field_errors

    def test_seal_fault(self):
        f = SealFault(
            message="Validation failed",
            errors={"name": ["required"], "age": ["too young"]},
        )
        assert len(f.field_errors) == 2

    def test_imprint_fault(self):
        f = ImprintFault(message="Cannot create")
        assert f.code == "BP300"

    def test_projection_fault(self):
        f = ProjectionFault("missing", ["summary", "detail"])
        assert "missing" in str(f)

    def test_lens_depth_fault(self):
        f = LensDepthFault("user.manager.manager", 2)
        assert "depth exceeded" in str(f).lower() or "depth" in str(f).lower()

    def test_lens_cycle_fault(self):
        f = LensCycleFault(["A", "B", "A"])
        assert "circular" in str(f).lower() or "Circular" in str(f)


# ═══════════════════════════════════════════════════════════════════════
# 11. EDGE CASES & ADVANCED
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_pure_blueprint_no_model(self):
        """Blueprint without a model — pure validation contract."""
        class LoginBP(Blueprint):
            username = TextFacet(min_length=3)
            password = TextFacet(min_length=8)

        bp = LoginBP(data={"username": "alice", "password": "password123"})
        assert bp.is_sealed() is True
        assert bp.validated_data["username"] == "alice"

    def test_blueprint_repr(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "test"})
        r = repr(bp)
        assert "TestBP" in r
        assert "pending" in r

    def test_facet_names(self):
        class TestBP(Blueprint):
            name = TextFacet()
            age = IntFacet()

        names = TestBP.facet_names()
        assert "name" in names
        assert "age" in names

    def test_get_facet(self):
        class TestBP(Blueprint):
            name = TextFacet(max_length=100)

        facet = TestBP.get_facet("name")
        assert isinstance(facet, TextFacet)
        assert facet.max_length == 100
        assert TestBP.get_facet("missing") is None

    def test_multiple_errors_accumulated(self):
        class TestBP(Blueprint):
            name = TextFacet(min_length=2)
            age = IntFacet(min_value=0)
            email = EmailFacet()

        bp = TestBP(data={"name": "x", "age": -1, "email": "bad"})
        assert bp.is_sealed() is False
        assert "name" in bp.errors
        assert "age" in bp.errors
        assert "email" in bp.errors

    def test_data_property_after_seal(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "Alice"})
        bp.is_sealed()
        assert bp.data == {"name": "Alice"}

    def test_sealed_idempotent(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is True
        assert bp.is_sealed() is True  # cached

    def test_projection_registry_contains(self):
        reg = ProjectionRegistry()
        reg.configure(
            projections={"summary": ["name"]},
            default="summary",
            all_facet_names={"name", "age"},
            write_only_names=set(),
        )
        assert "summary" in reg
        assert "missing" not in reg

    def test_inherit_and_extend(self):
        class BaseBP(Blueprint):
            id = IntFacet(read_only=True)
            created_at = DateTimeFacet(read_only=True)

        class UserBP(BaseBP):
            name = TextFacet()
            email = EmailFacet()

        assert "id" in UserBP._all_facets
        assert "created_at" in UserBP._all_facets
        assert "name" in UserBP._all_facets
        assert "email" in UserBP._all_facets

    def test_empty_data_dict(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={})
        assert bp.is_sealed() is False
        assert "name" in bp.errors

    def test_extra_data_ignored(self):
        class TestBP(Blueprint):
            name = TextFacet()

        bp = TestBP(data={"name": "Alice", "unknown_field": "ignored"})
        assert bp.is_sealed() is True
        assert "unknown_field" not in bp.validated_data

    def test_hidden_field_with_default(self):
        class TestBP(Blueprint):
            name = TextFacet()
            audit_id = Hidden(default=42)

        bp = TestBP(data={"name": "Alice"})
        assert bp.is_sealed() is True
        assert bp.validated_data["audit_id"] == 42

    def test_facet_ordering_stable(self):
        """Facets should maintain declaration order."""
        class TestBP(Blueprint):
            z_field = TextFacet()
            a_field = IntFacet()
            m_field = BoolFacet()

        names = list(TestBP._all_facets.keys())
        assert names == ["z_field", "a_field", "m_field"]


class TestDIInjection:
    def test_inject_facet_from_context(self):
        class TestBP(Blueprint):
            name = TextFacet()
            service_val = Inject("my_service", attr="value")

        mock_container = MagicMock()
        mock_service = MagicMock()
        mock_service.value = "injected"
        mock_container.resolve.return_value = mock_service

        bp = TestBP(
            data={"name": "test"},
            context={"container": mock_container},
        )
        assert bp.is_sealed() is True
        assert bp.validated_data.get("service_val") == "injected"

    def test_inject_via_method(self):
        class TestBP(Blueprint):
            name = TextFacet()
            total = Inject("pricer", via="calculate")

        mock_container = MagicMock()
        mock_pricer = MagicMock()
        mock_pricer.calculate.return_value = 42.0
        mock_container.resolve.return_value = mock_pricer

        bp = TestBP(
            data={"name": "test"},
            context={"container": mock_container},
        )
        assert bp.is_sealed() is True
        assert bp.validated_data.get("total") == 42.0

    def test_inject_no_container(self):
        class TestBP(Blueprint):
            name = TextFacet()
            service = Inject("missing")

        bp = TestBP(data={"name": "test"})
        assert bp.is_sealed() is True
        # No container → inject returns UNSET → skipped
        assert "service" not in bp.validated_data
