"""
Task Controllers — Page + API.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.templates import TemplateEngine

from modules.shared.serializers import TaskCreateSerializer
from .services import TaskService


class TaskController(Controller):
    """Template-rendered task pages."""

    prefix = "/"
    tags = ["tasks", "pages"]

    def __init__(self, templates: TemplateEngine = None, service: TaskService = None):
        self.templates = templates
        self.service = service

    @GET("/")
    async def tasks_list_page(self, ctx: RequestCtx):
        page = int(ctx.query_param("page", "1"))
        search = ctx.query_param("search", "")
        status = ctx.query_param("status", "")
        priority = ctx.query_param("priority", "")

        result = await self.service.list_tasks(
            search=search or None,
            status=status or None,
            priority=priority or None,
            page=page,
        )

        return await self.templates.render_to_response(
            "tasks/list.html",
            {
                "page_title": "Tasks — CRM",
                "tasks": result["items"],
                "total": result["total"],
                "page": result["page"],
                "total_pages": result["total_pages"],
                "search": search,
                "status_filter": status,
                "priority_filter": priority,
            },
            request_ctx=ctx,
        )

    @GET("/«id:int»")
    async def task_detail_page(self, ctx: RequestCtx, id: int):
        task = await self.service.get_task(id)
        return await self.templates.render_to_response(
            "tasks/detail.html",
            {"page_title": f"{task['title']} — CRM", "task": task},
            request_ctx=ctx,
        )

    @GET("/new")
    async def task_new_page(self, ctx: RequestCtx):
        return await self.templates.render_to_response(
            "tasks/form.html",
            {"page_title": "New Task — CRM", "task": None, "mode": "create"},
            request_ctx=ctx,
        )


class TaskAPIController(Controller):
    """JSON API for tasks."""

    prefix = "/api"
    tags = ["tasks", "api"]

    def __init__(self, service: TaskService = None):
        self.service = service

    @GET("/")
    async def api_list(self, ctx: RequestCtx):
        result = await self.service.list_tasks(
            search=ctx.query_param("search"),
            status=ctx.query_param("status"),
            priority=ctx.query_param("priority"),
            task_type=ctx.query_param("type"),
            page=int(ctx.query_param("page", "1")),
        )
        return Response.json(result)

    @POST("/")
    async def api_create(self, ctx: RequestCtx):
        data = await ctx.json()
        serializer = TaskCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response.json({"error": "Validation failed", "details": serializer.errors}, status=400)
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        task = await self.service.create_task(serializer.validated_data, user_id=user_id)
        return Response.json({"task": task}, status=201)

    @GET("/«id:int»")
    async def api_get(self, ctx: RequestCtx, id: int):
        task = await self.service.get_task(id)
        return Response.json({"task": task})

    @PUT("/«id:int»")
    async def api_update(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        task = await self.service.update_task(id, data)
        return Response.json({"task": task})

    @PUT("/«id:int»/complete")
    async def api_complete(self, ctx: RequestCtx, id: int):
        """Mark task as completed."""
        task = await self.service.update_task(id, {"status": "completed"})
        return Response.json({"task": task, "message": "Task completed"})

    @DELETE("/«id:int»")
    async def api_delete(self, ctx: RequestCtx, id: int):
        await self.service.delete_task(id)
        return Response.json({"message": "Task deleted"})

    @GET("/stats")
    async def api_stats(self, ctx: RequestCtx):
        stats = await self.service.get_task_stats()
        return Response.json(stats)
