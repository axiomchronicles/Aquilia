"""
Modern Controller Example - Complete application with controllers.

This example demonstrates:
- Controller-based routing with patterns
- DI integration
- CRUD operations
- Request context usage
- Response handling
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.manifest import AppManifest
from typing import Annotated, Dict, List
from dataclasses import dataclass, field


# ============================================================================
# Domain Models
# ============================================================================

@dataclass
class User:
    """User model."""
    id: int
    name: str
    email: str
    active: bool = True


# ============================================================================
# Services (for DI demonstration)
# ============================================================================

class UserService:
    """Simple in-memory user service."""
    
    def __init__(self):
        self.users: Dict[int, User] = {
            1: User(1, "Alice", "alice@example.com"),
            2: User(2, "Bob", "bob@example.com"),
        }
        self.next_id = 3
    
    def list_all(self) -> List[User]:
        """Get all users."""
        return list(self.users.values())
    
    def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def create(self, name: str, email: str) -> User:
        """Create a new user."""
        user = User(self.next_id, name, email)
        self.users[user.id] = user
        self.next_id += 1
        return user
    
    def update(self, user_id: int, name: str = None, email: str = None) -> User | None:
        """Update user."""
        user = self.users.get(user_id)
        if user:
            if name:
                user.name = name
            if email:
                user.email = email
        return user
    
    def delete(self, user_id: int) -> bool:
        """Delete user."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


# ============================================================================
# Controllers
# ============================================================================

class UsersController(Controller):
    """
    Users Controller - RESTful CRUD for users.
    
    Demonstrates:
    - DI injection via constructor
    - Pattern-based routing with types
    - Full CRUD operations
    - JSON responses
    """
    
    prefix = "/users"
    tags = ["users"]
    
    # Note: In real app, service would be injected via DI
    # def __init__(self, service: Annotated[UserService, Inject()]):
    #     self.service = service
    
    def __init__(self):
        """Initialize with service (temporary without DI)."""
        self.service = UserService()
    
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        """
        List all users.
        
        GET /users
        """
        users = self.service.list_all()
        return Response.json({
            "users": [
                {"id": u.id, "name": u.name, "email": u.email, "active": u.active}
                for u in users
            ],
            "total": len(users)
        })
    
    @POST("/")
    async def create_user(self, ctx: RequestCtx):
        """
        Create a new user.
        
        POST /users
        Body: {"name": "...", "email": "..."}
        """
        data = await ctx.json()
        
        # Validation
        if "name" not in data or "email" not in data:
            return Response.json({
                "error": "Missing required fields: name, email"
            }, status=400)
        
        user = self.service.create(data["name"], data["email"])
        
        return Response.json({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created": True
        }, status=201)
    
    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        """
        Get user by ID.
        
        GET /users/123
        """
        user = self.service.get_by_id(id)
        
        if not user:
            return Response.json({
                "error": f"User {id} not found"
            }, status=404)
        
        return Response.json({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "active": user.active
        })
    
    @PUT("/«id:int»")
    async def update_user(self, ctx: RequestCtx, id: int):
        """
        Update user by ID.
        
        PUT /users/123
        Body: {"name": "...", "email": "..."}
        """
        data = await ctx.json()
        
        user = self.service.update(
            id,
            name=data.get("name"),
            email=data.get("email")
        )
        
        if not user:
            return Response.json({
                "error": f"User {id} not found"
            }, status=404)
        
        return Response.json({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "updated": True
        })
    
    @DELETE("/«id:int»")
    async def delete_user(self, ctx: RequestCtx, id: int):
        """
        Delete user by ID.
        
        DELETE /users/123
        """
        deleted = self.service.delete(id)
        
        if not deleted:
            return Response.json({
                "error": f"User {id} not found"
            }, status=404)
        
        return Response(status=204)


class HealthController(Controller):
    """
    Health check controller.
    
    Simple controller without DI.
    """
    
    prefix = "/health"
    tags = ["health"]
    
    @GET("/")
    async def health_check(self, ctx: RequestCtx):
        """
        Health check endpoint.
        
        GET /health
        """
        return Response.json({
            "status": "healthy",
            "service": "aquilia-demo",
            "version": "1.0.0"
        })
    
    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        """
        Ping endpoint.
        
        GET /health/ping
        """
        return Response.json({"pong": True})


class DocsController(Controller):
    """
    API documentation controller.
    
    Shows how to return HTML responses.
    """
    
    prefix = "/docs"
    tags = ["docs"]
    
    @GET("/")
    async def index(self, ctx: RequestCtx):
        """
        API documentation index.
        
        GET /docs
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Aquilia Demo API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #0066cc; }
            </style>
        </head>
        <body>
            <h1>Aquilia Demo API</h1>
            <p>Modern controller-based API with pattern routing</p>
            
            <h2>Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> /health - Health check
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /users - List all users
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /users - Create user
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /users/:id - Get user by ID
            </div>
            
            <div class="endpoint">
                <span class="method">PUT</span> /users/:id - Update user
            </div>
            
            <div class="endpoint">
                <span class="method">DELETE</span> /users/:id - Delete user
            </div>
        </body>
        </html>
        """
        return Response(html, content_type="text/html")


# ============================================================================
# Application Manifest
# ============================================================================

class DemoManifest(AppManifest):
    """Application manifest for the demo."""
    
    name = "demo"
    version = "1.0.0"
    description = "Demo application with modern controllers"
    
    # Controllers to load
    controllers = [
        "examples.controllers_modern:UsersController",
        "examples.controllers_modern:HealthController",
        "examples.controllers_modern:DocsController",
    ]
    
    # Services to register (would be used by DI)
    services = [
        "examples.controllers_modern:UserService",
    ]


# ============================================================================
# Main - Run the server
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Aquilia Modern Controllers Demo")
    print("=" * 70)
    print()
    print("This example demonstrates the new controller architecture:")
    print("  ✓ Pattern-based routing (/users/«id:int»)")
    print("  ✓ Clean controller classes")
    print("  ✓ Type-safe parameters")
    print("  ✓ RESTful CRUD operations")
    print()
    print("To run with a server:")
    print("  1. Create a server with DemoManifest")
    print("  2. Start with: uvicorn app:server.app")
    print()
    print("Available routes:")
    print("  GET    /health       - Health check")
    print("  GET    /health/ping  - Ping endpoint")
    print("  GET    /users        - List users")
    print("  POST   /users        - Create user")
    print("  GET    /users/1      - Get user by ID")
    print("  PUT    /users/1      - Update user")
    print("  DELETE /users/1      - Delete user")
    print("  GET    /docs         - API documentation")
    print()
    print("=" * 70)
