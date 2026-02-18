# Aquilia Migration System

A modern, DSL-driven schema migration system for the Aquilia framework.

## Overview

Aquilia's migration system provides:

- **Declarative DSL** — Express schema changes as composable Python operations
- **Schema snapshot diffing** — Auto-detect model changes with rename detection  
- **Safe startup guard** — Server refuses to boot on stale/missing databases
- **Multi-dialect support** — SQLite, PostgreSQL, MySQL SQL compilation
- **Backward compatibility** — Legacy raw-SQL migrations still work

---

## Quick Start

### 1. Define Models

```python
from aquilia.models import Model, CharField, IntegerField, ForeignKey

class User(Model):
    email = CharField(max_length=255, unique=True)
    name = CharField(max_length=100)
    age = IntegerField(null=True)

    class Meta:
        db_table = "users"
```

### 2. Generate Migration

```bash
aq db makemigrations
# ✓ Generated DSL migration: 20260301_143022_user.py (1 model(s): User)
```

### 3. Apply Migration

```bash
aq db migrate
# ✓ Applied 1 migration(s)
```

---

## CLI Commands

### `aq db makemigrations`

Generate a migration file from current model definitions.

```bash
aq db makemigrations [OPTIONS]

Options:
  --app TEXT           Filter by app name
  --migrations-dir     Migration directory (default: migrations)
  --dsl / --no-dsl     Use DSL format (default: --dsl)
  -v, --verbose        Verbose output
```

**`--dsl` (default):** Uses the new DSL system — snapshots the current schema,
diffs against the previous snapshot, and generates a migration file with
`CreateModel`, `AddField`, `RenameField`, etc.

**`--no-dsl`:** Falls back to the legacy raw-SQL migration generator.

### `aq db migrate`

Apply pending migrations to the database.

```bash
aq db migrate [OPTIONS]

Options:
  --migrations-dir      Migration directory (default: migrations)
  --database-url TEXT   Database URL (default: sqlite:///db.sqlite3)
  --target TEXT         Target revision (for rollback)
  --fake                Mark as applied without executing SQL
  --plan                Preview SQL only (dry-run)
  --database TEXT       Database alias (for multi-db setups)
  -v, --verbose         Verbose output
```

**`--fake`:** Records the migration as applied in the tracking table without
actually executing any SQL. Useful when you've manually applied changes.

**`--plan`:** Shows the SQL that *would* be executed without touching the
database.

### `aq db showmigrations`

List all migrations and their applied status.

```bash
aq db showmigrations [OPTIONS]

Options:
  --migrations-dir      Migration directory
  --database-url TEXT   Database URL to check against
  -v, --verbose         Verbose output
```

Output:
```
  [X] 20260217_210454_order_orderevent_orderitem_and_7_more
  [ ] 20260301_143022_add_user_phone
```

### `aq db sqlmigrate`

Display the compiled SQL for a specific migration.

```bash
aq db sqlmigrate MIGRATION_NAME [OPTIONS]

Options:
  --migrations-dir    Migration directory
  --database TEXT     Database alias
```

---

## Migration DSL Reference

### Column Builders (`C` / `columns`)

```python
from aquilia.models.migration_dsl import columns as C

C.auto("id")                                    # INTEGER PRIMARY KEY AUTOINCREMENT
C.bigauto("id")                                 # BIGINT PRIMARY KEY AUTOINCREMENT
C.varchar("name", 100)                          # VARCHAR(100) NOT NULL
C.varchar("bio", 500, null=True)                # VARCHAR(500)
C.varchar("email", 255, unique=True)            # VARCHAR(255) UNIQUE NOT NULL
C.varchar("role", 20, default="user")           # VARCHAR(20) NOT NULL DEFAULT 'user'
C.text("body")                                  # TEXT NOT NULL
C.integer("count", default=0)                   # INTEGER NOT NULL DEFAULT 0
C.boolean("active", default=True)               # INTEGER NOT NULL DEFAULT 1
C.real("score", default=0.0)                    # REAL NOT NULL DEFAULT 0.0
C.decimal("price", 10, 2)                       # DECIMAL(10,2) NOT NULL
C.timestamp("created_at")                       # TIMESTAMP NOT NULL
C.timestamp("deleted_at", null=True)            # TIMESTAMP
C.date("birthday", null=True)                   # DATE
C.uuid("uuid", unique=True)                     # VARCHAR(36) UNIQUE NOT NULL
C.blob("data", null=True)                       # BLOB
C.foreign_key("user_id", "users", "id")         # INTEGER NOT NULL REFERENCES "users"("id")
C.foreign_key("cat_id", "cats", "id",           # ... ON DELETE SET NULL
              null=True, on_delete="SET NULL")
```

### Operations

#### `CreateModel`

```python
CreateModel(
    name="User",
    table="users",
    fields=[
        C.auto("id"),
        C.varchar("email", 255, unique=True),
        C.varchar("name", 100),
    ],
)
```

#### `DropModel`

```python
DropModel(name="User", table="users")
```

#### `RenameModel`

```python
RenameModel(
    old_name="User", new_name="Account",
    old_table="users", new_table="accounts",
)
```

#### `AddField`

```python
AddField(
    model_name="User",
    table="users",
    field=C.varchar("phone", 20, null=True),
)
```

#### `RemoveField`

```python
RemoveField(model_name="User", table="users", field_name="phone")
```

#### `AlterField`

```python
AlterField(
    model_name="User",
    table="users",
    field_name="email",
    new_field=C.varchar("email", 500, unique=True),
)
```

#### `RenameField`

```python
RenameField(
    model_name="User",
    table="users",
    old_name="email",
    new_name="email_address",
)
```

#### `CreateIndex` / `DropIndex`

```python
CreateIndex("idx_users_email", "users", ["email"])
CreateIndex("idx_users_role_active", "users", ["role", "is_active"], unique=True)
DropIndex("idx_users_email")
```

#### `AddConstraint` / `RemoveConstraint`

```python
AddConstraint(name="chk_positive", table="orders", definition="CHECK (total >= 0)")
RemoveConstraint(name="chk_positive", table="orders")
```

#### `RunSQL`

```python
RunSQL(
    forward="INSERT INTO config (key, value) VALUES ('version', '2');",
    reverse="DELETE FROM config WHERE key = 'version';",
)
```

#### `RunPython`

```python
def populate_defaults(conn):
    # conn is the raw database connection
    ...

RunPython(forward=populate_defaults)
```

### Migration File Structure

```python
"""
Migration: 20260301_143022_create_users
Generated: 2026-03-01T14:30:22+00:00
"""

from aquilia.models.migration_dsl import (
    CreateModel, AddField, CreateIndex, columns as C,
)

class Meta:
    revision = "20260301_143022"
    slug = "create_users"
    models = ["User"]

operations = [
    CreateModel(
        name="User",
        table="users",
        fields=[
            C.auto("id"),
            C.varchar("email", 255, unique=True),
        ],
    ),
    CreateIndex("idx_users_email", "users", ["email"]),
]
```

---

## Safe Startup Behavior

### The Problem

By default, SQLite creates a database file on first connection. This means
a typo in your database URL or a missing migration step silently creates an
empty database — leading to confusing runtime errors.

### The Solution

Aquilia's **startup guard** checks:

1. **Database exists** — the file must already exist (for SQLite)
2. **No pending migrations** — all on-disk migrations must be recorded in
   the `aquilia_migrations` tracking table

If either check fails, the server **refuses to start** and prints a clear
error message:

```
╔══════════════════════════════════════════════════════════╗
║  Database is not ready.                                 ║
║                                                         ║
║  Reason: Database file does not exist: db.sqlite3       ║
║                                                         ║
║  Run `aq db migrate` to apply pending migrations.       ║
║  Or set AQUILIA_AUTO_MIGRATE=1 to auto-apply.           ║
╚══════════════════════════════════════════════════════════╝
```

### Overriding the Guard

Set the environment variable to skip the guard:

```bash
AQUILIA_AUTO_MIGRATE=1 aq run
```

Or in your workspace config:

```python
class Workspace:
    @staticmethod
    def database():
        return {
            "url": "sqlite:///db.sqlite3",
            "auto_migrate": True,
        }
```

### No WAL/SHM Files

The startup guard uses **read-only** SQLite connections (`?mode=ro`) to
probe the database. This prevents creation of WAL (Write-Ahead Logging)
and SHM (Shared Memory) files, which is important for:

- CI/CD pipelines checking migration status
- Docker health checks
- Read-only filesystem environments

---

## Schema Snapshot Format

The snapshot file (`migrations/schema_snapshot.json`) records the full
schema state after the last `makemigrations` run:

```json
{
  "models": {
    "User": {
      "table": "users",
      "fields": {
        "id": {
          "name": "id",
          "type": "INTEGER",
          "primary_key": true,
          "autoincrement": true
        },
        "email": {
          "name": "email",
          "type": "VARCHAR(255)",
          "unique": true
        }
      }
    }
  }
}
```

This file should be **committed to version control**. It enables the
diff algorithm to detect:

- Added/removed models
- Added/removed/changed fields
- Renamed models (Jaccard similarity ≥ 0.6)
- Renamed fields (same type + name similarity)

---

## Tracking Table

Applied migrations are tracked in `aquilia_migrations`:

| Column       | Type      | Description                   |
|-------------|-----------|-------------------------------|
| `revision`  | TEXT (PK) | Revision ID (YYYYMMDD_HHMMSS) |
| `slug`      | TEXT      | Human-readable slug           |
| `checksum`  | TEXT      | SHA-256 of migration file     |
| `applied_at`| TEXT      | ISO 8601 timestamp            |

---

## Multi-Dialect Support

The DSL compiles to dialect-specific SQL:

| Feature           | SQLite       | PostgreSQL    | MySQL           |
|------------------|-------------|---------------|-----------------|
| Auto-increment   | AUTOINCREMENT| SERIAL        | AUTO_INCREMENT  |
| Boolean default  | `DEFAULT 1`  | `DEFAULT TRUE`| `DEFAULT 1`    |
| Text type        | TEXT         | TEXT          | TEXT            |
| UUID             | VARCHAR(36)  | UUID / VARCHAR| VARCHAR(36)     |

---

## Architecture

```
aquilia/models/
├── migration_dsl.py       # DSL primitives (ColumnDef, Operations, Migration)
├── schema_snapshot.py      # Snapshot creation, persistence, diff engine
├── migration_runner.py     # Execute & track migrations
├── migration_gen.py        # Generate migration files from diffs
├── startup_guard.py        # Prevent implicit DB creation
├── base.py                 # ModelRegistry (guarded on_startup)
└── __init__.py             # Public exports
```

### Flow

```
Model classes → create_snapshot() → compute_diff() → diff_to_operations()
    → generate_dsl_migration()  →  migration file written to disk
                                        ↓
                                  MigrationRunner.migrate()
                                        ↓
                              compile_upgrade(dialect) → SQL
                                        ↓
                              execute transactionally
                                        ↓
                              record in aquilia_migrations
```
