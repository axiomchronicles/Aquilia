"""
AMDL Parser — Aquilia Model Definition Language.

Single-pass, line-oriented parser that reads `.amdl` files and produces
a list of `ModelNode` AST nodes.  Designed to be <300 LOC.

Grammar (line patterns):
    ≪ MODEL <Name> ≫             → begin model stanza
    ≪ /MODEL ≫                   → end model stanza
    slot <name> :: <Type> [...]   → field
    link <name> -> KIND Target .. → relationship
    index [f1, f2] unique?        → composite index
    hook <event> -> <handler>     → lifecycle hook
    meta <key> = "<value>"        → metadata
    note "<text>"                 → documentation note
    # ...                         → comment (ignored)
    (blank)                       → ignored
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..faults.domains import AMDLParseFault
from .ast_nodes import (
    AMDLFile,
    FieldType,
    HookNode,
    IndexNode,
    LinkKind,
    LinkNode,
    MetaNode,
    ModelNode,
    NoteNode,
    SlotNode,
)

# ── Whitelisted default expressions ──────────────────────────────────────────
ALLOWED_DEFAULTS = frozenset({"now_utc()", "uuid4()", "seq()"})
ALLOWED_DEFAULT_PATTERN = re.compile(r'^(now_utc\(\)|uuid4\(\)|seq\(\)|env\("[A-Za-z_][A-Za-z0-9_]*"\))$')

# ── Compiled regex patterns ──────────────────────────────────────────────────
RE_MODEL_OPEN = re.compile(r'^\s*≪\s*MODEL\s+([A-Za-z_][A-Za-z0-9_]*)\s*≫\s*$')
RE_MODEL_CLOSE = re.compile(r'^\s*≪\s*/MODEL\s*≫\s*$')

RE_SLOT = re.compile(
    r'^\s*slot\s+([a-z_][a-z0-9_]*)\s*::\s*'
    r'([A-Za-z]+(?:\([^)]*\))?)\s*'
    r'(?:\[([^\]]*)\])?\s*$'
)

RE_LINK = re.compile(
    r'^\s*link\s+([a-z_][a-z0-9_]*)\s*->\s*'
    r'(ONE|MANY|MANY_THROUGH)\s+'
    r'([A-Za-z_][A-Za-z0-9_]*)\s*'
    r'(?:\[([^\]]*)\])?\s*$'
)

RE_INDEX = re.compile(
    r'^\s*index\s+\[([^\]]+)\]\s*(unique)?\s*$'
)

RE_HOOK = re.compile(
    r'^\s*hook\s+([a-z_][a-z0-9_]*)\s*->\s*([a-z_][a-z0-9_]*)\s*$'
)

RE_META = re.compile(
    r'^\s*meta\s+([a-z_][a-z0-9_]*)\s*=\s*"([^"]*)"\s*$'
)

RE_NOTE = re.compile(
    r'^\s*note\s+"([^"]*)"\s*$'
)

# ── Field type mapping ───────────────────────────────────────────────────────
FIELD_TYPE_MAP = {ft.value: ft for ft in FieldType}


class AMDLParseError(AMDLParseFault):
    """
    Raised when AMDL parsing fails.

    Inherits from ``AMDLParseFault`` (which is a ``Fault`` → ``Exception``)
    so it flows through the AquilaFaults pipeline while remaining
    backward-compatible with code that catches ``AMDLParseError``.
    """

    def __init__(self, message: str, file: str = "<unknown>", line: int = 0):
        super().__init__(file=file, line=line, reason=message)


def _parse_type(raw: str) -> Tuple[FieldType, Optional[Tuple[Any, ...]]]:
    """Parse a type token like 'Str', 'Decimal(10,2)', 'Enum(a,b,c)'."""
    paren_idx = raw.find("(")
    if paren_idx == -1:
        name = raw.strip()
        ft = FIELD_TYPE_MAP.get(name)
        if ft is None:
            raise AMDLParseError(f"Unknown field type '{name}'")
        return ft, None

    name = raw[:paren_idx].strip()
    params_raw = raw[paren_idx + 1 : raw.rindex(")")].strip()
    ft = FIELD_TYPE_MAP.get(name)
    if ft is None:
        raise AMDLParseError(f"Unknown field type '{name}'")

    # Parse params
    params = tuple(p.strip() for p in params_raw.split(","))
    # Try to convert numeric params
    converted: list[Any] = []
    for p in params:
        try:
            converted.append(int(p))
        except ValueError:
            converted.append(p)
    return ft, tuple(converted)


def _parse_modifiers(raw: Optional[str]) -> Dict[str, Any]:
    """Parse the modifier list inside square brackets."""
    if not raw or not raw.strip():
        return {}

    mods: Dict[str, Any] = {}
    # Split carefully — handle default:=expr which may contain commas inside parens
    tokens = _split_modifier_tokens(raw.strip())

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # default:=expr
        if token.startswith("default:="):
            expr = token[len("default:="):].strip()
            if not ALLOWED_DEFAULT_PATTERN.match(expr):
                raise AMDLParseError(
                    f"Disallowed default expression '{expr}'. "
                    f"Allowed: now_utc(), uuid4(), seq(), env(\"VAR\")"
                )
            mods["default"] = expr
        # note="..."
        elif token.startswith("note="):
            mods["note"] = token[len("note="):].strip().strip('"')
        # key=value
        elif "=" in token:
            key, val = token.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"')
            try:
                mods[key] = int(val)
            except ValueError:
                mods[key] = val
        # bare flags
        else:
            mods[token] = True

    return mods


def _split_modifier_tokens(raw: str) -> List[str]:
    """Split modifier string by commas, respecting parentheses."""
    tokens: List[str] = []
    depth = 0
    current: list[str] = []
    for ch in raw:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            tokens.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


def parse_amdl(source: str, file_path: str = "<string>") -> AMDLFile:
    """
    Parse AMDL source text into an AMDLFile.

    Args:
        source: Full text of the .amdl file
        file_path: Path for error messages

    Returns:
        AMDLFile with parsed models and any errors
    """
    result = AMDLFile(path=file_path)
    current_model: Optional[ModelNode] = None
    lines = source.splitlines()

    for line_num_0, raw_line in enumerate(lines):
        line_num = line_num_0 + 1
        stripped = raw_line.strip()

        # Skip blanks and comments
        if not stripped or stripped.startswith("#"):
            continue

        # ── MODEL open ───────────────────────────────────────────────
        m = RE_MODEL_OPEN.match(stripped)
        if m:
            if current_model is not None:
                result.errors.append(
                    f"{file_path}:{line_num}: Nested MODEL stanza "
                    f"('{m.group(1)}' inside '{current_model.name}') is not allowed"
                )
                continue
            current_model = ModelNode(
                name=m.group(1),
                source_file=file_path,
                start_line=line_num,
            )
            continue

        # ── MODEL close ──────────────────────────────────────────────
        if RE_MODEL_CLOSE.match(stripped):
            if current_model is None:
                result.errors.append(
                    f"{file_path}:{line_num}: ≪ /MODEL ≫ without matching ≪ MODEL ≫"
                )
                continue
            current_model.end_line = line_num
            result.models.append(current_model)
            current_model = None
            continue

        # Everything below requires being inside a MODEL stanza
        if current_model is None:
            result.errors.append(
                f"{file_path}:{line_num}: Directive outside MODEL stanza: {stripped[:60]}"
            )
            continue

        try:
            _parse_directive(stripped, current_model, file_path, line_num)
        except AMDLParseError as e:
            result.errors.append(str(e))

    # Unclosed model
    if current_model is not None:
        result.errors.append(
            f"{file_path}: Unclosed MODEL stanza '{current_model.name}' "
            f"(opened at line {current_model.start_line})"
        )

    return result


def _parse_directive(
    line: str,
    model: ModelNode,
    file_path: str,
    line_num: int,
) -> None:
    """Parse a single directive line inside a MODEL stanza."""

    # ── slot ─────────────────────────────────────────────────────────
    m = RE_SLOT.match(line)
    if m:
        name = m.group(1)
        ft, type_params = _parse_type(m.group(2))
        mods = _parse_modifiers(m.group(3))

        slot = SlotNode(
            name=name,
            field_type=ft,
            type_params=type_params,
            modifiers=mods,
            is_pk=mods.pop("PK", False) is True,
            is_unique=mods.pop("unique", False) is True,
            is_nullable=mods.pop("nullable", False) is True,
            max_length=mods.pop("max", None),
            default_expr=mods.pop("default", None),
            note=mods.pop("note", None),
            line_number=line_num,
            source_file=file_path,
        )

        # Auto type implies PK
        if ft == FieldType.AUTO:
            slot.is_pk = True

        model.slots.append(slot)
        return

    # ── link ─────────────────────────────────────────────────────────
    m = RE_LINK.match(line)
    if m:
        name = m.group(1)
        kind_str = m.group(2)
        target = m.group(3)
        mods = _parse_modifiers(m.group(4))

        kind = LinkKind(kind_str)
        link = LinkNode(
            name=name,
            kind=kind,
            target_model=target,
            fk_field=mods.pop("fk", None),
            back_name=mods.pop("back", None),
            through_model=mods.pop("through", None),
            modifiers=mods,
            line_number=line_num,
            source_file=file_path,
        )
        model.links.append(link)
        return

    # ── index ────────────────────────────────────────────────────────
    m = RE_INDEX.match(line)
    if m:
        fields_raw = m.group(1)
        is_unique = m.group(2) is not None
        fields = [f.strip() for f in fields_raw.split(",")]
        idx = IndexNode(
            fields=fields,
            is_unique=is_unique,
            line_number=line_num,
            source_file=file_path,
        )
        model.indexes.append(idx)
        return

    # ── hook ─────────────────────────────────────────────────────────
    m = RE_HOOK.match(line)
    if m:
        hook = HookNode(
            event=m.group(1),
            handler_name=m.group(2),
            line_number=line_num,
            source_file=file_path,
        )
        model.hooks.append(hook)
        return

    # ── meta ─────────────────────────────────────────────────────────
    m = RE_META.match(line)
    if m:
        model.meta[m.group(1)] = m.group(2)
        return

    # ── note ─────────────────────────────────────────────────────────
    m = RE_NOTE.match(line)
    if m:
        model.notes.append(m.group(1))
        return

    # Unknown directive
    raise AMDLParseError(
        f"Unrecognized directive: {line[:80]}",
        file=file_path,
        line=line_num,
    )


def parse_amdl_file(path: str | Path) -> AMDLFile:
    """
    Parse an `.amdl` file from disk.

    Args:
        path: Path to the .amdl file

    Returns:
        AMDLFile with parsed models

    Raises:
        FileNotFoundError: If file does not exist
        AMDLParseError: If file has fatal parse errors
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"AMDL file not found: {p}")
    source = p.read_text(encoding="utf-8")
    result = parse_amdl(source, str(p))
    if result.errors:
        raise AMDLParseError(
            f"Found {len(result.errors)} error(s) in {p}:\n"
            + "\n".join(f"  • {e}" for e in result.errors)
        )
    return result


def parse_amdl_directory(directory: str | Path) -> List[AMDLFile]:
    """
    Parse all `.amdl` files in a directory (non-recursive).

    Args:
        directory: Path to scan for .amdl files

    Returns:
        List of AMDLFile results
    """
    d = Path(directory)
    if not d.is_dir():
        return []
    files: List[AMDLFile] = []
    for amdl_path in sorted(d.glob("*.amdl")):
        files.append(parse_amdl_file(amdl_path))
    return files
