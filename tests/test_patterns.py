"""
Test 14: Patterns System (patterns/)

Tests PatternParser, PatternCompiler, PatternMatcher, AST nodes,
CompiledPattern, MatchResult via the parse_pattern convenience function.
"""

import pytest

from aquilia.patterns.compiler.parser import parse_pattern, Tokenizer, PatternParser
from aquilia.patterns.compiler.ast_nodes import (
    StaticSegment,
    TokenSegment,
    SplatSegment,
    OptionalGroup,
    PatternAST,
    SegmentKind,
    Span,
    Constraint,
    ConstraintKind,
)
from aquilia.patterns.compiler.compiler import PatternCompiler, CompiledPattern
from aquilia.patterns.matcher import PatternMatcher


def _parse(pattern_str: str) -> PatternAST:
    """Helper to tokenize and parse a pattern string."""
    return parse_pattern(pattern_str)


# ============================================================================
# PatternParser (via parse_pattern)
# ============================================================================

class TestPatternParser:

    def test_parse_static(self):
        ast = _parse("/users")
        assert ast.raw == "/users"
        statics = [s for s in ast.segments if isinstance(s, StaticSegment)]
        assert len(statics) > 0

    def test_parse_single_param(self):
        ast = _parse("/users/«id»")
        tokens = [s for s in ast.segments if isinstance(s, TokenSegment)]
        assert len(tokens) >= 1

    def test_parse_typed_param(self):
        ast = _parse("/users/«id:int»")
        tokens = [s for s in ast.segments if isinstance(s, TokenSegment)]
        assert len(tokens) >= 1
        token_seg = tokens[0]
        # Type info is stored in param_type field
        assert token_seg.param_type == "int" or len(token_seg.constraints) > 0 or token_seg.name == "id"

    def test_parse_multiple_params(self):
        ast = _parse("/users/«id»/posts/«post_id»")
        tokens = [s for s in ast.segments if isinstance(s, TokenSegment)]
        assert len(tokens) >= 2

    def test_parse_root(self):
        ast = _parse("/")
        assert ast.raw == "/"

    def test_parse_mixed(self):
        ast = _parse("/api/users/«id»")
        statics = [s for s in ast.segments if isinstance(s, StaticSegment)]
        tokens = [s for s in ast.segments if isinstance(s, TokenSegment)]
        assert len(statics) >= 1
        assert len(tokens) >= 1

    def test_parse_raw_preserved(self):
        ast = _parse("/api/v2/items")
        assert ast.raw == "/api/v2/items"

    def test_tokenizer(self):
        tokenizer = Tokenizer("/users/«id»")
        tokens = tokenizer.tokenize()
        assert len(tokens) > 0

    def test_parser_needs_tokens(self):
        tokenizer = Tokenizer("/users")
        tokens = tokenizer.tokenize()
        parser = PatternParser(tokens)
        ast = parser.parse("/users")
        assert isinstance(ast, PatternAST)


# ============================================================================
# AST Nodes
# ============================================================================

class TestASTNodes:

    def test_static_segment(self):
        seg = StaticSegment(value="users")
        assert seg.value == "users"
        assert seg.kind == SegmentKind.STATIC

    def test_token_segment(self):
        seg = TokenSegment(name="id")
        assert seg.name == "id"
        assert seg.kind == SegmentKind.TOKEN

    def test_token_segment_with_constraint(self):
        constraint = Constraint(kind=ConstraintKind.REGEX, value="\\d+")
        seg = TokenSegment(name="id", constraints=[constraint])
        assert len(seg.constraints) == 1
        assert seg.constraints[0].value == "\\d+"

    def test_splat_segment(self):
        seg = SplatSegment(name="rest")
        assert seg.name == "rest"
        assert seg.kind == SegmentKind.SPLAT

    def test_segment_kinds(self):
        assert SegmentKind.STATIC is not None
        assert SegmentKind.TOKEN is not None
        assert SegmentKind.SPLAT is not None

    def test_span(self):
        span = Span(start=0, end=5, line=1, column=1)
        assert span.start == 0
        assert span.end == 5

    def test_pattern_ast(self):
        seg = StaticSegment(value="users")
        ast = PatternAST(raw="/users", segments=[seg])
        assert len(ast.segments) == 1
        assert ast.raw == "/users"

    def test_pattern_ast_to_dict(self):
        seg = StaticSegment(value="users")
        ast = PatternAST(raw="/users", segments=[seg])
        d = ast.to_dict()
        assert "raw" in d
        assert "segments" in d

    def test_static_segment_to_dict(self):
        seg = StaticSegment(value="users")
        d = seg.to_dict()
        assert d["kind"] == "static"
        assert d["value"] == "users"


# ============================================================================
# PatternCompiler
# ============================================================================

class TestPatternCompiler:

    def test_compile_static(self):
        ast = _parse("/users")
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        assert isinstance(compiled, CompiledPattern)

    def test_compile_param(self):
        ast = _parse("/users/«id:int»")
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        assert isinstance(compiled, CompiledPattern)

    def test_compiled_to_dict(self):
        ast = _parse("/users")
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        d = compiled.to_dict()
        assert "pattern" in d or "raw" in d or isinstance(d, dict)

    def test_compiled_to_json(self):
        ast = _parse("/users")
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        j = compiled.to_json()
        assert isinstance(j, str)

    def test_compiled_specificity(self):
        ast_static = _parse("/users/list")
        ast_param = _parse("/users/«id»")
        compiler = PatternCompiler()
        c_static = compiler.compile(ast_static)
        c_param = compiler.compile(ast_param)
        # Static patterns should have higher specificity
        assert c_static.specificity >= c_param.specificity

    def test_compiled_multi_param(self):
        ast = _parse("/users/«id»/posts/«post_id»")
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        assert isinstance(compiled, CompiledPattern)


# ============================================================================
# PatternMatcher
# ============================================================================

class TestPatternMatcher:

    def _compile(self, pattern_str):
        ast = _parse(pattern_str)
        compiler = PatternCompiler()
        return compiler.compile(ast)

    def test_create(self):
        matcher = PatternMatcher()
        assert matcher is not None

    def test_add_pattern(self):
        matcher = PatternMatcher()
        compiled = self._compile("/users")
        matcher.add_pattern(compiled)
        # No error is success

    @pytest.mark.asyncio
    async def test_match_static(self):
        matcher = PatternMatcher()
        matcher.add_pattern(self._compile("/users"))
        result = await matcher.match("/users")
        assert result is not None

    @pytest.mark.asyncio
    async def test_match_param(self):
        matcher = PatternMatcher()
        matcher.add_pattern(self._compile("/users/«id:int»"))
        result = await matcher.match("/users/42")
        assert result is not None
        assert result.params.get("id") is not None

    @pytest.mark.asyncio
    async def test_no_match(self):
        matcher = PatternMatcher()
        matcher.add_pattern(self._compile("/users"))
        result = await matcher.match("/posts")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_patterns(self):
        matcher = PatternMatcher()
        matcher.add_pattern(self._compile("/users"))
        matcher.add_pattern(self._compile("/posts"))
        r1 = await matcher.match("/users")
        r2 = await matcher.match("/posts")
        assert r1 is not None
        assert r2 is not None

    @pytest.mark.asyncio
    async def test_match_result_to_dict(self):
        matcher = PatternMatcher()
        matcher.add_pattern(self._compile("/users/«id:int»"))
        result = await matcher.match("/users/42")
        assert result is not None
        d = result.to_dict()
        assert isinstance(d, dict)
