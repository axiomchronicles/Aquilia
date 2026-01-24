"""LSP support package."""

from .metadata import (
    generate_lsp_metadata,
    generate_hover_docs,
    generate_autocomplete_snippets,
    generate_vscode_extension,
    generate_diagnostic_codes,
)

__all__ = [
    "generate_lsp_metadata",
    "generate_hover_docs",
    "generate_autocomplete_snippets",
    "generate_vscode_extension",
    "generate_diagnostic_codes",
]
