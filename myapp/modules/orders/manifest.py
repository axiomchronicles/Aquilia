"""
Orders Module Manifest — Order processing, cart & fulfillment.

Defines complete module configuration:
- Services: OrderService (cart + checkout + lifecycle)
- Controllers: CartController, OrderController
- Fault domain: ORDERS
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="orders",
    version="1.0.0",
    description="Order processing, cart management & fulfillment pipeline",
    author="nexus-engineering@nexus-platform.com",
    tags=["orders", "cart", "checkout", "fulfillment"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.orders.services:OrderService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.orders.controllers:CartController",
        "modules.orders.controllers:OrderController",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/orders",
    base_path="modules.orders",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="ORDERS",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="order_tracking", enabled=True),
        FeatureConfig(name="auto_fulfillment", enabled=False),
        FeatureConfig(name="payment_gateway", enabled=False),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=["users", "products"],
)


__all__ = ["manifest"]
