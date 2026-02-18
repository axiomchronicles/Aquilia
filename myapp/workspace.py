"""
Aquilia CRM Dashboard - Workspace Configuration
================================================
Production-grade CRM built entirely on the Aquilia framework.
"""

from datetime import timedelta

from aquilia import Workspace, Module, Integration
from aquilia.sessions import (
    SessionPolicy,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
)

workspace = (
    Workspace(
        name="aquilia-crm",
        version="1.0.0",
        description="Production-grade CRM Dashboard built on Aquilia",
    )
    .database(url="sqlite:///crm.db", auto_create=True)

    # ---- Modules ---------------------------------------------------------

    .module(Module("tasks", version="1.0.0", description="CRM task management module")
        .route_prefix("/tasks")
        .tags("tasks", "crm")
        .register_controllers(
            "modules.tasks.controllers:TaskController",
            "modules.tasks.controllers:TaskAPIController"
        )
        .register_services(
            "modules.tasks.services:TaskService"
        ))

    .module(Module("dummy", version="0.1.0", description="Dummy module")
        .route_prefix("/dummy")
        .tags("dummy", "core")
        .register_controllers(
            "modules.dummy.controllers:DummyController"
        )
        .register_services(
            "modules.dummy.services:DummyService"
        ))

    .module(Module("crm_auth", version="1.0.0", description="CRM authentication and user management module")
        .route_prefix("/auth")
        .tags("auth", "crm", "users")
        .register_controllers(
            "modules.crm_auth.controllers:AuthPageController",
            "modules.crm_auth.controllers:AuthAPIController"
        )
        .register_services(
            "modules.crm_auth.services:CRMAuthService"
        ))

    .module(Module("crm_mail", version="1.0.0", description="CRM email campaigns and mail management module")
        .route_prefix("/mail")
        .tags("mail", "crm", "campaigns")
        .register_controllers(
            "modules.crm_mail.controllers:MailController"
        )
        .register_services(
            "modules.crm_mail.services:CRMMailService"
        ))

    .module(Module("contacts", version="1.0.0", description="CRM contact management module")
        .route_prefix("/contacts")
        .tags("contacts", "crm")
        .register_controllers(
            "modules.contacts.controllers:ContactController",
            "modules.contacts.controllers:ContactAPIController"
        )
        .register_services(
            "modules.contacts.services:ContactService"
        ))

    .module(Module("deals", version="1.0.0", description="CRM deal pipeline and opportunity management module")
        .route_prefix("/deals")
        .tags("deals", "crm", "pipeline")
        .register_controllers(
            "modules.deals.controllers:DealController",
            "modules.deals.controllers:DealAPIController"
        )
        .register_services(
            "modules.deals.services:DealService"
        ))

    .module(Module("companies", version="1.0.0", description="CRM company management module")
        .route_prefix("/companies")
        .tags("companies", "crm")
        .register_controllers(
            "modules.companies.controllers:CompanyController",
            "modules.companies.controllers:CompanyAPIController"
        )
        .register_services(
            "modules.companies.services:CompanyService"
        ))

    .module(Module("analytics", version="1.0.0", description="CRM analytics and dashboard module")
        .route_prefix("/dashboard")
        .tags("analytics", "crm", "dashboard")
        .register_controllers(
            "modules.analytics.controllers:DashboardController"
        )
        .register_services(
            "modules.analytics.services:AnalyticsService"
        ))

    # --- Integrations ---
    .integrate(Integration.di(auto_wire=True, manifest_validation=True))
    .integrate(Integration.registry(mode="auto", fingerprint_verification=True))
    .integrate(Integration.routing(strict_matching=True, version_support=True, compression=True))

    .integrate(Integration.auth(
        enabled=True,
        store_type="memory",
        secret_key="crm-super-secret-key-change-in-prod-2026",
        algorithm="HS256",
        issuer="aquilia-crm",
        access_token_ttl_minutes=60,
        refresh_token_ttl_days=30,
    ))

    .integrate(Integration.database(url="sqlite:///crm.db", auto_connect=True))

    .integrate(Integration.cache(
        backend="memory",
        default_ttl=300,
        max_size=10000,
        eviction_policy="lru",
        stampede_prevention=True,
        ttl_jitter=True,
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
        cache_max_age=86400,
        etag=True,
    ))

    .integrate(Integration.mail(provider="console", default_from="crm@aquilia.dev"))

    .integrate(Integration.fault_handling(default_strategy="propagate", metrics_enabled=True))
    .integrate(Integration.patterns())

    .integrate(Integration.cors(
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    ))

    .integrate(Integration.rate_limit(limit=200, window=60))

    .integrate(Integration.openapi(
        title="Aquilia CRM API",
        version="1.0.0",
        description="Production CRM Dashboard API",
        contact_name="CRM Team",
        contact_email="crm@aquilia.dev",
        license_name="MIT",
        # swagger_ui_theme="dark",
    ))

    # --- Sessions ---
    .sessions(policies=[
        SessionPolicy(
            name="crm_session",
            ttl=timedelta(days=7),
            idle_timeout=timedelta(hours=2),
            rotate_on_privilege_change=True,
            persistence=PersistencePolicy(
                enabled=True, store_name="memory", write_through=True,
            ),
            concurrency=ConcurrencyPolicy(
                max_sessions_per_principal=5, behavior_on_limit="evict_oldest",
            ),
            transport=TransportPolicy(
                adapter="cookie",
                cookie_httponly=True,
                cookie_secure=False,
                cookie_samesite="lax",
            ),
            scope="user",
        ),
    ])

    # --- Security ---
    .security(
        cors_enabled=True,
        csrf_protection=False,
        helmet_enabled=True,
        rate_limiting=True,
        https_redirect=False,
        hsts=False,
        proxy_fix=False,
    )

    # --- Telemetry ---
    .telemetry(
        tracing_enabled=False,
        metrics_enabled=True,
        logging_enabled=True,
    )
)

__all__ = ["workspace"]
