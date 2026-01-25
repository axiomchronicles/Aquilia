"""
Mode module controllers (request handlers).

This file defines the HTTP endpoints for the mode module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import ModeNotFoundFault
from .services import ModeService


class ModeController(Controller):
    """
    Controller for mode endpoints.

    Provides RESTful CRUD operations for mode.
    """
    prefix = "/mode"
    tags = ["mode"]

    def __init__(self):
        # Instantiate service directly instead of relying on DI
        # TODO: Remove this workaround once DI system is fully integrated
        self.service = ModeService()

    @GET("/")
    async def list_mode(self, ctx: RequestCtx):
        """
        Get list of mode.

        Example:
            GET /mode/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_mode(self, ctx: RequestCtx):
        """
        Create new mode.

        Example:
            POST /mode/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_mode(self, ctx: RequestCtx, id: int):
        """
        Get single mode by ID.

        Example:
            GET /mode/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise ModeNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_mode(self, ctx: RequestCtx, id: int):
        """
        Update mode by ID.

        Example:
            PUT /mode/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise ModeNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_mode(self, ctx: RequestCtx, id: int):
        """
        Delete mode by ID.

        Example:
            DELETE /mode/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise ModeNotFoundFault(item_id=id)

        return Response(status=204)