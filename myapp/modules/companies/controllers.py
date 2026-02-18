"""
Company Controllers — Page + API.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.templates import TemplateEngine

from modules.shared.serializers import CompanyCreateSerializer
from .services import CompanyService


class CompanyController(Controller):
    """Template-rendered company pages."""

    prefix = "/"
    tags = ["companies", "pages"]

    def __init__(self, templates: TemplateEngine = None, service: CompanyService = None):
        self.templates = templates
        self.service = service

    @GET("/")
    async def companies_list_page(self, ctx: RequestCtx):
        page = int(ctx.query_param("page", "1"))
        search = ctx.query_param("search", "")
        industry = ctx.query_param("industry", "")

        result = await self.service.list_companies(
            search=search or None,
            industry=industry or None,
            page=page,
        )

        return await self.templates.render_to_response(
            "companies/list.html",
            {
                "page_title": "Companies — CRM",
                "companies": result["items"],
                "total": result["total"],
                "page": result["page"],
                "total_pages": result["total_pages"],
                "search": search,
                "industry_filter": industry,
            },
            request_ctx=ctx,
        )

    @GET("/«id:int»")
    async def company_detail_page(self, ctx: RequestCtx, id: int):
        company = await self.service.get_company(id)
        return await self.templates.render_to_response(
            "companies/detail.html",
            {"page_title": f"{company['name']} — CRM", "company": company},
            request_ctx=ctx,
        )

    @GET("/new")
    async def company_new_page(self, ctx: RequestCtx):
        return await self.templates.render_to_response(
            "companies/form.html",
            {"page_title": "New Company — CRM", "company": None, "mode": "create"},
            request_ctx=ctx,
        )

    @GET("/«id:int»/edit")
    async def company_edit_page(self, ctx: RequestCtx, id: int):
        company = await self.service.get_company(id)
        return await self.templates.render_to_response(
            "companies/form.html",
            {"page_title": f"Edit {company['name']} — CRM", "company": company, "mode": "edit"},
            request_ctx=ctx,
        )


class CompanyAPIController(Controller):
    """JSON API for companies."""

    prefix = "/api"
    tags = ["companies", "api"]

    def __init__(self, service: CompanyService = None):
        self.service = service

    @GET("/")
    async def api_list(self, ctx: RequestCtx):
        result = await self.service.list_companies(
            search=ctx.query_param("search"),
            industry=ctx.query_param("industry"),
            page=int(ctx.query_param("page", "1")),
            per_page=int(ctx.query_param("per_page", "25")),
        )
        return Response.json(result)

    @POST("/")
    async def api_create(self, ctx: RequestCtx):
        data = await ctx.json()
        serializer = CompanyCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response.json({"error": "Validation failed", "details": serializer.errors}, status=400)
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        company = await self.service.create_company(serializer.validated_data, user_id=user_id)
        return Response.json({"company": company}, status=201)

    @GET("/«id:int»")
    async def api_get(self, ctx: RequestCtx, id: int):
        company = await self.service.get_company(id)
        return Response.json({"company": company})

    @PUT("/«id:int»")
    async def api_update(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        company = await self.service.update_company(id, data)
        return Response.json({"company": company})

    @DELETE("/«id:int»")
    async def api_delete(self, ctx: RequestCtx, id: int):
        await self.service.delete_company(id)
        return Response.json({"message": "Company deleted"})

    @GET("/stats")
    async def api_stats(self, ctx: RequestCtx):
        stats = await self.service.get_company_stats()
        return Response.json(stats)
