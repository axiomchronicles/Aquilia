"""
Tokenizer and parser for AquilaPatterns.

Implements the formal EBNF grammar with error recovery and span tracking.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any
from enum import Enum

from .ast_nodes import (
    PatternAST,
    StaticSegment,
    TokenSegment,
    OptionalGroup,
    SplatSegment,
    QueryParam,
    Constraint,
    Transform,
    Span,
    ConstraintKind,
    BaseSegment,
)
from ..diagnostics.errors import PatternSyntaxError


class TokenType(str, Enum):
    """Token types for the lexer."""
    SLASH = "SLASH"
    LANGLE = "LANGLE"         # <
    RANGLE = "RANGLE"         # >
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    STAR = "STAR"
    COLON = "COLON"
    PIPE = "PIPE"
    EQUALS = "EQUALS"
    AT = "AT"
    COMMA = "COMMA"
    AMP = "AMP"
    QUESTION = "QUESTION"
    IDENT = "IDENT"
    NUMBER = "NUMBER"
    STRING = "STRING"
    STATIC = "STATIC"
    EOF = "EOF"


@dataclass
class PatternToken:
    """A lexical token with position information."""
    type: TokenType
    value: Any
    span: Span

    def __repr__(self) -> str:
        return f"{self.type}('{self.value}') at {self.span}"


class Tokenizer:
    """Tokenizer for URL patterns."""

    def __init__(self, source: str, filename: Optional[str] = None):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[PatternToken] = []

    def error(self, message: str) -> PatternSyntaxError:
        """Create syntax error at current position."""
        return PatternSyntaxError(
            message=message,
            span=Span(self.pos, self.pos + 1, self.line, self.column),
            file=self.filename,
        )

    def peek(self, offset: int = 0) -> Optional[str]:
        """Peek at character without consuming."""
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else None

    def advance(self) -> Optional[str]:
        """Consume and return next character."""
        if self.pos >= len(self.source):
            return None
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.peek() and self.peek() in " \t\n\r":
            self.advance()

    def read_ident(self) -> str:
        """Read identifier [A-Za-z_][A-Za-z0-9_]*."""
        start = self.pos
        if not (self.peek() and (self.peek().isalpha() or self.peek() == "_")):
            raise self.error("Expected identifier")

        while self.peek() and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()

        return self.source[start:self.pos]

    def read_number(self) -> float:
        """Read numeric literal."""
        start = self.pos
        has_dot = False

        while self.peek():
            ch = self.peek()
            if ch.isdigit():
                self.advance()
            elif ch == "." and not has_dot:
                has_dot = True
                self.advance()
            else:
                break

        try:
            value_str = self.source[start:self.pos]
            return float(value_str) if has_dot else int(value_str)
        except ValueError:
            raise self.error(f"Invalid number: {self.source[start:self.pos]}")

    def read_string(self, quote: str) -> str:
        """Read quoted string."""
        start = self.pos
        self.advance()  # skip opening quote

        escaped = False
        while self.peek():
            ch = self.peek()
            if escaped:
                escaped = False
                self.advance()
            elif ch == "\\":
                escaped = True
                self.advance()
            elif ch == quote:
                self.advance()  # skip closing quote
                return self.source[start + 1:self.pos - 1]
            else:
                self.advance()

        raise self.error(f"Unterminated string starting at pos {start}")

    def read_static(self) -> str:
        """Read static text until special character."""
        start = self.pos
        special = "/<[]?&*"

        while self.peek() and self.peek() not in special:
            self.advance()

        return self.source[start:self.pos]

    def tokenize(self) -> List[PatternToken]:
        """Tokenize the source into tokens."""
        self.tokens = []

        while self.pos < len(self.source):
            start_pos = self.pos
            start_line = self.line
            start_col = self.column

            ch = self.peek()

            if ch == "/":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.SLASH,
                    "/",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "<":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.LANGLE,
                    "<",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == ">":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.RANGLE,
                    ">",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "[":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.LBRACKET,
                    "[",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "]":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.RBRACKET,
                    "]",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "(":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.LPAREN,
                    "(",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == ")":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.RPAREN,
                    ")",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "*":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.STAR,
                    "*",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == ":":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.COLON,
                    ":",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "|":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.PIPE,
                    "|",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "=":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.EQUALS,
                    "=",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "@":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.AT,
                    "@",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == ",":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.COMMA,
                    ",",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "&":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.AMP,
                    "&",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch == "?":
                self.advance()
                self.tokens.append(PatternToken(
                    TokenType.QUESTION,
                    "?",
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch in " \t\n\r":
                self.skip_whitespace()
            elif ch == '"' or ch == "'":
                value = self.read_string(ch)
                self.tokens.append(PatternToken(
                    TokenType.STRING,
                    value,
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch.isdigit():
                value = self.read_number()
                self.tokens.append(PatternToken(
                    TokenType.NUMBER,
                    value,
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            elif ch.isalpha() or ch == "_":
                value = self.read_ident()
                self.tokens.append(PatternToken(
                    TokenType.IDENT,
                    value,
                    Span(start_pos, self.pos, start_line, start_col)
                ))
            else:
                # Static text
                value = self.read_static()
                if value:
                    self.tokens.append(PatternToken(
                        TokenType.STATIC,
                        value,
                        Span(start_pos, self.pos, start_line, start_col)
                    ))

        # Add EOF token
        self.tokens.append(PatternToken(
            TokenType.EOF,
            None,
            Span(self.pos, self.pos, self.line, self.column)
        ))

        return self.tokens


class PatternParser:
    """Parser for URL patterns following the EBNF grammar."""

    def __init__(self, tokens: List[PatternToken], filename: Optional[str] = None):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0

    def error(self, message: str) -> PatternSyntaxError:
        """Create syntax error at current token."""
        token = self.current()
        return PatternSyntaxError(
            message=message,
            span=token.span,
            file=self.filename,
        )

    def current(self) -> PatternToken:
        """Get current token."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def peek(self, offset: int = 0) -> PatternToken:
        """Peek at token without consuming."""
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else self.tokens[-1]

    def advance(self) -> PatternToken:
        """Consume and return current token."""
        token = self.current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> PatternToken:
        """Consume token of expected type or error."""
        token = self.current()
        if token.type != token_type:
            raise self.error(f"Expected {token_type}, got {token.type}")
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        return self.current().type in token_types

    def parse(self, raw: str) -> PatternAST:
        """Parse tokens into AST."""
        start_span = self.current().span
        segments = []
        query_params = []

        # Expect leading slash
        if not self.match(TokenType.SLASH):
            raise self.error("Pattern must start with /")
        self.advance()

        # Parse path components separated by slashes
        while not self.match(TokenType.EOF, TokenType.QUESTION):
            # Parse one path component (segments between slashes)
            component_segments = self.parse_segment_list()
            segments.extend(component_segments)
            
            # Check for slash (path separator)
            if self.match(TokenType.SLASH):
                self.advance()
            else:
                # No more slashes, should be EOF or QUESTION
                break

        # Optional query string
        if self.match(TokenType.QUESTION):
            self.advance()
            query_params = self.parse_query_list()

        # Expect EOF
        if not self.match(TokenType.EOF):
            raise self.error(f"Unexpected token: {self.current()}")

        end_span = self.tokens[self.pos - 1].span
        return PatternAST(
            raw=raw,
            segments=segments,
            query_params=query_params,
            file=self.filename,
            span=Span(start_span.start, end_span.end, start_span.line, start_span.column),
        )

    def parse_segment_list(self) -> List[BaseSegment]:
        """Parse segments within a single path component (until a slash or end)."""
        segments = []

        # Parse segments until we hit a slash, EOF, question mark, or bracket
        while not self.match(TokenType.EOF, TokenType.SLASH, TokenType.QUESTION, TokenType.RBRACKET):
            segment = self.parse_segment()
            
            # Combine adjacent static segments
            if segments and isinstance(segments[-1], StaticSegment) and isinstance(segment, StaticSegment):
                segments[-1].value += segment.value
                # Update span
                if segments[-1].span and segment.span:
                    segments[-1].span.end = segment.span.end
            else:
                segments.append(segment)

        return segments

    def parse_segment(self) -> BaseSegment:
        """Parse single segment."""
        if self.match(TokenType.LANGLE):
            return self.parse_token()
        elif self.match(TokenType.LBRACKET):
            return self.parse_optional()
        elif self.match(TokenType.STAR):
            return self.parse_splat()
        elif self.match(TokenType.STATIC, TokenType.IDENT):
            return self.parse_static()
        else:
            raise self.error(f"Expected segment, got {self.current().type}")

    def parse_static(self) -> StaticSegment:
        """Parse static text segment, combining IDENT and STATIC tokens."""
        start_token = self.current()
        parts = []
        start_span = start_token.span
        end_span = start_token.span
        
        # Consume IDENT and STATIC tokens together (for hyphenated names like "test-templates")
        while self.match(TokenType.IDENT, TokenType.STATIC):
            token = self.current()
            parts.append(token.value)
            end_span = token.span
            self.advance()
        
        value = "".join(parts)
        return StaticSegment(value=value, span=start_span)

    def parse_token(self) -> TokenSegment:
        """Parse token segment <name:type|constraints=default@transform>."""
        start = self.expect(TokenType.LANGLE).span

        # Parse name
        name_token = self.expect(TokenType.IDENT)
        name = name_token.value
        param_type = "str"
        constraints = []
        default = None
        transform = None

        # Optional type
        if self.match(TokenType.COLON):
            self.advance()
            type_token = self.expect(TokenType.IDENT)
            param_type = type_token.value

        # Optional constraints
        if self.match(TokenType.PIPE):
            self.advance()
            constraints = self.parse_constraint_list()

        # Optional default
        if self.match(TokenType.EQUALS):
            self.advance()
            default = self.parse_default_value()

        # Optional transform
        if self.match(TokenType.AT):
            self.advance()
            transform = self.parse_transform()

        end = self.expect(TokenType.RANGLE).span

        return TokenSegment(
            name=name,
            param_type=param_type,
            constraints=constraints,
            default=default,
            transform=transform,
            span=Span(start.start, end.end, start.line, start.column),
        )

    def parse_optional(self) -> OptionalGroup:
        """Parse optional group [...]."""
        start = self.expect(TokenType.LBRACKET).span
        segments = self.parse_segment_list()
        end = self.expect(TokenType.RBRACKET).span

        return OptionalGroup(
            segments=segments,
            span=Span(start.start, end.end, start.line, start.column),
        )

    def parse_splat(self) -> SplatSegment:
        """Parse splat segment *name or *name:type."""
        start = self.expect(TokenType.STAR).span
        name_token = self.expect(TokenType.IDENT)
        name = name_token.value
        param_type = "path"

        # Optional type
        if self.match(TokenType.COLON):
            self.advance()
            type_token = self.expect(TokenType.IDENT)
            param_type = type_token.value

        return SplatSegment(
            name=name,
            param_type=param_type,
            span=Span(start.start, name_token.span.end, start.line, start.column),
        )

    def parse_constraint_list(self) -> List[Constraint]:
        """Parse constraint list."""
        constraints = []
        constraints.append(self.parse_constraint())

        while self.match(TokenType.PIPE) and self.peek(1).type != TokenType.RANGLE:
            self.advance()
            constraints.append(self.parse_constraint())

        return constraints

    def parse_constraint(self) -> Constraint:
        """Parse single constraint."""
        token = self.current()

        if self.match(TokenType.IDENT):
            ident = self.advance().value

            if ident == "min" and self.match(TokenType.EQUALS):
                self.advance()
                value = self.expect(TokenType.NUMBER).value
                return Constraint(ConstraintKind.MIN, value, token.span)
            elif ident == "max" and self.match(TokenType.EQUALS):
                self.advance()
                value = self.expect(TokenType.NUMBER).value
                return Constraint(ConstraintKind.MAX, value, token.span)
            elif ident == "re" and self.match(TokenType.EQUALS):
                self.advance()
                value = self.expect(TokenType.STRING).value
                return Constraint(ConstraintKind.REGEX, value, token.span)
            elif ident == "in" and self.match(TokenType.EQUALS):
                self.advance()
                self.expect(TokenType.LPAREN)
                values = self.parse_value_list()
                self.expect(TokenType.RPAREN)
                return Constraint(ConstraintKind.ENUM, values, token.span)
            else:
                # Predicate: ident:value
                if self.match(TokenType.COLON):
                    self.advance()
                    if self.match(TokenType.STRING, TokenType.IDENT):
                        value = self.advance().value
                        return Constraint(ConstraintKind.PREDICATE, {ident: value}, token.span)

        raise self.error(f"Invalid constraint: {token}")

    def parse_value_list(self) -> List[Any]:
        """Parse comma-separated value list."""
        values = []
        
        if self.match(TokenType.STRING, TokenType.IDENT, TokenType.NUMBER):
            values.append(self.advance().value)

        while self.match(TokenType.COMMA):
            self.advance()
            if self.match(TokenType.STRING, TokenType.IDENT, TokenType.NUMBER):
                values.append(self.advance().value)

        return values

    def parse_default_value(self) -> Any:
        """Parse default value."""
        if self.match(TokenType.STRING, TokenType.NUMBER):
            return self.advance().value
        elif self.match(TokenType.IDENT):
            # Handle special values like true/false/null
            value = self.advance().value
            if value in ("true", "True"):
                return True
            elif value in ("false", "False"):
                return False
            elif value in ("null", "None"):
                return None
            return value
        else:
            raise self.error("Expected default value")

    def parse_transform(self) -> Transform:
        """Parse transform function."""
        name_token = self.expect(TokenType.IDENT)
        name = name_token.value
        args = []

        # Optional arguments
        if self.match(TokenType.LPAREN):
            self.advance()
            if not self.match(TokenType.RPAREN):
                args = self.parse_value_list()
            self.expect(TokenType.RPAREN)

        return Transform(name=name, args=args, span=name_token.span)

    def parse_query_list(self) -> List[QueryParam]:
        """Parse query parameter list."""
        params = []
        params.append(self.parse_query_param())

        while self.match(TokenType.AMP):
            self.advance()
            params.append(self.parse_query_param())

        return params

    def parse_query_param(self) -> QueryParam:
        """Parse single query parameter."""
        start = self.current().span
        name_token = self.expect(TokenType.IDENT)
        name = name_token.value
        param_type = "str"
        constraints = []
        default = None

        # Optional type
        if self.match(TokenType.COLON):
            self.advance()
            type_token = self.expect(TokenType.IDENT)
            param_type = type_token.value

        # Optional constraints
        if self.match(TokenType.PIPE):
            self.advance()
            constraints = self.parse_constraint_list()

        # Optional default
        if self.match(TokenType.EQUALS):
            self.advance()
            default = self.parse_default_value()

        return QueryParam(
            name=name,
            param_type=param_type,
            constraints=constraints,
            default=default,
            span=Span(start.start, self.tokens[self.pos - 1].span.end, start.line, start.column),
        )


def parse_pattern(source: str, filename: Optional[str] = None) -> PatternAST:
    """Parse a URL pattern into an AST."""
    tokenizer = Tokenizer(source, filename)
    tokens = tokenizer.tokenize()
    parser = PatternParser(tokens, filename)
    return parser.parse(source)
