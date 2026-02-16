"""
Blogs module controllers (request handlers).

This file demonstrates the new DI-Serializer integration features:

1. **FastAPI-style auto-injection**: Type-hint a parameter with a Serializer
   subclass and it's automatically parsed from the request body and validated.

2. **Response serialization**: Use `response_serializer` on decorators to
   auto-serialize handler return values.

3. **DI-aware defaults**: Serializer fields with CurrentUserDefault,
   CurrentRequestDefault, or InjectDefault are automatically resolved from
   the request context and DI container.

4. **Enhanced validators**: RangeValidator, CompoundValidator, ConditionalValidator
   provide powerful reusable validation logic.

Examples:
    - POST handler: Serializer auto-injected and validated
    - PUT handler: Partial updates with validated_data
    - GET handler: Response auto-serialized via decorator
"""

from aquilia import Controller, GET, POST, PUT, DELETE, PATCH, RequestCtx, Response
from .faults import BlogsNotFoundFault, BlogsOperationFault
from .services import BlogsService
from .serializers import (
    BlogPostSerializer,
    BlogPostUpdateSerializer,
    BlogPostListSerializer,
    BlogCommentSerializer,
    PaginatedBlogListSerializer,
)


class BlogsController(Controller):
    """
    Controller for blogs endpoints with DI-Serializer integration.

    Demonstrates:
    - FastAPI-style serializer auto-injection (type-hinted parameters)
    - Response serialization via decorator
    - DI-aware defaults in serializers
    - Enhanced validators
    """
    prefix = "/"
    tags = ["blogs"]

    def __init__(self, service: "BlogsService" = None):
        # Service is auto-injected via DI container
        self.service = service or BlogsService()

    @GET("/", response_serializer=BlogPostListSerializer)
    async def list_blogs(self, ctx: RequestCtx):
        """
        List all blogs with response serialization.

        The response_serializer automatically converts the list of blog
        objects to serialized dicts via BlogPostListSerializer.

        Example:
            GET /blogs/ 
            -> [{"id": 1, "title": "...", "excerpt": "...", ...}, ...]
        """
        items = await self.service.get_all()
        # Return raw objects - response_serializer handles conversion
        return items

    @POST("/")
    async def create_blog(
        self, 
        ctx: RequestCtx,
        serializer: BlogPostSerializer,  # ← FastAPI-style auto-injection!
    ):
        """
        Create a new blog post with auto-validation.

        **FastAPI-style serializer injection**: The `serializer` parameter
        is automatically:
        1. Detected as a Serializer subclass
        2. Instantiated with request body data
        3. Validated via `.is_valid(raise_fault=True)`
        4. Injected as a full serializer instance (can call .save())

        The serializer's DI-aware defaults are automatically resolved:
        - `author_id`: Populated from CurrentUserDefault (request.state["identity"])
        - `client_ip`: Populated from CurrentRequestDefault (request.client_ip)

        Example:
            POST /blogs/
            Body: {
                "title": "My First Post",
                "content": "This is the content...",
                "excerpt": "A brief excerpt",
                "published": true
            }
            
            The serializer automatically adds:
            - author_id: 42  (from authenticated user)
            - client_ip: "192.168.1.1"  (from request)
            
            Response: {"id": 1, "title": "My First Post", "author_id": 42, ...}
        """
        # serializer.validated_data already includes DI-injected defaults
        item = await self.service.create(serializer.validated_data)
        return Response.json(item, status=201)

    @POST("/alt")
    async def create_blog_alt(
        self, 
        ctx: RequestCtx,
        post_data: BlogPostSerializer,  # ← Parameter name doesn't end with _serializer
    ):
        """
        Alternative syntax: inject validated_data directly.

        When the parameter name does NOT end with "_serializer" or "_ser",
        the engine injects `serializer.validated_data` instead of the full
        serializer instance.

        This is more concise when you don't need access to .save() or .errors.

        Example:
            POST /blogs/alt
            Body: {"title": "...", "content": "..."}
            
            The `post_data` parameter receives the validated dict directly,
            with DI defaults already injected.
        """
        item = await self.service.create(post_data)
        return Response.json(item, status=201)

    @GET("/«id:int»", response_serializer=BlogPostSerializer)
    async def get_blog(self, ctx: RequestCtx, id: int):
        """
        Get a blog by ID with response serialization.

        The response_serializer automatically converts the blog object
        to a serialized dict.

        Example:
            GET /blogs/1 
            -> {
                "id": 1, 
                "title": "My Post",
                "content": "...",
                "author_id": 42,
                "created_at": "2026-02-16T10:30:00Z",
                ...
            }
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise BlogsNotFoundFault(item_id=id)
        # Return raw object - response_serializer handles conversion
        return item

    @PUT("/«id:int»")
    async def update_blog(
        self, 
        ctx: RequestCtx, 
        id: int,
        serializer: BlogPostSerializer,  # ← Auto-validated
    ):
        """
        Full update of a blog post.

        Uses the full BlogPostSerializer for validation.

        Example:
            PUT /blogs/1
            Body: {"title": "Updated", "content": "New content", ...}
            -> {"id": 1, "title": "Updated", ...}
        """
        item = await self.service.update(id, serializer.validated_data)
        if not item:
            raise BlogsNotFoundFault(item_id=id)
        return Response.json(item)

    @PATCH("/«id:int»")
    async def partial_update_blog(
        self, 
        ctx: RequestCtx, 
        id: int,
        update_data: BlogPostUpdateSerializer,  # ← Partial update serializer
    ):
        """
        Partial update of a blog post.

        Uses BlogPostUpdateSerializer where all fields are optional.
        The `updated_by` field is auto-populated via CurrentUserDefault.

        Example:
            PATCH /blogs/1
            Body: {"title": "New Title"}
            
            The serializer automatically adds:
            - updated_by: 42  (from authenticated user)
            
            Only the provided fields are updated.
        """
        item = await self.service.update(id, update_data)
        if not item:
            raise BlogsNotFoundFault(item_id=id)
        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_blog(self, ctx: RequestCtx, id: int):
        """
        Delete a blog by ID.

        Example:
            DELETE /blogs/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise BlogsNotFoundFault(item_id=id)
        return Response(status=204)

    @POST("/«id:int»/comments")
    async def create_comment(
        self,
        ctx: RequestCtx,
        id: int,
        comment_ser: BlogCommentSerializer,  # ← _ser suffix = full serializer
    ):
        """
        Create a comment on a blog post.

        Demonstrates:
        - ConditionalValidator: Email is only validated if notify_reply=True
        - DI-aware defaults: commenter_id auto-populated (optional for anonymous)
        - Parameter naming: ends with _ser, so full serializer is injected

        Example:
            POST /blogs/1/comments
            Body: {
                "post_id": 1,
                "author_name": "Kai",
                "content": "Great post!",
                "notify_reply": true,
                "email": "kai@example.com"
            }
            
            If notify_reply=False, email validation is skipped.
            If authenticated, commenter_id is auto-populated.
        """
        # Validate post exists
        post = await self.service.get_by_id(id)
        if not post:
            raise BlogsNotFoundFault(item_id=id)
        
        # Add comment (in real app, this would go to a comments service)
        comment = comment_ser.validated_data
        comment["id"] = 1  # Mock ID
        comment["created_at"] = "2026-02-16T10:30:00Z"
        
        return Response.json(comment, status=201)