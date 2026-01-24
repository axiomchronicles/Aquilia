"""
Integration tests for AquilaPatterns full pipeline.

Tests the complete flow:
- Parse → Compile → Match
- Multiple patterns in router
- OpenAPI generation
- Error diagnostics
- Caching integration
"""

import pytest
import asyncio
import json
from aquilia.patterns import (
    parse_pattern,
    PatternCompiler,
    PatternMatcher,
    calculate_specificity,
    generate_openapi_params,
)
from aquilia.patterns.openapi import patterns_to_openapi_spec
from aquilia.patterns.cache import PatternCache, compile_pattern
from aquilia.patterns.diagnostics.errors import PatternSyntaxError, PatternSemanticError


class TestFullPipeline:
    """Test complete parse → compile → match pipeline."""
    
    @pytest.mark.asyncio
    async def test_simple_pipeline(self):
        """Test simple end-to-end flow."""
        # Parse
        pattern_str = "/users/«id:int»"
        ast = parse_pattern(pattern_str)
        
        # Compile
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        # Match
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        result = await matcher.match("/users/42")
        
        assert result is not None
        assert result.params["id"] == 42
        assert result.pattern.raw == pattern_str
    
    @pytest.mark.asyncio
    async def test_pipeline_with_constraints(self):
        """Test pipeline with constraint validation."""
        pattern_str = "/items/«id:int|min=1|max=100»"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        # Valid
        result = await matcher.match("/items/50")
        assert result is not None
        assert result.params["id"] == 50
        
        # Too low
        result = await matcher.match("/items/0")
        assert result is None
        
        # Too high
        result = await matcher.match("/items/101")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_pipeline_with_optional_groups(self):
        """Test pipeline with optional groups."""
        pattern_str = "/users[/«id:int»]"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        # With optional part
        result = await matcher.match("/users/42")
        assert result is not None
        
        # Without optional part
        result = await matcher.match("/users")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_with_splat(self):
        """Test pipeline with splat pattern."""
        pattern_str = "/files/*path"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        matcher = PatternMatcher()
        matcher.add_pattern(compiled)
        
        result = await matcher.match("/files/docs/api/readme.md")
        assert result is not None
        assert result.params["path"] == "docs/api/readme.md"


class TestMultiPatternRouting:
    """Test routing with multiple patterns."""
    
    @pytest.mark.asyncio
    async def test_static_vs_dynamic_priority(self):
        """Test that static patterns have priority over dynamic."""
        patterns = [
            "/users/list",
            "/users/«id:int»",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Should match static pattern
        result = await matcher.match("/users/list")
        assert result is not None
        assert result.pattern.raw == "/users/list"
    
    @pytest.mark.asyncio
    async def test_typed_vs_generic_priority(self):
        """Test that typed patterns have priority."""
        patterns = [
            "/items/«name:str»",
            "/items/«id:int»",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Should match int pattern for number
        result = await matcher.match("/items/42")
        assert result is not None
        assert result.pattern.raw == "/items/«id:int»"
        assert result.params["id"] == 42
    
    @pytest.mark.asyncio
    async def test_constrained_vs_unconstrained_priority(self):
        """Test that constrained patterns have priority."""
        patterns = [
            "/items/«id:int»",
            "/items/«id:int|min=100»",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Should match constrained pattern
        result = await matcher.match("/items/150")
        assert result is not None
        assert result.pattern.raw == "/items/«id:int|min=100»"
        
        # Should fall back to unconstrained
        result = await matcher.match("/items/50")
        assert result is not None
        assert result.pattern.raw == "/items/«id:int»"
    
    @pytest.mark.asyncio
    async def test_complex_routing_table(self):
        """Test routing with complex pattern set."""
        patterns = [
            "/",
            "/api/v1",
            "/api/v1/users",
            "/api/v1/users/«id:int»",
            "/api/v1/users/«id:uuid»",
            "/api/v1/users/«id:int»/posts",
            "/api/v1/users/«id:int»/posts/«post_id:int»",
            "/api/v1/posts",
            "/api/v1/posts/«slug:slug»",
            "/files/*path",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Test various paths
        test_cases = [
            ("/", "/"),
            ("/api/v1", "/api/v1"),
            ("/api/v1/users/42", "/api/v1/users/«id:int»"),
            ("/api/v1/users/42/posts", "/api/v1/users/«id:int»/posts"),
            ("/api/v1/posts/hello-world", "/api/v1/posts/«slug:slug»"),
            ("/files/docs/readme.md", "/files/*path"),
        ]
        
        for path, expected_pattern in test_cases:
            result = await matcher.match(path)
            assert result is not None, f"Failed to match {path}"
            assert result.pattern.raw == expected_pattern, \
                f"Expected {expected_pattern} but got {result.pattern.raw}"


class TestOpenAPIIntegration:
    """Test OpenAPI generation integration."""
    
    def test_single_pattern_openapi(self):
        """Test OpenAPI generation for single pattern."""
        pattern_str = "/users/«id:int»"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        params = generate_openapi_params(compiled)
        assert len(params) == 1
        assert params[0]["name"] == "id"
        assert params[0]["in"] == "path"
        assert params[0]["schema"]["type"] == "integer"
    
    def test_full_api_spec_generation(self):
        """Test generating complete OpenAPI spec."""
        patterns = [
            ("/users", "GET", "list_users"),
            ("/users/«id:int»", "GET", "get_user"),
            ("/users/«id:int»", "PUT", "update_user"),
            ("/users/«id:int»", "DELETE", "delete_user"),
            ("/posts/«slug:slug»", "GET", "get_post"),
        ]
        
        compiler = PatternCompiler()
        compiled_patterns = []
        
        for pattern_str, method, handler in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            compiled_patterns.append((compiled, method, handler))
        
        spec = patterns_to_openapi_spec(
            compiled_patterns,
            title="Test API",
            version="1.0.0",
        )
        
        assert "openapi" in spec
        assert spec["openapi"] == "3.0.0"
        assert "paths" in spec
        assert len(spec["paths"]) > 0
        
        # Verify user endpoints
        assert "/users" in spec["paths"]
        assert "/users/{id}" in spec["paths"]
        
        # Verify methods
        assert "get" in spec["paths"]["/users/{id}"]
        assert "put" in spec["paths"]["/users/{id}"]
        assert "delete" in spec["paths"]["/users/{id}"]
    
    def test_openapi_with_constraints(self):
        """Test OpenAPI generation with constraints."""
        pattern_str = "/items/«id:int|min=1|max=100»"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        compiled = compiler.compile(ast)
        
        params = generate_openapi_params(compiled)
        assert len(params) == 1
        
        param = params[0]
        assert param["schema"]["type"] == "integer"
        assert param["schema"]["minimum"] == 1
        assert param["schema"]["maximum"] == 100


class TestCachingIntegration:
    """Test caching integration."""
    
    def test_cache_hit(self):
        """Test cache hit scenario."""
        cache = PatternCache(max_size=100)
        pattern_str = "/users/«id:int»"
        
        # First compile (cache miss)
        compiled1 = cache.compile_with_cache(pattern_str)
        assert compiled1 is not None
        
        stats = cache.get_stats()
        assert stats.misses == 1
        assert stats.hits == 0
        
        # Second compile (cache hit)
        compiled2 = cache.compile_with_cache(pattern_str)
        assert compiled2 is not None
        
        stats = cache.get_stats()
        assert stats.hits == 1
        
        # Should be same object
        assert compiled1.raw == compiled2.raw
        assert compiled1.specificity == compiled2.specificity
    
    def test_cache_eviction(self):
        """Test cache eviction with LRU policy."""
        cache = PatternCache(max_size=3)
        
        patterns = [
            "/pattern1",
            "/pattern2",
            "/pattern3",
            "/pattern4",
        ]
        
        # Fill cache
        for pattern in patterns[:3]:
            cache.compile_with_cache(pattern)
        
        assert len(cache) == 3
        
        # Add one more (should evict oldest)
        cache.compile_with_cache(patterns[3])
        assert len(cache) == 3
        
        stats = cache.get_stats()
        assert stats.evictions == 1
    
    def test_cache_with_ttl(self):
        """Test cache with TTL expiration."""
        import time
        
        cache = PatternCache(max_size=100, ttl=0.1)  # 100ms TTL
        pattern_str = "/users/«id:int»"
        
        # Compile
        compiled1 = cache.compile_with_cache(pattern_str)
        assert compiled1 is not None
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired and recompiled
        compiled2 = cache.compile_with_cache(pattern_str)
        assert compiled2 is not None
        
        stats = cache.get_stats()
        assert stats.misses == 2  # Both were misses (second expired)
    
    def test_global_cache_convenience(self):
        """Test global cache convenience function."""
        pattern_str = "/users/«id:int»"
        
        # Use global cache
        compiled = compile_pattern(pattern_str, use_cache=True)
        assert compiled is not None
        
        # Use no cache
        compiled2 = compile_pattern(pattern_str, use_cache=False)
        assert compiled2 is not None


class TestErrorDiagnostics:
    """Test error diagnostic integration."""
    
    def test_syntax_error_with_span(self):
        """Test syntax error includes span information."""
        pattern_str = "/users/«id:int"
        
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern(pattern_str)
        
        error = exc_info.value
        assert error.span is not None
        assert error.span.start >= 0
        assert error.message is not None
    
    def test_semantic_error_duplicate_params(self):
        """Test semantic error for duplicate parameters."""
        pattern_str = "/users/«id:int»/posts/«id:int»"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        with pytest.raises(PatternSemanticError) as exc_info:
            compiler.compile(ast)
        
        error = exc_info.value
        assert "duplicate" in error.message.lower()
    
    def test_semantic_error_unknown_type(self):
        """Test semantic error for unknown type."""
        pattern_str = "/users/«id:unknown_type»"
        ast = parse_pattern(pattern_str)
        
        compiler = PatternCompiler()
        with pytest.raises(PatternSemanticError) as exc_info:
            compiler.compile(ast)
        
        error = exc_info.value
        assert "unknown" in error.message.lower() or "type" in error.message.lower()
    
    def test_error_formatting(self):
        """Test error message formatting."""
        pattern_str = "/users/«id:int"
        
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern(pattern_str)
        
        error = exc_info.value
        formatted = error.format()
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert pattern_str in formatted or "id:int" in formatted


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.mark.asyncio
    async def test_rest_api_routing(self):
        """Test typical REST API routing."""
        patterns = [
            # User endpoints
            "/api/users",
            "/api/users/«id:int»",
            "/api/users/«id:int»/profile",
            "/api/users/«id:int»/posts",
            
            # Post endpoints
            "/api/posts",
            "/api/posts/«id:int»",
            "/api/posts/«slug:slug»",
            
            # Search
            "/api/search?q=«query:str»&limit=«limit:int=10»",
            
            # Files
            "/api/files/*path",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Test various real-world paths
        test_cases = [
            ("/api/users", "/api/users"),
            ("/api/users/42", "/api/users/«id:int»"),
            ("/api/users/42/profile", "/api/users/«id:int»/profile"),
            ("/api/posts/hello-world", "/api/posts/«slug:slug»"),
            ("/api/files/docs/api.md", "/api/files/*path"),
        ]
        
        for path, expected in test_cases:
            result = await matcher.match(path)
            assert result is not None
            assert result.pattern.raw == expected
    
    def test_api_versioning(self):
        """Test API versioning scenarios."""
        patterns = [
            "/api/v1/users/«id:int»",
            "/api/v2/users/«id:uuid»",
            "/api/v3/users/«id:uuid»/extended",
        ]
        
        compiler = PatternCompiler()
        compiled_patterns = []
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            compiled_patterns.append(compiled)
        
        # Generate OpenAPI for each version
        v1_patterns = [(p, "GET", "handler") for p in compiled_patterns if "v1" in p.raw]
        v2_patterns = [(p, "GET", "handler") for p in compiled_patterns if "v2" in p.raw]
        
        v1_spec = patterns_to_openapi_spec(v1_patterns, title="API v1", version="1.0.0")
        v2_spec = patterns_to_openapi_spec(v2_patterns, title="API v2", version="2.0.0")
        
        assert v1_spec["info"]["version"] == "1.0.0"
        assert v2_spec["info"]["version"] == "2.0.0"
    
    @pytest.mark.asyncio
    async def test_microservice_routing(self):
        """Test microservice-style routing."""
        patterns = [
            "/auth/login",
            "/auth/logout",
            "/auth/refresh",
            "/users/«id:int»",
            "/products/«id:int»",
            "/orders/«id:uuid»",
            "/payments/«id:uuid»/status",
        ]
        
        compiler = PatternCompiler()
        matcher = PatternMatcher()
        
        for pattern_str in patterns:
            ast = parse_pattern(pattern_str)
            compiled = compiler.compile(ast)
            matcher.add_pattern(compiled)
        
        # Simulate requests
        result = await matcher.match("/auth/login")
        assert result is not None
        
        result = await matcher.match("/users/123")
        assert result is not None
        assert result.params["id"] == 123
        
        uuid_val = "123e4567-e89b-12d3-a456-426614174000"
        result = await matcher.match(f"/orders/{uuid_val}")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
