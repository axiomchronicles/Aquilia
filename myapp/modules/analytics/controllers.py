"""
Dashboard Controller — Main CRM dashboard page.
"""

from aquilia import Controller, GET, RequestCtx, Response
from aquilia.templates import TemplateEngine

from .services import AnalyticsService


class DashboardController(Controller):
    """Main dashboard — the CRM home page."""

    prefix = "/"
    tags = ["dashboard"]

    def __init__(self, templates: TemplateEngine = None, analytics: AnalyticsService = None):
        self.templates = templates
        self.analytics = analytics

    @GET("/")
    async def dashboard_page(self, ctx: RequestCtx):
        """Render the main CRM dashboard."""
        data = await self.analytics.get_dashboard_data()

        return await self.templates.render_to_response(
            "dashboard/index.html",
            {
                "page_title": "Dashboard — Aquilia CRM",
                "kpis": data["kpis"],
                "pipeline": data["pipeline"],
                "recent_activities": data["recent_activities"],
                "tasks_overview": data["tasks_overview"],
                "revenue_by_stage": data["revenue_by_stage"],
                "contacts_by_status": data["contacts_by_status"],
                "top_deals": data["top_deals"],
                "team_performance": data["team_performance"],
            },
            request_ctx=ctx,
        )

    @GET("/api/stats")
    async def api_dashboard_stats(self, ctx: RequestCtx):
        """JSON endpoint for dashboard data (for AJAX refresh)."""
        data = await self.analytics.get_dashboard_data()
        return Response.json(data)
