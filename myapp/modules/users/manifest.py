"""
Users Module - Manifest

Showcases:
- AppManifest with full configuration
- Service and controller registration
- Fault handling config
- Feature flags
- Lifecycle hooks
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    FaultHandlerConfig,
    LifecycleConfig,
    FeatureConfig,
)

manifest = AppManifest(
    # Identity
    name="users",
    version="0.1.0",
    description="User management with auth, sessions, and DI",
    author="team@aquilia.dev",
    tags=["users", "auth", "core"],

    # Components
    services=[
        "modules.users.services:UserRepository",
        "modules.users.services:TokenService",
        "modules.users.services:UserService",
    ],
    controllers=[
        "modules.users.controllers:UsersController",
    ],

    # Routing
    route_prefix="/users",
    base_path="modules.users",

    # Fault handling
    faults=FaultHandlingConfig(
        default_domain="USERS",
        strategy="propagate",
        handlers=[],
    ),

    # Feature flags
    features=[
        FeatureConfig(name="user_registration", enabled=True),
        FeatureConfig(name="social_login", enabled=False),
        FeatureConfig(name="two_factor_auth", enabled=False),
    ],
)
