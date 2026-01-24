"""
AquilaPatterns - Professional URL pattern language and compiler for Aquilia.

This module provides a unique, expressive, static-first URL pattern system with:
- Formal EBNF grammar with tokenizer/parser
- AST compilation with optimized matchers
- Radix trie integration for fast routing
- OpenAPI schema generation
- LSP support for IDE integration
- Comprehensive diagnostics and error reporting
"""

from .compiler.parser import PatternParser, PatternToken, parse_pattern
from .compiler.ast_nodes import (
    PatternAST,
    StaticSegment,
    TokenSegment,
    OptionalGroup,
    SplatSegment,
    QueryParam,
)
from .compiler.compiler import PatternCompiler, CompiledPattern
from .compiler.specificity import calculate_specificity
from .types.registry import TypeRegistry, register_type
from .validators.registry import ConstraintRegistry, register_constraint
from .transforms.registry import TransformRegistry, register_transform
from .diagnostics.errors import (
    PatternSyntaxError,
    PatternSemanticError,
    RouteAmbiguityError,
    PatternDiagnostic,
)
from .matcher import PatternMatcher, MatchResult
from .openapi import generate_openapi_params
from .cache import PatternCache, compile_pattern, get_global_cache, set_global_cache
from .autofix import (
    AutoFixEngine,
    FixSuggestion,
    DiagnosticFix,
    generate_fix_suggestions,
    ErrorRecovery,
)

__version__ = "0.2.0"

__all__ = [
    # Parser
    "PatternParser",
    "PatternToken",
    "parse_pattern",
    # AST
    "PatternAST",
    "StaticSegment",
    "TokenSegment",
    "OptionalGroup",
    "SplatSegment",
    "QueryParam",
    # Compiler
    "PatternCompiler",
    "CompiledPattern",
    "calculate_specificity",
    # Registries
    "TypeRegistry",
    "register_type",
    "ConstraintRegistry",
    "register_constraint",
    "TransformRegistry",
    "register_transform",
    # Diagnostics
    "PatternSyntaxError",
    "PatternSemanticError",
    "RouteAmbiguityError",
    "PatternDiagnostic",
    # Matcher
    "PatternMatcher",
    "MatchResult",
    # OpenAPI
    "generate_openapi_params",
    # Caching (NEW in v0.2.0)
    "PatternCache",
    "compile_pattern",
    "get_global_cache",
    "set_global_cache",
    # Auto-fix (NEW in v0.2.0)
    "AutoFixEngine",
    "FixSuggestion",
    "DiagnosticFix",
    "generate_fix_suggestions",
    "ErrorRecovery",
]
