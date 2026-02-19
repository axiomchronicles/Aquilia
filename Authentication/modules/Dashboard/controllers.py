"""
Dashboard module controllers (request handlers).

This file defines the HTTP endpoints for the Dashboard module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import DashboardNotFoundFault
from .services import DashboardService


class DashboardController(Controller):
    """
    Controller for Dashboard endpoints.

    Provides RESTful CRUD operations for Dashboard.
    """
    prefix = "/"
    tags = ["Dashboard"]

    def __init__(self, service: "DashboardService" = None):
        # Instantiate service directly if not injected
        self.service = service or DashboardService()

    @GET("/")
    async def list_Dashboard(self, ctx: RequestCtx):
        """
        List all Dashboard.

        Example:
            GET /Dashboard/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_Dashboard(self, ctx: RequestCtx):
        """
        Create a new Dashboard.

        Example:
            POST /Dashboard/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_Dashboard(self, ctx: RequestCtx, id: int):
        """
        Get a Dashboard by ID.

        Example:
            GET /Dashboard/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise DashboardNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_Dashboard(self, ctx: RequestCtx, id: int):
        """
        Update a Dashboard by ID.

        Example:
            PUT /Dashboard/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise DashboardNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_Dashboard(self, ctx: RequestCtx, id: int):
        """
        Delete a Dashboard by ID.

        Example:
            DELETE /Dashboard/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise DashboardNotFoundFault(item_id=id)

        return Response(status=204)