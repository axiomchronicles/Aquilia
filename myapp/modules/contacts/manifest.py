"""
CRM Contacts Module Manifest
==============================

Provides contact management with CRUD operations,
search, filtering, pagination, and activity tracking.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="contacts",
    version="1.0.0",
    description="CRM contact management module",
    services=[
        "modules.contacts.services:ContactService",
    ],
    controllers=[
        "modules.contacts.controllers:ContactController",
        "modules.contacts.controllers:ContactAPIController",
    ],
    route_prefix="/contacts",
    base_path="modules.contacts",
    faults=FaultHandlingConfig(
        default_domain="CONTACTS",
        strategy="propagate",
    ),
    depends_on=["crm_auth"],
    tags=["contacts", "crm"],
)
