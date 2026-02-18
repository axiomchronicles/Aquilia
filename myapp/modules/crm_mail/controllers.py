"""
Mail Controller — Campaign pages + API.
"""

from aquilia import Controller, GET, POST, RequestCtx, Response
from aquilia.templates import TemplateEngine

from modules.shared.serializers import CampaignCreateSerializer
from .services import CRMMailService


class MailController(Controller):
    """Mail campaign management."""

    prefix = "/"
    tags = ["mail"]

    def __init__(self, templates: TemplateEngine = None, service: CRMMailService = None):
        self.templates = templates
        self.service = service

    @GET("/")
    async def campaigns_page(self, ctx: RequestCtx):
        page = int(ctx.query_param("page", "1"))
        result = await self.service.list_campaigns(page=page)
        return await self.templates.render_to_response(
            "mail/campaigns.html",
            {
                "page_title": "Email Campaigns — CRM",
                "campaigns": result["items"],
                "total": result["total"],
                "page": result["page"],
                "total_pages": result["total_pages"],
            },
            request_ctx=ctx,
        )

    @GET("/new")
    async def new_campaign_page(self, ctx: RequestCtx):
        return await self.templates.render_to_response(
            "mail/compose.html",
            {"page_title": "New Campaign — CRM"},
            request_ctx=ctx,
        )

    @POST("/api/campaigns")
    async def api_create_campaign(self, ctx: RequestCtx):
        data = await ctx.json()
        serializer = CampaignCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response.json({"error": "Validation failed", "details": serializer.errors}, status=400)
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        campaign = await self.service.create_campaign(serializer.validated_data, sender_id=user_id)
        return Response.json({"campaign": campaign}, status=201)

    @POST("/api/campaigns/«id:int»/send")
    async def api_send_campaign(self, ctx: RequestCtx, id: int):
        result = await self.service.send_campaign(id)
        return Response.json(result)

    @POST("/api/send")
    async def api_send_email(self, ctx: RequestCtx):
        """Send a direct email to a contact."""
        data = await ctx.json()
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        result = await self.service.send_contact_email(
            contact_id=data["contact_id"],
            subject=data["subject"],
            body=data["body"],
            sender_id=user_id,
        )
        return Response.json(result)
