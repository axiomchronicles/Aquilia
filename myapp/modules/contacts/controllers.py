"""
Contact Controllers — Page + API endpoints.
Uses Aquilia Controller, TemplateEngine, FilterSet, Pagination.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.templates import TemplateEngine
from aquilia.sessions import authenticated

from modules.shared.auth_guard import login_required
from modules.shared.serializers import ContactCreateSerializer
from .services import ContactService


class ContactController(Controller):
    """Template-rendered contact pages."""

    prefix = "/"
    tags = ["contacts", "pages"]

    def __init__(self, templates: TemplateEngine = None, service: ContactService = None):
        self.templates = templates
        self.service = service

    @GET("/")
    async def contacts_list_page(self, ctx: RequestCtx):
        """Render contacts list page."""
        if guard := login_required(ctx):
            return guard
        page = int(ctx.query_param("page", "1"))
        search = ctx.query_param("search", "")
        status = ctx.query_param("status", "")
        source = ctx.query_param("source", "")

        result = await self.service.list_contacts(
            search=search or None,
            status=status or None,
            source=source or None,
            page=page,
        )

        return await self.templates.render_to_response(
            "contacts/list.html",
            {
                "page_title": "Contacts — CRM",
                "contacts": result["items"],
                "total": result["total"],
                "page": result["page"],
                "total_pages": result["total_pages"],
                "search": search,
                "status_filter": status,
                "source_filter": source,
            },
            request_ctx=ctx,
        )

    @GET("/«id:int»")
    async def contact_detail_page(self, ctx: RequestCtx, id: int):
        """Render contact detail page."""
        if guard := login_required(ctx):
            return guard
        contact = await self.service.get_contact(id)
        return await self.templates.render_to_response(
            "contacts/detail.html",
            {"page_title": f"{contact['first_name']} {contact['last_name']} — CRM", "contact": contact},
            request_ctx=ctx,
        )

    @GET("/new")
    async def contact_new_page(self, ctx: RequestCtx):
        """Render new contact form."""
        if guard := login_required(ctx):
            return guard
        return await self.templates.render_to_response(
            "contacts/form.html",
            {"page_title": "New Contact — CRM", "contact": None, "mode": "create"},
            request_ctx=ctx,
        )

    @GET("/«id:int»/edit")
    async def contact_edit_page(self, ctx: RequestCtx, id: int):
        """Render edit contact form."""
        if guard := login_required(ctx):
            return guard
        contact = await self.service.get_contact(id)
        return await self.templates.render_to_response(
            "contacts/form.html",
            {"page_title": f"Edit {contact['first_name']} — CRM", "contact": contact, "mode": "edit"},
            request_ctx=ctx,
        )


class ContactAPIController(Controller):
    """JSON API for contacts — CRUD operations."""

    prefix = "/api"
    tags = ["contacts", "api"]

    def __init__(self, service: ContactService = None):
        self.service = service

    @GET("/")
    @authenticated
    async def api_list_contacts(self, ctx: RequestCtx):
        """List contacts with filters."""
        result = await self.service.list_contacts(
            search=ctx.query_param("search"),
            status=ctx.query_param("status"),
            source=ctx.query_param("source"),
            page=int(ctx.query_param("page", "1")),
            per_page=int(ctx.query_param("per_page", "25")),
        )
        return Response.json(result)

    @POST("/")
    @authenticated
    async def api_create_contact(self, ctx: RequestCtx):
        """Create a new contact."""
        data = await ctx.json()
        serializer = ContactCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response.json({"error": "Validation failed", "details": serializer.errors}, status=400)

        user_id = None
        if ctx.session:
            user_id = ctx.session.data.get("user_id")

        contact = await self.service.create_contact(serializer.validated_data, user_id=user_id)
        return Response.json({"contact": contact, "message": "Contact created"}, status=201)

    @GET("/«id:int»")
    @authenticated
    async def api_get_contact(self, ctx: RequestCtx, id: int):
        """Get contact by ID."""
        contact = await self.service.get_contact(id)
        return Response.json({"contact": contact})

    @PUT("/«id:int»")
    @authenticated
    async def api_update_contact(self, ctx: RequestCtx, id: int):
        """Update a contact."""
        data = await ctx.json()
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        contact = await self.service.update_contact(id, data, user_id=user_id)
        return Response.json({"contact": contact, "message": "Contact updated"})

    @DELETE("/«id:int»")
    @authenticated
    async def api_delete_contact(self, ctx: RequestCtx, id: int):
        """Delete a contact."""
        await self.service.delete_contact(id)
        return Response.json({"message": "Contact deleted"})

    @GET("/stats")
    @authenticated
    async def api_contact_stats(self, ctx: RequestCtx):
        """Get contact statistics."""
        stats = await self.service.get_contact_stats()
        return Response.json(stats)
