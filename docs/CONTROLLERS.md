# Aquilia Controllers - Complete Guide

## Overview

**Controllers** are the new first-class way to build request handlers in Aquilia v2.0. They replace function-based `@flow` handlers with a powerful class-based system that provides:

- **Constructor DI injection** - Dependencies resolved automatically
- **Type-safe routing** - Path parameters with type conversion
- **Pipeline composition** - Class-level and method-level middlewares
- **Lifecycle hooks** - Startup, shutdown, per-request hooks
- **Zero side effects** - Declared in manifests, lazy-loaded
- **Static analysis** - Routes extracted at compile-time
- **Deep integration** - Auth, Sessions, DI, Faults, OpenAPI

## Quick Start

### Basic Controller

```python
from aquilia import Controller, GET, POST, RequestCtx, Response

class HealthController(Controller):
    prefix = "/health"
    
    @GET("/")
    async def check(self, ctx: RequestCtx):
        return Response({"status": "healthy"})
```

### Controller with DI

```python
from aquilia import Controller, GET, RequestCtx, Response
from typing import Annotated
from aquilia.di import Inject

class UsersController(Controller):
    prefix = "/users"
    
    def __init__(self, repo: Annotated[UserRepo, Inject(tag="users")]):
        self.repo = repo
    
    @GET("/")
    async def list(self, ctx: RequestCtx):
        users = await self.repo.list_all()
        return Response({"users": users})
    
    @GET("/«id:int»")
    async def retrieve(self, ctx: RequestCtx, id: int):
        user = await self.repo.get(id)
        return Response(user)
```

## Core Concepts

### 1. Controller Base Class

All controllers inherit from `Controller`:

```python
class MyController(Controller):
    prefix = "/api"              # URL prefix for all routes
    pipeline = [Auth.guard()]    # Class-level middleware
    tags = ["api", "v1"]         # OpenAPI tags
    instantiation_mode = "per_request"  # or "singleton"
```

**Class Attributes:**
- `prefix`: URL prefix applied to all methods
- `pipeline`: List of middleware/guards for all methods
- `tags`: OpenAPI tags
- `instantiation_mode`: How controller is instantiated

### 2. Method Decorators

HTTP method decorators define routes:

```python
@GET(path, **metadata)
@POST(path, **metadata)
@PUT(path, **metadata)
@PATCH(path, **metadata)
@DELETE(path, **metadata)
@HEAD(path, **metadata)
@OPTIONS(path, **metadata)
@WS(path, **metadata)  # WebSocket
```

**Decorator Arguments:**
- `path`: URL path template (optional, derives from method name)
- `pipeline`: Method-level middleware (overrides class-level)
- `summary`: OpenAPI summary
- `description`: OpenAPI description
- `tags`: Additional tags
- `deprecated`: Mark as deprecated
- `response_model`: Response type
- `status_code`: Default status code

### 3. Path Parameters

Path parameters use Aquilia's pattern syntax:

```python
# Simple parameter (string)
@GET("/users/«username»")
async def get_user(self, ctx, username: str):
    ...

# Typed parameter
@GET("/users/«id:int»")
async def get_user(self, ctx, id: int):
    ...

# Multiple parameters
@GET("/posts/«post_id:int»/comments/«comment_id:int»")
async def get_comment(self, ctx, post_id: int, comment_id: int):
    ...
```

**Supported Types:**
- `int` - Integer
- `str` - String (default)
- `float` - Float
- `bool` - Boolean
- `path` - Path segment (allows slashes)

### 4. RequestCtx

Every controller method receives `RequestCtx` as first parameter:

```python
async def my_method(self, ctx: RequestCtx):
    # Access request
    ctx.request          # Request object
    ctx.method           # HTTP method
    ctx.path             # Request path
    ctx.headers          # Headers dict
    ctx.query_params     # Query parameters
    
    # Access auth & session (if available)
    ctx.identity         # Authenticated identity
    ctx.session          # Active session
    
    # Access DI container
    ctx.container        # Request-scoped container
    
    # Custom state
    ctx.state["key"]     # Additional state
    
    # Parse body
    data = await ctx.json()
    form = await ctx.form()
```

### 5. Constructor Injection

Controllers support DI through constructor parameters:

```python
from typing import Annotated
from aquilia.di import Inject

class MyController(Controller):
    def __init__(
        self,
        db: Annotated[Database, Inject()],
        cache: Annotated[Cache, Inject(tag="redis")],
        config: Annotated[Config, Inject()],
    ):
        self.db = db
        self.cache = cache
        self.config = config
```

**DI Resolution:**
- Per-request mode: Controller instantiated per request with request-scoped DI
- Singleton mode: Controller instantiated once with app-scoped DI

## Advanced Features

### Lifecycle Hooks

Controllers can define lifecycle hooks:

```python
class DatabaseController(Controller):
    instantiation_mode = "singleton"
    
    async def on_startup(self, ctx: RequestCtx):
        """Called once at app startup (singleton only)."""
        self.connection = await open_db_connection()
    
    async def on_shutdown(self, ctx: RequestCtx):
        """Called once at app shutdown (singleton only)."""
        await self.connection.close()
    
    async def on_request(self, ctx: RequestCtx):
        """Called before each request."""
        self.request_count += 1
    
    async def on_response(self, ctx: RequestCtx, response):
        """Called after each request."""
        response.headers["X-Request-Count"] = str(self.request_count)
        return response
```

### Pipeline Composition

Combine class-level and method-level pipelines:

```python
class AdminController(Controller):
    prefix = "/admin"
    pipeline = [Auth.guard()]  # All methods require auth by default
    
    @GET("/status", pipeline=[])  # Override: no auth required
    async def status(self, ctx):
        return Response({"status": "ok"})
    
    @GET("/users", pipeline=[Auth.require_role("admin")])
    async def users(self, ctx):
        # Requires auth (from class) + admin role (from method)
        return Response({"users": []})
```

### Auth & Session Integration

Controllers integrate seamlessly with Auth and Sessions:

```python
class AccountController(Controller):
    prefix = "/account"
    pipeline = [Auth.guard()]  # Require authentication
    
    @GET("/me")
    async def me(self, ctx: RequestCtx):
        # ctx.identity is available
        return Response({
            "user_id": ctx.identity.id,
            "username": ctx.identity.get_attribute("username"),
            "roles": ctx.identity.get_attribute("roles"),
        })
    
    @GET("/session")
    async def session(self, ctx: RequestCtx):
        # ctx.session is available
        return Response({
            "session_id": str(ctx.session.id),
            "expires": ctx.session.expires_at.isoformat(),
        })
```

### Instantiation Modes

**Per-Request (Default):**
```python
class UsersController(Controller):
    instantiation_mode = "per_request"
    
    def __init__(self, repo: UserRepo):
        self.repo = repo  # New repo instance per request
```

**Singleton:**
```python
class CacheController(Controller):
    instantiation_mode = "singleton"
    
    def __init__(self, cache: Cache):
        self.cache = cache  # Shared cache instance
```

**Choosing the Right Mode:**
- Use **per_request** when:
  - Controller holds request-specific state
  - Need request-scoped dependencies
  - Default safe choice
- Use **singleton** when:
  - Controller is stateless
  - Holds app-level resources (DB connections, caches)
  - Performance optimization

## Manifest Declaration

Controllers must be declared in your manifest:

```yaml
# module.aq
controllers:
  - modules.users.controllers:UsersController
  - modules.auth.controllers:AuthController
  - modules.admin.controllers:AdminController

controller_instantiation:
  users: per_request
  auth: per_request
  admin: singleton
```

Or in Python manifest:

```python
from aquilia import AppManifest

manifest = AppManifest(
    name="my_app",
    version="1.0.0",
    controllers=[
        "modules.users.controllers:UsersController",
        "modules.auth.controllers:AuthController",
    ],
    controller_config={
        "admin": {"instantiation_mode": "singleton"},
    },
)
```

## Compilation & Routing

### Compile-Time Analysis

`aq compile` analyzes controllers and generates routing metadata:

```bash
aq compile
```

This:
1. Reads controller declarations from manifest
2. Lazily imports controller classes
3. Extracts route metadata from decorators
4. Computes route specificity
5. Detects conflicts
6. Generates `patterns.crous` with optimized routing data
7. Generates OpenAPI documentation

### Route Specificity

Routes are ranked by specificity to resolve ambiguity:

```python
# Specificity scores (higher = more specific):
# /users/admin          -> 200  (2 static segments)
# /users/«id:int»       -> 150  (1 static + 1 typed param)
# /users/«name»         -> 125  (1 static + 1 untyped param)
# /«category»/«slug»    -> 50   (2 untyped params)
```

### Conflict Detection

Compiler detects route conflicts:

```python
# Conflict: Same method and path
class Users1(Controller):
    @GET("/users/«id:int»")
    async def get(self, ctx, id: int): ...

class Users2(Controller):
    @GET("/users/«user_id:int»")  # CONFLICT!
    async def fetch(self, ctx, user_id: int): ...
```

Error:
```
RouteConflictError: Route conflict detected:
  GET /users/«id:int» in Users1.get
  GET /users/«user_id:int» in Users2.fetch
Suggestion: Use different paths or namespaces
```

## Migration from @flow

### Old Style (Function-based Flow)

```python
from aquilia import flow, Response

@flow("/users")
async def list_users(ctx):
    return Response({"users": []})

@flow("/users/{id:int}")
async def get_user(ctx, id: int):
    return Response({"user": {"id": id}})
```

### New Style (Controller)

```python
from aquilia import Controller, GET, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"
    
    @GET("/")
    async def list(self, ctx: RequestCtx):
        return Response({"users": []})
    
    @GET("/«id:int»")
    async def retrieve(self, ctx: RequestCtx, id: int):
        return Response({"user": {"id": id}})
```

### Automatic Migration

Use `aq migrate-flows` to convert function-based flows:

```bash
aq migrate-flows modules/users/flows.py
```

This generates Controller-based equivalents.

### Compatibility Layer

For gradual migration, both styles work together:

```python
# Old flows still work
@flow("/legacy")
async def legacy_handler(ctx):
    return Response({"type": "legacy"})

# New controllers
class ModernController(Controller):
    prefix = "/modern"
    
    @GET("/")
    async def handler(self, ctx):
        return Response({"type": "modern"})
```

## Testing Controllers

Controllers are easy to test:

```python
import pytest
from your_module import UsersController, UserRepository

@pytest.mark.asyncio
async def test_list_users():
    # Arrange
    repo = UserRepository()  # or mock
    controller = UsersController(repo=repo)
    
    # Create mock context
    from aquilia import Request, RequestCtx
    request = Request(method="GET", path="/users", headers={}, query_params={})
    ctx = RequestCtx(request=request)
    
    # Act
    response = await controller.list(ctx)
    
    # Assert
    assert response.status_code == 200
    data = response.body
    assert "users" in data
```

### With Dependency Injection

```python
@pytest.mark.asyncio
async def test_with_di():
    from aquilia import Container
    from aquilia.controller import ControllerFactory, InstantiationMode
    
    # Setup DI container
    container = Container()
    container.register(UserRepository)
    
    # Create controller via factory
    factory = ControllerFactory(app_container=container)
    controller = await factory.create(
        UsersController,
        mode=InstantiationMode.PER_REQUEST,
        request_container=container,
    )
    
    # Test
    ctx = ...
    response = await controller.list(ctx)
    assert response.status_code == 200
```

## Best Practices

### 1. Organize by Resource

```
modules/
  users/
    controllers.py    # UsersController
    models.py         # User model
    repository.py     # UserRepository
  posts/
    controllers.py    # PostsController
    models.py         # Post model
    repository.py     # PostRepository
```

### 2. Use Type Annotations

```python
from typing import List, Optional

@GET("/users")
async def list(self, ctx: RequestCtx) -> Response:
    users: List[User] = await self.repo.list_all()
    return Response({"users": users})
```

### 3. Leverage DI

```python
# Good: Inject dependencies
class UsersController(Controller):
    def __init__(self, repo: UserRepository, cache: Cache):
        self.repo = repo
        self.cache = cache

# Avoid: Creating dependencies manually
class UsersController(Controller):
    def __init__(self):
        self.repo = UserRepository()  # Bad!
```

### 4. Keep Controllers Thin

```python
# Good: Delegate to service layer
class UsersController(Controller):
    def __init__(self, service: UserService):
        self.service = service
    
    @POST("/")
    async def create(self, ctx):
        data = await ctx.json()
        user = await self.service.create_user(data)
        return Response(user, status_code=201)

# Avoid: Business logic in controller
class UsersController(Controller):
    @POST("/")
    async def create(self, ctx):
        data = await ctx.json()
        # Validation
        if not data.get("email"):
            ...
        # Hashing
        password_hash = ...
        # Database
        user = ...
        # Email
        send_email(...)
        # Too much logic here!
```

### 5. Use Descriptive Method Names

```python
# Good
@GET("/")
async def list(self, ctx): ...

@GET("/«id:int»")
async def retrieve(self, ctx, id): ...

@POST("/")
async def create(self, ctx): ...

@PUT("/«id:int»")
async def update(self, ctx, id): ...

@DELETE("/«id:int»")
async def delete(self, ctx, id): ...

# These names clearly indicate CRUD operations
```

## OpenAPI Integration

Controllers automatically generate OpenAPI documentation:

```python
class UsersController(Controller):
    prefix = "/users"
    tags = ["users"]
    
    @GET(
        "/",
        summary="List all users",
        description="Returns a paginated list of all users in the system.",
        response_model=UserListResponse,
    )
    async def list(self, ctx: RequestCtx):
        """
        Additional description from docstring.
        
        Can include markdown formatting.
        """
        ...
```

Access generated OpenAPI docs:
```bash
aq compile  # Generates openapi.json
```

## Performance Considerations

### Per-Request Overhead

Per-request instantiation has minimal overhead (~1-5µs per request) but provides:
- Request isolation
- Safe request-scoped dependencies
- No shared state bugs

### Singleton Optimization

For stateless controllers with high traffic:

```python
class HighTrafficController(Controller):
    instantiation_mode = "singleton"
    
    def __init__(self, db: Database):
        self.db = db  # Shared DB pool
    
    @GET("/data")
    async def get_data(self, ctx):
        # No per-request allocation of controller
        ...
```

### Async Best Practices

```python
# Good: Use async for I/O
@GET("/users")
async def list(self, ctx):
    users = await self.repo.list_all()  # Async DB call
    return Response({"users": users})

# Avoid: Blocking I/O in async
@GET("/users")
async def list(self, ctx):
    users = self.repo.list_all_blocking()  # Blocks event loop!
    return Response({"users": users})
```

## Troubleshooting

### Controller not found

**Error:** `ControllerNotFoundError: modules.users.flows:UsersController`

**Solution:** Check manifest declaration:
```yaml
controllers:
  - modules.users.flows:UsersController  # Correct import path?
```

### Route conflict

**Error:** `RouteConflictError: Duplicate route GET /users/«id:int»`

**Solution:** Make paths more specific or use namespaces:
```python
# Option 1: More specific paths
@GET("/users/by-id/«id:int»")
@GET("/users/by-name/«name»")

# Option 2: Different prefixes
class UsersController:
    prefix = "/api/v1/users"

class LegacyUsersController:
    prefix = "/api/v0/users"
```

### Scope violation

**Error:** `ScopeViolationError: Singleton controller cannot inject request-scoped provider`

**Solution:** Change instantiation mode or use app-scoped dependencies:
```python
# Option 1: Use per_request mode
class MyController(Controller):
    instantiation_mode = "per_request"
    
    def __init__(self, request_dep: RequestScopedService):
        ...

# Option 2: Use app-scoped dependencies only
class MyController(Controller):
    instantiation_mode = "singleton"
    
    def __init__(self, app_dep: AppScopedService):
        ...
```

## Summary

Controllers are the new first-class citizen in Aquilia v2.0:

✅ **Type-safe** - Full type hints and static analysis  
✅ **DI-first** - Automatic dependency injection  
✅ **Zero side effects** - Manifest-first declaration  
✅ **Deeply integrated** - Auth, Sessions, Faults, OpenAPI  
✅ **Migration friendly** - Works alongside legacy @flow  
✅ **Production ready** - Compile-time optimization  

Start using Controllers today for a better development experience!
