"""
AquilaMail ATS (Aquilia Template Syntax) — Stub module.

This module provides the public API for rendering ATS mail templates.
The full lexer/parser/compiler is implemented in PR2; this stub provides
simple placeholder replacement so that the rest of the mail pipeline can
be developed and tested end-to-end.

ATS Syntax (stub supports expressions only):
    << expr >>           — expression interpolation
    [[% if cond %]]      — control flow (PR2)
    [[% for x in xs %]]  — loops (PR2)
    [[% block name %]]   — template inheritance (PR2)

Filters (PR2):
    << name | title >>
    << price | currency("USD") >>
    << bio | truncate(120) >>
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..faults import MailTemplateFault

# ── Stub expression regex ───────────────────────────────────────────

# Matches << expr >> (the stub expression delimiter)
_EXPR_RE = re.compile(r"<<\s*(.+?)\s*>>")

# ── Template search paths (set via MailConfig or default) ───────────

_template_dirs: List[Path] = []


def configure(template_dirs: Optional[List[str]] = None) -> None:
    """Set template search directories (called at MailService startup)."""
    global _template_dirs
    if template_dirs:
        _template_dirs = [Path(d) for d in template_dirs]


# ── Rendering helpers ───────────────────────────────────────────────


def _resolve_dotted(name: str, context: Dict[str, Any]) -> Any:
    """
    Resolve a dotted name against a context dict.

    Example:
        _resolve_dotted("user.name", {"user": {"name": "Asha"}})
        → "Asha"
    """
    parts = name.strip().split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return ""  # undefined → empty string
            current = current[part]
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return ""
    return current


def _substitute(match: re.Match, context: Dict[str, Any]) -> str:
    """Replace a single << expr >> match."""
    expr = match.group(1).strip()

    # Handle filter syntax: << expr | filter >>  (stub: ignore filter)
    if "|" in expr:
        expr = expr.split("|")[0].strip()

    value = _resolve_dotted(expr, context)
    if value is None:
        return ""
    return str(value)


# ── Public API ──────────────────────────────────────────────────────


def render_string(template_text: str, context: Dict[str, Any]) -> str:
    """
    Render an ATS template string with the given context.

    This is the stub implementation that handles ``<< expr >>`` expressions.
    Control-flow tags (``[[% ... %]]``) are passed through as-is until PR2.

    Args:
        template_text: ATS template source text.
        context: Variables to interpolate.

    Returns:
        Rendered string.
    """
    return _EXPR_RE.sub(lambda m: _substitute(m, context), template_text)


def render_template(
    template_name: str,
    context: Dict[str, Any],
    *,
    template_dirs: Optional[List[str]] = None,
) -> str:
    """
    Render a named ATS template file with the given context.

    Searches ``_template_dirs`` (configured via ``MailConfig.template.dirs``)
    for the template file, reads it, and calls ``render_string``.

    Args:
        template_name: Template filename (e.g. ``"welcome.aqt"``).
        context: Variables for interpolation.
        template_dirs: Override search directories (optional).

    Returns:
        Rendered HTML/text.

    Raises:
        MailTemplateFault: If the template file cannot be found.
    """
    dirs = (
        [Path(d) for d in template_dirs]
        if template_dirs
        else _template_dirs
    )

    # Search for the template
    for d in dirs:
        candidate = d / template_name
        if candidate.is_file():
            source = candidate.read_text(encoding="utf-8")
            return render_string(source, context)

    # Not found in configured dirs — try template_name as absolute/relative path
    p = Path(template_name)
    if p.is_file():
        source = p.read_text(encoding="utf-8")
        return render_string(source, context)

    searched = ", ".join(str(d) for d in dirs) if dirs else "(no dirs configured)"
    raise MailTemplateFault(
        f"Template '{template_name}' not found.  Searched: {searched}",
        template_name=template_name,
    )
