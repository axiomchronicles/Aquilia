"""
Deal Controllers — Page + API, including pipeline Kanban view.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.templates import TemplateEngine
from aquilia.sessions import authenticated

from modules.shared.auth_guard import login_required
from modules.shared.serializers import DealCreateSerializer
from .services import DealService


class DealController(Controller):
    """Template-rendered deal/pipeline pages."""

    prefix = "/"
    tags = ["deals", "pages"]

    def __init__(self, templates: TemplateEngine = None, service: DealService = None):
        self.templates = templates
        self.service = service

    @GET("/")
    async def deals_list_page(self, ctx: RequestCtx):
        if guard := login_required(ctx):
            return guard
        page = int(ctx.query_param("page", "1"))
        search = ctx.query_param("search", "")
        stage = ctx.query_param("stage", "")
        priority = ctx.query_param("priority", "")

        result = await self.service.list_deals(
            search=search or None,
            stage=stage or None,
            priority=priority or None,
            page=page,
        )

        return await self.templates.render_to_response(
            "deals/list.html",
            {
                "page_title": "Deals — CRM",
                "deals": result["items"],
                "total": result["total"],
                "page": result["page"],
                "total_pages": result["total_pages"],
                "search": search,
                "stage_filter": stage,
                "priority_filter": priority,
            },
            request_ctx=ctx,
        )

    @GET("/pipeline")
    async def pipeline_board_page(self, ctx: RequestCtx):
        """Render Kanban-style pipeline board."""
        if guard := login_required(ctx):
            return guard
        board = await self.service.get_pipeline_board()
        stats = await self.service.get_pipeline_stats()

        return await self.templates.render_to_response(
            "deals/pipeline.html",
            {
                "page_title": "Pipeline — CRM",
                "board": board,
                "stats": stats,
            },
            request_ctx=ctx,
        )

    @GET("/«id:int»")
    async def deal_detail_page(self, ctx: RequestCtx, id: int):
        if guard := login_required(ctx):
            return guard
        deal = await self.service.get_deal(id)
        return await self.templates.render_to_response(
            "deals/detail.html",
            {"page_title": f"{deal['title']} — CRM", "deal": deal},
            request_ctx=ctx,
        )

    @GET("/new")
    async def deal_new_page(self, ctx: RequestCtx):
        if guard := login_required(ctx):
            return guard
        return await self.templates.render_to_response(
            "deals/form.html",
            {"page_title": "New Deal — CRM", "deal": None, "mode": "create"},
            request_ctx=ctx,
        )

    @GET("/«id:int»/edit")
    async def deal_edit_page(self, ctx: RequestCtx, id: int):
        if guard := login_required(ctx):
            return guard
        deal = await self.service.get_deal(id)
        return await self.templates.render_to_response(
            "deals/form.html",
            {"page_title": f"Edit {deal['title']} — CRM", "deal": deal, "mode": "edit"},
            request_ctx=ctx,
        )


class DealAPIController(Controller):
    """JSON API for deals."""

    prefix = "/api"
    tags = ["deals", "api"]

    def __init__(self, service: DealService = None):
        self.service = service

    @GET("/")
    @authenticated
    async def api_list(self, ctx: RequestCtx):
        result = await self.service.list_deals(
            search=ctx.query_param("search"),
            stage=ctx.query_param("stage"),
            priority=ctx.query_param("priority"),
            page=int(ctx.query_param("page", "1")),
        )
        return Response.json(result)

    @POST("/")
    @authenticated
    async def api_create(self, ctx: RequestCtx):
        data = await ctx.json()
        serializer = DealCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response.json({"error": "Validation failed", "details": serializer.errors}, status=400)
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        deal = await self.service.create_deal(serializer.validated_data, user_id=user_id)
        return Response.json({"deal": deal}, status=201)

    @GET("/«id:int»")
    @authenticated
    async def api_get(self, ctx: RequestCtx, id: int):
        deal = await self.service.get_deal(id)
        return Response.json({"deal": deal})

    @PUT("/«id:int»")
    @authenticated
    async def api_update(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        deal = await self.service.update_deal(id, data)
        return Response.json({"deal": deal})

    @PUT("/«id:int»/stage")
    @authenticated
    async def api_update_stage(self, ctx: RequestCtx, id: int):
        """Update deal stage (Kanban drag-and-drop)."""
        data = await ctx.json()
        deal = await self.service.update_deal(id, {"stage": data["stage"]})
        return Response.json({"deal": deal})

    @DELETE("/«id:int»")
    @authenticated
    async def api_delete(self, ctx: RequestCtx, id: int):
        await self.service.delete_deal(id)
        return Response.json({"message": "Deal deleted"})

    @GET("/pipeline")
    @authenticated
    async def api_pipeline(self, ctx: RequestCtx):
        board = await self.service.get_pipeline_board()
        return Response.json({"pipeline": board})

    @GET("/stats")
    async def api_stats(self, ctx: RequestCtx):
        stats = await self.service.get_pipeline_stats()
        return Response.json(stats)
