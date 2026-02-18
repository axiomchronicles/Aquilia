"""
Users Module Manifest — User management, authentication & authorization.

Defines complete module configuration:
- Services: UserService (CRUD), AuthService (auth flows)
- Controllers: UserController, AuthController
- Middleware: RequireAuth, RoleGuard, RequestLogging
- Fault domain: USERS
- Session: user_session
"""

from datetime import timedelta
from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    SessionConfig,
    LifecycleConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="users",
    version="1.0.0",
    description="User management, authentication & authorization module",
    author="nexus-engineering@nexus-platform.com",
    tags=["users", "auth", "identity", "core"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.users.services:UserService",
        "modules.users.services:AuthService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.users.controllers:AuthController",
        "modules.users.controllers:UserController",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[
        MiddlewareConfig(
            class_path="modules.users.middleware:RequireAuthMiddleware",
            scope="app",
            priority=10,
            config={},
        ),
        MiddlewareConfig(
            class_path="modules.users.middleware:RoleGuardMiddleware",
            scope="app",
            priority=20,
            config={},
        ),
        MiddlewareConfig(
            class_path="modules.users.middleware:RequestLoggingMiddleware",
            scope="app",
            priority=5,
            config={},
        ),
    ],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/users",
    base_path="modules.users",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="USERS",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[
        SessionConfig(
            name="user_session",
            enabled=True,
            ttl=timedelta(days=14),
            idle_timeout=timedelta(hours=2),
            transport="cookie",
            store="memory",
        ),
    ],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="two_factor_auth", enabled=False),
        FeatureConfig(name="social_login", enabled=False),
        FeatureConfig(name="password_reset", enabled=True),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=[],
)


__all__ = ["manifest"]
