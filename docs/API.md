# Aquilia API Reference

## Core Components

### AppManifest

Pure data-driven application manifest.

```python
from aquilia import AppManifest, Config

class MyConfig(Config):
    setting1: str = "value"
    setting2: int = 42

class MyApp(AppManifest):
    name = "myapp"
    version = "1.0.0"
    config = MyConfig
    controllers = ["apps.myapp.controllers:MyController"]
    services = ["apps.myapp.services:MyService"]
    depends_on = ["auth"]
    middlewares = [
        ("aquilia.middleware:CORSMiddleware", {"allow_origins": ["*"]}),
    ]
    
    def on_startup(self, ctx):
        ctx.log.info("Starting")
    
    def on_shutdown(self, ctx):
        ctx.log.info("Stopping")
```

**Fields:**
- `name`: App name (required)
- `version`: Semantic version (required)
- `config`: Config class
- `controllers`: List of controller import paths
- `services`: List of service import paths
- `depends_on`: List of app dependencies
- `middlewares`: List of (path, kwargs) tuples
- `on_startup`: Startup hook
- `on_shutdown`: Shutdown hook

### ConfigLoader

Loads and merges configuration from multiple sources.

```python
from aquilia import ConfigLoader

cfg = ConfigLoader.load(
    paths=["config/*.py"],      # Config files
    env_prefix="AQ_",            # Env var prefix
    env_file=".env",             # .env file
    overrides={"key": "value"},  # Manual overrides
)

# Access config
value = cfg.get("key", default="default_value")
app_cfg = cfg.get_app_config("myapp", MyConfig)
```

**Merge Precedence:**
1. Manual overrides (highest)
2. Environment variables
3. .env file
4. Config files
5. Defaults (lowest)

### Registry

Central registry that orchestrates app loading and dependency resolution.

```python
from aquilia import Registry, ConfigLoader

cfg = ConfigLoader.load()
registry = Registry.from_manifests(
    [App1, App2, App3],
    config=cfg,
    overrides={"ServiceName": MockService}  # For testing
)

# Properties
registry.fingerprint  # Deployment fingerprint
registry.apps         # Dict of app contexts
registry.load_order   # Dependency-sorted app names

# Methods
await registry.startup()   # Execute startup hooks
await registry.shutdown()  # Execute shutdown hooks
issues = registry.validate()  # Validate configuration
```

### Flow & Routing

Flow-first routing system.

```python
from aquilia import flow, Response

# Basic flow
@flow("/users/{id}").GET
async def get_user(id: int):
    return Response.json({"id": id})

# With dependency injection
@flow("/users").POST
async def create_user(request, UserService: UserService):
    data = await request.json()
    user = await UserService.create(data)
    return Response.json(user, status=201)

# With effects
from aquilia import DBTx

@flow("/orders/{id}").POST
async def create_order(id: int, db: DBTx['write']):
    order = await db.create_order(id)
    return Response.json(order)
```

**Supported HTTP Methods:**
- `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`

**Path Parameters:**
- `{name}` - String parameter
- `{id:int}` - Integer parameter
- `{value:float}` - Float parameter
- `*` - Wildcard (matches rest of path)

### Request

ASGI request wrapper.

```python
# Properties
request.method        # HTTP method
request.path          # Request path
request.query_string  # Raw query string
request.query         # Parsed query params
request.headers       # Request headers
request.url           # Full URL
request.client        # Client address (host, port)
request.state         # Request state dict

# Methods
body = await request.body()        # Full body as bytes
text = await request.text()        # Body as text
data = await request.json()        # Parse JSON
data = await request.json(Model)   # Parse into model
form = await request.form()        # Parse form data

# Streaming
async for chunk in request.stream():
    process(chunk)

# Path parameters
params = request.path_params()
id = params.get("id")
```

### Response

HTTP response builder.

```python
from aquilia import Response

# JSON response
Response.json({"key": "value"}, status=200)

# Text response
Response.text("Hello", status=200)

# HTML response
Response.html("<h1>Hello</h1>", status=200)

# Redirect
Response.redirect("/new-url", status=307)

# Streaming
async def generate():
    for i in range(10):
        yield f"chunk {i}\n".encode()

Response.stream(generate(), media_type="text/plain")

# Cookies
response = Response.json({"ok": True})
response.set_cookie("session", "token123", max_age=3600)
response.delete_cookie("old_cookie")

# Headers
response.headers["X-Custom"] = "value"
```

**Helper Functions:**
```python
from aquilia.response import Ok, Created, NotFound, BadRequest

Ok({"status": "success"})           # 200
Created({"id": 123})                # 201
NoContent()                         # 204
BadRequest("Invalid input")         # 400
Unauthorized()                      # 401
Forbidden()                         # 403
NotFound("Resource not found")      # 404
InternalError("Server error")       # 500
```

### DI Container

Scoped dependency injection.

```python
from aquilia import DIContainer, ServiceScope

container = DIContainer()

# Register services
container.register(
    name="UserService",
    factory=UserService,
    scope=ServiceScope.SINGLETON,  # SINGLETON, REQUEST, TRANSIENT
)

# Create request scope
request_scope = container.create_scope("request")

# Resolve services
service = await container.resolve("UserService")

# Cleanup
await container.dispose()
```

**Service Scopes:**
- `SINGLETON`: One instance per app lifetime
- `REQUEST`: One instance per request (ephemeral)
- `TRANSIENT`: New instance every time

### Effects

Typed capability system.

```python
from aquilia import Effect, EffectProvider

# Define effect
class DBTx(Effect):
    def __init__(self, mode: str = "read"):
        super().__init__("DBTx", mode=mode, kind=EffectKind.DB)

# Implement provider
class DBTxProvider(EffectProvider):
    async def initialize(self):
        self.pool = create_pool()
    
    async def acquire(self, mode: str):
        conn = await self.pool.acquire()
        return conn
    
    async def release(self, resource, success: bool):
        if success:
            await resource.commit()
        else:
            await resource.rollback()
        await self.pool.release(resource)

# Register
registry.effect_registry.register("DBTx", DBTxProvider())

# Use in handler
@flow("/users/{id}").PUT
async def update_user(id: int, db: DBTx['write']):
    # db is automatically acquired and released
    await db.update(...)
```

### Middleware

Composable async middleware.

```python
from aquilia.middleware import Middleware, Handler
from aquilia import Request, Response, RequestCtx

# Define middleware
async def my_middleware(
    request: Request,
    ctx: RequestCtx,
    next: Handler
) -> Response:
    # Pre-processing
    start = time.time()
    
    # Call next handler
    response = await next(request, ctx)
    
    # Post-processing
    duration = time.time() - start
    response.headers["X-Duration"] = str(duration)
    
    return response

# Register
middleware_stack.add(
    my_middleware,
    scope="global",    # global, app:name, controller:name, route:pattern
    priority=50,       # Lower = earlier
    name="timing",
)
```

**Built-in Middleware:**
- `RequestIdMiddleware`: Adds request ID
- `ExceptionMiddleware`: Global exception handler
- `LoggingMiddleware`: Request/response logging
- `TimeoutMiddleware`: Request timeout
- `CORSMiddleware`: CORS support
- `CompressionMiddleware`: Gzip compression

### Server

Main server class.

```python
from aquilia import AquiliaServer, Registry, ConfigLoader

cfg = ConfigLoader.load()
registry = Registry.from_manifests([App1, App2])
server = AquiliaServer(registry=registry, config=cfg)

# Run development server
server.run(
    host="127.0.0.1",
    port=8000,
    reload=True,
    log_level="info",
)

# Or get ASGI app for production
app = server.get_asgi_app()
# uvicorn.run(app)
```

## CLI Commands

```bash
# Create new project
aq new project myapp

# Create new app
aq new app users

# Validate manifests and config
aq validate [--settings path/to/settings.py]

# Run development server
aq run [--host 127.0.0.1] [--port 8000] [--reload] [--log-level info]

# Inspect routes and apps
aq inspect

# Show configuration
aq config

# Run from custom location
aq --path /path/to/project run
```

## Testing

```python
import pytest
from aquilia import Registry, ConfigLoader

@pytest.fixture
def registry():
    """Create test registry."""
    cfg = ConfigLoader.load(overrides={"debug": True})
    registry = Registry.from_manifests(
        [TestApp],
        config=cfg,
        overrides={
            "UserService": MockUserService,
        }
    )
    return registry

@pytest.mark.asyncio
async def test_user_creation(registry):
    """Test user creation."""
    await registry.startup()
    
    # Test logic here
    
    await registry.shutdown()
```

## Best Practices

1. **Keep manifests pure data** - No side effects in manifest declarations
2. **Use typed configs** - Leverage type hints for validation
3. **Declare dependencies explicitly** - Use `depends_on` for app dependencies
4. **Scope services appropriately** - Use REQUEST scope for per-request data
5. **Use effects for I/O** - Declare effects in handler signatures
6. **Test with overrides** - Use Registry overrides for mocking
7. **Validate in CI** - Run `aq validate` in CI/CD pipeline
8. **Use fingerprints** - Track deployment fingerprints for auditing
