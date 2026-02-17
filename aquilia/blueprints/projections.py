"""
Aquilia Blueprint Projections — named, reusable field subsets.

A Projection is a named subset of facets — like a SQL view over a model.
Instead of repeating ``fields = [...]`` everywhere, define projections
once and select them at route level.

Naming:
    - "Projection" because it projects a subset of the model's facets
      onto the output, like a database projection.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Sequence, Set, Type, TYPE_CHECKING

from .exceptions import ProjectionFault

if TYPE_CHECKING:
    from .core import Blueprint


__all__ = ["ProjectionRegistry"]


class ProjectionRegistry:
    """
    Manages named projections for a Blueprint class.

    Projections are defined in the Blueprint's ``Spec`` inner class::

        class Spec:
            model = Product
            projections = {
                "summary": ["id", "name", "price"],
                "detail": ["id", "name", "description", "price", "category"],
                "admin": "__all__",
            }
            default_projection = "detail"

    Special values:
        - ``"__all__"``: all non-write-only facets
        - ``"__minimal__"``: only PK + read-only facets

    A projection can also exclude fields with ``-`` prefix::

        projections = {
            "public": ["-password", "-email"],  # all except these
        }
    """

    def __init__(self):
        self._projections: Dict[str, FrozenSet[str]] = {}
        self._exclusion_projections: Dict[str, FrozenSet[str]] = {}
        self._default: str | None = None
        self._all_facets: FrozenSet[str] = frozenset()

    def configure(
        self,
        projections: Dict[str, str | List[str]] | None,
        default: str | None,
        all_facet_names: Set[str],
        write_only_names: Set[str],
    ) -> None:
        """
        Configure projections from Spec definitions.

        Args:
            projections: Mapping of name → field list (or "__all__")
            default: Name of the default projection
            all_facet_names: Complete set of facet names
            write_only_names: Set of write-only facet names
        """
        self._all_facets = frozenset(all_facet_names - write_only_names)

        if projections is None:
            # No projections defined — create a default "__all__" projection
            self._projections["__all__"] = self._all_facets
            self._default = "__all__"
            return

        for name, fields in projections.items():
            if fields == "__all__":
                self._projections[name] = self._all_facets
            elif fields == "__minimal__":
                # Just PK fields — resolved later by the Blueprint
                self._projections[name] = frozenset()  # placeholder
            elif isinstance(fields, (list, tuple)):
                # Check for exclusion syntax
                includes = []
                excludes = []
                for f in fields:
                    if isinstance(f, str) and f.startswith("-"):
                        excludes.append(f[1:])
                    else:
                        includes.append(f)

                if excludes and not includes:
                    # Exclusion-only: all facets minus excluded
                    self._projections[name] = frozenset(
                        self._all_facets - frozenset(excludes)
                    )
                elif includes:
                    self._projections[name] = frozenset(includes)
                else:
                    self._projections[name] = self._all_facets
            else:
                # Single field name or other
                self._projections[name] = frozenset([str(fields)])

        self._default = default or next(iter(self._projections), None)

    def resolve(self, name: str | None = None) -> FrozenSet[str]:
        """
        Resolve a projection name to a set of facet names.

        Args:
            name: Projection name (None = default)

        Returns:
            Frozen set of facet names in the projection.

        Raises:
            ProjectionFault: If the projection name doesn't exist.
        """
        if name is None:
            name = self._default
        if name is None:
            return self._all_facets

        if name not in self._projections:
            raise ProjectionFault(name, list(self._projections.keys()))

        return self._projections[name]

    @property
    def default_name(self) -> str | None:
        return self._default

    @property
    def available(self) -> List[str]:
        return list(self._projections.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._projections

    def __repr__(self) -> str:
        return f"<ProjectionRegistry projections={list(self._projections.keys())} default={self._default!r}>"
