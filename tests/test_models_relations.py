"""
Tests for Model Relationships — $link and $link_many.

Uses in-memory SQLite with the blog example models.
"""

import pytest
from aquilia.models.parser import parse_amdl
from aquilia.models.runtime import ModelProxy, ModelRegistry
from aquilia.db.engine import AquiliaDatabase


# ── Helper ───────────────────────────────────────────────────────────────────

def dollar(obj, name):
    """Shorthand: getattr(obj, '$name')"""
    return getattr(obj, f"${name}")


# ── AMDL source ──────────────────────────────────────────────────────────────

BLOG_AMDL = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot username :: Str [max=150, unique]
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
    database = AquiliaDatabase("sqlite:///:memory:")
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def registry(db):
    result = parse_amdl(BLOG_AMDL)
    assert not result.errors

    reg = ModelRegistry(db)
    for model in result.models:
        reg.register_model(model)
    await reg.create_tables(db)
    return reg


class TestDollarLink:
    """Test $link (ONE relationships)."""

    @pytest.mark.asyncio
    async def test_link_one(self, registry):
        """Access ONE relationship via $link."""
        User = registry.get_proxy("User")
        Post = registry.get_proxy("Post")

        user = await dollar(User, "create")({"username": "author1"})
        post = await dollar(Post, "create")({
            "title": "Hello World",
            "body": "Content here",
            "author_id": user.id,
        })

        # Access author via $link
        author = await dollar(post, "link")("author")
        assert author is not None
        assert author.username == "author1"
        assert author.id == user.id

    @pytest.mark.asyncio
    async def test_link_one_none(self, registry):
        """$link returns None when FK points to non-existent row."""
        Post = registry.get_proxy("Post")
        post = await dollar(Post, "create")({
            "title": "Orphan Post",
            "body": "No author",
            "author_id": 99999,
        })

        author = await dollar(post, "link")("author")
        assert author is None


class TestDollarLinkMany:
    """Test $link_many (MANY relationships)."""

    @pytest.mark.asyncio
    async def test_link_many_through(self, registry):
        """Access MANY relationship via $link_many (through table)."""
        User = registry.get_proxy("User")
        Post = registry.get_proxy("Post")
        Tag = registry.get_proxy("Tag")

        user = await dollar(User, "create")({"username": "tagger"})
        post = await dollar(Post, "create")({
            "title": "Tagged Post",
            "body": "Has tags",
            "author_id": user.id,
        })

        tag1 = await dollar(Tag, "create")({"name": "python"})
        tag2 = await dollar(Tag, "create")({"name": "aquilia"})

        # Create through records manually
        db = registry._db
        await db.execute(
            'INSERT INTO "blog_post_tag" ("post_id", "tag_id") VALUES (?, ?)',
            [post.id, tag1.id],
        )
        await db.execute(
            'INSERT INTO "blog_post_tag" ("post_id", "tag_id") VALUES (?, ?)',
            [post.id, tag2.id],
        )

        # Fetch via $link_many
        tags = await dollar(post, "link_many")("tags")
        assert len(tags) == 2
        tag_names = {t.name for t in tags}
        assert "python" in tag_names
        assert "aquilia" in tag_names

    @pytest.mark.asyncio
    async def test_link_many_attach(self, registry):
        """Attach via $link_many (creates through records)."""
        User = registry.get_proxy("User")
        Post = registry.get_proxy("Post")
        Tag = registry.get_proxy("Tag")

        user = await dollar(User, "create")({"username": "attacher"})
        post = await dollar(Post, "create")({
            "title": "Attach Test",
            "body": "Will attach tags",
            "author_id": user.id,
        })

        tag1 = await dollar(Tag, "create")({"name": "tag_a"})
        tag2 = await dollar(Tag, "create")({"name": "tag_b"})

        # Attach by PK
        await dollar(post, "link_many")("tags", [tag1.id, tag2.id])

        # Verify
        tags = await dollar(post, "link_many")("tags")
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_link_unknown_raises(self, registry):
        """$link with unknown name raises ModelNotFoundFault."""
        from aquilia.faults.domains import ModelNotFoundFault
        User = registry.get_proxy("User")
        user = await dollar(User, "create")({"username": "bad_link"})

        with pytest.raises(ModelNotFoundFault):
            await dollar(user, "link")("nonexistent")
