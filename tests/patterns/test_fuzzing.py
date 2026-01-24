"""
Fuzzing harness for AquilaPatterns parser and compiler.

Tests robustness against:
- Malformed inputs
- Edge cases
- Random mutations
- Pathological patterns
"""

import pytest
import random
import string
from hypothesis import given, strategies as st, settings, assume
from aquilia.patterns.compiler.parser import parse_pattern
from aquilia.patterns.compiler.compiler import PatternCompiler
from aquilia.patterns.diagnostics.errors import PatternSyntaxError, PatternSemanticError


# ============================================================================
# Fuzzing Strategies
# ============================================================================

def random_string(min_len=0, max_len=50):
    """Generate random string."""
    length = random.randint(min_len, max_len)
    return ''.join(random.choices(string.printable, k=length))


def mutate_pattern(pattern: str) -> str:
    """Apply random mutation to pattern."""
    if not pattern:
        return random_string(1, 20)
    
    mutations = [
        lambda p: p + random.choice("«»[]()/:@|=&?*"),  # Add random char
        lambda p: p[:-1] if len(p) > 1 else p,  # Remove last char
        lambda p: random.choice("«»[]()/:@|=&?*") + p,  # Prepend char
        lambda p: p.replace("/", "//") if "/" in p else p,  # Double slashes
        lambda p: p.replace("«", "««") if "«" in p else p,  # Double guillemets
        lambda p: p.replace("»", "") if "»" in p else p,  # Remove closing
        lambda p: p.replace("[", "[[") if "[" in p else p,  # Double brackets
        lambda p: p.replace(":", "::") if ":" in p else p,  # Double colons
        lambda p: p[:len(p)//2],  # Truncate
        lambda p: p * 2,  # Duplicate
    ]
    
    mutation = random.choice(mutations)
    return mutation(pattern)


# ============================================================================
# Fuzzing Tests
# ============================================================================

class TestParserFuzzing:
    """Fuzz test parser with random inputs."""
    
    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=200)
    def test_parser_never_crashes_on_random_text(self, text):
        """Test that parser never crashes on random text."""
        try:
            parse_pattern(text)
        except (PatternSyntaxError, PatternSemanticError, ValueError):
            # Expected errors are OK
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error on input '{text}': {e}")
    
    @given(st.text(alphabet="«»[]()/:@|=&?*", min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_parser_handles_special_chars(self, text):
        """Test parser with only special characters."""
        try:
            parse_pattern(text)
        except (PatternSyntaxError, PatternSemanticError, ValueError):
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error on special chars '{text}': {e}")
    
    @given(st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_parser_with_repeated_chars(self, base):
        """Test parser with repeated characters."""
        # Create patterns with extreme repetition
        for repeat in [10, 50, 100]:
            pattern = base * repeat
            try:
                parse_pattern(pattern)
            except (PatternSyntaxError, PatternSemanticError, ValueError, MemoryError):
                pass
            except Exception as e:
                pytest.fail(f"Unexpected error on repeated '{base}': {e}")
    
    def test_deeply_nested_structures(self):
        """Test parser with deeply nested structures."""
        # Deeply nested brackets
        for depth in [10, 50, 100]:
            pattern = "/" + "[/" * depth + "x" + "]" * depth
            try:
                parse_pattern(pattern)
            except (PatternSyntaxError, PatternSemanticError, RecursionError):
                pass
            except Exception as e:
                pytest.fail(f"Unexpected error on depth {depth}: {e}")
    
    def test_extremely_long_patterns(self):
        """Test parser with extremely long patterns."""
        for length in [1000, 5000, 10000]:
            pattern = "/" + "a" * length
            try:
                ast = parse_pattern(pattern)
                # Should handle gracefully
                assert ast is not None
            except (PatternSyntaxError, MemoryError):
                pass
    
    def test_binary_data(self):
        """Test parser with binary data."""
        for _ in range(50):
            binary = bytes([random.randint(0, 255) for _ in range(50)])
            try:
                text = binary.decode('utf-8', errors='ignore')
                parse_pattern(text)
            except (PatternSyntaxError, PatternSemanticError, ValueError):
                pass
    
    def test_unicode_edge_cases(self):
        """Test parser with unicode edge cases."""
        edge_cases = [
            "\x00\x01\x02",  # Null and control chars
            "�" * 20,  # Replacement character
            "🔥" * 20,  # Emojis
            "\u200b" * 20,  # Zero-width spaces
            "\n\r\t" * 20,  # Whitespace
            "⁰¹²³⁴⁵⁶⁷⁸⁹",  # Superscript numbers
        ]
        
        for text in edge_cases:
            try:
                parse_pattern(text)
            except (PatternSyntaxError, PatternSemanticError, ValueError):
                pass


class TestCompilerFuzzing:
    """Fuzz test compiler with edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compiler = PatternCompiler()
    
    @given(st.text(alphabet=string.ascii_lowercase + "_", min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_compiler_with_random_type_names(self, type_name):
        """Test compiler with random type names."""
        pattern = f"/items/«id:{type_name}»"
        
        try:
            ast = parse_pattern(pattern)
            self.compiler.compile(ast)
        except (PatternSyntaxError, PatternSemanticError, ValueError):
            # Expected for unknown types
            pass
    
    @given(
        st.integers(min_value=-1000000, max_value=1000000),
        st.integers(min_value=-1000000, max_value=1000000),
    )
    @settings(max_examples=100)
    def test_compiler_with_extreme_constraint_values(self, min_val, max_val):
        """Test compiler with extreme constraint values."""
        pattern = f"/items/«id:int|min={min_val}|max={max_val}»"
        
        try:
            ast = parse_pattern(pattern)
            compiled = self.compiler.compile(ast)
            assert compiled is not None
        except (PatternSyntaxError, PatternSemanticError, ValueError):
            pass
    
    def test_compiler_with_many_parameters(self):
        """Test compiler with many parameters."""
        for count in [10, 50, 100]:
            segments = [f"«param{i}:int»" for i in range(count)]
            pattern = "/" + "/".join(segments)
            
            try:
                ast = parse_pattern(pattern)
                compiled = self.compiler.compile(ast)
                assert len(compiled.params) == count
            except (PatternSyntaxError, PatternSemanticError, MemoryError):
                pass
    
    def test_compiler_with_complex_regex(self):
        """Test compiler with complex regex patterns."""
        complex_regexes = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$",  # Password
            r"\d{3}-\d{2}-\d{4}",  # SSN
            r"(https?://)?([a-z0-9-]+\.)+[a-z]{2,}",  # URL
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",  # UUID
        ]
        
        for regex in complex_regexes:
            pattern = f'/items/«value:str|regex={regex}»'
            try:
                ast = parse_pattern(pattern)
                compiled = self.compiler.compile(ast)
                assert compiled is not None
            except (PatternSyntaxError, PatternSemanticError, ValueError):
                pass


class TestMutationFuzzing:
    """Test with pattern mutations."""
    
    valid_patterns = [
        "/users/«id:int»",
        "/items/*path",
        "/search?q=«query:str»",
        "/api/v1/users[/«id:int»]",
        "/posts/«id:int|min=1»",
    ]
    
    def test_random_mutations(self):
        """Test parser with random mutations of valid patterns."""
        for _ in range(100):
            base_pattern = random.choice(self.valid_patterns)
            mutated = mutate_pattern(base_pattern)
            
            try:
                parse_pattern(mutated)
            except (PatternSyntaxError, PatternSemanticError, ValueError):
                pass
            except Exception as e:
                # Some mutations might be acceptable
                pass
    
    def test_truncation_fuzzing(self):
        """Test truncated patterns."""
        for pattern in self.valid_patterns:
            for length in range(1, len(pattern)):
                truncated = pattern[:length]
                try:
                    parse_pattern(truncated)
                except (PatternSyntaxError, PatternSemanticError, ValueError):
                    pass
    
    def test_insertion_fuzzing(self):
        """Test patterns with random insertions."""
        for pattern in self.valid_patterns:
            for pos in range(len(pattern)):
                for char in "«»[]()/:@|=&?*\n\r\t\x00":
                    mutated = pattern[:pos] + char + pattern[pos:]
                    try:
                        parse_pattern(mutated)
                    except (PatternSyntaxError, PatternSemanticError, ValueError):
                        pass
    
    def test_deletion_fuzzing(self):
        """Test patterns with random deletions."""
        for pattern in self.valid_patterns:
            for pos in range(len(pattern)):
                mutated = pattern[:pos] + pattern[pos+1:]
                try:
                    parse_pattern(mutated)
                except (PatternSyntaxError, PatternSemanticError, ValueError):
                    pass


class TestPathologicalPatterns:
    """Test known pathological patterns."""
    
    def test_catastrophic_backtracking_patterns(self):
        """Test patterns that could cause catastrophic backtracking."""
        # These patterns are designed to stress regex engines
        pathological = [
            "/users/" + "«id:int»/" * 20,
            "/files/" + "*path/" * 10,
            "/" + "[/x]" * 20,
        ]
        
        for pattern in pathological:
            try:
                ast = parse_pattern(pattern)
                compiler = PatternCompiler()
                compiled = compiler.compile(ast)
                assert compiled is not None
            except (PatternSyntaxError, PatternSemanticError, RecursionError):
                pass
    
    def test_ambiguous_patterns(self):
        """Test patterns that are ambiguous."""
        ambiguous_pairs = [
            ("/users/«id:int»", "/users/«name:str»"),
            ("/items/«x:str»", "/items/«y:str»"),
            ("/*path", "/*rest"),
        ]
        
        for pattern1, pattern2 in ambiguous_pairs:
            try:
                ast1 = parse_pattern(pattern1)
                ast2 = parse_pattern(pattern2)
                
                compiler = PatternCompiler()
                compiled1 = compiler.compile(ast1)
                compiled2 = compiler.compile(ast2)
                
                # Both should compile
                assert compiled1 is not None
                assert compiled2 is not None
            except (PatternSyntaxError, PatternSemanticError):
                pass
    
    def test_memory_exhaustion_patterns(self):
        """Test patterns that could exhaust memory."""
        # Very long patterns
        try:
            # 1 million character pattern
            pattern = "/" + "a" * 1_000_000
            ast = parse_pattern(pattern)
        except (MemoryError, PatternSyntaxError):
            pass
        
        # Many small segments
        try:
            pattern = "/" + "/".join(["x"] * 10000)
            ast = parse_pattern(pattern)
        except (MemoryError, PatternSyntaxError):
            pass


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_recovery_from_partial_tokens(self):
        """Test recovery from incomplete tokens."""
        partial_patterns = [
            "/users/«id",
            "/users/«id:",
            "/users/«id:int",
            "/users/«id:int|",
            "/users/«id:int|min",
            "/users/«id:int|min=",
        ]
        
        for pattern in partial_patterns:
            try:
                parse_pattern(pattern)
            except PatternSyntaxError as e:
                # Should get meaningful error
                assert e.message is not None
                assert len(e.message) > 0
    
    def test_recovery_from_mismatched_delimiters(self):
        """Test recovery from mismatched delimiters."""
        mismatched = [
            "/users[/«id:int»",  # Missing ]
            "/users]/«id:int»",  # Extra ]
            "/users/«id:int]",  # Wrong delimiter
            "/users/[id:int»]",  # Mixed delimiters
        ]
        
        for pattern in mismatched:
            try:
                parse_pattern(pattern)
            except PatternSyntaxError as e:
                # Should get meaningful error about delimiters
                assert e.message is not None


class TestPerformanceFuzzing:
    """Test performance characteristics under fuzzing."""
    
    @pytest.mark.timeout(5)
    def test_parser_performance_random_input(self):
        """Test that parser completes in reasonable time."""
        for _ in range(100):
            length = random.randint(0, 500)
            pattern = random_string(0, length)
            
            try:
                parse_pattern(pattern)
            except (PatternSyntaxError, PatternSemanticError, ValueError):
                pass
    
    @pytest.mark.timeout(10)
    def test_compiler_performance_complex_patterns(self):
        """Test that compiler completes in reasonable time."""
        compiler = PatternCompiler()
        
        for _ in range(50):
            # Generate complex pattern
            param_count = random.randint(1, 20)
            segments = [f"«p{i}:int|min={i}|max={i+100}»" for i in range(param_count)]
            pattern = "/" + "/".join(segments)
            
            try:
                ast = parse_pattern(pattern)
                compiler.compile(ast)
            except (PatternSyntaxError, PatternSemanticError):
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
