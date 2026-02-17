"""
Testaquilia module controllers (request handlers).

This file defines the HTTP endpoints for the testaquilia module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import TestaquiliaNotFoundFault
from .services import TestaquiliaService


class TestaquiliaController(Controller):
    """
    Controller for testaquilia endpoints.

    Provides RESTful CRUD operations for testaquilia.
    """
    prefix = "/"
    tags = ["testaquilia"]

    def __init__(self, service: "TestaquiliaService" = None):
        # Instantiate service directly if not injected
        self.service = service or TestaquiliaService()

    @GET("/")
    async def list_testaquilia(self, ctx: RequestCtx):
        """
        List all testaquilia.

        Example:
            GET /testaquilia/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_testaquilia(self, ctx: RequestCtx):
        """
        Create a new testaquilia.

        Example:
            POST /testaquilia/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_testaquilia(self, ctx: RequestCtx, id: int):
        """
        Get a testaquilia by ID.

        Example:
            GET /testaquilia/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise TestaquiliaNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_testaquilia(self, ctx: RequestCtx, id: int):
        """
        Update a testaquilia by ID.

        Example:
            PUT /testaquilia/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise TestaquiliaNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_testaquilia(self, ctx: RequestCtx, id: int):
        """
        Delete a testaquilia by ID.

        Example:
            DELETE /testaquilia/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise TestaquiliaNotFoundFault(item_id=id)

        return Response(status=204)