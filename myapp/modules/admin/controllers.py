"""
Admin Module — Controllers

Admin dashboard with template rendering, system health,
bulk operations, and cache management.

Integrates:
- Aquilia Controller with self.render() for HTML templates
- Aquilia TemplateEngine (Jinja2 sandboxed rendering)
- Aquilia Response (JSON + HTML + SSE)
- Aquilia Cache (dashboard caching, cache flush)
- Full DI orchestration across all modules
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET, POST, DELETE
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import AdminService
from .faults import AdminAccessDeniedFault
from ..users.faults import InsufficientPermissionsFault


class AdminDashboardController(Controller):
    """
    Admin dashboard — HTML rendered via Aquilia TemplateEngine
    and JSON API endpoints for admin operations.
    """
    prefix = "/admin"
    tags = ["Admin"]

    def _require_admin(self, ctx: RequestCtx) -> None:
        """Guard: require admin role."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise AdminAccessDeniedFault()

    # ── Dashboard (Template Rendered) ────────────────────────

    @GET("/")
    async def dashboard_page(self, ctx: RequestCtx) -> Response:
        """
        Render admin dashboard HTML using Aquilia TemplateEngine.
        Uses self.render() — the Controller template integration.
        """
        self._require_admin(ctx)

        admin_service = await ctx.container.resolve_async(AdminService)
        dashboard = await admin_service.get_admin_dashboard()

        return self.render(
            "admin/dashboard.html",
            context={
                "stats": dashboard["stats"],
                "top_products": dashboard["top_products"],
                "order_distribution": dashboard["order_distribution"],
                "user": {
                    "id": ctx.identity.id,
                    "roles": ctx.identity.attributes.get("roles", []),
                },
            },
        )

    # ── JSON API Endpoints ───────────────────────────────────

    @GET("/api/dashboard")
    async def dashboard_api(self, ctx: RequestCtx) -> Response:
        """JSON dashboard data for SPA/API consumption."""
        self._require_admin(ctx)

        admin_service = await ctx.container.resolve_async(AdminService)
        dashboard = await admin_service.get_admin_dashboard()
        return Response.json(dashboard)

    @GET("/api/health")
    async def health_check(self, ctx: RequestCtx) -> Response:
        """System health check — cache, database, mail."""
        self._require_admin(ctx)

        admin_service = await ctx.container.resolve_async(AdminService)
        health = await admin_service.system_health_check()
        status = 200 if health.get("overall") == "healthy" else 503
        return Response.json(health, status=status)

    # ── Bulk Operations ──────────────────────────────────────

    @POST("/api/users/bulk-status")
    async def bulk_user_status(self, ctx: RequestCtx) -> Response:
        """Bulk activate/deactivate users."""
        self._require_admin(ctx)

        body = await ctx.request.json()
        admin_service = await ctx.container.resolve_async(AdminService)
        result = await admin_service.bulk_update_user_status(
            user_ids=body.get("user_ids", []),
            is_active=body.get("is_active", True),
        )
        return Response.json(result)

    @POST("/api/orders/bulk-status")
    async def bulk_order_status(self, ctx: RequestCtx) -> Response:
        """Bulk update order statuses."""
        self._require_admin(ctx)

        body = await ctx.request.json()
        admin_service = await ctx.container.resolve_async(AdminService)
        result = await admin_service.bulk_update_order_status(
            order_ids=body.get("order_ids", []),
            new_status=body.get("status", ""),
            actor_id=ctx.identity.id,
        )
        return Response.json(result)

    # ── Notifications ────────────────────────────────────────

    @POST("/api/notifications/broadcast")
    async def broadcast_notification(self, ctx: RequestCtx) -> Response:
        """Send system-wide notification."""
        self._require_admin(ctx)

        body = await ctx.request.json()
        admin_service = await ctx.container.resolve_async(AdminService)
        result = await admin_service.send_admin_notification(
            title=body.get("title", ""),
            body=body.get("body", ""),
            target_user_ids=body.get("user_ids"),
        )
        return Response.json(result)

    # ── Cache Management ─────────────────────────────────────

    @DELETE("/api/cache")
    async def flush_cache(self, ctx: RequestCtx) -> Response:
        """Flush dashboard cache."""
        self._require_admin(ctx)

        admin_service = await ctx.container.resolve_async(AdminService)
        await admin_service.invalidate_dashboard_cache()
        return Response.json({"message": "Dashboard cache flushed"})
