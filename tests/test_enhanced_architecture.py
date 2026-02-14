"""
Tests for the enhanced architecture — validators, lookups, expressions,
aggregates, signals, manager, query builder, registry, options, CLI commands.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Validators ───────────────────────────────────────────────────────────────


class TestValidators:
    """Tests for aquilia.models.fields.validators module."""

    def test_min_value_validator_pass(self):
        from aquilia.models.fields.validators import MinValueValidator
        v = MinValueValidator(0)
        v(5)  # should not raise

    def test_min_value_validator_fail(self):
        from aquilia.models.fields.validators import MinValueValidator, ValidationError
        v = MinValueValidator(10)
        with pytest.raises(ValidationError, match="greater than or equal to 10"):
            v(5)

    def test_max_value_validator_pass(self):
        from aquilia.models.fields.validators import MaxValueValidator
        v = MaxValueValidator(100)
        v(50)

    def test_max_value_validator_fail(self):
        from aquilia.models.fields.validators import MaxValueValidator, ValidationError
        v = MaxValueValidator(100)
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            v(150)

    def test_min_length_validator_pass(self):
        from aquilia.models.fields.validators import MinLengthValidator
        v = MinLengthValidator(3)
        v("hello")

    def test_min_length_validator_fail(self):
        from aquilia.models.fields.validators import MinLengthValidator, ValidationError
        v = MinLengthValidator(5)
        with pytest.raises(ValidationError, match="at least 5"):
            v("hi")

    def test_max_length_validator_pass(self):
        from aquilia.models.fields.validators import MaxLengthValidator
        v = MaxLengthValidator(10)
        v("hello")

    def test_max_length_validator_fail(self):
        from aquilia.models.fields.validators import MaxLengthValidator, ValidationError
        v = MaxLengthValidator(3)
        with pytest.raises(ValidationError, match="at most 3"):
            v("hello")

    def test_regex_validator_pass(self):
        from aquilia.models.fields.validators import RegexValidator
        v = RegexValidator(r'^[a-z]+$')
        v("hello")

    def test_regex_validator_fail(self):
        from aquilia.models.fields.validators import RegexValidator, ValidationError
        v = RegexValidator(r'^[a-z]+$')
        with pytest.raises(ValidationError):
            v("Hello123")

    def test_email_validator_pass(self):
        from aquilia.models.fields.validators import EmailValidator
        v = EmailValidator()
        v("test@example.com")
        v("user.name+tag@domain.co.uk")

    def test_email_validator_fail(self):
        from aquilia.models.fields.validators import EmailValidator, ValidationError
        v = EmailValidator()
        with pytest.raises(ValidationError, match="valid email"):
            v("not-an-email")

    def test_url_validator_pass(self):
        from aquilia.models.fields.validators import URLValidator
        v = URLValidator()
        v("https://example.com/path")
        v("http://localhost:8080")

    def test_url_validator_fail(self):
        from aquilia.models.fields.validators import URLValidator, ValidationError
        v = URLValidator()
        with pytest.raises(ValidationError, match="valid URL"):
            v("not-a-url")

    def test_slug_validator_pass(self):
        from aquilia.models.fields.validators import SlugValidator
        v = SlugValidator()
        v("my-slug-123")

    def test_slug_validator_fail(self):
        from aquilia.models.fields.validators import SlugValidator, ValidationError
        v = SlugValidator()
        with pytest.raises(ValidationError, match="valid slug"):
            v("not a slug!")

    def test_prohibit_null_chars(self):
        from aquilia.models.fields.validators import ProhibitNullCharactersValidator, ValidationError
        v = ProhibitNullCharactersValidator()
        v("hello world")
        with pytest.raises(ValidationError, match="Null characters"):
            v("hello\x00world")

    def test_decimal_validator_pass(self):
        from aquilia.models.fields.validators import DecimalValidator
        from decimal import Decimal
        v = DecimalValidator(max_digits=5, decimal_places=2)
        v(Decimal("123.45"))
        v(Decimal("0.99"))

    def test_decimal_validator_fail_digits(self):
        from aquilia.models.fields.validators import DecimalValidator, ValidationError
        from decimal import Decimal
        v = DecimalValidator(max_digits=3, decimal_places=1)
        with pytest.raises(ValidationError, match="digits"):
            v(Decimal("1234.5"))

    def test_file_extension_validator_pass(self):
        from aquilia.models.fields.validators import FileExtensionValidator
        v = FileExtensionValidator(allowed_extensions=["jpg", "png", "gif"])
        v("photo.jpg")
        v("image.PNG")

    def test_file_extension_validator_fail(self):
        from aquilia.models.fields.validators import FileExtensionValidator, ValidationError
        v = FileExtensionValidator(allowed_extensions=["jpg", "png"])
        with pytest.raises(ValidationError, match="Allowed"):
            v("document.pdf")

    def test_step_value_validator_pass(self):
        from aquilia.models.fields.validators import StepValueValidator
        v = StepValueValidator(step=5)
        v(10)
        v(25)

    def test_step_value_validator_fail(self):
        from aquilia.models.fields.validators import StepValueValidator, ValidationError
        v = StepValueValidator(step=5)
        with pytest.raises(ValidationError, match="multiple of 5"):
            v(7)

    def test_range_validator_pass(self):
        from aquilia.models.fields.validators import RangeValidator
        v = RangeValidator(min_val=1, max_val=100)
        v(50)

    def test_range_validator_fail_low(self):
        from aquilia.models.fields.validators import RangeValidator, ValidationError
        v = RangeValidator(min_val=10, max_val=100)
        with pytest.raises(ValidationError):
            v(5)

    def test_range_validator_fail_high(self):
        from aquilia.models.fields.validators import RangeValidator, ValidationError
        v = RangeValidator(min_val=10, max_val=100)
        with pytest.raises(ValidationError):
            v(200)

    def test_validator_repr(self):
        from aquilia.models.fields.validators import MinValueValidator
        v = MinValueValidator(5)
        assert "MinValueValidator" in repr(v)

    def test_validator_eq(self):
        from aquilia.models.fields.validators import MinValueValidator
        v1 = MinValueValidator(5)
        v2 = MinValueValidator(5)
        v3 = MinValueValidator(10)
        assert v1 == v2
        assert v1 != v3


# ── Lookups ──────────────────────────────────────────────────────────────────


class TestLookups:
    """Tests for aquilia.models.fields.lookups module."""

    def test_exact_lookup(self):
        from aquilia.models.fields.lookups import Exact
        lookup = Exact("name", "Alice")
        sql, params = lookup.as_sql()
        assert sql == '"name" = ?'
        assert params == ["Alice"]

    def test_iexact_lookup(self):
        from aquilia.models.fields.lookups import IExact
        lookup = IExact("name", "alice")
        sql, params = lookup.as_sql()
        assert 'LOWER' in sql
        assert params == ["alice"]

    def test_contains_lookup(self):
        from aquilia.models.fields.lookups import Contains
        lookup = Contains("name", "lic")
        sql, params = lookup.as_sql()
        assert 'LIKE' in sql
        assert params == ["%lic%"]

    def test_icontains_lookup(self):
        from aquilia.models.fields.lookups import IContains
        lookup = IContains("name", "lic")
        sql, params = lookup.as_sql()
        assert 'LOWER' in sql
        assert params == ["%lic%"]

    def test_startswith_lookup(self):
        from aquilia.models.fields.lookups import StartsWith
        lookup = StartsWith("name", "Al")
        sql, params = lookup.as_sql()
        assert 'LIKE' in sql
        assert params == ["Al%"]

    def test_endswith_lookup(self):
        from aquilia.models.fields.lookups import EndsWith
        lookup = EndsWith("name", "ice")
        sql, params = lookup.as_sql()
        assert 'LIKE' in sql
        assert params == ["%ice"]

    def test_in_lookup(self):
        from aquilia.models.fields.lookups import In
        lookup = In("id", [1, 2, 3])
        sql, params = lookup.as_sql()
        assert "IN" in sql
        assert params == [1, 2, 3]

    def test_gt_lookup(self):
        from aquilia.models.fields.lookups import Gt
        lookup = Gt("age", 18)
        sql, params = lookup.as_sql()
        assert '"age" > ?' == sql
        assert params == [18]

    def test_gte_lookup(self):
        from aquilia.models.fields.lookups import Gte
        lookup = Gte("age", 18)
        sql, params = lookup.as_sql()
        assert '"age" >= ?' == sql
        assert params == [18]

    def test_lt_lookup(self):
        from aquilia.models.fields.lookups import Lt
        lookup = Lt("price", 100)
        sql, params = lookup.as_sql()
        assert '"price" < ?' == sql
        assert params == [100]

    def test_lte_lookup(self):
        from aquilia.models.fields.lookups import Lte
        lookup = Lte("price", 100)
        sql, params = lookup.as_sql()
        assert '"price" <= ?' == sql
        assert params == [100]

    def test_isnull_lookup_true(self):
        from aquilia.models.fields.lookups import IsNull
        lookup = IsNull("email", True)
        sql, params = lookup.as_sql()
        assert "IS NULL" in sql
        assert params == []

    def test_isnull_lookup_false(self):
        from aquilia.models.fields.lookups import IsNull
        lookup = IsNull("email", False)
        sql, params = lookup.as_sql()
        assert "IS NOT NULL" in sql
        assert params == []

    def test_range_lookup(self):
        from aquilia.models.fields.lookups import Range
        lookup = Range("price", (10, 100))
        sql, params = lookup.as_sql()
        assert "BETWEEN" in sql
        assert params == [10, 100]

    def test_regex_lookup(self):
        from aquilia.models.fields.lookups import Regex
        lookup = Regex("name", r'^[A-Z]')
        sql, params = lookup.as_sql()
        assert "REGEXP" in sql
        assert params == [r'^[A-Z]']

    def test_register_and_resolve_lookup(self):
        from aquilia.models.fields.lookups import register_lookup, resolve_lookup, Lookup

        class MyCustomLookup(Lookup):
            lookup_name = "custom_test"
            def as_sql(self, dialect="sqlite"):
                return f'CUSTOM("{self.field_name}", ?)', [self.value]

        register_lookup("custom_test", MyCustomLookup)
        resolved = resolve_lookup("name", "custom_test", "test")
        assert resolved is not None
        sql, params = resolved.as_sql()
        assert "CUSTOM" in sql
        assert params == ["test"]

    def test_lookup_repr(self):
        from aquilia.models.fields.lookups import Exact
        lookup = Exact("name", "Alice")
        assert "Exact" in repr(lookup)


# ── Enhanced Expressions ─────────────────────────────────────────────────────


class TestEnhancedExpressions:
    """Tests for enhanced expression types."""

    def test_when_with_dict_condition(self):
        from aquilia.models.expression import When, Value
        w = When(condition={"status": "active"}, then=Value(1))
        sql, params = w.as_sql()
        assert "WHEN" in sql
        assert "THEN" in sql
        assert "active" in params

    def test_when_with_string_condition(self):
        from aquilia.models.expression import When, Value
        w = When(condition="age > 18", then=Value("adult"))
        sql, params = w.as_sql()
        assert "age > 18" in sql
        assert "adult" in params

    def test_when_with_lookup_kwargs(self):
        from aquilia.models.expression import When, Value
        w = When(then=Value("yes"), active=True)
        sql, params = w.as_sql()
        assert "WHEN" in sql
        assert True in params

    def test_case_expression(self):
        from aquilia.models.expression import Case, When, Value
        expr = Case(
            When(condition={"status": "active"}, then=Value("Active")),
            When(condition={"status": "inactive"}, then=Value("Inactive")),
            default=Value("Unknown"),
        )
        sql, params = expr.as_sql()
        assert "CASE" in sql
        assert "WHEN" in sql
        assert "ELSE" in sql
        assert "END" in sql
        assert "Active" in params
        assert "Inactive" in params
        assert "Unknown" in params

    def test_case_without_default(self):
        from aquilia.models.expression import Case, When, Value
        expr = Case(
            When(condition={"x": 1}, then=Value("one")),
        )
        sql, params = expr.as_sql()
        assert "CASE" in sql
        assert "ELSE" not in sql

    def test_subquery(self):
        from aquilia.models.expression import Subquery
        # Mock a queryset
        mock_qs = MagicMock()
        mock_qs._build_select.return_value = ('SELECT * FROM "orders"', [])
        sub = Subquery(mock_qs)
        sql, params = sub.as_sql()
        assert sql == '(SELECT * FROM "orders")'

    def test_exists(self):
        from aquilia.models.expression import Exists
        mock_qs = MagicMock()
        mock_qs._build_select.return_value = ('SELECT 1 FROM "orders"', [])
        ex = Exists(mock_qs)
        sql, params = ex.as_sql()
        assert sql == 'EXISTS (SELECT 1 FROM "orders")'

    def test_outer_ref(self):
        from aquilia.models.expression import OuterRef
        ref = OuterRef("user_id")
        sql, params = ref.as_sql()
        assert sql == '"user_id"'
        assert "OuterRef" in repr(ref)

    def test_expression_wrapper(self):
        from aquilia.models.expression import ExpressionWrapper, F
        wrapped = ExpressionWrapper(F("price") + F("tax"))
        sql, params = wrapped.as_sql()
        assert "price" in sql
        assert "tax" in sql

    def test_func(self):
        from aquilia.models.expression import Func, F
        upper = Func("UPPER", F("name"))
        sql, params = upper.as_sql()
        assert sql == 'UPPER("name")'

    def test_func_multiple_args(self):
        from aquilia.models.expression import Func, F, Value
        fn = Func("COALESCE", F("val"), Value(0))
        sql, params = fn.as_sql()
        assert "COALESCE" in sql
        assert params == [0]

    def test_cast(self):
        from aquilia.models.expression import Cast, F
        expr = Cast(F("price"), "INTEGER")
        sql, params = expr.as_sql()
        assert sql == 'CAST("price" AS INTEGER)'

    def test_cast_with_string_arg(self):
        from aquilia.models.expression import Cast
        expr = Cast("price", "TEXT")
        sql, params = expr.as_sql()
        assert "CAST" in sql
        assert "TEXT" in sql

    def test_coalesce(self):
        from aquilia.models.expression import Coalesce, F, Value
        expr = Coalesce(F("nickname"), F("name"), Value("Anonymous"))
        sql, params = expr.as_sql()
        assert "COALESCE" in sql
        assert params == ["Anonymous"]

    def test_greatest_sqlite(self):
        from aquilia.models.expression import Greatest, F, Value
        expr = Greatest(F("a"), F("b"), Value(0))
        sql, params = expr.as_sql("sqlite")
        assert "MAX(" in sql  # SQLite fallback

    def test_greatest_postgres(self):
        from aquilia.models.expression import Greatest, F, Value
        expr = Greatest(F("a"), F("b"), Value(0))
        sql, params = expr.as_sql("postgresql")
        assert "GREATEST(" in sql

    def test_least_sqlite(self):
        from aquilia.models.expression import Least, F, Value
        expr = Least(F("a"), F("b"), Value(100))
        sql, params = expr.as_sql("sqlite")
        assert "MIN(" in sql  # SQLite fallback

    def test_least_postgres(self):
        from aquilia.models.expression import Least, F, Value
        expr = Least(F("a"), F("b"), Value(100))
        sql, params = expr.as_sql("postgresql")
        assert "LEAST(" in sql

    def test_nullif(self):
        from aquilia.models.expression import NullIf, F, Value
        expr = NullIf(F("value"), Value(0))
        sql, params = expr.as_sql()
        assert "NULLIF" in sql
        assert params == [0]


# ── Enhanced Aggregates ──────────────────────────────────────────────────────


class TestEnhancedAggregates:
    """Tests for enhanced aggregate types."""

    def test_array_agg_sqlite(self):
        from aquilia.models.aggregate import ArrayAgg
        agg = ArrayAgg("name")
        sql, params = agg.as_sql("sqlite")
        assert "GROUP_CONCAT" in sql  # SQLite fallback

    def test_array_agg_postgres(self):
        from aquilia.models.aggregate import ArrayAgg
        agg = ArrayAgg("name", distinct=True)
        sql, params = agg.as_sql("postgresql")
        assert "ARRAY_AGG" in sql
        assert "DISTINCT" in sql

    def test_string_agg_sqlite(self):
        from aquilia.models.aggregate import StringAgg
        agg = StringAgg("name", delimiter=", ")
        sql, params = agg.as_sql("sqlite")
        assert "GROUP_CONCAT" in sql
        assert ", " in params

    def test_string_agg_postgres(self):
        from aquilia.models.aggregate import StringAgg
        agg = StringAgg("name", delimiter=", ")
        sql, params = agg.as_sql("postgresql")
        assert "STRING_AGG" in sql
        assert ", " in params

    def test_string_agg_mysql(self):
        from aquilia.models.aggregate import StringAgg
        agg = StringAgg("name", delimiter="; ")
        sql, params = agg.as_sql("mysql")
        assert "GROUP_CONCAT" in sql
        assert "SEPARATOR" in sql

    def test_group_concat_sqlite(self):
        from aquilia.models.aggregate import GroupConcat
        agg = GroupConcat("tag", separator=", ")
        sql, params = agg.as_sql("sqlite")
        assert "GROUP_CONCAT" in sql
        assert ", " in params

    def test_group_concat_mysql(self):
        from aquilia.models.aggregate import GroupConcat
        agg = GroupConcat("tag", separator="; ")
        sql, params = agg.as_sql("mysql")
        assert "SEPARATOR" in sql

    def test_bool_and_sqlite(self):
        from aquilia.models.aggregate import BoolAnd
        agg = BoolAnd("active")
        sql, params = agg.as_sql("sqlite")
        assert "MIN(" in sql  # SQLite fallback

    def test_bool_and_postgres(self):
        from aquilia.models.aggregate import BoolAnd
        agg = BoolAnd("active")
        sql, params = agg.as_sql("postgresql")
        assert "BOOL_AND" in sql

    def test_bool_or_sqlite(self):
        from aquilia.models.aggregate import BoolOr
        agg = BoolOr("active")
        sql, params = agg.as_sql("sqlite")
        assert "MAX(" in sql  # SQLite fallback

    def test_bool_or_postgres(self):
        from aquilia.models.aggregate import BoolOr
        agg = BoolOr("active")
        sql, params = agg.as_sql("postgresql")
        assert "BOOL_OR" in sql


# ── Enhanced Signals ─────────────────────────────────────────────────────────


class TestEnhancedSignals:
    """Tests for enhanced signal features."""

    def test_receiver_decorator(self):
        from aquilia.models.signals import Signal, receiver

        test_signal = Signal("test_receiver")
        results = []

        @receiver(test_signal)
        def handler(sender, **kwargs):
            results.append("called")

        test_signal.send_sync(sender=object)
        assert results == ["called"]
        test_signal.clear()

    def test_receiver_with_sender_filter(self):
        from aquilia.models.signals import Signal, receiver

        test_signal = Signal("test_receiver_sender")
        results = []

        class MyModel:
            pass

        class OtherModel:
            pass

        @receiver(test_signal, sender=MyModel)
        def handler(sender, **kwargs):
            results.append(sender.__name__)

        test_signal.send_sync(sender=MyModel)
        test_signal.send_sync(sender=OtherModel)
        assert results == ["MyModel"]
        test_signal.clear()

    def test_class_prepared_signal_exists(self):
        from aquilia.models.signals import class_prepared
        assert class_prepared.name == "class_prepared"

    def test_pre_migrate_signal_exists(self):
        from aquilia.models.signals import pre_migrate
        assert pre_migrate.name == "pre_migrate"

    def test_post_migrate_signal_exists(self):
        from aquilia.models.signals import post_migrate
        assert post_migrate.name == "post_migrate"

    def test_receiver_multiple_signals(self):
        from aquilia.models.signals import Signal, receiver

        sig1 = Signal("multi_1")
        sig2 = Signal("multi_2")
        results = []

        @receiver(sig1)
        @receiver(sig2)
        def handler(sender, **kwargs):
            results.append("called")

        sig1.send_sync(sender=object)
        sig2.send_sync(sender=object)
        assert results == ["called", "called"]
        sig1.clear()
        sig2.clear()


# ── Enhanced Manager ─────────────────────────────────────────────────────────


class TestEnhancedManager:
    """Tests for enhanced manager features."""

    def test_queryset_class_exists(self):
        from aquilia.models.manager import QuerySet
        qs = QuerySet()
        assert hasattr(qs, "get_queryset")

    def test_from_queryset_creates_manager_class(self):
        from aquilia.models.manager import Manager, QuerySet

        class MyQuerySet(QuerySet):
            def active(self):
                return self.get_queryset()

        MyManager = Manager.from_queryset(MyQuerySet)
        assert "active" in dir(MyManager)
        assert issubclass(MyManager, Manager)

    def test_from_queryset_custom_name(self):
        from aquilia.models.manager import Manager, QuerySet

        class SpecialQS(QuerySet):
            def special(self):
                return self.get_queryset()

        CustomMgr = Manager.from_queryset(SpecialQS, class_name="CustomMgr")
        assert CustomMgr.__name__ == "CustomMgr"
        assert "special" in dir(CustomMgr)


# ── QNode / Query Builder ───────────────────────────────────────────────────


class TestQNode:
    """Tests for QNode (composable filter) system."""

    def test_qnode_basic(self):
        from aquilia.models.query import QNode
        q = QNode(name="Alice")
        sql, params = q._build_sql()
        assert '"name" = ?' in sql
        assert params == ["Alice"]

    def test_qnode_and(self):
        from aquilia.models.query import QNode
        q = QNode(name="Alice") & QNode(active=True)
        sql, params = q._build_sql()
        assert "AND" in sql
        assert "Alice" in params
        assert True in params

    def test_qnode_or(self):
        from aquilia.models.query import QNode
        q = QNode(name="Alice") | QNode(name="Bob")
        sql, params = q._build_sql()
        assert "OR" in sql
        assert "Alice" in params
        assert "Bob" in params

    def test_qnode_negation(self):
        from aquilia.models.query import QNode
        q = ~QNode(banned=True)
        sql, params = q._build_sql()
        assert "NOT" in sql
        assert True in params

    def test_qnode_complex(self):
        from aquilia.models.query import QNode
        q = (QNode(active=True) & QNode(role="admin")) | QNode(is_superuser=True)
        sql, params = q._build_sql()
        assert "OR" in sql
        assert "admin" in params

    def test_qnode_with_lookups(self):
        from aquilia.models.query import QNode
        q = QNode(age__gt=18)
        sql, params = q._build_sql()
        assert '"age" > ?' in sql
        assert params == [18]

    def test_qnode_contains_lookup(self):
        from aquilia.models.query import QNode
        q = QNode(name__contains="lic")
        sql, params = q._build_sql()
        assert "LIKE" in sql
        assert "%lic%" in params

    def test_qnode_in_lookup(self):
        from aquilia.models.query import QNode
        q = QNode(id__in=[1, 2, 3])
        sql, params = q._build_sql()
        assert "IN" in sql
        assert params == [1, 2, 3]

    def test_qnode_isnull_lookup(self):
        from aquilia.models.query import QNode
        q = QNode(email__isnull=True)
        sql, params = q._build_sql()
        assert "IS NULL" in sql

    def test_qnode_range_lookup(self):
        from aquilia.models.query import QNode
        q = QNode(price__range=(10, 100))
        sql, params = q._build_sql()
        assert "BETWEEN" in sql
        assert params == [10, 100]

    def test_qnode_repr(self):
        from aquilia.models.query import QNode
        q = QNode(name="Alice")
        assert "QNode" in repr(q)


# ── Registry ────────────────────────────────────────────────────────────────


class TestNewRegistry:
    """Tests for the enhanced ModelRegistry."""

    def test_registry_import(self):
        from aquilia.models.registry import ModelRegistry
        assert hasattr(ModelRegistry, "register")
        assert hasattr(ModelRegistry, "check_constraints")
        assert hasattr(ModelRegistry, "get_app_models")
        assert hasattr(ModelRegistry, "drop_tables")

    def test_registry_check_constraints(self):
        from aquilia.models.registry import ModelRegistry
        # Should return list (may be empty if no issues)
        issues = ModelRegistry.check_constraints()
        assert isinstance(issues, list)


# ── Enhanced Options ─────────────────────────────────────────────────────────


class TestEnhancedOptions:
    """Tests for enhanced Options class."""

    def test_options_new_attributes(self):
        from aquilia.models.options import Options

        class Meta:
            table = "test_table"
            managed = True
            select_on_save = False
            default_permissions = ("add", "change", "delete", "view")
            get_latest_by = "created_at"
            order_with_respect_to = None
            proxy = False

        opts = Options("TestModel", Meta)
        assert opts.table_name == "test_table"
        assert opts.managed is True
        assert opts.select_on_save is False
        assert "view" in opts.default_permissions
        assert opts.get_latest_by == "created_at"
        assert opts.proxy is False

    def test_options_label_properties(self):
        from aquilia.models.options import Options

        class Meta:
            app_label = "myapp"

        opts = Options("User", Meta)
        assert opts.label == "myapp.User"
        assert opts.label_lower == "myapp.user"

    def test_options_default_managed(self):
        from aquilia.models.options import Options
        opts = Options("TestModel")
        assert opts.managed is True  # Default should be True


# ── Imports / Exports ────────────────────────────────────────────────────────


class TestNewExports:
    """Test that all new types are properly exported."""

    def test_expression_exports(self):
        from aquilia.models import (
            When, Case, Subquery, Exists, OuterRef,
            ExpressionWrapper, Func, Cast, Coalesce,
            Greatest, Least, NullIf,
        )

    def test_aggregate_exports(self):
        from aquilia.models import (
            ArrayAgg, StringAgg, GroupConcat, BoolAnd, BoolOr,
        )

    def test_signal_exports(self):
        from aquilia.models import receiver, class_prepared, pre_migrate, post_migrate

    def test_manager_exports(self):
        from aquilia.models import QuerySet

    def test_query_exports(self):
        from aquilia.models import QNode, QCombination, QueryBuilder

    def test_registry_exports(self):
        from aquilia.models import NewModelRegistry

    def test_options_exports(self):
        from aquilia.models import EnhancedOptions

    def test_validators_from_fields(self):
        from aquilia.models.fields import (
            MinValueValidator, MaxValueValidator,
            MinLengthValidator, MaxLengthValidator,
            RegexValidator, EmailValidator, URLValidator,
            SlugValidator, DecimalValidator,
        )

    def test_lookups_from_fields(self):
        from aquilia.models.fields import (
            Lookup, Exact, IExact, Contains, IContains,
            StartsWith, EndsWith, In, Gt, Gte, Lt, Lte,
            IsNull, Range, Regex,
            register_lookup, resolve_lookup, lookup_registry,
        )


# ── CLI Commands ─────────────────────────────────────────────────────────────


class TestCLICommands:
    """Test new CLI command functions."""

    def test_table_to_class_name(self):
        from aquilia.cli.commands.model_cmds import _table_to_class_name
        assert _table_to_class_name("users") == "Users"
        assert _table_to_class_name("order_items") == "OrderItems"
        assert _table_to_class_name("user-profiles") == "UserProfiles"

    def test_sql_type_to_field_int(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("INTEGER", 1, None)
        assert field_type == "IntegerField"

    def test_sql_type_to_field_varchar(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("VARCHAR(255)", 1, None)
        assert field_type == "CharField"
        assert "max_length=255" in args

    def test_sql_type_to_field_text(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("TEXT", 0, None)
        assert field_type == "TextField"
        assert "null=True" in args

    def test_sql_type_to_field_bool(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("BOOLEAN", 1, None)
        assert field_type == "BooleanField"

    def test_sql_type_to_field_float(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("REAL", 1, None)
        assert field_type == "FloatField"

    def test_sql_type_to_field_datetime(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("DATETIME", 1, None)
        assert field_type == "DateTimeField"

    def test_sql_type_to_field_json(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("JSON", 1, None)
        assert field_type == "JSONField"

    def test_sql_type_to_field_blob(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("BLOB", 0, None)
        assert field_type == "BinaryField"

    def test_sql_type_to_field_bigint(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("BIGINT", 1, None)
        assert field_type == "BigIntegerField"

    def test_sql_type_to_field_decimal(self):
        from aquilia.cli.commands.model_cmds import _sql_type_to_field
        field_type, args = _sql_type_to_field("DECIMAL(10,2)", 1, None)
        assert field_type == "DecimalField"

    def test_showmigrations_empty(self, tmp_path):
        from aquilia.cli.commands.model_cmds import cmd_showmigrations
        results = cmd_showmigrations(
            migrations_dir=str(tmp_path / "no_migrations"),
            verbose=False,
        )
        assert results == []

    def test_sqlmigrate_not_found(self, tmp_path):
        from aquilia.cli.commands.model_cmds import cmd_sqlmigrate
        result = cmd_sqlmigrate(
            migration_name="nonexistent",
            migrations_dir=str(tmp_path),
            verbose=False,
        )
        assert result is None


# ── Query Builder Enhanced Features ──────────────────────────────────────────


class TestQueryBuilderEnhanced:
    """Tests for the enhanced Q query builder features."""

    def test_q_random_order(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("test", MagicMock(), mock_db)
        q2 = q.order("?")
        assert "RANDOM()" in q2._order_clauses

    def test_q_only_fields(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("test", MagicMock(), mock_db)
        q2 = q.only("name", "email")
        sql, _ = q2._build_select()
        assert '"name"' in sql
        assert '"email"' in sql

    def test_q_defer_fields(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("test", MagicMock(), mock_db)
        q2 = q.defer("bio")
        assert q2._defer_fields == ["bio"]

    def test_q_prefetch_related(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("test", MagicMock(), mock_db)
        q2 = q.prefetch_related("posts", "comments")
        assert q2._prefetch_related == ["posts", "comments"]

    def test_q_repr(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("users", MagicMock(), mock_db)
        r = repr(q)
        assert "<Q:" in r
        assert "users" in r

    def test_q_filter_with_qnode(self):
        from aquilia.models.query import Q, QNode
        mock_db = MagicMock()
        q = Q("users", MagicMock(), mock_db)
        qn = QNode(name="Alice") | QNode(name="Bob")
        q2 = q.filter(qn)
        assert len(q2._wheres) == 1
        assert "OR" in q2._wheres[0]

    def test_q_exclude_with_lookups(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("users", MagicMock(), mock_db)
        q2 = q.exclude(status="banned")
        assert any("NOT" in w for w in q2._wheres)

    def test_q_filter_range(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("products", MagicMock(), mock_db)
        q2 = q.filter(price__range=(10, 100))
        sql, params = q2._build_select()
        assert "BETWEEN" in sql

    def test_q_filter_regex(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("users", MagicMock(), mock_db)
        q2 = q.filter(name__regex=r'^[A-Z]')
        sql, params = q2._build_select()
        assert "REGEXP" in sql

    def test_q_icontains(self):
        from aquilia.models.query import Q
        mock_db = MagicMock()
        q = Q("users", MagicMock(), mock_db)
        q2 = q.filter(name__icontains="alice")
        sql, params = q2._build_select()
        assert "LOWER" in sql
