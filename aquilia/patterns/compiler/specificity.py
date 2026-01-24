"""
Specificity scoring for pattern ranking.

Formula:
--------
- Static segment: +200
- Typed token with strong constraint (regex, enum, int, uuid): +120
- Typed token generic (str): +50
- Splat (*): +0
- Optional segment: -20 per optional node
- Predicate present: +10
- Segment count tiebreaker: + (segment_count * 2)
"""

from typing import List
from .ast_nodes import (
    PatternAST,
    StaticSegment,
    TokenSegment,
    OptionalGroup,
    SplatSegment,
    ConstraintKind,
    BaseSegment,
)


STRONG_TYPES = {"int", "float", "uuid", "bool", "json"}


def calculate_specificity(ast: PatternAST) -> int:
    """Calculate specificity score for pattern ranking."""
    score = 0
    segment_count = 0

    def score_segments(segments: List[BaseSegment], in_optional: bool = False):
        nonlocal score, segment_count

        for segment in segments:
            segment_count += 1

            if isinstance(segment, StaticSegment):
                score += 200
            elif isinstance(segment, TokenSegment):
                # Check type and constraints
                has_strong_constraint = (
                    segment.param_type in STRONG_TYPES
                    or any(c.kind in (ConstraintKind.REGEX, ConstraintKind.ENUM) for c in segment.constraints)
                )

                if has_strong_constraint:
                    score += 120
                else:
                    score += 50

                # Predicate bonus
                if any(c.kind == ConstraintKind.PREDICATE for c in segment.constraints):
                    score += 10

            elif isinstance(segment, SplatSegment):
                score += 0  # No bonus for splat
            elif isinstance(segment, OptionalGroup):
                score -= 20  # Penalty for optional
                score_segments(segment.segments, in_optional=True)

    score_segments(ast.segments)

    # Tiebreaker: segment count
    score += segment_count * 2

    return score
