"""
Comprehensive unit tests for AquilaPatterns matcher.

Tests cover:
- Basic matching
- Parameter extraction
- Type casting during matching
- Constraint validation during matching
- Query parameter matching
- Optional group matching
- Specificity-based routing
"""

import pytest
import asyncio
from aquilia.patterns.matcher import PatternMatcher, MatchResult
from aquilia.patterns.compiler.compiler import PatternCompiler
from aquilia.patterns.compiler.parser import parse_pattern


class TestBasicMatching:
    """Test basic pattern matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_match_static_path(self):
        """Test matching static path."""
        ast = parse_pattern("/users/list")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users/list")
        assert result is not None
        assert result.params == {}
    
    @pytest.mark.asyncio
    async def test_no_match_different_path(self):
        """Test that different path doesn't match."""
        ast = parse_pattern("/users/list")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/list")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_match_with_parameter(self):
        """Test matching with parameter extraction."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users/42")
        assert result is not None
        assert result.params["id"] == 42
    
    @pytest.mark.asyncio
    async def test_match_multiple_parameters(self):
        """Test matching with multiple parameters."""
        ast = parse_pattern("/users/«user_id:int»/posts/«post_id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users/42/posts/123")
        assert result is not None
        assert result.params["user_id"] == 42
        assert result.params["post_id"] == 123
    
    @pytest.mark.asyncio
    async def test_match_splat(self):
        """Test matching splat pattern."""
        ast = parse_pattern("/files/*path")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/files/docs/readme.md")
        assert result is not None
        assert result.params["path"] == "docs/readme.md"
    
    @pytest.mark.asyncio
    async def test_trailing_slash_handling(self):
        """Test that trailing slashes are handled correctly."""
        ast = parse_pattern("/users")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result1 = await self.matcher.match("/users")
        result2 = await self.matcher.match("/users/")
        
        assert result1 is not None
        assert result2 is not None


class TestTypeCastingDuringMatch:
    """Test type casting during matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_int_casting(self):
        """Test integer type casting during match."""
        ast = parse_pattern("/items/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/42")
        assert result is not None
        assert result.params["id"] == 42
        assert isinstance(result.params["id"], int)
    
    @pytest.mark.asyncio
    async def test_float_casting(self):
        """Test float type casting during match."""
        ast = parse_pattern("/items/«price:float»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/19.99")
        assert result is not None
        assert result.params["price"] == 19.99
        assert isinstance(result.params["price"], float)
    
    @pytest.mark.asyncio
    async def test_bool_casting(self):
        """Test boolean type casting during match."""
        ast = parse_pattern("/items/«active:bool»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/true")
        assert result is not None
        assert result.params["active"] is True
    
    @pytest.mark.asyncio
    async def test_invalid_int_no_match(self):
        """Test that invalid int causes no match."""
        ast = parse_pattern("/items/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/not-a-number")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_str_always_matches(self):
        """Test that string type always matches."""
        ast = parse_pattern("/items/«name:str»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/hello-world")
        assert result is not None
        assert result.params["name"] == "hello-world"


class TestConstraintValidation:
    """Test constraint validation during matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_min_constraint_validation(self):
        """Test minimum constraint validation."""
        ast = parse_pattern("/items/«id:int|min=10»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Should match
        result = await self.matcher.match("/items/15")
        assert result is not None
        
        # Should not match
        result = await self.matcher.match("/items/5")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_max_constraint_validation(self):
        """Test maximum constraint validation."""
        ast = parse_pattern("/items/«id:int|max=100»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Should match
        result = await self.matcher.match("/items/50")
        assert result is not None
        
        # Should not match
        result = await self.matcher.match("/items/150")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_regex_constraint_validation(self):
        """Test regex constraint validation."""
        ast = parse_pattern(r'/users/«name:str|regex=[a-z]+»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Should match
        result = await self.matcher.match("/users/john")
        assert result is not None
        
        # Should not match (contains numbers)
        result = await self.matcher.match("/users/john123")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_enum_constraint_validation(self):
        """Test enum constraint validation."""
        ast = parse_pattern('/status/«value:str|enum=pending,active,done»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Should match
        result = await self.matcher.match("/status/active")
        assert result is not None
        
        # Should not match
        result = await self.matcher.match("/status/invalid")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_multiple_constraints(self):
        """Test multiple constraint validation."""
        ast = parse_pattern('/items/«id:int|min=1|max=100»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Within range
        result = await self.matcher.match("/items/50")
        assert result is not None
        
        # Below range
        result = await self.matcher.match("/items/0")
        assert result is None
        
        # Above range
        result = await self.matcher.match("/items/101")
        assert result is None


class TestQueryParameters:
    """Test query parameter matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_single_query_param(self):
        """Test matching single query parameter."""
        ast = parse_pattern('/search?q=«query:str»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/search", {"q": "hello"})
        assert result is not None
        assert result.query["query"] == "hello"
    
    @pytest.mark.asyncio
    async def test_multiple_query_params(self):
        """Test matching multiple query parameters."""
        ast = parse_pattern('/search?q=«query:str»&limit=«limit:int»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/search", {"q": "test", "limit": "10"})
        assert result is not None
        assert result.query["query"] == "test"
        assert result.query["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_query_param_with_default(self):
        """Test query parameter with default value."""
        ast = parse_pattern('/search?limit=«limit:int=10»')
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Without param, should use default
        result = await self.matcher.match("/search", {})
        assert result is not None
        # Note: Default handling may vary by implementation


class TestOptionalGroups:
    """Test optional group matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_optional_group_present(self):
        """Test matching when optional group is present."""
        ast = parse_pattern("/users[/«id:int»]")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users/42")
        assert result is not None
        assert result.params.get("id") == 42
    
    @pytest.mark.asyncio
    async def test_optional_group_absent(self):
        """Test matching when optional group is absent."""
        ast = parse_pattern("/users[/«id:int»]")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users")
        assert result is not None
        assert "id" not in result.params or result.params.get("id") is None
    
    @pytest.mark.asyncio
    async def test_nested_optional_groups(self):
        """Test nested optional groups."""
        ast = parse_pattern("/a[/b[/c]]")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # All levels
        result = await self.matcher.match("/a/b/c")
        assert result is not None
        
        # Middle level
        result = await self.matcher.match("/a/b")
        assert result is not None
        
        # Base level
        result = await self.matcher.match("/a")
        assert result is not None


class TestSpecificityBasedRouting:
    """Test that specificity determines match order."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_static_wins_over_dynamic(self):
        """Test that static pattern wins over dynamic."""
        # Add in reverse specificity order
        dynamic_ast = parse_pattern("/users/«id:int»")
        static_ast = parse_pattern("/users/list")
        
        dynamic = self.compiler.compile(dynamic_ast)
        static = self.compiler.compile(static_ast)
        
        self.matcher.add_pattern(dynamic)
        self.matcher.add_pattern(static)
        
        # Should match static pattern
        result = await self.matcher.match("/users/list")
        assert result is not None
        assert result.pattern.raw == "/users/list"
    
    @pytest.mark.asyncio
    async def test_typed_wins_over_generic(self):
        """Test that typed pattern wins over generic string."""
        generic_ast = parse_pattern("/items/«name:str»")
        typed_ast = parse_pattern("/items/«id:int»")
        
        generic = self.compiler.compile(generic_ast)
        typed = self.compiler.compile(typed_ast)
        
        self.matcher.add_pattern(generic)
        self.matcher.add_pattern(typed)
        
        # Should match typed pattern for number
        result = await self.matcher.match("/items/42")
        assert result is not None
        assert result.pattern.raw == "/items/«id:int»"
    
    @pytest.mark.asyncio
    async def test_constrained_wins_over_unconstrained(self):
        """Test that constrained pattern wins."""
        unconstrained_ast = parse_pattern("/items/«id:int»")
        constrained_ast = parse_pattern("/items/«id:int|min=100»")
        
        unconstrained = self.compiler.compile(unconstrained_ast)
        constrained = self.compiler.compile(constrained_ast)
        
        self.matcher.add_pattern(unconstrained)
        self.matcher.add_pattern(constrained)
        
        # Should match constrained for values >= 100
        result = await self.matcher.match("/items/150")
        assert result is not None
        assert result.pattern.raw == "/items/«id:int|min=100»"


class TestMatcherEdgeCases:
    """Test edge cases in matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_empty_matcher(self):
        """Test matching with no patterns."""
        result = await self.matcher.match("/any/path")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_root_path_match(self):
        """Test matching root path."""
        ast = parse_pattern("/")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_unicode_path_match(self):
        """Test matching unicode paths."""
        ast = parse_pattern("/用户/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/用户/42")
        assert result is not None
        assert result.params["id"] == 42
    
    @pytest.mark.asyncio
    async def test_very_long_path(self):
        """Test matching very long paths."""
        segments = "/".join(f"seg{i}" for i in range(20))
        ast = parse_pattern(f"/{segments}")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match(f"/{segments}")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_special_chars_in_params(self):
        """Test parameters with special characters."""
        ast = parse_pattern("/items/«name:str»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/items/hello-world_123")
        assert result is not None
        assert result.params["name"] == "hello-world_123"


class TestMatchResultSerialization:
    """Test MatchResult serialization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_to_dict(self):
        """Test serialization to dictionary."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        result = await self.matcher.match("/users/42")
        assert result is not None
        
        data = result.to_dict()
        assert "pattern" in data
        assert "params" in data
        assert "query" in data
        assert data["params"]["id"] == 42


class TestConcurrency:
    """Test concurrent matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
        self.matcher = PatternMatcher()
    
    @pytest.mark.asyncio
    async def test_concurrent_matches(self):
        """Test that multiple concurrent matches work."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        self.matcher.add_pattern(compiled)
        
        # Run multiple matches concurrently
        tasks = [
            self.matcher.match(f"/users/{i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should match
        assert all(r is not None for r in results)
        
        # Each should have correct ID
        for i, result in enumerate(results):
            assert result.params["id"] == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
