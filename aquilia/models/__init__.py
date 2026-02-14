"""
Aquilia Model System — Pure Python, Django-grade ORM.

The model system has been completely rewritten from the old AMDL DSL
to a pure Pythonic, metaclass-driven architecture.

Usage:
    from aquilia.models import Model
    from aquilia.models.fields import (
        CharField, IntegerField, DateTimeField, ForeignKey, ManyToManyField,
    )

    class User(Model):
        table = "users"

        name = CharField(max_length=150)
        email = EmailField(unique=True)
        active = BooleanField(default=True)
        created_at = DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-created_at"]

Public API:
    - Model: Base class for all models
    - Fields: All field types (Char, Integer, DateTime, FK, M2M, etc.)
    - Q: Query builder
    - ModelRegistry: Global model registry
    - Migrations: MigrationRunner, MigrationOps, generate_migration_file
    - Database: AquiliaDatabase (re-exported from aquilia.db)
    - Faults: ModelNotFoundFault, QueryFault, etc.
"""

# ── New Pure Python Model System ─────────────────────────────────────────────

from .base import (
    Model,
    ModelMeta,
    ModelRegistry,
    Options,
    Q,
)

from .fields import (
    # Base
    Field,
    FieldValidationError,
    Index,
    UniqueConstraint,
    UNSET,
    # Numeric
    AutoField,
    BigAutoField,
    IntegerField,
    BigIntegerField,
    SmallIntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    FloatField,
    DecimalField,
    # Text
    CharField,
    TextField,
    SlugField,
    EmailField,
    URLField,
    UUIDField,
    FilePathField,
    # Date/Time
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    # Boolean
    BooleanField,
    # Binary/Special
    BinaryField,
    JSONField,
    # Relationships
    ForeignKey,
    OneToOneField,
    ManyToManyField,
    RelationField,
    # IP/Network
    GenericIPAddressField,
    InetAddressField,
    # File/Media
    FileField,
    ImageField,
    # PostgreSQL
    ArrayField,
    HStoreField,
    RangeField,
    IntegerRangeField,
    BigIntegerRangeField,
    DecimalRangeField,
    DateRangeField,
    DateTimeRangeField,
    CICharField,
    CIEmailField,
    CITextField,
    # Meta/Special
    GeneratedField,
    OrderWrt,
)

# ── Legacy AMDL compatibility layer ─────────────────────────────────────────
# These are preserved for backward compatibility with existing code that
# imports AMDL types. They still function but are deprecated.

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

from .parser import (
    AMDLParseError,
    parse_amdl,
    parse_amdl_file,
    parse_amdl_directory,
)

from .runtime import (
    ModelProxy,
    ModelRegistry as LegacyModelRegistry,
    Q as LegacyQ,
    generate_create_table_sql,
    generate_create_index_sql,
)

from .migrations import (
    MigrationOps,
    MigrationRunner,
    MigrationInfo,
    generate_migration_file,
    generate_migration_from_models,
    op,
)

# Re-export model-specific faults for convenience
from ..faults.domains import (
    ModelFault,
    AMDLParseFault,
    ModelNotFoundFault,
    ModelRegistrationFault,
    MigrationFault,
    MigrationConflictFault,
    QueryFault,
    DatabaseConnectionFault,
    SchemaFault,
)

__all__ = [
    # ── New Pure Python Model System ─────────────────────────────────
    "Model",
    "ModelMeta",
    "ModelRegistry",
    "Options",
    "Q",
    # Fields
    "Field",
    "FieldValidationError",
    "Index",
    "UniqueConstraint",
    "UNSET",
    "AutoField",
    "BigAutoField",
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "FloatField",
    "DecimalField",
    "CharField",
    "TextField",
    "SlugField",
    "EmailField",
    "URLField",
    "UUIDField",
    "FilePathField",
    "DateField",
    "TimeField",
    "DateTimeField",
    "DurationField",
    "BooleanField",
    "BinaryField",
    "JSONField",
    "ForeignKey",
    "OneToOneField",
    "ManyToManyField",
    "RelationField",
    "GenericIPAddressField",
    "InetAddressField",
    "FileField",
    "ImageField",
    "ArrayField",
    "HStoreField",
    "RangeField",
    "IntegerRangeField",
    "BigIntegerRangeField",
    "DecimalRangeField",
    "DateRangeField",
    "DateTimeRangeField",
    "CICharField",
    "CIEmailField",
    "CITextField",
    "GeneratedField",
    "OrderWrt",
    # ── Legacy AMDL (backward compat) ────────────────────────────────
    "AMDLFile",
    "FieldType",
    "HookNode",
    "IndexNode",
    "LinkKind",
    "LinkNode",
    "MetaNode",
    "ModelNode",
    "NoteNode",
    "SlotNode",
    "AMDLParseError",
    "parse_amdl",
    "parse_amdl_file",
    "parse_amdl_directory",
    "ModelProxy",
    "LegacyModelRegistry",
    "LegacyQ",
    "generate_create_table_sql",
    "generate_create_index_sql",
    # Migrations
    "MigrationOps",
    "MigrationRunner",
    "MigrationInfo",
    "generate_migration_file",
    "generate_migration_from_models",
    "op",
    # Faults (re-exported)
    "ModelFault",
    "AMDLParseFault",
    "ModelNotFoundFault",
    "ModelRegistrationFault",
    "MigrationFault",
    "MigrationConflictFault",
    "QueryFault",
    "DatabaseConnectionFault",
    "SchemaFault",
]
