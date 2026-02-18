"""
Admin Module Manifest — Dashboard, system management & bulk operations.

Defines complete module configuration:
- Services: AdminService
- Controllers: AdminDashboardController
- Fault domain: ADMIN
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="admin",
    version="1.0.0",
    description="Admin dashboard, system health monitoring & bulk operations",
    author="nexus-engineering@nexus-platform.com",
    tags=["admin", "dashboard", "management", "system"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.admin.services:AdminService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.admin.controllers:AdminDashboardController",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/admin",
    base_path="modules.admin",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="ADMIN",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="admin_dashboard_html", enabled=True),
        FeatureConfig(name="bulk_user_operations", enabled=True),
        FeatureConfig(name="system_diagnostics", enabled=True),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=["users", "products", "orders", "analytics"],
)


__all__ = ["manifest"]
