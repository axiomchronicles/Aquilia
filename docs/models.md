# Aquilia Models & DB — Architecture & Usage Guide

## Overview

The Aquilia ORM is a **pure Python, async-first, metaclass-driven** model system that provides Django-grade ORM capabilities while staying idiomatic to Aquilia's architecture (DI, Faults, Lifecycle hooks).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Defining Models](#defining-models)
3. [Field Types](#field-types)
4. [Field Mixins & Composites](#field-mixins--composites)
5. [Queries](#queries)
6. [Expressions & Aggregates](#expressions--aggregates)
7. [Managers](#managers)
8. [Relationships](#relationships)
9. [Signals](#signals)
10. [Transactions](#transactions)
11. [Enums & Choices](#enums--choices)
12. [Constraints & Indexes](#constraints--indexes)
13. [Deletion Behavior](#deletion-behavior)
14. [Database Backends](#database-backends)
15. [Migrations](#migrations)
16. [SQL Builder (Advanced)](#sql-builder)
17. [CLI Commands](#cli-commands)
18. [Upgrade Guide](#upgrade-guide)

---

## Quick Start

```python
from aquilia.models import Model, CharField, IntegerField, DateTimeField, Manager
from aquilia.db import AquiliaDatabase, configure_database

# 1. Configure database
db = configure_database("sqlite:///app.db")

# 2. Define models
class User(Model):
    table = "users"

    name = CharField(max_length=150)
    email = CharField(max_length=255, unique=True)
    age = IntegerField(null=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

# 3. Create tables
await db.connect()
await ModelRegistry.create_tables(db)

# 4. CRUD
user = await User.create(name="Alice", email="alice@example.com", age=30)
user = await User.get(pk=1)
users = await User.objects.filter(age__gte=18).order("-name").all()
await user.delete_instance()
```

---

## Defining Models

Models are Python classes that subclass `Model`. Fields are declared as class attributes.

```python
from aquilia.models import (
    Model, CharField, IntegerField, BooleanField,
    DateTimeField, ForeignKey, ManyToManyField, Index,
)

class Article(Model):
    table = "articles"

    title = CharField(max_length=200)
    body = TextField()
    published = BooleanField(default=False)
    views = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    author = ForeignKey("User", related_name="articles")
    tags = ManyToManyField("Tag", related_name="articles")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["title", "published"]),
        ]
        constraints = []
        verbose_name = "Article"
```

### Meta Options

| Option | Description |
|--------|-------------|
| `table` / `table_name` | Database table name (defaults to lowercased class name) |
| `ordering` | Default ORDER BY (prefix `-` for DESC) |
| `indexes` | List of `Index` objects |
| `constraints` | List of `UniqueConstraint`, `CheckConstraint`, etc. |
| `abstract` | If `True`, no table created, fields inherited by subclasses |
| `unique_together` | Legacy: list of field tuples that must be unique together |
| `verbose_name` | Human-readable name |
| `app_label` | Owning module name |

---

## Field Types

### Core Fields

| Field | SQL Type | Key Parameters |
|-------|----------|----------------|
| `AutoField` | INTEGER PK AUTOINCREMENT | — |
| `BigAutoField` | INTEGER PK AUTOINCREMENT | — |
| `IntegerField` | INTEGER | `min_value`, `max_value` |
| `BigIntegerField` | BIGINT | — |
| `SmallIntegerField` | SMALLINT | — |
| `PositiveIntegerField` | INTEGER CHECK(≥0) | — |
| `FloatField` | REAL | — |
| `DecimalField` | DECIMAL(p,s) | `max_digits`, `decimal_places` |
| `CharField` | VARCHAR(n) | `max_length` (required) |
| `TextField` | TEXT | — |
| `SlugField` | VARCHAR(50) | `max_length` |
| `EmailField` | VARCHAR(254) | validates email format |
| `URLField` | VARCHAR(200) | validates URL |
| `UUIDField` | CHAR(36) | `auto=True` for auto-gen |
| `BooleanField` | BOOLEAN | — |
| `DateField` | DATE | `auto_now`, `auto_now_add` |
| `TimeField` | TIME | `auto_now`, `auto_now_add` |
| `DateTimeField` | TIMESTAMP | `auto_now`, `auto_now_add` |
| `DurationField` | REAL (seconds) | — |
| `BinaryField` | BLOB | — |
| `JSONField` | TEXT/JSON | — |
| `FileField` | VARCHAR(255) | `upload_to` |
| `ImageField` | VARCHAR(255) | `upload_to` |

### Relationship Fields

| Field | Description |
|-------|-------------|
| `ForeignKey(to, on_delete=..., related_name=...)` | Many-to-one |
| `OneToOneField(to, on_delete=..., related_name=...)` | One-to-one |
| `ManyToManyField(to, related_name=..., through=...)` | Many-to-many junction |

### Common Field Options

| Option | Default | Description |
|--------|---------|-------------|
| `null` | `False` | Allow NULL in database |
| `blank` | `False` | Allow empty in validation |
| `default` | UNSET | Default value or callable |
| `unique` | `False` | UNIQUE constraint |
| `db_index` | `False` | Create index on column |
| `primary_key` | `False` | PRIMARY KEY |
| `choices` | `None` | List of (value, label) tuples |
| `validators` | `[]` | List of validator callables |
| `column_name` | field name | Override database column name |
| `help_text` | `""` | Documentation string |

---

## Field Mixins & Composites

### Mixins

Create reusable field variants by composing mixins:

```python
from aquilia.models.fields import NullableMixin, UniqueMixin, IndexedMixin, EncryptedMixin
from aquilia.models import CharField

class NullableUniqueEmail(NullableMixin, UniqueMixin, CharField):
    pass

email = NullableUniqueEmail(max_length=255)
# → null=True, blank=True, unique=True
```

Available mixins:
- **NullableMixin** — sets `null=True, blank=True`
- **UniqueMixin** — sets `unique=True`
- **IndexedMixin** — sets `db_index=True`
- **AutoNowMixin** — sets `auto_now=True`
- **ChoiceMixin** — adds `get_display()`, `choice_values`
- **EncryptedMixin** — base64 placeholder (configure with `configure_encryption()`)

### EnumField

```python
from aquilia.models.fields import EnumField
import enum

class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

class Product(Model):
    color = EnumField(enum_class=Color)
```

### CompositeField

Groups multiple fields into one logical attribute:

```python
from aquilia.models.fields import CompositeField
from aquilia.models import FloatField

class Location(Model):
    coords = CompositeField(
        schema={"lat": FloatField(), "lng": FloatField()},
        strategy="json",  # or "expand"
    )
```

### CompositePrimaryKey

```python
from aquilia.models.fields import CompositePrimaryKey

class OrderItem(Model):
    class Meta:
        primary_key = CompositePrimaryKey(fields=["order_id", "product_id"])
```

---

## Queries

### Query Builder (Q)

```python
# Basic queries
users = await User.query().filter(active=True).all()
user  = await User.query().filter(email="alice@test.com").first()
count = await User.query().filter(age__gte=18).count()

# Django-style lookups
users = await User.query().filter(
    name__startswith="A",
    age__gte=18,
    age__lte=65,
).order("-created_at").limit(10).all()

# Raw WHERE
users = await User.query().where("age > ? AND active = ?", 18, True).all()

# Exclude
users = await User.query().exclude(active=False).all()

# Values (dict output)
emails = await User.query().values("email", "name")

# Values list (flat)
emails = await User.query().values_list("email", flat=True)

# Distinct
unique = await User.query().distinct().values("department")

# Update / Delete
await User.query().filter(active=False).update(active=True)
await User.query().filter(age__lt=0).delete()
```

### Lookup Operators

| Lookup | SQL | Example |
|--------|-----|---------|
| `field` | `= ?` | `filter(name="Alice")` |
| `field__gt` | `> ?` | `filter(age__gt=18)` |
| `field__gte` | `>= ?` | `filter(age__gte=18)` |
| `field__lt` | `< ?` | `filter(age__lt=65)` |
| `field__lte` | `<= ?` | `filter(age__lte=65)` |
| `field__ne` | `!= ?` | `filter(status__ne="deleted")` |
| `field__in` | `IN (?, ?)` | `filter(id__in=[1,2,3])` |
| `field__contains` | `LIKE %?%` | `filter(name__contains="ali")` |
| `field__startswith` | `LIKE ?%` | `filter(name__startswith="A")` |
| `field__endswith` | `LIKE %?` | `filter(email__endswith=".com")` |
| `field__ilike` | `LOWER() LIKE LOWER()` | `filter(name__ilike="alice")` |
| `field__isnull` | `IS NULL` / `IS NOT NULL` | `filter(bio__isnull=True)` |

---

## Expressions & Aggregates

### F() Expressions

Reference database columns in queries:

```python
from aquilia.models import F, Value

# Field reference in update
await Product.query().update({"price": F("price") * 1.1})

# Arithmetic
expr = F("price") * F("quantity") - F("discount")
```

### Aggregates

```python
from aquilia.models import Sum, Avg, Count, Max, Min

result = await Order.query().aggregate(
    total=Sum("amount"),
    avg_amount=Avg("amount"),
    count=Count("id"),
    max_amount=Max("amount"),
)
# result == {"total": 1500, "avg_amount": 150.0, "count": 10, "max_amount": 500}
```

### Annotate

```python
from aquilia.models import Count

# Annotate each result with computed values
users = await User.query().annotate(
    post_count=Count("id")
).group_by("id").all()
```

---

## Managers

Every model automatically gets a `Manager` instance as `objects`:

```python
users = await User.objects.filter(active=True).all()
user  = await User.objects.get(pk=1)
count = await User.objects.count()
```

### Custom Managers

```python
from aquilia.models import Manager

class PublishedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status="published")

class Article(Model):
    table = "articles"
    title = CharField(max_length=200)
    status = CharField(max_length=20, default="draft")

    objects = Manager()           # default
    published = PublishedManager()  # pre-filtered

# Usage
articles = await Article.published.all()
```

---

## Relationships

```python
# Forward FK
author = await post.related("author")

# Reverse FK (via related_name)
posts = await user.related("posts")

# M2M
tags = await post.related("tags")

# Attach / Detach M2M
await post.attach("tags", tag1, tag2)
await post.detach("tags", tag1)
```

---

## Signals

Signals fire during model lifecycle events:

```python
from aquilia.models import pre_save, post_save, pre_delete, post_delete

@pre_save.connect
async def on_pre_save(sender, instance, created, **kwargs):
    if created:
        print(f"About to create {sender.__name__}")

@post_save.connect
async def on_post_save(sender, instance, created, **kwargs):
    if created:
        print(f"Created {instance}")

@pre_delete.connect
async def on_pre_delete(sender, instance, **kwargs):
    print(f"About to delete {instance}")

@post_delete.connect
async def on_post_delete(sender, instance, **kwargs):
    print(f"Deleted {instance}")
```

Available signals:
- `pre_init` / `post_init` — during `__init__`
- `pre_save` / `post_save` — during `create()`, `save()`
- `pre_delete` / `post_delete` — during `delete_instance()`
- `m2m_changed` — M2M modifications

---

## Transactions

```python
from aquilia.models import atomic

async with atomic(db):
    user = await User.create(name="Alice")
    await Profile.create(user_id=user.id, bio="Hello")
    # Auto-commits on success, rolls back on exception
```

Nested savepoints:

```python
async with atomic(db):
    await User.create(name="Alice")
    async with atomic(db):  # creates SAVEPOINT
        await User.create(name="Bob")
        raise Exception("oops")  # rolls back to savepoint
    # Alice is still saved
```

---

## Enums & Choices

```python
from aquilia.models import TextChoices, IntegerChoices

class Status(TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"

class Priority(IntegerChoices):
    LOW = 0, "Low"
    MEDIUM = 1, "Medium"
    HIGH = 2, "High"

# Usage
Status.choices    # [("draft", "Draft"), ("published", "Published"), ...]
Status.values     # ["draft", "published", "archived"]
Status.labels     # ["Draft", "Published", "Archived"]
Status.DRAFT.label  # "Draft"

class Article(Model):
    status = CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
```

---

## Constraints & Indexes

### CheckConstraint

```python
from aquilia.models import CheckConstraint

class Product(Model):
    price = DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            CheckConstraint(check="price > 0", name="positive_price"),
        ]
```

### ExclusionConstraint (PostgreSQL)

```python
from aquilia.models import ExclusionConstraint

class Reservation(Model):
    class Meta:
        constraints = [
            ExclusionConstraint(
                name="no_overlapping",
                expressions=[("room_id", "="), ("during", "&&")],
                index_type="GIST",
            ),
        ]
```

### Advanced Indexes

```python
from aquilia.models import GinIndex, GistIndex, BrinIndex, HashIndex, FunctionalIndex

class Article(Model):
    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"], name="idx_search_gin"),
            FunctionalIndex(
                expression='LOWER("email")',
                name="idx_email_lower",
            ),
        ]
```

---

## Deletion Behavior

```python
from aquilia.models import ForeignKey, CASCADE, SET_NULL, PROTECT, RESTRICT

class Comment(Model):
    post = ForeignKey("Post", on_delete=CASCADE)       # delete with parent
    author = ForeignKey("User", on_delete=SET_NULL, null=True)  # set to NULL
    editor = ForeignKey("User", on_delete=PROTECT)     # prevent deletion
```

Constants: `CASCADE`, `SET_NULL`, `PROTECT`, `SET_DEFAULT`, `DO_NOTHING`, `RESTRICT`

---

## Database Backends

### SQLite (Default)

```python
from aquilia.db import configure_database
db = configure_database("sqlite:///app.db")
```

### PostgreSQL

```python
from aquilia.db import PostgresAdapter
adapter = PostgresAdapter()
await adapter.connect("postgresql://user:pass@localhost/dbname")
```

Requires: `pip install asyncpg`

### MySQL

```python
from aquilia.db import MySQLAdapter
adapter = MySQLAdapter()
await adapter.connect("mysql://user:pass@localhost/dbname")
```

Requires: `pip install aiomysql`

### Backend Capabilities

```python
adapter.capabilities.supports_returning    # True for PostgreSQL
adapter.capabilities.supports_json_type    # True for PG & MySQL
adapter.capabilities.supports_arrays       # True for PG only
adapter.capabilities.param_style           # "qmark" / "numeric" / "format"
```

---

## SQL Builder

For advanced SQL generation:

```python
from aquilia.models import SQLBuilder, InsertBuilder, UpdateBuilder, DeleteBuilder

# SELECT
sql, params = (
    SQLBuilder()
    .from_table("users")
    .select("name", "email")
    .where("active = ?", True)
    .order_by('"name" ASC')
    .limit(10)
    .build()
)

# INSERT
sql, params = (
    InsertBuilder("users")
    .from_dict({"name": "Alice", "email": "alice@test.com"})
    .build()
)

# UPDATE
sql, params = (
    UpdateBuilder("users")
    .set(active=False)
    .where("id = ?", 1)
    .build()
)

# DELETE
sql, params = (
    DeleteBuilder("users")
    .where("id = ?", 1)
    .build()
)
```

---

## CLI Commands

```bash
# Generate migrations
aq model makemigrations

# Apply migrations
aq model migrate

# Dump model schema
aq model dump

# Interactive model shell
aq model shell
```

---

## Upgrade Guide

### From AMDL to Pure Python Models

The old AMDL DSL-based model system is **fully preserved** for backward compatibility. All AMDL types (`ModelProxy`, `LegacyModelRegistry`, `parse_amdl`, etc.) remain importable from `aquilia.models`.

To migrate to pure Python models:

1. Replace `.amdl` files with Python model classes
2. Change `from aquilia.models import ModelProxy` → `from aquilia.models import Model`
3. Define fields as class attributes instead of AMDL slots
4. Use `await Model.create()` instead of `$model.create()`

### Breaking Changes (None)

- All existing imports continue to work
- `aquilia.models.fields.CharField` still resolves correctly
- The `fields/` package re-exports everything from the original `fields_module.py`
- `Model.__init__` now fires `pre_init`/`post_init` signals (no behavioral change unless you connect receivers)
- `Model.create()`, `save()`, `delete_instance()` now fire `pre_save`/`post_save`/`pre_delete`/`post_delete` signals
- Every model now has an `objects` Manager attribute (accessible only on the class, not instances)

---

## Architecture

```
aquilia/
├── models/
│   ├── __init__.py          # Public API re-exports
│   ├── base.py              # Model, ModelMeta, ModelRegistry, Q, Options
│   ├── fields_module.py     # All field type definitions (renamed from fields.py)
│   ├── fields/              # Field sub-package
│   │   ├── __init__.py      # Re-exports fields_module + new types
│   │   ├── mixins.py        # NullableMixin, UniqueMixin, etc.
│   │   ├── composite.py     # CompositeField, CompositePrimaryKey
│   │   └── enum_field.py    # EnumField
│   ├── expression.py        # F(), Value(), RawSQL(), CombinedExpression
│   ├── aggregate.py         # Sum, Avg, Count, Max, Min, StdDev, Variance
│   ├── signals.py           # pre_save, post_save, pre_delete, post_delete, etc.
│   ├── transactions.py      # atomic(), Atomic, TransactionManager
│   ├── deletion.py          # CASCADE, SET_NULL, PROTECT, etc.
│   ├── enums.py             # TextChoices, IntegerChoices
│   ├── sql_builder.py       # SQLBuilder, InsertBuilder, UpdateBuilder, etc.
│   ├── manager.py           # Manager, BaseManager
│   ├── constraint.py        # CheckConstraint, ExclusionConstraint
│   ├── index.py             # GinIndex, GistIndex, BrinIndex, etc.
│   ├── migrations.py        # MigrationRunner, MigrationOps
│   ├── parser.py            # Legacy AMDL parser
│   ├── runtime.py           # Legacy AMDL runtime
│   └── ast_nodes.py         # Legacy AMDL AST
│
└── db/
    ├── __init__.py           # Public API re-exports
    ├── engine.py             # AquiliaDatabase (main engine)
    └── backends/
        ├── __init__.py       # Backend package exports
        ├── base.py           # DatabaseAdapter ABC, AdapterCapabilities
        ├── sqlite.py         # SQLiteAdapter
        ├── postgres.py       # PostgresAdapter
        └── mysql.py          # MySQLAdapter
```
