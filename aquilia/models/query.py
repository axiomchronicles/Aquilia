"""
Aquilia Query Builder — chainable, async-terminal Q object.

Usage:
    users = await User.query().where("active = ?", True).order("-id").limit(10).all()
    count = await User.query().where("age > ?", 18).count()
    result = await User.query().aggregate(avg_age=Avg("age"))
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from .fields.lookups import resolve_lookup, lookup_registry

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase
    from .base import Model

__all__ = ["Q", "QNode", "QCombination"]


# ── Q Combinator (for AND/OR composition) ────────────────────────────────────


class QNode:
    """
    Composable filter node for complex WHERE clauses.

    Usage:
        from aquilia.models.query import QNode as QF

        # OR
        q = QF(name="Alice") | QF(name="Bob")
        users = await User.query().apply_q(q).all()

        # AND + OR
        q = (QF(active=True) & QF(role="admin")) | QF(is_superuser=True)
        users = await User.query().apply_q(q).all()

        # Negation
        q = ~QF(banned=True)
        users = await User.query().apply_q(q).all()
    """

    AND = "AND"
    OR = "OR"

    def __init__(self, **kwargs: Any):
        self.filters: Dict[str, Any] = kwargs
        self.negated: bool = False
        self.children: List[QNode] = []
        self.connector: str = self.AND

    def __and__(self, other: QNode) -> QNode:
        node = QNode()
        node.connector = self.AND
        node.children = [self, other]
        return node

    def __or__(self, other: QNode) -> QNode:
        node = QNode()
        node.connector = self.OR
        node.children = [self, other]
        return node

    def __invert__(self) -> QNode:
        clone = QNode(**self.filters)
        clone.negated = not self.negated
        clone.children = self.children[:]
        clone.connector = self.connector
        return clone

    def _build_sql(self) -> Tuple[str, List[Any]]:
        """Build SQL WHERE clause fragment from this node."""
        parts: List[str] = []
        params: List[Any] = []

        # Own filters
        for key, value in self.filters.items():
            clause, clause_params = _build_filter_clause(key, value)
            parts.append(clause)
            params.extend(clause_params)

        # Child nodes
        for child in self.children:
            child_sql, child_params = child._build_sql()
            if child_sql:
                parts.append(f"({child_sql})")
                params.extend(child_params)

        if not parts:
            return "", []

        joiner = f" {self.connector} "
        sql = joiner.join(parts)

        if self.negated:
            sql = f"NOT ({sql})"

        return sql, params

    def __repr__(self) -> str:
        if self.children:
            return f"QNode({self.connector}, children={len(self.children)})"
        return f"QNode({self.filters})"


# Alias for convenience
QCombination = QNode


def _build_filter_clause(key: str, value: Any) -> Tuple[str, List[Any]]:
    """Convert a key=value filter pair to SQL clause + params.

    Delegates to the Lookup registry from fields.lookups for all
    recognised suffixes, falling back to legacy handling for
    ``ne`` and ``ilike`` which have no dedicated Lookup class.
    """
    if "__" in key:
        field, op = key.rsplit("__", 1)

        # Lookup registry covers: exact, iexact, contains, icontains,
        # startswith, istartswith, endswith, iendswith, in, gt, gte,
        # lt, lte, isnull, range, regex, iregex, date, year, month, day
        registry = lookup_registry()
        if op in registry:
            lookup_inst = resolve_lookup(field, op, value)
            return lookup_inst.as_sql()

        # Legacy / extra lookups not in the registry
        if op == "ne":
            return f'"{field}" != ?', [value]
        elif op == "ilike":
            return f'LOWER("{field}") LIKE LOWER(?)', [value]
        elif op == "like":
            return f'"{field}" LIKE ?', [value]
        else:
            return f'"{field}" = ?', [value]
    else:
        return f'"{key}" = ?', [value]


# ── Q (Query Builder) ────────────────────────────────────────────────────────


class Q:
    """
    Aquilia Query builder — chainable, async-terminal.

    Usage:
        users = await User.query().where("active = ?", True).order("-id").limit(10).all()
        count = await User.query().where("age > ?", 18).count()
        result = await User.query().aggregate(avg_age=Avg("age"))
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
        "_annotations",
        "_group_by",
        "_having",
        "_having_params",
        "_distinct",
        "_select_related",
        "_prefetch_related",
        "_only_fields",
        "_defer_fields",
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
        self._annotations: Dict[str, Any] = {}
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._having_params: List[Any] = []
        self._distinct: bool = False
        self._select_related: List[str] = []
        self._prefetch_related: List[str] = []
        self._only_fields: List[str] = []
        self._defer_fields: List[str] = []

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

    def filter(self, *q_nodes: QNode, **kwargs: Any) -> Q:
        """
        Django-style filter: User.query().filter(name="John", active=True)

        Also supports QNode composition:
            User.query().filter(QNode(name="Alice") | QNode(name="Bob"))
        """
        new = self._clone()

        # Handle QNode objects
        for qn in q_nodes:
            if isinstance(qn, QNode):
                sql, params = qn._build_sql()
                if sql:
                    new._wheres.append(f"({sql})")
                    new._params.extend(params)

        # Handle keyword filters
        for key, value in kwargs.items():
            clause, params = _build_filter_clause(key, value)
            new._wheres.append(clause)
            new._params.extend(params)

        return new

    def exclude(self, **kwargs: Any) -> Q:
        """
        Exclude matching records: User.query().exclude(active=False)
        """
        new = self._clone()
        for key, value in kwargs.items():
            clause, params = _build_filter_clause(key, value)
            new._wheres.append(f"NOT ({clause})")
            new._params.extend(params)
        return new

    def order(self, *fields: str) -> Q:
        """
        ORDER BY — prefix with '-' for DESC.

        Usage:
            .order("-created_at", "name")   # ORDER BY created_at DESC, name ASC
            .order("?")                     # ORDER BY RANDOM()
        """
        new = self._clone()
        for f in fields:
            if f == "?":
                new._order_clauses.append("RANDOM()")
            elif f.startswith("-"):
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

    def distinct(self) -> Q:
        """Apply SELECT DISTINCT."""
        new = self._clone()
        new._distinct = True
        return new

    def only(self, *fields: str) -> Q:
        """Load only specified fields (deferred loading for others)."""
        new = self._clone()
        new._only_fields = list(fields)
        return new

    def defer(self, *fields: str) -> Q:
        """Defer loading of specified fields."""
        new = self._clone()
        new._defer_fields = list(fields)
        return new

    def annotate(self, **expressions: Any) -> Q:
        """
        Add aggregate/expression annotations.

        Usage:
            from aquilia.models.aggregate import Avg, Count
            qs = User.query().annotate(avg_age=Avg("age"), num=Count("id"))
        """
        new = self._clone()
        new._annotations.update(expressions)
        return new

    def group_by(self, *fields: str) -> Q:
        """GROUP BY clause."""
        new = self._clone()
        new._group_by.extend(fields)
        return new

    def having(self, clause: str, *args: Any) -> Q:
        """HAVING clause (use after group_by)."""
        new = self._clone()
        new._having.append(clause)
        new._having_params.extend(args)
        return new

    def select_related(self, *fields: str) -> Q:
        """
        Hint for eager loading related objects.

        Currently stores the relation names; actual JOIN-based loading
        is applied when executing the query.
        """
        new = self._clone()
        new._select_related.extend(fields)
        return new

    def prefetch_related(self, *fields: str) -> Q:
        """
        Hint for prefetch loading (separate queries per relation).
        """
        new = self._clone()
        new._prefetch_related.extend(fields)
        return new

    def apply_q(self, q_node: QNode) -> Q:
        """Apply a QNode filter to this queryset."""
        return self.filter(q_node)

    async def aggregate(self, **expressions: Any) -> Dict[str, Any]:
        """
        Compute aggregates and return a dict.

        Usage:
            result = await User.query().aggregate(avg_age=Avg("age"), total=Count("id"))
            # result == {"avg_age": 25.5, "total": 100}
        """
        from .aggregate import Aggregate

        from .expression import Expression

        select_parts = []
        params: List[Any] = []
        for alias, expr in expressions.items():
            if isinstance(expr, (Aggregate, Expression)):
                sql_fragment, expr_params = expr.as_sql("sqlite")
                select_parts.append(f"{sql_fragment} AS \"{alias}\"")
                params.extend(expr_params)
            else:
                select_parts.append(f"{expr} AS \"{alias}\"")

        sql = f'SELECT {", ".join(select_parts)} FROM "{self._table}"'
        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)

        row = await self._db.fetch_one(sql, params)
        return dict(row) if row else {alias: None for alias in expressions}

    def _clone(self) -> Q:
        c = Q(self._table, self._model_cls, self._db)
        c._wheres = self._wheres.copy()
        c._params = self._params.copy()
        c._order_clauses = self._order_clauses.copy()
        c._limit_val = self._limit_val
        c._offset_val = self._offset_val
        c._annotations = self._annotations.copy()
        c._group_by = self._group_by.copy()
        c._having = self._having.copy()
        c._having_params = self._having_params.copy()
        c._distinct = self._distinct
        c._select_related = self._select_related.copy()
        c._prefetch_related = self._prefetch_related.copy()
        c._only_fields = self._only_fields.copy()
        c._defer_fields = self._defer_fields.copy()
        return c

    def _build_select(self, count: bool = False) -> Tuple[str, List[Any]]:
        from .aggregate import Aggregate
        from .expression import Expression

        params = self._params.copy()

        if count:
            col = "COUNT(*)"
        elif self._annotations:
            parts = []
            # Determine columns
            if self._only_fields:
                parts.extend(f'"{f}"' for f in self._only_fields)
            else:
                parts.append("*")
            for alias, expr in self._annotations.items():
                if isinstance(expr, (Aggregate, Expression)):
                    sql_frag, expr_params = expr.as_sql("sqlite")
                    parts.append(f'{sql_frag} AS "{alias}"')
                    params = list(expr_params) + params
                else:
                    parts.append(f'{expr} AS "{alias}"')
            col = ", ".join(parts)
        elif self._only_fields:
            col = ", ".join(f'"{f}"' for f in self._only_fields)
        else:
            col = "*"

        distinct = "DISTINCT " if self._distinct and not count else ""
        sql = f'SELECT {distinct}{col} FROM "{self._table}"'

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)

        if self._group_by:
            sql += " GROUP BY " + ", ".join(f'"{g}"' for g in self._group_by)

        if self._having:
            sql += " HAVING " + " AND ".join(f"({h})" for h in self._having)
            params.extend(self._having_params)

        if not count and self._order_clauses:
            sql += " ORDER BY " + ", ".join(self._order_clauses)
        elif not count and not self._order_clauses and hasattr(self._model_cls, '_meta'):
            # Apply default ordering from Meta class
            meta_ordering = getattr(self._model_cls._meta, 'ordering', [])
            if meta_ordering:
                default_order = []
                for f in meta_ordering:
                    if f.startswith("-"):
                        default_order.append(f'"{f[1:]}" DESC')
                    else:
                        default_order.append(f'"{f}" ASC')
                sql += " ORDER BY " + ", ".join(default_order)
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

    async def last(self) -> Optional[Model]:
        """Return last matching row or None."""
        # Reverse ordering, get first
        new = self._clone()
        if new._order_clauses:
            reversed_order = []
            for clause in new._order_clauses:
                if clause.endswith(" ASC"):
                    reversed_order.append(clause.replace(" ASC", " DESC"))
                elif clause.endswith(" DESC"):
                    reversed_order.append(clause.replace(" DESC", " ASC"))
                else:
                    reversed_order.append(clause)
            new._order_clauses = reversed_order
        else:
            # Default to PK DESC
            pk = self._model_cls._pk_name
            new._order_clauses = [f'"{pk}" DESC']
        return await new.first()

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

    async def in_bulk(self, id_list: List[Any]) -> Dict[Any, Model]:
        """
        Return a dict mapping PKs to instances for the given ID list.
        """
        if not id_list:
            return {}
        pk_name = self._model_cls._pk_name
        placeholders = ", ".join("?" for _ in id_list)
        sql = f'SELECT * FROM "{self._table}" WHERE "{pk_name}" IN ({placeholders})'
        rows = await self._db.fetch_all(sql, list(id_list))
        result = {}
        pk_attr = self._model_cls._pk_attr
        for row in rows:
            instance = self._model_cls.from_row(row)
            result[getattr(instance, pk_attr)] = instance
        return result

    async def explain(self) -> str:
        """Return the query execution plan (EXPLAIN)."""
        sql, params = self._build_select()
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        rows = await self._db.fetch_all(explain_sql, params)
        return "\n".join(str(row) for row in rows)

    # ── Iteration support ────────────────────────────────────────────

    def __aiter__(self):
        return _QueryIterator(self)

    def __repr__(self) -> str:
        sql, params = self._build_select()
        return f"<Q: {sql} {params}>"


class _QueryIterator:
    """Async iterator for Q querysets."""

    def __init__(self, query: Q):
        self._query = query
        self._results: Optional[List] = None
        self._index = 0

    async def __anext__(self):
        if self._results is None:
            self._results = await self._query.all()
        if self._index >= len(self._results):
            raise StopAsyncIteration
        item = self._results[self._index]
        self._index += 1
        return item
