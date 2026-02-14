"""
Blogs module controllers (request handlers).

This file defines the HTTP endpoints for the blogs module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import BlogsNotFoundFault, BlogsOperationFault
from .services import BlogsService


class BlogsController(Controller):
    """
    Controller for blogs endpoints.

    Provides RESTful CRUD operations for blogs.
    """
    prefix = "/"
    tags = ["blogs"]

    def __init__(self, service: "BlogsService" = None):
        # Instantiate service directly if not injected
        self.service = service or BlogsService()

    @GET("/")
    async def list_blogs(self, ctx: RequestCtx):
        """
        Get list of blogs.

        Example:
            GET /blogs/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        raise BlogsOperationFault

    @POST("/")
    async def create_blogs(self, ctx: RequestCtx):
        """
        Create new blogs.

        Example:
            POST /blogs/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_blogs(self, ctx: RequestCtx, id: int):
        """
        Get single blogs by ID.

        Example:
            GET /blogs/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise BlogsNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_blogs(self, ctx: RequestCtx, id: int):
        """
        Update blogs by ID.

        Example:
            PUT /blogs/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise BlogsNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_blogs(self, ctx: RequestCtx, id: int):
        """
        Delete blogs by ID.

        Example:
            DELETE /blogs/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise BlogsNotFoundFault(item_id=id)

        return Response(status=204)