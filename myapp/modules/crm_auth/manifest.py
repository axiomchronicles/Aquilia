"""
CRM Authentication Module Manifest
====================================

Provides user registration, login, JWT authentication,
session management, and role-based access control.
"""

from aquilia.manifest import AppManifest, FaultHandlingConfig


manifest = AppManifest(
    name="crm_auth",
    version="1.0.0",
    description="CRM authentication and user management module",
    services=[
        "modules.crm_auth.services:CRMAuthService",
    ],
    controllers=[
        "modules.crm_auth.controllers:AuthPageController",
        "modules.crm_auth.controllers:AuthAPIController",
    ],
    route_prefix="/auth",
    base_path="modules.crm_auth",
    faults=FaultHandlingConfig(
        default_domain="AUTH",
        strategy="propagate",
    ),
    depends_on=[],
    tags=["auth", "crm", "users"],
)
