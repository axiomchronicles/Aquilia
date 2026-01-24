"""
Pattern matcher with optimized matching algorithm.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import anyio

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

        Uses anyio for async context but matching is still sync.
        """
        query_params = query_params or {}

        # Remove trailing slash for matching
        path = path.rstrip("/") if len(path) > 1 else path

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
                    # Cast value
                    value = await anyio.to_thread.run_sync(param.castor, value_str)

                    # Validate constraints
                    for validator in param.validators:
                        if not await anyio.to_thread.run_sync(validator, value):
                            return None

                    params[name] = value
                except (ValueError, TypeError):
                    return None
        else:
            # Segment-by-segment matching
            result = await self._match_segments(pattern, path)
            if result is None:
                return None
            params = result

        # Match query parameters
        query = {}
        for name, param in pattern.query.items():
            if name in query_params:
                value_str = query_params[name]
                try:
                    value = await anyio.to_thread.run_sync(param.castor, value_str)

                    # Validate constraints
                    for validator in param.validators:
                        if not await anyio.to_thread.run_sync(validator, value):
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

    async def _match_segments(
        self,
        pattern: CompiledPattern,
        path: str,
    ) -> Optional[Dict[str, Any]]:
        """Match path segments without regex."""
        path_segments = [s for s in path.split("/") if s]
        pattern_segments = pattern.ast.segments
        params = {}
        path_idx = 0
        pattern_idx = 0

        while pattern_idx < len(pattern_segments):
            segment = pattern_segments[pattern_idx]

            if isinstance(segment, StaticSegment):
                if path_idx >= len(path_segments) or path_segments[path_idx] != segment.value:
                    return None
                path_idx += 1
            elif isinstance(segment, TokenSegment):
                if path_idx >= len(path_segments):
                    return None

                value_str = path_segments[path_idx]
                param = pattern.params[segment.name]

                try:
                    value = await anyio.to_thread.run_sync(param.castor, value_str)

                    # Validate constraints
                    for validator in param.validators:
                        if not await anyio.to_thread.run_sync(validator, value):
                            return None

                    params[segment.name] = value
                except (ValueError, TypeError):
                    return None

                path_idx += 1
            elif isinstance(segment, SplatSegment):
                # Capture remaining segments
                remaining = path_segments[path_idx:]
                param = pattern.params[segment.name]

                if segment.param_type == "path":
                    # Join as string
                    value = "/".join(remaining)
                else:
                    # Return as list
                    value = remaining

                params[segment.name] = value
                path_idx = len(path_segments)
            elif isinstance(segment, OptionalGroup):
                # Try to match optional group
                saved_idx = path_idx
                opt_result = await self._match_optional(segment, path_segments, path_idx, pattern)
                if opt_result:
                    params.update(opt_result["params"])
                    path_idx = opt_result["idx"]
                # If optional doesn't match, continue (that's OK)

            pattern_idx += 1

        # All path segments must be consumed
        if path_idx != len(path_segments):
            return None

        return params

    async def _match_optional(
        self,
        group: OptionalGroup,
        path_segments: List[str],
        start_idx: int,
        pattern: CompiledPattern,
    ) -> Optional[Dict[str, Any]]:
        """Try to match an optional group."""
        params = {}
        idx = start_idx

        for segment in group.segments:
            if isinstance(segment, StaticSegment):
                if idx >= len(path_segments) or path_segments[idx] != segment.value:
                    return None
                idx += 1
            elif isinstance(segment, TokenSegment):
                if idx >= len(path_segments):
                    return None

                value_str = path_segments[idx]
                param = pattern.params[segment.name]

                try:
                    value = await anyio.to_thread.run_sync(param.castor, value_str)

                    # Validate constraints
                    for validator in param.validators:
                        if not await anyio.to_thread.run_sync(validator, value):
                            return None

                    params[segment.name] = value
                except (ValueError, TypeError):
                    return None

                idx += 1

        return {"params": params, "idx": idx}
