"""
Dummy module controllers (request handlers).

This file defines the HTTP endpoints for the dummy module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import DummyNotFoundFault
from .services import DummyService


class DummyController(Controller):
    """
    Controller for dummy endpoints.

    Provides RESTful CRUD operations for dummy.
    """
    prefix = "/"
    tags = ["dummy"]

    def __init__(self, service: "DummyService" = None):
        # Instantiate service directly if not injected
        self.service = service or DummyService()

    @GET("/")
    async def list_dummy(self, ctx: RequestCtx):
        """
        List all dummy.

        Example:
            GET /dummy/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_dummy(self, ctx: RequestCtx):
        """
        Create a new dummy.

        Example:
            POST /dummy/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_dummy(self, ctx: RequestCtx, id: int):
        """
        Get a dummy by ID.

        Example:
            GET /dummy/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise DummyNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_dummy(self, ctx: RequestCtx, id: int):
        """
        Update a dummy by ID.

        Example:
            PUT /dummy/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise DummyNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_dummy(self, ctx: RequestCtx, id: int):
        """
        Delete a dummy by ID.

        Example:
            DELETE /dummy/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise DummyNotFoundFault(item_id=id)

        return Response(status=204)