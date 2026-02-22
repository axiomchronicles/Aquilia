"""
LSP (Language Server Protocol) support for IDE integration.

Generates metadata files and provides hover/autocomplete data.
"""

import json
from typing import Dict, Any, List
from pathlib import Path

from .compiler.compiler import CompiledPattern
from .grammar import TOKEN_TYPES, KEYWORDS, CONSTRAINT_OPS, DEFAULT_TYPES


def generate_lsp_metadata(
    patterns: List[CompiledPattern],
    output_path: Path,
):
    """
    Generate patterns.json for LSP consumption.

    This file contains all compiled pattern metadata for IDE tooling.
    """
    metadata = {
        "version": "1.0",
        "patterns": [
            {
                "raw": p.raw,
                "file": p.file,
                "specificity": p.specificity,
                "params": {
                    name: {
                        "type": param.param_type,
                        "constraints": param.constraints,
                        "default": param.default,
                    }
                    for name, param in p.params.items()
                },
                "query": {
                    name: {
                        "type": param.param_type,
                        "constraints": param.constraints,
                        "default": param.default,
                    }
                    for name, param in p.query.items()
                },
            }
            for p in patterns
        ],
    }

    output_path.write_text(json.dumps(metadata, indent=2))


def generate_hover_docs() -> Dict[str, str]:
    """Generate hover documentation for pattern syntax."""
    return {
        "<>": "Token parameter: <name:type|constraints=default@transform>",
        "[": "Optional group: [/segment]",
        "]": "End of optional group",
        "*": "Splat (multi-segment capture)",
        ":": "Type annotation",
        "|": "Constraint separator",
        "=": "Default value",
        "@": "Transform function",
        "min=": "Minimum value/length constraint",
        "max=": "Maximum value/length constraint",
        "re=": "Regex pattern constraint",
        "in=": "Enum constraint",
    }


def generate_autocomplete_snippets() -> List[Dict[str, Any]]:
    """Generate autocomplete snippets for VS Code."""
    snippets = [
        {
            "label": "Integer parameter",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:int>",
            "documentation": "Add an integer path parameter",
        },
        {
            "label": "String parameter",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:str>",
            "documentation": "Add a string path parameter",
        },
        {
            "label": "UUID parameter",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:uuid>",
            "documentation": "Add a UUID parameter",
        },
        {
            "label": "Slug parameter",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:slug>",
            "documentation": "Add a slug parameter",
        },
        {
            "label": "Parameter with constraint",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:${2:type}|${3:constraint}>",
            "documentation": "Add a parameter with constraints",
        },
        {
            "label": "Optional parameter with default",
            "kind": CompletionItemKind.Snippet,
            "insertText": "<${1:name}:${2:type}=${3:default}>",
            "documentation": "Add an optional parameter with a default value",
        },
        {
            "label": "optional-group",
            "insertText": "[${1:segments}]",
            "description": "Optional segment group",
        },
        {
            "label": "splat",
            "insertText": "*${1:name}",
            "description": "Multi-segment capture",
        },
        {
            "label": "query-param",
            "insertText": "?${1:name}:${2:type}",
            "description": "Query parameter",
        },
        {
            "label": "constraint-range",
            "insertText": "|min=${1:min}|max=${2:max}",
            "description": "Min/max range constraint",
        },
        {
            "label": "constraint-regex",
            "insertText": "|re=\"${1:pattern}\"",
            "description": "Regex constraint",
        },
        {
            "label": "constraint-enum",
            "insertText": "|in=(${1:val1},${2:val2})",
            "description": "Enum constraint",
        },
    ]

    return snippets


def generate_vscode_extension(output_dir: Path):
    """Generate VS Code extension files for AquilaPatterns."""
    # package.json
    package_json = {
        "name": "aquila-patterns",
        "displayName": "AquilaPatterns",
        "description": "Syntax highlighting and IntelliSense for AquilaPatterns",
        "version": "0.1.0",
        "engines": {"vscode": "^1.60.0"},
        "categories": ["Programming Languages"],
        "contributes": {
            "languages": [
                {
                    "id": "aquila-pattern",
                    "extensions": [".aquila"],
                    "configuration": "./language-configuration.json",
                }
            ],
            "grammars": [
                {
                    "language": "aquila-pattern",
                    "scopeName": "source.aquila",
                    "path": "./syntaxes/aquila.tmLanguage.json",
                }
            ],
            "snippets": [
                {
                    "language": "python",
                    "path": "./snippets/patterns.json",
                }
            ],
        },
    }

    # Write package.json
    (output_dir / "package.json").write_text(json.dumps(package_json, indent=2))

    # Snippets
    snippets = {
        "AquilaPattern Token": {
            "prefix": "aptoken",
            "body": ["<${1:name}:${2:int}>"],
            "description": "AquilaPattern token parameter",
        },
        "AquilaPattern Optional": {
            "prefix": "apopt",
            "body": ["[${1:segment}]"],
            "description": "AquilaPattern optional group",
        },
        "AquilaPattern Splat": {
            "prefix": "apsplat",
            "body": ["*${1:path}"],
            "description": "AquilaPattern splat capture",
        },
    }

    snippets_dir = output_dir / "snippets"
    snippets_dir.mkdir(exist_ok=True)
    (snippets_dir / "patterns.json").write_text(json.dumps(snippets, indent=2))


def generate_diagnostic_codes() -> Dict[str, str]:
    """Generate diagnostic code descriptions for LSP."""
    return {
        "AP001": "Syntax error: Unterminated token",
        "AP002": "Syntax error: Invalid token syntax",
        "AP003": "Syntax error: Unmatched bracket",
        "AP004": "Semantic error: Duplicate parameter name",
        "AP005": "Semantic error: Unknown type",
        "AP006": "Semantic error: Invalid constraint",
        "AP007": "Route ambiguity: Patterns conflict",
        "AP008": "Warning: Optional group with default may mask routes",
    }
