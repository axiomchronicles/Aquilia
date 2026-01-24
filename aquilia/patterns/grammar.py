"""
Formal EBNF grammar for AquilaPatterns.

Grammar Specification
=====================

<pattern> ::= "/" <segment-list> [ "/" ] [ "?" <query-list> ]
<segment-list> ::= <segment> ( "/" <segment> )*
<segment> ::= <static> | <token> | <optional> | <splat>
<static> ::= <char>+
<token> ::= "«" <ident> [ ":" <type> ] [ "|" <constraint-list> ] [ "=" <default> ] [ "@" <transform> ] "»"
<optional> ::= "[" <segment-list> "]"
<splat> ::= "*" <ident> [ ":" <type> ]
<constraint-list> ::= <constraint> ( "|" <constraint> )*
<constraint> ::= <cmp> | "re=" <regex-literal> | "in=(" <value-list> ")" | <predicate>
<cmp> ::= ("min="|"max=") <number>
<predicate> ::= <ident> ":" <value>
<query-list> ::= <qparam> ( "&" <qparam> )*
<qparam> ::= <ident> [ ":" <type> ] [ "|" <constraint-list> ] [ "=" <default> ]
<ident> ::= [A-Za-z_][A-Za-z0-9_]*
<type> ::= <ident>
<transform> ::= <ident> [ "(" <arg-list> ")" ]
<default> ::= <string-literal> | <number>

Built-in Types
==============
- str: string (default)
- int: integer
- float: floating point
- uuid: UUID v4
- slug: URL-safe slug [a-z0-9-]+
- path: multi-segment path
- bool: boolean (true/false, 1/0, yes/no)
- json: JSON object/array
- any: matches anything (no casting)

Token Examples
==============
«id:int»                          # Single segment, cast to int
«slug:slug|re=^[a-z0-9-]+$»      # Slug with regex constraint
«year:int|min=1900|max=2100»     # Integer with range
«tag:str|in=(python,rust,go)»    # Enum constraint
«data:json»                       # JSON object
*path                             # Multi-segment capture
*path:path                        # Multi-segment as string

Complete Pattern Examples
=========================
/users/«id:int»
/files/*path
/articles[/«year:int»[/«month:int»]]
/search?query:str|min=1&limit:int=10
/api/«v:ver@semver»/items
/blog/«slug:str|re=^[a-z0-9-]+$»
/data/«id:uuid»
/archive/«date:str|re=^\d{4}-\d{2}-\d{2}$»
/products[/«category:slug»]/«id:int»
"""

EBNF_GRAMMAR = """
pattern        = "/" segment_list [ "/" ] [ "?" query_list ]
segment_list   = segment ( "/" segment )*
segment        = static | token | optional | splat
static         = char+
token          = "«" ident [ ":" type ] [ "|" constraint_list ] [ "=" default ] [ "@" transform ] "»"
optional       = "[" segment_list "]"
splat          = "*" ident [ ":" type ]
constraint_list = constraint ( "|" constraint )*
constraint     = cmp | "re=" regex_literal | "in=(" value_list ")" | predicate
cmp            = ("min="|"max=") number
predicate      = ident ":" value
query_list     = qparam ( "&" qparam )*
qparam         = ident [ ":" type ] [ "|" constraint_list ] [ "=" default ]
ident          = [A-Za-z_][A-Za-z0-9_]*
type           = ident
transform      = ident [ "(" arg_list ")" ]
default        = string_literal | number
"""

# Token types for the lexer
TOKEN_TYPES = [
    "SLASH",           # /
    "LGUIL",           # «
    "RGUIL",           # »
    "LBRACKET",        # [
    "RBRACKET",        # ]
    "LPAREN",          # (
    "RPAREN",          # )
    "STAR",            # *
    "COLON",           # :
    "PIPE",            # |
    "EQUALS",          # =
    "AT",              # @
    "COMMA",           # ,
    "AMP",             # &
    "QUESTION",        # ?
    "IDENT",           # identifier
    "NUMBER",          # numeric literal
    "STRING",          # string literal
    "REGEX",           # regex literal
    "STATIC",          # static text
    "EOF",             # end of input
]

# Reserved keywords
KEYWORDS = {
    "min", "max", "re", "in",
    "str", "int", "float", "uuid", "slug", "path", "bool", "json", "any",
}

# Constraint operators
CONSTRAINT_OPS = {
    "min=": "minimum value or length",
    "max=": "maximum value or length",
    "re=": "regex pattern match",
    "in=": "value must be in enumerated set",
}

# Default types for common patterns
DEFAULT_TYPES = {
    "id": "int",
    "slug": "slug",
    "uuid": "uuid",
    "path": "path",
    "page": "int",
    "limit": "int",
    "offset": "int",
}
