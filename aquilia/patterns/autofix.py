"""
Auto-fix suggestions and error recovery for pattern diagnostics.

Provides intelligent suggestions for common pattern errors:
- Missing closing delimiters
- Invalid type names with fuzzy matching
- Duplicate parameter names
- Conflicting patterns
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher, get_close_matches

from .compiler.ast_nodes import PatternAST, TokenSegment, QueryParam
from .compiler.compiler import CompiledPattern
from .compiler.specificity import calculate_specificity
from .types.registry import TypeRegistry
from .validators.registry import ConstraintRegistry


@dataclass
class FixSuggestion:
    """Represents a single fix suggestion."""
    title: str
    description: str
    old_code: str
    new_code: str
    confidence: float  # 0.0 - 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "old_code": self.old_code,
            "new_code": self.new_code,
            "confidence": self.confidence,
        }


@dataclass
class DiagnosticFix:
    """Container for diagnostic with fix suggestions."""
    error_message: str
    suggestions: List[FixSuggestion]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error_message,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


class AutoFixEngine:
    """Engine for generating automatic fix suggestions."""
    
    def __init__(
        self,
        type_registry: Optional[TypeRegistry] = None,
        constraint_registry: Optional[ConstraintRegistry] = None,
    ):
        self.type_registry = type_registry or TypeRegistry.default()
        self.constraint_registry = constraint_registry or ConstraintRegistry()
    
    def suggest_type_fix(self, invalid_type: str) -> List[FixSuggestion]:
        """
        Suggest fixes for invalid type names.
        
        Uses fuzzy matching to find similar valid types.
        """
        suggestions = []
        valid_types = list(self.type_registry.castors.keys())
        
        # Find close matches
        matches = get_close_matches(invalid_type, valid_types, n=3, cutoff=0.6)
        
        for match in matches:
            # Calculate similarity
            similarity = SequenceMatcher(None, invalid_type, match).ratio()
            
            suggestions.append(FixSuggestion(
                title=f"Did you mean '{match}'?",
                description=f"Replace '{invalid_type}' with valid type '{match}'",
                old_code=f"«param:{invalid_type}»",
                new_code=f"«param:{match}»",
                confidence=similarity,
            ))
        
        # If no close matches, suggest 'str' as fallback
        if not matches:
            suggestions.append(FixSuggestion(
                title="Use 'str' type",
                description=f"Replace unknown type '{invalid_type}' with 'str'",
                old_code=f"«param:{invalid_type}»",
                new_code="«param:str»",
                confidence=0.5,
            ))
        
        return suggestions
    
    def suggest_delimiter_fix(self, pattern: str, expected: str) -> List[FixSuggestion]:
        """
        Suggest fixes for missing or mismatched delimiters.
        
        Args:
            pattern: The problematic pattern
            expected: Expected closing delimiter
        """
        suggestions = []
        
        # Check for common mistakes
        if "«" in pattern and "»" not in pattern:
            # Missing closing guillemet
            fixed = pattern + "»"
            suggestions.append(FixSuggestion(
                title="Add missing closing guillemet",
                description="Pattern has unclosed token delimiter",
                old_code=pattern,
                new_code=fixed,
                confidence=0.95,
            ))
        
        elif "[" in pattern and "]" not in pattern:
            # Missing closing bracket
            fixed = pattern + "]"
            suggestions.append(FixSuggestion(
                title="Add missing closing bracket",
                description="Optional group is not closed",
                old_code=pattern,
                new_code=fixed,
                confidence=0.95,
            ))
        
        elif "(" in pattern and ")" not in pattern:
            # Missing closing paren
            fixed = pattern + ")"
            suggestions.append(FixSuggestion(
                title="Add missing closing parenthesis",
                description="Constraint predicate is not closed",
                old_code=pattern,
                new_code=fixed,
                confidence=0.95,
            ))
        
        return suggestions
    
    def suggest_duplicate_param_fix(
        self,
        pattern: str,
        duplicate_name: str,
        occurrences: List[int],
    ) -> List[FixSuggestion]:
        """
        Suggest fixes for duplicate parameter names.
        
        Args:
            pattern: The pattern with duplicates
            duplicate_name: The duplicate parameter name
            occurrences: Positions of duplicates
        """
        suggestions = []
        
        # Suggest renaming subsequent occurrences
        for idx, occurrence in enumerate(occurrences[1:], start=2):
            new_name = f"{duplicate_name}{idx}"
            suggestions.append(FixSuggestion(
                title=f"Rename duplicate to '{new_name}'",
                description=f"Parameter '{duplicate_name}' appears multiple times",
                old_code=f"«{duplicate_name}:...",
                new_code=f"«{new_name}:...",
                confidence=0.8,
            ))
        
        return suggestions
    
    def suggest_conflict_resolution(
        self,
        pattern1: CompiledPattern,
        pattern2: CompiledPattern,
    ) -> List[FixSuggestion]:
        """
        Suggest fixes for conflicting patterns with same specificity.
        
        Args:
            pattern1: First conflicting pattern
            pattern2: Second conflicting pattern
        """
        suggestions = []
        
        # Check if adding constraints could resolve
        if len(pattern1.params) > 0 and len(pattern2.params) > 0:
            param_name = list(pattern1.params.keys())[0]
            
            suggestions.append(FixSuggestion(
                title="Add constraint to disambiguate",
                description="Add a constraint to make patterns unique",
                old_code=f"«{param_name}:int»",
                new_code=f"«{param_name}:int|min=100»",
                confidence=0.7,
            ))
        
        # Suggest changing type to more specific
        for param_name, param in pattern1.params.items():
            if param.param_type == "str":
                suggestions.append(FixSuggestion(
                    title=f"Use more specific type for '{param_name}'",
                    description="Replace generic 'str' with specific type like 'slug' or 'uuid'",
                    old_code=f"«{param_name}:str»",
                    new_code=f"«{param_name}:slug»",
                    confidence=0.6,
                ))
        
        # Suggest adding static prefix
        if not pattern1.static_prefix or len(pattern1.static_prefix) < 3:
            suggestions.append(FixSuggestion(
                title="Add static prefix to distinguish patterns",
                description="Adding a static prefix increases specificity",
                old_code=pattern1.raw,
                new_code=f"/api{pattern1.raw}",
                confidence=0.8,
            ))
        
        return suggestions
    
    def suggest_empty_token_fix(self, pattern: str) -> List[FixSuggestion]:
        """Suggest fixes for empty tokens «»."""
        suggestions = []
        
        suggestions.append(FixSuggestion(
            title="Add parameter name",
            description="Token must have a name",
            old_code="«»",
            new_code="«param:str»",
            confidence=0.9,
        ))
        
        return suggestions
    
    def suggest_constraint_fix(
        self,
        invalid_constraint: str,
        param_type: str,
    ) -> List[FixSuggestion]:
        """
        Suggest fixes for invalid constraints.
        
        Args:
            invalid_constraint: The invalid constraint operator
            param_type: Type of the parameter
        """
        suggestions = []
        valid_constraints = ["min", "max", "regex", "enum"]
        
        # Find close matches
        matches = get_close_matches(invalid_constraint, valid_constraints, n=2, cutoff=0.6)
        
        for match in matches:
            suggestions.append(FixSuggestion(
                title=f"Did you mean '{match}'?",
                description=f"Replace '{invalid_constraint}' with valid constraint '{match}'",
                old_code=f"|{invalid_constraint}=...",
                new_code=f"|{match}=...",
                confidence=0.85,
            ))
        
        # Suggest valid constraints for type
        if param_type in ["int", "float"]:
            suggestions.append(FixSuggestion(
                title="Use 'min' or 'max' for numeric types",
                description=f"Numeric types support min/max constraints",
                old_code=f"|{invalid_constraint}=...",
                new_code="|min=0|max=100",
                confidence=0.7,
            ))
        
        elif param_type == "str":
            suggestions.append(FixSuggestion(
                title="Use 'regex' for string validation",
                description="String types can use regex patterns",
                old_code=f"|{invalid_constraint}=...",
                new_code="|regex=[a-z]+",
                confidence=0.7,
            ))
        
        return suggestions
    
    def suggest_regex_fix(self, pattern: str, regex_error: str) -> List[FixSuggestion]:
        """Suggest fixes for invalid regex patterns."""
        suggestions = []
        
        # Common regex mistakes
        if "(" in pattern and ")" not in pattern:
            suggestions.append(FixSuggestion(
                title="Close regex group",
                description="Regex has unclosed group",
                old_code=pattern,
                new_code=pattern + ")",
                confidence=0.9,
            ))
        
        if "[" in pattern and "]" not in pattern:
            suggestions.append(FixSuggestion(
                title="Close regex character class",
                description="Character class is not closed",
                old_code=pattern,
                new_code=pattern + "]",
                confidence=0.9,
            ))
        
        # Suggest escaping special characters
        special_chars = r".*+?[]{}()|^$\\"
        for char in special_chars:
            if char in pattern and f"\\{char}" not in pattern:
                fixed = pattern.replace(char, f"\\{char}")
                suggestions.append(FixSuggestion(
                    title=f"Escape special character '{char}'",
                    description="Special regex characters should be escaped",
                    old_code=pattern,
                    new_code=fixed,
                    confidence=0.75,
                ))
                break  # Only suggest first fix
        
        return suggestions


class ErrorRecovery:
    """Error recovery strategies for parser."""
    
    @staticmethod
    def recover_from_unclosed_token(source: str, pos: int) -> Optional[str]:
        """
        Attempt to recover from unclosed token by adding closing delimiter.
        
        Args:
            source: Original source
            pos: Position of error
        
        Returns:
            Recovered source or None
        """
        # Find the last opening delimiter
        last_open = source.rfind("«", 0, pos)
        if last_open == -1:
            return None
        
        # Check if there's a matching close after the open
        if "»" not in source[last_open:]:
            # Add closing delimiter
            # Find next slash or end
            next_slash = source.find("/", last_open)
            if next_slash == -1:
                return source + "»"
            else:
                return source[:next_slash] + "»" + source[next_slash:]
        
        return None
    
    @staticmethod
    def recover_from_unclosed_bracket(source: str, pos: int) -> Optional[str]:
        """Recover from unclosed optional group."""
        last_open = source.rfind("[", 0, pos)
        if last_open == -1:
            return None
        
        if "]" not in source[last_open:]:
            return source + "]"
        
        return None
    
    @staticmethod
    def recover_from_invalid_token(source: str, pos: int) -> Optional[str]:
        """
        Recover from invalid token by providing default.
        
        Args:
            source: Original source
            pos: Position of error
        
        Returns:
            Recovered source with default token
        """
        # Find empty token «»
        if source[pos:pos+2] == "«»":
            return source[:pos] + "«param:str»" + source[pos+2:]
        
        return None


def generate_fix_suggestions(
    error_type: str,
    error_message: str,
    pattern: str,
    **context,
) -> DiagnosticFix:
    """
    Generate fix suggestions for a diagnostic error.
    
    Args:
        error_type: Type of error (syntax, semantic, ambiguity)
        error_message: Error message
        pattern: The problematic pattern
        **context: Additional context (e.g., invalid_type, duplicate_name)
    
    Returns:
        Diagnostic with fix suggestions
    """
    engine = AutoFixEngine()
    suggestions = []
    
    # Route to appropriate suggestion generator
    if "unknown type" in error_message.lower():
        invalid_type = context.get("invalid_type", "")
        suggestions = engine.suggest_type_fix(invalid_type)
    
    elif "unterminated" in error_message.lower() or "unclosed" in error_message.lower():
        expected = context.get("expected_delimiter", "»")
        suggestions = engine.suggest_delimiter_fix(pattern, expected)
    
    elif "duplicate" in error_message.lower():
        duplicate_name = context.get("duplicate_name", "")
        occurrences = context.get("occurrences", [])
        suggestions = engine.suggest_duplicate_param_fix(pattern, duplicate_name, occurrences)
    
    elif "empty token" in error_message.lower():
        suggestions = engine.suggest_empty_token_fix(pattern)
    
    elif "invalid constraint" in error_message.lower():
        invalid_constraint = context.get("invalid_constraint", "")
        param_type = context.get("param_type", "str")
        suggestions = engine.suggest_constraint_fix(invalid_constraint, param_type)
    
    elif "regex" in error_message.lower():
        regex_error = context.get("regex_error", "")
        suggestions = engine.suggest_regex_fix(pattern, regex_error)
    
    elif "conflict" in error_message.lower() or "ambiguous" in error_message.lower():
        pattern1 = context.get("pattern1")
        pattern2 = context.get("pattern2")
        if pattern1 and pattern2:
            suggestions = engine.suggest_conflict_resolution(pattern1, pattern2)
    
    return DiagnosticFix(
        error_message=error_message,
        suggestions=suggestions,
    )
