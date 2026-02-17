"""
Aquilia Blueprints — first-class model↔world contracts.

A Blueprint declares the contract between a Model and the outside world:
what the world sees (Facets), named subsets (Projections), how data
enters (Casts), how integrity is enforced (Seals), and how data is
written back (Imprints).

Quick Start::

    from aquilia.blueprints import Blueprint, Facet, Lens, Computed, Constant

    class ProductBlueprint(Blueprint):
        class Spec:
            model = Product
            projections = {
                "summary": ["id", "name", "price"],
                "detail": "__all__",
            }

    # Outbound: Model → dict
    bp = ProductBlueprint(instance=product)
    data = bp.data  # respects default projection

    # With projection:
    bp = ProductBlueprint(instance=product, projection="summary")
    data = bp.data

    # Inbound: dict → validated data
    bp = ProductBlueprint(data={"name": "Widget", "price": 9.99})
    if bp.is_sealed():
        product = await bp.imprint()

    # Route-level:
    @GET("/products", response_blueprint=ProductBlueprint["summary"])
    async def list_products():
        return await Product.objects.all()
"""

from .core import Blueprint, BlueprintMeta
from .facets import (
    # Base
    Facet,
    UNSET,
    # Text
    TextFacet,
    EmailFacet,
    URLFacet,
    SlugFacet,
    IPFacet,
    # Numeric
    IntFacet,
    FloatFacet,
    DecimalFacet,
    # Boolean
    BoolFacet,
    # Date/Time
    DateFacet,
    TimeFacet,
    DateTimeFacet,
    DurationFacet,
    UUIDFacet,
    # Structured
    ListFacet,
    DictFacet,
    JSONFacet,
    FileFacet,
    ChoiceFacet,
    # Special
    Computed,
    Constant,
    WriteOnly,
    ReadOnly,
    Hidden,
    Inject,
    # Utilities
    derive_facet,
    MODEL_FIELD_TO_FACET,
)
from .lenses import Lens
from .projections import ProjectionRegistry
from .exceptions import (
    BlueprintFault,
    CastFault,
    SealFault,
    ImprintFault,
    ProjectionFault,
    LensDepthFault,
    LensCycleFault,
    BLUEPRINT,
)
from .schema import generate_schema, generate_component_schemas
from .integration import (
    is_blueprint_class,
    is_projected_blueprint,
    resolve_blueprint_from_annotation,
    bind_blueprint_to_request,
    render_blueprint_response,
)

__all__ = [
    # Core
    "Blueprint",
    "BlueprintMeta",
    # Facets
    "Facet",
    "UNSET",
    "TextFacet",
    "EmailFacet",
    "URLFacet",
    "SlugFacet",
    "IPFacet",
    "IntFacet",
    "FloatFacet",
    "DecimalFacet",
    "BoolFacet",
    "DateFacet",
    "TimeFacet",
    "DateTimeFacet",
    "DurationFacet",
    "UUIDFacet",
    "ListFacet",
    "DictFacet",
    "JSONFacet",
    "FileFacet",
    "ChoiceFacet",
    "Computed",
    "Constant",
    "WriteOnly",
    "ReadOnly",
    "Hidden",
    "Inject",
    "derive_facet",
    "MODEL_FIELD_TO_FACET",
    # Lenses
    "Lens",
    # Projections
    "ProjectionRegistry",
    # Exceptions
    "BlueprintFault",
    "CastFault",
    "SealFault",
    "ImprintFault",
    "ProjectionFault",
    "LensDepthFault",
    "LensCycleFault",
    "BLUEPRINT",
    # Schema
    "generate_schema",
    "generate_component_schemas",
    # Integration
    "is_blueprint_class",
    "is_projected_blueprint",
    "resolve_blueprint_from_annotation",
    "bind_blueprint_to_request",
    "render_blueprint_response",
]
