"""
Aquilia Blueprint Schema — OpenAPI/JSON Schema generation.

Generates OpenAPI 3.x compatible schemas from Blueprint classes,
including per-projection schemas and $ref for Lens'd Blueprints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Blueprint


__all__ = ["generate_schema", "generate_component_schemas"]


def generate_schema(
    blueprint_cls: Type[Blueprint],
    *,
    projection: str | None = None,
    mode: str = "output",
) -> Dict[str, Any]:
    """
    Generate a JSON Schema for a Blueprint.

    Args:
        blueprint_cls: The Blueprint class
        projection: Named projection (None = default)
        mode: "output" (response) or "input" (request body)

    Returns:
        JSON Schema dict
    """
    return blueprint_cls.to_schema(projection=projection, mode=mode)


def generate_component_schemas(
    *blueprint_classes: Type[Blueprint],
    include_projections: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate OpenAPI component schemas for multiple Blueprints.

    Returns a dict suitable for OpenAPI's ``components.schemas`` section.

    Args:
        blueprint_classes: Blueprint classes to generate schemas for
        include_projections: If True, generate separate schemas for each projection
    """
    schemas: Dict[str, Dict[str, Any]] = {}

    for bp_cls in blueprint_classes:
        # Default schema
        name = bp_cls.__name__
        schemas[name] = bp_cls.to_schema(mode="output")
        schemas[f"{name}_Input"] = bp_cls.to_schema(mode="input")

        # Per-projection schemas
        if include_projections and hasattr(bp_cls, "_projections"):
            for proj_name in bp_cls._projections.available:
                if proj_name == "__all__":
                    continue
                key = f"{name}_{proj_name}"
                schemas[key] = bp_cls.to_schema(projection=proj_name, mode="output")

    return schemas
