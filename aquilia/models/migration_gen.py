"""
Aquilia Migration File Generator — creates DSL migration files.

Generates human-readable Python-DSL migration files from schema diffs.
This replaces the old raw-SQL migration generator.
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from .migration_dsl import (
    ColumnDef,
    CreateModel,
    CreateIndex,
    DropModel,
    RenameModel,
    AddField,
    RemoveField,
    AlterField,
    RenameField,
    DropIndex,
    RunSQL,
    Operation,
    _SENTINEL,
)
from .schema_snapshot import (
    create_snapshot,
    save_snapshot,
    load_snapshot,
    compute_diff,
    diff_to_operations,
    SchemaDiff,
)

logger = logging.getLogger("aquilia.models.migration_gen")


def _generate_revision() -> str:
    """Generate a timestamp-based revision ID."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S")


def _slugify(name: str) -> str:
    """Convert model name to a migration slug."""
    return re.sub(r"[^a-z0-9]+", name.lower(), "_").strip("_")


def generate_dsl_migration(
    model_classes: list,
    migrations_dir: str | Path,
    snapshot_path: Optional[str | Path] = None,
    slug: Optional[str] = None,
) -> Optional[Path]:
    """
    Generate a DSL migration file from the diff between the current
    snapshot and the current model definitions.

    Steps:
    1. Load the previous snapshot (or start from empty)
    2. Create a new snapshot from current model classes
    3. Compute the diff
    4. Generate DSL operations from the diff
    5. Write the migration file
    6. Save the new snapshot

    Args:
        model_classes: List of Model subclass classes
        migrations_dir: Directory to write migration file
        snapshot_path: Path to schema_snapshot.json (default: migrations_dir/schema_snapshot.json)
        slug: Optional slug for filename

    Returns:
        Path to generated migration file, or None if no changes detected.
    """
    mdir = Path(migrations_dir)
    mdir.mkdir(parents=True, exist_ok=True)

    snap_path = Path(snapshot_path) if snapshot_path else mdir / "schema_snapshot.json"

    # Load old snapshot
    old_snapshot = load_snapshot(snap_path) or {"version": 1, "models": {}, "checksum": ""}

    # Create new snapshot
    new_snapshot = create_snapshot(model_classes)

    # Compute diff
    diff = compute_diff(old_snapshot, new_snapshot)

    if not diff.has_changes:
        logger.info("No model changes detected")
        return None

    # Generate operations from diff
    operations = diff_to_operations(diff, old_snapshot, new_snapshot)

    if not operations:
        logger.info("No operations generated from diff")
        return None

    # Build revision and slug
    rev = _generate_revision()
    model_names = _affected_model_names(diff)

    if not slug:
        if len(model_names) <= 3:
            slug = "_".join(n.lower() for n in model_names)
        else:
            slug = "_".join(n.lower() for n in model_names[:3])
            slug += f"_and_{len(model_names) - 3}_more"

    # Generate file content
    content = _render_migration_file(rev, slug, model_names, operations)

    filename = f"{rev}_{slug}.py"
    filepath = mdir / filename
    filepath.write_text(content, encoding="utf-8")

    # Save new snapshot
    save_snapshot(new_snapshot, snap_path)

    logger.info(f"Generated DSL migration: {filepath}")
    return filepath


def _affected_model_names(diff: SchemaDiff) -> List[str]:
    """Get all model names affected by a diff."""
    names: List[str] = []
    names.extend(diff.added_models)
    names.extend(diff.removed_models)
    for old, new in diff.renamed_models:
        names.append(new)
    names.extend(diff.altered_models.keys())
    return sorted(set(names))


def _render_migration_file(
    revision: str,
    slug: str,
    model_names: List[str],
    operations: List[Operation],
) -> str:
    """Render a DSL migration file as Python source."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    models_str = ", ".join(model_names)

    # Build imports
    op_types = set(type(op).__name__ for op in operations)
    imports = sorted(op_types)
    imports_line = ", ".join(imports)

    lines = [
        '"""',
        f"Migration: {revision}_{slug}",
        f"Generated: {now}",
        f"Models: {models_str}",
        '"""',
        "",
        "from aquilia.models.migration_dsl import (",
        f"    {imports_line},",
        "    columns as C,",
        ")",
        "",
        "",
        "class Meta:",
        f'    revision = "{revision}"',
        f'    slug = "{slug}"',
        f"    models = {model_names!r}",
        "",
        "",
    ]

    # Render operations list
    lines.append("operations = [")
    for op in operations:
        lines.append(_render_operation(op))
    lines.append("]")
    lines.append("")

    return "\n".join(lines)


def _render_operation(op: Operation) -> str:
    """Render a single Operation as Python source."""
    if isinstance(op, CreateModel):
        field_lines = []
        for f in op.fields:
            field_lines.append(f"            {_render_column_def(f)},")
        fields_str = "\n".join(field_lines)
        return (
            f"    CreateModel(\n"
            f"        name={op.name!r},\n"
            f"        table={op.table!r},\n"
            f"        fields=[\n"
            f"{fields_str}\n"
            f"        ],\n"
            f"    ),"
        )
    elif isinstance(op, DropModel):
        return f"    DropModel(name={op.name!r}, table={op.table!r}),"
    elif isinstance(op, RenameModel):
        return (
            f"    RenameModel(\n"
            f"        old_name={op.old_name!r}, new_name={op.new_name!r},\n"
            f"        old_table={op.old_table!r}, new_table={op.new_table!r},\n"
            f"    ),"
        )
    elif isinstance(op, AddField):
        return (
            f"    AddField(\n"
            f"        model_name={op.model_name!r}, table={op.table!r},\n"
            f"        column={_render_column_def(op.column)},\n"
            f"    ),"
        )
    elif isinstance(op, RemoveField):
        return f"    RemoveField(model_name={op.model_name!r}, table={op.table!r}, column_name={op.column_name!r}),"
    elif isinstance(op, AlterField):
        return (
            f"    AlterField(\n"
            f"        model_name={op.model_name!r}, table={op.table!r},\n"
            f"        column_name={op.column_name!r}, new_type={op.new_type!r},\n"
            f"    ),"
        )
    elif isinstance(op, RenameField):
        return (
            f"    RenameField(\n"
            f"        model_name={op.model_name!r}, table={op.table!r},\n"
            f"        old_name={op.old_name!r}, new_name={op.new_name!r},\n"
            f"    ),"
        )
    elif isinstance(op, CreateIndex):
        return (
            f"    CreateIndex(\n"
            f"        name={op.name!r}, table={op.table!r},\n"
            f"        columns={op.columns!r}, unique={op.unique!r},\n"
            f"    ),"
        )
    elif isinstance(op, DropIndex):
        return f"    DropIndex(name={op.name!r}),"
    elif isinstance(op, RunSQL):
        return f"    RunSQL(sql={op.sql!r}),"
    else:
        return f"    # Unknown operation: {op.describe()}"


def _render_column_def(col: ColumnDef) -> str:
    """Render a ColumnDef as a C.xxx() call."""
    if col.primary_key and col.autoincrement:
        return f'C.auto("{col.name}")'

    # Determine builder method
    t = col.col_type.upper()
    kwargs: List[str] = []

    if col.nullable:
        kwargs.append("null=True")
    if col.unique:
        kwargs.append("unique=True")
    if col.default is not _SENTINEL:
        kwargs.append(f"default={col.default!r}")

    kwargs_str = ", ".join(kwargs)

    if col.references:
        ref_table, ref_col = col.references
        parts = [f'"{col.name}"', f'"{ref_table}"', f'"{ref_col}"']
        if col.nullable:
            parts.append("null=True")
        if col.on_delete != "CASCADE":
            parts.append(f'on_delete="{col.on_delete}"')
        if col.on_update != "CASCADE":
            parts.append(f'on_update="{col.on_update}"')
        return f"C.foreign_key({', '.join(parts)})"

    if "VARCHAR" in t:
        import re
        m = re.search(r'\((\d+)\)', t)
        length = m.group(1) if m else "255"
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.varchar("{col.name}", {length}{extra})'
    elif t == "TEXT":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.text("{col.name}"{extra})'
    elif t == "INTEGER":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.integer("{col.name}"{extra})'
    elif "DECIMAL" in t:
        import re
        m = re.search(r'\((\d+),\s*(\d+)\)', t)
        if m:
            extra = f", {kwargs_str}" if kwargs_str else ""
            return f'C.decimal("{col.name}", {m.group(1)}, {m.group(2)}{extra})'
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.decimal("{col.name}"{extra})'
    elif t == "TIMESTAMP":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.timestamp("{col.name}"{extra})'
    elif t == "REAL":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.real("{col.name}"{extra})'
    elif t == "BLOB":
        return f'C.blob("{col.name}")'
    elif t == "DATE":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.date("{col.name}"{extra})'
    elif t == "TIME":
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.time("{col.name}"{extra})'
    elif t in ("VARCHAR(36)",) or "UUID" in t:
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.uuid("{col.name}"{extra})'
    else:
        extra = f", {kwargs_str}" if kwargs_str else ""
        return f'C.text("{col.name}"{extra})'
