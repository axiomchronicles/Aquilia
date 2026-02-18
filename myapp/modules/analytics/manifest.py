"""
CRM Analytics Module Manifest
===============================

Provides the main CRM dashboard with KPIs, charts,
pipeline analytics, revenue tracking, and team performance.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="analytics",
    version="1.0.0",
    description="CRM analytics and dashboard module",
    services=[
        "modules.analytics.services:AnalyticsService",
    ],
    controllers=[
        "modules.analytics.controllers:DashboardController",
    ],
    route_prefix="/dashboard",
    base_path="modules.analytics",
    faults=FaultHandlingConfig(
        default_domain="ANALYTICS",
        strategy="propagate",
    ),
    depends_on=["crm_auth", "contacts", "companies", "deals", "tasks"],
    tags=["analytics", "crm", "dashboard"],
)
