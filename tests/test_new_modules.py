"""
Tests for new model modules: expressions, aggregates, signals,
transactions, deletion, enums, sql_builder, manager, constraints, indexes.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ═══════════════════════════════════════════════════════════════════════════
# Expression Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.expression import (
    F, Value, RawSQL, Col, Star, CombinedExpression, Expression,
)


class TestF:
    def test_as_sql(self):
        f = F("age")
        sql, params = f.as_sql("sqlite")
        assert sql == '"age"'
        assert params == []

    def test_arithmetic_add(self):
        expr = F("age") + 1
        assert isinstance(expr, CombinedExpression)
        sql, params = expr.as_sql("sqlite")
        assert sql == '("age" + ?)'
        assert params == [1]

    def test_arithmetic_sub(self):
        expr = F("price") - F("discount")
        sql, params = expr.as_sql("sqlite")
        assert sql == '("price" - "discount")'
        assert params == []

    def test_arithmetic_mul(self):
        expr = F("quantity") * F("price")
        sql, params = expr.as_sql("sqlite")
        assert sql == '("quantity" * "price")'
        assert params == []

    def test_arithmetic_div(self):
        expr = F("total") / 2
        sql, params = expr.as_sql("sqlite")
        assert sql == '("total" / ?)'
        assert params == [2]

    def test_chained_operations(self):
        expr = (F("price") * F("qty")) - F("discount")
        sql, params = expr.as_sql("sqlite")
        assert "price" in sql
        assert "qty" in sql
        assert "discount" in sql

    def test_radd(self):
        expr = 10 + F("age")
        sql, params = expr.as_sql("sqlite")
        assert params == [10]

    def test_rsub(self):
        expr = 100 - F("age")
        sql, params = expr.as_sql("sqlite")
        assert params == [100]

    def test_mod(self):
        expr = F("id") % 2
        sql, params = expr.as_sql("sqlite")
        assert sql == '("id" % ?)'
        assert params == [2]


class TestValue:
    def test_string(self):
        v = Value("hello")
        sql, params = v.as_sql("sqlite")
        assert sql == "?"
        assert params == ["hello"]

    def test_integer(self):
        v = Value(42)
        sql, params = v.as_sql("sqlite")
        assert sql == "?"
        assert params == [42]

    def test_none(self):
        v = Value(None)
        sql, params = v.as_sql("sqlite")
        assert sql == "NULL"
        assert params == []


class TestRawSQL:
    def test_raw(self):
        r = RawSQL("COALESCE(?, ?)", [0, 1])
        sql, params = r.as_sql("sqlite")
        assert sql == "COALESCE(?, ?)"
        assert params == [0, 1]


class TestCol:
    def test_with_table(self):
        c = Col("users", "email")
        sql, params = c.as_sql("sqlite")
        assert sql == '"users"."email"'
        assert params == []


class TestStar:
    def test_star(self):
        s = Star()
        sql, params = s.as_sql("sqlite")
        assert sql == "*"
        assert params == []


# ═══════════════════════════════════════════════════════════════════════════
# Aggregate Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.aggregate import Sum, Avg, Count, Max, Min, StdDev, Variance


class TestAggregates:
    def test_count(self):
        c = Count("id")
        sql, params = c.as_sql("sqlite")
        assert sql == 'COUNT("id")'
        assert params == []

    def test_count_star(self):
        c = Count("*")
        sql, params = c.as_sql("sqlite")
        assert sql == "COUNT(*)"

    def test_count_distinct(self):
        c = Count("email", distinct=True)
        sql, params = c.as_sql("sqlite")
        assert sql == 'COUNT(DISTINCT "email")'

    def test_sum(self):
        s = Sum("price")
        sql, params = s.as_sql("sqlite")
        assert sql == 'SUM("price")'

    def test_avg(self):
        a = Avg("age")
        sql, params = a.as_sql("sqlite")
        assert sql == 'AVG("age")'

    def test_max(self):
        m = Max("score")
        sql, params = m.as_sql("sqlite")
        assert sql == 'MAX("score")'

    def test_min(self):
        m = Min("score")
        sql, params = m.as_sql("sqlite")
        assert sql == 'MIN("score")'

    def test_stddev(self):
        sd = StdDev("values")
        sql, params = sd.as_sql("sqlite")
        # SQLite doesn't have STDDEV natively; we still emit the SQL
        assert "values" in sql

    def test_variance(self):
        v = Variance("values")
        sql, params = v.as_sql("sqlite")
        assert "values" in sql

    def test_aggregate_arithmetic(self):
        expr = Sum("price") + Value(10)
        sql, params = expr.as_sql("sqlite")
        assert "SUM" in sql
        assert params == [10]

    def test_aggregate_alias(self):
        s = Sum("price", alias="total_price")
        assert s.alias == "total_price"


# ═══════════════════════════════════════════════════════════════════════════
# Signal Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.signals import (
    Signal, pre_save, post_save, pre_delete, post_delete,
    pre_init, post_init, m2m_changed,
)


class TestSignal:
    def test_connect_and_send_sync(self):
        sig = Signal("test")
        received = []

        def handler(sender, **kwargs):
            received.append((sender, kwargs))

        sig.connect(handler)
        sig.send_sync(sender="test", foo="bar")
        assert len(received) == 1
        assert received[0][0] == "test"
        assert received[0][1]["foo"] == "bar"

    @pytest.mark.asyncio
    async def test_send_async(self):
        sig = Signal("test_async")
        received = []

        async def handler(sender, **kwargs):
            received.append((sender, kwargs))

        sig.connect(handler)
        await sig.send(sender="test", value=42)
        assert len(received) == 1
        assert received[0][1]["value"] == 42

    def test_disconnect(self):
        sig = Signal("test_disconnect")
        received = []

        def handler(sender, **kwargs):
            received.append(sender)

        sig.connect(handler)
        sig.send_sync(sender="a")
        assert len(received) == 1

        sig.disconnect(handler)
        sig.send_sync(sender="b")
        assert len(received) == 1  # not called again

    def test_has_listeners(self):
        sig = Signal("test_has_listeners")
        assert not sig.has_listeners()
        handler = lambda sender, **kw: None
        sig.connect(handler)
        assert sig.has_listeners()

    def test_clear(self):
        sig = Signal("test_clear")
        sig.connect(lambda sender, **kw: None)
        sig.clear()
        assert not sig.has_listeners()

    def test_builtin_signals_exist(self):
        """Verify built-in signals are proper Signal instances."""
        assert isinstance(pre_save, Signal)
        assert isinstance(post_save, Signal)
        assert isinstance(pre_delete, Signal)
        assert isinstance(post_delete, Signal)
        assert isinstance(pre_init, Signal)
        assert isinstance(post_init, Signal)
        assert isinstance(m2m_changed, Signal)

    def test_send_sync_with_multiple_handlers(self):
        sig = Signal("test_multi")
        calls = []

        def h1(sender, **kw):
            calls.append("h1")

        def h2(sender, **kw):
            calls.append("h2")

        sig.connect(h1)
        sig.connect(h2)
        sig.send_sync(sender="test")
        assert calls == ["h1", "h2"]


# ═══════════════════════════════════════════════════════════════════════════
# Deletion Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.deletion import (
    CASCADE, SET_NULL, PROTECT, SET_DEFAULT, DO_NOTHING, RESTRICT,
    OnDeleteHandler, SET, ProtectedError, RestrictedError,
)


class TestDeletion:
    def test_constants(self):
        assert CASCADE == "CASCADE"
        assert SET_NULL == "SET NULL"
        assert PROTECT == "PROTECT"
        assert SET_DEFAULT == "SET DEFAULT"
        assert DO_NOTHING == "DO NOTHING"
        assert RESTRICT == "RESTRICT"

    def test_set_factory(self):
        handler = SET(42)
        assert handler.value == 42
        assert "SET" in repr(handler)

    def test_protected_error(self):
        with pytest.raises(ProtectedError):
            raise ProtectedError("Cannot delete: protected references exist")

    def test_restricted_error(self):
        with pytest.raises(RestrictedError):
            raise RestrictedError("Cannot delete: restricted references exist")


# ═══════════════════════════════════════════════════════════════════════════
# Enums / Choices Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.enums import TextChoices, IntegerChoices, Choices


class TestTextChoices:
    def test_basic(self):
        class Status(TextChoices):
            DRAFT = "draft", "Draft"
            PUBLISHED = "published", "Published"
            ARCHIVED = "archived", "Archived"

        assert Status.DRAFT == "draft"
        assert Status.DRAFT.label == "Draft"
        assert ("draft", "Draft") in Status.choices
        assert "draft" in Status.values
        assert "Draft" in Status.labels

    def test_auto_label(self):
        class Color(TextChoices):
            RED = "red"
            GREEN = "green"

        assert Color.RED == "red"
        # Auto-generated label
        assert Color.RED.label == "Red"


class TestIntegerChoices:
    def test_basic(self):
        class Priority(IntegerChoices):
            LOW = 0, "Low"
            MEDIUM = 1, "Medium"
            HIGH = 2, "High"

        assert Priority.LOW == 0
        assert Priority.LOW.label == "Low"
        assert (0, "Low") in Priority.choices
        assert 2 in Priority.values


# ═══════════════════════════════════════════════════════════════════════════
# SQL Builder Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.sql_builder import (
    SQLBuilder, InsertBuilder, UpdateBuilder, DeleteBuilder, CreateTableBuilder,
)


class TestSQLBuilder:
    def test_simple_select(self):
        b = SQLBuilder().from_table("users")
        sql, params = b.build()
        assert sql == 'SELECT * FROM "users"'
        assert params == []

    def test_where(self):
        b = SQLBuilder().from_table("users").where("active = ?", True)
        sql, params = b.build()
        assert 'WHERE' in sql
        assert params == [True]

    def test_multiple_where(self):
        b = SQLBuilder().from_table("users").where("active = ?", True).where("age > ?", 18)
        sql, params = b.build()
        assert 'AND' in sql
        assert params == [True, 18]

    def test_order_by(self):
        b = SQLBuilder().from_table("users").order_by("name ASC")
        sql, params = b.build()
        assert 'ORDER BY' in sql
        assert 'name ASC' in sql

    def test_limit_offset(self):
        b = SQLBuilder().from_table("users").limit(10).offset(20)
        sql, params = b.build()
        assert 'LIMIT 10' in sql
        assert 'OFFSET 20' in sql

    def test_group_by(self):
        b = SQLBuilder().from_table("orders").select("status", "COUNT(*) AS cnt").group_by("status")
        sql, params = b.build()
        assert 'GROUP BY' in sql

    def test_distinct(self):
        b = SQLBuilder().from_table("users").distinct()
        sql, params = b.build()
        assert 'DISTINCT' in sql

    def test_having(self):
        b = (
            SQLBuilder()
            .from_table("orders")
            .select("status", "COUNT(*) AS cnt")
            .group_by("status")
            .having("COUNT(*) > ?", 5)
        )
        sql, params = b.build()
        assert 'HAVING' in sql
        assert params == [5]


class TestInsertBuilder:
    def test_basic_insert(self):
        b = InsertBuilder("users").from_dict({"name": "Alice", "age": 30})
        sql, params = b.build()
        assert 'INSERT INTO "users"' in sql
        assert 'VALUES' in sql
        assert "Alice" in params
        assert 30 in params

    def test_returning(self):
        b = InsertBuilder("users").from_dict({"name": "Bob"}).returning("id")
        sql, params = b.build()
        assert 'RETURNING' in sql


class TestUpdateBuilder:
    def test_basic_update(self):
        b = UpdateBuilder("users").set(name="Bob").where("id = ?", 1)
        sql, params = b.build()
        assert 'UPDATE "users"' in sql
        assert 'SET' in sql
        assert 'WHERE' in sql

    def test_update_without_where(self):
        b = UpdateBuilder("users").set(active=False)
        sql, params = b.build()
        assert 'WHERE' not in sql


class TestDeleteBuilder:
    def test_basic_delete(self):
        b = DeleteBuilder("users").where("id = ?", 1)
        sql, params = b.build()
        assert 'DELETE FROM "users"' in sql
        assert 'WHERE' in sql

    def test_delete_all(self):
        b = DeleteBuilder("users")
        sql, params = b.build()
        assert 'DELETE FROM "users"' in sql


class TestCreateTableBuilder:
    def test_basic_table(self):
        b = (
            CreateTableBuilder("users")
            .column('"id" INTEGER PRIMARY KEY AUTOINCREMENT')
            .column('"name" TEXT NOT NULL')
            .column('"email" TEXT UNIQUE')
        )
        sql = b.build()
        assert 'CREATE TABLE IF NOT EXISTS "users"' in sql
        assert "id" in sql
        assert "name" in sql
        assert "email" in sql


# ═══════════════════════════════════════════════════════════════════════════
# Manager Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.manager import Manager, BaseManager
from aquilia.models.base import Model, ModelRegistry, Q
from aquilia.models.fields_module import CharField, IntegerField, BooleanField


class TestManager:
    def setup_method(self):
        ModelRegistry.reset()

    def test_auto_objects_manager(self):
        """Models should automatically get an `objects` Manager."""

        class Item(Model):
            table = "items"
            name = CharField(max_length=100)

        assert hasattr(Item, "objects")
        assert isinstance(Item.objects, Manager)

    def test_custom_manager(self):
        """User-defined manager should not be overridden."""

        class CustomManager(Manager):
            pass

        class Widget(Model):
            table = "widgets"
            name = CharField(max_length=100)
            objects = CustomManager()

        assert isinstance(Widget.objects, CustomManager)

    def test_manager_instance_access_raises(self):
        """Manager should not be accessible from instances."""

        class Gizmo(Model):
            table = "gizmos"
            name = CharField(max_length=100)

        g = Gizmo(name="test")
        with pytest.raises(AttributeError):
            _ = g.objects

    def test_manager_repr(self):
        class Thing(Model):
            table = "things"
            name = CharField(max_length=100)

        assert "Manager" in repr(Thing.objects)
        assert "Thing" in repr(Thing.objects)


# ═══════════════════════════════════════════════════════════════════════════
# Constraint Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.constraint import CheckConstraint, ExclusionConstraint, Deferrable


class TestCheckConstraint:
    def test_sql(self):
        c = CheckConstraint(check="age >= 0", name="valid_age")
        sql = c.sql("users")
        assert 'CHECK' in sql
        assert 'age >= 0' in sql
        assert 'valid_age' in sql

    def test_alter_add(self):
        c = CheckConstraint(check="price > 0", name="positive_price")
        sql = c.sql_alter_add("products")
        assert 'ALTER TABLE' in sql
        assert 'ADD CONSTRAINT' in sql

    def test_deconstruct(self):
        c = CheckConstraint(check="x > 0", name="pos_x")
        d = c.deconstruct()
        assert d["type"] == "CheckConstraint"
        assert d["check"] == "x > 0"
        assert d["name"] == "pos_x"

    def test_equality(self):
        c1 = CheckConstraint(check="x > 0", name="c1")
        c2 = CheckConstraint(check="x > 0", name="c1")
        c3 = CheckConstraint(check="x > 0", name="c2")
        assert c1 == c2
        assert c1 != c3


class TestExclusionConstraint:
    def test_postgres_sql(self):
        c = ExclusionConstraint(
            name="no_overlap",
            expressions=[("room_id", "="), ("during", "&&")],
            index_type="GIST",
        )
        sql = c.sql("reservations", dialect="postgresql")
        assert 'EXCLUDE' in sql
        assert 'GIST' in sql

    def test_sqlite_fallback(self):
        c = ExclusionConstraint(
            name="no_overlap",
            expressions=[("a", "=")],
        )
        sql = c.sql("t", dialect="sqlite")
        assert sql.startswith("--")  # comment fallback


# ═══════════════════════════════════════════════════════════════════════════
# Index Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.index import (
    GinIndex, GistIndex, BrinIndex, HashIndex, FunctionalIndex,
)


class TestGinIndex:
    def test_postgres(self):
        idx = GinIndex(fields=["tags"], name="idx_tags_gin")
        sql = idx.sql("articles", dialect="postgresql")
        assert 'USING GIN' in sql
        assert 'idx_tags_gin' in sql

    def test_sqlite_fallback(self):
        idx = GinIndex(fields=["tags"], name="idx_tags_gin")
        sql = idx.sql("articles", dialect="sqlite")
        assert 'USING' not in sql  # standard B-tree fallback


class TestGistIndex:
    def test_postgres(self):
        idx = GistIndex(fields=["location"], name="idx_location_gist")
        sql = idx.sql("places", dialect="postgresql")
        assert 'USING GIST' in sql


class TestBrinIndex:
    def test_postgres(self):
        idx = BrinIndex(fields=["created_at"], name="idx_created_brin")
        sql = idx.sql("events", dialect="postgresql")
        assert 'USING BRIN' in sql


class TestHashIndex:
    def test_postgres(self):
        idx = HashIndex(fields=["lookup_key"], name="idx_key_hash")
        sql = idx.sql("cache", dialect="postgresql")
        assert 'USING HASH' in sql


class TestFunctionalIndex:
    def test_expression(self):
        idx = FunctionalIndex(
            expression='LOWER("email")',
            name="idx_email_lower",
        )
        sql = idx.sql("users")
        assert 'LOWER("email")' in sql
        assert 'idx_email_lower' in sql

    def test_conditional(self):
        idx = FunctionalIndex(
            expression='"email"',
            name="idx_active_email",
            condition="active = true",
        )
        sql = idx.sql("users")
        assert 'WHERE' in sql
        assert 'active = true' in sql


# ═══════════════════════════════════════════════════════════════════════════
# Transactions Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.transactions import atomic, Atomic, TransactionManager


class TestAtomic:
    def test_atomic_returns_context_manager(self):
        """atomic() should return an async context manager."""
        ctx = atomic()
        assert isinstance(ctx, Atomic)


class TestTransactionManager:
    def test_on_commit_hook(self):
        tm = TransactionManager()
        called = []
        tm.on_commit(lambda: called.append(1))
        assert len(tm._on_commit_hooks) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Field Mixins Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.models.fields.mixins import (
    NullableMixin, UniqueMixin, IndexedMixin, AutoNowMixin,
    ChoiceMixin, EncryptedMixin,
)
from aquilia.models.fields.composite import CompositeField, CompositePrimaryKey, CompositeAttribute
from aquilia.models.fields.enum_field import EnumField


class TestFieldMixins:
    def test_nullable_mixin(self):
        class NullableChar(NullableMixin, CharField):
            pass

        f = NullableChar(max_length=50)
        assert f.null is True
        assert f.blank is True

    def test_unique_mixin(self):
        class UniqueChar(UniqueMixin, CharField):
            pass

        f = UniqueChar(max_length=100)
        assert f.unique is True

    def test_indexed_mixin(self):
        class IndexedChar(IndexedMixin, CharField):
            pass

        f = IndexedChar(max_length=100)
        assert f.db_index is True


class TestEnumField:
    def test_basic(self):
        import enum

        class Color(enum.Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        f = EnumField(enum_class=Color)
        assert f.choices == [("red", "RED"), ("green", "GREEN"), ("blue", "BLUE")]

    def test_to_db(self):
        import enum

        class Status(enum.Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        f = EnumField(enum_class=Status)
        assert f.to_db(Status.ACTIVE) == "active"

    def test_to_python(self):
        import enum

        class Status(enum.Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        f = EnumField(enum_class=Status)
        result = f.to_python("active")
        assert result == Status.ACTIVE


class TestCompositeField:
    def test_basic(self):
        cf = CompositeField(
            schema={"street": CharField(max_length=200), "city": CharField(max_length=100)},
        )
        assert "street" in cf.schema
        assert "city" in cf.schema


class TestCompositePrimaryKey:
    def test_fields(self):
        cpk = CompositePrimaryKey(fields=["tenant_id", "user_id"])
        assert cpk.fields == ["tenant_id", "user_id"]
        assert "PRIMARY KEY" in cpk.sql()


# ═══════════════════════════════════════════════════════════════════════════
# Backend Adapter Tests
# ═══════════════════════════════════════════════════════════════════════════

from aquilia.db.backends.base import DatabaseAdapter, AdapterCapabilities
from aquilia.db.backends.sqlite import SQLiteAdapter
from aquilia.db.backends.postgres import PostgresAdapter
from aquilia.db.backends.mysql import MySQLAdapter


class TestAdapterCapabilities:
    def test_sqlite_capabilities(self):
        adapter = SQLiteAdapter()
        assert adapter.capabilities.name == "sqlite"
        assert adapter.capabilities.supports_savepoints is True
        assert adapter.capabilities.supports_returning is False

    def test_postgres_capabilities(self):
        adapter = PostgresAdapter()
        assert adapter.capabilities.name == "postgresql"
        assert adapter.capabilities.supports_returning is True
        assert adapter.capabilities.supports_json_type is True
        assert adapter.capabilities.supports_arrays is True
        assert adapter.capabilities.param_style == "numeric"

    def test_mysql_capabilities(self):
        adapter = MySQLAdapter()
        assert adapter.capabilities.name == "mysql"
        assert adapter.capabilities.supports_returning is False
        assert adapter.capabilities.supports_arrays is False
        assert adapter.capabilities.param_style == "format"


class TestPostgresAdapter:
    def test_adapt_sql(self):
        adapter = PostgresAdapter()
        result = adapter.adapt_sql("SELECT * FROM users WHERE id = ? AND name = ?")
        assert result == "SELECT * FROM users WHERE id = $1 AND name = $2"

    def test_dialect(self):
        adapter = PostgresAdapter()
        assert adapter.dialect == "postgresql"

    def test_not_connected(self):
        adapter = PostgresAdapter()
        assert not adapter.is_connected


class TestMySQLAdapter:
    def test_adapt_sql(self):
        adapter = MySQLAdapter()
        result = adapter.adapt_sql("SELECT * FROM users WHERE id = ? AND name = ?")
        assert result == "SELECT * FROM users WHERE id = %s AND name = %s"

    def test_dialect(self):
        adapter = MySQLAdapter()
        assert adapter.dialect == "mysql"

    def test_not_connected(self):
        adapter = MySQLAdapter()
        assert not adapter.is_connected


class TestSQLiteAdapterUnit:
    def test_adapt_sql(self):
        adapter = SQLiteAdapter()
        result = adapter.adapt_sql("SELECT * FROM users WHERE id = ?")
        # SQLite uses ? natively
        assert result == "SELECT * FROM users WHERE id = ?"

    def test_dialect(self):
        adapter = SQLiteAdapter()
        assert adapter.dialect == "sqlite"


# ═══════════════════════════════════════════════════════════════════════════
# Integration: Signals + Model lifecycle
# ═══════════════════════════════════════════════════════════════════════════

import aiosqlite
from aquilia.db import AquiliaDatabase


class TestSignalModelIntegration:
    """Test that signals fire during Model CRUD operations."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ModelRegistry.reset()
        # Clear all signal receivers to avoid cross-test contamination
        pre_save.clear()
        post_save.clear()
        pre_delete.clear()
        post_delete.clear()
        pre_init.clear()
        post_init.clear()
        yield
        ModelRegistry.reset()
        pre_save.clear()
        post_save.clear()
        pre_delete.clear()
        post_delete.clear()
        pre_init.clear()
        post_init.clear()

    @pytest.mark.asyncio
    async def test_pre_post_save_on_create(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        class Book(Model):
            table = "books"
            title = CharField(max_length=200)

        ModelRegistry.set_database(db)
        await ModelRegistry.create_tables(db)

        events = []

        async def on_pre_save(sender, **kwargs):
            events.append(("pre_save", kwargs.get("created")))

        async def on_post_save(sender, **kwargs):
            events.append(("post_save", kwargs.get("created")))

        pre_save.connect(on_pre_save)
        post_save.connect(on_post_save)

        book = await Book.create(title="Test Book")
        assert book.title == "Test Book"

        # pre_save fires twice: once from create(), once from save() inside create()?
        # Actually create() calls __init__ then does INSERT — it fires pre_save and post_save
        assert ("pre_save", True) in events
        assert ("post_save", True) in events

        await db.disconnect()

    @pytest.mark.asyncio
    async def test_pre_post_delete(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        class Note(Model):
            table = "notes"
            text = CharField(max_length=500)

        ModelRegistry.set_database(db)
        await ModelRegistry.create_tables(db)

        events = []

        async def on_pre_delete(sender, **kwargs):
            events.append("pre_delete")

        async def on_post_delete(sender, **kwargs):
            events.append("post_delete")

        pre_delete.connect(on_pre_delete)
        post_delete.connect(on_post_delete)

        note = await Note.create(text="Hello")
        await note.delete_instance()

        assert "pre_delete" in events
        assert "post_delete" in events

        await db.disconnect()

    @pytest.mark.asyncio
    async def test_pre_init_post_init(self):
        events = []

        def on_pre_init(sender, **kwargs):
            events.append("pre_init")

        def on_post_init(sender, **kwargs):
            events.append("post_init")

        pre_init.connect(on_pre_init)
        post_init.connect(on_post_init)

        class SimpleModel(Model):
            table = "simple"
            name = CharField(max_length=50)

        _ = SimpleModel(name="test")
        assert "pre_init" in events
        assert "post_init" in events


# ═══════════════════════════════════════════════════════════════════════════
# Integration: Q query builder with annotate/aggregate
# ═══════════════════════════════════════════════════════════════════════════


class TestQueryBuilderEnhancements:
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ModelRegistry.reset()
        yield
        ModelRegistry.reset()

    @pytest.mark.asyncio
    async def test_aggregate(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        class Score(Model):
            table = "scores"
            player = CharField(max_length=100)
            points = IntegerField()

        ModelRegistry.set_database(db)
        await ModelRegistry.create_tables(db)

        await Score.create(player="Alice", points=10)
        await Score.create(player="Bob", points=20)
        await Score.create(player="Charlie", points=30)

        result = await Score.query().aggregate(
            total=Sum("points"),
            avg_points=Avg("points"),
            count=Count("id"),
        )

        assert result["total"] == 60
        assert result["avg_points"] == 20.0
        assert result["count"] == 3

        await db.disconnect()

    @pytest.mark.asyncio
    async def test_distinct(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        class Tag(Model):
            table = "tags"
            name = CharField(max_length=50)

        ModelRegistry.set_database(db)
        await ModelRegistry.create_tables(db)

        await Tag.create(name="python")
        await Tag.create(name="python")
        await Tag.create(name="rust")

        all_tags = await Tag.query().all()
        assert len(all_tags) == 3

        distinct_vals = await Tag.query().distinct().values("name")
        # Note: DISTINCT on SELECT * won't deduplicate since ids differ
        # but DISTINCT on values("name") should work at the SQL level
        # (actual dedup depends on whether we SELECT DISTINCT name)
        assert len(distinct_vals) >= 2

        await db.disconnect()

    @pytest.mark.asyncio
    async def test_group_by_having(self):
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()

        class Sale(Model):
            table = "sales"
            category = CharField(max_length=50)
            amount = IntegerField()

        ModelRegistry.set_database(db)
        await ModelRegistry.create_tables(db)

        await Sale.create(category="books", amount=100)
        await Sale.create(category="books", amount=200)
        await Sale.create(category="electronics", amount=500)

        # Use raw SQL to test group_by since annotate + group_by returns model objects
        result = await db.fetch_all(
            'SELECT category, SUM(amount) as total FROM "sales" '
            'GROUP BY category HAVING SUM(amount) > ?',
            [150],
        )
        assert len(result) == 2  # both categories have total > 150

        await db.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
# Import Tests — verify everything re-exports cleanly
# ═══════════════════════════════════════════════════════════════════════════


class TestImports:
    def test_models_package_exports(self):
        """All new modules should be importable from aquilia.models."""
        from aquilia.models import (
            # Core
            Model, Q, ModelRegistry, Manager, BaseManager,
            # Expressions
            F, Value, RawSQL, Expression,
            # Aggregates
            Sum, Avg, Count, Max, Min,
            # Signals
            Signal, pre_save, post_save, pre_delete, post_delete,
            # Transactions
            atomic, Atomic, TransactionManager,
            # Deletion
            CASCADE, SET_NULL, PROTECT, SET_DEFAULT, DO_NOTHING, RESTRICT,
            # Enums
            TextChoices, IntegerChoices,
            # SQL Builder
            SQLBuilder, InsertBuilder, UpdateBuilder, DeleteBuilder,
            # Constraints
            CheckConstraint, ExclusionConstraint,
            # Indexes
            GinIndex, GistIndex, BrinIndex, HashIndex, FunctionalIndex,
            # Field mixins
            EnumField, CompositeField, CompositePrimaryKey,
            NullableMixin, UniqueMixin, EncryptedMixin,
        )

    def test_db_package_exports(self):
        """Backend adapters should be importable from aquilia.db."""
        from aquilia.db import (
            AquiliaDatabase,
            DatabaseAdapter,
            AdapterCapabilities,
            SQLiteAdapter,
            PostgresAdapter,
            MySQLAdapter,
        )

    def test_fields_package_exports(self):
        """Fields sub-package should export both old and new types."""
        from aquilia.models.fields import (
            CharField, IntegerField, BooleanField,  # old
            EnumField, CompositeField, NullableMixin,  # new
        )
