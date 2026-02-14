"""
Aquilia Field Lookups — extensible lookup system for query filters.

Lookups define how field__lookup=value translates to SQL predicates.
Each Lookup knows its SQL operator, how to prepare the RHS, and
whether it is case-sensitive.

Usage:
    from aquilia.models.fields.lookups import Exact, IExact, Contains

    # Lookups are automatically resolved by the Q query builder.
    # Custom lookups can be registered:
    Lookup.register("year", YearLookup)
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type


__all__ = [
    "Lookup",
    "Exact",
    "IExact",
    "Contains",
    "IContains",
    "StartsWith",
    "IStartsWith",
    "EndsWith",
    "IEndsWith",
    "In",
    "Gt",
    "Gte",
    "Lt",
    "Lte",
    "IsNull",
    "Range",
    "Regex",
    "IRegex",
    "Date",
    "Year",
    "Month",
    "Day",
    "lookup_registry",
    "resolve_lookup",
]


class Lookup:
    """
    Base class for field lookups.

    Each lookup knows:
    - lookup_name: the name used in filter(field__lookup=val)
    - sql_operator: the SQL comparison operator
    - How to format the LHS / RHS of the comparison
    """

    lookup_name: ClassVar[str] = ""
    sql_operator: ClassVar[str] = "="
    bilateral: ClassVar[bool] = False  # Apply transform to both sides

    def __init__(self, field_name: str, value: Any):
        self.field_name = field_name
        self.value = value

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        """Return (sql_clause, params) for this lookup."""
        lhs = f'"{self.field_name}"'
        return f"{lhs} {self.sql_operator} ?", [self.value]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.field_name}={self.value!r}>"


class Exact(Lookup):
    lookup_name = "exact"
    sql_operator = "="


class IExact(Lookup):
    """Case-insensitive exact match."""
    lookup_name = "iexact"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'LOWER("{self.field_name}") = LOWER(?)', [self.value]


class Contains(Lookup):
    lookup_name = "contains"
    sql_operator = "LIKE"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'"{self.field_name}" LIKE ?', [f"%{self.value}%"]


class IContains(Lookup):
    """Case-insensitive contains."""
    lookup_name = "icontains"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'LOWER("{self.field_name}") LIKE LOWER(?)', [f"%{self.value}%"]


class StartsWith(Lookup):
    lookup_name = "startswith"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'"{self.field_name}" LIKE ?', [f"{self.value}%"]


class IStartsWith(Lookup):
    """Case-insensitive startswith."""
    lookup_name = "istartswith"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'LOWER("{self.field_name}") LIKE LOWER(?)', [f"{self.value}%"]


class EndsWith(Lookup):
    lookup_name = "endswith"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'"{self.field_name}" LIKE ?', [f"%{self.value}"]


class IEndsWith(Lookup):
    """Case-insensitive endswith."""
    lookup_name = "iendswith"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'LOWER("{self.field_name}") LIKE LOWER(?)', [f"%{self.value}"]


class In(Lookup):
    lookup_name = "in"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if not self.value:
            return "1 = 0", []  # Always false
        placeholders = ", ".join("?" for _ in self.value)
        return f'"{self.field_name}" IN ({placeholders})', list(self.value)


class Gt(Lookup):
    lookup_name = "gt"
    sql_operator = ">"


class Gte(Lookup):
    lookup_name = "gte"
    sql_operator = ">="


class Lt(Lookup):
    lookup_name = "lt"
    sql_operator = "<"


class Lte(Lookup):
    lookup_name = "lte"
    sql_operator = "<="


class IsNull(Lookup):
    lookup_name = "isnull"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if self.value:
            return f'"{self.field_name}" IS NULL', []
        return f'"{self.field_name}" IS NOT NULL', []


class Range(Lookup):
    """Filter within a range: field__range=(lo, hi)."""
    lookup_name = "range"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        lo, hi = self.value
        return f'"{self.field_name}" BETWEEN ? AND ?', [lo, hi]


class Regex(Lookup):
    """Filter by regex (PostgreSQL: ~, SQLite: REGEXP if loaded)."""
    lookup_name = "regex"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'"{self.field_name}" ~ ?', [self.value]
        # SQLite: requires REGEXP function to be loaded
        return f'"{self.field_name}" REGEXP ?', [self.value]


class IRegex(Lookup):
    """Case-insensitive regex."""
    lookup_name = "iregex"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'"{self.field_name}" ~* ?', [self.value]
        return f'LOWER("{self.field_name}") REGEXP LOWER(?)', [self.value]


class Date(Lookup):
    """Extract date from datetime and compare."""
    lookup_name = "date"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'("{self.field_name}")::date = ?', [self.value]
        return f'DATE("{self.field_name}") = ?', [str(self.value)]


class Year(Lookup):
    """Extract year and compare."""
    lookup_name = "year"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'EXTRACT(YEAR FROM "{self.field_name}") = ?', [self.value]
        return f'CAST(STRFTIME("%Y", "{self.field_name}") AS INTEGER) = ?', [self.value]


class Month(Lookup):
    """Extract month and compare."""
    lookup_name = "month"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'EXTRACT(MONTH FROM "{self.field_name}") = ?', [self.value]
        return f'CAST(STRFTIME("%m", "{self.field_name}") AS INTEGER) = ?', [self.value]


class Day(Lookup):
    """Extract day and compare."""
    lookup_name = "day"

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "postgresql":
            return f'EXTRACT(DAY FROM "{self.field_name}") = ?', [self.value]
        return f'CAST(STRFTIME("%d", "{self.field_name}") AS INTEGER) = ?', [self.value]


# ── Lookup Registry ──────────────────────────────────────────────────────────

_REGISTRY: Dict[str, Type[Lookup]] = {}


def _register_builtins() -> None:
    """Register all built-in lookups."""
    for cls in [
        Exact, IExact, Contains, IContains, StartsWith, IStartsWith,
        EndsWith, IEndsWith, In, Gt, Gte, Lt, Lte, IsNull, Range,
        Regex, IRegex, Date, Year, Month, Day,
    ]:
        _REGISTRY[cls.lookup_name] = cls


_register_builtins()


def lookup_registry() -> Dict[str, Type[Lookup]]:
    """Return a copy of the lookup registry."""
    return dict(_REGISTRY)


def register_lookup(name: str, cls: Type[Lookup]) -> None:
    """Register a custom lookup type."""
    _REGISTRY[name] = cls


def resolve_lookup(field_name: str, lookup_name: str, value: Any) -> Lookup:
    """
    Resolve a lookup name to a Lookup instance.

    Args:
        field_name: The database field/column name
        lookup_name: The lookup suffix (e.g., "gt", "contains")
        value: The comparison value

    Returns:
        Lookup instance

    Raises:
        ValueError: If lookup_name is not registered
    """
    cls = _REGISTRY.get(lookup_name)
    if cls is None:
        raise ValueError(
            f"Unknown lookup '{lookup_name}'. Available: {sorted(_REGISTRY.keys())}"
        )
    return cls(field_name, value)
