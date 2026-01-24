"""
Comprehensive unit tests for AquilaPatterns compiler.

Tests cover:
- AST compilation
- Type casting
- Constraint validation
- Specificity calculation
- Regex generation
- OpenAPI metadata
"""

import pytest
import re
from aquilia.patterns.compiler.compiler import (
    PatternCompiler,
    CompiledPattern,
    CompiledParam,
)
from aquilia.patterns.compiler.parser import parse_pattern
from aquilia.patterns.compiler.specificity import calculate_specificity
from aquilia.patterns.diagnostics.errors import PatternSemanticError
from aquilia.patterns.types.registry import TypeRegistry
from aquilia.patterns.validators.registry import ConstraintRegistry


class TestCompiler:
    """Test basic compiler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_compile_static_pattern(self):
        """Test compiling static pattern."""
        ast = parse_pattern("/users/list")
        compiled = self.compiler.compile(ast)
        
        assert isinstance(compiled, CompiledPattern)
        assert compiled.raw == "/users/list"
        assert compiled.static_prefix == "/users/list"
        assert len(compiled.params) == 0
    
    def test_compile_simple_token(self):
        """Test compiling simple token."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        assert "id" in compiled.params
        param = compiled.params["id"]
        assert param.name == "id"
        assert param.param_type == "int"
        assert param.castor is not None
    
    def test_compile_with_default(self):
        """Test compiling token with default value."""
        ast = parse_pattern("/items/«limit:int=10»")
        compiled = self.compiler.compile(ast)
        
        param = compiled.params["limit"]
        assert param.default == 10
    
    def test_compile_with_constraints(self):
        """Test compiling with constraints."""
        ast = parse_pattern("/items/«id:int|min=1|max=100»")
        compiled = self.compiler.compile(ast)
        
        param = compiled.params["id"]
        assert len(param.validators) == 2
    
    def test_compile_splat(self):
        """Test compiling splat pattern."""
        ast = parse_pattern("/files/*path")
        compiled = self.compiler.compile(ast)
        
        assert "path" in compiled.params
        param = compiled.params["path"]
        assert param.param_type == "path"
    
    def test_compile_query_params(self):
        """Test compiling query parameters."""
        ast = parse_pattern("/search?q=«query:str»")
        compiled = self.compiler.compile(ast)
        
        assert "query" in compiled.query
        query_param = compiled.query["query"]
        assert query_param.name == "query"
    
    def test_static_prefix_extraction(self):
        """Test static prefix extraction."""
        ast = parse_pattern("/api/v1/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        assert compiled.static_prefix == "/api/v1/users"
    
    def test_regex_compilation(self):
        """Test regex pattern compilation."""
        ast = parse_pattern("/users/«id:int»/posts/«post_id:int»")
        compiled = self.compiler.compile(ast)
        
        assert compiled.compiled_re is not None
        assert compiled.compiled_re.match("/users/42/posts/123")
    
    def test_openapi_generation(self):
        """Test OpenAPI metadata generation."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        assert "parameters" in compiled.openapi
        assert len(compiled.openapi["parameters"]) == 1
        
        param_spec = compiled.openapi["parameters"][0]
        assert param_spec["name"] == "id"
        assert param_spec["in"] == "path"
        assert param_spec["schema"]["type"] == "integer"
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        data = compiled.to_dict()
        assert "raw" in data
        assert "params" in data
        assert "specificity" in data
    
    def test_to_json_serialization(self):
        """Test JSON serialization."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        json_str = compiled.to_json()
        assert isinstance(json_str, str)
        assert '"raw"' in json_str


class TestTypeCasting:
    """Test type casting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_int_casting(self):
        """Test integer type casting."""
        ast = parse_pattern("/items/«id:int»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["id"].castor
        assert castor("42") == 42
        assert castor("0") == 0
        assert castor("-5") == -5
    
    def test_float_casting(self):
        """Test float type casting."""
        ast = parse_pattern("/items/«price:float»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["price"].castor
        assert castor("3.14") == 3.14
        assert castor("0.5") == 0.5
        assert castor("100") == 100.0
    
    def test_bool_casting(self):
        """Test boolean type casting."""
        ast = parse_pattern("/items/«active:bool»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["active"].castor
        assert castor("true") is True
        assert castor("false") is False
        assert castor("1") is True
        assert castor("0") is False
    
    def test_uuid_casting(self):
        """Test UUID type casting."""
        ast = parse_pattern("/items/«id:uuid»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["id"].castor
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = castor(valid_uuid)
        assert result is not None
    
    def test_slug_casting(self):
        """Test slug type validation."""
        ast = parse_pattern("/posts/«slug:slug»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["slug"].castor
        assert castor("hello-world") == "hello-world"
        assert castor("my-post-123") == "my-post-123"
    
    def test_invalid_int_casting(self):
        """Test invalid integer casting."""
        ast = parse_pattern("/items/«id:int»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["id"].castor
        with pytest.raises(ValueError):
            castor("not-a-number")
    
    def test_str_casting_always_succeeds(self):
        """Test that string casting always succeeds."""
        ast = parse_pattern("/items/«name:str»")
        compiled = self.compiler.compile(ast)
        
        castor = compiled.params["name"].castor
        assert castor("hello") == "hello"
        assert castor("123") == "123"
        assert castor("") == ""


class TestConstraintValidation:
    """Test constraint validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_min_constraint(self):
        """Test minimum value constraint."""
        ast = parse_pattern("/items/«id:int|min=10»")
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["id"].validators
        assert len(validators) == 1
        
        validator = validators[0]
        assert validator(10) is True
        assert validator(15) is True
        assert validator(5) is False
    
    def test_max_constraint(self):
        """Test maximum value constraint."""
        ast = parse_pattern("/items/«id:int|max=100»")
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["id"].validators
        validator = validators[0]
        assert validator(100) is True
        assert validator(50) is True
        assert validator(101) is False
    
    def test_min_max_combined(self):
        """Test combined min and max constraints."""
        ast = parse_pattern("/items/«id:int|min=1|max=100»")
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["id"].validators
        assert len(validators) == 2
        
        # Should pass all validators
        assert all(v(50) for v in validators)
        assert not all(v(0) for v in validators)
        assert not all(v(101) for v in validators)
    
    def test_regex_constraint(self):
        """Test regex constraint."""
        ast = parse_pattern(r'/users/«name:str|regex=[a-z]+»')
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["name"].validators
        validator = validators[0]
        
        assert validator("hello") is True
        assert validator("abc") is True
        assert validator("Hello") is False
        assert validator("123") is False
    
    def test_enum_constraint(self):
        """Test enum constraint."""
        ast = parse_pattern('/status/«value:str|enum=pending,active,done»')
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["value"].validators
        validator = validators[0]
        
        assert validator("pending") is True
        assert validator("active") is True
        assert validator("done") is True
        assert validator("invalid") is False
    
    def test_multiple_constraints(self):
        """Test multiple constraints on same parameter."""
        ast = parse_pattern('/items/«count:int|min=1|max=100»')
        compiled = self.compiler.compile(ast)
        
        validators = compiled.params["count"].validators
        assert len(validators) == 2


class TestSpecificity:
    """Test specificity calculation."""
    
    def test_static_segments_highest(self):
        """Test that static segments have highest specificity."""
        static_ast = parse_pattern("/users/list")
        param_ast = parse_pattern("/users/«id:int»")
        
        static_score = calculate_specificity(static_ast)
        param_score = calculate_specificity(param_ast)
        
        assert static_score > param_score
    
    def test_typed_tokens_higher_than_generic(self):
        """Test that typed tokens have higher specificity than generic."""
        int_ast = parse_pattern("/users/«id:int»")
        str_ast = parse_pattern("/users/«name:str»")
        
        int_score = calculate_specificity(int_ast)
        str_score = calculate_specificity(str_ast)
        
        assert int_score > str_score
    
    def test_constraints_increase_specificity(self):
        """Test that constraints increase specificity."""
        without_ast = parse_pattern("/items/«id:int»")
        with_ast = parse_pattern("/items/«id:int|min=1»")
        
        without_score = calculate_specificity(without_ast)
        with_score = calculate_specificity(with_ast)
        
        assert with_score > without_score
    
    def test_splat_lowest_specificity(self):
        """Test that splat has lowest specificity."""
        static_ast = parse_pattern("/files/list")
        token_ast = parse_pattern("/files/«name:str»")
        splat_ast = parse_pattern("/files/*path")
        
        static_score = calculate_specificity(static_ast)
        token_score = calculate_specificity(token_ast)
        splat_score = calculate_specificity(splat_ast)
        
        assert static_score > token_score > splat_score
    
    def test_optional_reduces_specificity(self):
        """Test that optional groups reduce specificity."""
        without_ast = parse_pattern("/users/«id:int»")
        with_ast = parse_pattern("/users[/«id:int»]")
        
        without_score = calculate_specificity(without_ast)
        with_score = calculate_specificity(with_ast)
        
        assert without_score > with_score
    
    def test_longer_patterns_more_specific(self):
        """Test that longer patterns are more specific."""
        short_ast = parse_pattern("/users")
        long_ast = parse_pattern("/users/list/active")
        
        short_score = calculate_specificity(short_ast)
        long_score = calculate_specificity(long_ast)
        
        assert long_score > short_score
    
    def test_deterministic_scoring(self):
        """Test that scoring is deterministic."""
        ast = parse_pattern("/users/«id:int|min=1»")
        
        score1 = calculate_specificity(ast)
        score2 = calculate_specificity(ast)
        
        assert score1 == score2


class TestCompilerErrors:
    """Test compiler error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_unknown_type_error(self):
        """Test error on unknown type."""
        ast = parse_pattern("/items/«id:unknown_type»")
        
        with pytest.raises(PatternSemanticError) as exc_info:
            self.compiler.compile(ast)
        
        assert "unknown" in str(exc_info.value).lower() or "type" in str(exc_info.value).lower()
    
    def test_duplicate_param_error(self):
        """Test error on duplicate parameter names."""
        ast = parse_pattern("/users/«id:int»/posts/«id:int»")
        
        with pytest.raises(PatternSemanticError) as exc_info:
            self.compiler.compile(ast)
        
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_invalid_regex_error(self):
        """Test error on invalid regex pattern."""
        ast = parse_pattern(r'/users/«name:str|regex=[invalid(»')
        
        with pytest.raises(PatternSemanticError):
            self.compiler.compile(ast)
    
    def test_invalid_constraint_value(self):
        """Test error on invalid constraint value."""
        # Min value must be a number
        ast = parse_pattern('/items/«id:int|min=abc»')
        
        with pytest.raises((PatternSemanticError, ValueError)):
            self.compiler.compile(ast)


class TestCompilerOptimizations:
    """Test compiler optimizations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_regex_compiled_once(self):
        """Test that regex is compiled once."""
        ast = parse_pattern("/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        assert compiled.compiled_re is not None
        # Regex should be pre-compiled
        assert isinstance(compiled.compiled_re.pattern, str)
    
    def test_static_prefix_optimization(self):
        """Test static prefix extraction for quick rejection."""
        ast = parse_pattern("/api/v1/users/«id:int»")
        compiled = self.compiler.compile(ast)
        
        # Should extract longest static prefix
        assert compiled.static_prefix == "/api/v1/users"
        assert len(compiled.static_prefix) > 0
    
    def test_validator_caching(self):
        """Test that validators are cached."""
        ast = parse_pattern("/items/«id:int|min=1»")
        compiled1 = self.compiler.compile(ast)
        compiled2 = self.compiler.compile(ast)
        
        # Both should have validators
        assert len(compiled1.params["id"].validators) > 0
        assert len(compiled2.params["id"].validators) > 0


class TestEdgeCases:
    """Test edge cases in compilation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    def test_empty_pattern(self):
        """Test compiling empty pattern."""
        ast = parse_pattern("")
        compiled = self.compiler.compile(ast)
        
        assert compiled.static_prefix == ""
        assert len(compiled.params) == 0
    
    def test_root_path(self):
        """Test compiling root path."""
        ast = parse_pattern("/")
        compiled = self.compiler.compile(ast)
        
        assert isinstance(compiled, CompiledPattern)
    
    def test_very_long_pattern(self):
        """Test compiling very long pattern."""
        segments = "/".join(f"seg{i}" for i in range(50))
        ast = parse_pattern(f"/{segments}")
        compiled = self.compiler.compile(ast)
        
        assert isinstance(compiled, CompiledPattern)
    
    def test_unicode_parameters(self):
        """Test parameters with unicode names."""
        ast = parse_pattern("/users/«用户id:int»")
        compiled = self.compiler.compile(ast)
        
        assert "用户id" in compiled.params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
