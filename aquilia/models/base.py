"""
Aquilia Model Base — Pure Python, metaclass-driven ORM.

Usage:
    from aquilia.models import Model
    from aquilia.models.fields import CharField, IntegerField, DateTimeField

    class User(Model):
        table = "users"

        name = CharField(max_length=150)
        email = CharField(max_length=255, unique=True)
        age = IntegerField(null=True)
        created_at = DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-created_at"]
            indexes = [
                Index(fields=["email", "name"]),
            ]
"""

from __future__ import annotations

import copy
import datetime
import decimal
import hashlib
import json
import logging
import uuid
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TYPE_CHECKING,
)

from .fields import (
    AutoField,
    BigAutoField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    Field,
    FieldValidationError,
    ForeignKey,
    Index,
    IntegerField,
    ManyToManyField,
    OneToOneField,
    RelationField,
    TimeField,
    UniqueConstraint,
    UNSET,
)

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase

logger = logging.getLogger("aquilia.models")


# ── Model Options (parsed from Meta class) ───────────────────────────────────


class Options:
    """
    Parsed model options from inner Meta class.

    Attributes:
        table_name: Database table name
        ordering: Default query ordering
        indexes: Composite indexes
        constraints: Unique constraints
        abstract: Whether model is abstract (no table)
        verbose_name: Human-readable model name
        verbose_name_plural: Human-readable plural
        app_label: Owning module name
    """

    __slots__ = (
        "table_name",
        "ordering",
        "indexes",
        "constraints",
        "abstract",
        "verbose_name",
        "verbose_name_plural",
        "app_label",
        "unique_together",
    )

    def __init__(
        self,
        model_name: str,
        meta: Optional[type] = None,
        table_attr: Optional[str] = None,
    ):
        self.table_name = table_attr or (
            getattr(meta, "table", None) or getattr(meta, "table_name", None)
            if meta else None
        ) or model_name.lower()
        self.ordering: List[str] = getattr(meta, "ordering", []) if meta else []
        self.indexes: List[Index] = getattr(meta, "indexes", []) if meta else []
        self.constraints: List[UniqueConstraint] = getattr(meta, "constraints", []) if meta else []
        self.abstract: bool = getattr(meta, "abstract", False) if meta else False
        self.verbose_name: str = getattr(meta, "verbose_name", model_name) if meta else model_name
        self.verbose_name_plural: str = getattr(
            meta, "verbose_name_plural", f"{self.verbose_name}s"
        ) if meta else f"{model_name}s"
        self.app_label: str = getattr(meta, "app_label", "") if meta else ""
        self.unique_together: List[Tuple[str, ...]] = (
            getattr(meta, "unique_together", []) if meta else []
        )


# ── Model Registry ───────────────────────────────────────────────────────────


class ModelRegistry:
    """
    Global registry for all Model subclasses.

    Replaces the old AMDL-based ModelRegistry.
    Tracks all concrete models and resolves forward references.
    """

    _models: Dict[str, Type[Model]] = {}
    _db: Optional[AquiliaDatabase] = None

    @classmethod
    def register(cls, model_cls: Type[Model]) -> None:
        """Register a model class."""
        name = model_cls.__name__
        cls._models[name] = model_cls
        # Resolve any pending forward FK references
        cls._resolve_relations()

    @classmethod
    def get(cls, name: str) -> Optional[Type[Model]]:
        """Get model class by name."""
        return cls._models.get(name)

    @classmethod
    def all_models(cls) -> Dict[str, Type[Model]]:
        """Get all registered models."""
        return dict(cls._models)

    @classmethod
    def set_database(cls, db: AquiliaDatabase) -> None:
        """Set global database for all models."""
        cls._db = db
        for model_cls in cls._models.values():
            model_cls._db = db

    @classmethod
    def get_database(cls) -> Optional[AquiliaDatabase]:
        return cls._db

    @classmethod
    def _resolve_relations(cls) -> None:
        """Resolve forward-referenced model names in FK/M2M fields."""
        for model_cls in cls._models.values():
            for field in model_cls._fields.values():
                if isinstance(field, RelationField) and isinstance(field.to, str):
                    field.resolve_model(cls._models)

    @classmethod
    async def create_tables(cls, db: Optional[AquiliaDatabase] = None) -> List[str]:
        """Create tables for all registered models."""
        target_db = db or cls._db
        if not target_db:
            raise RuntimeError("No database configured for ModelRegistry")

        statements: List[str] = []
        for model_cls in cls._models.values():
            if model_cls._meta.abstract:
                continue

            # Create main table
            sql = model_cls.generate_create_table_sql()
            await target_db.execute(sql)
            statements.append(sql)

            # Create indexes
            for idx_sql in model_cls.generate_index_sql():
                await target_db.execute(idx_sql)
                statements.append(idx_sql)

            # Create M2M junction tables
            for m2m_sql in model_cls.generate_m2m_sql():
                await target_db.execute(m2m_sql)
                statements.append(m2m_sql)

        return statements

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._models.clear()
        cls._db = None

    # ── Lifecycle hooks (DI compatibility) ───────────────────────────

    async def on_startup(self) -> None:
        if ModelRegistry._models:
            await ModelRegistry.create_tables()

    async def on_shutdown(self) -> None:
        pass


# ── Model Metaclass ──────────────────────────────────────────────────────────


class ModelMeta(type):
    """
    Metaclass for Aquilia models.

    Handles:
    - Field collection and ordering
    - Auto-PK injection (BigAutoField)
    - Meta class parsing
    - Model registration
    """

    def __new__(
        mcs,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs,
    ) -> ModelMeta:
        # Don't process the base Model class itself
        parents = [b for b in bases if isinstance(b, ModelMeta)]
        if not parents:
            return super().__new__(mcs, name, bases, namespace)

        # Extract Meta class
        meta_class = namespace.pop("Meta", None)

        # Extract `table = "..."` or `table_name = "..."` attribute
        table_attr = namespace.pop("table", None) or namespace.pop("table_name", None)

        # Collect fields from current class
        fields: Dict[str, Field] = {}
        m2m_fields: Dict[str, ManyToManyField] = {}

        # Inherit fields from parents
        for parent in bases:
            if hasattr(parent, "_fields"):
                fields.update(parent._fields)
            if hasattr(parent, "_m2m_fields"):
                m2m_fields.update(parent._m2m_fields)

        # Collect new fields
        new_fields: Dict[str, Field] = {}
        for key, value in list(namespace.items()):
            if isinstance(value, ManyToManyField):
                m2m_fields[key] = value
                new_fields[key] = value
            elif isinstance(value, Field):
                fields[key] = value
                new_fields[key] = value

        # Parse options
        opts = Options(name, meta_class, table_attr)

        # Auto-inject PK if no primary key defined (and not abstract)
        if not opts.abstract:
            has_pk = any(f.primary_key for f in fields.values())
            if not has_pk:
                pk_field = BigAutoField()
                pk_field.__set_name__(None, "id")
                fields["id"] = pk_field
                namespace["id"] = pk_field

        # Create class
        cls = super().__new__(mcs, name, bases, namespace)

        # Attach metadata
        cls._fields = fields
        cls._m2m_fields = m2m_fields
        cls._meta = opts
        cls._table_name = opts.table_name
        cls._db = None

        # Determine PK
        cls._pk_name = "id"
        for fname, field in fields.items():
            if field.primary_key:
                cls._pk_name = field.column_name
                cls._pk_attr = fname
                break

        # Set name on all fields
        for fname, field in new_fields.items():
            field.__set_name__(cls, fname)
            field.model = cls

        # Collect column names (excludes M2M)
        cls._column_names = [
            f.column_name for f in fields.values()
            if not isinstance(f, ManyToManyField)
        ]

        # Collect attr names (excludes M2M)
        cls._attr_names = [
            fname for fname, f in fields.items()
            if not isinstance(f, ManyToManyField)
        ]

        # Register in global registry (skip abstract)
        if not opts.abstract:
            ModelRegistry.register(cls)

        return cls


# ── Q (Query Builder) ────────────────────────────────────────────────────────


class Q:
    """
    Aquilia Query builder — chainable, async-terminal.

    Usage:
        users = await User.query().where("active = ?", True).order("-id").limit(10).all()
        count = await User.query().where("age > ?", 18).count()
    """

    __slots__ = (
        "_table",
        "_model_cls",
        "_wheres",
        "_params",
        "_order_clauses",
        "_limit_val",
        "_offset_val",
        "_db",
    )

    def __init__(self, table: str, model_cls: Type[Model], db: AquiliaDatabase):
        self._table = table
        self._model_cls = model_cls
        self._wheres: List[str] = []
        self._params: List[Any] = []
        self._order_clauses: List[str] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._db = db

    def where(self, clause: str, *args: Any, **kwargs: Any) -> Q:
        """
        Add WHERE clause.

        Supports positional (?) and named (:name) parameters.
        """
        new = self._clone()
        if kwargs:
            processed = clause
            param_values: List[Any] = []
            for key, val in kwargs.items():
                processed = processed.replace(f":{key}", "?")
                param_values.append(val)
            new._wheres.append(processed)
            new._params.extend(param_values)
        else:
            new._wheres.append(clause)
            new._params.extend(args)
        return new

    def filter(self, **kwargs: Any) -> Q:
        """
        Django-style filter: User.query().filter(name="John", active=True)
        """
        new = self._clone()
        for key, value in kwargs.items():
            if "__" in key:
                field, op = key.rsplit("__", 1)
                lookup_map = {
                    "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
                    "ne": "!=", "like": "LIKE", "ilike": "LIKE",
                    "in": "IN", "isnull": "IS NULL" if value else "IS NOT NULL",
                    "contains": "LIKE", "startswith": "LIKE", "endswith": "LIKE",
                }
                sql_op = lookup_map.get(op, "=")

                if op == "in":
                    placeholders = ", ".join("?" for _ in value)
                    new._wheres.append(f'"{field}" IN ({placeholders})')
                    new._params.extend(value)
                elif op == "isnull":
                    null_clause = "IS NULL" if value else "IS NOT NULL"
                    new._wheres.append(f'"{field}" {null_clause}')
                elif op == "contains":
                    new._wheres.append(f'"{field}" LIKE ?')
                    new._params.append(f"%{value}%")
                elif op == "startswith":
                    new._wheres.append(f'"{field}" LIKE ?')
                    new._params.append(f"{value}%")
                elif op == "endswith":
                    new._wheres.append(f'"{field}" LIKE ?')
                    new._params.append(f"%{value}")
                elif op == "ilike":
                    new._wheres.append(f'LOWER("{field}") LIKE LOWER(?)')
                    new._params.append(value)
                else:
                    new._wheres.append(f'"{field}" {sql_op} ?')
                    new._params.append(value)
            else:
                new._wheres.append(f'"{key}" = ?')
                new._params.append(value)
        return new

    def exclude(self, **kwargs: Any) -> Q:
        """
        Exclude matching records: User.query().exclude(active=False)
        """
        new = self._clone()
        for key, value in kwargs.items():
            new._wheres.append(f'"{key}" != ?')
            new._params.append(value)
        return new

    def order(self, *fields: str) -> Q:
        """
        ORDER BY — prefix with '-' for DESC.
        """
        new = self._clone()
        for f in fields:
            if f.startswith("-"):
                new._order_clauses.append(f'"{f[1:]}" DESC')
            else:
                new._order_clauses.append(f'"{f}" ASC')
        return new

    def limit(self, n: int) -> Q:
        new = self._clone()
        new._limit_val = n
        return new

    def offset(self, n: int) -> Q:
        new = self._clone()
        new._offset_val = n
        return new

    def _clone(self) -> Q:
        c = Q(self._table, self._model_cls, self._db)
        c._wheres = self._wheres.copy()
        c._params = self._params.copy()
        c._order_clauses = self._order_clauses.copy()
        c._limit_val = self._limit_val
        c._offset_val = self._offset_val
        return c

    def _build_select(self, count: bool = False) -> Tuple[str, List[Any]]:
        col = "COUNT(*)" if count else "*"
        sql = f'SELECT {col} FROM "{self._table}"'
        params = self._params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
        if not count and self._order_clauses:
            sql += " ORDER BY " + ", ".join(self._order_clauses)
        if not count and self._limit_val is not None:
            sql += f" LIMIT {self._limit_val}"
        if not count and self._offset_val is not None:
            sql += f" OFFSET {self._offset_val}"

        return sql, params

    async def all(self) -> List[Model]:
        """Execute and return all matching rows."""
        sql, params = self._build_select()
        rows = await self._db.fetch_all(sql, params)
        return [self._model_cls.from_row(row) for row in rows]

    async def one(self) -> Model:
        """Return exactly one row. Raises if 0 or >1."""
        from ..faults.domains import ModelNotFoundFault, QueryFault
        sql, params = self._build_select()
        sql += " LIMIT 2"
        rows = await self._db.fetch_all(sql, params)
        if len(rows) == 0:
            raise ModelNotFoundFault(model_name=self._model_cls.__name__)
        if len(rows) > 1:
            raise QueryFault(
                model=self._model_cls.__name__,
                operation="one",
                reason=f"Multiple rows found, expected one",
            )
        return self._model_cls.from_row(rows[0])

    async def first(self) -> Optional[Model]:
        """Return first matching row or None."""
        sql, params = self._build_select()
        sql += " LIMIT 1"
        rows = await self._db.fetch_all(sql, params)
        if not rows:
            return None
        return self._model_cls.from_row(rows[0])

    async def count(self) -> int:
        sql, params = self._build_select(count=True)
        val = await self._db.fetch_val(sql, params)
        return int(val) if val else 0

    async def exists(self) -> bool:
        """Check if any matching rows exist."""
        return (await self.count()) > 0

    async def update(self, values: Dict[str, Any] = None, **kwargs) -> int:
        """Update matching rows."""
        data = {**(values or {}), **kwargs}
        set_parts = [f'"{k}" = ?' for k in data]
        set_params = list(data.values())

        sql = f'UPDATE "{self._table}" SET {", ".join(set_parts)}'
        params = set_params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount

    async def delete(self) -> int:
        """Delete matching rows."""
        sql = f'DELETE FROM "{self._table}"'
        params = self._params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount

    async def values(self, *fields: str) -> List[Dict[str, Any]]:
        """Return only specific field values as dicts."""
        if fields:
            cols = ", ".join(f'"{f}"' for f in fields)
        else:
            cols = "*"
        sql = f'SELECT {cols} FROM "{self._table}"'
        params = self._params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
        if self._order_clauses:
            sql += " ORDER BY " + ", ".join(self._order_clauses)
        if self._limit_val is not None:
            sql += f" LIMIT {self._limit_val}"

        rows = await self._db.fetch_all(sql, params)
        return rows

    async def values_list(self, *fields: str, flat: bool = False) -> List[Any]:
        """Return field values as tuples (or flat list if single field + flat=True)."""
        rows = await self.values(*fields)
        if flat and len(fields) == 1:
            return [row[fields[0]] for row in rows]
        return [tuple(row.values()) for row in rows]


# ── Model Base Class ─────────────────────────────────────────────────────────


class Model(metaclass=ModelMeta):
    """
    Aquilia Model base class — pure Python, async-first ORM.

    Define models by subclassing and declaring fields:

        class User(Model):
            table = "users"

            name = CharField(max_length=150)
            email = EmailField(unique=True)
            active = BooleanField(default=True)
            created_at = DateTimeField(auto_now_add=True)

    API:
        user = await User.create(name="Alice", email="alice@test.com")
        user = await User.get(pk=1)
        users = await User.query().filter(active=True).order("-created_at").all()
        await User.query().filter(pk=1).update(name="Bob")
        await User.query().filter(pk=1).delete()

        # Relationships
        posts = await user.related("posts")  # reverse FK
        await post.related("author")         # forward FK
    """

    # Class-level attributes set by metaclass
    _fields: ClassVar[Dict[str, Field]] = {}
    _m2m_fields: ClassVar[Dict[str, ManyToManyField]] = {}
    _meta: ClassVar[Options]
    _table_name: ClassVar[str] = ""
    _pk_name: ClassVar[str] = "id"
    _pk_attr: ClassVar[str] = "id"
    _column_names: ClassVar[List[str]] = []
    _attr_names: ClassVar[List[str]] = []
    _db: ClassVar[Optional[AquiliaDatabase]] = None

    def __init__(self, **kwargs: Any):
        """Create a model instance (in-memory, not persisted)."""
        for attr_name, field in self._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif field.column_name in kwargs:
                setattr(self, attr_name, kwargs[field.column_name])
            elif field.has_default():
                setattr(self, attr_name, field.get_default())
            else:
                setattr(self, attr_name, None)

    def __repr__(self) -> str:
        pk_val = getattr(self, self._pk_attr, "?")
        return f"<{self.__class__.__name__} pk={pk_val}>"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return getattr(self, self._pk_attr) == getattr(other, other._pk_attr)

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, getattr(self, self._pk_attr, None)))

    # ── Class-level DB ───────────────────────────────────────────────

    @classmethod
    def _get_db(cls) -> AquiliaDatabase:
        """Get database connection."""
        db = cls._db or ModelRegistry.get_database()
        if db is None:
            from ..db.engine import get_database
            db = get_database()
        return db

    # ── CRUD API ─────────────────────────────────────────────────────

    @classmethod
    async def create(cls, **data: Any) -> Model:
        """
        Create and persist a new record.

        Usage:
            user = await User.create(name="Alice", email="alice@test.com")
        """
        db = cls._get_db()
        instance = cls(**data)

        # Process fields: defaults, auto_now_add, validation
        final_data: Dict[str, Any] = {}
        for attr_name, field in cls._fields.items():
            if isinstance(field, ManyToManyField):
                continue

            value = getattr(instance, attr_name, None)

            # Skip auto-PKs
            if field.primary_key and isinstance(field, (AutoField, BigAutoField)) and value is None:
                continue

            # pre_save hook
            if hasattr(field, "pre_save"):
                value = field.pre_save(instance, is_create=True)
                if value is not None:
                    setattr(instance, attr_name, value)

            # Apply default if still None
            if value is None and field.has_default():
                value = field.get_default()
                setattr(instance, attr_name, value)

            if value is not None:
                # Convert to DB format
                db_value = field.to_db(value)
                final_data[field.column_name] = db_value
            elif not field.null and not field.primary_key:
                # Required field with no value
                if not field.has_default():
                    final_data[field.column_name] = None  # Let DB handle

        if not final_data:
            from ..faults.domains import QueryFault
            raise QueryFault(
                model=cls.__name__,
                operation="create",
                reason="Cannot create record with empty data",
            )

        cols = list(final_data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(f'"{c}"' for c in cols)
        values = list(final_data.values())

        sql = f'INSERT INTO "{cls._table_name}" ({col_names}) VALUES ({placeholders})'
        cursor = await db.execute(sql, values)

        if cursor.lastrowid:
            setattr(instance, cls._pk_attr, cursor.lastrowid)

        return instance

    @classmethod
    async def get(cls, pk: Any = None, **filters: Any) -> Optional[Model]:
        """
        Get a single record by PK or filters.

        Usage:
            user = await User.get(pk=1)
            user = await User.get(email="alice@test.com")
        """
        db = cls._get_db()

        if pk is not None:
            sql = f'SELECT * FROM "{cls._table_name}" WHERE "{cls._pk_name}" = ?'
            row = await db.fetch_one(sql, [pk])
        elif filters:
            wheres = [f'"{k}" = ?' for k in filters]
            sql = f'SELECT * FROM "{cls._table_name}" WHERE ' + " AND ".join(wheres)
            row = await db.fetch_one(sql, list(filters.values()))
        else:
            from ..faults.domains import QueryFault
            raise QueryFault(
                model=cls.__name__,
                operation="get",
                reason="Must provide pk or filters",
            )

        if row is None:
            return None
        return cls.from_row(row)

    @classmethod
    async def get_or_create(
        cls, defaults: Optional[Dict[str, Any]] = None, **lookup: Any
    ) -> Tuple[Model, bool]:
        """
        Get existing or create new record.

        Returns (instance, created) tuple.
        """
        instance = await cls.get(**lookup)
        if instance is not None:
            return instance, False

        create_data = {**lookup, **(defaults or {})}
        instance = await cls.create(**create_data)
        return instance, True

    @classmethod
    async def update_or_create(
        cls, defaults: Optional[Dict[str, Any]] = None, **lookup: Any
    ) -> Tuple[Model, bool]:
        """
        Update existing or create new record.

        Returns (instance, created) tuple.
        """
        instance = await cls.get(**lookup)
        if instance is not None:
            # Update
            update_data = defaults or {}
            if update_data:
                await cls.query().filter(**lookup).update(update_data)
                for k, v in update_data.items():
                    setattr(instance, k, v)
            return instance, False

        create_data = {**lookup, **(defaults or {})}
        instance = await cls.create(**create_data)
        return instance, True

    @classmethod
    async def bulk_create(cls, instances: List[Dict[str, Any]]) -> List[Model]:
        """Create multiple records efficiently."""
        results = []
        for data in instances:
            obj = await cls.create(**data)
            results.append(obj)
        return results

    @classmethod
    def query(cls) -> Q:
        """
        Start a query chain.

        Usage:
            users = await User.query().filter(active=True).all()
        """
        return Q(cls._table_name, cls, cls._get_db())

    @classmethod
    async def all(cls) -> List[Model]:
        """Shortcut: get all records."""
        return await cls.query().all()

    @classmethod
    async def count(cls) -> int:
        """Shortcut: count all records."""
        return await cls.query().count()

    # ── Instance methods ─────────────────────────────────────────────

    async def save(self) -> Model:
        """
        Save instance (insert or update).

        If PK is set, updates. Otherwise, inserts.
        """
        pk_val = getattr(self, self._pk_attr, None)
        db = self._get_db()

        if pk_val is not None:
            # Update
            data: Dict[str, Any] = {}
            for attr_name, field in self._fields.items():
                if isinstance(field, ManyToManyField):
                    continue
                if field.primary_key:
                    continue
                value = getattr(self, attr_name, None)
                if hasattr(field, "pre_save"):
                    value = field.pre_save(self, is_create=False)
                    setattr(self, attr_name, value)
                if value is not None:
                    data[field.column_name] = field.to_db(value)
                else:
                    data[field.column_name] = None

            if data:
                set_parts = [f'"{k}" = ?' for k in data]
                params = list(data.values()) + [pk_val]
                sql = (
                    f'UPDATE "{self._table_name}" SET {", ".join(set_parts)} '
                    f'WHERE "{self._pk_name}" = ?'
                )
                await db.execute(sql, params)
        else:
            # Insert
            result = await self.__class__.create(
                **{
                    attr: getattr(self, attr)
                    for attr in self._attr_names
                    if getattr(self, attr, None) is not None
                }
            )
            setattr(self, self._pk_attr, getattr(result, self._pk_attr))

        return self

    async def delete_instance(self) -> int:
        """Delete this instance from database."""
        pk_val = getattr(self, self._pk_attr)
        if pk_val is None:
            raise ValueError("Cannot delete unsaved instance")
        db = self._get_db()
        cursor = await db.execute(
            f'DELETE FROM "{self._table_name}" WHERE "{self._pk_name}" = ?',
            [pk_val],
        )
        return cursor.rowcount

    async def refresh(self) -> Model:
        """Reload instance from database."""
        pk_val = getattr(self, self._pk_attr)
        if pk_val is None:
            raise ValueError("Cannot refresh unsaved instance")
        fresh = await self.__class__.get(pk=pk_val)
        if fresh is None:
            raise ValueError(f"{self.__class__.__name__} with pk={pk_val} no longer exists")
        for attr in self._attr_names:
            setattr(self, attr, getattr(fresh, attr))
        return self

    # ── Relationships ────────────────────────────────────────────────

    async def related(self, name: str) -> Any:
        """
        Access a related model via FK or M2M.

        Usage:
            author = await post.related("author")     # FK forward
            posts = await user.related("posts")        # FK reverse (via related_name)
            tags = await post.related("tags")           # M2M
        """
        # Check forward FK
        field = self._fields.get(name)
        if isinstance(field, ForeignKey):
            fk_value = getattr(self, name, None)
            if fk_value is None:
                # Try the _id column
                fk_value = getattr(self, field.column_name, None)
            if fk_value is None:
                return None
            target = field.related_model
            if target is None:
                target = ModelRegistry.get(field.to if isinstance(field.to, str) else field.to.__name__)
            if target is None:
                return None
            return await target.get(pk=fk_value)

        # Check M2M
        if name in self._m2m_fields:
            m2m = self._m2m_fields[name]
            target = m2m.related_model or ModelRegistry.get(
                m2m.to if isinstance(m2m.to, str) else m2m.to.__name__
            )
            if target is None:
                return []

            jt = m2m.junction_table_name(self.__class__)
            src_col, tgt_col = m2m.junction_columns(self.__class__)
            pk_val = getattr(self, self._pk_attr)
            target_pk = getattr(target, '_pk_name', 'id')

            db = self._get_db()
            sql = (
                f'SELECT t.* FROM "{target._table_name}" t '
                f'INNER JOIN "{jt}" j ON t."{target_pk}" = j."{tgt_col}" '
                f'WHERE j."{src_col}" = ?'
            )
            rows = await db.fetch_all(sql, [pk_val])
            return [target.from_row(r) for r in rows]

        # Check reverse FK (search other models for FK pointing to us)
        for model_cls in ModelRegistry.all_models().values():
            for fname, f in model_cls._fields.items():
                if isinstance(f, ForeignKey) and f.related_name == name:
                    target_model_name = f.to if isinstance(f.to, str) else f.to.__name__
                    if target_model_name == self.__class__.__name__:
                        pk_val = getattr(self, self._pk_attr)
                        return await model_cls.query().where(
                            f'"{f.column_name}" = ?', pk_val
                        ).all()

        raise AttributeError(f"No relation '{name}' on {self.__class__.__name__}")

    async def attach(self, name: str, *targets: Any) -> None:
        """
        Attach records to a M2M relationship.

        Usage:
            await post.attach("tags", tag1.id, tag2.id)
        """
        m2m = self._m2m_fields.get(name)
        if m2m is None:
            raise AttributeError(f"No M2M relation '{name}' on {self.__class__.__name__}")

        jt = m2m.junction_table_name(self.__class__)
        src_col, tgt_col = m2m.junction_columns(self.__class__)
        pk_val = getattr(self, self._pk_attr)
        db = self._get_db()

        for target in targets:
            target_pk = target if isinstance(target, (int, str)) else getattr(target, target._pk_attr)
            await db.execute(
                f'INSERT OR IGNORE INTO "{jt}" ("{src_col}", "{tgt_col}") VALUES (?, ?)',
                [pk_val, target_pk],
            )

    async def detach(self, name: str, *targets: Any) -> None:
        """
        Detach records from a M2M relationship.

        Usage:
            await post.detach("tags", tag1.id)
        """
        m2m = self._m2m_fields.get(name)
        if m2m is None:
            raise AttributeError(f"No M2M relation '{name}' on {self.__class__.__name__}")

        jt = m2m.junction_table_name(self.__class__)
        src_col, tgt_col = m2m.junction_columns(self.__class__)
        pk_val = getattr(self, self._pk_attr)
        db = self._get_db()

        for target in targets:
            target_pk = target if isinstance(target, (int, str)) else getattr(target, target._pk_attr)
            await db.execute(
                f'DELETE FROM "{jt}" WHERE "{src_col}" = ? AND "{tgt_col}" = ?',
                [pk_val, target_pk],
            )

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self, *, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Serialize model instance to dict."""
        exclude = set(exclude or [])
        result: Dict[str, Any] = {}
        for attr_name, field in self._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            if attr_name in exclude:
                continue
            value = getattr(self, attr_name, None)
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            elif isinstance(value, datetime.date):
                value = value.isoformat()
            elif isinstance(value, datetime.time):
                value = value.isoformat()
            elif isinstance(value, datetime.timedelta):
                value = value.total_seconds()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, bytes):
                value = value.hex()
            elif isinstance(value, decimal.Decimal):
                value = str(value)
            result[attr_name] = value
        return result

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Model:
        """Create model instance from database row dict."""
        instance = cls.__new__(cls)

        for attr_name, field in cls._fields.items():
            if isinstance(field, ManyToManyField):
                continue

            col_name = field.column_name
            if col_name in row:
                raw = row[col_name]
                setattr(instance, attr_name, field.to_python(raw))
            elif attr_name in row:
                raw = row[attr_name]
                setattr(instance, attr_name, field.to_python(raw))
            else:
                setattr(instance, attr_name, None)

        return instance

    # ── SQL Generation ───────────────────────────────────────────────

    @classmethod
    def generate_create_table_sql(cls, dialect: str = "sqlite") -> str:
        """Generate CREATE TABLE SQL."""
        cols: List[str] = []
        for attr_name, field in cls._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            col_def = field.sql_column_def(dialect)
            if col_def:
                cols.append(col_def)

        # unique_together constraints
        for ut in cls._meta.unique_together:
            col_list = ", ".join(f'"{f}"' for f in ut)
            cols.append(f"UNIQUE ({col_list})")

        # UniqueConstraint from Meta.constraints
        for constraint in cls._meta.constraints:
            col_list = ", ".join(f'"{f}"' for f in constraint.fields)
            cols.append(f"UNIQUE ({col_list})")

        body = ",\n  ".join(cols)
        return f'CREATE TABLE IF NOT EXISTS "{cls._table_name}" (\n  {body}\n);'

    @classmethod
    def generate_index_sql(cls, dialect: str = "sqlite") -> List[str]:
        """Generate CREATE INDEX statements from Meta.indexes."""
        stmts: List[str] = []
        for idx in cls._meta.indexes:
            stmts.append(idx.sql(cls._table_name))

        # db_index on individual fields
        for attr_name, field in cls._fields.items():
            if field.db_index and not field.primary_key and not field.unique:
                idx_name = f"idx_{cls._table_name}_{field.column_name}"
                stmts.append(
                    f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "{cls._table_name}" ("{field.column_name}");'
                )

        return stmts

    @classmethod
    def generate_m2m_sql(cls, dialect: str = "sqlite") -> List[str]:
        """Generate junction table SQL for M2M fields."""
        stmts: List[str] = []
        for attr_name, m2m in cls._m2m_fields.items():
            if m2m.through:
                continue  # User-defined through table

            jt = m2m.junction_table_name(cls)
            src_col, tgt_col = m2m.junction_columns(cls)
            sql = (
                f'CREATE TABLE IF NOT EXISTS "{jt}" (\n'
                f'  "id" INTEGER PRIMARY KEY AUTOINCREMENT,\n'
                f'  "{src_col}" INTEGER NOT NULL,\n'
                f'  "{tgt_col}" INTEGER NOT NULL,\n'
                f'  UNIQUE ("{src_col}", "{tgt_col}")\n'
                f');'
            )
            stmts.append(sql)
        return stmts

    @classmethod
    def fingerprint(cls) -> str:
        """Compute deterministic hash for migration diffing."""
        data = {
            "name": cls.__name__,
            "table": cls._table_name,
            "fields": {
                name: field.deconstruct()
                for name, field in cls._fields.items()
                if not isinstance(field, ManyToManyField)
            },
        }
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
