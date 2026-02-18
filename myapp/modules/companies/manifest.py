"""
CRM Companies Module Manifest
===============================

Provides company/organization management with CRUD operations,
associated contacts, deals, and company analytics.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="companies",
    version="1.0.0",
    description="CRM company management module",
    services=[
        "modules.companies.services:CompanyService",
    ],
    controllers=[
        "modules.companies.controllers:CompanyController",
        "modules.companies.controllers:CompanyAPIController",
    ],
    route_prefix="/companies",
    base_path="modules.companies",
    faults=FaultHandlingConfig(
        default_domain="COMPANIES",
        strategy="propagate",
    ),
    depends_on=["crm_auth"],
    tags=["companies", "crm"],
)
