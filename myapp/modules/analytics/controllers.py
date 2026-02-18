"""
Analytics Module — Controllers

Dashboard analytics, reporting endpoints, and ML recommendations.

Integrates:
- Aquilia Controller
- Aquilia Response (JSON + SSE streaming for live dashboards)
- Aquilia Cache (aggregation caching)
- Aquilia MLOps (recommendation endpoints)
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import AnalyticsService, RecommendationService
from ..users.faults import InsufficientPermissionsFault


class AnalyticsController(Controller):
    """Admin analytics dashboard endpoints."""
    prefix = "/analytics"
    tags = ["Analytics"]

    @GET("/dashboard")
    async def dashboard(self, ctx: RequestCtx) -> Response:
        """Aggregated dashboard KPIs (admin only)."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        service = await ctx.container.resolve_async(AnalyticsService)
        stats = await service.get_dashboard_stats()
        return Response.json(stats)

    @GET("/revenue")
    async def revenue_timeline(self, ctx: RequestCtx) -> Response:
        """Revenue timeline data for charting."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        days = int(ctx.request.query_params.get("days", 30))
        service = await ctx.container.resolve_async(AnalyticsService)
        timeline = await service.get_revenue_timeline(days=days)
        return Response.json({"timeline": timeline, "days": days})

    @GET("/top-products")
    async def top_products(self, ctx: RequestCtx) -> Response:
        """Top products by sales volume."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        limit = int(ctx.request.query_params.get("limit", 10))
        service = await ctx.container.resolve_async(AnalyticsService)
        products = await service.get_top_products(limit=limit)
        return Response.json({"products": products})

    @GET("/orders/distribution")
    async def order_distribution(self, ctx: RequestCtx) -> Response:
        """Order status distribution."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        service = await ctx.container.resolve_async(AnalyticsService)
        distribution = await service.get_order_status_distribution()
        return Response.json(distribution)

    @GET("/revenue/stream")
    async def revenue_stream(self, ctx: RequestCtx) -> Response:
        """
        Live revenue stream via Server-Sent Events (SSE).
        Uses Aquilia Response.sse() for real-time dashboard updates.
        """
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        import asyncio
        import json
        from datetime import datetime, timezone

        async def revenue_generator():
            service = await ctx.container.resolve_async(AnalyticsService)
            while True:
                stats = await service.get_dashboard_stats()
                yield {
                    "event": "revenue_update",
                    "data": json.dumps({
                        "revenue": stats["orders"]["revenue"],
                        "orders": stats["orders"]["total"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }),
                }
                await asyncio.sleep(10)

        return Response.sse(revenue_generator())


class RecommendationController(Controller):
    """ML-powered product recommendation endpoints."""
    prefix = "/recommendations"
    tags = ["Recommendations"]

    @GET("/for-me")
    async def personal_recommendations(self, ctx: RequestCtx) -> Response:
        """Personalized recommendations for the authenticated user."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        limit = int(ctx.request.query_params.get("limit", 8))
        service = await ctx.container.resolve_async(RecommendationService)
        recommendations = await service.get_for_user(
            user_id=int(ctx.identity.id), limit=limit
        )
        return Response.json({"recommendations": recommendations})

    @GET("/similar/«product_id:int»")
    async def similar_products(self, ctx: RequestCtx, product_id: int) -> Response:
        """Content-based similar product suggestions."""
        limit = int(ctx.request.query_params.get("limit", 6))
        service = await ctx.container.resolve_async(RecommendationService)
        similar = await service.get_similar_products(
            product_id=product_id, limit=limit
        )
        return Response.json({"similar": similar})
