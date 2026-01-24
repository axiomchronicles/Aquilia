"""
Comprehensive unit tests for AquilaPatterns parser.

Tests cover:
- Tokenization
- Pattern parsing
- AST construction
- Error handling
- Edge cases
"""

import pytest
from aquilia.patterns.compiler.parser import (
    Tokenizer,
    PatternParser,
    PatternToken,
    TokenType,
    parse_pattern,
)
from aquilia.patterns.compiler.ast_nodes import (
    PatternAST,
    StaticSegment,
    TokenSegment,
    SplatSegment,
    OptionalGroup,
    QueryParam,
    Constraint,
    ConstraintKind,
)
from aquilia.patterns.diagnostics.errors import PatternSyntaxError


class TestTokenizer:
    """Test tokenizer functionality."""
    
    def test_tokenize_empty_string(self):
        """Test tokenizing empty string."""
        tokenizer = Tokenizer("")
        tokens = tokenizer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
    
    def test_tokenize_static_path(self):
        """Test tokenizing static path."""
        tokenizer = Tokenizer("/users/list")
        tokens = tokenizer.tokenize()
        
        assert tokens[0].type == TokenType.SLASH
        assert tokens[1].type == TokenType.STATIC
        assert tokens[1].value == "users"
        assert tokens[2].type == TokenType.SLASH
        assert tokens[3].type == TokenType.STATIC
        assert tokens[3].value == "list"
        assert tokens[4].type == TokenType.EOF
    
    def test_tokenize_simple_token(self):
        """Test tokenizing simple parametric token."""
        tokenizer = Tokenizer("/users/«id:int»")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens[:-1]]  # Exclude EOF
        assert TokenType.LGUIL in token_types
        assert TokenType.RGUIL in token_types
        assert TokenType.COLON in token_types
    
    def test_tokenize_splat(self):
        """Test tokenizing splat pattern."""
        tokenizer = Tokenizer("/files/*path")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens]
        assert TokenType.STAR in token_types
    
    def test_tokenize_optional_group(self):
        """Test tokenizing optional group."""
        tokenizer = Tokenizer("/users[/«id:int»]")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens]
        assert TokenType.LBRACKET in token_types
        assert TokenType.RBRACKET in token_types
    
    def test_tokenize_query_params(self):
        """Test tokenizing query parameters."""
        tokenizer = Tokenizer("/search?q=«query:str»")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens]
        assert TokenType.QUESTION in token_types
        assert TokenType.EQUALS in token_types
    
    def test_tokenize_constraints(self):
        """Test tokenizing constraints."""
        tokenizer = Tokenizer("/items/«id:int|min=1|max=100»")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens]
        assert TokenType.PIPE in token_types
        assert token_types.count(TokenType.PIPE) == 2
    
    def test_tokenize_numbers(self):
        """Test tokenizing numeric literals."""
        tokenizer = Tokenizer("«age:int|min=18|max=99.5»")
        tokens = tokenizer.tokenize()
        
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(numbers) == 3
        assert numbers[0].value == 18
        assert numbers[1].value == 99.5
    
    def test_tokenize_strings(self):
        """Test tokenizing string literals."""
        tokenizer = Tokenizer('«name:str|regex="[a-z]+"»')
        tokens = tokenizer.tokenize()
        
        strings = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strings) == 1
        assert strings[0].value == "[a-z]+"
    
    def test_tokenize_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        tokenizer = Tokenizer("/users / «id:int» ")
        tokens = tokenizer.tokenize()
        
        # Whitespace should be skipped
        static_tokens = [t for t in tokens if t.type == TokenType.STATIC]
        assert len(static_tokens) == 1
    
    def test_tokenize_special_chars(self):
        """Test tokenizing special characters."""
        tokenizer = Tokenizer("«param:str@transform»")
        tokens = tokenizer.tokenize()
        
        token_types = [t.type for t in tokens]
        assert TokenType.AT in token_types
    
    def test_tokenize_span_tracking(self):
        """Test that spans are tracked correctly."""
        tokenizer = Tokenizer("/users")
        tokens = tokenizer.tokenize()
        
        for token in tokens:
            assert token.span is not None
            assert token.span.start >= 0
            assert token.span.end >= token.span.start


class TestParser:
    """Test parser functionality."""
    
    def test_parse_static_path(self):
        """Test parsing static path."""
        ast = parse_pattern("/users/list")
        
        assert isinstance(ast, PatternAST)
        assert len(ast.segments) == 2
        assert isinstance(ast.segments[0], StaticSegment)
        assert ast.segments[0].value == "users"
        assert isinstance(ast.segments[1], StaticSegment)
        assert ast.segments[1].value == "list"
    
    def test_parse_simple_token(self):
        """Test parsing simple token."""
        ast = parse_pattern("/users/«id:int»")
        
        assert len(ast.segments) == 2
        assert isinstance(ast.segments[1], TokenSegment)
        assert ast.segments[1].name == "id"
        assert ast.segments[1].param_type == "int"
    
    def test_parse_token_without_type(self):
        """Test parsing token without explicit type."""
        ast = parse_pattern("/users/«id»")
        
        token = ast.segments[1]
        assert isinstance(token, TokenSegment)
        assert token.name == "id"
        assert token.param_type == "str"  # Default type
    
    def test_parse_splat(self):
        """Test parsing splat pattern."""
        ast = parse_pattern("/files/*path")
        
        assert len(ast.segments) == 2
        assert isinstance(ast.segments[1], SplatSegment)
        assert ast.segments[1].name == "path"
    
    def test_parse_optional_group(self):
        """Test parsing optional group."""
        ast = parse_pattern("/users[/«id:int»]")
        
        assert len(ast.segments) == 2
        assert isinstance(ast.segments[1], OptionalGroup)
        assert len(ast.segments[1].segments) == 1
    
    def test_parse_nested_optional_groups(self):
        """Test parsing nested optional groups."""
        ast = parse_pattern("/a[/b[/c]]")
        
        outer_group = ast.segments[1]
        assert isinstance(outer_group, OptionalGroup)
        
        inner_group = outer_group.segments[1]
        assert isinstance(inner_group, OptionalGroup)
    
    def test_parse_constraints(self):
        """Test parsing constraints."""
        ast = parse_pattern("/items/«id:int|min=1|max=100»")
        
        token = ast.segments[1]
        assert len(token.constraints) == 2
        
        min_constraint = token.constraints[0]
        assert min_constraint.kind == ConstraintKind.MIN
        assert min_constraint.value == 1
        
        max_constraint = token.constraints[1]
        assert max_constraint.kind == ConstraintKind.MAX
        assert max_constraint.value == 100
    
    def test_parse_regex_constraint(self):
        """Test parsing regex constraint."""
        ast = parse_pattern(r'/users/«name:str|regex=[a-z]+»')
        
        token = ast.segments[1]
        assert len(token.constraints) == 1
        assert token.constraints[0].kind == ConstraintKind.REGEX
        assert token.constraints[0].value == "[a-z]+"
    
    def test_parse_enum_constraint(self):
        """Test parsing enum constraint."""
        ast = parse_pattern('/status/«value:str|enum=pending,active,done»')
        
        token = ast.segments[1]
        constraint = token.constraints[0]
        assert constraint.kind == ConstraintKind.ENUM
        assert constraint.value == ["pending", "active", "done"]
    
    def test_parse_transform(self):
        """Test parsing transform."""
        ast = parse_pattern('/users/«name:str@lower»')
        
        token = ast.segments[1]
        assert token.transform is not None
        assert token.transform.name == "lower"
    
    def test_parse_default_value(self):
        """Test parsing default value."""
        ast = parse_pattern('/items/«limit:int=10»')
        
        token = ast.segments[1]
        assert token.default == 10
    
    def test_parse_query_params(self):
        """Test parsing query parameters."""
        ast = parse_pattern('/search?q=«query:str»')
        
        assert len(ast.query_params) == 1
        assert ast.query_params[0].name == "query"
        assert ast.query_params[0].param_type == "str"
    
    def test_parse_multiple_query_params(self):
        """Test parsing multiple query parameters."""
        ast = parse_pattern('/search?q=«query:str»&limit=«limit:int»')
        
        assert len(ast.query_params) == 2
        assert ast.query_params[0].name == "query"
        assert ast.query_params[1].name == "limit"
    
    def test_parse_complex_pattern(self):
        """Test parsing complex pattern with multiple features."""
        pattern = '/api/v1/users/«id:int|min=1»[/posts/«post_id:uuid»]?page=«page:int=1»'
        ast = parse_pattern(pattern)
        
        assert len(ast.segments) == 4  # api, v1, users, token, optional
        assert len(ast.query_params) == 1
        
        token = ast.segments[3]
        assert isinstance(token, TokenSegment)
        assert token.name == "id"
        assert len(token.constraints) == 1
        
        optional = ast.segments[4]
        assert isinstance(optional, OptionalGroup)
    
    def test_get_static_prefix(self):
        """Test extracting static prefix."""
        ast = parse_pattern('/api/v1/users/«id:int»')
        assert ast.get_static_prefix() == "/api/v1/users"
    
    def test_get_param_names(self):
        """Test extracting parameter names."""
        ast = parse_pattern('/users/«id:int»/posts/«post_id:int»')
        params = ast.get_param_names()
        assert "id" in params
        assert "post_id" in params
        assert len(params) == 2
    
    def test_ast_to_dict(self):
        """Test AST serialization to dict."""
        ast = parse_pattern('/users/«id:int»')
        data = ast.to_dict()
        
        assert "segments" in data
        assert "query_params" in data
        assert len(data["segments"]) == 2


class TestParserErrors:
    """Test parser error handling."""
    
    def test_unterminated_token(self):
        """Test error on unterminated token."""
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern('/users/«id:int')
        
        assert "unterminated" in str(exc_info.value).lower() or "expected" in str(exc_info.value).lower()
    
    def test_empty_token(self):
        """Test error on empty token."""
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern('/users/«»')
        
        assert "empty" in str(exc_info.value).lower() or "expected" in str(exc_info.value).lower()
    
    def test_unmatched_bracket(self):
        """Test error on unmatched bracket."""
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern('/users[/«id:int»')
        
        assert "bracket" in str(exc_info.value).lower() or "expected" in str(exc_info.value).lower()
    
    def test_invalid_constraint_syntax(self):
        """Test error on invalid constraint syntax."""
        with pytest.raises(PatternSyntaxError):
            parse_pattern('/users/«id:int|min»')  # Missing value
    
    def test_missing_colon_in_token(self):
        """Test error when colon is missing in typed token."""
        # This should either work (default to str) or error clearly
        try:
            ast = parse_pattern('/users/«id»')
            assert ast.segments[1].param_type == "str"
        except PatternSyntaxError:
            pass  # Either behavior is acceptable
    
    def test_invalid_query_param_syntax(self):
        """Test error on invalid query param syntax."""
        with pytest.raises(PatternSyntaxError):
            parse_pattern('/search?=«query:str»')  # Missing param name
    
    def test_error_span_information(self):
        """Test that errors include span information."""
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern('/users/«id:int')
        
        error = exc_info.value
        assert error.span is not None
        assert error.span.start >= 0


class TestParserEdgeCases:
    """Test edge cases and corner cases."""
    
    def test_empty_pattern(self):
        """Test parsing empty pattern."""
        ast = parse_pattern("")
        assert len(ast.segments) == 0
    
    def test_root_path(self):
        """Test parsing root path."""
        ast = parse_pattern("/")
        assert len(ast.segments) == 0
    
    def test_multiple_slashes(self):
        """Test handling of multiple consecutive slashes."""
        ast = parse_pattern("/users//list")
        # Should normalize or handle gracefully
        assert isinstance(ast, PatternAST)
    
    def test_trailing_slash(self):
        """Test pattern with trailing slash."""
        ast = parse_pattern("/users/")
        assert isinstance(ast, PatternAST)
    
    def test_unicode_in_static(self):
        """Test unicode characters in static segments."""
        ast = parse_pattern("/用户/列表")
        assert ast.segments[0].value == "用户"
        assert ast.segments[1].value == "列表"
    
    def test_very_long_pattern(self):
        """Test very long pattern."""
        segments = "/".join(f"segment{i}" for i in range(100))
        pattern = f"/{segments}"
        ast = parse_pattern(pattern)
        assert len(ast.segments) == 100
    
    def test_deeply_nested_optional_groups(self):
        """Test deeply nested optional groups."""
        pattern = "/a[/b[/c[/d[/e]]]]"
        ast = parse_pattern(pattern)
        assert isinstance(ast, PatternAST)
    
    def test_special_chars_in_static(self):
        """Test special characters in static segments."""
        ast = parse_pattern("/users-list/api_v1")
        assert "users-list" in ast.segments[0].value
        assert "api_v1" in ast.segments[1].value
    
    def test_numbers_in_static(self):
        """Test numbers in static segments."""
        ast = parse_pattern("/api/v1/v2")
        assert "v1" in ast.segments[1].value
        assert "v2" in ast.segments[2].value


class TestParserRecovery:
    """Test error recovery mechanisms."""
    
    def test_recover_from_missing_closing_delim(self):
        """Test recovery from missing closing delimiter."""
        # Parser should provide helpful error message
        with pytest.raises(PatternSyntaxError) as exc_info:
            parse_pattern('/users/«id:int')
        
        # Error should be informative
        assert exc_info.value.message is not None
    
    def test_multiple_errors_reported(self):
        """Test that multiple errors can be detected."""
        # Pattern with multiple issues
        with pytest.raises(PatternSyntaxError):
            parse_pattern('/users/«id:int[/posts')  # Unterminated and unmatched


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
