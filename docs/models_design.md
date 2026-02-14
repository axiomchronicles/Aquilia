# Aquilia Model System — Design Document

> **Version**: 1.0.0  
> **Status**: Implementation Phase  
> **Date**: 2026-02-14  

---

## 1. Overview

The Aquilia Model System introduces **AMDL (Aquilia Model Definition Language)**, a stanza-based, line-oriented DSL for declaring database models. AMDL is parsed at build/startup time, producing an AST that drives:

- Runtime model proxy generation (`ModelProxy` classes with `$`-prefixed async API)
- Migration generation and execution
- DI/lifecycle integration (database connections registered in Aquilia's `Container`)
- CLI commands (`aq makemigrations`, `aq migrate`, `aq model dump`, `aq shell`)

### Design Principles

1. **Async-first**: All data access is `await`-based.  
2. **SQLite-by-default**: Zero-config for development; Postgres/MySQL planned.  
3. **Unique syntax**: AMDL uses `slot`, `link`, `hook`, `meta`, `note` — no resemblance to Django/SQLAlchemy ORM.  
4. **Safe defaults**: Only whitelisted expressions (`now_utc()`, `uuid4()`, `env("VAR")`, `seq()`) in AMDL defaults.  
5. **DI-native**: Database engine and model proxies registered in Aquilia's DI container.  
6. **CLI-first UX**: Migrations are driven by `aq` commands, not runtime magic.

---

## 2. AMDL Specification

### 2.1 File Format

- Extension: `.amdl`
- Encoding: UTF-8
- Line-oriented; indentation is cosmetic
- Comments: lines starting with `#` are ignored

### 2.2 Stanza Structure

```
≪ MODEL <ModelName> ≫
  <directives...>
≪ /MODEL ≫
```

### 2.3 Directives

| Directive | Syntax | Purpose |
|-----------|--------|---------|
| `slot` | `slot <name> :: <Type> [opts...]` | Define a column/field |
| `link` | `link <name> -> ONE\|MANY <Target> [opts...]` | Define a relationship |
| `index` | `index [<f1>, <f2>] unique?` | Composite index |
| `hook` | `hook <lifecycle_event> -> <hook_name>` | Lifecycle hook binding |
| `meta` | `meta <key> = "<value>"` | Model metadata |
| `note` | `note "<text>"` | Documentation annotation |

### 2.4 Field Types

| AMDL Type | SQL (SQLite) | SQL (Postgres) | Python |
|-----------|-------------|----------------|--------|
| `Auto` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL` | `int` |
| `Int` | `INTEGER` | `INTEGER` | `int` |
| `BigInt` | `INTEGER` | `BIGINT` | `int` |
| `Str` | `VARCHAR(N)` | `VARCHAR(N)` | `str` |
| `Text` | `TEXT` | `TEXT` | `str` |
| `Bool` | `BOOLEAN` | `BOOLEAN` | `bool` |
| `Float` | `REAL` | `DOUBLE PRECISION` | `float` |
| `Decimal(p,s)` | `DECIMAL(p,s)` | `NUMERIC(p,s)` | `Decimal` |
| `JSON` | `TEXT` | `JSONB` | `dict` |
| `Bytes` | `BLOB` | `BYTEA` | `bytes` |
| `DateTime` | `TIMESTAMP` | `TIMESTAMPTZ` | `datetime` |
| `Date` | `DATE` | `DATE` | `date` |
| `Time` | `TIME` | `TIME` | `time` |
| `UUID` | `VARCHAR(36)` | `UUID` | `uuid.UUID` |

### 2.5 Slot Modifiers

Inside `[...]`: `PK`, `unique`, `nullable`, `max=N`, `default:=<expr>`, `note="..."`

### 2.6 Allowed Default Expressions

| Expression | Result |
|-----------|--------|
| `now_utc()` | `datetime.utcnow()` / SQL `CURRENT_TIMESTAMP` |
| `uuid4()` | `uuid.uuid4()` |
| `env("VAR")` | `os.environ["VAR"]` |
| `seq()` | Auto-increment (migration serial) |

No arbitrary Python is allowed.

---

## 3. Runtime API

### 3.1 ModelProxy

Generated from AMDL AST. All model operations use `$`-prefix.

```python
# Create
user = await User.$create({"username": "pawan", "email": "p@example.com"})

# Get by PK
user = await User.$get(pk=1)

# Query
rows = await User.$query().where("is_active = :a", a=True).order("-id").limit(10).all()

# Update
await User.$update(filters={"username": "old"}, values={"is_active": False})

# Delete
await User.$delete(filters={"id": 5})

# Relationship access
profile = await user.$link("profile")
posts = await user.$link_many("posts")
```

### 3.2 Q (Query) Object

Chainable, async-terminal:

```python
q = User.$query()
q = q.where("age > :min_age", min_age=18)
q = q.order("-created_at")
q = q.limit(20).offset(40)
rows = await q.all()         # List[User]
one = await q.one()           # User or raises
count = await q.count()       # int
await q.update({"role": "admin"})
await q.delete()
```

### 3.3 Transaction API

```python
from aquilia.db import get_database

db = get_database()
async with db.transaction():
    await User.$create({...})
    await Post.$create({...})
```

---

## 4. Migration System

### 4.1 `aq makemigrations`

1. Parse all `.amdl` files from configured model directories
2. Compute fingerprint (hash of AST)
3. Diff against last migration state
4. Emit migration script under `migrations/<timestamp>_<slug>.py`

### 4.2 Migration Script Format

```python
from aquilia.models.migrations import op

def upgrade(conn):
    op.create_table("aq_user", [
        op.pk("id"),
        op.varchar("username", 150, unique=True),
        op.varchar("email", 255, nullable=True),
        op.blob("password_hash"),
        op.timestamp("created_at", default="CURRENT_TIMESTAMP"),
    ])

def downgrade(conn):
    op.drop_table("aq_user")
```

### 4.3 `aq migrate`

- Reads `aquilia_migrations` tracking table
- Applies pending migrations in timestamp order
- Supports `--to <rev>` for rollback

---

## 5. DI / Lifecycle Integration

### 5.1 Database Provider

At startup, `AquiliaServer` calls `register_database()` which:

1. Reads `database` config from `ConfigLoader` (URL, pool settings)
2. Creates `AquiliaDatabase` (wraps `aiosqlite` / SA Core)
3. Registers as `ValueProvider` in all DI containers

### 5.2 Model Registry

`ModelRegistry` is a singleton that holds all parsed AMDL models and their runtime proxies. Registered in DI as `aquilia.models.ModelRegistry`.

### 5.3 Lifecycle Hooks

- **startup**: Connect database, register models, run pending migrations (if auto-migrate enabled)
- **shutdown**: Close database connections

---

## 6. Security

- AMDL `default:=` expressions are parsed by a whitelist evaluator — no `eval()` or `exec()`
- SQL queries use parameterized statements exclusively
- Migration scripts are generated code reviewed by developers
- Connection strings can reference `env("VAR")` — never hardcoded secrets

---

## 7. Performance Notes

- SQLite: single writer, WAL mode enabled by default
- Connection pooling via `aiosqlite` with configurable pool size
- Model proxies are thin wrappers — no ORM overhead
- Query objects build SQL strings; no lazy loading magic

---

## 8. File Map

### New Files

| Path | Purpose |
|------|---------|
| `aquilia/models/__init__.py` | Model system public API |
| `aquilia/models/parser.py` | AMDL parser → AST |
| `aquilia/models/ast_nodes.py` | AST node dataclasses |
| `aquilia/models/runtime.py` | ModelProxy + Q + ModelRegistry |
| `aquilia/models/migrations.py` | Migration ops + runner |
| `aquilia/db/__init__.py` | Database public API |
| `aquilia/db/engine.py` | AquiliaDatabase async engine |
| `aquilia/cli/commands/model_cmds.py` | CLI: makemigrations, migrate, model dump, shell |
| `examples/blog/models.amdl` | Example AMDL file |
| `tests/test_models_parser.py` | Parser tests |
| `tests/test_models_runtime.py` | Runtime proxy tests |
| `tests/test_models_migrations.py` | Migration tests |
| `tests/test_db_integration.py` | End-to-end DB tests |
| `docs/models_design.md` | This document |

### Modified Files

| Path | Change |
|------|--------|
| `aquilia/__init__.py` | Export model system symbols |
| `aquilia/cli/__main__.py` | Register model CLI commands |
| `aquilia/cli/commands/__init__.py` | Add model_cmds import |
| `pyproject.toml` | Add `aiosqlite` dependency |
| `requirements-dev.txt` | Add `aiosqlite` |

---

## 9. Future Work (Planned)

- **Postgres driver**: `asyncpg` + full dialect
- **MySQL driver**: `aiomysql` + dialect
- **AMDL IDE support**: VS Code extension for `.amdl` syntax highlighting
- **Model validation**: AMDL `!validator` directives
- **Seeding**: `aq seed` command for test data
- **Schema introspection**: Reverse-engineer `.amdl` from existing DB
