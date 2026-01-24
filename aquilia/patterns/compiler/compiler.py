"""
Compiler that transforms AST into executable compiled patterns.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Pattern
import json

from .ast_nodes import (
    PatternAST,
    StaticSegment,
    TokenSegment,
    OptionalGroup,
    SplatSegment,
    QueryParam,
    Constraint,
    ConstraintKind,
    BaseSegment,
)
from .specificity import calculate_specificity
from ..types.registry import TypeRegistry
from ..validators.registry import ConstraintRegistry
from ..transforms.registry import TransformRegistry
from ..diagnostics.errors import PatternSemanticError


@dataclass
class CompiledParam:
    """Compiled parameter metadata."""
    index: int
    name: str
    param_type: str
    constraints: List[Dict[str, Any]]
    default: Optional[Any]
    transform: Optional[str]
    castor: Callable[[str], Any]
    validators: List[Callable[[Any], bool]]


@dataclass
class CompiledPattern:
    """Fully compiled pattern ready for matching."""
    raw: str
    file: Optional[str]
    span: Optional[Dict[str, int]]
    static_prefix: str
    segments: List[Dict[str, Any]]
    params: Dict[str, CompiledParam]
    query: Dict[str, CompiledParam]
    specificity: int
    compiled_re: Optional[Pattern]
    castors: List[Callable]
    openapi: Dict[str, Any]
    ast: PatternAST

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "raw": self.raw,
            "file": self.file,
            "span": self.span,
            "static_prefix": self.static_prefix,
            "segments": self.segments,
            "params": {
                name: {
                    "index": p.index,
                    "type": p.param_type,
                    "constraints": p.constraints,
                    "default": p.default,
                    "transform": p.transform,
                }
                for name, p in self.params.items()
            },
            "query": {
                name: {
                    "index": p.index,
                    "type": p.param_type,
                    "constraints": p.constraints,
                    "default": p.default,
                    "transform": p.transform,
                }
                for name, p in self.query.items()
            },
            "specificity": self.specificity,
            "openapi": self.openapi,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class PatternCompiler:
    """Compiles AST into optimized executable patterns."""

    def __init__(
        self,
        type_registry: Optional[TypeRegistry] = None,
        constraint_registry: Optional[ConstraintRegistry] = None,
        transform_registry: Optional[TransformRegistry] = None,
    ):
        self.type_registry = type_registry or TypeRegistry.default()
        self.constraint_registry = constraint_registry or ConstraintRegistry.default()
        self.transform_registry = transform_registry or TransformRegistry.default()

    def compile(self, ast: PatternAST) -> CompiledPattern:
        """Compile AST into executable pattern."""
        # Extract static prefix
        static_prefix = ast.get_static_prefix()

        # Validate no duplicate param names
        param_names = ast.get_param_names()
        if len(param_names) != len(set(param_names)):
            duplicates = [name for name in param_names if param_names.count(name) > 1]
            raise PatternSemanticError(
                f"Duplicate parameter names: {', '.join(set(duplicates))}",
                span=ast.span,
                file=ast.file,
            )

        # Compile parameters
        params = {}
        param_index = 0

        def compile_segments(segments: List[BaseSegment]):
            nonlocal param_index
            for segment in segments:
                if isinstance(segment, TokenSegment):
                    param = self._compile_param(segment, param_index)
                    params[segment.name] = param
                    param_index += 1
                elif isinstance(segment, SplatSegment):
                    param = self._compile_splat(segment, param_index)
                    params[segment.name] = param
                    param_index += 1
                elif isinstance(segment, OptionalGroup):
                    compile_segments(segment.segments)

        compile_segments(ast.segments)

        # Compile query parameters
        query = {}
        for i, qparam in enumerate(ast.query_params):
            query[qparam.name] = self._compile_query_param(qparam, i)

        # Calculate specificity
        specificity = calculate_specificity(ast)

        # Compile regex if needed
        compiled_re = self._compile_regex(ast) if self._needs_regex(ast) else None

        # Build castors list
        castors = [p.castor for p in params.values()]

        # Generate OpenAPI metadata
        openapi = self._generate_openapi(ast, params, query)

        # Serialize segments
        segments = [seg.to_dict() for seg in ast.segments]

        return CompiledPattern(
            raw=ast.raw,
            file=ast.file,
            span={"start": ast.span.start, "end": ast.span.end} if ast.span else None,
            static_prefix=static_prefix,
            segments=segments,
            params=params,
            query=query,
            specificity=specificity,
            compiled_re=compiled_re,
            castors=castors,
            openapi=openapi,
            ast=ast,
        )

    def _compile_param(self, segment: TokenSegment, index: int) -> CompiledParam:
        """Compile a token parameter."""
        # Get type castor
        castor = self.type_registry.get_castor(segment.param_type)

        # Compile constraints
        validators = []
        constraints_data = []
        for constraint in segment.constraints:
            validator = self._compile_constraint(constraint, segment.param_type)
            if validator:
                validators.append(validator)
            constraints_data.append(constraint.to_dict())

        return CompiledParam(
            index=index,
            name=segment.name,
            param_type=segment.param_type,
            constraints=constraints_data,
            default=segment.default,
            transform=segment.transform.name if segment.transform else None,
            castor=castor,
            validators=validators,
        )

    def _compile_splat(self, segment: SplatSegment, index: int) -> CompiledParam:
        """Compile a splat parameter."""
        castor = self.type_registry.get_castor(segment.param_type)

        return CompiledParam(
            index=index,
            name=segment.name,
            param_type=segment.param_type,
            constraints=[],
            default=None,
            transform=None,
            castor=castor,
            validators=[],
        )

    def _compile_query_param(self, qparam: QueryParam, index: int) -> CompiledParam:
        """Compile a query parameter."""
        castor = self.type_registry.get_castor(qparam.param_type)

        validators = []
        constraints_data = []
        for constraint in qparam.constraints:
            validator = self._compile_constraint(constraint, qparam.param_type)
            if validator:
                validators.append(validator)
            constraints_data.append(constraint.to_dict())

        return CompiledParam(
            index=index,
            name=qparam.name,
            param_type=qparam.param_type,
            constraints=constraints_data,
            default=qparam.default,
            transform=None,
            castor=castor,
            validators=validators,
        )

    def _compile_constraint(self, constraint: Constraint, param_type: str) -> Optional[Callable]:
        """Compile a constraint into a validator function."""
        if constraint.kind == ConstraintKind.MIN:
            return lambda value: value >= constraint.value
        elif constraint.kind == ConstraintKind.MAX:
            return lambda value: value <= constraint.value
        elif constraint.kind == ConstraintKind.REGEX:
            pattern = re.compile(constraint.value)
            return lambda value: bool(pattern.match(str(value)))
        elif constraint.kind == ConstraintKind.ENUM:
            allowed = set(constraint.value)
            return lambda value: value in allowed
        elif constraint.kind == ConstraintKind.PREDICATE:
            # Predicates handled separately at routing time
            return None
        return None

    def _needs_regex(self, ast: PatternAST) -> bool:
        """Check if pattern requires regex matching."""
        # For now, simple patterns use segment-by-segment matching
        # Complex patterns with optional groups might need regex
        has_optional = any(isinstance(seg, OptionalGroup) for seg in ast.segments)
        return has_optional

    def _compile_regex(self, ast: PatternAST) -> Pattern:
        """Compile AST into a regex pattern."""
        parts = ["^"]

        def build_regex(segments: List[BaseSegment], optional: bool = False):
            group_parts = []
            for segment in segments:
                if isinstance(segment, StaticSegment):
                    group_parts.append(re.escape(segment.value))
                elif isinstance(segment, TokenSegment):
                    # Use named group
                    if segment.constraints:
                        # Check for regex constraint
                        regex_constraint = next(
                            (c for c in segment.constraints if c.kind == ConstraintKind.REGEX),
                            None
                        )
                        if regex_constraint:
                            group_parts.append(f"(?P<{segment.name}>{regex_constraint.value})")
                        else:
                            group_parts.append(f"(?P<{segment.name}>[^/]+)")
                    else:
                        group_parts.append(f"(?P<{segment.name}>[^/]+)")
                elif isinstance(segment, SplatSegment):
                    group_parts.append(f"(?P<{segment.name}>.*)")
                elif isinstance(segment, OptionalGroup):
                    inner = []
                    build_regex(segment.segments, optional=True)
                    if inner:
                        group_parts.append("(?:" + "/".join(inner) + ")?")

            if optional:
                return "(?:/" + "/".join(group_parts) + ")?"
            else:
                return "/".join(group_parts)

        regex_str = build_regex(ast.segments)
        parts.append(regex_str)
        parts.append("$")

        return re.compile("".join(parts))

    def _generate_openapi(
        self,
        ast: PatternAST,
        params: Dict[str, CompiledParam],
        query: Dict[str, CompiledParam],
    ) -> Dict[str, Any]:
        """Generate OpenAPI parameter schemas."""
        openapi_params = []

        # Path parameters
        for name, param in params.items():
            schema = self._param_to_openapi_schema(param)
            openapi_params.append({
                "name": name,
                "in": "path",
                "required": param.default is None,
                "schema": schema,
            })

        # Query parameters
        for name, param in query.items():
            schema = self._param_to_openapi_schema(param)
            openapi_params.append({
                "name": name,
                "in": "query",
                "required": param.default is None,
                "schema": schema,
            })

        return {"parameters": openapi_params}

    def _param_to_openapi_schema(self, param: CompiledParam) -> Dict[str, Any]:
        """Convert parameter to OpenAPI schema."""
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "uuid": "string",
            "slug": "string",
            "path": "string",
            "json": "object",
            "any": "string",
        }

        schema = {
            "type": type_map.get(param.param_type, "string"),
        }

        # Add format hints
        if param.param_type == "uuid":
            schema["format"] = "uuid"
        elif param.param_type == "slug":
            schema["pattern"] = "^[a-z0-9-]+$"

        # Add constraints
        for constraint in param.constraints:
            if constraint["kind"] == "min":
                if param.param_type in ("int", "float"):
                    schema["minimum"] = constraint["value"]
                else:
                    schema["minLength"] = constraint["value"]
            elif constraint["kind"] == "max":
                if param.param_type in ("int", "float"):
                    schema["maximum"] = constraint["value"]
                else:
                    schema["maxLength"] = constraint["value"]
            elif constraint["kind"] == "regex":
                schema["pattern"] = constraint["value"]
            elif constraint["kind"] == "enum":
                schema["enum"] = constraint["value"]

        # Add default
        if param.default is not None:
            schema["default"] = param.default

        return schema
