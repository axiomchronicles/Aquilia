"""
Complete Controller Example

Demonstrates the full Controller system with:
- DI constructor injection
- Multiple HTTP methods
- Path parameters
- Class-level and method-level pipelines
- Auth integration
- Session integration
"""

from typing import Annotated, List, Optional
from aquilia import (
    Controller,
    RequestCtx,
    GET, POST, PUT, DELETE,
    Response,
)
from aquilia.di import Inject


# ============================================================================
# Example 1: Basic Controller
# ============================================================================

class HealthController(Controller):
    """Simple health check controller."""
    
    prefix = "/health"
    
    @GET("/")
    async def check(self, ctx: RequestCtx):
        """Health check endpoint."""
        return Response({"status": "healthy", "version": "2.0.0"})
    
    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        """Ping endpoint."""
        return Response.text("pong")


# ============================================================================
# Example 2: Controller with DI
# ============================================================================

# Mock repository for demonstration
class UserRepository:
    """User data access."""
    
    async def list_all(self) -> List[dict]:
        return [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]
    
    async def get(self, user_id: int) -> Optional[dict]:
        users = await self.list_all()
        for user in users:
            if user["id"] == user_id:
                return user
        return None
    
    async def create(self, data: dict) -> dict:
        # In production, save to database
        return {"id": 3, **data}
    
    async def update(self, user_id: int, data: dict) -> Optional[dict]:
        user = await self.get(user_id)
        if user:
            user.update(data)
            return user
        return None
    
    async def delete(self, user_id: int) -> bool:
        # In production, delete from database
        return True


class UsersController(Controller):
    """
    Users CRUD controller with DI injection.
    
    Demonstrates:
    - Constructor injection
    - Path parameters with types
    - Multiple HTTP methods
    - RESTful routing
    """
    
    prefix = "/users"
    tags = ["users"]
    
    def __init__(self, repo: Annotated[UserRepository, Inject(tag="users")]):
        """
        Initialize controller with injected repository.
        
        Args:
            repo: User repository (injected by DI)
        """
        self.repo = repo
    
    @GET("/", summary="List all users")
    async def list(self, ctx: RequestCtx):
        """Get all users."""
        users = await self.repo.list_all()
        return Response({"users": users, "count": len(users)})
    
    @GET("/«id:int»", summary="Get user by ID")
    async def retrieve(self, ctx: RequestCtx, id: int):
        """
        Get a specific user.
        
        Args:
            id: User ID (from path)
        """
        user = await self.repo.get(id)
        if user is None:
            return Response({"error": "User not found"}, status_code=404)
        return Response(user)
    
    @POST("/", summary="Create user")
    async def create(self, ctx: RequestCtx):
        """Create a new user."""
        data = await ctx.json()
        user = await self.repo.create(data)
        return Response(user, status_code=201)
    
    @PUT("/«id:int»", summary="Update user")
    async def update(self, ctx: RequestCtx, id: int):
        """Update an existing user."""
        data = await ctx.json()
        user = await self.repo.update(id, data)
        if user is None:
            return Response({"error": "User not found"}, status_code=404)
        return Response(user)
    
    @DELETE("/«id:int»", summary="Delete user")
    async def delete(self, ctx: RequestCtx, id: int):
        """Delete a user."""
        success = await self.repo.delete(id)
        if not success:
            return Response({"error": "User not found"}, status_code=404)
        return Response({"message": "User deleted"}, status_code=204)


# ============================================================================
# Example 3: Controller with Auth & Sessions
# ============================================================================

class AccountController(Controller):
    """
    Account management with auth and sessions.
    
    Demonstrates:
    - Class-level pipeline (auth required for all methods)
    - Session access
    - Identity access
    """
    
    prefix = "/account"
    # pipeline = [Auth.guard()]  # Requires auth for all endpoints
    tags = ["account"]
    
    @GET("/me", summary="Get current user")
    async def me(self, ctx: RequestCtx):
        """
        Get current authenticated user.
        
        Requires authentication (from class-level pipeline).
        """
        # ctx.identity is available from auth middleware
        if ctx.identity is None:
            return Response({"error": "Not authenticated"}, status_code=401)
        
        return Response({
            "identity_id": ctx.identity.id,
            "username": ctx.identity.get_attribute("username"),
            "email": ctx.identity.get_attribute("email"),
            "roles": ctx.identity.get_attribute("roles", []),
        })
    
    @GET("/session", summary="Get session info")
    async def session(self, ctx: RequestCtx):
        """Get current session information."""
        if ctx.session is None:
            return Response({"error": "No active session"}, status_code=400)
        
        return Response({
            "session_id": str(ctx.session.id),
            "created_at": ctx.session.created_at.isoformat(),
            # Add more session info as needed
        })


# ============================================================================
# Example 4: Controller with Lifecycle Hooks
# ============================================================================

class DatabaseController(Controller):
    """
    Controller with lifecycle management.
    
    Demonstrates:
    - on_startup hook
    - on_shutdown hook
    - on_request hook
    - Singleton instantiation mode
    """
    
    prefix = "/db"
    instantiation_mode = "singleton"  # One instance for entire app
    
    def __init__(self):
        self.connection = None
        self.query_count = 0
    
    async def on_startup(self, ctx: RequestCtx):
        """Called once at app startup."""
        print("🔌 Opening database connection...")
        self.connection = "postgresql://localhost/mydb"  # Mock connection
        print(f"   ✓ Connected to {self.connection}")
    
    async def on_shutdown(self, ctx: RequestCtx):
        """Called once at app shutdown."""
        print("🔌 Closing database connection...")
        self.connection = None
        print(f"   ✓ Total queries: {self.query_count}")
    
    async def on_request(self, ctx: RequestCtx):
        """Called before each request."""
        self.query_count += 1
    
    @GET("/stats")
    async def stats(self, ctx: RequestCtx):
        """Get database statistics."""
        return Response({
            "connection": self.connection,
            "queries": self.query_count,
        })


# ============================================================================
# Example 5: Controller with Method-Level Pipeline Override
# ============================================================================

class AdminController(Controller):
    """
    Admin controller with flexible auth.
    
    Demonstrates:
    - Method-level pipeline override
    - Optional auth on specific endpoints
    """
    
    prefix = "/admin"
    # pipeline = [Auth.guard()]  # Default: require auth
    tags = ["admin"]
    
    @GET("/status")
    # pipeline=[Auth.optional()]  # Override: make auth optional
    async def status(self, ctx: RequestCtx):
        """Public admin status endpoint."""
        return Response({"status": "operational"})
    
    @GET("/users")
    # pipeline=[Auth.guard(), Auth.require_role("admin")]  # Require admin role
    async def list_users(self, ctx: RequestCtx):
        """List all users (admin only)."""
        return Response({"users": []})


# ============================================================================
# Example 6: WebSocket Controller
# ============================================================================

class ChatController(Controller):
    """
    WebSocket chat controller.
    
    Demonstrates:
    - WebSocket routes
    """
    
    prefix = "/chat"
    
    @WS("/room/«room_id»")
    async def room(self, ctx: RequestCtx, room_id: str):
        """
        WebSocket chat room.
        
        Args:
            room_id: Chat room ID
        """
        # In production, handle WebSocket connection
        return Response({"message": "WebSocket endpoint", "room": room_id})


# ============================================================================
# Usage in Manifest
# ============================================================================

"""
In your module.aq or AppManifest:

controllers:
  - examples.controllers_demo:HealthController
  - examples.controllers_demo:UsersController
  - examples.controllers_demo:AccountController
  - examples.controllers_demo:DatabaseController
  - examples.controllers_demo:AdminController
  - examples.controllers_demo:ChatController

controller_instantiation:
  database: singleton  # DatabaseController uses singleton mode
  # All others use per_request by default
"""


# ============================================================================
# Testing Controllers
# ============================================================================

async def test_controller_direct():
    """
    Test controllers directly (unit testing).
    
    Controllers are just classes, so they're easy to test!
    """
    # Create mock repository
    repo = UserRepository()
    
    # Instantiate controller
    controller = UsersController(repo=repo)
    
    # Create mock context
    from aquilia import Request
    request = Request(method="GET", path="/users", headers={}, query_params={})
    ctx = RequestCtx(request=request)
    
    # Call method directly
    response = await controller.list(ctx)
    
    print("Test response:", response)
    assert response.status_code == 200


if __name__ == "__main__":
    import asyncio
    
    print("\n" + "=" * 70)
    print("🎯 AQUILIA CONTROLLER EXAMPLES")
    print("=" * 70 + "\n")
    
    print("✅ Defined 6 example controllers:")
    print("  1. HealthController - Basic routes")
    print("  2. UsersController - CRUD with DI")
    print("  3. AccountController - Auth & Sessions")
    print("  4. DatabaseController - Lifecycle hooks")
    print("  5. AdminController - Pipeline overrides")
    print("  6. ChatController - WebSocket support")
    
    print("\n" + "=" * 70)
    print("🧪 Running direct test...")
    print("=" * 70 + "\n")
    
    asyncio.run(test_controller_direct())
    
    print("\n" + "=" * 70)
    print("✨ Controllers are the new first-class way to build Aquilia apps!")
    print("=" * 70 + "\n")
