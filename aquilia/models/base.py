"""
Aquilia Model Base — Pure Python, metaclass-driven, async-first ORM.

Inspired by Django's model architecture but with Aquilia's unique
async-first, chainable query syntax.

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

    # Aquilia QuerySet API (async-terminal)
    users = await User.objects.filter(active=True).order("-created_at").all()
    user  = await User.objects.get(pk=1)
    count = await User.objects.filter(age__gt=18).count()
    await User.objects.filter(pk=1).update(name="Bob")
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

from .fields_module import (
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

from .signals import (
    pre_save,
    post_save,
    pre_delete,
    post_delete,
    pre_init,
    post_init,
    class_prepared,
    m2m_changed,
)

from .manager import Manager, BaseManager
from .deletion import (
    CASCADE,
    SET_NULL,
    PROTECT,
    SET_DEFAULT,
    DO_NOTHING,
    RESTRICT,
    OnDeleteHandler,
    ProtectedError,
    RestrictedError,
)
from .constraint import CheckConstraint
from .sql_builder import InsertBuilder, UpdateBuilder, DeleteBuilder, CreateTableBuilder

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase
    from .expression import Expression

logger = logging.getLogger("aquilia.models")


# ── Model Options — delegate to options.py ───────────────────────────────────
# Keep this import for backward compatibility; the canonical Options is
# in options.py (imported by metaclass.py).

from .options import Options


# ── Model Registry — delegate to registry.py ────────────────────────────────
# Keep ModelRegistry importable from base.py for backward compat, but the
# canonical implementation lives in registry.py.

from .registry import ModelRegistry as _CanonicalRegistry


class _ModelRegistryMeta(type):
    """Metaclass for ModelRegistry that forwards attribute access to the canonical registry."""

    @property
    def _models(cls) -> Dict[str, Type[Model]]:
        return _CanonicalRegistry._models

    @_models.setter
    def _models(cls, value):
        _CanonicalRegistry._models = value

    @property
    def _db(cls):
        return _CanonicalRegistry._db

    @_db.setter
    def _db(cls, value):
        _CanonicalRegistry._db = value

    @property
    def _app_models(cls):
        return _CanonicalRegistry._app_models

    @_app_models.setter
    def _app_models(cls, value):
        _CanonicalRegistry._app_models = value


class ModelRegistry(metaclass=_ModelRegistryMeta):
    """
    Backward-compatible wrapper around registry.ModelRegistry.

    All calls are forwarded to the canonical registry in registry.py.
    Class attributes (_models, _db) are live properties that always
    reflect the canonical registry's state.
    """

    @classmethod
    def register(cls, model_cls: Type[Model]) -> None:
        _CanonicalRegistry.register(model_cls)

    @classmethod
    def get(cls, name: str) -> Optional[Type[Model]]:
        return _CanonicalRegistry.get(name)

    @classmethod
    def all_models(cls) -> Dict[str, Type[Model]]:
        return _CanonicalRegistry.all_models()

    @classmethod
    def set_database(cls, db: AquiliaDatabase) -> None:
        _CanonicalRegistry.set_database(db)

    @classmethod
    def get_database(cls) -> Optional[AquiliaDatabase]:
        return _CanonicalRegistry.get_database()

    @classmethod
    def _resolve_relations(cls) -> None:
        _CanonicalRegistry._resolve_relations()

    @classmethod
    async def create_tables(cls, db: Optional[AquiliaDatabase] = None) -> List[str]:
        return await _CanonicalRegistry.create_tables(db)

    @classmethod
    def reset(cls) -> None:
        _CanonicalRegistry.reset()

    # ── Lifecycle hooks (DI compatibility) ───────────────────────────

    async def on_startup(self) -> None:
        if _CanonicalRegistry._models:
            await _CanonicalRegistry.create_tables()

    async def on_shutdown(self) -> None:
        pass


# ── Model Metaclass — delegate to metaclass.py ──────────────────────────────
# Import the canonical ModelMeta for backward compatibility.

from .metaclass import ModelMeta


# ── Q (Query Builder) — delegate to query.py ─────────────────────────────────
# The canonical Q class lives in query.py. Import it here for backward compat.

from .query import Q


# ── Model Base Class ─────────────────────────────────────────────────────────


class Model(metaclass=ModelMeta):
    """
    Aquilia Model base class — pure Python, async-first ORM.

    Inspired by Django's Model class but with Aquilia's unique async-first
    syntax and chainable query API.

    Define models by subclassing and declaring fields:

        class User(Model):
            table = "users"

            name = CharField(max_length=150)
            email = EmailField(unique=True)
            active = BooleanField(default=True)
            created_at = DateTimeField(auto_now_add=True)

            class Meta:
                ordering = ["-created_at"]
                get_latest_by = "created_at"

    API — Django-style via objects Manager:
        user  = await User.objects.create(name="Alice", email="alice@test.com")
        user  = await User.objects.get(pk=1)
        users = await User.objects.filter(active=True).order("-created_at").all()
        await User.objects.filter(pk=1).update(name="Bob")
        await User.objects.filter(pk=1).delete()

    API — Aquilia shorthand (class-level convenience):
        user  = await User.create(name="Alice", email="alice@test.com")
        user  = await User.get(pk=1)
        users = await User.query().filter(active=True).all()

    Relationships:
        posts  = await user.related("posts")   # reverse FK
        author = await post.related("author")   # forward FK
        tags   = await post.related("tags")     # M2M
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
    _using_db: Optional[str] = None  # per-instance DB alias

    def __init__(self, **kwargs: Any):
        """Create a model instance (in-memory, not persisted)."""
        pre_init.send_sync(sender=self.__class__, kwargs=kwargs)
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
        post_init.send_sync(sender=self.__class__, instance=self)

    def __repr__(self) -> str:
        pk_val = getattr(self, self._pk_attr, "?")
        return f"<{self.__class__.__name__} pk={pk_val}>"

    def __str__(self) -> str:
        """
        Human-readable representation. Override in subclass for custom display.

        Default: tries the first CharField value, then falls back to repr.
        """
        for attr_name, field in self._fields.items():
            if isinstance(field, CharField) and not field.primary_key:
                val = getattr(self, attr_name, None)
                if val is not None:
                    return str(val)
        return repr(self)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return getattr(self, self._pk_attr) == getattr(other, other._pk_attr)

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, getattr(self, self._pk_attr, None)))

    # ── pk property (Django-style shortcut) ──────────────────────────

    @property
    def pk(self) -> Any:
        """Shortcut for accessing the primary key value (Django-style)."""
        return getattr(self, self._pk_attr, None)

    @pk.setter
    def pk(self, value: Any) -> None:
        """Set the primary key value."""
        setattr(self, self._pk_attr, value)

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

        # Validate all fields before persisting (like Django)
        instance.full_clean()

        # Signal: pre_save (created=True)
        await pre_save.send(sender=cls, instance=instance, created=True)

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

        # Use InsertBuilder from sql_builder for safe, consistent SQL generation
        builder = InsertBuilder(cls._table_name).from_dict(final_data)
        sql, values = builder.build()
        cursor = await db.execute(sql, values)

        if cursor.lastrowid:
            setattr(instance, cls._pk_attr, cursor.lastrowid)

        # Signal: post_save (created=True)
        await post_save.send(sender=cls, instance=instance, created=True)

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
    async def bulk_create(
        cls,
        instances: List[Dict[str, Any]],
        *,
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False,
    ) -> List[Model]:
        """
        Create multiple records efficiently using batched inserts.

        Like Django's bulk_create — faster than individual create() calls.

        Note: Signals (pre_save/post_save) are NOT fired for bulk_create
        (same behavior as Django). Use individual create() if you need signals.

        Usage:
            users = await User.bulk_create([
                {"name": "Alice", "email": "alice@test.com"},
                {"name": "Bob", "email": "bob@test.com"},
            ], batch_size=100)

        Args:
            instances: List of dicts with field data
            batch_size: Number of records per INSERT batch (None = all at once)
            ignore_conflicts: If True, use INSERT OR IGNORE (SQLite)
        """
        if not instances:
            return []

        db = cls._get_db()
        results: List[Model] = []

        # Process in batches
        effective_batch = batch_size or len(instances)
        for i in range(0, len(instances), effective_batch):
            batch = instances[i : i + effective_batch]
            for data in batch:
                obj = cls(**data)

                # Process fields
                final_data: Dict[str, Any] = {}
                for attr_name, field in cls._fields.items():
                    if isinstance(field, ManyToManyField):
                        continue
                    value = getattr(obj, attr_name, None)
                    if field.primary_key and isinstance(field, (AutoField, BigAutoField)) and value is None:
                        continue
                    if hasattr(field, "pre_save"):
                        value = field.pre_save(obj, is_create=True)
                        if value is not None:
                            setattr(obj, attr_name, value)
                    if value is None and field.has_default():
                        value = field.get_default()
                        setattr(obj, attr_name, value)
                    if value is not None:
                        final_data[field.column_name] = field.to_db(value)

                if final_data:
                    builder = InsertBuilder(cls._table_name).from_dict(final_data)
                    sql, values = builder.build()
                    if ignore_conflicts:
                        sql = sql.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
                    cursor = await db.execute(sql, values)
                    if cursor.lastrowid:
                        setattr(obj, cls._pk_attr, cursor.lastrowid)
                results.append(obj)

        return results

    @classmethod
    async def bulk_update(
        cls,
        instances: List[Model],
        fields: List[str],
        *,
        batch_size: Optional[int] = None,
    ) -> int:
        """
        Update specific fields on multiple model instances efficiently.

        Like Django's bulk_update — updates only specified fields.

        Note: Signals are NOT fired (same as Django). Auto-now fields
        are NOT updated automatically.

        Usage:
            for user in users:
                user.name = user.name.upper()
            await User.bulk_update(users, fields=["name"])

        Args:
            instances: List of Model instances with updated attributes
            fields: List of field names to update
            batch_size: Records per batch (None = all)

        Returns:
            Total number of rows updated
        """
        if not instances or not fields:
            return 0

        db = cls._get_db()
        total_updated = 0
        effective_batch = batch_size or len(instances)

        for i in range(0, len(instances), effective_batch):
            batch = instances[i : i + effective_batch]
            for obj in batch:
                pk_val = getattr(obj, cls._pk_attr)
                if pk_val is None:
                    continue
                data: Dict[str, Any] = {}
                for fname in fields:
                    field = cls._fields.get(fname)
                    if field is None or isinstance(field, ManyToManyField):
                        continue
                    value = getattr(obj, fname, None)
                    if value is not None:
                        data[field.column_name] = field.to_db(value)
                    else:
                        data[field.column_name] = None
                if data:
                    builder = UpdateBuilder(cls._table_name).set_dict(data)
                    builder.where(f'"{cls._pk_name}" = ?', pk_val)
                    sql, params = builder.build()
                    cursor = await db.execute(sql, params)
                    total_updated += cursor.rowcount

        return total_updated

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

    @classmethod
    async def latest(cls, field_name: Optional[str] = None) -> Model:
        """
        Return the latest record by date field (Django-style).

        Uses Meta.get_latest_by if field_name is not provided.

        Usage:
            latest_user = await User.latest()           # uses Meta.get_latest_by
            latest_user = await User.latest("created_at")
        """
        field = field_name or getattr(cls._meta, "get_latest_by", None)
        if not field:
            raise ValueError(
                f"{cls.__name__}.latest() requires 'field_name' argument or "
                f"Meta.get_latest_by to be set"
            )
        result = await cls.query().order(f"-{field}").first()
        if result is None:
            from ..faults.domains import ModelNotFoundFault
            raise ModelNotFoundFault(model_name=cls.__name__)
        return result

    @classmethod
    async def earliest(cls, field_name: Optional[str] = None) -> Model:
        """
        Return the earliest record by date field (Django-style).

        Uses Meta.get_latest_by if field_name is not provided.

        Usage:
            first_user = await User.earliest()
            first_user = await User.earliest("created_at")
        """
        field = field_name or getattr(cls._meta, "get_latest_by", None)
        if not field:
            raise ValueError(
                f"{cls.__name__}.earliest() requires 'field_name' argument or "
                f"Meta.get_latest_by to be set"
            )
        result = await cls.query().order(field).first()
        if result is None:
            from ..faults.domains import ModelNotFoundFault
            raise ModelNotFoundFault(model_name=cls.__name__)
        return result

    @classmethod
    async def raw(cls, sql: str, params: Optional[List[Any]] = None) -> List[Model]:
        """
        Execute raw SQL and return model instances (Django-style).

        The SQL must return columns matching the model's fields.

        Usage:
            users = await User.raw(
                "SELECT * FROM users WHERE age > ? ORDER BY name",
                [18]
            )

        ⚠️ Use parameterized queries to prevent SQL injection.
        """
        db = cls._get_db()
        rows = await db.fetch_all(sql, params or [])
        return [cls.from_row(row) for row in rows]

    @classmethod
    def using(cls, db_alias: str) -> Q:
        """
        Target a specific database for this query (Django-style).

        Usage:
            users = await User.using("replica").filter(active=True).all()
        """
        # For now, returns a standard query. Multi-DB routing support
        # will resolve the alias to an actual connection.
        qs = cls.query()
        qs._db_alias = db_alias
        return qs

    # ── Instance methods ─────────────────────────────────────────────

    async def save(
        self,
        *,
        update_fields: Optional[List[str]] = None,
        force_insert: bool = False,
        force_update: bool = False,
        validate: bool = False,
    ) -> Model:
        """
        Save instance (insert or update).

        If PK is set, updates. Otherwise, inserts.

        Args:
            update_fields: Only update these specific fields (Django-style).
                          More efficient — generates SET for only these columns.
            force_insert: Force INSERT even if PK is set.
            force_update: Force UPDATE even if PK is None (raises if no PK).
            validate: Run full_clean() before saving (default False for perf).

        Usage:
            user.name = "Updated"
            await user.save(update_fields=["name"])  # only updates name column
            await user.save(validate=True)            # validates before saving
        """
        if force_insert and force_update:
            raise ValueError("Cannot use force_insert and force_update together")

        pk_val = getattr(self, self._pk_attr, None)

        if force_update and pk_val is None:
            raise ValueError("Cannot force_update on unsaved instance (no PK)")

        db = self._get_db()
        is_create = pk_val is None or force_insert

        # Optional validation
        if validate:
            self.full_clean()

        # Signal: pre_save
        await pre_save.send(sender=self.__class__, instance=self, created=is_create)

        if not is_create:
            # Update
            data: Dict[str, Any] = {}
            target_fields = update_fields or [
                attr for attr in self._attr_names
                if not self._fields[attr].primary_key
            ]

            for attr_name in target_fields:
                field = self._fields.get(attr_name)
                if field is None or isinstance(field, ManyToManyField):
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
                builder = UpdateBuilder(self._table_name).set_dict(data)
                builder.where(f'"{self._pk_name}" = ?', pk_val)
                sql, params = builder.build()
                await db.execute(sql, params)

            # select_on_save: re-read from DB to get computed columns
            if self._meta.select_on_save:
                await self.refresh()
        else:
            # Insert
            create_data = {
                attr: getattr(self, attr)
                for attr in self._attr_names
                if getattr(self, attr, None) is not None
            }
            # If force_insert with existing PK, include it
            if force_insert and pk_val is not None:
                create_data[self._pk_attr] = pk_val
            result = await self.__class__.create(**create_data)
            setattr(self, self._pk_attr, getattr(result, self._pk_attr))

        # Signal: post_save
        await post_save.send(sender=self.__class__, instance=self, created=is_create)

        return self

    @classmethod
    def _get_reverse_fk_refs(cls) -> List[Tuple[Type[Model], str, str]]:
        """
        Get all (model_cls, column_name, on_delete) tuples where other models
        have ForeignKey pointing to this model. Cached per class.
        """
        cache_attr = "_reverse_fk_cache"
        if hasattr(cls, cache_attr) and cls._reverse_fk_cache is not None:
            return cls._reverse_fk_cache

        refs: List[Tuple[Type[Model], str, str]] = []
        for model_cls in ModelRegistry.all_models().values():
            for fname, field in model_cls._fields.items():
                if isinstance(field, ForeignKey):
                    target_name = field.to if isinstance(field.to, str) else field.to.__name__
                    if target_name == cls.__name__:
                        refs.append((model_cls, field.column_name, field.on_delete))

        cls._reverse_fk_cache = refs
        return refs

    async def delete_instance(self) -> int:
        """
        Delete this instance from database.

        Handles on_delete cascading via OnDeleteHandler from deletion.py:
        - CASCADE: delete related records
        - SET_NULL: set FK to NULL
        - PROTECT: raise ProtectedError if references exist
        - RESTRICT: raise RestrictedError if references exist
        """
        pk_val = getattr(self, self._pk_attr)
        if pk_val is None:
            raise ValueError("Cannot delete unsaved instance")

        # Signal: pre_delete
        await pre_delete.send(sender=self.__class__, instance=self)

        db = self._get_db()

        # Handle on_delete for models that FK to us (cached lookup)
        for model_cls, col_name, on_delete_action in self._get_reverse_fk_refs():
            handler = OnDeleteHandler(on_delete_action)
            await handler.handle(db, model_cls, col_name, pk_val)

        # Delete this instance using DeleteBuilder
        builder = DeleteBuilder(self._table_name)
        builder.where(f'"{self._pk_name}" = ?', pk_val)
        sql, params = builder.build()
        cursor = await db.execute(sql, params)
        row_count = cursor.rowcount

        # Signal: post_delete
        await post_delete.send(sender=self.__class__, instance=self)

        return row_count

    def full_clean(self, exclude: Optional[List[str]] = None) -> None:
        """
        Validate instance completely — like Django's Model.full_clean().

        Calls:
        1. clean_fields() — per-field validation (type, null, choices, validators)
        2. clean() — model-level cross-field validation (override in subclass)

        Raises:
            FieldValidationError: If any field fails validation
        """
        self.clean_fields(exclude=exclude)
        self.clean()

    def clean_fields(self, exclude: Optional[List[str]] = None) -> None:
        """
        Validate all fields on this instance.

        Runs field.validate() for each field, collecting errors.

        Raises:
            FieldValidationError: On first validation failure
        """
        exclude = set(exclude or [])
        errors: Dict[str, str] = {}
        for attr_name, field in self._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            if attr_name in exclude:
                continue
            value = getattr(self, attr_name, None)
            try:
                field.validate(value)
            except FieldValidationError as e:
                errors[attr_name] = str(e)
        if errors:
            first_field = next(iter(errors))
            raise FieldValidationError(first_field, errors[first_field])

    def clean(self) -> None:
        """
        Model-level validation hook — override in subclasses.

        Called by full_clean() after clean_fields(). Use for cross-field
        validation logic.

        Usage:
            class Event(Model):
                start = DateTimeField()
                end = DateTimeField()

                def clean(self):
                    if self.start and self.end and self.start > self.end:
                        raise FieldValidationError("end", "End must be after start")
        """
        pass

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

        # Signal: m2m_changed
        await m2m_changed.send(
            sender=self.__class__,
            instance=self,
            action="attach",
            model=name,
            pk_set=[t if isinstance(t, (int, str)) else getattr(t, t._pk_attr) for t in targets],
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

        # Signal: m2m_changed
        await m2m_changed.send(
            sender=self.__class__,
            instance=self,
            action="detach",
            model=name,
            pk_set=[t if isinstance(t, (int, str)) else getattr(t, t._pk_attr) for t in targets],
        )

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(
        self,
        *,
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Serialize model instance to dict.

        Args:
            fields: Whitelist of field names to include (all if None).
            exclude: Blacklist of field names to exclude.

        Usage:
            user.to_dict()                         # all fields
            user.to_dict(fields=["id", "name"])    # only id & name
            user.to_dict(exclude=["password"])      # everything except password
        """
        include = set(fields) if fields else None
        skip = set(exclude or [])
        result: Dict[str, Any] = {}

        for attr_name, field in self._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            if include is not None and attr_name not in include:
                continue
            if attr_name in skip:
                continue

            value = getattr(self, attr_name, None)
            value = self._serialize_value(value)
            result[attr_name] = value
        return result

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Convert a Python value to a JSON-safe representation."""
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, datetime.time):
            return value.isoformat()
        if isinstance(value, datetime.timedelta):
            return value.total_seconds()
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, bytes):
            return value.hex()
        if isinstance(value, decimal.Decimal):
            return str(value)
        return value

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
        """Generate CREATE TABLE SQL using CreateTableBuilder."""
        builder = CreateTableBuilder(cls._table_name)

        for attr_name, field in cls._fields.items():
            if isinstance(field, ManyToManyField):
                continue
            col_def = field.sql_column_def(dialect)
            if col_def:
                builder.column(col_def)

        # unique_together constraints
        for ut in cls._meta.unique_together:
            col_list = ", ".join(f'"{f}"' for f in ut)
            builder.constraint(f"UNIQUE ({col_list})")

        # Meta.constraints — CheckConstraint, UniqueConstraint, etc.
        for constraint in cls._meta.constraints:
            if isinstance(constraint, CheckConstraint):
                builder.constraint(constraint.sql(cls._table_name, dialect))
            elif hasattr(constraint, 'fields'):
                col_list = ", ".join(f'"{f}"' for f in constraint.fields)
                builder.constraint(f"UNIQUE ({col_list})")

        return builder.build()

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
