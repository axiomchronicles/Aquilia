"""
Aquilia Model System — AMDL-based, async-first models.

Public API:
    - AMDL parser: parse_amdl, parse_amdl_file, parse_amdl_directory
    - AST nodes: ModelNode, SlotNode, LinkNode, etc.
    - Runtime: ModelProxy, Q, ModelRegistry
    - Migrations: MigrationRunner, MigrationOps, op, generate_migration_file
    - Database: AquiliaDatabase (re-exported from aquilia.db)
    - Faults: ModelNotFoundFault, QueryFault, etc. (re-exported from aquilia.faults)
"""

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
    ModelRegistry,
    Q,
    generate_create_table_sql,
    generate_create_index_sql,
)

from .migrations import (
    MigrationOps,
    MigrationRunner,
    MigrationInfo,
    generate_migration_file,
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
    # AST
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
    # Parser
    "AMDLParseError",
    "parse_amdl",
    "parse_amdl_file",
    "parse_amdl_directory",
    # Runtime
    "ModelProxy",
    "ModelRegistry",
    "Q",
    "generate_create_table_sql",
    "generate_create_index_sql",
    # Migrations
    "MigrationOps",
    "MigrationRunner",
    "MigrationInfo",
    "generate_migration_file",
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
