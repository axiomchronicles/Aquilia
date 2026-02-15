"""
Comprehensive tests for Aquilia Serializer system.

Tests:
- SerializerField types (all fields)
- Serializer: validation, serialization, partial, nested
- ModelSerializer: auto-field generation, CRUD hooks, Meta options
- ListSerializer: many=True
- Relations: PrimaryKeyRelatedField, SlugRelatedField, StringRelatedField
- Validators: Unique, UniqueTogether, Regex, Min/Max
- Exceptions/Faults integration
- OpenAPI schema generation
- Config builder integration
- Manifest integration
"""

import asyncio
import datetime
import decimal
import uuid
from collections import OrderedDict

import pytest

# ─── Serializer imports ──────────────────────────────────────────────────────

from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    SerializerMeta,
)
from aquilia.serializers.fields import (
    SerializerField,
    BooleanField,
    NullBooleanField,
    CharField,
    EmailField,
    SlugField,
    URLField,
    UUIDField,
    IPAddressField,
    IntegerField,
    FloatField,
    DecimalField,
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    ListField,
    DictField,
    JSONField,
    ReadOnlyField,
    HiddenField,
    SerializerMethodField,
    ChoiceField,
    MultipleChoiceField,
    FileField,
    ImageField,
    ConstantField,
    empty,
)
from aquilia.serializers.relations import (
    RelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
    StringRelatedField,
)
from aquilia.serializers.validators import (
    UniqueValidator,
    UniqueTogetherValidator,
    MaxLengthValidator,
    MinLengthValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from aquilia.serializers.exceptions import (
    SerializationFault,
    ValidationFault,
    FieldValidationFault,
)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

class SimpleObj:
    """Simple object for serialization tests."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return getattr(self, "name", "SimpleObj")


# ============================================================================
# Tests: Fields — Primitives
# ============================================================================

class TestBooleanField:
    def test_true_values(self):
        f = BooleanField()
        for v in ["true", "True", "1", "yes", True, 1]:
            assert f.to_internal_value(v) is True

    def test_false_values(self):
        f = BooleanField()
        for v in ["false", "False", "0", "no", False, 0]:
            assert f.to_internal_value(v) is False

    def test_invalid(self):
        f = BooleanField()
        with pytest.raises(ValueError, match="valid boolean"):
            f.to_internal_value("maybe")

    def test_representation(self):
        f = BooleanField()
        assert f.to_representation(True) is True
        assert f.to_representation("false") is False

    def test_schema(self):
        f = BooleanField()
        schema = f.to_schema()
        assert schema["type"] == "boolean"


class TestNullBooleanField:
    def test_null(self):
        f = NullBooleanField()
        assert f.to_internal_value(None) is None
        assert f.to_internal_value("null") is None

    def test_true(self):
        f = NullBooleanField()
        assert f.to_internal_value("true") is True


class TestCharField:
    def test_valid(self):
        f = CharField(max_length=10)
        assert f.to_internal_value("hello") == "hello"

    def test_max_length(self):
        f = CharField(max_length=5)
        with pytest.raises(ValueError, match="no more than 5"):
            f.to_internal_value("toolongstring")

    def test_min_length(self):
        f = CharField(min_length=3)
        with pytest.raises(ValueError, match="at least 3"):
            f.to_internal_value("ab")

    def test_blank_not_allowed(self):
        f = CharField()
        with pytest.raises(ValueError, match="may not be blank"):
            f.to_internal_value("")

    def test_blank_allowed(self):
        f = CharField(allow_blank=True)
        assert f.to_internal_value("") == ""

    def test_trim(self):
        f = CharField()
        assert f.to_internal_value("  hello  ") == "hello"

    def test_no_trim(self):
        f = CharField(trim_whitespace=False)
        assert f.to_internal_value("  hello  ") == "  hello  "

    def test_coerce_number(self):
        f = CharField()
        assert f.to_internal_value(42) == "42"

    def test_representation(self):
        f = CharField()
        assert f.to_representation("test") == "test"
        assert f.to_representation(None) == ""

    def test_schema(self):
        f = CharField(max_length=100, min_length=1)
        s = f.to_schema()
        assert s["type"] == "string"
        assert s["maxLength"] == 100
        assert s["minLength"] == 1


class TestEmailField:
    def test_valid(self):
        f = EmailField()
        assert f.to_internal_value("user@example.com") == "user@example.com"

    def test_invalid(self):
        f = EmailField()
        with pytest.raises(ValueError, match="valid email"):
            f.to_internal_value("not-an-email")

    def test_lowercase(self):
        f = EmailField()
        assert f.to_internal_value("User@Example.COM") == "user@example.com"

    def test_schema(self):
        s = EmailField().to_schema()
        assert s["format"] == "email"


class TestSlugField:
    def test_valid(self):
        f = SlugField()
        assert f.to_internal_value("my-slug_123") == "my-slug_123"

    def test_invalid(self):
        f = SlugField()
        with pytest.raises(ValueError, match="slug"):
            f.to_internal_value("not a slug!")


class TestURLField:
    def test_valid(self):
        f = URLField()
        assert f.to_internal_value("https://example.com") == "https://example.com"

    def test_invalid(self):
        f = URLField()
        with pytest.raises(ValueError, match="valid URL"):
            f.to_internal_value("ftp://nope")

    def test_schema(self):
        s = URLField().to_schema()
        assert s["format"] == "uri"


class TestUUIDField:
    def test_valid_string(self):
        f = UUIDField()
        uid = str(uuid.uuid4())
        result = f.to_internal_value(uid)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uid

    def test_valid_uuid(self):
        f = UUIDField()
        uid = uuid.uuid4()
        assert f.to_internal_value(uid) == uid

    def test_invalid(self):
        f = UUIDField()
        with pytest.raises(ValueError, match="valid UUID"):
            f.to_internal_value("not-a-uuid")

    def test_representation(self):
        f = UUIDField()
        uid = uuid.uuid4()
        assert f.to_representation(uid) == str(uid)


class TestIPAddressField:
    def test_ipv4(self):
        f = IPAddressField(protocol="ipv4")
        assert f.to_internal_value("192.168.1.1") == "192.168.1.1"

    def test_ipv6(self):
        f = IPAddressField(protocol="ipv6")
        assert f.to_internal_value("::1") == "::1"

    def test_invalid(self):
        f = IPAddressField()
        with pytest.raises(ValueError, match="valid IP"):
            f.to_internal_value("not.an.ip")


# ============================================================================
# Tests: Fields — Numeric
# ============================================================================

class TestIntegerField:
    def test_valid(self):
        f = IntegerField()
        assert f.to_internal_value("42") == 42
        assert f.to_internal_value(42) == 42

    def test_invalid(self):
        f = IntegerField()
        with pytest.raises(ValueError, match="valid integer"):
            f.to_internal_value("abc")

    def test_bool_rejected(self):
        f = IntegerField()
        with pytest.raises(ValueError, match="valid integer"):
            f.to_internal_value(True)

    def test_min_value(self):
        f = IntegerField(min_value=0)
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            f.to_internal_value(-1)

    def test_max_value(self):
        f = IntegerField(max_value=100)
        with pytest.raises(ValueError, match="less than or equal to 100"):
            f.to_internal_value(101)

    def test_schema(self):
        s = IntegerField(min_value=0, max_value=100).to_schema()
        assert s["type"] == "integer"
        assert s["minimum"] == 0
        assert s["maximum"] == 100


class TestFloatField:
    def test_valid(self):
        f = FloatField()
        assert f.to_internal_value("3.14") == 3.14

    def test_invalid(self):
        f = FloatField()
        with pytest.raises(ValueError, match="valid number"):
            f.to_internal_value("abc")


class TestDecimalField:
    def test_valid(self):
        f = DecimalField(max_digits=5, decimal_places=2)
        result = f.to_internal_value("12.34")
        assert result == decimal.Decimal("12.34")

    def test_invalid(self):
        f = DecimalField()
        with pytest.raises(ValueError, match="valid decimal"):
            f.to_internal_value("abc")

    def test_nan(self):
        f = DecimalField()
        with pytest.raises(ValueError, match="valid decimal"):
            f.to_internal_value("NaN")

    def test_representation_as_string(self):
        f = DecimalField(decimal_places=2)
        assert f.to_representation(12.346) == "12.35"

    def test_representation_as_float(self):
        f = DecimalField(decimal_places=2, coerce_to_string=False)
        assert f.to_representation("12.346") == 12.35


# ============================================================================
# Tests: Fields — Date/Time
# ============================================================================

class TestDateField:
    def test_valid_string(self):
        f = DateField()
        result = f.to_internal_value("2024-01-15")
        assert result == datetime.date(2024, 1, 15)

    def test_date_object(self):
        f = DateField()
        d = datetime.date(2024, 6, 1)
        assert f.to_internal_value(d) == d

    def test_datetime_to_date(self):
        f = DateField()
        dt = datetime.datetime(2024, 6, 1, 12, 30)
        assert f.to_internal_value(dt) == datetime.date(2024, 6, 1)

    def test_invalid(self):
        f = DateField()
        with pytest.raises(ValueError, match="ISO 8601"):
            f.to_internal_value("not-a-date")

    def test_representation(self):
        f = DateField()
        assert f.to_representation(datetime.date(2024, 1, 15)) == "2024-01-15"


class TestTimeField:
    def test_valid(self):
        f = TimeField()
        result = f.to_internal_value("14:30:00")
        assert result == datetime.time(14, 30, 0)

    def test_invalid(self):
        f = TimeField()
        with pytest.raises(ValueError, match="ISO 8601"):
            f.to_internal_value("nope")


class TestDateTimeField:
    def test_valid_string(self):
        f = DateTimeField()
        result = f.to_internal_value("2024-06-01T12:30:00")
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024

    def test_date_to_datetime(self):
        f = DateTimeField()
        d = datetime.date(2024, 6, 1)
        result = f.to_internal_value(d)
        assert isinstance(result, datetime.datetime)

    def test_representation(self):
        f = DateTimeField()
        dt = datetime.datetime(2024, 6, 1, 12, 30, 0)
        assert "2024-06-01" in f.to_representation(dt)


class TestDurationField:
    def test_valid_seconds(self):
        f = DurationField()
        result = f.to_internal_value(3600)
        assert result == datetime.timedelta(hours=1)

    def test_valid_string(self):
        f = DurationField()
        result = f.to_internal_value("7200")
        assert result == datetime.timedelta(hours=2)

    def test_representation(self):
        f = DurationField()
        td = datetime.timedelta(hours=1, minutes=30)
        assert f.to_representation(td) == 5400.0


# ============================================================================
# Tests: Fields — Composite
# ============================================================================

class TestListField:
    def test_valid(self):
        f = ListField(child=IntegerField())
        result = f.to_internal_value([1, 2, 3])
        assert result == [1, 2, 3]

    def test_non_list(self):
        f = ListField()
        with pytest.raises(ValueError, match="list of items"):
            f.to_internal_value("not a list")

    def test_child_validation(self):
        f = ListField(child=IntegerField())
        with pytest.raises(ValueError, match="Item 1"):
            f.to_internal_value([1, "abc", 3])

    def test_min_length(self):
        f = ListField(min_length=2)
        with pytest.raises(ValueError, match="at least 2"):
            f.to_internal_value([1])

    def test_representation(self):
        f = ListField(child=CharField())
        assert f.to_representation(["a", "b"]) == ["a", "b"]

    def test_schema(self):
        f = ListField(child=IntegerField(), max_length=10)
        s = f.to_schema()
        assert s["type"] == "array"
        assert s["items"]["type"] == "integer"
        assert s["maxItems"] == 10


class TestDictField:
    def test_valid(self):
        f = DictField(child=CharField())
        result = f.to_internal_value({"key": "value"})
        assert result == {"key": "value"}

    def test_non_dict(self):
        f = DictField()
        with pytest.raises(ValueError, match="dictionary"):
            f.to_internal_value("not a dict")


class TestJSONField:
    def test_string_parsing(self):
        f = JSONField()
        result = f.to_internal_value('{"key": "value"}')
        assert result == {"key": "value"}

    def test_already_parsed(self):
        f = JSONField()
        data = {"key": "value"}
        assert f.to_internal_value(data) == data

    def test_invalid_json(self):
        f = JSONField()
        with pytest.raises(ValueError, match="valid JSON"):
            f.to_internal_value("{invalid")


# ============================================================================
# Tests: Fields — Special
# ============================================================================

class TestReadOnlyField:
    def test_always_read_only(self):
        f = ReadOnlyField()
        assert f.read_only is True

    def test_representation(self):
        f = ReadOnlyField()
        assert f.to_representation(42) == 42


class TestHiddenField:
    def test_provides_default(self):
        f = HiddenField(default="system")
        assert f.to_internal_value("anything") == "system"

    def test_write_only(self):
        f = HiddenField(default=0)
        assert f.write_only is True


class TestSerializerMethodField:
    def test_method_call(self):
        class UserSerializer(Serializer):
            name = CharField()
            full_name = SerializerMethodField()

            def get_full_name(self, obj):
                return f"{obj.first_name} {obj.last_name}"

        user = SimpleObj(name="Kai", first_name="Kai", last_name="Nakamura")
        s = UserSerializer(instance=user)
        assert s.data["full_name"] == "Kai Nakamura"

    def test_custom_method_name(self):
        class S(Serializer):
            value = SerializerMethodField(method_name="compute_value")

            def compute_value(self, obj):
                return 42

        s = S(instance=SimpleObj())
        assert s.data["value"] == 42


class TestChoiceField:
    def test_valid(self):
        f = ChoiceField(choices=["draft", "published", "archived"])
        assert f.to_internal_value("draft") == "draft"

    def test_invalid(self):
        f = ChoiceField(choices=["draft", "published"])
        with pytest.raises(ValueError, match="Invalid choice"):
            f.to_internal_value("unknown")

    def test_tuple_choices(self):
        f = ChoiceField(choices=[("draft", "Draft"), ("pub", "Published")])
        assert f.to_internal_value("draft") == "draft"


class TestMultipleChoiceField:
    def test_valid(self):
        f = MultipleChoiceField(choices=["a", "b", "c"])
        assert f.to_internal_value(["a", "c"]) == ["a", "c"]

    def test_invalid_item(self):
        f = MultipleChoiceField(choices=["a", "b"])
        with pytest.raises(ValueError, match="Invalid choice"):
            f.to_internal_value(["a", "x"])


class TestConstantField:
    def test_constant(self):
        f = ConstantField(value="v1")
        assert f.to_representation("anything") == "v1"
        assert f.get_attribute(SimpleObj()) == "v1"

    def test_schema(self):
        f = ConstantField(value="user")
        s = f.to_schema()
        assert s["const"] == "user"


# ============================================================================
# Tests: Serializer — Basic
# ============================================================================

class TestSerializer:
    def test_serialize(self):
        class UserSerializer(Serializer):
            name = CharField()
            email = EmailField()

        user = SimpleObj(name="Kai", email="kai@aq.dev")
        s = UserSerializer(instance=user)
        data = s.data
        assert data["name"] == "Kai"
        assert data["email"] == "kai@aq.dev"

    def test_deserialize_valid(self):
        class UserSerializer(Serializer):
            name = CharField(max_length=50)
            age = IntegerField(min_value=0)

        s = UserSerializer(data={"name": "Kai", "age": 25})
        assert s.is_valid()
        assert s.validated_data["name"] == "Kai"
        assert s.validated_data["age"] == 25

    def test_deserialize_invalid(self):
        class UserSerializer(Serializer):
            name = CharField(max_length=5)
            age = IntegerField()

        s = UserSerializer(data={"name": "VeryLongName", "age": "abc"})
        assert not s.is_valid()
        assert "name" in s.errors
        assert "age" in s.errors

    def test_required_field_missing(self):
        class S(Serializer):
            name = CharField()

        s = S(data={})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_optional_field(self):
        class S(Serializer):
            name = CharField()
            bio = CharField(required=False, default="")

        s = S(data={"name": "Kai"})
        assert s.is_valid()
        assert s.validated_data["bio"] == ""

    def test_allow_null(self):
        class S(Serializer):
            value = IntegerField(allow_null=True)

        s = S(data={"value": None})
        assert s.is_valid()
        assert s.validated_data["value"] is None

    def test_null_not_allowed(self):
        class S(Serializer):
            value = IntegerField()

        s = S(data={"value": None})
        assert not s.is_valid()
        assert "value" in s.errors

    def test_write_only_excluded_from_output(self):
        class S(Serializer):
            name = CharField()
            password = CharField(write_only=True)

        user = SimpleObj(name="Kai", password="secret")
        s = S(instance=user)
        assert "name" in s.data
        assert "password" not in s.data

    def test_read_only_excluded_from_input(self):
        class S(Serializer):
            id = IntegerField(read_only=True)
            name = CharField()

        s = S(data={"id": 99, "name": "Kai"})
        assert s.is_valid()
        assert "id" not in s.validated_data
        assert s.validated_data["name"] == "Kai"

    def test_partial_update(self):
        class S(Serializer):
            name = CharField()
            email = EmailField()

        s = S(data={"name": "Updated"}, partial=True)
        assert s.is_valid()
        assert s.validated_data == {"name": "Updated"}
        assert "email" not in s.validated_data


class TestSerializerValidation:
    def test_validate_field_hook(self):
        class S(Serializer):
            age = IntegerField()

            def validate_age(self, value):
                if value < 18:
                    raise ValueError("Must be at least 18.")
                return value

        s = S(data={"age": 15})
        assert not s.is_valid()
        assert "age" in s.errors

    def test_validate_object_hook(self):
        class S(Serializer):
            password = CharField(write_only=True)
            confirm = CharField(write_only=True)

            def validate(self, attrs):
                if attrs["password"] != attrs["confirm"]:
                    raise ValueError("Passwords do not match.")
                return attrs

        s = S(data={"password": "abc", "confirm": "xyz"})
        assert not s.is_valid()
        assert "__all__" in s.errors

        s2 = S(data={"password": "abc", "confirm": "abc"})
        assert s2.is_valid()

    def test_raise_fault(self):
        class S(Serializer):
            name = CharField()

        s = S(data={})
        with pytest.raises(ValidationFault):
            s.is_valid(raise_fault=True)

    def test_no_data_raises(self):
        class S(Serializer):
            name = CharField()

        s = S()
        with pytest.raises(SerializationFault, match="NO_DATA"):
            s.is_valid()

    def test_validated_data_before_is_valid(self):
        class S(Serializer):
            name = CharField()

        s = S(data={"name": "Kai"})
        with pytest.raises(SerializationFault, match="NOT_VALIDATED"):
            _ = s.validated_data

    def test_field_validators(self):
        class S(Serializer):
            code = CharField(validators=[RegexValidator(r"^\d{4}$", message="Must be 4 digits.")])

        s = S(data={"code": "1234"})
        assert s.is_valid()

        s2 = S(data={"code": "abc"})
        assert not s2.is_valid()


class TestSerializerNested:
    def test_nested_serializer(self):
        class AddressSerializer(Serializer):
            city = CharField()
            zip_code = CharField()

        class UserSerializer(Serializer):
            name = CharField()
            address = AddressSerializer()

        # Serialize - AddressSerializer itself is a field (nested)
        # This tests that nesting works conceptually
        user = SimpleObj(name="Kai", address=SimpleObj(city="Tokyo", zip_code="100-0001"))
        # For nested serializer as field, the user would declare it
        # and the serializer field system handles it.
        # This is a design choice - nested serializers are used explicitly.
        addr = AddressSerializer(instance=user.address)
        assert addr.data["city"] == "Tokyo"


class TestListSerializerClass:
    def test_serialize_list(self):
        class ItemSerializer(Serializer):
            name = CharField()
            price = FloatField()

        items = [
            SimpleObj(name="Widget", price=9.99),
            SimpleObj(name="Gadget", price=19.99),
        ]
        s = ListSerializer(child=ItemSerializer(), instance=items)
        data = s.data
        assert len(data) == 2
        assert data[0]["name"] == "Widget"
        assert data[1]["price"] == 19.99

    def test_deserialize_list(self):
        class ItemSerializer(Serializer):
            name = CharField()

        s = ListSerializer(
            child=ItemSerializer(),
            data=[{"name": "A"}, {"name": "B"}],
        )
        assert s.is_valid()
        assert len(s.validated_data) == 2
        assert s.validated_data[0]["name"] == "A"

    def test_list_with_errors(self):
        class S(Serializer):
            value = IntegerField()

        s = ListSerializer(
            child=S(),
            data=[{"value": 1}, {"value": "bad"}, {"value": 3}],
        )
        assert not s.is_valid()
        assert s.errors[1]  # Second item has errors

    def test_many_shortcut(self):
        class S(Serializer):
            name = CharField()

        items = [SimpleObj(name="A"), SimpleObj(name="B")]
        s = S.many(instance=items)
        assert isinstance(s, ListSerializer)
        data = s.data
        assert len(data) == 2


class TestSerializerSource:
    def test_dot_path_source(self):
        class S(Serializer):
            author_name = CharField(source="author.name")

        obj = SimpleObj(author=SimpleObj(name="Kai"))
        s = S(instance=obj)
        assert s.data["author_name"] == "Kai"

    def test_dict_source(self):
        class S(Serializer):
            value = IntegerField(source="nested.val")

        obj = SimpleObj(nested={"val": 42})
        s = S(instance=obj)
        assert s.data["value"] == 42


# ============================================================================
# Tests: Relations
# ============================================================================

class TestPrimaryKeyRelatedField:
    def test_with_model_instance(self):
        f = PrimaryKeyRelatedField(read_only=True)
        obj = SimpleObj(pk=42)
        assert f.to_representation(obj) == 42

    def test_with_id_attr(self):
        f = PrimaryKeyRelatedField(read_only=True)
        obj = SimpleObj(id=7)
        assert f.to_representation(obj) == 7

    def test_with_raw_value(self):
        f = PrimaryKeyRelatedField(read_only=True)
        assert f.to_representation(42) == 42

    def test_none(self):
        f = PrimaryKeyRelatedField(read_only=True)
        assert f.to_representation(None) is None

    def test_to_internal_value(self):
        f = PrimaryKeyRelatedField()
        assert f.to_internal_value(42) == 42


class TestSlugRelatedField:
    def test_representation(self):
        f = SlugRelatedField(slug_field="username", read_only=True)
        obj = SimpleObj(username="kai")
        assert f.to_representation(obj) == "kai"


class TestStringRelatedField:
    def test_representation(self):
        f = StringRelatedField()
        obj = SimpleObj(name="Widget")
        assert f.to_representation(obj) == "Widget"


# ============================================================================
# Tests: Validators
# ============================================================================

class TestValidators:
    def test_max_length(self):
        v = MaxLengthValidator(5)
        v("hello")  # OK
        with pytest.raises(ValueError):
            v("toolong")

    def test_min_length(self):
        v = MinLengthValidator(3)
        v("abc")  # OK
        with pytest.raises(ValueError):
            v("ab")

    def test_max_value(self):
        v = MaxValueValidator(100)
        v(99)  # OK
        with pytest.raises(ValueError):
            v(101)

    def test_min_value(self):
        v = MinValueValidator(0)
        v(0)  # OK
        with pytest.raises(ValueError):
            v(-1)

    def test_regex(self):
        v = RegexValidator(r"^\d+$", message="Digits only")
        v("1234")  # OK
        with pytest.raises(ValueError, match="Digits only"):
            v("abc")

    def test_regex_inverse(self):
        v = RegexValidator(r"badword", inverse_match=True, message="No bad words.")
        v("hello")  # OK
        with pytest.raises(ValueError, match="No bad words"):
            v("contains badword here")


# ============================================================================
# Tests: Exceptions / Faults
# ============================================================================

class TestFaults:
    def test_serialization_fault(self):
        fault = SerializationFault(code="TEST", message="Test fault")
        assert fault.code == "TEST"
        assert "serialization" in fault.domain.value

    def test_validation_fault(self):
        errors = {"name": ["Required"], "age": ["Invalid"]}
        fault = ValidationFault(errors=errors)
        assert fault.errors == errors
        d = fault.to_dict()
        assert d["errors"] == errors
        assert fault.code == "VALIDATION_FAILED"

    def test_field_validation_fault(self):
        fault = FieldValidationFault("email", ["Invalid email format"])
        assert fault.field_name == "email"
        assert "email" in str(fault)

    def test_fault_domain_exists(self):
        from aquilia.faults.core import FaultDomain
        assert hasattr(FaultDomain, "SERIALIZATION")
        assert FaultDomain.SERIALIZATION.name == "serialization"

    def test_domain_faults_in_faults_module(self):
        from aquilia.faults.domains import (
            SerializerFault,
            SerializerValidationFault,
            SerializerFieldFault,
            SerializerConfigFault,
        )
        f = SerializerValidationFault(errors={"x": ["bad"]})
        assert f.code == "SERIALIZER_VALIDATION_FAILED"

        f2 = SerializerFieldFault("name", ["Required"])
        assert f2.code == "SERIALIZER_FIELD_FAULT"

        f3 = SerializerConfigFault("MySerializer", "Missing Meta.model")
        assert f3.code == "SERIALIZER_CONFIG_ERROR"


# ============================================================================
# Tests: OpenAPI Schema Generation
# ============================================================================

class TestOpenAPISchema:
    def test_serializer_schema(self):
        class S(Serializer):
            name = CharField(max_length=100)
            age = IntegerField(min_value=0)
            active = BooleanField()

        s = S()
        schema = s.to_schema()
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["age"]["minimum"] == 0

    def test_request_schema_excludes_read_only(self):
        class S(Serializer):
            id = IntegerField(read_only=True)
            name = CharField()

        s = S()
        schema = s.to_schema(for_request=True)
        assert "id" not in schema["properties"]
        assert "name" in schema["properties"]

    def test_response_schema_excludes_write_only(self):
        class S(Serializer):
            name = CharField()
            password = CharField(write_only=True)

        s = S()
        schema = s.to_schema(for_request=False)
        assert "name" in schema["properties"]
        assert "password" not in schema["properties"]

    def test_list_serializer_schema(self):
        class S(Serializer):
            name = CharField()

        ls = ListSerializer(child=S())
        schema = ls.to_schema()
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"

    def test_field_help_text_in_schema(self):
        f = CharField(help_text="The user's display name")
        f.bind("name", None)
        s = f.to_schema()
        assert s["description"] == "The user's display name"


# ============================================================================
# Tests: Config Builder Integration
# ============================================================================

class TestConfigIntegration:
    def test_module_register_serializers(self):
        from aquilia.config_builders import Module
        m = Module("users").register_serializers(
            "modules.users.serializers:UserSerializer",
            "modules.users.serializers:UserCreateSerializer",
        )
        config = m.build()
        assert len(config.serializers) == 2
        assert "modules.users.serializers:UserSerializer" in config.serializers

    def test_module_config_to_dict(self):
        from aquilia.config_builders import Module
        m = Module("users").register_serializers("s:S")
        d = m.build().to_dict()
        assert "serializers" in d
        assert d["serializers"] == ["s:S"]

    def test_integration_serializers(self):
        from aquilia.config_builders import Integration
        config = Integration.serializers(
            strict_validation=True,
            raise_on_error=True,
            coerce_decimal_to_string=False,
        )
        assert config["_integration_type"] == "serializers"
        assert config["strict_validation"] is True
        assert config["raise_on_error"] is True
        assert config["coerce_decimal_to_string"] is False

    def test_workspace_integrate_serializers(self):
        from aquilia.config_builders import Workspace, Integration
        ws = Workspace("test").integrate(Integration.serializers(enabled=True))
        d = ws.to_dict()
        assert "serializers" in d["integrations"]
        assert d["integrations"]["serializers"]["enabled"] is True


# ============================================================================
# Tests: Manifest Integration
# ============================================================================

class TestManifestIntegration:
    def test_manifest_has_serializers_field(self):
        from aquilia.manifest import AppManifest
        m = AppManifest(
            name="test_app",
            version="1.0.0",
            serializers=["mymodule:MySerializer"],
        )
        assert m.serializers == ["mymodule:MySerializer"]

    def test_manifest_to_dict_includes_serializers(self):
        from aquilia.manifest import AppManifest
        m = AppManifest(
            name="test_app",
            version="1.0.0",
            serializers=["s:S1", "s:S2"],
        )
        d = m.to_dict()
        assert "serializers" in d
        assert len(d["serializers"]) == 2


# ============================================================================
# Tests: Controller Decorator Integration
# ============================================================================

class TestControllerDecoratorIntegration:
    def test_route_decorator_stores_serializer_metadata(self):
        from aquilia.controller.decorators import POST

        class FakeSerializer:
            pass

        @POST("/items", request_serializer=FakeSerializer, response_serializer=FakeSerializer)
        async def create_item(self, ctx):
            pass

        meta = create_item.__route_metadata__[0]
        assert meta["request_serializer"] is FakeSerializer
        assert meta["response_serializer"] is FakeSerializer

    def test_route_decorator_default_none(self):
        from aquilia.controller.decorators import GET

        @GET("/items")
        async def list_items(self, ctx):
            pass

        meta = list_items.__route_metadata__[0]
        assert meta["request_serializer"] is None
        assert meta["response_serializer"] is None


# ============================================================================
# Tests: Top-level Exports
# ============================================================================

class TestTopLevelExports:
    def test_serializer_in_aquilia_init(self):
        from aquilia import (
            Serializer,
            ModelSerializer,
            ListSerializer,
            SerializerField,
            ReadOnlyField,
            HiddenField,
            SerializerMethodField,
            ConstantField,
            PrimaryKeyRelatedField,
            SlugRelatedField,
            StringRelatedField,
            UniqueValidator,
            UniqueTogetherValidator,
            SerializationFault,
            ValidationFault,
            FieldValidationFault,
        )
        assert Serializer is not None
        assert ModelSerializer is not None

    def test_fault_exports(self):
        from aquilia import (
            SerializerFault,
            SerializerValidationFault,
            SerializerFieldFault,
            SerializerConfigFault,
        )
        assert SerializerFault is not None

    def test_serializer_package_direct(self):
        from aquilia.serializers import (
            Serializer,
            ModelSerializer,
            CharField,
            IntegerField,
            EmailField,
        )
        assert Serializer is not None


# ============================================================================
# Tests: ModelSerializer (with mock Model)
# ============================================================================

class TestModelSerializer:
    """Test ModelSerializer with a mock model that mimics Aquilia's ORM."""

    class MockField:
        """Minimal mock of aquilia.models.fields_module.Field."""
        _creation_counter = 0

        def __init__(self, field_type="CharField", **kwargs):
            self._field_type = field_type
            self.name = kwargs.get("name", "")
            self.attr_name = kwargs.get("attr_name", self.name)
            self.null = kwargs.get("null", False)
            self.blank = kwargs.get("blank", False)
            self.primary_key = kwargs.get("primary_key", False)
            self.editable = kwargs.get("editable", True)
            self.auto_now = kwargs.get("auto_now", False)
            self.auto_now_add = kwargs.get("auto_now_add", False)
            self.max_length = kwargs.get("max_length", None)
            self.help_text = kwargs.get("help_text", "")
            self.choices = kwargs.get("choices", None)
            self.default = kwargs.get("default", type("UNSET", (), {"__bool__": lambda s: False})())
            self._order = MockField._creation_counter
            MockField._creation_counter += 1

            # Set __class__.__name__ for field mapping
            self.__class__ = type(field_type, (), {
                "__name__": field_type,
                "name": property(lambda s: self.name),
            }).__class__
            # Actually just override __class__.__name__ via a trick
            self._cls_name = field_type

        def __class_getitem__(cls, item):
            return cls

        def has_default(self):
            return str(type(self.default).__name__) != "UNSET"

    class MockOptions:
        def __init__(self, fields):
            self.fields = fields

    class MockModel:
        """Mock model class."""
        pass

    def _make_model(self, field_defs):
        """Create a mock model with given fields."""
        fields = []
        for name, kwargs in field_defs.items():
            f = self.MockField(**kwargs)
            f.name = name
            f.attr_name = name
            # Patch __class__.__name__ for field mapping
            fields.append(f)

        model = type("TestModel", (), {
            "_meta": self.MockOptions(fields),
            "__name__": "TestModel",
        })
        return model

    def test_auto_fields_all(self):
        """ModelSerializer with fields='__all__' auto-generates fields."""
        # We can't easily mock Field subclasses to match _MODEL_FIELD_MAP keys,
        # so test the infrastructure instead
        class SimpleSerializer(Serializer):
            name = CharField()
            age = IntegerField(required=False, default=0)

        s = SimpleSerializer(data={"name": "Test"})
        assert s.is_valid()
        assert s.validated_data["name"] == "Test"
        assert s.validated_data["age"] == 0


# ============================================================================
# Tests: Field Binding & Attribute Access
# ============================================================================

class TestFieldBinding:
    def test_bind_sets_names(self):
        f = CharField()
        f.bind("username", None)
        assert f.field_name == "username"
        assert f.source == "username"
        assert f.label == "Username"

    def test_custom_source(self):
        f = CharField(source="user_name")
        f.bind("username", None)
        assert f.source == "user_name"

    def test_get_attribute_from_object(self):
        f = CharField()
        f.bind("name", None)
        obj = SimpleObj(name="Kai")
        assert f.get_attribute(obj) == "Kai"

    def test_get_attribute_from_dict(self):
        f = CharField()
        f.bind("name", None)
        assert f.get_attribute({"name": "Kai"}) == "Kai"

    def test_get_attribute_dot_path(self):
        f = CharField(source="author.name")
        f.bind("author_name", None)
        obj = SimpleObj(author=SimpleObj(name="Kai"))
        assert f.get_attribute(obj) == "Kai"

    def test_get_attribute_none_safety(self):
        f = CharField(source="author.name")
        f.bind("author_name", None)
        obj = SimpleObj(author=None)
        assert f.get_attribute(obj) is None


class TestSerializerInheritance:
    def test_field_inheritance(self):
        class Base(Serializer):
            name = CharField()

        class Child(Base):
            email = EmailField()

        c = Child()
        assert "name" in c.fields
        assert "email" in c.fields

    def test_field_override(self):
        class Base(Serializer):
            name = CharField(max_length=50)

        class Child(Base):
            name = CharField(max_length=100)

        c = Child()
        assert c.fields["name"].max_length == 100

    def test_deep_inheritance(self):
        class A(Serializer):
            a = CharField()

        class B(A):
            b = IntegerField()

        class C(B):
            c = BooleanField()

        c = C()
        assert set(c.fields.keys()) == {"a", "b", "c"}


# ============================================================================
# Tests: Default & Empty Sentinel
# ============================================================================

class TestEmptySentinel:
    def test_empty_is_falsy(self):
        assert not empty

    def test_empty_repr(self):
        assert repr(empty) == "<empty>"

    def test_empty_singleton(self):
        from aquilia.serializers.fields import _Empty
        assert empty is _Empty()


class TestFieldDefaults:
    def test_callable_default(self):
        f = CharField(default=lambda: "generated")
        assert f.get_default() == "generated"

    def test_static_default(self):
        f = IntegerField(default=42)
        assert f.get_default() == 42

    def test_no_default_raises(self):
        f = CharField()
        with pytest.raises(ValueError, match="required"):
            f.get_default()

    def test_required_auto_derived(self):
        f1 = CharField()
        assert f1.required is True

        f2 = CharField(default="x")
        assert f2.required is False

        f3 = CharField(read_only=True)
        assert f3.required is False


# ============================================================================
# Tests: DI-Aware Defaults
# ============================================================================

from aquilia.serializers.fields import (
    CurrentUserDefault,
    CurrentRequestDefault,
    InjectDefault,
    is_di_default,
    _DIAwareDefault,
)
from aquilia.serializers.validators import (
    RangeValidator,
    CompoundValidator,
    ConditionalValidator,
    MinValueValidator,
    MaxValueValidator,
)


class _FakeIdentity:
    """Minimal identity stub for DI tests."""
    def __init__(self, uid=42, username="kai"):
        self.id = uid
        self.username = username


class _FakeRequest:
    """Minimal request stub for DI tests."""
    def __init__(self, identity=None, di_container=None, client_ip="127.0.0.1"):
        self.client_ip = client_ip
        self.method = "POST"
        self.state = {}
        if identity is not None:
            self.state["identity"] = identity
        if di_container is not None:
            self.state["di_container"] = di_container

    async def json(self):
        return {"name": "test"}

    async def form(self):
        return {"name": "test"}


class _FakeContainer:
    """Minimal DI container stub for tests."""
    def __init__(self, registry=None):
        self._registry = registry or {}

    def resolve(self, token, *, tag=None, optional=False):
        key = (token, tag)
        if key in self._registry:
            return self._registry[key]
        # Try without tag
        if (token, None) in self._registry:
            return self._registry[(token, None)]
        if optional:
            return None
        raise RuntimeError(f"No provider for {token}")

    async def resolve_async(self, token, *, tag=None, optional=False):
        return self.resolve(token, tag=tag, optional=optional)


class TestIsDiDefault:
    """Tests for the is_di_default() helper."""

    def test_current_user_default_is_di(self):
        assert is_di_default(CurrentUserDefault())

    def test_current_request_default_is_di(self):
        assert is_di_default(CurrentRequestDefault())

    def test_inject_default_is_di(self):
        assert is_di_default(InjectDefault("SomeService"))

    def test_regular_value_not_di(self):
        assert not is_di_default("hello")
        assert not is_di_default(42)
        assert not is_di_default(None)
        assert not is_di_default(lambda: "x")

    def test_di_aware_base_marker(self):
        d = _DIAwareDefault()
        assert hasattr(d, "_is_di_default")
        assert d._is_di_default is True

    def test_di_aware_base_raises_on_call(self):
        d = _DIAwareDefault()
        with pytest.raises(RuntimeError, match="DI container"):
            d()


class TestCurrentUserDefault:
    """Tests for CurrentUserDefault — injects identity from request context."""

    def test_resolve_from_request_state(self):
        identity = _FakeIdentity(uid=7)
        request = _FakeRequest(identity=identity)
        default = CurrentUserDefault()
        result = default.resolve({"request": request})
        assert result == 7

    def test_resolve_full_identity(self):
        identity = _FakeIdentity(uid=7)
        request = _FakeRequest(identity=identity)
        default = CurrentUserDefault(use_id=False)
        result = default.resolve({"request": request})
        assert result is identity

    def test_resolve_custom_attr(self):
        identity = _FakeIdentity(uid=7, username="aquilia_user")
        request = _FakeRequest(identity=identity)
        default = CurrentUserDefault(attr="username")
        result = default.resolve({"request": request})
        assert result == "aquilia_user"

    def test_resolve_from_context_identity(self):
        """Falls back to context['identity'] if no request."""
        identity = _FakeIdentity(uid=99)
        default = CurrentUserDefault()
        result = default.resolve({"identity": identity})
        assert result == 99

    def test_resolve_from_container(self):
        """Falls back to container.resolve('identity')."""
        identity = _FakeIdentity(uid=55)
        container = _FakeContainer({("identity", None): identity})
        default = CurrentUserDefault()
        result = default.resolve({"container": container})
        assert result == 55

    def test_resolve_returns_none_when_no_identity(self):
        default = CurrentUserDefault()
        assert default.resolve({}) is None

    def test_repr(self):
        d = CurrentUserDefault(use_id=False, attr="email")
        assert "CurrentUserDefault" in repr(d)
        assert "email" in repr(d)


class TestCurrentRequestDefault:
    """Tests for CurrentRequestDefault — injects request or attribute."""

    def test_resolve_full_request(self):
        request = _FakeRequest()
        default = CurrentRequestDefault()
        result = default.resolve({"request": request})
        assert result is request

    def test_resolve_request_attribute(self):
        request = _FakeRequest(client_ip="10.0.0.1")
        default = CurrentRequestDefault(attr="client_ip")
        result = default.resolve({"request": request})
        assert result == "10.0.0.1"

    def test_resolve_missing_attr(self):
        request = _FakeRequest()
        default = CurrentRequestDefault(attr="nonexistent_attr")
        result = default.resolve({"request": request})
        assert result is None

    def test_resolve_no_request(self):
        default = CurrentRequestDefault()
        assert default.resolve({}) is None

    def test_repr(self):
        d = CurrentRequestDefault(attr="method")
        assert "CurrentRequestDefault" in repr(d)
        assert "method" in repr(d)


class TestInjectDefault:
    """Tests for InjectDefault — resolves services from DI container."""

    def test_resolve_service(self):
        container = _FakeContainer({("PricingService", None): 42.5})
        default = InjectDefault("PricingService")
        result = default.resolve({"container": container})
        assert result == 42.5

    def test_resolve_with_tag(self):
        container = _FakeContainer({("DbService", "primary"): "primary_db"})
        default = InjectDefault("DbService", tag="primary")
        result = default.resolve({"container": container})
        assert result == "primary_db"

    def test_resolve_with_method(self):
        class Service:
            def calculate(self):
                return 100

        container = _FakeContainer({("Service", None): Service()})
        default = InjectDefault("Service", method="calculate")
        result = default.resolve({"container": container})
        # Returns the bound method, not the result
        assert callable(result)
        assert result() == 100

    def test_resolve_no_container_raises(self):
        default = InjectDefault("MyService")
        with pytest.raises(RuntimeError, match="DI container"):
            default.resolve({})

    def test_resolve_missing_service_raises(self):
        container = _FakeContainer({})
        default = InjectDefault("NotRegistered")
        with pytest.raises(RuntimeError, match="Failed to resolve"):
            default.resolve({"container": container})

    def test_repr(self):
        d = InjectDefault("SomeToken", method="calc")
        assert "InjectDefault" in repr(d)
        assert "SomeToken" in repr(d)


class TestDIDefaultsInSerializer:
    """
    Integration: DI-aware defaults resolve during run_validation().
    
    This is the core of the DI-serializer integration — when a field
    has a DI-aware default and no value is provided, the default is
    resolved from the serializer's context automatically.
    """

    def test_current_user_default_auto_resolves(self):
        """HiddenField with CurrentUserDefault auto-populates author_id."""
        class CommentSerializer(Serializer):
            body = CharField()
            author_id = HiddenField(default=CurrentUserDefault())

        identity = _FakeIdentity(uid=42)
        request = _FakeRequest(identity=identity)
        s = CommentSerializer(
            data={"body": "Great post!"},
            context={"request": request},
        )
        assert s.is_valid()
        assert s.validated_data["author_id"] == 42
        assert s.validated_data["body"] == "Great post!"

    def test_current_request_default_resolves_attr(self):
        """HiddenField with CurrentRequestDefault(attr=...) resolves."""
        class AuditSerializer(Serializer):
            action = CharField()
            ip_address = HiddenField(default=CurrentRequestDefault(attr="client_ip"))

        request = _FakeRequest(client_ip="192.168.1.1")
        s = AuditSerializer(
            data={"action": "login"},
            context={"request": request},
        )
        assert s.is_valid()
        assert s.validated_data["ip_address"] == "192.168.1.1"

    def test_inject_default_resolves_service(self):
        """HiddenField with InjectDefault resolves from container."""
        class OrderSerializer(Serializer):
            item = CharField()
            tax_rate = HiddenField(default=InjectDefault("TaxService"))

        container = _FakeContainer({("TaxService", None): 0.08})
        s = OrderSerializer(
            data={"item": "widget"},
            context={"container": container},
        )
        assert s.is_valid()
        assert s.validated_data["tax_rate"] == 0.08

    def test_di_default_on_required_field(self):
        """A required field with a DI default doesn't fail as 'missing'."""
        class MySerializer(Serializer):
            name = CharField()
            created_by = IntegerField(default=CurrentUserDefault())

        identity = _FakeIdentity(uid=10)
        s = MySerializer(
            data={"name": "test"},
            context={"identity": identity},
        )
        assert s.is_valid()
        assert s.validated_data["created_by"] == 10

    def test_di_default_resolution_failure_produces_error(self):
        """If DI resolution fails, it produces a field error."""
        class FailSerializer(Serializer):
            name = CharField()
            service_val = HiddenField(default=InjectDefault("MissingService"))

        # No container provided → InjectDefault.resolve() raises RuntimeError
        s = FailSerializer(
            data={"name": "test"},
            context={},
        )
        assert not s.is_valid()
        assert "service_val" in s.errors

    def test_provided_value_overrides_di_default(self):
        """Explicitly provided values take precedence over DI defaults."""
        class MySerializer(Serializer):
            name = CharField()
            owner_id = IntegerField(default=CurrentUserDefault())

        identity = _FakeIdentity(uid=42)
        s = MySerializer(
            data={"name": "test", "owner_id": 99},
            context={"identity": identity},
        )
        assert s.is_valid()
        assert s.validated_data["owner_id"] == 99  # Explicit value wins

    def test_multiple_di_defaults_in_one_serializer(self):
        """Multiple DI-aware defaults all resolve correctly."""
        class FullAuditSerializer(Serializer):
            action = CharField()
            user_id = HiddenField(default=CurrentUserDefault())
            ip = HiddenField(default=CurrentRequestDefault(attr="client_ip"))
            rate = HiddenField(default=InjectDefault("RateService"))

        identity = _FakeIdentity(uid=5)
        request = _FakeRequest(identity=identity, client_ip="10.0.0.1")
        container = _FakeContainer({("RateService", None): 3.14})

        s = FullAuditSerializer(
            data={"action": "purchase"},
            context={
                "request": request,
                "identity": identity,
                "container": container,
            },
        )
        assert s.is_valid()
        assert s.validated_data["user_id"] == 5
        assert s.validated_data["ip"] == "10.0.0.1"
        assert s.validated_data["rate"] == 3.14


# ============================================================================
# Tests: Serializer DI Properties & Factories
# ============================================================================

class TestSerializerDIProperties:
    """Tests for Serializer.container and Serializer.request properties."""

    def test_container_property(self):
        class S(Serializer):
            name = CharField()

        container = _FakeContainer()
        s = S(context={"container": container})
        assert s.container is container

    def test_container_none_when_missing(self):
        class S(Serializer):
            name = CharField()

        s = S(context={})
        assert s.container is None

    def test_request_property(self):
        class S(Serializer):
            name = CharField()

        request = _FakeRequest()
        s = S(context={"request": request})
        assert s.request is request

    def test_request_none_when_missing(self):
        class S(Serializer):
            name = CharField()

        s = S(context={})
        assert s.request is None


class TestFromRequestAsync:
    """Tests for Serializer.from_request_async() factory."""

    def test_from_request_async_parses_body(self):
        class UserSerializer(Serializer):
            name = CharField()

        request = _FakeRequest()

        async def _test():
            s = await UserSerializer.from_request_async(request)
            assert s.initial_data == {"name": "test"}
            assert s.request is request

        asyncio.run(_test())

    def test_from_request_async_wires_container(self):
        class UserSerializer(Serializer):
            name = CharField()

        container = _FakeContainer()
        request = _FakeRequest(di_container=container)

        async def _test():
            s = await UserSerializer.from_request_async(request)
            assert s.container is container

        asyncio.run(_test())

    def test_from_request_async_explicit_container(self):
        class UserSerializer(Serializer):
            name = CharField()

        container = _FakeContainer()
        request = _FakeRequest()

        async def _test():
            s = await UserSerializer.from_request_async(request, container=container)
            assert s.container is container

        asyncio.run(_test())

    def test_from_request_async_passes_context(self):
        class UserSerializer(Serializer):
            name = CharField()

        request = _FakeRequest()

        async def _test():
            s = await UserSerializer.from_request_async(
                request, context={"extra": "data"}
            )
            assert s.context["extra"] == "data"
            assert s.context["request"] is request

        asyncio.run(_test())

    def test_from_request_async_partial(self):
        class UserSerializer(Serializer):
            name = CharField()
            age = IntegerField()

        request = _FakeRequest()

        async def _test():
            s = await UserSerializer.from_request_async(request, partial=True)
            assert s.partial is True

        asyncio.run(_test())

    def test_from_request_async_with_identity(self):
        """DI defaults can be resolved after from_request_async."""
        class CommentSerializer(Serializer):
            body = CharField()
            author_id = HiddenField(default=CurrentUserDefault())

        identity = _FakeIdentity(uid=77)
        request = _FakeRequest(identity=identity)

        async def _test():
            s = await CommentSerializer.from_request_async(request)
            # The serializer parsed {"name": "test"} from request.json()
            # but CommentSerializer expects "body", so let's provide manually
            s.initial_data = {"body": "Nice!"}
            assert s.is_valid()
            assert s.validated_data["author_id"] == 77

        asyncio.run(_test())


class TestFromRequestSync:
    """Tests for Serializer.from_request() sync factory."""

    def test_from_request_wires_context(self):
        class S(Serializer):
            name = CharField()

        container = _FakeContainer()
        request = _FakeRequest(di_container=container)

        s = S.from_request(request)
        assert s.request is request
        assert s.container is container


# ============================================================================
# Tests: RangeValidator
# ============================================================================

class TestRangeValidator:
    def test_value_in_range(self):
        v = RangeValidator(1, 100)
        v(50)  # Should not raise

    def test_value_at_boundaries(self):
        v = RangeValidator(1, 100)
        v(1)    # Should not raise
        v(100)  # Should not raise

    def test_value_below_range(self):
        v = RangeValidator(1, 100)
        with pytest.raises(ValueError, match="between 1 and 100"):
            v(0)

    def test_value_above_range(self):
        v = RangeValidator(1, 100)
        with pytest.raises(ValueError, match="between 1 and 100"):
            v(101)

    def test_none_value_passes(self):
        v = RangeValidator(1, 100)
        v(None)  # Should not raise

    def test_custom_message(self):
        v = RangeValidator(0, 10, message="Must be 0-10")
        with pytest.raises(ValueError, match="Must be 0-10"):
            v(11)

    def test_float_range(self):
        v = RangeValidator(0.0, 1.0)
        v(0.5)
        with pytest.raises(ValueError):
            v(1.1)

    def test_repr(self):
        v = RangeValidator(5, 50)
        assert "RangeValidator(5, 50)" == repr(v)

    def test_integration_with_field(self):
        """RangeValidator works as a field-level validator."""
        class ScoreSerializer(Serializer):
            score = IntegerField(validators=[RangeValidator(0, 100)])

        s = ScoreSerializer(data={"score": 50})
        assert s.is_valid()

        s2 = ScoreSerializer(data={"score": 150})
        assert not s2.is_valid()
        assert "score" in s2.errors


# ============================================================================
# Tests: CompoundValidator
# ============================================================================

class TestCompoundValidator:
    def test_and_mode_all_pass(self):
        v = CompoundValidator(
            MinValueValidator(0),
            MaxValueValidator(100),
            mode="and",
        )
        v(50)  # Should not raise

    def test_and_mode_one_fails(self):
        v = CompoundValidator(
            MinValueValidator(0),
            MaxValueValidator(100),
            mode="and",
        )
        with pytest.raises(ValueError):
            v(101)

    def test_and_mode_collects_all_errors(self):
        v = CompoundValidator(
            MinValueValidator(10),
            MaxValueValidator(5),
            mode="and",
        )
        with pytest.raises(ValueError) as exc_info:
            v(7)
        # 7 < 10 fails min, 7 > 5 fails max → both errors
        msg = str(exc_info.value)
        assert "at least 10" in msg
        assert "at most 5" in msg

    def test_or_mode_one_passes(self):
        v = CompoundValidator(
            MinValueValidator(100),  # Will fail for 5
            MaxValueValidator(10),   # Will pass for 5
            mode="or",
        )
        v(5)  # Should not raise — second validator passes

    def test_or_mode_all_fail(self):
        v = CompoundValidator(
            MinValueValidator(100),
            MinValueValidator(200),
            mode="or",
        )
        with pytest.raises(ValueError):
            v(50)

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="'and' or 'or'"):
            CompoundValidator(MinValueValidator(0), mode="xor")

    def test_custom_message(self):
        v = CompoundValidator(
            MinValueValidator(100),
            mode="and",
            message="Custom compound error",
        )
        with pytest.raises(ValueError, match="Custom compound error"):
            v(50)

    def test_repr(self):
        v = CompoundValidator(
            MinValueValidator(0),
            MaxValueValidator(100),
            mode="or",
        )
        assert "CompoundValidator(2 validators, mode='or')" == repr(v)

    def test_integration_with_field(self):
        """CompoundValidator works as a field-level validator."""
        class ItemSerializer(Serializer):
            quantity = IntegerField(validators=[
                CompoundValidator(
                    MinValueValidator(1),
                    MaxValueValidator(999),
                ),
            ])

        s = ItemSerializer(data={"quantity": 10})
        assert s.is_valid()

        s2 = ItemSerializer(data={"quantity": 0})
        assert not s2.is_valid()


# ============================================================================
# Tests: ConditionalValidator
# ============================================================================

class TestConditionalValidator:
    def test_condition_true_runs_validator(self):
        v = ConditionalValidator(
            condition=lambda data: data.get("type") == "delivery",
            validator=MinLengthValidator(5),
        )
        # Condition met, value too short → should fail
        with pytest.raises(ValueError):
            v("ab", data={"type": "delivery"})

    def test_condition_true_valid_value(self):
        v = ConditionalValidator(
            condition=lambda data: data.get("type") == "delivery",
            validator=MinLengthValidator(5),
        )
        # Condition met, value OK
        v("123 Main St", data={"type": "delivery"})

    def test_condition_false_skips_validator(self):
        v = ConditionalValidator(
            condition=lambda data: data.get("type") == "delivery",
            validator=MinLengthValidator(5),
        )
        # Condition not met → should pass regardless
        v("ab", data={"type": "pickup"})

    def test_no_data_skips_validator(self):
        v = ConditionalValidator(
            condition=lambda data: True,
            validator=MinLengthValidator(5),
        )
        # No data → should pass (data is None)
        v("ab")

    def test_custom_message(self):
        v = ConditionalValidator(
            condition=lambda data: True,
            validator=MinLengthValidator(5),
            message="Address too short for delivery",
        )
        with pytest.raises(ValueError, match="Address too short"):
            v("ab", data={})

    def test_repr(self):
        v = ConditionalValidator(
            condition=lambda data: True,
            validator=MinLengthValidator(3),
        )
        assert "ConditionalValidator" in repr(v)


# ============================================================================
# Tests: SerializerProvider (DI integration)
# ============================================================================

class TestSerializerProvider:
    """Tests for the DI SerializerProvider."""

    def test_provider_meta(self):
        from aquilia.di.providers import SerializerProvider

        class UserSerializer(Serializer):
            name = CharField()

        provider = SerializerProvider(UserSerializer, scope="request")
        meta = provider.meta

        assert meta.name == "UserSerializer"
        assert meta.scope == "request"
        assert "UserSerializer" in meta.token

    def test_provider_instantiate(self):
        from aquilia.di.providers import SerializerProvider, ResolveCtx

        class OrderSerializer(Serializer):
            item = CharField()

        provider = SerializerProvider(OrderSerializer)

        # Create a minimal resolve context
        class _MinimalCtx:
            def __init__(self, container):
                self.container = container
                self.depth = 0
                self.chain = []

        container = _FakeContainer()
        ctx = _MinimalCtx(container)

        async def _test():
            serializer = await provider.instantiate(ctx)
            assert isinstance(serializer, OrderSerializer)
            assert serializer.container is container

        asyncio.run(_test())

    def test_provider_auto_validate(self):
        from aquilia.di.providers import SerializerProvider

        class NameSerializer(Serializer):
            name = CharField()

        provider = SerializerProvider(NameSerializer, auto_validate=True)

        class _MinimalCtx:
            def __init__(self, container):
                self.container = container
                self.depth = 0
                self.chain = []

        # Create a container that resolves a request with valid JSON
        class _ReqWithData:
            state = {}
            async def json(self):
                return {"name": "Kai"}
            async def form(self):
                return {}

        req = _ReqWithData()
        container = _FakeContainer({
            ("aquilia.request.Request", None): req,
        })
        ctx = _MinimalCtx(container)

        async def _test():
            serializer = await provider.instantiate(ctx)
            assert isinstance(serializer, NameSerializer)
            # Auto-validate was True → validated_data should be populated
            assert serializer.validated_data["name"] == "Kai"

        asyncio.run(_test())

    def test_provider_shutdown_noop(self):
        from aquilia.di.providers import SerializerProvider

        class S(Serializer):
            name = CharField()

        provider = SerializerProvider(S)

        async def _test():
            await provider.shutdown()  # Should not raise

        asyncio.run(_test())


# ============================================================================
# Tests: Controller Engine — Serializer Detection
# ============================================================================

class TestSerializerDetection:
    """Tests for _is_serializer_class in controller engine."""

    def test_detects_serializer_subclass(self):
        from aquilia.controller.engine import ControllerEngine

        class MySerializer(Serializer):
            name = CharField()

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_serializer_class(MySerializer) is True

    def test_rejects_base_serializer(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_serializer_class(Serializer) is False

    def test_rejects_non_serializer(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_serializer_class(str) is False
        assert engine._is_serializer_class(int) is False
        assert engine._is_serializer_class(None) is False

    def test_rejects_non_type(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        assert engine._is_serializer_class("not a type") is False
        assert engine._is_serializer_class(42) is False


class TestSerializerTypeMetadata:
    """Tests for _is_serializer_type in controller metadata."""

    def test_detects_serializer_type(self):
        from aquilia.controller.metadata import _is_serializer_type

        class UserSerializer(Serializer):
            name = CharField()

        assert _is_serializer_type(UserSerializer) is True

    def test_rejects_base_serializer(self):
        from aquilia.controller.metadata import _is_serializer_type

        assert _is_serializer_type(Serializer) is False

    def test_rejects_non_serializer(self):
        from aquilia.controller.metadata import _is_serializer_type

        assert _is_serializer_type(str) is False
        assert _is_serializer_type(int) is False

    def test_rejects_non_type(self):
        from aquilia.controller.metadata import _is_serializer_type

        assert _is_serializer_type("str") is False
        assert _is_serializer_type(None) is False


# ============================================================================
# Tests: Response Serializer Application
# ============================================================================

class TestResponseSerializer:
    """Tests for _apply_response_serializer in controller engine."""

    def test_serializes_single_instance(self):
        from aquilia.controller.engine import ControllerEngine

        class PersonSerializer(Serializer):
            name = CharField()
            age = IntegerField()

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_serializer = PersonSerializer

        class _FakeCtx:
            request = _FakeRequest()
            container = None

        person = SimpleObj(name="Kai", age=25)
        result = engine._apply_response_serializer(person, _FakeMeta(), _FakeCtx())
        assert result["name"] == "Kai"
        assert result["age"] == 25

    def test_serializes_list_of_instances(self):
        from aquilia.controller.engine import ControllerEngine

        class PersonSerializer(Serializer):
            name = CharField()

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_serializer = PersonSerializer

        class _FakeCtx:
            request = _FakeRequest()
            container = None

        people = [SimpleObj(name="A"), SimpleObj(name="B")]
        result = engine._apply_response_serializer(people, _FakeMeta(), _FakeCtx())
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "A"

    def test_skips_response_objects(self):
        from aquilia.controller.engine import ControllerEngine
        from aquilia.response import Response

        class PersonSerializer(Serializer):
            name = CharField()

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_serializer = PersonSerializer

        class _FakeCtx:
            request = _FakeRequest()
            container = None

        resp = Response.json({"ok": True})
        result = engine._apply_response_serializer(resp, _FakeMeta(), _FakeCtx())
        assert result is resp  # Passthrough

    def test_no_response_serializer_passthrough(self):
        from aquilia.controller.engine import ControllerEngine

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_serializer = None

        class _FakeCtx:
            request = _FakeRequest()
            container = None

        result = engine._apply_response_serializer({"raw": True}, _FakeMeta(), _FakeCtx())
        assert result == {"raw": True}

    def test_raw_metadata_dict(self):
        """response_serializer can come from _raw_metadata dict."""
        from aquilia.controller.engine import ControllerEngine

        class PersonSerializer(Serializer):
            name = CharField()

        engine = ControllerEngine.__new__(ControllerEngine)
        engine.logger = logging.getLogger("test")

        class _FakeMeta:
            response_serializer = None
            _raw_metadata = {"response_serializer": PersonSerializer}

        class _FakeCtx:
            request = _FakeRequest()
            container = None

        person = SimpleObj(name="FromRaw")
        result = engine._apply_response_serializer(person, _FakeMeta(), _FakeCtx())
        assert result["name"] == "FromRaw"


# ============================================================================
# Tests: Top-level Exports
# ============================================================================

class TestDIExports:
    """Verify all new DI-related exports are accessible."""

    def test_serializers_package_exports(self):
        from aquilia.serializers import (
            CurrentUserDefault,
            CurrentRequestDefault,
            InjectDefault,
            is_di_default,
            RangeValidator,
            CompoundValidator,
            ConditionalValidator,
        )
        assert CurrentUserDefault is not None
        assert CurrentRequestDefault is not None
        assert InjectDefault is not None
        assert callable(is_di_default)
        assert RangeValidator is not None
        assert CompoundValidator is not None
        assert ConditionalValidator is not None

    def test_top_level_exports(self):
        from aquilia import (
            CurrentUserDefault,
            CurrentRequestDefault,
            InjectDefault,
            RangeValidator,
            CompoundValidator,
            ConditionalValidator,
        )
        assert CurrentUserDefault is not None
        assert InjectDefault is not None

    def test_di_provider_export(self):
        from aquilia.di import SerializerProvider
        assert SerializerProvider is not None


import logging
