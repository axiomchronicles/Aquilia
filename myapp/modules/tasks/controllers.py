"""
Tasks Module - Controllers

Showcases:
- Structured fault handling (faults are raised, not caught)
- Status transition endpoints
- Assignment management
- Filtering and statistics
- PATCH for partial updates
"""

from aquilia import Controller, GET, POST, PUT, PATCH, DELETE, RequestCtx, Response
from .services import TaskService


class TasksController(Controller):
    """
    Task management controller.

    All faults raised by TaskService are automatically converted to
    proper HTTP responses by Aquilia's fault engine:
    - TaskNotFoundFault → 404
    - TaskValidationFault → 400
    - TaskAlreadyCompleteFault → 409
    - TaskQuotaExceededFault → 429
    """

    prefix = "/"
    tags = ["tasks", "project-management"]

    def __init__(self, service: TaskService = None):
        self.service = service or TaskService()

    # ── CRUD ─────────────────────────────────────────────────────────────

    @GET("/")
    async def list_tasks(self, ctx: RequestCtx):
        """
        List tasks with optional filtering.

        GET /tasks/?status=pending&priority=high&assignee=alice&tag=urgent

        All filter parameters are optional.
        """
        params = ctx.query_params
        tasks = await self.service.list_tasks(
            status=params.get("status"),
            priority=params.get("priority"),
            assignee=params.get("assignee"),
            tag=params.get("tag"),
        )
        return Response.json({
            "items": tasks,
            "total": len(tasks),
        })

    @POST("/")
    async def create_task(self, ctx: RequestCtx):
        """
        Create a new task.

        POST /tasks/
        Body: {
            "title": "Fix bug #123",
            "description": "...",
            "priority": "high",
            "assignee": "alice",
            "tags": ["bug", "urgent"],
            "due_date": "2025-12-31T00:00:00"
        }

        Raises TaskValidationFault (400) or TaskQuotaExceededFault (429).
        """
        data = await ctx.json()
        task = await self.service.create_task(data)
        return Response.json(task, status=201)

    @GET("/«id:str»")
    async def get_task(self, ctx: RequestCtx, id: str):
        """
        Get task by ID.

        GET /tasks/<id>
        Raises TaskNotFoundFault (404).
        """
        task = await self.service.get_task(id)
        return Response.json(task)

    @PUT("/«id:str»")
    async def update_task(self, ctx: RequestCtx, id: str):
        """
        Update task fields.

        PUT /tasks/<id>
        Body: {"title": "Updated title", "priority": "critical"}

        Raises TaskNotFoundFault (404) or TaskAlreadyCompleteFault (409).
        """
        data = await ctx.json()
        task = await self.service.update_task(id, data)
        return Response.json(task)

    @DELETE("/«id:str»")
    async def delete_task(self, ctx: RequestCtx, id: str):
        """
        Delete a task.

        DELETE /tasks/<id>
        Raises TaskNotFoundFault (404).
        """
        await self.service.delete_task(id)
        return Response.json({"deleted": True, "id": id})

    # ── Status Transitions ──────────────────────────────────────────────

    @PATCH("/«id:str»/status")
    async def change_status(self, ctx: RequestCtx, id: str):
        """
        Change task status.

        PATCH /tasks/<id>/status
        Body: {"status": "in_progress"}

        Valid transitions:
        - pending → in_progress, cancelled
        - in_progress → completed, cancelled
        - cancelled → pending (reopen)
        - completed → (none — immutable)
        """
        data = await ctx.json()
        new_status = data.get("status", "")
        task = await self.service.transition_status(id, new_status)
        return Response.json(task)

    # ── Assignment ──────────────────────────────────────────────────────

    @PATCH("/«id:str»/assign")
    async def assign_task(self, ctx: RequestCtx, id: str):
        """
        Assign task to a user.

        PATCH /tasks/<id>/assign
        Body: {"assignee": "alice"}

        Raises TaskAssignmentFault (409) if user is at capacity.
        """
        data = await ctx.json()
        assignee = data.get("assignee", "")
        if not assignee:
            return Response.json({"error": "Assignee is required"}, status=400)

        task = await self.service.assign_task(id, assignee)
        return Response.json(task)

    # ── Statistics ──────────────────────────────────────────────────────

    @GET("/stats")
    async def get_stats(self, ctx: RequestCtx):
        """
        Get task statistics.

        GET /tasks/stats
        Returns counts by status, by priority, and overdue count.
        """
        stats = await self.service.get_stats()
        return Response.json(stats)
