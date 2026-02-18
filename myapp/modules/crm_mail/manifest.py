"""
CRM Mail Module Manifest
==========================

Provides email campaign management, contact email sending,
campaign creation, and bulk email operations.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="crm_mail",
    version="1.0.0",
    description="CRM email campaigns and mail management module",
    services=[
        "modules.crm_mail.services:CRMMailService",
    ],
    controllers=[
        "modules.crm_mail.controllers:MailController",
    ],
    route_prefix="/mail",
    base_path="modules.crm_mail",
    faults=FaultHandlingConfig(
        default_domain="MAIL",
        strategy="propagate",
    ),
    depends_on=["crm_auth", "contacts"],
    tags=["mail", "crm", "campaigns"],
)
