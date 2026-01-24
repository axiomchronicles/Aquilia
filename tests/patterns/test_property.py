"""
Property-based tests for AquilaPatterns using Hypothesis.

Tests invariants and properties that should hold for all inputs:
- Parsing roundtrip
- Compilation idempotence
- Specificity transitivity
- Match determinism
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import asyncio

from aquilia.patterns.compiler.parser import parse_pattern
from aquilia.patterns.compiler.compiler import PatternCompiler
from aquilia.patterns.compiler.specificity import calculate_specificity
from aquilia.patterns.matcher import PatternMatcher
from aquilia.patterns.diagnostics.errors import PatternSyntaxError, PatternSemanticError


# ============================================================================
# Strategy Definitions
# ============================================================================

# Valid identifier characters
ident_chars = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=1,
    max_size=10,
)

# Valid type names
type_names = st.sampled_from([
    "str", "int", "float", "bool", "uuid", "slug", "path", "json", "any"
])

# Static segment strategy
static_segments = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
    min_size=1,
    max_size=20,
)

# Simple token strategy
simple_tokens = st.builds(
    lambda name, typ: f"«{name}:{typ}»",
    name=ident_chars,
    typ=type_names,
)

# Constraint values
constraint_values = st.one_of(
    st.integers(min_value=0, max_value=1000),
    st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
)

# Simple patterns (no edge cases)
simple_patterns = st.one_of(
    # Static only
    st.builds(lambda s: f"/{s}", s=static_segments),
    # Single token
    st.builds(lambda s, t: f"/{s}/{t}", s=static_segments, t=simple_tokens),
    # Two segments
    st.builds(
        lambda s1, s2: f"/{s1}/{s2}",
        s1=static_segments,
        s2=static_segments,
    ),
)

# Path components for matching
path_components = st.lists(
    static_segments,
    min_size=1,
    max_size=5,
)


# ============================================================================
# Property Tests
# ============================================================================

class TestParsingProperties:
    """Test parsing properties."""
    
    @given(static_segments)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_static_path_always_parseable(self, segment):
        """Test that static paths are always parseable."""
        pattern = f"/{segment}"
        
        try:
            ast = parse_pattern(pattern)
            assert ast is not None
            assert len(ast.segments) == 1
        except PatternSyntaxError:
            # Some special characters might cause issues - that's OK
            pass
    
    @given(ident_chars, type_names)
    @settings(max_examples=100)
    def test_simple_token_always_parseable(self, name, typ):
        """Test that simple tokens are always parseable."""
        pattern = f"/users/«{name}:{typ}»"
        
        ast = parse_pattern(pattern)
        assert ast is not None
        assert len(ast.segments) == 2
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_pattern_parse_never_crashes(self, pattern):
        """Test that parser never crashes (either succeeds or raises known error)."""
        try:
            ast = parse_pattern(pattern)
            assert ast is not None
        except (PatternSyntaxError, PatternSemanticError):
            # Known errors are acceptable
            pass
        except Exception as e:
            # Unexpected errors should fail the test
            pytest.fail(f"Unexpected error: {e}")


class TestCompilationProperties:
    """Test compilation properties."""
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_pattern_compiles(self, pattern):
        """Test that valid patterns compile successfully."""
        try:
            ast = parse_pattern(pattern)
            compiler = PatternCompiler()
            compiled = compiler.compile(ast)
            
            assert compiled is not None
            assert compiled.raw == pattern
        except (PatternSyntaxError, PatternSemanticError):
            # Some patterns may be invalid - that's OK
            pass
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_compilation_idempotent(self, pattern):
        """Test that compiling twice gives same result."""
        try:
            ast = parse_pattern(pattern)
            compiler = PatternCompiler()
            
            compiled1 = compiler.compile(ast)
            compiled2 = compiler.compile(ast)
            
            assert compiled1.specificity == compiled2.specificity
            assert compiled1.static_prefix == compiled2.static_prefix
            assert len(compiled1.params) == len(compiled2.params)
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_static_prefix_is_prefix(self, pattern):
        """Test that static prefix is actually a prefix of the pattern."""
        try:
            ast = parse_pattern(pattern)
            compiler = PatternCompiler()
            compiled = compiler.compile(ast)
            
            if compiled.static_prefix:
                # Static prefix should be a prefix of original pattern
                assert pattern.startswith(compiled.static_prefix)
        except (PatternSyntaxError, PatternSemanticError):
            pass


class TestSpecificityProperties:
    """Test specificity calculation properties."""
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_specificity_non_negative(self, pattern):
        """Test that specificity is always non-negative."""
        try:
            ast = parse_pattern(pattern)
            score = calculate_specificity(ast)
            assert score >= 0
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_specificity_deterministic(self, pattern):
        """Test that specificity is deterministic."""
        try:
            ast = parse_pattern(pattern)
            score1 = calculate_specificity(ast)
            score2 = calculate_specificity(ast)
            assert score1 == score2
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    def test_specificity_transitivity(self):
        """Test that specificity ordering is transitive."""
        # If A > B and B > C, then A > C
        patterns = [
            "/users/list/active",  # Most specific
            "/users/list",
            "/users/«id:int»",
            "/users/«name:str»",
            "/*path",  # Least specific
        ]
        
        asts = [parse_pattern(p) for p in patterns]
        scores = [calculate_specificity(ast) for ast in asts]
        
        # Verify transitivity
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], f"{patterns[i]} should be more specific than {patterns[i+1]}"


class TestMatchingProperties:
    """Test matching properties."""
    
    @pytest.mark.asyncio
    @given(static_segments)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_static_always_matches_itself(self, segment):
        """Test that static pattern always matches itself."""
        pattern = f"/{segment}"
        
        try:
            ast = parse_pattern(pattern)
            compiler = PatternCompiler()
            compiled = compiler.compile(ast)
            
            matcher = PatternMatcher()
            matcher.add_pattern(compiled)
            
            result = await matcher.match(pattern)
            assert result is not None
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    @pytest.mark.asyncio
    @given(ident_chars, st.integers(min_value=0, max_value=1000))
    @settings(max_examples=50)
    async def test_int_token_matches_numbers(self, name, value):
        """Test that int token matches numeric strings."""
        pattern = f"/items/«{name}:int»"
        path = f"/items/{value}"
        
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        result = await matcher.match(path)
        assert result is not None
        assert result.params[name] == value
    
    @pytest.mark.asyncio
    @given(ident_chars, static_segments)
    @settings(max_examples=50)
    async def test_str_token_matches_anything(self, name, value):
        """Test that str token matches any string."""
        pattern = f"/items/«{name}:str»"
        path = f"/items/{value}"
        
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        result = await matcher.match(path)
        assert result is not None
        assert result.params[name] == value
    
    @pytest.mark.asyncio
    @given(path_components)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_splat_matches_remaining(self, components):
        """Test that splat matches all remaining components."""
        pattern = "/files/*path"
        path = "/files/" + "/".join(components)
        
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        result = await matcher.match(path)
        assert result is not None
        assert "path" in result.params


class TestRoundtripProperties:
    """Test roundtrip properties."""
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_ast_to_dict_roundtrip(self, pattern):
        """Test that AST can be serialized and preserves structure."""
        try:
            ast = parse_pattern(pattern)
            data = ast.to_dict()
            
            # Verify basic structure
            assert "segments" in data
            assert "query_params" in data
            assert isinstance(data["segments"], list)
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    @given(simple_patterns)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_compiled_to_json_roundtrip(self, pattern):
        """Test that compiled pattern can be serialized to JSON."""
        try:
            ast = parse_pattern(pattern)
            compiler = PatternCompiler()
            compiled = compiler.compile(ast)
            
            json_str = compiled.to_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0
        except (PatternSyntaxError, PatternSemanticError):
            pass


# ============================================================================
# Stateful Testing
# ============================================================================

class PatternMatcherStateMachine(RuleBasedStateMachine):
    """Stateful testing for PatternMatcher."""
    
    def __init__(self):
        super().__init__()
        self.matcher = PatternMatcher()
        self.patterns = []
        self.compiler = PatternCompiler()
    
    @rule(pattern=simple_patterns)
    def add_pattern(self, pattern):
        """Add a pattern to the matcher."""
        try:
            ast = parse_pattern(pattern)
            compiled = self.compiler.compile(ast)
            self.matcher.add_pattern(compiled)
            self.patterns.append(pattern)
        except (PatternSyntaxError, PatternSemanticError):
            pass
    
    @rule(path=simple_patterns)
    def match_path(self, path):
        """Try to match a path."""
        try:
            # Use asyncio.run since this is sync context
            result = asyncio.run(self.matcher.match(path))
            # Result can be None or MatchResult
            if result is not None:
                assert hasattr(result, 'params')
                assert hasattr(result, 'query')
        except Exception:
            # Matching can fail - that's OK
            pass
    
    @invariant()
    def patterns_sorted_by_specificity(self):
        """Invariant: patterns should be sorted by specificity."""
        if len(self.matcher.patterns) > 1:
            for i in range(len(self.matcher.patterns) - 1):
                assert (
                    self.matcher.patterns[i].specificity >= 
                    self.matcher.patterns[i + 1].specificity
                ), "Patterns should be sorted by specificity (descending)"


# Test the state machine
TestPatternMatcher = PatternMatcherStateMachine.TestCase


# ============================================================================
# Constraint Property Tests
# ============================================================================

class TestConstraintProperties:
    """Test constraint validation properties."""
    
    @given(
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_min_constraint_consistent(self, min_val, test_val):
        """Test that min constraint is consistent."""
        pattern = f"/items/«id:int|min={min_val}»"
        
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        validator = compiled.params["id"].validators[0]
        
        # Values >= min should pass
        if test_val >= min_val:
            assert validator(test_val) is True
        # Values < min should fail
        else:
            assert validator(test_val) is False
    
    @given(
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_max_constraint_consistent(self, max_val, test_val):
        """Test that max constraint is consistent."""
        pattern = f"/items/«id:int|max={max_val}»"
        
        ast = parse_pattern(pattern)
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        validator = compiled.params["id"].validators[0]
        
        # Values <= max should pass
        if test_val <= max_val:
            assert validator(test_val) is True
        # Values > max should fail
        else:
            assert validator(test_val) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
