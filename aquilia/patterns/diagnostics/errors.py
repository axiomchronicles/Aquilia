"""
Diagnostic errors for AquilaPatterns.
"""

from dataclasses import dataclass
from typing import Optional, List
from ..compiler.ast_nodes import Span


@dataclass
class PatternDiagnostic:
    """Base class for all pattern diagnostics."""
    message: str
    span: Optional[Span] = None
    file: Optional[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

    def format(self) -> str:
        """Format diagnostic for display."""
        parts = []

        # Error type and location
        error_type = self.__class__.__name__
        if self.file and self.span:
            parts.append(f"{error_type}: {self.message}")
            parts.append(f"  --> {self.file}:{self.span.line}:{self.span.column}")
        elif self.span:
            parts.append(f"{error_type}: {self.message}")
            parts.append(f"  --> {self.span}")
        else:
            parts.append(f"{error_type}: {self.message}")

        # Suggestions
        if self.suggestions:
            parts.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                parts.append(f"  {i}) {suggestion}")

        return "\n".join(parts)


class PatternSyntaxError(PatternDiagnostic, Exception):
    """Syntax error in pattern."""
    pass


class PatternSemanticError(PatternDiagnostic, Exception):
    """Semantic error in pattern."""
    pass


class RouteAmbiguityError(PatternDiagnostic, Exception):
    """Two routes have ambiguous patterns."""

    def __init__(
        self,
        message: str,
        pattern1: str,
        pattern2: str,
        specificity: int,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.pattern1 = pattern1
        self.pattern2 = pattern2
        self.specificity = specificity

    def format(self) -> str:
        """Format ambiguity error."""
        parts = [
            f"RouteAmbiguityError: {self.message}",
            f"  Pattern 1: {self.pattern1} (specificity={self.specificity})",
            f"  Pattern 2: {self.pattern2} (specificity={self.specificity})",
        ]

        if self.suggestions:
            parts.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                parts.append(f"  {i}) {suggestion}")

        return "\n".join(parts)
