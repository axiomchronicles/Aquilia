"""
Tests for AMDL Parser — Aquilia Model Definition Language.

Validates:
- Parsing of all directive types
- AST node generation
- Error handling for malformed input
- File and directory parsing
"""

import pytest
from aquilia.models.parser import (
    parse_amdl,
    parse_amdl_file,
    AMDLParseError,
)
from aquilia.models.ast_nodes import (
    FieldType,
    LinkKind,
    ModelNode,
)


# ── Basic parsing ────────────────────────────────────────────────────────────


class TestAMDLParserBasic:
    """Test basic AMDL parsing."""

    def test_parse_empty(self):
        """Empty source produces empty result."""
        result = parse_amdl("")
        assert result.models == []
        assert result.errors == []

    def test_parse_comments_only(self):
        """Comments and blanks are ignored."""
        source = """
# This is a comment
# Another comment

"""
        result = parse_amdl(source)
        assert result.models == []
        assert result.errors == []

    def test_parse_single_model(self):
        """Parse a minimal model stanza."""
        source = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.models) == 1
        assert result.errors == []

        model = result.models[0]
        assert model.name == "User"
        assert len(model.slots) == 2

    def test_parse_slot_auto_pk(self):
        """Auto type implies PK."""
        source = """
≪ MODEL Item ≫
  slot id :: Auto [PK]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        model = result.models[0]
        slot = model.slots[0]

        assert slot.name == "id"
        assert slot.field_type == FieldType.AUTO
        assert slot.is_pk is True

    def test_parse_slot_modifiers(self):
        """Parse slot with multiple modifiers."""
        source = """
≪ MODEL User ≫
  slot email :: Str [max=255, unique, nullable]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        slot = result.models[0].slots[0]

        assert slot.name == "email"
        assert slot.field_type == FieldType.STR
        assert slot.max_length == 255
        assert slot.is_unique is True
        assert slot.is_nullable is True

    def test_parse_slot_default(self):
        """Parse slot with default expression."""
        source = """
≪ MODEL User ≫
  slot created_at :: DateTime [default:=now_utc()]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        slot = result.models[0].slots[0]

        assert slot.default_expr == "now_utc()"

    def test_parse_slot_empty_modifiers(self):
        """Parse slot with empty brackets."""
        source = """
≪ MODEL Post ≫
  slot body :: Text []
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.models) == 1
        slot = result.models[0].slots[0]
        assert slot.name == "body"
        assert slot.field_type == FieldType.TEXT

    def test_parse_decimal_type(self):
        """Parse Decimal type with precision and scale."""
        source = """
≪ MODEL Product ≫
  slot price :: Decimal(10,2) []
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        slot = result.models[0].slots[0]
        assert slot.field_type == FieldType.DECIMAL
        assert slot.type_params == (10, 2)


# ── Relationships ────────────────────────────────────────────────────────────


class TestAMDLParserLinks:
    """Test link directive parsing."""

    def test_parse_link_one(self):
        """Parse ONE relationship."""
        source = """
≪ MODEL Post ≫
  link author -> ONE User [fk=author_id, back=posts]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        link = result.models[0].links[0]

        assert link.name == "author"
        assert link.kind == LinkKind.ONE
        assert link.target_model == "User"
        assert link.fk_field == "author_id"
        assert link.back_name == "posts"

    def test_parse_link_many_through(self):
        """Parse MANY relationship with through model."""
        source = """
≪ MODEL Post ≫
  link tags -> MANY Tag [through=PostTag, back=posts]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        link = result.models[0].links[0]

        assert link.name == "tags"
        assert link.kind == LinkKind.MANY
        assert link.target_model == "Tag"
        assert link.through_model == "PostTag"
        assert link.back_name == "posts"


# ── Index, Hook, Meta, Note ──────────────────────────────────────────────────


class TestAMDLParserDirectives:
    """Test index, hook, meta, and note directives."""

    def test_parse_index_unique(self):
        """Parse unique composite index."""
        source = """
≪ MODEL PostTag ≫
  index [post_id, tag_id] unique
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        idx = result.models[0].indexes[0]

        assert idx.fields == ["post_id", "tag_id"]
        assert idx.is_unique is True

    def test_parse_index_non_unique(self):
        """Parse non-unique index."""
        source = """
≪ MODEL Post ≫
  index [author_id]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        idx = result.models[0].indexes[0]

        assert idx.fields == ["author_id"]
        assert idx.is_unique is False

    def test_parse_hook(self):
        """Parse hook directive."""
        source = """
≪ MODEL User ≫
  hook before_save -> hash_password
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        hook = result.models[0].hooks[0]

        assert hook.event == "before_save"
        assert hook.handler_name == "hash_password"

    def test_parse_meta(self):
        """Parse meta directive."""
        source = """
≪ MODEL User ≫
  meta table = "aq_user"
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert result.models[0].meta["table"] == "aq_user"
        assert result.models[0].table_name == "aq_user"

    def test_parse_note(self):
        """Parse note directive."""
        source = """
≪ MODEL User ≫
  note "Core user model for auth"
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert "Core user model for auth" in result.models[0].notes


# ── Multiple models ──────────────────────────────────────────────────────────


class TestAMDLParserMultiModel:
    """Test multi-model parsing."""

    def test_parse_multiple_models(self):
        """Parse multiple models in one file."""
        source = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
  meta table = "users"
≪ /MODEL ≫

≪ MODEL Post ≫
  slot id :: Auto [PK]
  slot title :: Str [max=200]
  meta table = "posts"
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.models) == 2
        assert result.models[0].name == "User"
        assert result.models[1].name == "Post"


# ── Error handling ───────────────────────────────────────────────────────────


class TestAMDLParserErrors:
    """Test error handling."""

    def test_unclosed_model(self):
        """Detect unclosed MODEL stanza."""
        source = """
≪ MODEL User ≫
  slot id :: Auto [PK]
"""
        result = parse_amdl(source)
        assert len(result.errors) > 0
        assert "Unclosed" in result.errors[0]

    def test_nested_model(self):
        """Detect nested MODEL stanza."""
        source = """
≪ MODEL User ≫
  ≪ MODEL Post ≫
  ≪ /MODEL ≫
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.errors) > 0
        assert "Nested" in result.errors[0]

    def test_directive_outside_model(self):
        """Detect directive outside MODEL stanza."""
        source = """
slot name :: Str [max=100]
"""
        result = parse_amdl(source)
        assert len(result.errors) > 0
        assert "outside" in result.errors[0]

    def test_disallowed_default(self):
        """Reject disallowed default expressions."""
        source = """
≪ MODEL Bad ≫
  slot x :: Str [default:=eval("bad")]
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.errors) > 0
        assert "Disallowed" in result.errors[0]

    def test_unknown_type(self):
        """Reject unknown field types."""
        source = """
≪ MODEL Bad ≫
  slot x :: FakeType []
≪ /MODEL ≫
"""
        result = parse_amdl(source)
        assert len(result.errors) > 0


# ── Fingerprint ──────────────────────────────────────────────────────────────


class TestModelFingerprint:
    """Test model fingerprinting for migration diffing."""

    def test_fingerprint_deterministic(self):
        """Same model produces same fingerprint."""
        source = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
≪ /MODEL ≫
"""
        r1 = parse_amdl(source)
        r2 = parse_amdl(source)
        assert r1.models[0].fingerprint() == r2.models[0].fingerprint()

    def test_fingerprint_changes_with_schema(self):
        """Different schema produces different fingerprint."""
        s1 = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=100]
≪ /MODEL ≫
"""
        s2 = """
≪ MODEL User ≫
  slot id :: Auto [PK]
  slot name :: Str [max=200]
≪ /MODEL ≫
"""
        r1 = parse_amdl(s1)
        r2 = parse_amdl(s2)
        assert r1.models[0].fingerprint() != r2.models[0].fingerprint()


# ── File parsing ─────────────────────────────────────────────────────────────


class TestAMDLFileParsing:
    """Test file-based parsing."""

    def test_parse_blog_example(self):
        """Parse the blog example file."""
        import os
        blog_path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "blog", "models.amdl"
        )
        if not os.path.exists(blog_path):
            pytest.skip("Blog example not found")

        result = parse_amdl_file(blog_path)
        model_names = [m.name for m in result.models]
        assert "User" in model_names
        assert "Post" in model_names
        assert "Tag" in model_names
        assert "PostTag" in model_names

    def test_parse_nonexistent_file(self):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_amdl_file("/nonexistent/path.amdl")
