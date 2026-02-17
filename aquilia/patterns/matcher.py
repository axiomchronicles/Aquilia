"""
Pattern matcher with optimized matching algorithm.

Performance notes (v0.2.0):
- Castors and validators are called **inline** (no thread dispatch).
  int(), str(), and typical constraint lambdas are trivial CPU-bound
  operations that complete in < 100 ns.  Dispatching them to a thread
  pool via anyio.to_thread.run_sync added 10-50 us of overhead **per
  parameter per match** — completely unacceptable on the hot path.
- Regex-based matching is preferred when available (compiled during
  pattern compilation) for single-shot matching.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from .compiler.compiler import CompiledPattern
from .compiler.ast_nodes import StaticSegment, TokenSegment, SplatSegment, OptionalGroup


@dataclass
class MatchResult:
    """Result of pattern matching."""
    pattern: CompiledPattern
    params: Dict[str, Any]
    query: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern.raw,
            "params": self.params,
            "query": self.query,
        }


class PatternMatcher:
    """Matches request paths against compiled patterns."""

    def __init__(self):
        self.patterns: List[CompiledPattern] = []

    def add_pattern(self, pattern: CompiledPattern):
        """Add a compiled pattern to the matcher."""
        self.patterns.append(pattern)
        # Sort by specificity (descending)
        self.patterns.sort(key=lambda p: p.specificity, reverse=True)

    async def match(
        self,
        path: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[MatchResult]:
        """
        Match a path against patterns.

        All castor/validator calls are executed inline (no thread dispatch)
        since they are trivial CPU-bound operations.
        """
        query_params = query_params or {}

        # Remove trailing slash for matching
        if len(path) > 1 and path[-1] == "/":
            path = path[:-1]

        # Try each pattern in specificity order
        for pattern in self.patterns:
            result = await self._try_match(pattern, path, query_params)
            if result:
                return result

        return None

    async def _try_match(
        self,
        pattern: CompiledPattern,
        path: str,
        query_params: Dict[str, str],
    ) -> Optional[MatchResult]:
        """Try to match a single pattern."""
        # Quick prefix check
        if pattern.static_prefix and not path.startswith(pattern.static_prefix):
            return None

        # Use regex if available
        if pattern.compiled_re:
            match = pattern.compiled_re.match(path)
            if not match:
                return None

            params = {}
            for name, param in pattern.params.items():
                value_str = match.group(name)
                try:
                    # Cast value inline - castors are trivial (int, str, etc.)
                    value = param.castor(value_str)

                    # Validate constraints inline
                    for validator in param.validators:
                        if not validator(value):
                            return None

                    params[name] = value
                except (ValueError, TypeError):
                    return None
        else:
            # Segment-by-segment matching
            result = self._match_segments_sync(pattern, path)
            if result is None:
                return None
            params = result

        # Match query parameters
        query = {}
        for name, param in pattern.query.items():
            if name in query_params:
                value_str = query_params[name]
                try:
                    value = param.castor(value_str)

                    for validator in param.validators:
                        if not validator(value):
                            return None

                    query[name] = value
                except (ValueError, TypeError):
                    return None
            elif param.default is not None:
                query[name] = param.default
            else:
                # Required param missing
                return None

        return MatchResult(pattern=pattern, params=params, query=query)

    def _match_segments_sync(
        self,
        pattern: CompiledPattern,
        path: str,
    ) -> Optional[Dict[str, Any]]:
        """Match path segments without regex (fully synchronous)."""
        path_segments = path.split("/")
        # Filter empty segments from leading/trailing slashes
        path_segments = [s for s in path_segments if s]
        pattern_segments = pattern.ast.segments
        params: Dict[str, Any] = {}
        path_idx = 0
        pattern_idx = 0
        num_path = len(path_segments)
        num_pattern = len(pattern_segments)

        while pattern_idx < num_pattern:
            segment = pattern_segments[pattern_idx]

            if isinstance(segment, StaticSegment):
                if path_idx >= num_path or path_segments[path_idx] != segment.value:
                    return None
                path_idx += 1
            elif isinstance(segment, TokenSegment):
                if path_idx >= num_path:
                    return None

                value_str = path_segments[path_idx]
                param = pattern.params[segment.name]

                try:
                    value = param.castor(value_str)

                    for validator in param.validators:
                        if not validator(value):
                            return None

                    params[segment.name] = value
                except (ValueError, TypeError):
                    return None

                path_idx += 1
            elif isinstance(segment, SplatSegment):
                remaining = path_segments[path_idx:]
                if segment.param_type == "path":
                    params[segment.name] = "/".join(remaining)
                else:
                    params[segment.name] = remaining
                path_idx = num_path
            elif isinstance(segment, OptionalGroup):
                opt_result = self._match_optional_sync(segment, path_segments, path_idx, pattern)
                if opt_result:
                    params.update(opt_result["params"])
                    path_idx = opt_result["idx"]

            pattern_idx += 1

        if path_idx != num_path:
            return None

        return params

    def _match_optional_sync(
        self,
        group: OptionalGroup,
        path_segments: List[str],
        start_idx: int,
        pattern: CompiledPattern,
    ) -> Optional[Dict[str, Any]]:
        """Try to match an optional group (fully synchronous)."""
        params: Dict[str, Any] = {}
        idx = start_idx
        num_path = len(path_segments)

        for segment in group.segments:
            if isinstance(segment, StaticSegment):
                if idx >= num_path or path_segments[idx] != segment.value:
                    return None
                idx += 1
            elif isinstance(segment, TokenSegment):
                if idx >= num_path:
                    return None

                value_str = path_segments[idx]
                param = pattern.params[segment.name]

                try:
                    value = param.castor(value_str)

                    for validator in param.validators:
                        if not validator(value):
                            return None

                    params[segment.name] = value
                except (ValueError, TypeError):
                    return None

                idx += 1

        return {"params": params, "idx": idx}
