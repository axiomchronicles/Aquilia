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

from .manager import Manager, BaseManager, QuerySet

# New split-module exports (available but not replacing base.py)
from .registry import ModelRegistry as NewModelRegistry
from .query import Q as QueryBuilder, QNode, QCombination
from .options import Options as EnhancedOptions

from .fields_module import (
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

# New sub-module exports
from .fields import (
    NullableMixin,
    UniqueMixin,
    IndexedMixin,
    AutoNowMixin,
    ChoiceMixin,
    EncryptedMixin,
    CompositeField,
    CompositePrimaryKey,
    CompositeAttribute,
    EnumField,
)

# ── Expression / Aggregate system ────────────────────────────────────────────

from .expression import (
    Expression,
    F,
    Value,
    RawSQL,
    Col,
    Star,
    CombinedExpression,
    When,
    Case,
    Subquery,
    Exists,
    OuterRef,
    ExpressionWrapper,
    Func,
    Cast,
    Coalesce,
    Greatest,
    Least,
    NullIf,
)

from .aggregate import (
    Aggregate,
    Sum,
    Avg,
    Count,
    Max,
    Min,
    StdDev,
    Variance,
    ArrayAgg,
    StringAgg,
    GroupConcat,
    BoolAnd,
    BoolOr,
)

# ── Signals ──────────────────────────────────────────────────────────────────

from .signals import (
    Signal,
    pre_save,
    post_save,
    pre_delete,
    post_delete,
    pre_init,
    post_init,
    m2m_changed,
    receiver,
    class_prepared,
    pre_migrate,
    post_migrate,
)

# ── Transactions ─────────────────────────────────────────────────────────────

from .transactions import atomic, Atomic, TransactionManager

# ── Deletion constants ───────────────────────────────────────────────────────

from .deletion import (
    CASCADE,
    SET_NULL,
    PROTECT,
    SET_DEFAULT,
    DO_NOTHING,
    RESTRICT,
    OnDeleteHandler,
    SET,
    ProtectedError,
    RestrictedError,
)

# ── Enums / Choices ──────────────────────────────────────────────────────────

from .enums import Choices, TextChoices, IntegerChoices

# ── SQL Builder ──────────────────────────────────────────────────────────────

from .sql_builder import SQLBuilder, InsertBuilder, UpdateBuilder, DeleteBuilder, CreateTableBuilder

# ── Constraints & Indexes ────────────────────────────────────────────────────

from .constraint import CheckConstraint, ExclusionConstraint, Deferrable

from .index import (
    GinIndex,
    GistIndex,
    BrinIndex,
    HashIndex,
    FunctionalIndex,
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
    # New split modules
    "NewModelRegistry",
    "QueryBuilder",
    "QNode",
    "QCombination",
    "EnhancedOptions",
    # Manager
    "Manager",
    "BaseManager",
    "QuerySet",
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
    # Field mixins & composites
    "NullableMixin",
    "UniqueMixin",
    "IndexedMixin",
    "AutoNowMixin",
    "ChoiceMixin",
    "EncryptedMixin",
    "CompositeField",
    "CompositePrimaryKey",
    "CompositeAttribute",
    "EnumField",
    # Expressions & Aggregates
    "Expression",
    "F",
    "Value",
    "RawSQL",
    "Col",
    "Star",
    "CombinedExpression",
    "When",
    "Case",
    "Subquery",
    "Exists",
    "OuterRef",
    "ExpressionWrapper",
    "Func",
    "Cast",
    "Coalesce",
    "Greatest",
    "Least",
    "NullIf",
    "Aggregate",
    "Sum",
    "Avg",
    "Count",
    "Max",
    "Min",
    "StdDev",
    "Variance",
    "ArrayAgg",
    "StringAgg",
    "GroupConcat",
    "BoolAnd",
    "BoolOr",
    # Signals
    "Signal",
    "pre_save",
    "post_save",
    "pre_delete",
    "post_delete",
    "pre_init",
    "post_init",
    "m2m_changed",
    "receiver",
    "class_prepared",
    "pre_migrate",
    "post_migrate",
    # Transactions
    "atomic",
    "Atomic",
    "TransactionManager",
    # Deletion
    "CASCADE",
    "SET_NULL",
    "PROTECT",
    "SET_DEFAULT",
    "DO_NOTHING",
    "RESTRICT",
    "OnDeleteHandler",
    "SET",
    "ProtectedError",
    "RestrictedError",
    # Enums / Choices
    "Choices",
    "TextChoices",
    "IntegerChoices",
    # SQL Builder
    "SQLBuilder",
    "InsertBuilder",
    "UpdateBuilder",
    "DeleteBuilder",
    "CreateTableBuilder",
    # Constraints & Indexes
    "CheckConstraint",
    "ExclusionConstraint",
    "Deferrable",
    "GinIndex",
    "GistIndex",
    "BrinIndex",
    "HashIndex",
    "FunctionalIndex",
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
