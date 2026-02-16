"""Aquilia CLI — UI utilities (re-exports from colors module)."""

from .colors import (  # noqa: F401
    # Basic output
    success,
    error,
    warning,
    info,
    dim,
    bold,
    accent,
    # Structural
    banner,
    section,
    rule,
    kv,
    badge,
    tree_item,
    bullet,
    step,
    indent_echo,
    table,
    panel,
    # File-operation helpers
    file_written,
    file_skipped,
    file_dry,
    next_steps,
)
