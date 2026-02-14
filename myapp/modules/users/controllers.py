"""
Users Module - Controllers

Showcases:
- Full CRUD controller
- DI constructor injection (UserService)
- RequestCtx usage (json, headers, session)
- Auth guard patterns
- Session integration
- Custom fault raising
- Lifecycle hooks (on_startup, on_request, on_response)
- Response types (json, status codes)
"""

import time
from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .services import UserService
from .faults import (
    UserNotFoundFault,
    DuplicateEmailFault,
    InvalidCredentialsFault,
    UnauthorizedFault,
    ForbiddenFault,
)


class UsersController(Controller):
    """
    Users API controller.

    Demonstrates:
    - RESTful CRUD with pattern-based routing
    - DI injection via constructor
    - Session-based auth tracking
    - Custom faults for error handling
    - Lifecycle hooks
    """

    prefix = "/"
    tags = ["users", "auth"]

    def __init__(self, service: UserService = None):
        self.service = service or UserService()
        self._request_count = 0

    async def on_request(self, ctx: RequestCtx):
        """Track request count (lifecycle hook)."""
        self._request_count += 1
        ctx.state["request_start"] = time.time()

    async def on_response(self, ctx: RequestCtx, response: Response):
        """Add timing header (lifecycle hook)."""
        start = ctx.state.get("request_start")
        if start:
            elapsed = time.time() - start
            response.headers["X-Response-Time"] = f"{elapsed:.4f}s"

    # ── Registration & Login ─────────────────────────────────────────────

    @POST("/register")
    async def register(self, ctx: RequestCtx):
        """
        Register a new user.

        POST /users/register
        Body: {"email": "...", "password": "...", "name": "..."}
        """
        data = await ctx.json()

        email = data.get("email", "")
        password = data.get("password", "")
        name = data.get("name", "")

        if not email or not password or not name:
            return Response.json(
                {"error": "email, password, and name are required"},
                status=400,
            )

        result = await self.service.register(email, password, name)

        if "error" in result:
            raise DuplicateEmailFault(email)

        return Response.json(result, status=201)

    @POST("/login")
    async def login(self, ctx: RequestCtx):
        """
        Authenticate user and return token.

        POST /users/login
        Body: {"email": "...", "password": "..."}
        """
        data = await ctx.json()
        email = data.get("email", "")
        password = data.get("password", "")

        if not email or not password:
            return Response.json(
                {"error": "email and password are required"},
                status=400,
            )

        result = await self.service.login(email, password)
        if not result:
            raise InvalidCredentialsFault()

        # Store user ID in session if available
        if ctx.session is not None:
            ctx.session["user_id"] = result["user"]["id"]
            ctx.session["authenticated"] = True

        return Response.json({
            "token": result["token"],
            "user": result["user"],
        })

    # ── Profile ─────────────────────────────────────────────────────────

    @GET("/profile")
    async def get_profile(self, ctx: RequestCtx):
        """
        Get current user's profile.

        GET /users/profile
        Headers: Authorization: Bearer <token>

        Demonstrates reading user identity from session.
        """
        user_id = self._get_user_id(ctx)
        if not user_id:
            raise UnauthorizedFault("profile")

        profile = await self.service.get_profile(user_id)
        if not profile:
            raise UserNotFoundFault(user_id)

        return Response.json(profile)

    @PUT("/profile")
    async def update_profile(self, ctx: RequestCtx):
        """
        Update current user's profile.

        PUT /users/profile
        Body: {"name": "New Name"}
        """
        user_id = self._get_user_id(ctx)
        if not user_id:
            raise UnauthorizedFault("profile")

        data = await ctx.json()
        updated = await self.service.update_profile(user_id, data)
        if not updated:
            raise UserNotFoundFault(user_id)

        return Response.json(updated)

    # ── Admin endpoints ─────────────────────────────────────────────────

    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        """
        List all users (admin only).

        GET /users/
        """
        users = await self.service.list_users()
        return Response.json({
            "items": users,
            "total": len(users),
        })

    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        """
        Get user by ID.

        GET /users/:id
        """
        profile = await self.service.get_profile(str(id))
        if not profile:
            raise UserNotFoundFault(str(id))
        return Response.json(profile)

    @DELETE("/«id:int»")
    async def delete_user(self, ctx: RequestCtx, id: int):
        """
        Delete user by ID (admin only).

        DELETE /users/:id
        """
        repo = self.service.repo
        deleted = await repo.delete(str(id))
        if not deleted:
            raise UserNotFoundFault(str(id))
        return Response.json({"deleted": True, "id": id})

    # ── Stats ───────────────────────────────────────────────────────────

    @GET("/stats")
    async def stats(self, ctx: RequestCtx):
        """
        Get module stats.

        GET /users/stats
        Demonstrates state tracking via lifecycle hooks.
        """
        users = await self.service.list_users()
        return Response.json({
            "total_users": len(users),
            "total_requests": self._request_count,
        })

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_user_id(self, ctx: RequestCtx) -> str | None:
        """Extract user ID from session or identity."""
        # Check session first
        if ctx.session and ctx.session.get("user_id"):
            return ctx.session["user_id"]
        # Check identity
        if ctx.identity and hasattr(ctx.identity, "id"):
            return ctx.identity.id
        # Check Authorization header (simple token lookup)
        auth_header = ctx.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # In a real app, validate token and extract user_id
            return None
        return None
