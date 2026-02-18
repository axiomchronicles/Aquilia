"""
Products Module Manifest — Catalog, categories, reviews & inventory.

Defines complete module configuration:
- Services: ProductService, CategoryService
- Controllers: ProductController, CategoryController
- Fault domain: PRODUCTS
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="products",
    version="1.0.0",
    description="Product catalog, categories, reviews & inventory management",
    author="nexus-engineering@nexus-platform.com",
    tags=["products", "catalog", "inventory"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.products.services:CategoryService",
        "modules.products.services:ProductService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.products.controllers:CategoryController",
        "modules.products.controllers:ProductController",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/products",
    base_path="modules.products",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="PRODUCTS",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="product_reviews", enabled=True),
        FeatureConfig(name="product_variants", enabled=True),
        FeatureConfig(name="advanced_search", enabled=False),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=["users"],
)


__all__ = ["manifest"]
