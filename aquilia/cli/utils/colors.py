"""
Aquilia CLI — UI toolkit.

Provides a rich set of styled output primitives built on Click:

    Output helpers:
        success(), error(), warning(), info(), dim(), bold()

    Structural elements:
        banner()        — branded header with box drawing
        section()       — section divider with title
        rule()          — thin horizontal rule
        kv()            — key-value pair, aligned
        badge()         — inline status badge  [OK]  [FAIL]  [SKIP]
        tree_item()     — indented tree node
        table()         — minimal aligned table
        panel()         — bordered panel/box

    Progress:
        step()          — numbered step indicator
        bullet()        — bulleted list item
        indent()        — echo with indentation

All output respects terminal width and degrades gracefully on
non-colour terminals (click.style handles NO_COLOR / TERM=dumb).
"""

from __future__ import annotations

import os
import shutil
from typing import Optional, Sequence

import click

# ═══════════════════════════════════════════════════════════════════════════
# Terminal helpers
# ═══════════════════════════════════════════════════════════════════════════

_TERM_WIDTH: Optional[int] = None


def _tw() -> int:
    """Terminal width, cached and clamped to a sane range."""
    global _TERM_WIDTH
    if _TERM_WIDTH is None:
        _TERM_WIDTH = max(40, min(shutil.get_terminal_size((80, 24)).columns, 120))
    return _TERM_WIDTH


# ═══════════════════════════════════════════════════════════════════════════
# Basic styled output  (backward-compatible API)
# ═══════════════════════════════════════════════════════════════════════════


def success(message: str) -> None:
    """Print success message in green."""
    click.echo(click.style(message, fg="green"))


def error(message: str) -> None:
    """Print error message in red."""
    click.echo(click.style(message, fg="red"))


def warning(message: str) -> None:
    """Print warning message in yellow."""
    click.echo(click.style(message, fg="yellow"))


def info(message: str) -> None:
    """Print info message in cyan."""
    click.echo(click.style(message, fg="cyan"))


def dim(message: str) -> None:
    """Print dimmed message."""
    click.echo(click.style(message, dim=True))


def bold(message: str) -> str:
    """Return bold-styled text (does not echo)."""
    return click.style(message, bold=True)


def accent(message: str) -> str:
    """Return magenta-accented text (does not echo)."""
    return click.style(message, fg="magenta")


# ═══════════════════════════════════════════════════════════════════════════
# Box-drawing characters
# ═══════════════════════════════════════════════════════════════════════════

# Heavy box set
_H_TL = "\u250f"   # ┏
_H_TR = "\u2513"   # ┓
_H_BL = "\u2517"   # ┗
_H_BR = "\u251b"   # ┛
_H_H  = "\u2501"   # ━
_H_V  = "\u2503"   # ┃

# Light box set
_L_TL = "\u250c"   # ┌
_L_TR = "\u2510"   # ┐
_L_BL = "\u2514"   # └
_L_BR = "\u2518"   # ┘
_L_H  = "\u2500"   # ─
_L_V  = "\u2502"   # │

# Tee / cross
_L_LT = "\u251c"   # ├
_L_RT = "\u2524"   # ┤

# Other
_BULLET = "\u2022"     # •
_ARROW  = "\u2192"     # →
_CHECK  = "\u2713"     # ✓
_CROSS  = "\u2717"     # ✗
_CIRCLE = "\u25cb"     # ○
_DOT    = "\u00b7"     # ·
_DASH   = "\u2500"     # ─


# ═══════════════════════════════════════════════════════════════════════════
# Banner
# ═══════════════════════════════════════════════════════════════════════════


def banner(
    title: str = "Aquilia",
    subtitle: str = "",
    *,
    width: Optional[int] = None,
    fg: str = "cyan",
) -> None:
    """
    Print a bordered banner with centred title.

        ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃                     Aquilia                         ┃
        ┃           Manifest-driven web framework             ┃
        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """
    w = width or min(_tw(), 60)
    inner = w - 2
    top = f"{_H_TL}{_H_H * inner}{_H_TR}"
    bot = f"{_H_BL}{_H_H * inner}{_H_BR}"
    title_line = f"{_H_V}{title.center(inner)}{_H_V}"

    click.echo(click.style(top, fg=fg))
    click.echo(click.style(title_line, fg=fg, bold=True))
    if subtitle:
        sub_line = f"{_H_V}{subtitle.center(inner)}{_H_V}"
        click.echo(click.style(sub_line, fg=fg))
    click.echo(click.style(bot, fg=fg))


# ═══════════════════════════════════════════════════════════════════════════
# Section / Rule
# ═══════════════════════════════════════════════════════════════════════════


def section(title: str, *, width: Optional[int] = None, fg: str = "cyan") -> None:
    """
    Print a section header with a ruled line.

        ── Docker ─────────────────────────────────
    """
    w = width or _tw()
    pad = 2
    dashes = w - len(title) - pad - 4  # 4 = leading "── " + trailing " ─…"
    if dashes < 4:
        dashes = 4
    line = f"{_L_H}{_L_H} {title} {_L_H * dashes}"
    click.echo(click.style(line, fg=fg, bold=True))


def rule(*, char: str = _L_H, width: Optional[int] = None, fg: str = "white") -> None:
    """Print a thin horizontal rule."""
    w = width or _tw()
    click.echo(click.style(char * w, fg=fg, dim=True))


# ═══════════════════════════════════════════════════════════════════════════
# Key / Value
# ═══════════════════════════════════════════════════════════════════════════


def kv(
    key: str,
    value: str,
    *,
    key_width: int = 20,
    indent: int = 2,
    key_fg: str = "white",
    val_fg: str = "cyan",
) -> None:
    """
    Print an aligned key-value pair.

        Modules:          8
        DB driver:        postgres
    """
    prefix = " " * indent
    k = click.style(f"{key}:", fg=key_fg)
    v = click.style(str(value), fg=val_fg)
    padding = " " * max(1, key_width - len(key) - 1)
    click.echo(f"{prefix}{k}{padding}{v}")


# ═══════════════════════════════════════════════════════════════════════════
# Badges / Status indicators
# ═══════════════════════════════════════════════════════════════════════════


def badge(label: str, *, style: str = "ok") -> str:
    """
    Return an inline badge string (not echoed).

        [OK]  [FAIL]  [SKIP]  [WARN]
    """
    colours = {
        "ok":   ("green",  f" {_CHECK} "),
        "fail": ("red",    f" {_CROSS} "),
        "skip": ("yellow", f" {_CIRCLE} "),
        "warn": ("yellow", f" ! "),
        "info": ("cyan",   f" {_DOT} "),
    }
    fg, icon = colours.get(style, ("white", f" {_DOT} "))
    return click.style(f"[{icon}{label}]", fg=fg)


# ═══════════════════════════════════════════════════════════════════════════
# Tree / Lists
# ═══════════════════════════════════════════════════════════════════════════


def tree_item(
    text: str,
    *,
    last: bool = False,
    depth: int = 0,
    fg: str = "white",
) -> None:
    """
    Print an indented tree node.

        ├── controllers.py
        └── services.py
    """
    indent_str = f"{'    ' * depth}"
    connector = f"{_L_BL}{_L_H}{_L_H} " if last else f"{_L_LT}{_L_H}{_L_H} "
    click.echo(
        click.style(indent_str, dim=True)
        + click.style(connector, dim=True)
        + click.style(text, fg=fg)
    )


def bullet(text: str, *, indent: int = 2, fg: str = "white") -> None:
    """Print a bulleted list item."""
    prefix = " " * indent
    click.echo(f"{prefix}{click.style(_BULLET, fg='cyan')} {click.style(text, fg=fg)}")


def step(number: int, text: str, *, fg: str = "cyan") -> None:
    """
    Print a numbered step.

        [1] cp .env.example .env
        [2] docker compose up -d
    """
    num = click.style(f"[{number}]", fg=fg, bold=True)
    click.echo(f"  {num} {text}")


def indent_echo(text: str, *, level: int = 1) -> None:
    """Echo text with indentation (2 spaces per level)."""
    click.echo(f"{'  ' * level}{text}")


# ═══════════════════════════════════════════════════════════════════════════
# Table
# ═══════════════════════════════════════════════════════════════════════════


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    col_widths: Optional[Sequence[int]] = None,
    header_fg: str = "cyan",
    row_fg: str = "white",
    indent: int = 2,
) -> None:
    """
    Print a minimal aligned table.

        Module              Version       Route
        ─────────────────── ──────────── ─────────────────
        users               1.0.0         /users
        products            0.5.0         /products
    """
    prefix = " " * indent
    ncols = len(headers)

    # Auto-compute column widths if not given
    if col_widths is None:
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < ncols:
                    widths[i] = max(widths[i], len(str(cell)))
        # add padding
        widths = [w + 2 for w in widths]
    else:
        widths = list(col_widths)

    # Header
    hdr = ""
    for i, h in enumerate(headers):
        hdr += h.ljust(widths[i])
    click.echo(f"{prefix}{click.style(hdr, fg=header_fg, bold=True)}")

    # Separator
    sep = ""
    for w in widths:
        sep += _L_H * w
    click.echo(f"{prefix}{click.style(sep, dim=True)}")

    # Rows
    for row in rows:
        line = ""
        for i, cell in enumerate(row):
            cell_str = str(cell)
            if i < len(widths):
                line += cell_str.ljust(widths[i])
            else:
                line += cell_str
        click.echo(f"{prefix}{click.style(line, fg=row_fg)}")


# ═══════════════════════════════════════════════════════════════════════════
# Panel / Box
# ═══════════════════════════════════════════════════════════════════════════


def panel(
    lines: Sequence[str],
    *,
    title: str = "",
    width: Optional[int] = None,
    fg: str = "cyan",
    pad: int = 1,
) -> None:
    """
    Print a bordered panel.

        ┌─ Next steps ─────────────────────────────┐
        │  1. cp .env.example .env                  │
        │  2. docker compose up -d                  │
        └───────────────────────────────────────────┘
    """
    w = width or min(_tw(), 60)
    inner = w - 2 - (pad * 2)

    # Top border
    if title:
        tbar = f"{_L_TL}{_L_H} {title} {_L_H * (inner - len(title) - 1)}{_L_H * (pad * 2 - 1)}{_L_TR}"
    else:
        tbar = f"{_L_TL}{_L_H * (w - 2)}{_L_TR}"
    click.echo(click.style(tbar, fg=fg))

    # Content lines
    sp = " " * pad
    for line in lines:
        # Truncate if too long
        truncated = line[:inner] if len(line) > inner else line
        padded = truncated.ljust(inner)
        click.echo(
            click.style(f"{_L_V}{sp}", fg=fg)
            + padded
            + click.style(f"{sp}{_L_V}", fg=fg)
        )

    # Bottom border
    bbar = f"{_L_BL}{_L_H * (w - 2)}{_L_BR}"
    click.echo(click.style(bbar, fg=fg))


# ═══════════════════════════════════════════════════════════════════════════
# Compound helpers (used across commands)
# ═══════════════════════════════════════════════════════════════════════════


def file_written(label: str, *, verbose: bool = False, path: str = "") -> None:
    """Announce a generated file."""
    mark = click.style(f"  {_CHECK}", fg="green")
    name = click.style(label, fg="white")
    click.echo(f"{mark} {name}")
    if verbose and path:
        dim(f"    {_ARROW} {path}")


def file_skipped(label: str, reason: str = "exists") -> None:
    """Announce a skipped file."""
    mark = click.style(f"  {_CIRCLE}", fg="yellow")
    name = click.style(label, fg="white", dim=True)
    hint = click.style(f"({reason})", dim=True)
    click.echo(f"{mark} {name} {hint}")


def file_dry(label: str) -> None:
    """Announce a dry-run file."""
    mark = click.style(f"  {_DOT}", fg="cyan")
    name = click.style(label, fg="white")
    tag = click.style("dry-run", fg="cyan", dim=True)
    click.echo(f"{mark} {name}  {tag}")


def next_steps(steps_list: Sequence[str], *, title: str = "Next steps") -> None:
    """Print a numbered next-steps panel."""
    content = [f"{i}. {s}" for i, s in enumerate(steps_list, 1)]
    panel(content, title=title)
