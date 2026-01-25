"""
Mymodule module controllers (request handlers).

This file defines the HTTP endpoints for the mymodule module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import MymoduleNotFoundFault
from .services import MymoduleService


class MymoduleController(Controller):
    """
    Controller for mymodule endpoints.

    Provides RESTful CRUD operations for mymodule.
    """
    prefix = "/mymodule"
    tags = ["mymodule"]

    def __init__(self, service: MymoduleService):
        self.service = service

    @GET("/")
    async def list_mymodule(self, ctx: RequestCtx):
        """
        Get list of mymodule.

        Example:
            GET /mymodule/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_mymodule(self, ctx: RequestCtx):
        """
        Create new mymodule.

        Example:
            POST /mymodule/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_mymodule(self, ctx: RequestCtx, id: int):
        """
        Get single mymodule by ID.

        Example:
            GET /mymodule/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise MymoduleNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_mymodule(self, ctx: RequestCtx, id: int):
        """
        Update mymodule by ID.

        Example:
            PUT /mymodule/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise MymoduleNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_mymodule(self, ctx: RequestCtx, id: int):
        """
        Delete mymodule by ID.

        Example:
            DELETE /mymodule/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise MymoduleNotFoundFault(item_id=id)

        return Response(status=204)