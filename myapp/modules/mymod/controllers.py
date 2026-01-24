"""
Mymod module controllers (request handlers).

This file defines the HTTP endpoints for the mymod module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from typing import Annotated
# from aquilia.di import Inject  # Uncomment for DI
# from .services import MymodService
from .faults import MymodNotFoundFault


class MymodController(Controller):
    """
    Controller for mymod endpoints.

    Provides RESTful CRUD operations for mymod.
    """

    prefix = "/mymod"
    tags = ["mymod"]

    # Uncomment for DI injection:
    # def __init__(self, service: Annotated[MymodService, Inject()]):
    #     self.service = service

    @GET("/")
    async def list_mymod(self, ctx: RequestCtx):
        """
        Get list of mymod.

        Example:
            GET /mymod/ -> {"items": [...], "total": 0}
        """
        # TODO: Implement list logic
        # items = await self.service.get_all()
        items = []

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_mymod(self, ctx: RequestCtx):
        """
        Create new mymod.

        Example:
            POST /mymod/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()

        # TODO: Validate and create
        # item = await self.service.create(data)
        item = {"id": 1, **data}

        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_mymod(self, ctx: RequestCtx, id: int):
        """
        Get single mymod by ID.

        Example:
            GET /mymod/1 -> {"id": 1, "name": "Example"}
        """
        # TODO: Fetch by ID
        # item = await self.service.get_by_id(id)
        # if not item:
        #     raise MymodNotFoundFault(item_id=id)

        item = {"id": id, "name": "Example"}

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_mymod(self, ctx: RequestCtx, id: int):
        """
        Update mymod by ID.

        Example:
            PUT /mymod/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()

        # TODO: Update logic
        # item = await self.service.update(id, data)
        # if not item:
        #     return Response.json({"error": "Not found"}, status=404)

        item = {"id": id, **data}

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_mymod(self, ctx: RequestCtx, id: int):
        """
        Delete mymod by ID.

        Example:
            DELETE /mymod/1 -> 204 No Content
        """
        # TODO: Delete logic
        # deleted = await self.service.delete(id)
        # if not deleted:
        #     return Response.json({"error": "Not found"}, status=404)

        return Response(status=204)