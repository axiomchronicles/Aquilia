"""
Tests for the new pure-Python ORM model system.

Covers:
- Field types and validation
- Model metaclass (auto-PK, Meta parsing, registration)
- ModelRegistry
- Q query builder
- Model CRUD (create, get, save, delete)
- Relationships (ForeignKey, ManyToMany)
- SQL generation (CREATE TABLE, INDEX, M2M)
- Migration generation from Python models
- Model fingerprinting / to_dict
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aquilia.models.base import Model, ModelMeta, ModelRegistry, Options, Q
from aquilia.models.fields import (
    # Base
    Field,
    FieldValidationError,
    Index,
    UniqueConstraint,
    UNSET,
    # Numeric
    AutoField,
    BigAutoField,
    IntegerField,
    BigIntegerField,
    SmallIntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    FloatField,
    DecimalField,
    # Text
    CharField,
    TextField,
    SlugField,
    EmailField,
    URLField,
    UUIDField,
    FilePathField,
    # Date/Time
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    # Boolean
    BooleanField,
    # Binary/Special
    BinaryField,
    JSONField,
    # Relationships
    ForeignKey,
    OneToOneField,
    ManyToManyField,
    RelationField,
    # IP
    GenericIPAddressField,
    InetAddressField,
    # File
    FileField,
    ImageField,
    # PostgreSQL
    ArrayField,
    HStoreField,
    RangeField,
    IntegerRangeField,
    BigIntegerRangeField,
    DecimalRangeField,
    DateRangeField,
    DateTimeRangeField,
    CICharField,
    CIEmailField,
    CITextField,
    # Meta
    GeneratedField,
    OrderWrt,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset ModelRegistry between tests to avoid cross-contamination."""
    old_models = ModelRegistry._models.copy()
    old_db = ModelRegistry._db
    yield
    ModelRegistry._models = old_models
    ModelRegistry._db = old_db


def fresh_model(name, bases=(Model,), attrs=None, meta_attrs=None):
    """
    Create a fresh Model subclass dynamically for testing.
    Uses unique names to avoid metaclass conflicts.
    """
    attrs = attrs or {}
    if meta_attrs:
        meta_cls = type("Meta", (), meta_attrs)
        attrs["Meta"] = meta_cls
    # Make sure model name is unique
    unique_name = f"{name}_{uuid.uuid4().hex[:8]}"
    cls = type(unique_name, bases, attrs)
    return cls


# ============================================================================
# Field Type Tests
# ============================================================================


class TestFieldBase:
    """Test Field base class."""

    def test_field_default(self):
        f = Field(default="hello")
        assert f.default == "hello"

    def test_field_null(self):
        f = Field(null=True)
        assert f.null is True

    def test_field_null_default_false(self):
        f = Field()
        assert f.null is False

    def test_field_unique(self):
        f = Field(unique=True)
        assert f.unique is True

    def test_field_db_index(self):
        f = Field(db_index=True)
        assert f.db_index is True

    def test_field_primary_key(self):
        f = Field(primary_key=True)
        assert f.primary_key is True

    def test_field_choices(self):
        f = Field(choices=[("a", "Apple"), ("b", "Banana")])
        assert f.choices == [("a", "Apple"), ("b", "Banana")]

    def test_field_column(self):
        f = Field(db_column="custom_col")
        assert f.db_column == "custom_col"
        assert f.column_name == "custom_col"

    def test_field_contribute_to_class(self):
        f = Field()
        f.__set_name__(None, "my_field")
        assert f.name == "my_field"
        assert f.column_name == "my_field"

    def test_field_contribute_to_class_custom_column(self):
        f = Field(db_column="my_col")
        f.__set_name__(None, "my_field")
        assert f.attr_name == "my_field"
        assert f.column_name == "my_col"

    def test_field_deconstruct(self):
        f = Field(null=True, unique=True, default="x")
        f.__set_name__(None, "test")
        d = f.deconstruct()
        assert d["type"] == "Field"
        assert d["null"] is True
        assert d["unique"] is True
        assert d["default"] == "x"


class TestNumericFields:
    """Test numeric field types."""

    def test_auto_field(self):
        f = AutoField()
        assert f.primary_key is True
        assert f.sql_type() == "INTEGER"

    def test_big_auto_field(self):
        f = BigAutoField()
        assert f.primary_key is True
        assert f.sql_type() == "INTEGER"  # SQLite dialect
        assert f.sql_type("postgresql") == "BIGSERIAL"

    def test_integer_field_validate(self):
        f = IntegerField()
        assert f.validate(42) == 42
        assert f.validate("42") == 42

    def test_integer_field_validate_invalid(self):
        f = IntegerField()
        with pytest.raises(FieldValidationError):
            f.validate("not a number")

    def test_big_integer_field(self):
        f = BigIntegerField()
        assert f.sql_type("postgresql") == "BIGINT"
        assert f.validate(2**40) == 2**40

    def test_small_integer_field(self):
        f = SmallIntegerField()
        assert f.sql_type("postgresql") == "SMALLINT"
        assert f.sql_type() == "INTEGER"  # SQLite

    def test_positive_integer_field_valid(self):
        f = PositiveIntegerField()
        f.validate(5)

    def test_positive_integer_field_invalid(self):
        f = PositiveIntegerField()
        with pytest.raises(FieldValidationError):
            f.validate(-1)

    def test_positive_small_integer_field(self):
        f = PositiveSmallIntegerField()
        assert f.sql_type("postgresql") == "SMALLINT"
        f.validate(100)
        with pytest.raises(FieldValidationError):
            f.validate(-5)

    def test_float_field(self):
        f = FloatField()
        assert f.sql_type() == "REAL"
        assert f.validate(3.14) == pytest.approx(3.14)

    def test_decimal_field(self):
        f = DecimalField(max_digits=10, decimal_places=2)
        sql = f.sql_type()
        assert "DECIMAL" in sql or "NUMERIC" in sql or "TEXT" in sql
        result = f.validate(decimal.Decimal("99.99"))
        assert result == decimal.Decimal("99.99")

    def test_decimal_field_validate_digits(self):
        f = DecimalField(max_digits=5, decimal_places=2)
        f.validate(decimal.Decimal("999.99"))
        with pytest.raises(FieldValidationError):
            f.validate(decimal.Decimal("9999.99"))


class TestTextFields:
    """Test text field types."""

    def test_char_field(self):
        f = CharField(max_length=100)
        assert f.sql_type() == "VARCHAR(100)"
        assert f.validate("hello") == "hello"

    def test_char_field_max_length_validation(self):
        f = CharField(max_length=5)
        f.validate("hello")
        with pytest.raises(FieldValidationError):
            f.validate("hello world")

    def test_text_field(self):
        f = TextField()
        assert f.sql_type() == "TEXT"

    def test_slug_field(self):
        f = SlugField()
        assert f.sql_type() == "VARCHAR(50)"
        f.validate("my-slug-123")
        with pytest.raises(FieldValidationError):
            f.validate("Invalid Slug!")

    def test_email_field_valid(self):
        f = EmailField()
        f.validate("user@example.com")

    def test_email_field_invalid(self):
        f = EmailField()
        with pytest.raises(FieldValidationError):
            f.validate("not-an-email")

    def test_url_field_valid(self):
        f = URLField()
        f.validate("https://example.com")
        f.validate("http://localhost:8080/path")

    def test_url_field_invalid(self):
        f = URLField()
        with pytest.raises(FieldValidationError):
            f.validate("not a url")

    def test_uuid_field(self):
        f = UUIDField()
        assert f.sql_type() == "VARCHAR(36)"
        test_uuid = uuid.uuid4()
        result = f.to_python(str(test_uuid))
        assert isinstance(result, uuid.UUID)
        assert result == test_uuid

    def test_uuid_field_auto(self):
        f = UUIDField(auto=True)
        assert f.default is not None
        val = f.default()
        assert isinstance(val, uuid.UUID)

    def test_file_path_field(self):
        f = FilePathField()
        assert "VARCHAR" in f.sql_type()


class TestDateTimeFields:
    """Test date/time field types."""

    def test_date_field(self):
        f = DateField()
        assert f.sql_type() == "DATE"
        today = datetime.date.today()
        assert f.to_python(today) == today

    def test_date_field_from_string(self):
        f = DateField()
        result = f.to_python("2024-01-15")
        assert isinstance(result, datetime.date)
        assert result.year == 2024

    def test_time_field(self):
        f = TimeField()
        assert f.sql_type() == "TIME"

    def test_datetime_field(self):
        f = DateTimeField()
        assert f.sql_type() == "TIMESTAMP"

    def test_datetime_auto_now(self):
        f = DateTimeField(auto_now=True)
        assert f.auto_now is True

    def test_datetime_auto_now_add(self):
        f = DateTimeField(auto_now_add=True)
        assert f.auto_now_add is True

    def test_duration_field(self):
        f = DurationField()
        assert f.sql_type() == "INTEGER"  # SQLite stores as microseconds int
        td = datetime.timedelta(hours=2, minutes=30)
        db_val = f.to_db(td)
        assert isinstance(db_val, (int, float))
        round_trip = f.to_python(db_val)
        assert round_trip == td


class TestBooleanField:
    """Test boolean field."""

    def test_boolean_field(self):
        f = BooleanField()
        assert f.sql_type() == "INTEGER"

    def test_boolean_to_python(self):
        f = BooleanField()
        assert f.to_python(1) is True
        assert f.to_python(0) is False
        assert f.to_python(True) is True
        assert f.to_python(False) is False

    def test_boolean_to_db(self):
        f = BooleanField()
        assert f.to_db(True) == 1
        assert f.to_db(False) == 0


class TestBinaryAndJSONFields:
    """Test binary and JSON fields."""

    def test_binary_field(self):
        f = BinaryField()
        assert f.sql_type() == "BLOB"

    def test_json_field(self):
        f = JSONField()
        assert f.sql_type() == "TEXT"

    def test_json_field_to_db(self):
        f = JSONField()
        result = f.to_db({"key": "value"})
        assert isinstance(result, str)
        assert '"key"' in result

    def test_json_field_to_python(self):
        f = JSONField()
        result = f.to_python('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_field_already_parsed(self):
        f = JSONField()
        data = {"key": "value"}
        assert f.to_python(data) is data


class TestRelationFields:
    """Test relationship fields."""

    def test_foreign_key(self):
        fk = ForeignKey("User", on_delete="CASCADE")
        assert fk.to == "User"
        assert fk.on_delete == "CASCADE"

    def test_foreign_key_column_name(self):
        fk = ForeignKey("User", on_delete="CASCADE")
        fk.__set_name__(None, "author")
        assert fk.column_name == "author_id"

    def test_foreign_key_sql_type(self):
        fk = ForeignKey("User", on_delete="CASCADE")
        assert fk.sql_type() == "INTEGER"

    def test_one_to_one_field(self):
        oto = OneToOneField("Profile", on_delete="CASCADE")
        assert oto.to == "Profile"
        assert oto.unique is True

    def test_many_to_many_field(self):
        m2m = ManyToManyField("Tag")
        assert m2m.to == "Tag"

    def test_many_to_many_custom_through(self):
        m2m = ManyToManyField("Role", through="user_roles")
        assert m2m.through == "user_roles"


class TestIPFields:
    """Test IP address fields."""

    def test_generic_ip_address_field(self):
        f = GenericIPAddressField()
        assert "VARCHAR" in f.sql_type()
        f.validate("192.168.1.1")
        f.validate("::1")

    def test_generic_ip_address_field_invalid(self):
        f = GenericIPAddressField()
        with pytest.raises(FieldValidationError):
            f.validate("not-an-ip")

    def test_inet_field(self):
        f = InetAddressField()
        assert "VARCHAR" in f.sql_type()


class TestFileFields:
    """Test file/image fields."""

    def test_file_field(self):
        f = FileField(upload_to="uploads/")
        assert f.upload_to == "uploads/"
        assert "VARCHAR" in f.sql_type()

    def test_image_field(self):
        f = ImageField(upload_to="images/")
        assert f.upload_to == "images/"


class TestPostgreSQLFields:
    """Test PostgreSQL-specific fields."""

    def test_array_field(self):
        f = ArrayField(base_field=IntegerField())
        assert "TEXT" in f.sql_type()

    def test_hstore_field(self):
        f = HStoreField()
        assert f.sql_type() == "TEXT"

    def test_range_field(self):
        f = RangeField()
        f.validate([1, 10])
        with pytest.raises(FieldValidationError):
            f.validate("not a range")

    def test_integer_range_field(self):
        f = IntegerRangeField()
        assert f.sql_type("postgresql") == "INT4RANGE"
        assert f._field_type == "INT4RANGE"

    def test_big_integer_range_field(self):
        f = BigIntegerRangeField()
        assert f.sql_type("postgresql") == "INT8RANGE"
        assert f._field_type == "INT8RANGE"

    def test_decimal_range_field(self):
        f = DecimalRangeField()
        assert f.sql_type("postgresql") == "NUMRANGE"
        assert f._field_type == "NUMRANGE"

    def test_date_range_field(self):
        f = DateRangeField()
        assert f.sql_type("postgresql") == "DATERANGE"
        assert f._field_type == "DATERANGE"

    def test_datetime_range_field(self):
        f = DateTimeRangeField()
        assert f.sql_type("postgresql") == "TSTZRANGE"
        assert f._field_type == "TSTZRANGE"

    def test_ci_char_field(self):
        f = CICharField(max_length=100)
        assert f.sql_type() == "VARCHAR(100)"

    def test_ci_email_field(self):
        f = CIEmailField()
        f.validate("User@Example.COM")

    def test_ci_text_field(self):
        f = CITextField()
        assert f.sql_type() == "TEXT"


class TestMetaFields:
    """Test meta/special fields."""

    def test_generated_field(self):
        f = GeneratedField(expression="col1 + col2", output_field=IntegerField())
        assert f.expression == "col1 + col2"

    def test_order_wrt(self):
        f = OrderWrt()
        assert f.sql_type() == "INTEGER"


class TestIndexAndConstraints:
    """Test Index and UniqueConstraint."""

    def test_index(self):
        idx = Index(fields=["name", "email"])
        assert idx.fields == ["name", "email"]
        assert idx.unique is False

    def test_index_unique(self):
        idx = Index(fields=["email"], unique=True, name="idx_email")
        assert idx.unique is True
        assert idx.name == "idx_email"

    def test_unique_constraint(self):
        uc = UniqueConstraint(fields=["first_name", "last_name"], name="uniq_name")
        assert uc.fields == ["first_name", "last_name"]
        assert uc.name == "uniq_name"


# ============================================================================
# Model Metaclass / Registration Tests
# ============================================================================


class TestModelMeta:
    """Test ModelMeta metaclass behavior."""

    def test_auto_pk_injection(self):
        """Model without explicit PK gets BigAutoField."""
        M = fresh_model("AutoPKModel", attrs={
            "name": CharField(max_length=100),
        })
        assert hasattr(M, "id")
        assert isinstance(M._fields["id"], BigAutoField)

    def test_explicit_pk_no_injection(self):
        """Model with explicit PK doesn't get auto-injected one."""
        M = fresh_model("ExplicitPKModel", attrs={
            "uid": AutoField(),
            "name": CharField(max_length=100),
        })
        assert "uid" in M._fields
        # Should not have 'id' injected
        pk_fields = [f for f in M._fields.values() if f.primary_key]
        assert len(pk_fields) == 1
        assert pk_fields[0] is M._fields["uid"]

    def test_field_names_set(self):
        """Field names are set by contribute_to_class."""
        M = fresh_model("FieldNameModel", attrs={
            "title": CharField(max_length=200),
            "count": IntegerField(default=0),
        })
        assert M._fields["title"].name == "title"
        assert M._fields["count"].name == "count"

    def test_meta_table_name(self):
        """Meta.table sets the table name."""
        M = fresh_model("CustomTableModel", attrs={
            "x": IntegerField(),
        }, meta_attrs={"table": "my_custom_table"})
        assert M._meta.table_name == "my_custom_table"

    def test_meta_auto_table_name(self):
        """Without Meta.table_name, uses lowercase class name."""
        M = fresh_model("MyModel", attrs={
            "x": IntegerField(),
        })
        # The auto name is the lowercased unique class name
        assert M._meta.table_name == M.__name__.lower()

    def test_meta_ordering(self):
        """Meta.ordering is parsed."""
        M = fresh_model("OrderedModel", attrs={
            "name": CharField(max_length=100),
        }, meta_attrs={"ordering": ["-name"]})
        assert M._meta.ordering == ["-name"]

    def test_meta_abstract(self):
        """Abstract models are not registered."""
        initial_count = len(ModelRegistry._models)
        M = fresh_model("AbstractBase", attrs={
            "created": DateTimeField(auto_now_add=True),
        }, meta_attrs={"abstract": True})
        assert M._meta.abstract is True
        assert len(ModelRegistry._models) == initial_count

    def test_model_registered(self):
        """Non-abstract models are registered in ModelRegistry."""
        M = fresh_model("RegisteredModel", attrs={
            "data": TextField(),
        })
        assert M.__name__ in ModelRegistry._models

    def test_meta_indexes(self):
        """Meta.indexes are parsed."""
        M = fresh_model("IndexedModel", attrs={
            "name": CharField(max_length=100),
            "email": EmailField(),
        }, meta_attrs={
            "indexes": [Index(fields=["name", "email"])]
        })
        assert len(M._meta.indexes) == 1

    def test_meta_constraints(self):
        """Meta.constraints are parsed."""
        M = fresh_model("ConstrainedModel", attrs={
            "first": CharField(max_length=50),
            "last": CharField(max_length=50),
        }, meta_attrs={
            "constraints": [UniqueConstraint(fields=["first", "last"], name="uniq_full_name")]
        })
        assert len(M._meta.constraints) == 1


# ============================================================================
# ModelRegistry Tests
# ============================================================================


class TestModelRegistry:
    """Test ModelRegistry class methods."""

    def test_registry_has_models(self):
        M = fresh_model("RegModel", attrs={"x": IntegerField()})
        assert M.__name__ in ModelRegistry._models

    def test_registry_set_database(self):
        db = MagicMock()
        ModelRegistry.set_database(db)
        assert ModelRegistry._db is db
        # Restore
        ModelRegistry._db = None

    def test_registry_reset(self):
        M = fresh_model("ResetModel", attrs={"x": IntegerField()})
        name = M.__name__
        assert name in ModelRegistry._models
        ModelRegistry.reset()
        assert len(ModelRegistry._models) == 0

    def test_registry_resolve_relations(self):
        """ForeignKey string references are stored correctly."""
        M1 = fresh_model("Author", attrs={"name": CharField(max_length=100)})
        M2 = fresh_model("Book", attrs={
            "title": CharField(max_length=200),
            "author": ForeignKey(M1.__name__, on_delete="CASCADE"),
        })
        # FK should reference the model by name string
        fk = M2._fields["author"]
        assert fk.to == M1.__name__


# ============================================================================
# Q Query Builder Tests
# ============================================================================


class TestQBuilder:
    """Test Q query builder."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        db = MagicMock()
        ModelRegistry.set_database(db)
        yield
        ModelRegistry._db = None

    def _q(self, M):
        """Create a Q instance for model M using a mock DB."""
        return Q(M._table_name, M, ModelRegistry._db)

    def test_q_creation(self):
        M = fresh_model("QModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M)
        assert q._model_cls is M

    def test_q_where(self):
        M = fresh_model("QWhereModel", attrs={"age": IntegerField()})
        q = self._q(M).where("age > ?", 18)
        assert len(q._wheres) == 1
        assert q._params == [18]

    def test_q_filter_eq(self):
        M = fresh_model("QFilterModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M).filter(name="Alice")
        assert len(q._wheres) == 1
        assert "name" in q._wheres[0]

    def test_q_filter_gt(self):
        M = fresh_model("QFilterGtModel", attrs={"age": IntegerField()})
        q = self._q(M).filter(age__gt=18)
        assert '"age" > ?' in q._wheres[0]
        assert q._params == [18]

    def test_q_filter_lt(self):
        M = fresh_model("QFilterLtModel", attrs={"score": FloatField()})
        q = self._q(M).filter(score__lt=50.0)
        assert '"score" < ?' in q._wheres[0]

    def test_q_filter_gte(self):
        M = fresh_model("QFilterGteModel", attrs={"x": IntegerField()})
        q = self._q(M).filter(x__gte=10)
        assert '"x" >= ?' in q._wheres[0]

    def test_q_filter_lte(self):
        M = fresh_model("QFilterLteModel", attrs={"x": IntegerField()})
        q = self._q(M).filter(x__lte=10)
        assert '"x" <= ?' in q._wheres[0]

    def test_q_filter_contains(self):
        M = fresh_model("QContainsModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M).filter(name__contains="ali")
        assert "LIKE" in q._wheres[0]
        assert q._params == ["%ali%"]

    def test_q_filter_startswith(self):
        M = fresh_model("QStartModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M).filter(name__startswith="A")
        assert q._params == ["A%"]

    def test_q_filter_endswith(self):
        M = fresh_model("QEndModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M).filter(name__endswith="z")
        assert q._params == ["%z"]

    def test_q_filter_in(self):
        M = fresh_model("QInModel", attrs={"status": CharField(max_length=20)})
        q = self._q(M).filter(status__in=["active", "pending"])
        assert "IN" in q._wheres[0]

    def test_q_filter_isnull(self):
        M = fresh_model("QIsNullModel", attrs={"email": CharField(max_length=100, null=True)})
        q = self._q(M).filter(email__isnull=True)
        assert "IS NULL" in q._wheres[0]

    def test_q_filter_isnull_false(self):
        M = fresh_model("QNotNullModel", attrs={"email": CharField(max_length=100, null=True)})
        q = self._q(M).filter(email__isnull=False)
        assert "IS NOT NULL" in q._wheres[0]

    def test_q_exclude(self):
        M = fresh_model("QExcludeModel", attrs={"status": CharField(max_length=20)})
        q = self._q(M).exclude(status="deleted")
        # exclude now wraps with NOT() via _build_filter_clause
        assert "NOT" in q._wheres[0] and '"status" = ?' in q._wheres[0]

    def test_q_order(self):
        M = fresh_model("QOrderModel", attrs={"name": CharField(max_length=100)})
        q = self._q(M).order("name")
        assert q._order_clauses == ['"name" ASC']

    def test_q_order_desc(self):
        M = fresh_model("QOrderDescModel", attrs={"created": DateTimeField()})
        q = self._q(M).order("-created")
        assert q._order_clauses == ['"created" DESC']

    def test_q_limit(self):
        M = fresh_model("QLimitModel", attrs={"x": IntegerField()})
        q = self._q(M).limit(10)
        assert q._limit_val == 10

    def test_q_offset(self):
        M = fresh_model("QOffsetModel", attrs={"x": IntegerField()})
        q = self._q(M).offset(20)
        assert q._offset_val == 20

    def test_q_chain(self):
        M = fresh_model("QChainModel", attrs={
            "name": CharField(max_length=100),
            "age": IntegerField(),
        })
        q = self._q(M).filter(age__gt=18).order("-name").limit(5).offset(10)
        assert len(q._wheres) == 1
        assert q._order_clauses == ['"name" DESC']
        assert q._limit_val == 5
        assert q._offset_val == 10


# ============================================================================
# SQL Generation Tests
# ============================================================================


class TestSQLGeneration:
    """Test CREATE TABLE SQL generation."""

    def test_basic_table_sql(self):
        M = fresh_model("BasicSQL", attrs={
            "name": CharField(max_length=100),
            "age": IntegerField(default=0),
        })
        sql = M.generate_create_table_sql()
        assert "CREATE TABLE" in sql
        assert M._meta.table_name in sql
        assert "name" in sql
        assert "VARCHAR(100)" in sql
        assert "age" in sql
        assert "INTEGER" in sql

    def test_pk_in_sql(self):
        M = fresh_model("PKInSQL", attrs={
            "name": CharField(max_length=50),
        })
        sql = M.generate_create_table_sql()
        assert "PRIMARY KEY" in sql

    def test_unique_in_sql(self):
        M = fresh_model("UniqueSQL", attrs={
            "email": EmailField(unique=True),
        })
        sql = M.generate_create_table_sql()
        assert "UNIQUE" in sql

    def test_not_null_in_sql(self):
        M = fresh_model("NotNullSQL", attrs={
            "name": CharField(max_length=100),
        })
        sql = M.generate_create_table_sql()
        assert "NOT NULL" in sql

    def test_nullable_in_sql(self):
        M = fresh_model("NullableSQL", attrs={
            "bio": TextField(null=True),
        })
        sql = M.generate_create_table_sql()
        # bio should NOT have NOT NULL
        lines = sql.split("\n")
        bio_line = [l for l in lines if "bio" in l.lower()][0]
        assert "NOT NULL" not in bio_line

    def test_default_in_sql(self):
        M = fresh_model("DefaultSQL", attrs={
            "active": BooleanField(default=True),
        })
        sql = M.generate_create_table_sql()
        assert "DEFAULT" in sql

    def test_foreign_key_sql(self):
        M1 = fresh_model("FKParent", attrs={
            "name": CharField(max_length=100),
        })
        M2 = fresh_model("FKChild", attrs={
            "parent": ForeignKey(M1.__name__, on_delete="CASCADE"),
        })
        sql = M2.generate_create_table_sql()
        assert "parent_id" in sql
        assert "REFERENCES" in sql
        assert "CASCADE" in sql

    def test_index_sql_generation(self):
        M = fresh_model("IndexSQL", attrs={
            "name": CharField(max_length=100, db_index=True),
        })
        indexes = M.generate_index_sql()
        assert len(indexes) >= 1
        assert any("INDEX" in idx for idx in indexes)

    def test_m2m_junction_sql(self):
        M1 = fresh_model("M2MLeft", attrs={
            "name": CharField(max_length=100),
        })
        M2 = fresh_model("M2MRight", attrs={
            "label": CharField(max_length=50),
            "lefts": ManyToManyField(M1.__name__),
        })
        m2m_sqls = M2.generate_m2m_sql()
        assert len(m2m_sqls) >= 1
        assert any("CREATE TABLE" in s for s in m2m_sqls)


# ============================================================================
# Model Instance Tests
# ============================================================================


class TestModelInstance:
    """Test Model instance creation and methods."""

    def test_create_instance(self):
        M = fresh_model("InstanceModel", attrs={
            "name": CharField(max_length=100),
            "age": IntegerField(default=0),
        })
        obj = M(name="Alice", age=30)
        assert obj.name == "Alice"
        assert obj.age == 30

    def test_to_dict(self):
        M = fresh_model("DictModel", attrs={
            "name": CharField(max_length=100),
            "score": FloatField(default=0.0),
        })
        obj = M(name="Bob", score=95.5)
        d = obj.to_dict()
        assert d["name"] == "Bob"
        assert d["score"] == 95.5

    def test_repr(self):
        M = fresh_model("ReprModel", attrs={
            "name": CharField(max_length=100),
        })
        obj = M(name="Charlie")
        r = repr(obj)
        assert M.__name__ in r

    def test_fingerprint(self):
        M = fresh_model("FingerprintModel", attrs={
            "name": CharField(max_length=100),
        })
        fp = M.fingerprint()
        assert isinstance(fp, str)
        assert len(fp) > 0

    def test_default_values(self):
        M = fresh_model("DefaultValModel", attrs={
            "name": CharField(max_length=100, default="unnamed"),
            "active": BooleanField(default=True),
        })
        obj = M()
        assert obj.name == "unnamed"
        assert obj.active is True


# ============================================================================
# Model CRUD Tests (with mocked database)
# ============================================================================


class TestModelCRUD:
    """Test Model CRUD operations with mocked database."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        ModelRegistry.set_database(db)
        yield db
        ModelRegistry._db = None

    @pytest.mark.asyncio
    async def test_create(self, mock_db):
        M = fresh_model("CreateModel", attrs={
            "name": CharField(max_length=100),
        })
        cursor = AsyncMock()
        cursor.lastrowid = 1
        mock_db.execute.return_value = cursor
        
        obj = await M.create(name="Alice")
        assert obj.name == "Alice"
        assert obj.id == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get(self, mock_db):
        M = fresh_model("GetModel", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_one.return_value = {"id": 1, "name": "Bob"}
        
        obj = await M.get(pk=1)
        assert obj is not None
        assert obj.name == "Bob"

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_db):
        M = fresh_model("GetNotFoundModel", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_one.return_value = None
        
        obj = await M.get(pk=999)
        assert obj is None

    @pytest.mark.asyncio
    async def test_all(self, mock_db):
        M = fresh_model("AllModel", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_all.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        
        results = await M.all()
        assert len(results) == 2
        assert results[0].name == "Alice"
        assert results[1].name == "Bob"

    @pytest.mark.asyncio
    async def test_count(self, mock_db):
        M = fresh_model("CountModel", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_val.return_value = 42
        
        cnt = await M.count()
        assert cnt == 42

    @pytest.mark.asyncio
    async def test_save_new(self, mock_db):
        M = fresh_model("SaveNewModel", attrs={
            "name": CharField(max_length=100),
        })
        obj = M(name="Charlie")
        cursor = AsyncMock()
        cursor.lastrowid = 5
        mock_db.execute.return_value = cursor
        
        await obj.save()
        assert obj.id == 5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_existing(self, mock_db):
        M = fresh_model("SaveExModel", attrs={
            "name": CharField(max_length=100),
        })
        obj = M(id=1, name="Updated")
        
        await obj.save()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        assert "UPDATE" in sql

    @pytest.mark.asyncio
    async def test_delete_instance(self, mock_db):
        M = fresh_model("DeleteModel", attrs={
            "name": CharField(max_length=100),
        })
        obj = M(id=1, name="ToDelete")
        
        await obj.delete_instance()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        assert "DELETE" in sql

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, mock_db):
        M = fresh_model("GetOrCreate1", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_one.return_value = {"id": 1, "name": "Exists"}
        
        obj, created = await M.get_or_create(name="Exists")
        assert obj.name == "Exists"
        assert created is False

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, mock_db):
        M = fresh_model("GetOrCreate2", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_one.side_effect = [None, {"id": 2, "name": "New"}]
        cursor = AsyncMock()
        cursor.lastrowid = 2
        mock_db.execute.return_value = cursor
        
        obj, created = await M.get_or_create(name="New")
        assert obj.name == "New"
        assert created is True

    @pytest.mark.asyncio
    async def test_bulk_create(self, mock_db):
        M = fresh_model("BulkModel", attrs={
            "name": CharField(max_length=100),
        })
        cursor = AsyncMock()
        cursor.lastrowid = 1
        mock_db.execute.return_value = cursor
        
        items = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        results = await M.bulk_create(items)
        assert len(results) == 3


# ============================================================================
# Q Execution Tests (with mocked database)
# ============================================================================


class TestQExecution:
    """Test Q query execution with mocked database."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        ModelRegistry.set_database(db)
        yield db
        ModelRegistry._db = None

    @pytest.mark.asyncio
    async def test_q_all(self, mock_db):
        M = fresh_model("QAllExec", attrs={"name": CharField(max_length=100)})
        mock_db.fetch_all.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        
        results = await M.query().all()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_q_first(self, mock_db):
        M = fresh_model("QFirstExec", attrs={"name": CharField(max_length=100)})
        mock_db.fetch_all.return_value = [{"id": 1, "name": "Alice"}]
        
        result = await M.query().first()
        assert result.name == "Alice"

    @pytest.mark.asyncio
    async def test_q_count(self, mock_db):
        M = fresh_model("QCountExec", attrs={"name": CharField(max_length=100)})
        mock_db.fetch_val.return_value = 10
        
        cnt = await M.query().count()
        assert cnt == 10

    @pytest.mark.asyncio
    async def test_q_exists(self, mock_db):
        M = fresh_model("QExistsExec", attrs={"name": CharField(max_length=100)})
        mock_db.fetch_val.return_value = 1
        
        exists = await M.query().filter(name="Alice").exists()
        assert exists is True

    @pytest.mark.asyncio
    async def test_q_filter_exec(self, mock_db):
        M = fresh_model("QFilterExec", attrs={
            "name": CharField(max_length=100),
            "age": IntegerField(),
        })
        mock_db.fetch_all.return_value = [
            {"id": 1, "name": "Alice", "age": 25},
        ]
        
        results = await M.query().filter(age__gt=20).all()
        assert len(results) == 1
        assert results[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_q_update(self, mock_db):
        M = fresh_model("QUpdateExec", attrs={
            "name": CharField(max_length=100),
            "active": BooleanField(default=True),
        })
        cursor = AsyncMock()
        cursor.rowcount = 5
        mock_db.execute.return_value = cursor
        
        cnt = await M.query().filter(active=False).update(active=True)
        assert cnt == 5

    @pytest.mark.asyncio
    async def test_q_delete(self, mock_db):
        M = fresh_model("QDeleteExec", attrs={
            "name": CharField(max_length=100),
        })
        cursor = AsyncMock()
        cursor.rowcount = 3
        mock_db.execute.return_value = cursor
        
        cnt = await M.query().filter(name="old").delete()
        assert cnt == 3

    @pytest.mark.asyncio
    async def test_q_values(self, mock_db):
        M = fresh_model("QValuesExec", attrs={
            "name": CharField(max_length=100),
            "age": IntegerField(),
        })
        mock_db.fetch_all.return_value = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
        ]
        
        results = await M.query().values("name", "age")
        assert len(results) == 2
        assert results[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_q_values_list(self, mock_db):
        M = fresh_model("QVLExec", attrs={
            "name": CharField(max_length=100),
        })
        mock_db.fetch_all.return_value = [
            {"name": "Alice"},
            {"name": "Bob"},
        ]
        
        results = await M.query().values_list("name", flat=True)
        assert results == ["Alice", "Bob"]


# ============================================================================
# Migration Generation from Python Models
# ============================================================================


class TestMigrationFromModels:
    """Test generate_migration_from_models."""

    def test_generate_migration(self, tmp_path):
        from aquilia.models.migrations import generate_migration_from_models

        M = fresh_model("MigModel", attrs={
            "name": CharField(max_length=100),
            "active": BooleanField(default=True),
        })

        migration_path = generate_migration_from_models(
            [M], str(tmp_path), slug="test_migration"
        )
        assert migration_path.exists()
        content = migration_path.read_text()
        assert "upgrade" in content
        assert "downgrade" in content
        assert "CREATE TABLE" in content
        assert M._meta.table_name in content

    def test_generate_migration_with_fk(self, tmp_path):
        from aquilia.models.migrations import generate_migration_from_models

        M1 = fresh_model("MigParent", attrs={"name": CharField(max_length=100)})
        M2 = fresh_model("MigChild", attrs={
            "parent": ForeignKey(M1.__name__, on_delete="CASCADE"),
            "label": CharField(max_length=50),
        })

        path = generate_migration_from_models([M1, M2], str(tmp_path))
        assert path.exists()
        content = path.read_text()
        assert "REFERENCES" in content


# ============================================================================
# Integration Tests
# ============================================================================


class TestModelIntegration:
    """Test model system integration."""

    def test_import_from_aquilia(self):
        """Test top-level imports."""
        from aquilia import (
            Model, CharField, IntegerField, Q, ModelRegistry,
            ForeignKey, BooleanField, DateTimeField, TextField,
            EmailField, JSONField, FloatField, DecimalField,
            AutoField, BigAutoField,
        )
        assert Model is not None
        assert CharField is not None

    def test_import_legacy_compat(self):
        """Test legacy AMDL imports still work."""
        from aquilia import (
            ModelProxy, parse_amdl, AMDLFile, ModelNode,
            MigrationRunner, MigrationOps,
        )
        assert ModelProxy is not None

    def test_model_definition_syntax(self):
        """Test that the Aquilia model definition syntax works cleanly."""
        class Article(Model):
            title = CharField(max_length=200)
            content = TextField()
            published = BooleanField(default=False)
            views = IntegerField(default=0)
            created_at = DateTimeField(auto_now_add=True)

            class Meta:
                table_name = "articles"
                ordering = ["-created_at"]
                abstract = False

        assert "title" in Article._fields
        assert "content" in Article._fields
        assert Article._meta.table_name == "articles"
        assert Article._meta.ordering == ["-created_at"]

        sql = Article.generate_create_table_sql()
        assert "articles" in sql
        assert "title" in sql
        assert "VARCHAR(200)" in sql

    def test_model_with_relationships(self):
        """Test model with FK and M2M."""
        class Category(Model):
            name = CharField(max_length=100)

            class Meta:
                table_name = "categories_test"

        class Post(Model):
            title = CharField(max_length=200)
            category = ForeignKey("Category", on_delete="SET NULL", null=True)
            tags = ManyToManyField("Category")

            class Meta:
                table_name = "posts_test"

        assert "category" in Post._fields
        fk = Post._fields["category"]
        assert isinstance(fk, ForeignKey)
        assert fk.column_name == "category_id"

        sql = Post.generate_create_table_sql()
        assert "category_id" in sql
        assert "REFERENCES" in sql

        m2m_sqls = Post.generate_m2m_sql()
        assert len(m2m_sqls) >= 1

    def test_full_field_coverage(self):
        """Test model with many field types."""
        class FullModel(Model):
            name = CharField(max_length=100)
            bio = TextField(null=True)
            age = IntegerField(default=0)
            score = FloatField(default=0.0)
            price = DecimalField(max_digits=10, decimal_places=2, null=True)
            active = BooleanField(default=True)
            email = EmailField(unique=True)
            website = URLField(null=True)
            slug = SlugField()
            uuid = UUIDField(auto=True)
            data = JSONField(null=True)
            avatar = ImageField(upload_to="avatars/", null=True)
            ip = GenericIPAddressField(null=True)
            dob = DateField(null=True)
            login_time = TimeField(null=True)
            created = DateTimeField(auto_now_add=True)

            class Meta:
                table_name = "full_model_test"
                abstract = False

        assert len(FullModel._fields) >= 17  # 16 defined + id auto
        sql = FullModel.generate_create_table_sql()
        assert "full_model_test" in sql
        assert "VARCHAR(100)" in sql
        assert "TEXT" in sql
        assert "INTEGER" in sql
        assert "REAL" in sql
        assert "UNIQUE" in sql


# ============================================================================
# Deep Integration Tests — Cross-Module Connectivity
# ============================================================================


class TestLookupRegistryIntegration:
    """Tests that Q.filter() delegates to fields.lookups.resolve_lookup()."""

    def _q(self, model_cls):
        mock_db = MagicMock()
        return Q(table=model_cls._table_name, model_cls=model_cls, db=mock_db)

    def test_filter_exact_via_lookup(self):
        M = fresh_model("LkExact", attrs={"name": CharField(max_length=50)})
        q = self._q(M).filter(name__exact="Alice")
        assert '"name" = ?' in q._wheres[0]
        assert "Alice" in q._params

    def test_filter_iexact_via_lookup(self):
        M = fresh_model("LkIExact", attrs={"name": CharField(max_length=50)})
        q = self._q(M).filter(name__iexact="alice")
        assert "LOWER" in q._wheres[0]
        assert "alice" in q._params

    def test_filter_contains_via_lookup(self):
        M = fresh_model("LkContains", attrs={"bio": TextField()})
        q = self._q(M).filter(bio__contains="python")
        assert "LIKE" in q._wheres[0]
        assert "%python%" in q._params

    def test_filter_icontains_via_lookup(self):
        M = fresh_model("LkIContains", attrs={"bio": TextField()})
        q = self._q(M).filter(bio__icontains="python")
        assert "LOWER" in q._wheres[0]
        assert "LIKE" in q._wheres[0]

    def test_filter_startswith_via_lookup(self):
        M = fresh_model("LkStartsWith", attrs={"name": CharField(max_length=50)})
        q = self._q(M).filter(name__startswith="Al")
        assert "LIKE" in q._wheres[0]
        assert "Al%" in q._params

    def test_filter_endswith_via_lookup(self):
        M = fresh_model("LkEndsWith", attrs={"name": CharField(max_length=50)})
        q = self._q(M).filter(name__endswith="ice")
        assert "LIKE" in q._wheres[0]
        assert "%ice" in q._params

    def test_filter_gt_via_lookup(self):
        M = fresh_model("LkGt", attrs={"age": IntegerField()})
        q = self._q(M).filter(age__gt=18)
        assert '"age" > ?' in q._wheres[0]

    def test_filter_gte_via_lookup(self):
        M = fresh_model("LkGte", attrs={"age": IntegerField()})
        q = self._q(M).filter(age__gte=18)
        assert '"age" >= ?' in q._wheres[0]

    def test_filter_lt_via_lookup(self):
        M = fresh_model("LkLt", attrs={"age": IntegerField()})
        q = self._q(M).filter(age__lt=65)
        assert '"age" < ?' in q._wheres[0]

    def test_filter_lte_via_lookup(self):
        M = fresh_model("LkLte", attrs={"age": IntegerField()})
        q = self._q(M).filter(age__lte=65)
        assert '"age" <= ?' in q._wheres[0]

    def test_filter_in_via_lookup(self):
        M = fresh_model("LkIn", attrs={"status": CharField(max_length=20)})
        q = self._q(M).filter(status__in=["active", "pending"])
        assert "IN" in q._wheres[0]
        assert "active" in q._params
        assert "pending" in q._params

    def test_filter_isnull_via_lookup(self):
        M = fresh_model("LkIsNull", attrs={"email": CharField(max_length=100, null=True)})
        q = self._q(M).filter(email__isnull=True)
        assert "IS NULL" in q._wheres[0]

    def test_filter_isnull_false_via_lookup(self):
        M = fresh_model("LkIsNotNull", attrs={"email": CharField(max_length=100, null=True)})
        q = self._q(M).filter(email__isnull=False)
        assert "IS NOT NULL" in q._wheres[0]

    def test_filter_range_via_lookup(self):
        M = fresh_model("LkRange", attrs={"price": FloatField()})
        q = self._q(M).filter(price__range=(10.0, 50.0))
        assert "BETWEEN" in q._wheres[0]
        assert 10.0 in q._params
        assert 50.0 in q._params

    def test_filter_regex_via_lookup(self):
        M = fresh_model("LkRegex", attrs={"code": CharField(max_length=20)})
        q = self._q(M).filter(code__regex=r"^[A-Z]+$")
        assert "REGEXP" in q._wheres[0]

    def test_filter_date_via_lookup(self):
        """Date lookup should use DATE() function."""
        M = fresh_model("LkDate", attrs={"created": DateTimeField()})
        q = self._q(M).filter(created__date="2024-01-01")
        assert "DATE" in q._wheres[0]

    def test_filter_year_via_lookup(self):
        """Year lookup should use STRFTIME for sqlite."""
        M = fresh_model("LkYear", attrs={"created": DateTimeField()})
        q = self._q(M).filter(created__year=2024)
        assert "STRFTIME" in q._wheres[0] or "EXTRACT" in q._wheres[0]

    def test_filter_legacy_ne_still_works(self):
        """ne is not in lookup registry — should still work via fallback."""
        M = fresh_model("LkNe", attrs={"status": CharField(max_length=20)})
        q = self._q(M).filter(status__ne="deleted")
        assert "!=" in q._wheres[0]

    def test_filter_legacy_ilike_still_works(self):
        """ilike is not in lookup registry — should still work via fallback."""
        M = fresh_model("LkILike", attrs={"name": CharField(max_length=50)})
        q = self._q(M).filter(name__ilike="%test%")
        assert "LOWER" in q._wheres[0]


class TestCreateTableBuilderIntegration:
    """Tests that generate_create_table_sql uses CreateTableBuilder."""

    def test_basic_table_uses_builder(self):
        M = fresh_model("CTBBasic", attrs={"name": CharField(max_length=100)})
        sql = M.generate_create_table_sql()
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "VARCHAR(100)" in sql

    def test_check_constraint_in_builder(self):
        from aquilia.models.constraint import CheckConstraint
        M = fresh_model("CTBCheck", attrs={
            "age": IntegerField(),
        }, meta_attrs={
            "constraints": [CheckConstraint(check="age >= 0", name="age_positive")],
        })
        sql = M.generate_create_table_sql()
        assert "CHECK" in sql
        assert "age >= 0" in sql

    def test_unique_together_in_builder(self):
        M = fresh_model("CTBUniq", attrs={
            "first_name": CharField(max_length=50),
            "last_name": CharField(max_length=50),
        }, meta_attrs={
            "unique_together": [("first_name", "last_name")],
        })
        sql = M.generate_create_table_sql()
        assert "UNIQUE" in sql

    def test_unique_constraint_in_builder(self):
        M = fresh_model("CTBUniqC", attrs={
            "email": CharField(max_length=100),
            "username": CharField(max_length=50),
        }, meta_attrs={
            "constraints": [UniqueConstraint(fields=("email", "username"), name="unique_email_user")],
        })
        sql = M.generate_create_table_sql()
        assert "UNIQUE" in sql
        assert '"email"' in sql
        assert '"username"' in sql


class TestFullCleanIntegration:
    """Tests for full_clean(), clean_fields(), clean() — like Django."""

    def test_full_clean_valid(self):
        M = fresh_model("FCValid", attrs={"name": CharField(max_length=50)})
        instance = M(name="Alice")
        instance.full_clean()  # Should not raise

    def test_full_clean_null_violation(self):
        M = fresh_model("FCNull", attrs={"name": CharField(max_length=50)})
        instance = M()  # name is None, null=False
        with pytest.raises(FieldValidationError):
            instance.full_clean()

    def test_clean_fields_with_exclude(self):
        M = fresh_model("FCExclude", attrs={
            "name": CharField(max_length=50),
            "email": CharField(max_length=100),
        })
        instance = M()  # Both None
        # Excluding name — should still fail on email
        with pytest.raises(FieldValidationError) as exc_info:
            instance.clean_fields(exclude=["name"])
        assert "email" in str(exc_info.value)

    def test_clean_fields_with_choices(self):
        M = fresh_model("FCChoices", attrs={
            "status": CharField(max_length=20, choices=[("active", "Active"), ("banned", "Banned")]),
        })
        instance = M(status="invalid")
        with pytest.raises(FieldValidationError):
            instance.full_clean()

    def test_clean_fields_with_validators(self):
        from aquilia.models.fields.validators import MinValueValidator
        M = fresh_model("FCValidators", attrs={
            "age": IntegerField(validators=[MinValueValidator(0)]),
        })
        instance = M(age=-5)
        with pytest.raises(Exception):
            instance.full_clean()

    def test_clean_override(self):
        """Custom clean() for cross-field validation."""
        attrs = {
            "start": IntegerField(),
            "end": IntegerField(),
        }
        M = fresh_model("FCClean", attrs=attrs)

        # Monkey-patch clean for this test
        def custom_clean(self_inner):
            if self_inner.start is not None and self_inner.end is not None:
                if self_inner.start > self_inner.end:
                    raise FieldValidationError("end", "End must be >= start")
        M.clean = custom_clean

        instance = M(start=10, end=5)
        with pytest.raises(FieldValidationError):
            instance.full_clean()


class TestExcludeNOTIntegration:
    """Tests that exclude() wraps clauses with NOT() via _build_filter_clause."""

    def _q(self, model_cls):
        mock_db = MagicMock()
        return Q(table=model_cls._table_name, model_cls=model_cls, db=mock_db)

    def test_exclude_simple_not(self):
        M = fresh_model("ExclNot", attrs={"status": CharField(max_length=20)})
        q = self._q(M).exclude(status="deleted")
        assert "NOT" in q._wheres[0]
        assert '"status" = ?' in q._wheres[0]

    def test_exclude_with_lookup(self):
        M = fresh_model("ExclLookup", attrs={"age": IntegerField()})
        q = self._q(M).exclude(age__gt=100)
        assert "NOT" in q._wheres[0]
        assert '"age" > ?' in q._wheres[0]


class TestExpressionInAnnotations:
    """Tests that _build_select handles Expression objects in annotations."""

    def _q(self, model_cls):
        mock_db = MagicMock()
        return Q(table=model_cls._table_name, model_cls=model_cls, db=mock_db)

    def test_aggregate_in_annotations(self):
        from aquilia.models.aggregate import Count
        M = fresh_model("ExprAgg", attrs={"category": CharField(max_length=50)})
        q = self._q(M).annotate(total=Count("id"))
        sql, params = q._build_select()
        assert "COUNT" in sql
        assert "total" in sql

    def test_expression_f_in_annotations(self):
        from aquilia.models.expression import F
        M = fresh_model("ExprF", attrs={
            "price": FloatField(),
            "tax": FloatField(),
        })
        q = self._q(M).annotate(total=F("price") + F("tax"))
        sql, params = q._build_select()
        assert "total" in sql

    def test_expression_value_in_annotations(self):
        from aquilia.models.expression import Value
        M = fresh_model("ExprVal", attrs={"name": CharField(max_length=50)})
        q = self._q(M).annotate(constant=Value(42))
        sql, params = q._build_select()
        assert "constant" in sql


class TestMetaOrderingDefault:
    """Tests that Meta.ordering is applied as default ORDER BY."""

    def _q(self, model_cls):
        mock_db = MagicMock()
        return Q(table=model_cls._table_name, model_cls=model_cls, db=mock_db)

    def test_meta_ordering_applied(self):
        M = fresh_model("MetaOrd", attrs={
            "name": CharField(max_length=50),
            "created": DateTimeField(),
        }, meta_attrs={"ordering": ["-created", "name"]})
        q = self._q(M)
        sql, params = q._build_select()
        assert "ORDER BY" in sql
        assert "DESC" in sql  # -created → DESC

    def test_explicit_order_overrides_meta(self):
        M = fresh_model("MetaOrdOvr", attrs={
            "name": CharField(max_length=50),
            "age": IntegerField(),
        }, meta_attrs={"ordering": ["name"]})
        q = self._q(M).order("-age")
        sql, params = q._build_select()
        assert "ORDER BY" in sql
        assert '"age" DESC' in sql

    def test_no_meta_ordering_no_fallback(self):
        M = fresh_model("NoMetaOrd", attrs={"name": CharField(max_length=50)})
        q = self._q(M)
        sql, params = q._build_select()
        assert "ORDER BY" not in sql


class TestSQLBuilderIntegration:
    """Tests that Model.create/save/delete use sql_builder classes."""

    def test_insert_builder_format(self):
        """Verify InsertBuilder produces expected SQL format."""
        from aquilia.models.sql_builder import InsertBuilder
        builder = InsertBuilder("users").from_dict({"name": "Alice", "age": 30})
        sql, params = builder.build()
        assert "INSERT INTO" in sql
        assert '"users"' in sql
        assert '"name"' in sql
        assert '"age"' in sql
        assert params == ["Alice", 30]

    def test_update_builder_format(self):
        """Verify UpdateBuilder produces expected SQL format."""
        from aquilia.models.sql_builder import UpdateBuilder
        builder = UpdateBuilder("users").set_dict({"name": "Bob"})
        builder.where('"id" = ?', 1)
        sql, params = builder.build()
        assert "UPDATE" in sql
        assert "SET" in sql
        assert '"name" = ?' in sql
        assert params == ["Bob", 1]

    def test_delete_builder_format(self):
        """Verify DeleteBuilder produces expected SQL format."""
        from aquilia.models.sql_builder import DeleteBuilder
        builder = DeleteBuilder("users")
        builder.where('"id" = ?', 5)
        sql, params = builder.build()
        assert 'DELETE FROM "users"' in sql
        assert params == [5]

    def test_create_table_builder_format(self):
        """Verify CreateTableBuilder produces expected SQL format."""
        from aquilia.models.sql_builder import CreateTableBuilder
        builder = CreateTableBuilder("products")
        builder.column('"id" INTEGER PRIMARY KEY')
        builder.column('"name" VARCHAR(100) NOT NULL')
        builder.constraint("UNIQUE (\"name\")")
        sql = builder.build()
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"products"' in sql
        assert "UNIQUE" in sql


class TestDeletionIntegration:
    """Tests that deletion.py OnDeleteHandler uses sql_builder."""

    def test_on_delete_handler_cascade(self):
        """Verify OnDeleteHandler is importable and configured."""
        from aquilia.models.deletion import (
            CASCADE, SET_NULL, PROTECT, RESTRICT, DO_NOTHING,
            OnDeleteHandler, ProtectedError, RestrictedError,
        )
        handler = OnDeleteHandler(CASCADE)
        assert handler.action == CASCADE

    def test_on_delete_handler_protect(self):
        from aquilia.models.deletion import PROTECT, OnDeleteHandler
        handler = OnDeleteHandler(PROTECT)
        assert handler.action == PROTECT


class TestSignalIntegration:
    """Tests that signals are properly wired into models."""

    def test_class_prepared_exists(self):
        from aquilia.models.signals import class_prepared
        assert class_prepared is not None

    def test_m2m_changed_exists(self):
        from aquilia.models.signals import m2m_changed
        assert m2m_changed is not None

    def test_pre_migrate_exists(self):
        from aquilia.models.signals import pre_migrate, post_migrate
        assert pre_migrate is not None
        assert post_migrate is not None

    def test_signal_receiver_decorator(self):
        from aquilia.models.signals import receiver, pre_save
        called = []

        @receiver(pre_save)
        def on_pre_save(sender, **kwargs):
            called.append(sender)

        # Verify handler was registered
        assert len(pre_save._receivers) > 0


class TestQNodeWithLookupRegistry:
    """Tests that QNode._build_sql() goes through resolve_lookup."""

    def test_qnode_basic_filter(self):
        from aquilia.models.query import QNode
        node = QNode(name="Alice")
        sql, params = node._build_sql()
        assert '"name" = ?' in sql
        assert params == ["Alice"]

    def test_qnode_with_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(age__gte=18)
        sql, params = node._build_sql()
        assert '"age" >= ?' in sql
        assert params == [18]

    def test_qnode_and_composition(self):
        from aquilia.models.query import QNode
        node = QNode(active=True) & QNode(age__gt=18)
        sql, params = node._build_sql()
        assert "AND" in sql
        assert True in params
        assert 18 in params

    def test_qnode_or_composition(self):
        from aquilia.models.query import QNode
        node = QNode(role="admin") | QNode(is_superuser=True)
        sql, params = node._build_sql()
        assert "OR" in sql

    def test_qnode_negation(self):
        from aquilia.models.query import QNode
        node = ~QNode(banned=True)
        sql, params = node._build_sql()
        assert "NOT" in sql

    def test_qnode_contains_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(name__contains="test")
        sql, params = node._build_sql()
        assert "LIKE" in sql
        assert "%test%" in params

    def test_qnode_range_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(price__range=(10, 50))
        sql, params = node._build_sql()
        assert "BETWEEN" in sql
        assert 10 in params
        assert 50 in params

    def test_qnode_isnull_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(email__isnull=True)
        sql, params = node._build_sql()
        assert "IS NULL" in sql

    def test_qnode_in_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(status__in=["active", "pending", "review"])
        sql, params = node._build_sql()
        assert "IN" in sql
        assert "active" in params

    def test_qnode_regex_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(code__regex=r"^[A-Z]{3}$")
        sql, params = node._build_sql()
        assert "REGEXP" in sql

    def test_qnode_year_lookup(self):
        from aquilia.models.query import QNode
        node = QNode(created__year=2024)
        sql, params = node._build_sql()
        assert "STRFTIME" in sql or "EXTRACT" in sql
        assert 2024 in params


class TestConstraintIntegration:
    """Tests that constraint.py is properly used in DDL generation."""

    def test_check_constraint_sql(self):
        from aquilia.models.constraint import CheckConstraint
        c = CheckConstraint(check="price > 0", name="positive_price")
        sql = c.sql("products", "sqlite")
        assert "CHECK" in sql
        assert "price > 0" in sql

    def test_check_constraint_in_model_ddl(self):
        from aquilia.models.constraint import CheckConstraint
        M = fresh_model("CkModel", attrs={
            "price": FloatField(),
            "qty": IntegerField(),
        }, meta_attrs={
            "constraints": [
                CheckConstraint(check="price > 0", name="pos_price"),
                CheckConstraint(check="qty >= 0", name="non_neg_qty"),
            ],
        })
        sql = M.generate_create_table_sql()
        assert "price > 0" in sql
        assert "qty >= 0" in sql

    def test_mixed_constraints_and_unique_together(self):
        from aquilia.models.constraint import CheckConstraint
        M = fresh_model("MixedConst", attrs={
            "a": IntegerField(),
            "b": IntegerField(),
        }, meta_attrs={
            "unique_together": [("a", "b")],
            "constraints": [CheckConstraint(check="a != b", name="a_ne_b")],
        })
        sql = M.generate_create_table_sql()
        assert "UNIQUE" in sql
        assert "CHECK" in sql
        assert "a != b" in sql


class TestCrossModuleImports:
    """Tests that all modules can import from each other without circular import errors."""

    def test_base_imports_deletion(self):
        from aquilia.models.base import OnDeleteHandler, ProtectedError, RestrictedError
        assert OnDeleteHandler is not None

    def test_base_imports_sql_builder(self):
        from aquilia.models.base import InsertBuilder, UpdateBuilder, DeleteBuilder, CreateTableBuilder
        assert InsertBuilder is not None

    def test_base_imports_signals(self):
        from aquilia.models.base import pre_save, post_save, pre_delete, post_delete, class_prepared, m2m_changed
        assert class_prepared is not None

    def test_base_imports_constraint(self):
        from aquilia.models.base import CheckConstraint
        assert CheckConstraint is not None

    def test_query_imports_lookups(self):
        from aquilia.models.query import resolve_lookup, lookup_registry
        assert resolve_lookup is not None
        assert len(lookup_registry()) >= 20  # 20+ built-in lookups

    def test_deletion_imports_sql_builder(self):
        from aquilia.models.deletion import DeleteBuilder, UpdateBuilder
        assert DeleteBuilder is not None

    def test_migrations_imports_signals(self):
        from aquilia.models.migrations import pre_migrate, post_migrate
        assert pre_migrate is not None

    def test_all_modules_importable(self):
        """Smoke test — import every models sub-module."""
        import aquilia.models.base
        import aquilia.models.query
        import aquilia.models.signals
        import aquilia.models.deletion
        import aquilia.models.constraint
        import aquilia.models.sql_builder
        import aquilia.models.expression
        import aquilia.models.aggregate
        import aquilia.models.manager
        import aquilia.models.transactions
        import aquilia.models.migrations
        import aquilia.models.fields
        import aquilia.models.fields.validators
        import aquilia.models.fields.lookups
        assert True


class TestLookupRegistryDirect:
    """Tests for the lookup registry itself."""

    def test_registry_has_all_builtins(self):
        from aquilia.models.fields.lookups import lookup_registry
        reg = lookup_registry()
        expected = {
            "exact", "iexact", "contains", "icontains",
            "startswith", "istartswith", "endswith", "iendswith",
            "in", "gt", "gte", "lt", "lte", "isnull",
            "range", "regex", "iregex", "date", "year", "month", "day",
        }
        assert expected.issubset(set(reg.keys()))

    def test_resolve_lookup_exact(self):
        from aquilia.models.fields.lookups import resolve_lookup, Exact
        lookup = resolve_lookup("name", "exact", "Alice")
        assert isinstance(lookup, Exact)
        sql, params = lookup.as_sql()
        assert sql == '"name" = ?'
        assert params == ["Alice"]

    def test_resolve_lookup_unknown_raises(self):
        from aquilia.models.fields.lookups import resolve_lookup
        with pytest.raises(ValueError, match="Unknown lookup"):
            resolve_lookup("name", "nonexistent", "value")

    def test_register_custom_lookup(self):
        from aquilia.models.fields.lookups import register_lookup, resolve_lookup, Lookup

        class NotEqualLookup(Lookup):
            lookup_name = "neq"
            sql_operator = "!="

        register_lookup("neq", NotEqualLookup)
        lookup = resolve_lookup("status", "neq", "deleted")
        sql, params = lookup.as_sql()
        assert '"status" != ?' in sql

