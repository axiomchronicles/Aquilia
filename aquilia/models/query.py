"""
Aquilia Query Builder — chainable, immutable, async-terminal Q object.

Inspired by Django's QuerySet architecture — every chain method returns
a NEW Q instance (immutable cloning), and terminal methods (all, first,
count, etc.) are async and execute the query.

Unique Aquilia syntax differences from Django:
    - .query()  starts a chain   (Django: .objects.all())
    - .order()  for ordering     (Django: .order_by())
    - .where()  for raw clauses  (Aquilia-only: raw parameterized WHERE)
    - .one()    for strict get   (Aquilia-only: raises if != 1 result)
    - .apply_q()  for QNode      (Aquilia-only: composable QNode objects)
    - All terminal methods are async (await qs.all(), await qs.count())

Usage:
    users = await User.objects.filter(active=True).order("-id").limit(10).all()
    count = await User.objects.filter(age__gt=18).count()
    result = await User.objects.aggregate(avg_age=Avg("age"))
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from .fields.lookups import resolve_lookup, lookup_registry

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase
    from .base import Model

__all__ = ["Q", "QNode", "QCombination", "Prefetch"]


# ── Q Combinator (for AND/OR composition) ────────────────────────────────────


class QNode:
    """
    Composable filter node for complex WHERE clauses.

    Similar to Django's Q objects but named QNode to avoid confusion
    with Aquilia's Q (QuerySet) class.

    Usage:
        from aquilia.models.query import QNode as QF

        # OR
        q = QF(name="Alice") | QF(name="Bob")
        users = await User.objects.filter(q).all()

        # AND + OR
        q = (QF(active=True) & QF(role="admin")) | QF(is_superuser=True)

        # Negation
        q = ~QF(banned=True)
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


# ── Prefetch Object (Django-style custom prefetch) ───────────────────────────


class Prefetch:
    """
    Custom prefetch descriptor for prefetch_related().

    Allows specifying a custom queryset for the prefetch.

    Usage:
        from aquilia.models.query import Prefetch

        users = await User.objects.prefetch_related(
            Prefetch("orders", queryset=Order.objects.filter(total__gt=500))
        ).all()
    """

    def __init__(
        self,
        lookup: str,
        queryset: Optional[Q] = None,
        to_attr: Optional[str] = None,
    ):
        self.lookup = lookup
        self.queryset = queryset
        self.to_attr = to_attr or lookup

    def __repr__(self) -> str:
        return f"Prefetch({self.lookup!r})"


def _build_filter_clause(key: str, value: Any) -> Tuple[str, List[Any]]:
    """Convert a key=value filter pair to SQL clause + params.

    Delegates to the Lookup registry from fields.lookups for all
    recognised suffixes, falling back to legacy handling for
    ``ne`` and ``ilike`` which have no dedicated Lookup class.

    Supports F() expressions and Subquery as the comparison value:
        filter(balance__gt=F("min_balance"))  → "balance" > "min_balance"
        filter(dept_id__in=Subquery(...))     → "dept_id" IN (SELECT ...)
    """
    from .expression import Expression, Combinable

    def _render_value(val: Any) -> Tuple[str, List[Any]]:
        """Render a value — returns (sql_fragment, params)."""
        if isinstance(val, (Expression, Combinable)):
            return val.as_sql("sqlite")
        return "?", [val]

    if "__" in key:
        field, op = key.rsplit("__", 1)

        # If value is an F()/Expression, handle comparisons directly
        # This MUST come before the lookup registry which treats values as literals
        if isinstance(value, (Expression, Combinable)):
            rhs_sql, rhs_params = value.as_sql("sqlite")
            op_map = {
                "exact": "=", "gt": ">", "gte": ">=",
                "lt": "<", "lte": "<=", "ne": "!=",
            }
            if op in op_map:
                return f'"{field}" {op_map[op]} {rhs_sql}', rhs_params
            # For 'in' with a Subquery
            if op == "in" and hasattr(value, '_build_select'):
                sub_sql, sub_params = value._build_select()
                return f'"{field}" IN ({sub_sql})', sub_params

        # Lookup registry covers: exact, iexact, contains, icontains,
        # startswith, istartswith, endswith, iendswith, in, gt, gte,
        # lt, lte, isnull, range, regex, iregex, date, year, month, day
        registry = lookup_registry()
        if op in registry:
            lookup_inst = resolve_lookup(field, op, value)
            return lookup_inst.as_sql()

        # Legacy / extra lookups not in the registry
        if op == "ne":
            rhs, params = _render_value(value)
            return f'"{field}" != {rhs}', params
        elif op == "ilike":
            return f'LOWER("{field}") LIKE LOWER(?)', [value]
        elif op == "like":
            return f'"{field}" LIKE ?', [value]
        else:
            rhs, params = _render_value(value)
            return f'"{field}" = {rhs}', params
    else:
        rhs, params = _render_value(value)
        return f'"{key}" = {rhs}', params


# ── Q (QuerySet) — Immutable, Chainable, Async-Terminal ─────────────────────


class Q:
    """
    Aquilia QuerySet — chainable, immutable, async-terminal query builder.

    Every chain method returns a NEW Q instance (Django-style immutability).
    Terminal methods (all, first, count, etc.) are async and execute SQL.

    Chain methods (return new Q):
        filter(**kwargs)          — Django-style field lookups
        exclude(**kwargs)         — Negated filter
        where(clause, *args)     — Raw parameterized WHERE (Aquilia-only)
        order(*fields)           — ORDER BY ("-field" for DESC, "?" for RANDOM)
        limit(n)                 — LIMIT
        offset(n)                — OFFSET
        distinct()               — SELECT DISTINCT
        only(*fields)            — Load only specified fields
        defer(*fields)           — Defer loading of fields
        annotate(**exprs)        — Add computed annotations
        group_by(*fields)        — GROUP BY
        having(clause, *args)    — HAVING
        select_related(*fields)  — JOIN-based eager loading
        prefetch_related(*fields)— Separate-query prefetching
        apply_q(QNode)           — Apply composable QNode filter
        using(db_alias)          — Target specific database
        select_for_update()      — SELECT ... FOR UPDATE (locking)
        none()                   — Return empty queryset

    Terminal methods (async, execute query):
        all()                    — List[Model]
        first()                  — Optional[Model]
        last()                   — Optional[Model]
        one()                    — Model (raises if != 1)
        count()                  — int
        exists()                 — bool
        update(**kwargs)         — int (rows affected)
        delete()                 — int (rows deleted)
        values(*fields)          — List[Dict]
        values_list(*fields)     — List[Tuple] or flat list
        in_bulk(id_list)         — Dict[pk, Model]
        aggregate(**exprs)       — Dict[str, Any]
        explain()                — str (query plan)
        latest(field)            — Model
        earliest(field)          — Model
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
        "_db_alias",
        "_annotations",
        "_group_by",
        "_having",
        "_having_params",
        "_distinct",
        "_select_related",
        "_prefetch_related",
        "_only_fields",
        "_defer_fields",
        "_select_for_update",
        "_is_none",
        "_set_operations",
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
        self._db_alias: Optional[str] = None
        self._annotations: Dict[str, Any] = {}
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._having_params: List[Any] = []
        self._distinct: bool = False
        self._select_related: List[str] = []
        self._prefetch_related: List[Any] = []  # str or Prefetch
        self._only_fields: List[str] = []
        self._defer_fields: List[str] = []
        self._select_for_update: bool = False
        self._is_none: bool = False
        self._set_operations: List[Tuple[str, Q]] = []

    # ── Chain methods (return new Q) ─────────────────────────────────

    def where(self, clause: str, *args: Any, **kwargs: Any) -> Q:
        """
        Add raw WHERE clause (Aquilia-only syntax).

        Supports positional (?) and named (:name) parameters.

        Usage:
            .where("age > ?", 18)
            .where("status = :status AND role = :role", status="active", role="admin")
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

    def filter(self, *q_nodes: Any, **kwargs: Any) -> Q:
        """
        Django-style field lookup filter.

        Supports all lookups: exact, gt, gte, lt, lte, ne, contains,
        icontains, startswith, endswith, in, isnull, range, regex, etc.

        Also supports QNode objects for complex AND/OR/NOT composition:
            .filter(QNode(name="Alice") | QNode(name="Bob"))
            .filter(QNode(active=True) & QNode(role="admin"), age__gt=18)

        Usage:
            .filter(name="John")                    # exact match
            .filter(age__gt=18, active=True)         # AND conditions
            .filter(name__icontains="john")          # case-insensitive contains
            .filter(id__in=[1, 2, 3])                # IN clause
            .filter(created_at__range=(start, end))  # BETWEEN
        """
        new = self._clone()

        # Handle QNode objects (positional args)
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

    def exclude(self, *q_nodes: Any, **kwargs: Any) -> Q:
        """
        Negated filter — exclude matching records.

        Supports QNode objects for complex exclusions:
            .exclude(QNode(role="banned") | QNode(role="suspended"))

        Usage:
            .exclude(active=False)             # WHERE NOT (active = 0)
            .exclude(email__contains="spam")   # WHERE NOT (email LIKE '%spam%')
        """
        new = self._clone()
        # Handle QNode objects (positional args)
        for qn in q_nodes:
            if isinstance(qn, QNode):
                sql, params = qn._build_sql()
                if sql:
                    new._wheres.append(f"NOT ({sql})")
                    new._params.extend(params)
        # Handle keyword filters
        for key, value in kwargs.items():
            clause, params = _build_filter_clause(key, value)
            new._wheres.append(f"NOT ({clause})")
            new._params.extend(params)
        return new

    def order(self, *fields: Any) -> Q:
        """
        ORDER BY — Aquilia's primary ordering method.

        Prefix with '-' for DESC. Use '?' for RANDOM.
        Also accepts F().desc() / F().asc() OrderBy objects.

        Usage:
            .order("-created_at", "name")         # string-based
            .order("?")                           # RANDOM()
            .order(F("name").asc())                # expression-based
            .order(F("score").desc(nulls_last=True))  # NULLS LAST
        """
        from .expression import OrderBy
        new = self._clone()
        for f in fields:
            if isinstance(f, OrderBy):
                sql, _ = f.as_sql("sqlite")
                new._order_clauses.append(sql)
            elif isinstance(f, str):
                if f == "?":
                    new._order_clauses.append("RANDOM()")
                elif f.startswith("-"):
                    new._order_clauses.append(f'"{f[1:]}" DESC')
                else:
                    new._order_clauses.append(f'"{f}" ASC')
            else:
                # Other expression types
                if hasattr(f, 'as_sql'):
                    sql, _ = f.as_sql("sqlite")
                    new._order_clauses.append(sql)
        return new

    # Django-style alias
    order_by = order

    # ── Set Operations (Django-style) ────────────────────────────────

    def union(self, *querysets: Q, all: bool = False) -> Q:
        """
        Combine this queryset with others using UNION.

        By default removes duplicates. Pass all=True for UNION ALL.

        Usage:
            qs1 = User.objects.filter(role="admin")
            qs2 = User.objects.filter(role="staff")
            combined = qs1.union(qs2)
            results = await combined.all()
        """
        new = self._clone()
        for qs in querysets:
            op = "UNION ALL" if all else "UNION"
            new._set_operations.append((op, qs))
        return new

    def intersection(self, *querysets: Q) -> Q:
        """
        Combine with INTERSECT — only rows in ALL querysets.

        Usage:
            admins = User.objects.filter(role="admin")
            active = User.objects.filter(active=True)
            active_admins = admins.intersection(active)
        """
        new = self._clone()
        for qs in querysets:
            new._set_operations.append(("INTERSECT", qs))
        return new

    def difference(self, *querysets: Q) -> Q:
        """
        Combine with EXCEPT — rows in this set but not in others.

        Usage:
            all_users = User.objects.filter(active=True)
            admins = User.objects.filter(role="admin")
            non_admins = all_users.difference(admins)
        """
        new = self._clone()
        for qs in querysets:
            new._set_operations.append(("EXCEPT", qs))
        return new

    def limit(self, n: int) -> Q:
        """Set LIMIT on query results."""
        new = self._clone()
        new._limit_val = n
        return new

    def offset(self, n: int) -> Q:
        """Set OFFSET for pagination."""
        new = self._clone()
        new._offset_val = n
        return new

    def distinct(self) -> Q:
        """Apply SELECT DISTINCT."""
        new = self._clone()
        new._distinct = True
        return new

    def only(self, *fields: str) -> Q:
        """
        Load only specified fields (deferred loading for others).

        ⚠️ Accessing deferred fields will NOT trigger lazy load in Aquilia.

        Usage:
            users = await User.objects.only("id", "name").all()
        """
        new = self._clone()
        # Always include PK
        pk = self._model_cls._pk_attr
        field_list = list(fields)
        if pk not in field_list:
            field_list.insert(0, pk)
        new._only_fields = field_list
        return new

    def defer(self, *fields: str) -> Q:
        """
        Defer loading of specified fields.

        Usage:
            users = await User.objects.defer("bio", "avatar").all()
        """
        new = self._clone()
        new._defer_fields = list(fields)
        return new

    def annotate(self, **expressions: Any) -> Q:
        """
        Add aggregate/expression annotations to each row.

        Usage:
            from aquilia.models import Avg, Count, F

            qs = User.objects.annotate(
                order_count=Count("orders"),
                avg_spent=Avg("orders__total"),
            )
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
        Eager-load FK/OneToOne relations via JOINs.

        Like Django's select_related — reduces N+1 queries for FK.

        Usage:
            orders = await Order.objects.select_related("user").all()
            orders[0].user.name  # no extra query
        """
        new = self._clone()
        new._select_related.extend(fields)
        return new

    def prefetch_related(self, *lookups: Any) -> Q:
        """
        Prefetch related objects via separate queries.

        Accepts field names or Prefetch objects for custom querysets.

        Usage:
            users = await User.objects.prefetch_related("posts").all()
            users = await User.objects.prefetch_related(
                Prefetch("posts", queryset=Post.objects.filter(published=True))
            ).all()
        """
        new = self._clone()
        new._prefetch_related.extend(lookups)
        return new

    def select_for_update(self, *, nowait: bool = False, skip_locked: bool = False) -> Q:
        """
        Lock selected rows (SELECT ... FOR UPDATE).

        Use inside atomic() for safe concurrent updates.

        Usage:
            async with atomic():
                product = await Product.objects.select_for_update().filter(id=1).one()
                product.stock -= 1
                await product.save()
        """
        new = self._clone()
        new._select_for_update = True
        return new

    def using(self, db_alias: str) -> Q:
        """
        Target a specific database for this query (Django-style).

        Usage:
            users = await User.objects.using("replica").filter(active=True).all()
        """
        new = self._clone()
        new._db_alias = db_alias
        return new

    def apply_q(self, q_node: QNode) -> Q:
        """
        Apply a QNode filter to this queryset (Aquilia-only).

        Usage:
            q = QNode(active=True) | QNode(is_staff=True)
            users = await User.objects.apply_q(q).all()
        """
        return self.filter(q_node)

    def none(self) -> Q:
        """
        Return an empty queryset that evaluates to [] (Django-style).

        Useful for conditional query building.

        Usage:
            qs = User.objects.none()
            await qs.all()  # → []
            await qs.count()  # → 0
        """
        new = self._clone()
        new._is_none = True
        return new

    # ── Slicing support ──────────────────────────────────────────────

    def __getitem__(self, key: Any) -> Q:
        """
        Support Python slicing on querysets (Django-style).

        Usage:
            top_5 = User.objects.order("-score")[:5]
            page  = User.objects.order("id")[10:20]
        """
        if isinstance(key, slice):
            new = self._clone()
            if key.start is not None:
                new._offset_val = int(key.start)
            if key.stop is not None:
                start = key.start or 0
                new._limit_val = int(key.stop) - start
            return new
        elif isinstance(key, int):
            new = self._clone()
            new._offset_val = key
            new._limit_val = 1
            return new
        raise TypeError(f"Q indices must be integers or slices, not {type(key).__name__}")

    # ── Internal ─────────────────────────────────────────────────────

    def _clone(self) -> Q:
        """Create an immutable copy of this queryset."""
        c = Q(self._table, self._model_cls, self._db)
        c._wheres = self._wheres.copy()
        c._params = self._params.copy()
        c._order_clauses = self._order_clauses.copy()
        c._limit_val = self._limit_val
        c._offset_val = self._offset_val
        c._db_alias = self._db_alias
        c._annotations = self._annotations.copy()
        c._group_by = self._group_by.copy()
        c._having = self._having.copy()
        c._having_params = self._having_params.copy()
        c._distinct = self._distinct
        c._select_related = self._select_related.copy()
        c._prefetch_related = self._prefetch_related.copy()
        c._only_fields = self._only_fields.copy()
        c._defer_fields = self._defer_fields.copy()
        c._select_for_update = self._select_for_update
        c._is_none = self._is_none
        c._set_operations = self._set_operations[:]
        return c

    def _build_select(self, count: bool = False) -> Tuple[str, List[Any]]:
        """Build the SELECT SQL and parameter list."""
        from .aggregate import Aggregate
        from .expression import Expression

        params = self._params.copy()

        if count:
            col = "COUNT(*)"
        elif self._annotations:
            parts = []
            # Determine base columns
            if self._only_fields:
                parts.extend(f'"{f}"' for f in self._only_fields)
            elif self._defer_fields and hasattr(self._model_cls, '_column_names'):
                # Exclude deferred fields
                for cn in self._model_cls._attr_names:
                    if cn not in self._defer_fields:
                        field = self._model_cls._fields.get(cn)
                        if field:
                            parts.append(f'"{field.column_name}"')
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
        elif self._defer_fields and hasattr(self._model_cls, '_attr_names'):
            # Build column list excluding deferred fields
            selected = []
            for cn in self._model_cls._attr_names:
                if cn not in self._defer_fields:
                    field = self._model_cls._fields.get(cn)
                    if field:
                        selected.append(f'"{field.column_name}"')
            col = ", ".join(selected) if selected else "*"
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

        # SELECT FOR UPDATE (PostgreSQL/MySQL only, ignored on SQLite)
        if self._select_for_update and not count:
            sql += " FOR UPDATE"

        return sql, params

    # ── Terminal methods (async, execute query) ──────────────────────

    async def all(self) -> List[Model]:
        """Execute and return all matching rows as model instances."""
        if self._is_none:
            return []
        sql, params = self._build_select()

        # Apply set operations (UNION, INTERSECT, EXCEPT)
        if self._set_operations:
            for op, other_qs in self._set_operations:
                other_sql, other_params = other_qs._build_select()
                sql = f"({sql}) {op} ({other_sql})"
                params.extend(other_params)

        rows = await self._db.fetch_all(sql, params)
        return [self._model_cls.from_row(row) for row in rows]

    async def one(self) -> Model:
        """
        Return exactly one row. Raises if 0 or >1 (Aquilia-only).

        Use this when you expect exactly one result and want strict validation.
        """
        if self._is_none:
            from ..faults.domains import ModelNotFoundFault
            raise ModelNotFoundFault(model_name=self._model_cls.__name__)
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
                reason="Multiple rows found, expected one",
            )
        return self._model_cls.from_row(rows[0])

    async def first(self) -> Optional[Model]:
        """Return first matching row or None."""
        if self._is_none:
            return None
        sql, params = self._build_select()
        sql += " LIMIT 1"
        rows = await self._db.fetch_all(sql, params)
        if not rows:
            return None
        return self._model_cls.from_row(rows[0])

    async def last(self) -> Optional[Model]:
        """Return last matching row or None (reverses ordering)."""
        if self._is_none:
            return None
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
            pk = self._model_cls._pk_name
            new._order_clauses = [f'"{pk}" DESC']
        return await new.first()

    async def latest(self, field_name: Optional[str] = None) -> Model:
        """
        Return the latest record by date field.

        Uses Meta.get_latest_by if field_name is not provided.
        """
        field = field_name or getattr(self._model_cls._meta, "get_latest_by", None)
        if not field:
            raise ValueError(
                f"latest() requires 'field_name' or Meta.get_latest_by"
            )
        result = await self.order(f"-{field}").first()
        if result is None:
            from ..faults.domains import ModelNotFoundFault
            raise ModelNotFoundFault(model_name=self._model_cls.__name__)
        return result

    async def earliest(self, field_name: Optional[str] = None) -> Model:
        """
        Return the earliest record by date field.

        Uses Meta.get_latest_by if field_name is not provided.
        """
        field = field_name or getattr(self._model_cls._meta, "get_latest_by", None)
        if not field:
            raise ValueError(
                f"earliest() requires 'field_name' or Meta.get_latest_by"
            )
        result = await self.order(field).first()
        if result is None:
            from ..faults.domains import ModelNotFoundFault
            raise ModelNotFoundFault(model_name=self._model_cls.__name__)
        return result

    async def count(self) -> int:
        """Return count of matching rows."""
        if self._is_none:
            return 0
        sql, params = self._build_select(count=True)
        val = await self._db.fetch_val(sql, params)
        return int(val) if val else 0

    async def exists(self) -> bool:
        """
        Check if any matching rows exist.

        Usage:
            if await User.objects.filter(email="a@b.com").exists():
                print("Found!")
        """
        if self._is_none:
            return False
        return (await self.count()) > 0

    async def update(self, values: Dict[str, Any] = None, **kwargs) -> int:
        """
        Update matching rows. Returns number of affected rows.

        Supports F() expressions for race-safe updates:
            await Product.objects.filter(id=1).update(stock=F("stock") - 1)
        """
        if self._is_none:
            return 0
        from .expression import Expression
        data = {**(values or {}), **kwargs}
        set_parts = []
        set_params = []

        for k, v in data.items():
            if isinstance(v, Expression):
                expr_sql, expr_params = v.as_sql("sqlite")
                set_parts.append(f'"{k}" = {expr_sql}')
                set_params.extend(expr_params)
            else:
                set_parts.append(f'"{k}" = ?')
                set_params.append(v)

        sql = f'UPDATE "{self._table}" SET {", ".join(set_parts)}'
        params = set_params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount

    async def delete(self) -> int:
        """Delete matching rows. Returns number of deleted rows."""
        if self._is_none:
            return 0
        sql = f'DELETE FROM "{self._table}"'
        params = self._params.copy()

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)

        cursor = await self._db.execute(sql, params)
        return cursor.rowcount

    async def values(self, *fields: str) -> List[Dict[str, Any]]:
        """
        Return rows as dicts with only specified field values.

        Respects all query state: filters, ordering, group_by, having,
        annotations, set operations, limit/offset.

        Usage:
            data = await User.objects.values("id", "name")
            # [{"id": 1, "name": "Alice"}, ...]

            # With annotations:
            data = await User.objects.annotate(num=Count("id")).values("role", "num")
        """
        if self._is_none:
            return []

        # Build using the existing infrastructure for consistency
        from .aggregate import Aggregate
        from .expression import Expression

        params = self._params.copy()

        if fields:
            col_parts = []
            for f in fields:
                # Check if this is an annotation alias
                if f in self._annotations:
                    expr = self._annotations[f]
                    if isinstance(expr, (Aggregate, Expression)):
                        sql_frag, expr_params = expr.as_sql("sqlite")
                        col_parts.append(f'{sql_frag} AS "{f}"')
                        params = list(expr_params) + params
                    else:
                        col_parts.append(f'{expr} AS "{f}"')
                else:
                    col_parts.append(f'"{f}"')
            cols = ", ".join(col_parts)
        else:
            cols = "*"

        sql = f'SELECT {cols} FROM "{self._table}"'

        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
        if self._group_by:
            sql += " GROUP BY " + ", ".join(f'"{g}"' for g in self._group_by)
        if self._having:
            sql += " HAVING " + " AND ".join(f"({h})" for h in self._having)
            params.extend(self._having_params)
        if self._order_clauses:
            sql += " ORDER BY " + ", ".join(self._order_clauses)
        if self._limit_val is not None:
            sql += f" LIMIT {self._limit_val}"
        if self._offset_val is not None:
            sql += f" OFFSET {self._offset_val}"

        # Set operations
        if self._set_operations:
            for op, other_qs in self._set_operations:
                other_sql, other_params = other_qs._build_select()
                sql = f"({sql}) {op} ({other_sql})"
                params.extend(other_params)

        rows = await self._db.fetch_all(sql, params)
        return rows

    async def values_list(self, *fields: str, flat: bool = False) -> List[Any]:
        """
        Return field values as tuples, or flat list if single field + flat=True.

        Usage:
            names = await User.objects.values_list("name", flat=True)
            # ["Alice", "Bob", ...]
        """
        rows = await self.values(*fields)
        if flat and len(fields) == 1:
            return [row[fields[0]] for row in rows]
        return [tuple(row.values()) for row in rows]

    async def in_bulk(self, id_list: List[Any]) -> Dict[Any, Model]:
        """
        Return a dict mapping PKs to instances for the given ID list.

        Usage:
            users = await User.objects.in_bulk([1, 2, 3])
            # {1: <User pk=1>, 2: <User pk=2>, 3: <User pk=3>}
        """
        if not id_list or self._is_none:
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

    async def aggregate(self, **expressions: Any) -> Dict[str, Any]:
        """
        Compute aggregates and return a dict.

        Usage:
            result = await Product.objects.aggregate(
                avg_price=Avg("price"),
                total=Count("id"),
                max_price=Max("price"),
            )
            # {"avg_price": 25.5, "total": 100, "max_price": 99.99}
        """
        if self._is_none:
            return {alias: None for alias in expressions}
        from .aggregate import Aggregate
        from .expression import Expression

        select_parts = []
        params: List[Any] = []
        for alias, expr in expressions.items():
            if isinstance(expr, (Aggregate, Expression)):
                sql_fragment, expr_params = expr.as_sql("sqlite")
                select_parts.append(f'{sql_fragment} AS "{alias}"')
                params.extend(expr_params)
            else:
                select_parts.append(f'{expr} AS "{alias}"')

        sql = f'SELECT {", ".join(select_parts)} FROM "{self._table}"'
        if self._wheres:
            sql += " WHERE " + " AND ".join(f"({w})" for w in self._wheres)
            params.extend(self._params)

        row = await self._db.fetch_one(sql, params)
        return dict(row) if row else {alias: None for alias in expressions}

    async def create(self, **data: Any) -> Model:
        """
        Create a new record (Django-style shortcut on queryset).

        Usage:
            user = await User.objects.filter(role="admin").create(
                name="Admin", email="admin@test.com"
            )
        """
        return await self._model_cls.create(**data)

    async def get_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **lookup: Any
    ) -> Tuple[Model, bool]:
        """
        Get existing or create new (Django-style on queryset).

        Returns (instance, created) tuple.
        """
        return await self._model_cls.get_or_create(defaults=defaults, **lookup)

    async def update_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **lookup: Any
    ) -> Tuple[Model, bool]:
        """
        Update existing or create new (Django-style on queryset).

        Returns (instance, created) tuple.
        """
        return await self._model_cls.update_or_create(defaults=defaults, **lookup)

    async def explain(self, *, format: Optional[str] = None) -> str:
        """
        Return the query execution plan (EXPLAIN).

        Usage:
            plan = await User.objects.filter(active=True).explain()
            print(plan)
        """
        sql, params = self._build_select()
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        rows = await self._db.fetch_all(explain_sql, params)
        return "\n".join(str(row) for row in rows)

    # ── Iteration support ────────────────────────────────────────────

    def __aiter__(self):
        """
        Async iteration over queryset results.

        Usage:
            async for user in User.objects.filter(active=True):
                print(user.name)
        """
        return _QueryIterator(self)

    def __repr__(self) -> str:
        if self._is_none:
            return f"<Q: {self._model_cls.__name__}.none()>"
        sql, params = self._build_select()
        return f"<Q: {sql} {params}>"

    @property
    def query(self) -> str:
        """
        Return the raw SQL that would be executed (Django-style introspection).

        Usage:
            print(User.objects.filter(active=True).query)
        """
        sql, params = self._build_select()
        return sql


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
