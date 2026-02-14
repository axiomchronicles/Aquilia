"""
Tests for Model Runtime — ModelProxy, Q, ModelRegistry.

Tests the full $-prefixed async API with in-memory SQLite.

NOTE: Because ``$`` is not a valid Python identifier character,
we invoke the $-API via ``getattr(Cls, '$method')``.  At runtime
ModelProxy uses a metaclass ``__getattr__`` to dispatch these to
the underlying ``_dollar_*`` implementations.
"""

import pytest
from aquilia.models.parser import parse_amdl
from aquilia.models.runtime import (
    ModelProxy,
    ModelRegistry,
    Q,
    generate_create_table_sql,
)
from aquilia.db.engine import AquiliaDatabase


# ── Helpers ──────────────────────────────────────────────────────────────────

def dollar(obj, name):
    """Shorthand: getattr(obj, '$name')"""
    return getattr(obj, f"${name}")


# ── Fixtures ─────────────────────────────────────────────────────────────────

BLOG_AMDL = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot username :: Str [max=150, unique]
  slot email :: Str [max=255, nullable]
  slot created_at :: DateTime [default:=now_utc()]
  meta table = "aq_user"
≪ /MODEL ≫

≪ MODEL Post ≫
  slot id :: Auto [PK]
  slot title :: Str [max=300]
  slot body :: Text []
  slot author_id :: Int []
  link author -> ONE User [fk=author_id, back=posts]
  link tags -> MANY Tag [through=PostTag, back=posts]
  meta table = "blog_post"
≪ /MODEL ≫

≪ MODEL Tag ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100, unique]
  meta table = "blog_tag"
≪ /MODEL ≫

≪ MODEL PostTag ≫
  slot id :: Auto [PK]
  slot post_id :: Int []
  slot tag_id :: Int []
  index [post_id, tag_id] unique
  meta table = "blog_post_tag"
≪ /MODEL ≫
"""


@pytest.fixture
async def db():
    """In-memory SQLite database."""
    database = AquiliaDatabase("sqlite:///:memory:")
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def registry(db):
    """Model registry with blog models registered and tables created."""
    result = parse_amdl(BLOG_AMDL)
    assert not result.errors, f"Parse errors: {result.errors}"

    reg = ModelRegistry(db)
    for model in result.models:
        reg.register_model(model)

    await reg.create_tables(db)
    return reg


# ── SQL Generation ───────────────────────────────────────────────────────────


class TestSQLGeneration:
    """Test SQL generation from model nodes."""

    def test_create_table_sql(self):
        """Generate valid CREATE TABLE SQL."""
        result = parse_amdl("""
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100, unique]
  slot email :: Str [max=255, nullable]
  meta table = "test_user"
≪ /MODEL ≫
""")
        model = result.models[0]
        sql = generate_create_table_sql(model)

        assert 'CREATE TABLE IF NOT EXISTS "test_user"' in sql
        assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
        assert '"name" VARCHAR(100)' in sql
        assert "UNIQUE" in sql
        assert "NOT NULL" in sql


# ── ModelRegistry ────────────────────────────────────────────────────────────


class TestModelRegistry:
    """Test model registration and proxy generation."""

    def test_register_models(self, registry):
        """Models are registered with proxies."""
        assert registry.get_proxy("User") is not None
        assert registry.get_proxy("Post") is not None
        assert registry.get_proxy("Tag") is not None
        assert registry.get_proxy("PostTag") is not None

    def test_proxy_class_attrs(self, registry):
        """Proxy class has correct attributes."""
        User = registry.get_proxy("User")
        assert User._table_name == "aq_user"
        assert User._pk_name == "id"
        assert "username" in User._slot_names

    def test_emit_python(self, registry):
        """emit_python() produces valid source."""
        source = registry.emit_python()
        assert "class User(ModelProxy):" in source
        assert "class Post(ModelProxy):" in source
        assert '_table_name = "aq_user"' in source


# ── $create ──────────────────────────────────────────────────────────────────


class TestDollarCreate:
    """Test Model.$create() async API."""

    @pytest.mark.asyncio
    async def test_create_user(self, registry):
        """Create a user via $create."""
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "pawan", "email": "p@test.com"})

        assert user is not None
        assert user.username == "pawan"
        assert user.email == "p@test.com"
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_with_default(self, registry):
        """$create applies AMDL defaults."""
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "tester"})

        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_create_returns_instance(self, registry):
        """$create returns a ModelProxy instance."""
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "alice"})

        assert isinstance(user, ModelProxy)
        assert repr(user).startswith("<User")


# ── $get ─────────────────────────────────────────────────────────────────────


class TestDollarGet:
    """Test Model.$get() async API."""

    @pytest.mark.asyncio
    async def test_get_by_pk(self, registry):
        """Get user by primary key."""
        User = registry.get_proxy("User")
        created = await dollar(User, "create")({"username": "bob"})

        found = await dollar(User, "get")(pk=created.id)
        assert found is not None
        assert found.username == "bob"

    @pytest.mark.asyncio
    async def test_get_by_filters(self, registry):
        """Get user by filter kwargs."""
        User = registry.get_proxy("User")
        await dollar(User, "create")({"username": "carol"})

        found = await dollar(User, "get")(username="carol")
        assert found is not None
        assert found.username == "carol"

    @pytest.mark.asyncio
    async def test_get_not_found(self, registry):
        """$get returns None for missing PK."""
        User = registry.get_proxy("User")
        found = await dollar(User, "get")(pk=99999)
        assert found is None


# ── $query ───────────────────────────────────────────────────────────────────


class TestDollarQuery:
    """Test Model.$query() Q object."""

    @pytest.mark.asyncio
    async def test_query_all(self, registry):
        """Query all records."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "u1"})
        await create({"username": "u2"})
        await create({"username": "u3"})

        rows = await dollar(User, "query")().all()
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_query_where(self, registry):
        """Query with WHERE clause."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "active_user", "email": "a@test.com"})
        await create({"username": "other_user", "email": "b@test.com"})

        rows = await dollar(User, "query")().where('"username" = ?', "active_user").all()
        assert len(rows) == 1
        assert rows[0].username == "active_user"

    @pytest.mark.asyncio
    async def test_query_where_named(self, registry):
        """Query with named parameters."""
        User = registry.get_proxy("User")
        await dollar(User, "create")({"username": "named_test"})

        rows = await dollar(User, "query")().where(
            '"username" = :name', name="named_test"
        ).all()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_query_order(self, registry):
        """Query with ORDER BY."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "zzz"})
        await create({"username": "aaa"})

        rows = await dollar(User, "query")().order("username").all()
        assert rows[0].username == "aaa"
        assert rows[1].username == "zzz"

    @pytest.mark.asyncio
    async def test_query_order_desc(self, registry):
        """Query with DESC ordering."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "aaa"})
        await create({"username": "zzz"})

        rows = await dollar(User, "query")().order("-username").all()
        assert rows[0].username == "zzz"

    @pytest.mark.asyncio
    async def test_query_limit(self, registry):
        """Query with LIMIT."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        for i in range(5):
            await create({"username": f"u{i}"})

        rows = await dollar(User, "query")().limit(2).all()
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_query_count(self, registry):
        """Query count."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "c1"})
        await create({"username": "c2"})

        count = await dollar(User, "query")().count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_query_one(self, registry):
        """Query .one() returns exactly one."""
        User = registry.get_proxy("User")
        await dollar(User, "create")({"username": "only_one"})

        user = await dollar(User, "query")().where('"username" = ?', "only_one").one()
        assert user.username == "only_one"

    @pytest.mark.asyncio
    async def test_query_first(self, registry):
        """Query .first() returns first or None."""
        User = registry.get_proxy("User")
        result = await dollar(User, "query")().first()
        assert result is None

        await dollar(User, "create")({"username": "first_test"})
        result = await dollar(User, "query")().first()
        assert result is not None


# ── $update and $delete ──────────────────────────────────────────────────────


class TestDollarUpdateDelete:
    """Test $update and $delete."""

    @pytest.mark.asyncio
    async def test_update_by_filters(self, registry):
        """Update records by filter."""
        User = registry.get_proxy("User")
        await dollar(User, "create")({"username": "old_name"})

        count = await dollar(User, "update")(
            filters={"username": "old_name"},
            values={"username": "new_name"},
        )
        assert count == 1

        found = await dollar(User, "get")(username="new_name")
        assert found is not None

    @pytest.mark.asyncio
    async def test_delete_by_pk(self, registry):
        """Delete record by PK."""
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "to_delete"})

        count = await dollar(User, "delete")(pk=user.id)
        assert count == 1

        found = await dollar(User, "get")(pk=user.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_by_filters(self, registry):
        """Delete records by filter."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "del1"})
        await create({"username": "del2"})

        count = await dollar(User, "delete")(filters={"username": "del1"})
        assert count == 1

        remaining = await dollar(User, "query")().count()
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_query_update(self, registry):
        """Q.update() updates matching rows."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "qu1"})
        await create({"username": "qu2"})

        count = await dollar(User, "query")().where('"username" = ?', "qu1").update(
            {"email": "updated@test.com"}
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_query_delete(self, registry):
        """Q.delete() deletes matching rows."""
        User = registry.get_proxy("User")
        create = dollar(User, "create")
        await create({"username": "qd1"})
        await create({"username": "qd2"})

        count = await dollar(User, "query")().where('"username" = ?', "qd1").delete()
        assert count == 1


# ── to_dict ──────────────────────────────────────────────────────────────────


class TestToDict:
    """Test serialization."""

    @pytest.mark.asyncio
    async def test_to_dict(self, registry):
        """to_dict returns slot values."""
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "dict_test", "email": "d@test.com"})

        d = user.to_dict()
        assert d["username"] == "dict_test"
        assert d["email"] == "d@test.com"
        assert "id" in d
