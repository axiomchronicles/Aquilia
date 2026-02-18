"""
Aquilia Workspace Configuration — Industry-Grade E-Commerce + ML Platform

Demonstrates EVERY Aquilia subsystem in a cohesive production application:
- Controllers (HTTP + WebSocket)
- DI (Dependency Injection with scopes)
- Models (Pure Python ORM)
- Serializers (DRF-inspired validation)
- Auth (Identity, RBAC, tokens, hashing)
- Sessions (Cryptographic session management)
- Cache (LRU, stampede prevention)
- Mail (Async mail with templates)
- Templates (Jinja2 sandboxed rendering)
- Middleware (CORS, CSRF, rate limiting, security headers)
- WebSockets (Real-time chat + notifications)
- Artifacts (Content-addressed storage)
- Faults (Structured error handling)
- MLOps (Model registry, serving, drift detection)
- Effects & Patterns
- Lifecycle management
- Trace & Observability
"""

from aquilia import Workspace, Module, Integration
from datetime import timedelta
from aquilia.sessions import (
    SessionPolicy,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
)

workspace = (
    Workspace(
        name="nexus",
        version="1.0.0",
        description="Industry-grade e-commerce + ML platform built on Aquilia",
    )

    # ─── Runtime ──────────────────────────────────────────────────────
    .runtime(mode="dev", host="127.0.0.1", port=8000, reload=True, workers=1)

    # ═══════════════════════════════════════════════════════════════════
    #  MODULES — Each with controllers, services, models, serializers
    # ═══════════════════════════════════════════════════════════════════

    # Users & Authentication

    # Products: Catalog management

    # Orders: Order processing pipeline

    # Notifications: Real-time WebSocket + email

    # Analytics: ML-powered analytics & recommendations

    # Admin: Dashboard & system management

    # ═══════════════════════════════════════════════════════════════════
    #  INTEGRATIONS
    # ═══════════════════════════════════════════════════════════════════

    # ---- Test Module -----------------------------------------------------

    # ---- Modules ---------------------------------------------------------

    .module(Module("products", version="1.0.0", description="Product catalog, categories, reviews & inventory management")
        .route_prefix("/products")
        .tags("products", "catalog", "inventory")
        .register_controllers(
            "modules.products.controllers:CategoryController",
            "modules.products.controllers:ProductController"
        )
        .register_services(
            "modules.products.services:CategoryService",
            "modules.products.services:ProductService"
        ))

    .module(Module("admin", version="1.0.0", description="Admin dashboard, system health monitoring & bulk operations")
        .route_prefix("/admin")
        .tags("admin", "dashboard", "management", "system")
        .register_controllers(
            "modules.admin.controllers:AdminDashboardController"
        )
        .register_services(
            "modules.admin.services:AdminService"
        ))

    .module(Module("testaquilia", version="0.1.0", description="Testaquilia module")
        .route_prefix("/testaquilia")
        .tags("testaquilia", "core")
        .register_controllers(
            "modules.testaquilia.controllers:TestaquiliaController"
        )
        .register_services(
            "modules.testaquilia.services:TestaquiliaService"
        ))

    .module(Module("users", version="1.0.0", description="User management, authentication & authorization module")
        .route_prefix("/users")
        .tags("users", "auth", "identity", "core")
        .register_controllers(
            "modules.users.controllers:AuthController",
            "modules.users.controllers:UserController"
        )
        .register_services(
            "modules.users.services:UserService",
            "modules.users.services:AuthService"
        ))

    .module(Module("orders", version="1.0.0", description="Order processing, cart management & fulfillment pipeline")
        .route_prefix("/orders")
        .tags("orders", "cart", "checkout", "fulfillment")
        .register_controllers(
            "modules.orders.controllers:CartController",
            "modules.orders.controllers:OrderController"
        )
        .register_services(
            "modules.orders.services:OrderService"
        ))

    .module(Module("notifications", version="1.0.0", description="Real-time notifications, chat rooms & order tracking via WebSocket")
        .route_prefix("/notifications")
        .tags("notifications", "websocket", "chat", "realtime")
        .register_controllers(
            "modules.notifications.controllers:NotificationController"
        )
        .register_services(
            "modules.notifications.services:NotificationService"
        )
        .register_sockets(
            "modules.notifications.sockets:NotificationSocket",
            "modules.notifications.sockets:ChatSocket",
            "modules.notifications.sockets:OrderTrackingSocket"
        ))

    .module(Module("analytics", version="1.0.0", description="Business intelligence, KPI dashboards & ML-powered recommendations")
        .route_prefix("/analytics")
        .tags("analytics", "ml", "recommendations", "dashboard")
        .register_controllers(
            "modules.analytics.controllers:AnalyticsController",
            "modules.analytics.controllers:RecommendationController"
        )
        .register_services(
            "modules.analytics.services:AnalyticsService",
            "modules.analytics.services:RecommendationService"
        ))

    .integrate(Integration.di(auto_wire=True, manifest_validation=True))
    .integrate(Integration.registry(mode="auto", fingerprint_verification=True))
    .integrate(Integration.routing(strict_matching=True, version_support=True, compression=True))
    .integrate(Integration.fault_handling(default_strategy="propagate", metrics_enabled=True))
    .integrate(Integration.patterns())

    .integrate(Integration.database(
        url="sqlite:///nexus.db",
        auto_connect=True,
        auto_create=True,
        pool_size=5,
    ))

    .integrate(Integration.auth(
        enabled=True,
        store_type="memory",
        secret_key="nexus-dev-secret-key-change-in-production",
    ))

    .integrate(Integration.cache(
        backend="memory", default_ttl=300, max_size=10000,
        eviction_policy="lru", namespace="nexus", key_prefix="nx:",
    ))

    .integrate(
        Integration.templates
        .source("templates")
        .scan_modules()
        .cached("memory")
        .secure()
    )

    .integrate(Integration.static_files(
        directories={"/static": "static"},
        cache_max_age=86400, etag=True,
    ))

    .integrate(Integration.mail(
        default_from="noreply@nexus-platform.com",
        console_backend=True,
        subject_prefix="[Nexus] ",
        metrics_enabled=True,
    ))

    .integrate(Integration.serializers(strict_validation=True, raise_on_error=True))

    .integrate(Integration.openapi(
        title="Nexus Platform API",
        version="1.0.0",
        description="Industry-grade E-Commerce + ML Platform powered by Aquilia",
        contact_name="Nexus Engineering",
        contact_email="api@nexus-platform.com",
        license_name="MIT",
        swagger_ui_theme="dark",
    ))

    .integrate(Integration.cors(
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True, max_age=3600,
    ))

    .integrate(Integration.rate_limit(
        limit=200, window=60, algorithm="sliding_window",
        exempt_paths=["/health", "/docs", "/openapi.json", "/redoc"],
    ))

    .integrate(Integration.mlops(
        enabled=True, registry_db="models_registry.db",
        blob_root=".nexus-models", drift_method="psi",
        drift_threshold=0.25, max_batch_size=32,
        cache_enabled=True, cache_ttl=120,
    ))

    .integrate(Integration.logging(
        slow_threshold_ms=500, colorize=True,
        skip_paths=["/health", "/healthz", "/metrics"],
    ))

    # ─── Sessions ─────────────────────────────────────────────────────
    .sessions(policies=[
        SessionPolicy(
            name="web",
            ttl=timedelta(days=14),
            idle_timeout=timedelta(hours=2),
            rotate_on_privilege_change=True,
            persistence=PersistencePolicy(
                enabled=True, store_name="memory", write_through=True,
            ),
            concurrency=ConcurrencyPolicy(
                max_sessions_per_principal=5, behavior_on_limit="evict_oldest",
            ),
            transport=TransportPolicy(
                adapter="cookie", cookie_httponly=True,
                cookie_secure=False, cookie_samesite="lax",
            ),
            scope="user",
        ),
        SessionPolicy(
            name="api",
            ttl=timedelta(hours=1),
            idle_timeout=None,
            rotate_on_privilege_change=False,
            persistence=PersistencePolicy(
                enabled=True, store_name="memory", write_through=True,
            ),
            concurrency=ConcurrencyPolicy(
                max_sessions_per_principal=20, behavior_on_limit="reject",
            ),
            transport=TransportPolicy(adapter="header"),
            scope="api",
        ),
    ])

    # ─── Security ─────────────────────────────────────────────────────
    .security(
        cors_enabled=True, csrf_protection=False, helmet_enabled=True,
        rate_limiting=True, https_redirect=False, hsts=False, proxy_fix=False,
    )

    # ─── Telemetry ────────────────────────────────────────────────────
    .telemetry(tracing_enabled=False, metrics_enabled=True, logging_enabled=True)
)

__all__ = ["workspace"]
