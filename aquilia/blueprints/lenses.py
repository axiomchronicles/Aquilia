"""
Aquilia Blueprint Lenses — depth-controlled relational views.

A Lens lets a Blueprint expose related model data through another
Blueprint, with cycle detection, depth limits, and projection selection.

Naming:
    - "Lens" because it provides a focused *view* into related data,
      like an optical lens adjusting what you see.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TYPE_CHECKING

from .facets import Facet, UNSET
from .exceptions import LensDepthFault, LensCycleFault

if TYPE_CHECKING:
    from .core import Blueprint


__all__ = ["Lens"]


class Lens(Facet):
    """
    A relational facet that views related data through another Blueprint.

    Features:
        - Depth control: limits how deep nested Lenses resolve
        - Cycle detection: prevents infinite recursion
        - Projection selection: use a named projection of the target Blueprint
        - Many: handles to-many relations (returns list)

    Usage::

        class OrderBlueprint(Blueprint):
            customer = Lens(UserBlueprint["public"])
            items = Lens(OrderItemBlueprint, many=True, depth=2)

    Args:
        target: Blueprint class (or ProjectedBlueprint from subscript).
        many: If True, expect an iterable and mold each item.
        depth: Maximum nesting depth (default 3).
        source: Model attribute for the related object(s).
        read_only: Lenses are read-only by default.
    """

    _type_name = "object"

    def __init__(
        self,
        target: Type[Blueprint] | _ProjectedRef | None = None,
        *,
        many: bool = False,
        depth: int = 3,
        projection: str | None = None,
        **kwargs,
    ):
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

        # Handle ProjectedRef (from Blueprint["projection_name"])
        if isinstance(target, _ProjectedRef):
            self._target_cls = target.blueprint_cls
            self._projection = target.projection
        else:
            self._target_cls = target
            self._projection = projection

        self.many = many
        self.max_depth = depth

    @property
    def target(self) -> Type[Blueprint] | None:
        return self._target_cls

    def bind(self, name: str, blueprint: Blueprint) -> None:
        super().bind(name, blueprint)
        # If source not explicitly set, try to match model FK attribute
        if self.source == name and hasattr(blueprint, '_spec'):
            spec = blueprint._spec
            if spec and spec.model:
                model_fields = getattr(spec.model, '_fields', {})
                if name in model_fields:
                    # Check if it's a relation field
                    mf = model_fields[name]
                    if hasattr(mf, 'to'):
                        # It's a FK/M2M — source is the attribute name
                        pass

    def mold(self, value: Any, *, _depth: int = 0, _seen: set | None = None) -> Any:
        """
        Mold related data through the target Blueprint.

        Args:
            value: Related model instance(s)
            _depth: Current nesting depth (internal)
            _seen: Set of Blueprint class ids already in the chain (cycle detection)
        """
        if value is None:
            return None

        if _seen is None:
            _seen = set()

        # Cycle detection
        target_id = id(self._target_cls)
        if target_id in _seen:
            raise LensCycleFault(
                [cls.__name__ for cls in _seen] + [self._target_cls.__name__]
                if hasattr(self._target_cls, '__name__') else ["<unknown>"]
            )

        # Depth check
        if _depth >= self.max_depth:
            # At max depth, return PK only
            if self.many:
                return [self._pk_fallback(item) for item in value]
            return self._pk_fallback(value)

        new_seen = _seen | {target_id}

        if self.many:
            items = value if not hasattr(value, '__aiter__') else value
            if hasattr(items, 'all'):
                # It's a manager/queryset — can't iterate sync
                # Return empty; async path should be used
                return []
            return [
                self._mold_single(item, _depth=_depth + 1, _seen=new_seen)
                for item in items
            ]
        return self._mold_single(value, _depth=_depth + 1, _seen=new_seen)

    def _mold_single(self, instance: Any, *, _depth: int, _seen: set) -> Dict[str, Any]:
        """Mold a single related instance through the target Blueprint."""
        if self._target_cls is None:
            # No target blueprint — fall back to dict/PK
            return self._pk_fallback(instance)

        bp = self._target_cls(instance=instance, projection=self._projection)
        return bp.to_dict(_depth=_depth, _seen=_seen)

    @staticmethod
    def _pk_fallback(instance: Any) -> Any:
        """Fall back to PK when depth is exceeded or no target Blueprint."""
        if instance is None:
            return None
        if isinstance(instance, dict):
            return instance.get("id", instance.get("pk"))
        pk = getattr(instance, "pk", None)
        if pk is not None:
            return pk
        return getattr(instance, "id", None)

    def extract(self, instance: Any) -> Any:
        """Extract related data from the instance."""
        if self.source == "*":
            return instance

        # Handle dotted sources
        parts = self.source.split(".") if self.source else []
        obj = instance
        for part in parts:
            if obj is None:
                return None
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
        return obj

    def to_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema with $ref for the target Blueprint."""
        if self._target_cls is None:
            return {"type": "object"}

        ref_name = self._target_cls.__name__
        if self._projection:
            ref_name = f"{ref_name}_{self._projection}"

        if self.many:
            return {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{ref_name}"},
            }
        return {"$ref": f"#/components/schemas/{ref_name}"}


class _ProjectedRef:
    """
    Internal: holds a Blueprint class + projection name.

    Created by ``Blueprint["projection_name"]`` subscript syntax.
    """

    __slots__ = ("blueprint_cls", "projection")

    def __init__(self, blueprint_cls: Type[Blueprint], projection: str):
        self.blueprint_cls = blueprint_cls
        self.projection = projection

    def __repr__(self) -> str:
        return f"{self.blueprint_cls.__name__}[{self.projection!r}]"
