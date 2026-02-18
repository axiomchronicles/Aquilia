"""
Aquilia Schema Snapshot & Diff Engine.

Provides:
- ModelSnapshot: captures the current state of all Model subclasses
- SchemaDiff: computes the difference between two snapshots
- Rename heuristics for detecting renamed models/fields
- DSL operation generation from diffs

The snapshot is a JSON-serializable dict describing every model, field,
index, and constraint in the current codebase.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from .migration_dsl import (
    ColumnDef,
    CreateModel,
    DropModel,
    RenameModel,
    AddField,
    RemoveField,
    AlterField,
    RenameField,
    CreateIndex,
    DropIndex,
    Operation,
    _SENTINEL,
)

logger = logging.getLogger("aquilia.models.schema_snapshot")


# ── Snapshot Format ─────────────────────────────────────────────────────────


SNAPSHOT_VERSION = 1


def create_snapshot(model_classes: list) -> Dict[str, Any]:
    """
    Create a schema snapshot from a list of Model subclasses.

    Returns a JSON-serializable dict with the full schema state.

    Format:
        {
            "version": 1,
            "checksum": "<sha256>",
            "models": {
                "User": {
                    "table": "users",
                    "fields": {
                        "id": {"type": "INTEGER", "primary_key": true, ...},
                        "email": {"type": "VARCHAR(255)", "unique": true, ...},
                    },
                    "indexes": [
                        {"name": "idx_users_email", "columns": ["email"], "unique": false},
                    ],
                    "meta": {
                        "ordering": ["-created_at"],
                        "abstract": false,
                        "managed": true,
                    }
                }
            }
        }
    """
    from .fields_module import (
        Field, ForeignKey, OneToOneField, ManyToManyField,
        AutoField, BigAutoField, IntegerField, BigIntegerField,
        SmallIntegerField, FloatField, DecimalField,
        CharField, TextField, SlugField, EmailField, URLField,
        UUIDField, BooleanField, BinaryField, JSONField,
        DateField, TimeField, DateTimeField, DurationField,
        FileField, ImageField, GenericIPAddressField,
        ArrayField, HStoreField,
    )
    from .fields_module import Index as ModelIndex

    models_data: Dict[str, Any] = {}

    for model_cls in model_classes:
        meta = model_cls._meta
        if meta.abstract:
            continue
        if not meta.managed:
            continue

        name = model_cls.__name__
        table = meta.table_name

        # Serialize fields
        fields_data: Dict[str, Any] = {}
        for field_name, fld in model_cls._fields.items():
            fld_info = _serialize_field(fld)
            fields_data[field_name] = fld_info

        # Serialize indexes from Meta
        indexes_data: List[Dict[str, Any]] = []
        for idx in getattr(meta, "indexes", []):
            if isinstance(idx, ModelIndex):
                idx_fields = list(idx.fields) if hasattr(idx, 'fields') else []
                idx_name = getattr(idx, 'name', None) or _auto_index_name(table, idx_fields)
                indexes_data.append({
                    "name": idx_name,
                    "columns": idx_fields,
                    "unique": getattr(idx, 'unique', False),
                })

        # Add indexes from individual field db_index=True
        for field_name, fld in model_cls._fields.items():
            if getattr(fld, 'db_index', False) and not getattr(fld, 'primary_key', False):
                col_name = getattr(fld, 'column_name', field_name)
                idx_name = _auto_index_name(table, [col_name])
                # Avoid duplicates
                if not any(i["name"] == idx_name for i in indexes_data):
                    indexes_data.append({
                        "name": idx_name,
                        "columns": [col_name],
                        "unique": getattr(fld, 'unique', False),
                    })

        meta_data = {
            "ordering": list(meta.ordering) if meta.ordering else [],
            "abstract": meta.abstract,
            "managed": meta.managed,
        }

        models_data[name] = {
            "table": table,
            "fields": fields_data,
            "indexes": indexes_data,
            "meta": meta_data,
        }

    snapshot = {
        "version": SNAPSHOT_VERSION,
        "models": models_data,
    }
    snapshot["checksum"] = _compute_checksum(snapshot)
    return snapshot


def _serialize_field(fld) -> Dict[str, Any]:
    """Serialize a single Field instance to a snapshot dict."""
    from .fields_module import (
        ForeignKey, OneToOneField, ManyToManyField,
        AutoField, BigAutoField, IntegerField, BigIntegerField,
        SmallIntegerField, FloatField, DecimalField,
        CharField, TextField, SlugField, EmailField, URLField,
        UUIDField, BooleanField, BinaryField, JSONField,
        DateField, TimeField, DateTimeField, DurationField,
        FileField, ImageField,
    )

    info: Dict[str, Any] = {
        "field_class": type(fld).__name__,
    }

    # SQL type
    sql_type = _field_to_sql_type(fld)
    info["type"] = sql_type

    # Constraints
    if getattr(fld, 'primary_key', False):
        info["primary_key"] = True
    if getattr(fld, 'unique', False):
        info["unique"] = True
    if getattr(fld, 'null', False):
        info["nullable"] = True
    if hasattr(fld, 'default') and fld.default is not None:
        from .fields_module import UNSET
        if fld.default is not UNSET:
            try:
                # Only serialize JSON-safe defaults
                json.dumps(fld.default)
                info["default"] = fld.default
            except (TypeError, ValueError):
                if callable(fld.default):
                    info["default"] = f"<callable:{fld.default.__name__}>"
                else:
                    info["default"] = str(fld.default)

    # Max length
    if hasattr(fld, 'max_length') and fld.max_length:
        info["max_length"] = fld.max_length

    # FK reference
    if isinstance(fld, (ForeignKey, OneToOneField)):
        to = fld.to
        if isinstance(to, str):
            info["references"] = {"model": to}
        elif isinstance(to, type):
            info["references"] = {
                "model": to.__name__,
                "table": getattr(to._meta, 'table_name', to.__name__.lower()),
            }
        info["on_delete"] = getattr(fld, 'on_delete_action', 'CASCADE')

    # Decimal params
    if hasattr(fld, 'max_digits') and fld.max_digits:
        info["max_digits"] = fld.max_digits
    if hasattr(fld, 'decimal_places') and fld.decimal_places is not None:
        info["decimal_places"] = fld.decimal_places

    # Column name override
    col = getattr(fld, 'column_name', None) or getattr(fld, 'name', None)
    if col:
        info["column"] = col

    return info


def _field_to_sql_type(fld) -> str:
    """Map a Field instance to its SQL type string."""
    from .fields_module import (
        AutoField, BigAutoField, IntegerField, BigIntegerField,
        SmallIntegerField, FloatField, DecimalField,
        CharField, TextField, SlugField, EmailField, URLField,
        UUIDField, BooleanField, BinaryField, JSONField,
        DateField, TimeField, DateTimeField, DurationField,
        FileField, ImageField, ForeignKey, OneToOneField,
    )

    type_map = {
        AutoField: "INTEGER",
        BigAutoField: "INTEGER",
        IntegerField: "INTEGER",
        BigIntegerField: "INTEGER",
        SmallIntegerField: "INTEGER",
        FloatField: "REAL",
        BooleanField: "INTEGER",
        BinaryField: "BLOB",
        JSONField: "TEXT",
        DateField: "DATE",
        TimeField: "TIME",
        DateTimeField: "TIMESTAMP",
        DurationField: "INTEGER",
        UUIDField: "VARCHAR(36)",
        ForeignKey: "INTEGER",
        OneToOneField: "INTEGER",
    }

    for cls, sql_type in type_map.items():
        if isinstance(fld, cls):
            return sql_type

    if isinstance(fld, (CharField, SlugField, EmailField, URLField, FileField, ImageField)):
        ml = getattr(fld, 'max_length', 255) or 255
        return f"VARCHAR({ml})"

    if isinstance(fld, TextField):
        return "TEXT"

    if isinstance(fld, DecimalField):
        md = getattr(fld, 'max_digits', 10) or 10
        dp = getattr(fld, 'decimal_places', 2) or 2
        return f"DECIMAL({md},{dp})"

    return "TEXT"


def _auto_index_name(table: str, columns: List[str]) -> str:
    """Generate a deterministic index name."""
    cols = "_".join(columns)
    return f"idx_{table}_{cols}"


def _compute_checksum(snapshot: Dict[str, Any]) -> str:
    """Compute a stable checksum of the snapshot (excluding checksum field)."""
    data = {k: v for k, v in snapshot.items() if k != "checksum"}
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def save_snapshot(snapshot: Dict[str, Any], path: Path) -> None:
    """Write snapshot to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, default=str), encoding="utf-8")
    logger.info(f"Schema snapshot saved: {path}")


def load_snapshot(path: Path) -> Optional[Dict[str, Any]]:
    """Load snapshot from JSON file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Failed to load snapshot {path}: {exc}")
        return None


# ── Schema Diff Engine ──────────────────────────────────────────────────────

# Rename detection threshold: similarity ratio above this triggers rename
RENAME_THRESHOLD = 0.6


@dataclass
class SchemaDiff:
    """Result of comparing two snapshots."""

    added_models: List[str] = field(default_factory=list)
    removed_models: List[str] = field(default_factory=list)
    renamed_models: List[Tuple[str, str]] = field(default_factory=list)  # (old, new)
    altered_models: Dict[str, "ModelDiff"] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_models
            or self.removed_models
            or self.renamed_models
            or self.altered_models
        )


@dataclass
class ModelDiff:
    """Changes within a single model."""

    added_fields: List[str] = field(default_factory=list)
    removed_fields: List[str] = field(default_factory=list)
    renamed_fields: List[Tuple[str, str]] = field(default_factory=list)
    altered_fields: List[str] = field(default_factory=list)  # fields with changed type/constraints
    added_indexes: List[Dict[str, Any]] = field(default_factory=list)
    removed_indexes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_fields
            or self.removed_fields
            or self.renamed_fields
            or self.altered_fields
            or self.added_indexes
            or self.removed_indexes
        )


def compute_diff(old_snapshot: Dict[str, Any], new_snapshot: Dict[str, Any]) -> SchemaDiff:
    """
    Compute the diff between two schema snapshots.

    Includes heuristics for detecting renames (models and fields)
    to avoid data-loss migrations.
    """
    old_models = old_snapshot.get("models", {})
    new_models = new_snapshot.get("models", {})

    old_names = set(old_models.keys())
    new_names = set(new_models.keys())

    diff = SchemaDiff()

    # Detect renames vs add/remove
    purely_added = new_names - old_names
    purely_removed = old_names - new_names

    renamed_pairs: List[Tuple[str, str]] = []
    if purely_added and purely_removed:
        renamed_pairs = _detect_model_renames(old_models, new_models, purely_removed, purely_added)
        for old_name, new_name in renamed_pairs:
            purely_removed.discard(old_name)
            purely_added.discard(new_name)

    diff.added_models = sorted(purely_added)
    diff.removed_models = sorted(purely_removed)
    diff.renamed_models = renamed_pairs

    # Diff models that exist in both snapshots (including renamed)
    common_pairs: List[Tuple[str, str]] = []
    for name in old_names & new_names:
        common_pairs.append((name, name))
    for old_name, new_name in renamed_pairs:
        common_pairs.append((old_name, new_name))

    for old_name, new_name in common_pairs:
        model_diff = _diff_model(old_models[old_name], new_models[new_name])
        if model_diff.has_changes:
            diff.altered_models[new_name] = model_diff

    return diff


def _detect_model_renames(
    old_models: Dict, new_models: Dict,
    removed: Set[str], added: Set[str],
) -> List[Tuple[str, str]]:
    """
    Detect likely model renames using table-name and field-structure similarity.

    Heuristics:
    1. Same table name → definite rename
    2. High field-structure similarity → probable rename
    """
    pairs: List[Tuple[str, str]] = []
    used_old: Set[str] = set()
    used_new: Set[str] = set()

    # Pass 1: exact table name match
    for old_name in list(removed):
        old_table = old_models[old_name].get("table", "")
        for new_name in list(added):
            new_table = new_models[new_name].get("table", "")
            if old_table and old_table == new_table:
                pairs.append((old_name, new_name))
                used_old.add(old_name)
                used_new.add(new_name)
                break

    # Pass 2: field similarity
    remaining_old = removed - used_old
    remaining_new = added - used_new
    if remaining_old and remaining_new:
        for old_name in list(remaining_old):
            old_fields = set(old_models[old_name].get("fields", {}).keys())
            best_match = None
            best_score = 0.0

            for new_name in remaining_new:
                new_fields = set(new_models[new_name].get("fields", {}).keys())
                if not old_fields and not new_fields:
                    continue
                # Jaccard similarity
                intersection = old_fields & new_fields
                union = old_fields | new_fields
                score = len(intersection) / len(union) if union else 0
                if score > best_score:
                    best_score = score
                    best_match = new_name

            if best_match and best_score >= RENAME_THRESHOLD:
                pairs.append((old_name, best_match))
                remaining_new.discard(best_match)

    return pairs


def _diff_model(old_model: Dict, new_model: Dict) -> ModelDiff:
    """Diff two model snapshots."""
    diff = ModelDiff()

    old_fields = old_model.get("fields", {})
    new_fields = new_model.get("fields", {})

    old_field_names = set(old_fields.keys())
    new_field_names = set(new_fields.keys())

    # Detect field renames
    added_fields = new_field_names - old_field_names
    removed_fields = old_field_names - new_field_names

    renamed_pairs: List[Tuple[str, str]] = []
    if added_fields and removed_fields:
        renamed_pairs = _detect_field_renames(old_fields, new_fields, removed_fields, added_fields)
        for old_name, new_name in renamed_pairs:
            removed_fields.discard(old_name)
            added_fields.discard(new_name)

    diff.added_fields = sorted(added_fields)
    diff.removed_fields = sorted(removed_fields)
    diff.renamed_fields = renamed_pairs

    # Detect altered fields (common fields with changed properties)
    common = old_field_names & new_field_names
    for name in sorted(common):
        if _field_changed(old_fields[name], new_fields[name]):
            diff.altered_fields.append(name)

    # Diff indexes
    old_indexes = {i["name"]: i for i in old_model.get("indexes", [])}
    new_indexes = {i["name"]: i for i in new_model.get("indexes", [])}

    for name in sorted(set(new_indexes) - set(old_indexes)):
        diff.added_indexes.append(new_indexes[name])
    for name in sorted(set(old_indexes) - set(new_indexes)):
        diff.removed_indexes.append(old_indexes[name])

    return diff


def _detect_field_renames(
    old_fields: Dict, new_fields: Dict,
    removed: Set[str], added: Set[str],
) -> List[Tuple[str, str]]:
    """Detect field renames using type similarity."""
    pairs: List[Tuple[str, str]] = []
    used_new: Set[str] = set()

    for old_name in list(removed):
        old_type = old_fields[old_name].get("type", "")
        best_match = None
        best_score = 0.0

        for new_name in added - used_new:
            new_type = new_fields[new_name].get("type", "")
            # Same type is a strong signal
            score = 1.0 if old_type == new_type else 0.0
            # Name similarity adds signal
            name_sim = SequenceMatcher(None, old_name, new_name).ratio()
            score = (score * 0.7) + (name_sim * 0.3)

            if score > best_score:
                best_score = score
                best_match = new_name

        if best_match and best_score >= RENAME_THRESHOLD:
            pairs.append((old_name, best_match))
            used_new.add(best_match)

    return pairs


def _field_changed(old_field: Dict, new_field: Dict) -> bool:
    """Check if a field's schema-relevant properties changed."""
    keys = ("type", "primary_key", "unique", "nullable", "default", "max_length", "references")
    for k in keys:
        if old_field.get(k) != new_field.get(k):
            return True
    return False


# ── Generate Operations from Diff ───────────────────────────────────────────


def diff_to_operations(
    diff: SchemaDiff,
    old_snapshot: Dict[str, Any],
    new_snapshot: Dict[str, Any],
) -> List[Operation]:
    """
    Convert a SchemaDiff into a list of DSL operations.

    This is the core of makemigrations — it takes the delta between
    the previous snapshot and the current models, then emits the
    minimal set of operations to bring the schema up to date.
    """
    ops: List[Operation] = []
    new_models = new_snapshot.get("models", {})
    old_models = old_snapshot.get("models", {})

    # 1. Renamed models
    for old_name, new_name in diff.renamed_models:
        old_table = old_models[old_name]["table"]
        new_table = new_models[new_name]["table"]
        if old_table != new_table:
            ops.append(RenameModel(
                old_name=old_name, new_name=new_name,
                old_table=old_table, new_table=new_table,
            ))

    # 2. Removed models
    for name in diff.removed_models:
        table = old_models[name]["table"]
        ops.append(DropModel(name=name, table=table))

    # 3. Added models
    for name in diff.added_models:
        model_data = new_models[name]
        fields = _snapshot_fields_to_column_defs(model_data["fields"])
        ops.append(CreateModel(name=name, table=model_data["table"], fields=fields))

        # Add indexes for new models
        for idx in model_data.get("indexes", []):
            ops.append(CreateIndex(
                name=idx["name"],
                table=model_data["table"],
                columns=idx["columns"],
                unique=idx.get("unique", False),
            ))

    # 4. Altered models
    for model_name, model_diff in diff.altered_models.items():
        model_data = new_models[model_name]
        table = model_data["table"]

        # Renamed fields
        for old_fname, new_fname in model_diff.renamed_fields:
            ops.append(RenameField(
                model_name=model_name, table=table,
                old_name=old_fname, new_name=new_fname,
            ))

        # Removed fields
        for fname in model_diff.removed_fields:
            ops.append(RemoveField(model_name=model_name, table=table, column_name=fname))

        # Added fields
        for fname in model_diff.added_fields:
            fld_data = model_data["fields"][fname]
            col = _snapshot_field_to_column_def(fname, fld_data)
            ops.append(AddField(model_name=model_name, table=table, column=col))

        # Altered fields
        for fname in model_diff.altered_fields:
            fld_data = model_data["fields"][fname]
            ops.append(AlterField(
                model_name=model_name, table=table,
                column_name=getattr(fld_data, "get", lambda k, d=None: d)("column", fname),
                new_type=fld_data.get("type"),
            ))

        # Added indexes
        for idx in model_diff.added_indexes:
            ops.append(CreateIndex(
                name=idx["name"], table=table,
                columns=idx["columns"], unique=idx.get("unique", False),
            ))

        # Removed indexes
        for idx in model_diff.removed_indexes:
            ops.append(DropIndex(name=idx["name"], table=table))

    return ops


def _snapshot_fields_to_column_defs(fields_data: Dict[str, Any]) -> List[ColumnDef]:
    """Convert snapshot field dicts to ColumnDef objects."""
    defs: List[ColumnDef] = []
    for name, data in fields_data.items():
        defs.append(_snapshot_field_to_column_def(name, data))
    return defs


def _snapshot_field_to_column_def(name: str, data: Dict[str, Any]) -> ColumnDef:
    """Convert a single snapshot field dict to a ColumnDef."""
    col_name = data.get("column", name)
    col_type = data.get("type", "TEXT")

    ref = data.get("references")
    references = None
    on_delete = "CASCADE"
    on_update = "CASCADE"
    if ref and isinstance(ref, dict) and "table" in ref:
        references = (ref["table"], ref.get("column", "id"))
        on_delete = data.get("on_delete", "CASCADE")
        on_update = data.get("on_update", "CASCADE")

    default = data.get("default", _SENTINEL)
    if default is not None and isinstance(default, str) and default.startswith("<callable:"):
        default = _SENTINEL  # Can't serialize callables

    return ColumnDef(
        name=col_name,
        col_type=col_type,
        primary_key=data.get("primary_key", False),
        autoincrement=data.get("primary_key", False) and "INT" in col_type.upper(),
        unique=data.get("unique", False),
        nullable=data.get("nullable", False),
        default=default,
        references=references,
        on_delete=on_delete,
        on_update=on_update,
    )
