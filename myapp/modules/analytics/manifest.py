"""
Analytics Module Manifest — Business intelligence & ML recommendations.

Defines complete module configuration:
- Services: AnalyticsService, RecommendationService
- Controllers: AnalyticsController, RecommendationController
- Fault domain: ANALYTICS
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="analytics",
    version="1.0.0",
    description="Business intelligence, KPI dashboards & ML-powered recommendations",
    author="nexus-engineering@nexus-platform.com",
    tags=["analytics", "ml", "recommendations", "dashboard"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.analytics.services:AnalyticsService",
        "modules.analytics.services:RecommendationService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.analytics.controllers:AnalyticsController",
        "modules.analytics.controllers:RecommendationController",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/analytics",
    base_path="modules.analytics",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="ANALYTICS",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="ml_recommendations", enabled=True),
        FeatureConfig(name="live_dashboard_sse", enabled=True),
        FeatureConfig(name="revenue_forecasting", enabled=False),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=["users", "products", "orders"],
)


__all__ = ["manifest"]
