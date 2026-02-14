"""
Products Module - Manifest

Showcases pure Python Model registration, effect providers, and feature flags.
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    FeatureConfig,
    LifecycleConfig,
)

manifest = AppManifest(
    name="products",
    version="0.1.0",
    description="Product catalog with pure Python models, reviews, and stock management",
    author="team@aquilia.dev",
    tags=["products", "catalog", "models"],

    services=[
        "modules.products.services:ProductRepository",
        "modules.products.services:ProductService",
    ],
    controllers=[
        "modules.products.controllers:ProductsController",
    ],

    route_prefix="/products",
    base_path="modules.products",

    faults=FaultHandlingConfig(
        default_domain="PRODUCTS",
        strategy="propagate",
        handlers=[],
    ),

    features=[
        FeatureConfig(name="product_reviews", enabled=True),
        FeatureConfig(name="stock_management", enabled=True),
        FeatureConfig(name="product_images", enabled=False),
    ],
)
