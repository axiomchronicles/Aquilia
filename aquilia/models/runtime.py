"""
Aquilia Model Runtime — ModelProxy, Q (query), and ModelRegistry.

Generates lightweight Python proxy classes from AMDL AST nodes.
All data-access methods use the `$` prefix (Aquilia convention).

Integrates with:
- **AquilaFaults**: raises ``QueryFault``, ``ModelNotFoundFault``,
  ``ModelRegistrationFault`` instead of bare exceptions.
- **DI**: ``ModelRegistry`` is decorated with ``@service(scope="app")``
  and exposes ``on_startup`` / ``on_shutdown`` lifecycle hooks.
"""

from __future__ import annotations

import datetime
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Sequence, Type

from ..db.engine import AquiliaDatabase, get_database
from ..di.decorators import service
from ..faults.domains import (
    ModelNotFoundFault,
    ModelRegistrationFault,
    QueryFault,
    SchemaFault,
)
from .ast_nodes import FieldType, LinkKind, ModelNode, SlotNode

logger = logging.getLogger("aquilia.models.runtime")

# ── Default expression evaluator (safe whitelist) ────────────────────────────

_SAFE_DEFAULTS = {
    "now_utc()": lambda: datetime.datetime.now(datetime.timezone.utc),
    "uuid4()": lambda: str(uuid.uuid4()),
    "seq()": lambda: None,  # Handled by DB auto-increment
}


def _eval_default(expr: str) -> Any:
    """Evaluate a whitelisted AMDL default expression."""
    if expr in _SAFE_DEFAULTS:
        return _SAFE_DEFAULTS[expr]()
    if expr.startswith('env("') and expr.endswith('")'):
        var_name = expr[5:-2]
        return os.environ.get(var_name)
    raise ValueError(f"Disallowed default expression: {expr}")


# ── SQL type mapping (SQLite) ────────────────────────────────────────────────

SQLITE_TYPE_MAP = {
    FieldType.AUTO: "INTEGER",
    FieldType.INT: "INTEGER",
    FieldType.BIGINT: "INTEGER",
    FieldType.STR: "VARCHAR",
    FieldType.TEXT: "TEXT",
    FieldType.BOOL: "INTEGER",  # SQLite stores bools as int
    FieldType.FLOAT: "REAL",
    FieldType.DECIMAL: "DECIMAL",
    FieldType.JSON: "TEXT",
    FieldType.BYTES: "BLOB",
    FieldType.DATETIME: "TIMESTAMP",
    FieldType.DATE: "DATE",
    FieldType.TIME: "TIME",
    FieldType.UUID: "VARCHAR(36)",
    FieldType.ENUM: "VARCHAR(100)",
    FieldType.FOREIGN_KEY: "INTEGER",
}


def _sql_col_def(slot: SlotNode) -> str:
    """Generate SQL column definition from a SlotNode."""
    base_type = SQLITE_TYPE_MAP.get(slot.field_type, "TEXT")

    # Handle VARCHAR with max length
    if slot.field_type == FieldType.STR and slot.max_length:
        base_type = f"VARCHAR({slot.max_length})"
    elif slot.field_type == FieldType.DECIMAL and slot.type_params:
        p, s = slot.type_params[0], slot.type_params[1] if len(slot.type_params) > 1 else 0
        base_type = f"DECIMAL({p},{s})"

    parts = [f'"{slot.name}"', base_type]

    if slot.is_pk:
        parts.append("PRIMARY KEY")
        if slot.field_type == FieldType.AUTO:
            parts.append("AUTOINCREMENT")
    if slot.is_unique and not slot.is_pk:
        parts.append("UNIQUE")
    if not slot.is_nullable and not slot.is_pk:
        parts.append("NOT NULL")

    # SQL-level defaults
    if slot.default_expr:
        if slot.default_expr == "now_utc()":
            parts.append("DEFAULT CURRENT_TIMESTAMP")
        # Other defaults are handled at application level

    return " ".join(parts)


def generate_create_table_sql(model: ModelNode) -> str:
    """Generate CREATE TABLE SQL from a ModelNode."""
    cols = [_sql_col_def(s) for s in model.slots]

    # Add composite indexes as table constraints (unique ones)
    for idx in model.indexes:
        if idx.is_unique:
            field_list = ", ".join(f'"{f}"' for f in idx.fields)
            cols.append(f"UNIQUE ({field_list})")

    body = ",\n  ".join(cols)
    return f'CREATE TABLE IF NOT EXISTS "{model.table_name}" (\n  {body}\n);'


def generate_create_index_sql(model: ModelNode) -> List[str]:
    """Generate CREATE INDEX statements for non-unique indexes."""
    stmts: List[str] = []
    for idx in model.indexes:
        if not idx.is_unique:
            idx_name = idx.name or f"idx_{model.table_name}_{'_'.join(idx.fields)}"
            field_list = ", ".join(f'"{f}"' for f in idx.fields)
            stmts.append(
                f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "{model.table_name}" ({field_list});'
            )
    return stmts


# ── Q (Query) Object ────────────────────────────────────────────────────────


class Q:
    """
    Aquilia Query builder — chainable, async-terminal.

    Usage:
        rows = await User.$query().where("active = ?", True).order("-id").limit(10).all()
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

    def __init__(self, table: str, model_cls: Type[ModelProxy], db: AquiliaDatabase):
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
        Named params are converted to ? placeholders for SQLite.

        Examples:
            .where("active = ?", True)
            .where("age > :min_age", min_age=18)
        """
        new = self._clone()
        if kwargs:
            # Convert :name placeholders to ? for SQLite
            processed_clause = clause
            param_values: List[Any] = []
            for key, val in kwargs.items():
                processed_clause = processed_clause.replace(f":{key}", "?")
                param_values.append(val)
            new._wheres.append(processed_clause)
            new._params.extend(param_values)
        else:
            new._wheres.append(clause)
            new._params.extend(args)
        return new

    def order(self, *fields: str) -> Q:
        """
        Add ORDER BY clause.

        Prefix with '-' for DESC: .order("-created_at", "name")
        """
        new = self._clone()
        for f in fields:
            if f.startswith("-"):
                new._order_clauses.append(f'"{f[1:]}" DESC')
            else:
                new._order_clauses.append(f'"{f}" ASC')
        return new

    def limit(self, n: int) -> Q:
        """Set LIMIT."""
        new = self._clone()
        new._limit_val = n
        return new

    def offset(self, n: int) -> Q:
        """Set OFFSET."""
        new = self._clone()
        new._offset_val = n
        return new

    def _clone(self) -> Q:
        """Create a shallow copy for immutable chaining."""
        c = Q(self._table, self._model_cls, self._db)
        c._wheres = self._wheres.copy()
        c._params = self._params.copy()
        c._order_clauses = self._order_clauses.copy()
        c._limit_val = self._limit_val
        c._offset_val = self._offset_val
        return c

    def _build_select(self, count: bool = False) -> tuple[str, list[Any]]:
        """Build SELECT SQL string."""
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

    async def all(self) -> List[ModelProxy]:
        """Execute query and return all matching rows as proxy instances."""
        sql, params = self._build_select()
        rows = await self._db.fetch_all(sql, params)
        return [self._model_cls._from_row(row) for row in rows]

    async def one(self) -> ModelProxy:
        """Execute query and return exactly one row. Raises ModelNotFoundFault if 0 or >1."""
        sql, params = self._build_select()
        sql += " LIMIT 2"
        rows = await self._db.fetch_all(sql, params)
        if len(rows) == 0:
            raise ModelNotFoundFault(model_name=self._model_cls.__name__)
        if len(rows) > 1:
            raise QueryFault(
                model=self._model_cls.__name__,
                operation="one",
                reason=f"Multiple {self._model_cls.__name__} rows found, expected one",
            )
        return self._model_cls._from_row(rows[0])

    async def first(self) -> Optional[ModelProxy]:
        """Return first matching row or None."""
        sql, params = self._build_select()
        sql += " LIMIT 1"
        rows = await self._db.fetch_all(sql, params)
        if not rows:
            return None
        return self._model_cls._from_row(rows[0])

    async def count(self) -> int:
        """Return count of matching rows."""
        sql, params = self._build_select(count=True)
        val = await self._db.fetch_val(sql, params)
        return int(val) if val else 0

    async def update(self, values: Dict[str, Any]) -> int:
        """Update matching rows. Returns affected row count."""
        set_parts = [f'"{k}" = ?' for k in values]
        set_clause = ", ".join(set_parts)
        set_params = list(values.values())

        sql = f'UPDATE "{self._table}" SET {set_clause}'
        params = set_params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount

    async def delete(self) -> int:
        """Delete matching rows. Returns affected row count."""
        sql = f'DELETE FROM "{self._table}"'
        params = self._params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount


# ── ModelRegistry ────────────────────────────────────────────────────────────


@service(scope="app", name="ModelRegistry")
class ModelRegistry:
    """
    Central registry for AMDL models and their runtime proxies.

    Decorated with ``@service(scope="app")`` so the DI container can
    resolve it as a singleton for the application's lifetime.  Exposes
    ``on_startup`` / ``on_shutdown`` lifecycle hooks.
    """

    def __init__(self, db: Optional[AquiliaDatabase] = None):
        self._models: Dict[str, ModelNode] = {}
        self._proxies: Dict[str, Type[ModelProxy]] = {}
        self._db = db

    # ── Lifecycle hooks ──────────────────────────────────────────────

    async def on_startup(self) -> None:
        """Lifecycle hook — create tables for all registered models."""
        if self._models:
            await self.create_tables()

    async def on_shutdown(self) -> None:
        """Lifecycle hook — cleanup (reserved for future use)."""
        pass

    def register_model(self, model: ModelNode) -> Type[ModelProxy]:
        """
        Register an AMDL model and generate its runtime proxy class.

        Args:
            model: Parsed AMDL ModelNode

        Returns:
            Generated ModelProxy subclass
        """
        self._models[model.name] = model
        proxy_cls = self._generate_proxy(model)
        self._proxies[model.name] = proxy_cls
        logger.info(f"Registered model: {model.name} → {model.table_name}")
        return proxy_cls

    def get_model(self, name: str) -> Optional[ModelNode]:
        """Get parsed model AST by name."""
        return self._models.get(name)

    def get_proxy(self, name: str) -> Optional[Type[ModelProxy]]:
        """Get generated proxy class by model name."""
        return self._proxies.get(name)

    def all_models(self) -> List[ModelNode]:
        """Get all registered model nodes."""
        return list(self._models.values())

    def all_proxies(self) -> Dict[str, Type[ModelProxy]]:
        """Get all proxy classes."""
        return dict(self._proxies)

    def _generate_proxy(self, model: ModelNode) -> Type[ModelProxy]:
        """Generate a ModelProxy subclass from a ModelNode."""
        # Determine PK
        pk_name = "id"
        pk_slot = model.pk_slot
        if pk_slot:
            pk_name = pk_slot.name

        slot_names = [s.name for s in model.slots]

        # Create class dynamically
        cls_dict: Dict[str, Any] = {
            "_model_node": model,
            "_table_name": model.table_name,
            "_slot_names": slot_names,
            "_pk_name": pk_name,
            "_db": self._db,
            "_registry": self,
        }

        # Create the proxy class
        proxy_cls = type(model.name, (ModelProxy,), cls_dict)

        # Attach $-prefixed class methods as proper attributes
        # Python identifiers can't start with $, so we use a descriptor trick
        # But for practical usage, we attach them as regular methods
        # and provide a __getattr__ that maps $ calls

        return proxy_cls

    async def create_tables(self, db: Optional[AquiliaDatabase] = None) -> List[str]:
        """
        Create all registered model tables.

        Returns list of executed SQL statements.

        Raises:
            SchemaFault: When table creation fails
        """
        target_db = db or self._db or get_database()
        statements: List[str] = []

        for model in self._models.values():
            try:
                sql = generate_create_table_sql(model)
                await target_db.execute(sql)
                statements.append(sql)

                for idx_sql in generate_create_index_sql(model):
                    await target_db.execute(idx_sql)
                    statements.append(idx_sql)
            except (SchemaFault, QueryFault):
                raise
            except Exception as exc:
                raise SchemaFault(
                    table=model.table_name,
                    reason=str(exc),
                ) from exc

        return statements

    def set_database(self, db: AquiliaDatabase) -> None:
        """Update database reference for all proxies."""
        self._db = db
        for proxy_cls in self._proxies.values():
            proxy_cls._db = db

    def emit_python(self) -> str:
        """
        Generate Python source code for all model proxies.
        Useful for `aq model dump --emit`.
        """
        lines = [
            '"""Auto-generated Aquilia model proxies."""',
            "",
            "from aquilia.models.runtime import ModelProxy, Q",
            "",
        ]

        for model in self._models.values():
            proxy_cls = self._proxies.get(model.name)
            if not proxy_cls:
                continue

            lines.append(f"")
            lines.append(f"class {model.name}(ModelProxy):")
            lines.append(f'    """Generated from AMDL: {model.source_file}"""')
            lines.append(f'    _table_name = "{model.table_name}"')
            lines.append(f'    _pk_name = "{proxy_cls._pk_name}"')
            lines.append(f"    _slot_names = {proxy_cls._slot_names!r}")
            lines.append("")

            # Document slots
            for slot in model.slots:
                mods = []
                if slot.is_pk:
                    mods.append("PK")
                if slot.is_unique:
                    mods.append("unique")
                if slot.is_nullable:
                    mods.append("nullable")
                mod_str = f"  [{', '.join(mods)}]" if mods else ""
                lines.append(f"    # slot {slot.name} :: {slot.field_type.value}{mod_str}")

            lines.append("")

        return "\n".join(lines)


# ── Metaclass for $-prefix support ──────────────────────────────────────────

class _ModelProxyMeta(type):
    """Metaclass that supports $-prefixed attribute access on model classes."""

    def __getattr__(cls, name):
        mapping = {
            "$create": cls._dollar_create,
            "$get": cls._dollar_get,
            "$query": cls._dollar_query,
            "$update": cls._dollar_update,
            "$delete": cls._dollar_delete,
        }
        if name in mapping:
            return mapping[name]
        raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")


# ── ModelProxy (canonical, with metaclass) ───────────────────────────────────

class ModelProxy(metaclass=_ModelProxyMeta):
    """
    Base class for AMDL-generated model proxies.

    Provides the `$`-prefixed async API unique to Aquilia:
        await Model.$create({...})
        await Model.$get(pk=1)
        Model.$query().where(...).all()
        await Model.$update(filters={...}, values={...})
        await Model.$delete(pk=1)
        await instance.$link("relation_name")
        await instance.$link_many("relation_name")

    All validation / lookup errors are structured faults from
    ``aquilia.faults.domains`` rather than bare Python exceptions.
    """

    _model_node: Optional[ModelNode] = None
    _table_name: str = ""
    _slot_names: List[str] = []
    _pk_name: str = "id"
    _db: Optional[AquiliaDatabase] = None
    _registry: Optional[ModelRegistry] = None

    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name: str) -> Any:
        mapping = {
            "$link": self._dollar_link,
            "$link_many": self._dollar_link_many,
        }
        if name in mapping:
            return mapping[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    @classmethod
    def _from_row(cls, row: Dict[str, Any]) -> ModelProxy:
        instance = cls.__new__(cls)
        for k, v in row.items():
            setattr(instance, k, v)
        return instance

    @classmethod
    def _get_db(cls) -> AquiliaDatabase:
        if cls._db is not None:
            return cls._db
        return get_database()

    # ── Class-level $ API ────────────────────────────────────────────

    @classmethod
    async def _dollar_create(cls, data: Dict[str, Any]) -> ModelProxy:
        """Create a new record. Usage: await Model.$create({...})"""
        db = cls._get_db()
        model = cls._model_node

        final_data = {}
        if model:
            for slot in model.slots:
                if slot.name in data:
                    final_data[slot.name] = data[slot.name]
                elif slot.default_expr and slot.default_expr != "seq()":
                    final_data[slot.name] = _eval_default(slot.default_expr)
                elif slot.is_pk and slot.field_type == FieldType.AUTO:
                    continue
        else:
            final_data = dict(data)

        for k, v in data.items():
            if k not in final_data:
                final_data[k] = v

        if not final_data:
            raise QueryFault(
                model=cls.__name__,
                operation="$create",
                reason="Cannot create record with empty data",
            )

        cols = list(final_data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(f'"{c}"' for c in cols)
        values = list(final_data.values())

        sql = f'INSERT INTO "{cls._table_name}" ({col_names}) VALUES ({placeholders})'
        cursor = await db.execute(sql, values)

        if cursor.lastrowid and cls._pk_name:
            final_data[cls._pk_name] = cursor.lastrowid

        return cls._from_row(final_data)

    @classmethod
    async def _dollar_get(cls, pk: Any = None, **filters: Any) -> Optional[ModelProxy]:
        """Get by PK or filters. Usage: await Model.$get(pk=1)"""
        db = cls._get_db()

        if pk is not None:
            sql = f'SELECT * FROM "{cls._table_name}" WHERE "{cls._pk_name}" = ?'
            row = await db.fetch_one(sql, [pk])
        elif filters:
            wheres = [f'"{k}" = ?' for k in filters]
            sql = f'SELECT * FROM "{cls._table_name}" WHERE ' + " AND ".join(wheres)
            row = await db.fetch_one(sql, list(filters.values()))
        else:
            raise QueryFault(
                model=cls.__name__,
                operation="$get",
                reason="Must provide pk or filters to $get",
            )

        if row is None:
            return None
        return cls._from_row(row)

    @classmethod
    def _dollar_query(cls) -> Q:
        """Start a query chain. Usage: Model.$query().where(...)"""
        return Q(cls._table_name, cls, cls._get_db())

    @classmethod
    async def _dollar_update(cls, filters: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Update matching records. Returns affected count."""
        db = cls._get_db()
        set_parts = [f'"{k}" = ?' for k in values]
        where_parts = [f'"{k}" = ?' for k in filters]
        params = list(values.values()) + list(filters.values())
        sql = (
            f'UPDATE "{cls._table_name}" SET {", ".join(set_parts)} '
            f'WHERE {" AND ".join(where_parts)}'
        )
        cursor = await db.execute(sql, params)
        return cursor.rowcount

    @classmethod
    async def _dollar_delete(cls, filters: Optional[Dict[str, Any]] = None, pk: Any = None) -> int:
        """Delete records. Returns affected count."""
        db = cls._get_db()
        if pk is not None:
            sql = f'DELETE FROM "{cls._table_name}" WHERE "{cls._pk_name}" = ?'
            cursor = await db.execute(sql, [pk])
        elif filters:
            where_parts = [f'"{k}" = ?' for k in filters]
            sql = f'DELETE FROM "{cls._table_name}" WHERE ' + " AND ".join(where_parts)
            cursor = await db.execute(sql, list(filters.values()))
        else:
            raise QueryFault(
                model=cls.__name__,
                operation="$delete",
                reason="Must provide pk or filters to $delete",
            )
        return cursor.rowcount

    # ── Instance-level $ API ─────────────────────────────────────────

    async def _dollar_link(self, link_name: str) -> Optional[ModelProxy]:
        """Access a ONE relationship. Usage: await instance.$link("profile")"""
        if not self._model_node or not self._registry:
            raise ModelRegistrationFault(
                model_name=self.__class__.__name__,
                reason="Model not registered in ModelRegistry",
            )

        link = None
        for l in self._model_node.links:
            if l.name == link_name:
                link = l
                break
        if link is None:
            raise ModelNotFoundFault(
                model_name=f"{self.__class__.__name__}.{link_name}",
                metadata={"reason": f"No link '{link_name}' on {self.__class__.__name__}"},
            )

        target_cls = self._registry.get_proxy(link.target_model)
        if target_cls is None:
            raise ModelNotFoundFault(
                model_name=link.target_model,
                metadata={"reason": f"Target model '{link.target_model}' not found in registry"},
            )

        if link.kind == LinkKind.ONE:
            fk_value = getattr(self, link.fk_field, None) if link.fk_field else None
            if fk_value is None:
                return None
            return await target_cls._dollar_get(pk=fk_value)
        raise QueryFault(
            model=self.__class__.__name__,
            operation="$link",
            reason=f"$link expects ONE relationship, got {link.kind}",
        )

    async def _dollar_link_many(
        self, link_name: str, values: Optional[List[Any]] = None
    ) -> List[ModelProxy]:
        """Access a MANY relationship. Usage: await instance.$link_many("posts")"""
        if not self._model_node or not self._registry:
            raise ModelRegistrationFault(
                model_name=self.__class__.__name__,
                reason="Model not registered in ModelRegistry",
            )

        link = None
        for l in self._model_node.links:
            if l.name == link_name:
                link = l
                break
        if link is None:
            raise ModelNotFoundFault(
                model_name=f"{self.__class__.__name__}.{link_name}",
                metadata={"reason": f"No link '{link_name}' on {self.__class__.__name__}"},
            )

        target_cls = self._registry.get_proxy(link.target_model)
        if target_cls is None:
            raise ModelNotFoundFault(
                model_name=link.target_model,
                metadata={"reason": f"Target model '{link.target_model}' not found in registry"},
            )

        if link.kind == LinkKind.MANY and link.through_model:
            through_cls = self._registry.get_proxy(link.through_model)
            if through_cls is None:
                raise ModelNotFoundFault(
                    model_name=link.through_model,
                    metadata={"reason": f"Through model '{link.through_model}' not found in registry"},
                )

            my_pk = getattr(self, self._pk_name)
            my_model_name = self.__class__.__name__
            my_fk_col = f"{my_model_name.lower()}_id"
            target_fk_col = f"{link.target_model.lower()}_id"

            if values is not None:
                db = self._get_db()
                for val in values:
                    if isinstance(val, dict):
                        target = await target_cls._dollar_create(val)
                        target_pk = getattr(target, target_cls._pk_name)
                    elif isinstance(val, ModelProxy):
                        target_pk = getattr(val, target_cls._pk_name)
                    else:
                        target_pk = val
                    await db.execute(
                        f'INSERT OR IGNORE INTO "{through_cls._table_name}" '
                        f'("{my_fk_col}", "{target_fk_col}") VALUES (?, ?)',
                        [my_pk, target_pk],
                    )
                return []

            db = self._get_db()
            sql = (
                f'SELECT t.* FROM "{target_cls._table_name}" t '
                f'INNER JOIN "{through_cls._table_name}" j '
                f'ON t."{target_cls._pk_name}" = j."{target_fk_col}" '
                f'WHERE j."{my_fk_col}" = ?'
            )
            rows = await db.fetch_all(sql, [my_pk])
            return [target_cls._from_row(r) for r in rows]

        elif link.kind == LinkKind.MANY:
            back_fk = link.fk_field or f"{self.__class__.__name__.lower()}_id"
            my_pk = getattr(self, self._pk_name)
            return await target_cls._dollar_query().where(
                f'"{back_fk}" = ?', my_pk
            ).all()

        raise QueryFault(
            model=self.__class__.__name__,
            operation="$link_many",
            reason=f"$link_many expects MANY relationship, got {link.kind}",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model instance to dict."""
        result = {}
        for name in self._slot_names:
            if hasattr(self, name):
                val = getattr(self, name)
                if isinstance(val, datetime.datetime):
                    val = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    val = val.hex()
                elif isinstance(val, uuid.UUID):
                    val = str(val)
                result[name] = val
        return result

    def __repr__(self) -> str:
        pk_val = getattr(self, self._pk_name, "?")
        return f"<{self.__class__.__name__} {self._pk_name}={pk_val}>"
