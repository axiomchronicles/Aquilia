"""
Aquilia Expression System — F(), Value(), RawSQL() for query expressions.

Expressions are composable objects that can be used in filter(), annotate(),
aggregate(), and order_by() calls on QuerySets.

Usage:
    from aquilia.models.expression import F, Value, RawSQL

    # Increment a field
    await Post.query().filter(id=1).update(views=F("views") + 1)

    # Annotate with computed value
    results = await Product.query().annotate(
        discounted=F("price") * Value(0.9)
    ).all()
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple, Union


__all__ = [
    "Expression",
    "F",
    "Value",
    "RawSQL",
    "Col",
    "Star",
    "Combinable",
    "CombinedExpression",
    "When",
    "Case",
    "Subquery",
    "Exists",
    "OuterRef",
    "ExpressionWrapper",
    "Func",
    "Cast",
    "Coalesce",
    "Greatest",
    "Least",
    "NullIf",
]


class Combinable:
    """
    Base class providing arithmetic operators for expressions.

    Supports +, -, *, /, %, and & (bitwise AND), | (bitwise OR).
    """

    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    BITAND = "&"
    BITOR = "|"

    def __add__(self, other):
        return CombinedExpression(self, self.ADD, other)

    def __radd__(self, other):
        return CombinedExpression(Value(other), self.ADD, self)

    def __sub__(self, other):
        return CombinedExpression(self, self.SUB, other)

    def __rsub__(self, other):
        return CombinedExpression(Value(other), self.SUB, self)

    def __mul__(self, other):
        return CombinedExpression(self, self.MUL, other)

    def __rmul__(self, other):
        return CombinedExpression(Value(other), self.MUL, self)

    def __truediv__(self, other):
        return CombinedExpression(self, self.DIV, other)

    def __rtruediv__(self, other):
        return CombinedExpression(Value(other), self.DIV, self)

    def __mod__(self, other):
        return CombinedExpression(self, self.MOD, other)

    def __rmod__(self, other):
        return CombinedExpression(Value(other), self.MOD, self)

    def __neg__(self):
        return CombinedExpression(Value(0), self.SUB, self)


class Expression(Combinable):
    """
    Base class for all SQL expressions.

    Every expression must implement:
        as_sql() → (sql_string, params_list)
    """

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        """
        Render expression to SQL with bind parameters.

        Returns:
            Tuple of (sql_string, params_list)
        """
        raise NotImplementedError

    def resolve_expression(self, query=None, allow_joins=True):
        """Hook for QuerySet to resolve the expression in context."""
        return self


class F(Expression):
    """
    Reference to a model field in an expression context.

    Usage:
        F("price")         → "price"
        F("price") + 10    → "price" + ?  [10]
        F("views") + 1     → "views" + ?  [1]
    """

    def __init__(self, name: str):
        self.name = name

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'"{self.name}"', []

    def __repr__(self) -> str:
        return f"F({self.name!r})"


class Value(Expression):
    """
    Wraps a literal Python value as an SQL expression.

    Usage:
        Value(42)      → ? [42]
        Value("hello") → ? ["hello"]
        Value(None)    → NULL
    """

    def __init__(self, value: Any):
        self.value = value

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if self.value is None:
            return "NULL", []
        return "?", [self.value]

    def __repr__(self) -> str:
        return f"Value({self.value!r})"


class RawSQL(Expression):
    """
    Raw SQL expression — use with caution.

    Params are bound using the standard ? placeholder.

    Usage:
        RawSQL("COALESCE(price, 0)")
        RawSQL("price * ?", [1.1])
    """

    def __init__(self, sql: str, params: Optional[List[Any]] = None):
        self.sql = sql
        self.params = params or []

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return self.sql, list(self.params)

    def __repr__(self) -> str:
        return f"RawSQL({self.sql!r})"


class Col(Expression):
    """
    Reference to a specific table.column in a multi-table query.

    Usage:
        Col("users", "id")  → "users"."id"
    """

    def __init__(self, table: str, column: str):
        self.table = table
        self.column = column

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return f'"{self.table}"."{self.column}"', []

    def __repr__(self) -> str:
        return f"Col({self.table!r}, {self.column!r})"


class Star(Expression):
    """Represents * (all columns)."""

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return "*", []


class CombinedExpression(Expression):
    """
    Represents two expressions combined with an operator.

    Created by F("x") + 1, F("x") * F("y"), etc.
    """

    def __init__(
        self,
        lhs: Union[Expression, Any],
        connector: str,
        rhs: Union[Expression, Any],
    ):
        if not isinstance(lhs, Expression):
            lhs = Value(lhs)
        if not isinstance(rhs, Expression):
            rhs = Value(rhs)
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        lhs_sql, lhs_params = self.lhs.as_sql(dialect)
        rhs_sql, rhs_params = self.rhs.as_sql(dialect)
        sql = f"({lhs_sql} {self.connector} {rhs_sql})"
        return sql, lhs_params + rhs_params

    def __repr__(self) -> str:
        return f"CombinedExpression({self.lhs!r} {self.connector} {self.rhs!r})"


# ── Advanced Expression Types ────────────────────────────────────────────────


class When(Expression):
    """
    Conditional WHEN clause for use inside Case().

    Usage:
        When(condition={"status": "active"}, then=Value(1))
        When(condition="age > 18", then=Value("adult"))
    """

    def __init__(
        self,
        condition: Any = None,
        then: Any = None,
        **lookups: Any,
    ):
        self.condition = condition
        self.lookups = lookups
        self.then = then if isinstance(then, Expression) else Value(then)

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        params: List[Any] = []

        # Build condition
        if isinstance(self.condition, str):
            cond_sql = self.condition
        elif isinstance(self.condition, dict):
            parts = []
            for key, val in self.condition.items():
                parts.append(f'"{key}" = ?')
                params.append(val)
            cond_sql = " AND ".join(parts)
        elif self.lookups:
            parts = []
            for key, val in self.lookups.items():
                if "__" in key:
                    field, op = key.rsplit("__", 1)
                    op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "ne": "!="}
                    sql_op = op_map.get(op, "=")
                    parts.append(f'"{field}" {sql_op} ?')
                else:
                    parts.append(f'"{key}" = ?')
                params.append(val)
            cond_sql = " AND ".join(parts)
        elif isinstance(self.condition, Expression):
            cond_sql, cond_params = self.condition.as_sql(dialect)
            params.extend(cond_params)
        else:
            cond_sql = "1=1"

        then_sql, then_params = self.then.as_sql(dialect)
        params.extend(then_params)

        return f"WHEN {cond_sql} THEN {then_sql}", params

    def __repr__(self) -> str:
        return f"When({self.condition}, then={self.then})"


class Case(Expression):
    """
    SQL CASE expression.

    Usage:
        Case(
            When(condition={"status": "active"}, then=Value("Active")),
            When(condition={"status": "inactive"}, then=Value("Inactive")),
            default=Value("Unknown"),
        )
    """

    def __init__(self, *cases: When, default: Any = None):
        self.cases = cases
        self.default = default if isinstance(default, Expression) else Value(default) if default is not None else None

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        params: List[Any] = []
        parts = ["CASE"]

        for when in self.cases:
            when_sql, when_params = when.as_sql(dialect)
            parts.append(f"  {when_sql}")
            params.extend(when_params)

        if self.default is not None:
            default_sql, default_params = self.default.as_sql(dialect)
            parts.append(f"  ELSE {default_sql}")
            params.extend(default_params)

        parts.append("END")
        return " ".join(parts), params

    def __repr__(self) -> str:
        return f"Case({len(self.cases)} cases)"


class Subquery(Expression):
    """
    Wraps a query builder as a subquery expression.

    Usage:
        sub = Subquery(Order.query().filter(user_id=OuterRef("id")).values("total").limit(1))
        users = await User.query().annotate(latest_order=sub).all()
    """

    def __init__(self, queryset: Any, output_field: Any = None):
        self.queryset = queryset
        self.output_field = output_field

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if hasattr(self.queryset, "_build_select"):
            sql, params = self.queryset._build_select()
            return f"({sql})", params
        # Raw SQL fallback
        return f"({self.queryset})", []

    def __repr__(self) -> str:
        return f"Subquery({self.queryset!r})"


class Exists(Expression):
    """
    SQL EXISTS() expression.

    Usage:
        has_orders = Exists(Order.query().filter(user_id=OuterRef("id")))
        users = await User.query().annotate(has_orders=has_orders).all()
    """

    def __init__(self, queryset: Any):
        self.queryset = queryset

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if hasattr(self.queryset, "_build_select"):
            sql, params = self.queryset._build_select()
            return f"EXISTS ({sql})", params
        return f"EXISTS ({self.queryset})", []

    def __repr__(self) -> str:
        return f"Exists({self.queryset!r})"


class OuterRef(F):
    """
    Reference to a field from the outer query (for use in Subquery/Exists).

    In SQL this just renders as a quoted field name — the resolution happens
    contextually when the subquery is embedded.
    """

    def __repr__(self) -> str:
        return f"OuterRef({self.name!r})"


class ExpressionWrapper(Expression):
    """
    Wraps an expression with an explicit output type.

    Useful when combining F() objects where the result type differs from inputs.

    Usage:
        ExpressionWrapper(F("price") * F("quantity"), output_field=DecimalField())
    """

    def __init__(self, expression: Expression, output_field: Any = None):
        self.expression = expression
        self.output_field = output_field

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        return self.expression.as_sql(dialect)

    def __repr__(self) -> str:
        return f"ExpressionWrapper({self.expression!r})"


class Func(Expression):
    """
    Generic SQL function call.

    Usage:
        Func("UPPER", F("name"))           → UPPER("name")
        Func("COALESCE", F("val"), Value(0)) → COALESCE("val", ?)
    """

    def __init__(self, function: str, *args: Any):
        self.function = function
        self.args = [a if isinstance(a, Expression) else Value(a) for a in args]

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        params: List[Any] = []
        arg_parts: List[str] = []
        for arg in self.args:
            arg_sql, arg_params = arg.as_sql(dialect)
            arg_parts.append(arg_sql)
            params.extend(arg_params)
        return f"{self.function}({', '.join(arg_parts)})", params

    def __repr__(self) -> str:
        return f"Func({self.function!r}, {self.args!r})"


class Cast(Expression):
    """
    SQL CAST() expression.

    Usage:
        Cast(F("price"), "INTEGER")  → CAST("price" AS INTEGER)
    """

    def __init__(self, expression: Any, output_type: str):
        self.expression = expression if isinstance(expression, Expression) else F(expression) if isinstance(expression, str) else Value(expression)
        self.output_type = output_type

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        expr_sql, params = self.expression.as_sql(dialect)
        return f"CAST({expr_sql} AS {self.output_type})", params

    def __repr__(self) -> str:
        return f"Cast({self.expression!r}, {self.output_type!r})"


class Coalesce(Func):
    """
    SQL COALESCE() — returns first non-NULL argument.

    Usage:
        Coalesce(F("nickname"), F("name"), Value("Anonymous"))
    """

    def __init__(self, *args: Any):
        super().__init__("COALESCE", *args)


class Greatest(Func):
    """
    SQL GREATEST() (MAX on SQLite) — returns largest argument.

    Usage:
        Greatest(F("price"), F("min_price"), Value(0))
    """

    def __init__(self, *args: Any):
        super().__init__("GREATEST", *args)

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "sqlite":
            # SQLite uses MAX() for this purpose
            params: List[Any] = []
            arg_parts: List[str] = []
            for arg in self.args:
                arg_sql, arg_params = arg.as_sql(dialect)
                arg_parts.append(arg_sql)
                params.extend(arg_params)
            return f"MAX({', '.join(arg_parts)})", params
        return super().as_sql(dialect)


class Least(Func):
    """
    SQL LEAST() (MIN on SQLite) — returns smallest argument.

    Usage:
        Least(F("price"), F("max_price"), Value(100))
    """

    def __init__(self, *args: Any):
        super().__init__("LEAST", *args)

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        if dialect == "sqlite":
            # SQLite uses MIN() for this purpose
            params: List[Any] = []
            arg_parts: List[str] = []
            for arg in self.args:
                arg_sql, arg_params = arg.as_sql(dialect)
                arg_parts.append(arg_sql)
                params.extend(arg_params)
            return f"MIN({', '.join(arg_parts)})", params
        return super().as_sql(dialect)


class NullIf(Expression):
    """
    SQL NULLIF() — returns NULL if expression1 equals expression2.

    Usage:
        NullIf(F("value"), Value(0))  → NULLIF("value", ?)
    """

    def __init__(self, expression1: Any, expression2: Any):
        self.expr1 = expression1 if isinstance(expression1, Expression) else Value(expression1)
        self.expr2 = expression2 if isinstance(expression2, Expression) else Value(expression2)

    def as_sql(self, dialect: str = "sqlite") -> Tuple[str, List[Any]]:
        sql1, params1 = self.expr1.as_sql(dialect)
        sql2, params2 = self.expr2.as_sql(dialect)
        return f"NULLIF({sql1}, {sql2})", params1 + params2

    def __repr__(self) -> str:
        return f"NullIf({self.expr1!r}, {self.expr2!r})"
