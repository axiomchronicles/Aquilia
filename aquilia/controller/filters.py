"""
Aquilia Filter System — Django-REST-style filtering, searching, and ordering.

Provides declarative filter backends that integrate with Aquilia's
Controller engine to auto-filter querysets or list data from query
parameters.

Features:
- FilterSet:       Declarative field-based filtering (exact, range, boolean,
                   icontains, in, isnull, gt/lt/gte/lte, startswith, endswith)
- SearchFilter:    Multi-field text search via ?search=<term>
- OrderingFilter:  Dynamic ordering via ?ordering=<field>
- Custom backends: Implement BaseFilterBackend for full control

Usage:
    from aquilia import Controller, GET, FilterSet, SearchFilter, OrderingFilter

    class ProductFilter(FilterSet):
        class Meta:
            fields = {
                "category": ["exact"],
                "price": ["gte", "lte", "range"],
                "is_active": ["exact"],
                "name": ["icontains"],
            }

    class ProductsController(Controller):
        prefix = "/products"

        @GET("/", filterset_class=ProductFilter,
             search_fields=["name", "description"],
             ordering_fields=["price", "created_at", "name"])
        async def list_products(self, ctx):
            products = await Product.objects.all()
            return products   # engine auto-applies filter → search → order
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)


__all__ = [
    "BaseFilterBackend",
    "FilterSet",
    "FilterSetMeta",
    "SearchFilter",
    "OrderingFilter",
    "filter_queryset",
    "apply_filters_to_list",
]


# ═══════════════════════════════════════════════════════════════════════════
#  Lookup operators
# ═══════════════════════════════════════════════════════════════════════════

# Supported lookup suffixes → description
LOOKUP_TYPES: Dict[str, str] = {
    "exact":       "Exact match (default)",
    "iexact":      "Case-insensitive exact match",
    "contains":    "Substring match (case-sensitive)",
    "icontains":   "Substring match (case-insensitive)",
    "startswith":  "Starts with",
    "istartswith": "Starts with (case-insensitive)",
    "endswith":    "Ends with",
    "iendswith":   "Ends with (case-insensitive)",
    "gt":          "Greater than",
    "gte":         "Greater than or equal",
    "lt":          "Less than",
    "lte":         "Less than or equal",
    "in":          "In list (comma-separated)",
    "range":       "Between two values (comma-separated)",
    "isnull":      "Is null (true/false)",
    "regex":       "Regex match",
    "iregex":      "Regex match (case-insensitive)",
    "ne":          "Not equal",
    "date":        "Date portion of datetime",
    "year":        "Year of date/datetime",
    "month":       "Month of date/datetime",
    "day":         "Day of date/datetime",
}


# ═══════════════════════════════════════════════════════════════════════════
#  Value coercion helpers
# ═══════════════════════════════════════════════════════════════════════════

def _coerce_bool(val: str) -> bool:
    """Coerce a query-string value to a Python bool."""
    return val.lower() in ("true", "1", "yes", "on")


def _coerce_value(val: str, lookup: str = "exact") -> Any:
    """
    Best-effort coercion of a raw query-string value.

    For ``in`` / ``range`` lookups, returns a list.
    """
    if lookup in ("in", "range"):
        return [v.strip() for v in val.split(",") if v.strip()]

    if lookup == "isnull":
        return _coerce_bool(val)

    # Try numeric coercion
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        pass

    # Try ISO date
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(val, fmt)
        except (ValueError, TypeError):
            continue

    # Bool
    if val.lower() in ("true", "false"):
        return _coerce_bool(val)

    return val


# ═══════════════════════════════════════════════════════════════════════════
#  In-memory list filtering (for non-ORM data)
# ═══════════════════════════════════════════════════════════════════════════

def _matches_lookup(item_value: Any, lookup: str, filter_value: Any) -> bool:
    """Test a single lookup predicate against a value."""
    if item_value is None and lookup != "isnull":
        return False

    if lookup == "exact":
        return item_value == filter_value
    elif lookup == "iexact":
        return str(item_value).lower() == str(filter_value).lower()
    elif lookup == "ne":
        return item_value != filter_value
    elif lookup == "contains":
        return str(filter_value) in str(item_value)
    elif lookup == "icontains":
        return str(filter_value).lower() in str(item_value).lower()
    elif lookup == "startswith":
        return str(item_value).startswith(str(filter_value))
    elif lookup == "istartswith":
        return str(item_value).lower().startswith(str(filter_value).lower())
    elif lookup == "endswith":
        return str(item_value).endswith(str(filter_value))
    elif lookup == "iendswith":
        return str(item_value).lower().endswith(str(filter_value).lower())
    elif lookup == "gt":
        return item_value > filter_value
    elif lookup == "gte":
        return item_value >= filter_value
    elif lookup == "lt":
        return item_value < filter_value
    elif lookup == "lte":
        return item_value <= filter_value
    elif lookup == "in":
        coerced = [_try_coerce_like(item_value, v) for v in filter_value]
        return item_value in coerced
    elif lookup == "range":
        if len(filter_value) == 2:
            lo = _try_coerce_like(item_value, filter_value[0])
            hi = _try_coerce_like(item_value, filter_value[1])
            return lo <= item_value <= hi
        return False
    elif lookup == "isnull":
        if filter_value:
            return item_value is None
        else:
            return item_value is not None
    elif lookup == "regex":
        return bool(re.search(str(filter_value), str(item_value)))
    elif lookup == "iregex":
        return bool(re.search(str(filter_value), str(item_value), re.IGNORECASE))
    elif lookup == "year":
        return getattr(item_value, "year", None) == int(filter_value)
    elif lookup == "month":
        return getattr(item_value, "month", None) == int(filter_value)
    elif lookup == "day":
        return getattr(item_value, "day", None) == int(filter_value)
    return True


def _try_coerce_like(reference: Any, raw: str) -> Any:
    """Coerce *raw* to the same type as *reference*."""
    if isinstance(reference, int):
        try:
            return int(raw)
        except (ValueError, TypeError):
            return raw
    if isinstance(reference, float):
        try:
            return float(raw)
        except (ValueError, TypeError):
            return raw
    return raw


def _get_nested(obj: Any, dotted_key: str) -> Any:
    """
    Traverse nested dicts/objects via dotted path.

    ``_get_nested({"a": {"b": 1}}, "a.b")`` → ``1``
    """
    parts = dotted_key.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def apply_filters_to_list(
    data: List[Any],
    filters: Dict[str, Any],
) -> List[Any]:
    """
    Apply parsed filter clauses to an in-memory list of dicts / objects.

    ``filters`` is ``{"field__lookup": coerced_value, ...}``.
    """
    if not filters:
        return data

    result = data
    for key, val in filters.items():
        # Split field__lookup
        if "__" in key:
            parts = key.rsplit("__", 1)
            field_name, lookup = parts[0], parts[1]
            if lookup not in LOOKUP_TYPES:
                # Treat the whole key as a field name with exact match
                field_name = key
                lookup = "exact"
        else:
            field_name = key
            lookup = "exact"

        result = [
            item for item in result
            if _matches_lookup(_get_nested(item, field_name), lookup, val)
        ]
    return result


def apply_search_to_list(
    data: List[Any],
    search_term: str,
    search_fields: List[str],
) -> List[Any]:
    """
    Apply text search over *search_fields* on an in-memory list.

    An item passes if **any** search field contains *search_term*
    (case-insensitive).
    """
    if not search_term or not search_fields:
        return data
    term_lower = search_term.lower()
    return [
        item for item in data
        if any(
            term_lower in str(_get_nested(item, f) or "").lower()
            for f in search_fields
        )
    ]


def apply_ordering_to_list(
    data: List[Any],
    ordering: List[str],
) -> List[Any]:
    """
    Sort an in-memory list by one or more fields.

    Prefix ``-`` for descending.
    """
    if not ordering:
        return data

    import functools

    def _compare(a: Any, b: Any) -> int:
        for field_spec in ordering:
            desc = field_spec.startswith("-")
            field_name = field_spec.lstrip("-")
            va = _get_nested(a, field_name)
            vb = _get_nested(b, field_name)
            # Handle None
            if va is None and vb is None:
                continue
            if va is None:
                return 1 if not desc else -1
            if vb is None:
                return -1 if not desc else 1
            if va < vb:
                return 1 if desc else -1
            if va > vb:
                return -1 if desc else 1
        return 0

    return sorted(data, key=functools.cmp_to_key(_compare))


# ═══════════════════════════════════════════════════════════════════════════
#  FilterSet metaclass & class
# ═══════════════════════════════════════════════════════════════════════════

class FilterSetMeta(type):
    """
    Metaclass for FilterSet — collects ``Meta.fields`` at class creation.

    Accepts two forms for ``Meta.fields``:

    1. **List** — shorthand for exact-only filtering::

        class Meta:
            fields = ["status", "created_at"]

    2. **Dict** — explicit lookups per field::

        class Meta:
            fields = {
                "status": ["exact", "in"],
                "price": ["gte", "lte", "range"],
                "name": ["icontains"],
            }
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)
        meta = namespace.get("Meta") or getattr(cls, "Meta", None)

        if meta is not None:
            raw_fields = getattr(meta, "fields", None)
            if isinstance(raw_fields, (list, tuple)):
                cls._filter_fields = {f: ["exact"] for f in raw_fields}
            elif isinstance(raw_fields, dict):
                cls._filter_fields = dict(raw_fields)
            else:
                cls._filter_fields = {}
        else:
            cls._filter_fields = {}

        return cls


class FilterSet(metaclass=FilterSetMeta):
    """
    Declarative filter specification — Django-REST-Framework style.

    Parses query parameters from the request and produces a dict of
    ``{field__lookup: coerced_value}`` clauses that can be fed directly
    into ``Model.objects.filter()`` or ``apply_filters_to_list()``.

    Usage::

        class ProductFilter(FilterSet):
            class Meta:
                fields = {
                    "category": ["exact", "in"],
                    "price": ["gte", "lte", "range"],
                    "is_active": ["exact"],
                }

        # In controller — engine does this automatically:
        fs = ProductFilter(request=request)
        clauses = fs.parse()  # {"category": "electronics", "price__gte": 10}

    Custom filter methods
    ---------------------
    Define ``filter_<field>`` to override default behaviour::

        class ProductFilter(FilterSet):
            class Meta:
                fields = {"category": ["exact"]}

            def filter_category(self, value: str) -> dict:
                # Map "sale" → special clause
                if value == "sale":
                    return {"discount__gt": 0}
                return {"category": value}
    """

    _filter_fields: ClassVar[Dict[str, List[str]]] = {}

    def __init__(self, *, request: Any = None, query_params: Optional[Dict[str, str]] = None):
        if query_params is not None:
            self._params = query_params
        elif request is not None:
            # request.query_params is a MultiDict
            qp = request.query_params
            if hasattr(qp, "items"):
                self._params = dict(qp.items())
            else:
                self._params = dict(qp) if qp else {}
        else:
            self._params = {}

    # ── Public API ───────────────────────────────────────────────────

    def parse(self) -> Dict[str, Any]:
        """
        Parse query parameters into ORM-compatible filter clauses.

        Returns a dict like ``{"field__lookup": value, ...}`` that can be
        spread into ``Model.objects.filter(**clauses)``.
        """
        clauses: Dict[str, Any] = {}
        for field_name, lookups in self._filter_fields.items():
            for lookup in lookups:
                # Query param key: ``field`` for exact, ``field__lookup``
                # otherwise
                if lookup == "exact":
                    param_key = field_name
                else:
                    param_key = f"{field_name}__{lookup}"

                raw = self._params.get(param_key)
                if raw is None:
                    # Also check with Django-style double underscore in the
                    # query string itself (e.g., ?price__gte=10)
                    raw = self._params.get(param_key)
                if raw is None:
                    continue

                # Custom filter method?
                custom = getattr(self, f"filter_{field_name}", None)
                if custom is not None and lookup == "exact":
                    extra = custom(raw)
                    if isinstance(extra, dict):
                        clauses.update(extra)
                    continue

                coerced = _coerce_value(raw, lookup)
                if lookup == "exact":
                    clauses[field_name] = coerced
                else:
                    clauses[f"{field_name}__{lookup}"] = coerced

        return clauses

    def filter_list(self, data: List[Any]) -> List[Any]:
        """Convenience: parse + apply to an in-memory list."""
        clauses = self.parse()
        return apply_filters_to_list(data, clauses)

    async def filter_queryset(self, queryset: Any) -> Any:
        """
        Apply parsed clauses to an Aquilia QuerySet (Q object).

        Returns the filtered Q with ``.filter(**clauses)`` applied.
        """
        clauses = self.parse()
        if clauses:
            return queryset.filter(**clauses)
        return queryset


# ═══════════════════════════════════════════════════════════════════════════
#  Base filter backend protocol
# ═══════════════════════════════════════════════════════════════════════════

class BaseFilterBackend:
    """
    Abstract base for pluggable filter backends.

    Subclass and implement ``filter_data`` / ``filter_queryset``.
    The controller engine calls these in sequence.
    """

    def filter_data(
        self,
        data: List[Any],
        request: Any,
        **options: Any,
    ) -> List[Any]:
        """Filter an in-memory list. Return the filtered list."""
        return data

    async def filter_queryset(
        self,
        queryset: Any,
        request: Any,
        **options: Any,
    ) -> Any:
        """Filter an ORM queryset. Return the filtered queryset."""
        return queryset


# ═══════════════════════════════════════════════════════════════════════════
#  Built-in filter backends
# ═══════════════════════════════════════════════════════════════════════════

class SearchFilter(BaseFilterBackend):
    """
    Text search across multiple fields.

    Query parameter: ``?search=<term>``

    Usage on a route decorator::

        @GET("/", search_fields=["name", "description", "sku"])
        async def list_products(self, ctx): ...

    ORM mode:
        Builds a Q-node OR chain: ``name__icontains=term | desc__icontains=term``

    List mode:
        In-memory case-insensitive substring match.
    """

    search_param: str = "search"

    def _get_search_term(self, request: Any) -> str:
        qp = request.query_params if hasattr(request, "query_params") else {}
        return (qp.get(self.search_param) or "").strip()

    def filter_data(
        self,
        data: List[Any],
        request: Any,
        *,
        search_fields: Optional[List[str]] = None,
        **options: Any,
    ) -> List[Any]:
        term = self._get_search_term(request)
        if not term or not search_fields:
            return data
        return apply_search_to_list(data, term, search_fields)

    async def filter_queryset(
        self,
        queryset: Any,
        request: Any,
        *,
        search_fields: Optional[List[str]] = None,
        **options: Any,
    ) -> Any:
        term = self._get_search_term(request)
        if not term or not search_fields:
            return queryset

        # Build icontains Q-node chain (OR)
        try:
            from aquilia.models.query import QNode, QCombination
            nodes = [QNode(**{f"{f}__icontains": term}) for f in search_fields]
            combined = nodes[0]
            for n in nodes[1:]:
                combined = combined | n
            return queryset.apply_q(combined)
        except (ImportError, Exception):
            # Fallback — fetch all and filter in-memory
            items = await queryset.all()
            dicts = [i.to_dict() if hasattr(i, "to_dict") else i for i in items]
            return apply_search_to_list(dicts, term, search_fields)


class OrderingFilter(BaseFilterBackend):
    """
    Dynamic field ordering via ``?ordering=<field>`` query parameter.

    Multiple fields: ``?ordering=-price,name``

    Usage::

        @GET("/", ordering_fields=["price", "created_at", "name"])
        async def list_products(self, ctx): ...
    """

    ordering_param: str = "ordering"

    def _get_ordering(
        self, request: Any, *, ordering_fields: Optional[List[str]] = None,
    ) -> List[str]:
        qp = request.query_params if hasattr(request, "query_params") else {}
        raw = (qp.get(self.ordering_param) or "").strip()
        if not raw:
            return []
        requested = [f.strip() for f in raw.split(",") if f.strip()]
        if not ordering_fields:
            return requested
        # Whitelist
        allowed = set(ordering_fields)
        return [f for f in requested if f.lstrip("-") in allowed]

    def filter_data(
        self,
        data: List[Any],
        request: Any,
        *,
        ordering_fields: Optional[List[str]] = None,
        **options: Any,
    ) -> List[Any]:
        ordering = self._get_ordering(request, ordering_fields=ordering_fields)
        if not ordering:
            return data
        return apply_ordering_to_list(data, ordering)

    async def filter_queryset(
        self,
        queryset: Any,
        request: Any,
        *,
        ordering_fields: Optional[List[str]] = None,
        **options: Any,
    ) -> Any:
        ordering = self._get_ordering(request, ordering_fields=ordering_fields)
        if not ordering:
            return queryset
        return queryset.order(*ordering)


# ═══════════════════════════════════════════════════════════════════════════
#  Convenience entry point for the engine
# ═══════════════════════════════════════════════════════════════════════════

async def filter_queryset(
    queryset: Any,
    request: Any,
    *,
    filterset_class: Optional[Type[FilterSet]] = None,
    filterset_fields: Optional[Union[List[str], Dict[str, List[str]]]] = None,
    search_fields: Optional[List[str]] = None,
    ordering_fields: Optional[List[str]] = None,
) -> Any:
    """
    One-shot convenience: apply FilterSet + SearchFilter + OrderingFilter
    to an Aquilia Q queryset.
    """
    qs = queryset

    # 1. FilterSet
    if filterset_class is not None:
        fs = filterset_class(request=request)
        qs = await fs.filter_queryset(qs)
    elif filterset_fields is not None:
        # Build an ad-hoc FilterSet from a field list/dict
        if isinstance(filterset_fields, (list, tuple)):
            field_dict = {f: ["exact"] for f in filterset_fields}
        else:
            field_dict = dict(filterset_fields)
        adhoc = type("_AdhocFilter", (FilterSet,), {"Meta": type("Meta", (), {"fields": field_dict})})
        fs = adhoc(request=request)
        qs = await fs.filter_queryset(qs)

    # 2. Search
    if search_fields:
        sf = SearchFilter()
        qs = await sf.filter_queryset(qs, request, search_fields=search_fields)

    # 3. Ordering
    if ordering_fields:
        of = OrderingFilter()
        qs = await of.filter_queryset(qs, request, ordering_fields=ordering_fields)

    return qs


def filter_data(
    data: List[Any],
    request: Any,
    *,
    filterset_class: Optional[Type[FilterSet]] = None,
    filterset_fields: Optional[Union[List[str], Dict[str, List[str]]]] = None,
    search_fields: Optional[List[str]] = None,
    ordering_fields: Optional[List[str]] = None,
) -> List[Any]:
    """
    One-shot convenience: apply FilterSet + SearchFilter + OrderingFilter
    to an in-memory list of dicts/objects.
    """
    result = data

    # 1. FilterSet
    if filterset_class is not None:
        fs = filterset_class(request=request)
        result = fs.filter_list(result)
    elif filterset_fields is not None:
        if isinstance(filterset_fields, (list, tuple)):
            field_dict = {f: ["exact"] for f in filterset_fields}
        else:
            field_dict = dict(filterset_fields)
        _Meta = type("Meta", (), {"fields": field_dict})
        adhoc = type("_AdhocFilter", (FilterSet,), {"Meta": _Meta})
        fs = adhoc(request=request)
        result = fs.filter_list(result)

    # 2. Search
    if search_fields:
        sf = SearchFilter()
        result = sf.filter_data(result, request, search_fields=search_fields)

    # 3. Ordering
    if ordering_fields:
        of = OrderingFilter()
        result = of.filter_data(result, request, ordering_fields=ordering_fields)

    return result
