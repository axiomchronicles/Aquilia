"""
CRM Deals Module Manifest
===========================

Provides deal/opportunity management with pipeline stages,
Kanban board, revenue tracking, and stage transitions.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="deals",
    version="1.0.0",
    description="CRM deal pipeline and opportunity management module",
    services=[
        "modules.deals.services:DealService",
    ],
    controllers=[
        "modules.deals.controllers:DealController",
        "modules.deals.controllers:DealAPIController",
    ],
    route_prefix="/deals",
    base_path="modules.deals",
    faults=FaultHandlingConfig(
        default_domain="DEALS",
        strategy="propagate",
    ),
    depends_on=["crm_auth", "contacts", "companies"],
    tags=["deals", "crm", "pipeline"],
)
