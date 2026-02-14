# Aquilia Framework — Complete Usage Guide

> **Version:** 0.2.0  
> **Python:** 3.12+  
> **Architecture:** ASGI-native, modular, DI-first

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Workspace & Modules](#2-workspace--modules)
3. [Controllers](#3-controllers)
4. [Dependency Injection](#4-dependency-injection)
5. [Configuration](#5-configuration)
6. [Sessions](#6-sessions)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [Faults (Error Handling)](#8-faults-error-handling)
9. [WebSockets](#9-websockets)
10. [Templates](#10-templates)
11. [AMDL Models](#11-amdl-models)
12. [Effects](#12-effects)
13. [URL Patterns](#13-url-patterns)
14. [Middleware](#14-middleware)
15. [Lifecycle Management](#15-lifecycle-management)
16. [Request & Response](#16-request--response)
17. [Debug Pages](#17-debug-pages)
18. [CLI Reference](#18-cli-reference)
19. [Testing](#19-testing)
20. [Deployment](#20-deployment)

---

## 1. Getting Started

### Installation

```bash
pip install aquilia
```

### Create a Workspace

```bash
aq init workspace myapp
cd myapp
```

This generates:

```
myapp/
├── workspace.py          # Workspace structure (modules, integrations)
├── starter.py            # Welcome page (auto-loaded in debug mode)
├── config/
│   ├── base.yaml         # Shared defaults
│   ├── dev.yaml          # Development settings
│   └── prod.yaml         # Production settings
├── modules/              # Application modules
├── templates/            # Jinja2 templates
├── artifacts/            # Build artifacts
└── runtime/              # Runtime state
```

### Add a Module

```bash
aq add module blogs
```

Creates:

```
modules/blogs/
├── __init__.py
├── controllers.py        # HTTP endpoints
├── services.py           # Business logic
├── manifest.py           # Module manifest
└── faults.py             # Module-specific faults
```

### Run the Server

```bash
aq run dev
```

The server starts at `http://127.0.0.1:8000`. In debug mode, a welcome page appears at `/`.

---

## 2. Workspace & Modules

### Workspace Configuration (`workspace.py`)

The workspace is the **root of your application**. It defines:
- Which modules are loaded
- Which integrations are active
- Session, security, and telemetry settings

```python
from aquilia import Workspace, Module, Integration
from datetime import timedelta
from aquilia.sessions import SessionPolicy, PersistencePolicy, TransportPolicy

workspace = (
    Workspace(name="myapp", version="0.1.0", description="My app")

    # Register modules
    .module(Module("blogs", version="0.1.0")
        .route_prefix("/blogs")
        .tags("blogs", "core")
        .register_controllers("modules.blogs.controllers:BlogsController")
        .register_services("modules.blogs.services:BlogsService"))

    .module(Module("users", version="0.1.0")
        .route_prefix("/users")
        .register_controllers("modules.users.controllers:UsersController")
        .register_services("modules.users.services:UsersService"))

    # Core integrations
    .integrate(Integration.di(auto_wire=True, manifest_validation=True))
    .integrate(Integration.registry(mode="auto", fingerprint_verification=True))
    .integrate(Integration.routing(strict_matching=True, compression=True))
    .integrate(Integration.fault_handling(default_strategy="propagate"))
    .integrate(Integration.patterns())
    .integrate(Integration.templates.source("templates").scan_modules().cached("memory").secure())

    # Sessions
    .sessions(policies=[
        SessionPolicy(
            name="default",
            ttl=timedelta(days=7),
            idle_timeout=timedelta(hours=1),
            rotate_on_privilege_change=True,
            persistence=PersistencePolicy(enabled=True, store_name="memory"),
            transport=TransportPolicy(adapter="cookie", cookie_httponly=True),
            scope="user",
        ),
    ])

    # Security & telemetry
    .security(cors_enabled=False, csrf_protection=False, helmet_enabled=True)
    .telemetry(tracing_enabled=False, metrics_enabled=True, logging_enabled=True)
)
```

### Module Manifests (`manifest.py`)

Each module has a manifest that declares its components:

```python
from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig, FaultHandlerConfig,
    MiddlewareConfig, SessionConfig, LifecycleConfig, FeatureConfig,
)

manifest = AppManifest(
    name="blogs",
    version="0.1.0",
    description="Blog management",
    tags=["blogs", "content"],

    # Components
    services=["modules.blogs.services:BlogsService"],
    controllers=["modules.blogs.controllers:BlogsController"],

    # Routing
    route_prefix="/blogs",
    base_path="modules.blogs",

    # Faults
    faults=FaultHandlingConfig(
        default_domain="BLOGS",
        strategy="propagate",
        handlers=[
            FaultHandlerConfig(domain="BLOGS", handler="modules.blogs.faults:BlogsFaultHandler"),
        ],
    ),

    # Lifecycle hooks
    lifecycle=LifecycleConfig(
        on_startup=["modules.blogs.hooks:on_startup"],
        on_shutdown=["modules.blogs.hooks:on_shutdown"],
    ),

    # Feature flags
    features=[
        FeatureConfig(name="blog_comments", enabled=True),
        FeatureConfig(name="blog_reactions", enabled=False),
    ],
)
```

---

## 3. Controllers

Controllers are the HTTP layer. They handle requests and return responses.

### Basic Controller

```python
from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response

class BlogsController(Controller):
    prefix = "/"
    tags = ["blogs"]

    def __init__(self, service: BlogsService):
        self.service = service

    @GET("/")
    async def list_all(self, ctx: RequestCtx):
        items = await self.service.get_all()
        return Response.json({"items": items})

    @POST("/")
    async def create(self, ctx: RequestCtx):
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_one(self, ctx: RequestCtx, id: int):
        item = await self.service.get_by_id(id)
        if not item:
            raise BlogNotFoundFault(id)
        return Response.json(item)

    @PUT("/«id:int»")
    async def update(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        item = await self.service.update(id, data)
        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete(self, ctx: RequestCtx, id: int):
        await self.service.delete(id)
        return Response.json({"deleted": True})
```

### Route Decorators

| Decorator | HTTP Method | Example |
|-----------|-------------|---------|
| `@GET(path)` | GET | `@GET("/users")` |
| `@POST(path)` | POST | `@POST("/users")` |
| `@PUT(path)` | PUT | `@PUT("/users/«id:int»")` |
| `@PATCH(path)` | PATCH | `@PATCH("/users/«id:int»")` |
| `@DELETE(path)` | DELETE | `@DELETE("/users/«id:int»")` |
| `@HEAD(path)` | HEAD | `@HEAD("/health")` |
| `@OPTIONS(path)` | OPTIONS | `@OPTIONS("/users")` |
| `@WS(path)` | WebSocket | `@WS("/live")` |
| `@route(path, methods=[...])` | Multiple | `@route("/data", methods=["GET", "POST"])` |

### RequestCtx

Every handler receives a `RequestCtx` with:

```python
@GET("/example")
async def handler(self, ctx: RequestCtx):
    # Core
    ctx.request         # Full Request object
    ctx.identity        # Auth Identity (if authenticated)
    ctx.session         # Session object
    ctx.container       # DI container (request-scoped)
    ctx.state           # Arbitrary state dict

    # Convenience properties
    ctx.path            # URL path
    ctx.method          # HTTP method
    ctx.headers         # Request headers
    ctx.query_params    # Query parameters dict

    # Body parsing
    data = await ctx.json()    # Parse JSON body
    form = await ctx.form()    # Parse form data
```

### Lifecycle Hooks

Controllers support lifecycle hooks for setup/teardown:

```python
class UsersController(Controller):
    prefix = "/"
    instantiation_mode = "singleton"  # Required for on_startup/on_shutdown

    async def on_startup(self, ctx: RequestCtx):
        """Called once when the server starts."""
        self.cache = {}

    async def on_shutdown(self, ctx: RequestCtx):
        """Called once when the server shuts down."""
        self.cache.clear()

    async def on_request(self, ctx: RequestCtx):
        """Called before every request handler."""
        ctx.state["start_time"] = time.time()

    async def on_response(self, ctx: RequestCtx, response: Response):
        """Called after every request handler."""
        elapsed = time.time() - ctx.state["start_time"]
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
```

### Controller Pipeline

Attach middleware/guards at the controller level:

```python
class AdminController(Controller):
    prefix = "/admin"
    pipeline = [auth_guard, admin_role_guard]  # Executed before every handler
    tags = ["admin"]
```

### Template Rendering

Controllers can render templates:

```python
class PagesController(Controller):
    prefix = "/"

    @GET("/home")
    async def home(self, ctx: RequestCtx):
        return self.render("home.html", {
            "title": "Welcome",
            "user": ctx.identity,
        })
```

---

## 4. Dependency Injection

Aquilia's DI system supports automatic constructor injection, multiple scopes, and provider types.

### Marking Services

```python
from aquilia.di import service, factory, inject, Inject
from typing import Annotated

@service(scope="app")
class UserRepository:
    """App-scoped: one instance per application."""

    def __init__(self):
        self._storage = {}

    async def find(self, user_id: str):
        return self._storage.get(user_id)

    async def save(self, user_id: str, data: dict):
        self._storage[user_id] = data


@service(scope="request")
class RequestLogger:
    """Request-scoped: fresh instance per HTTP request."""

    def __init__(self):
        self.entries = []

    def log(self, message: str):
        self.entries.append(message)
```

### Scopes

| Scope | Description |
|-------|-------------|
| `singleton` | One instance for entire application lifetime |
| `app` | One instance per application (alias for singleton in most cases) |
| `request` | New instance per HTTP request |
| `transient` | New instance every time it's resolved |
| `pooled` | Instance from a pre-allocated pool |
| `ephemeral` | Ultra-short-lived, no caching |

### Constructor Injection

Dependencies are resolved by type from constructor parameters:

```python
@service(scope="app")
class UserService:
    def __init__(self, repo: UserRepository, hasher: PasswordHasher):
        self.repo = repo
        self.hasher = hasher
```

### Using `Inject` for Fine Control

```python
from typing import Annotated
from aquilia.di import Inject

@service(scope="app")
class OrderService:
    def __init__(
        self,
        primary_db: Annotated[Database, Inject(tag="primary")],
        cache: Annotated[CacheService, Inject(optional=True)],
    ):
        self.db = primary_db
        self.cache = cache  # None if not registered
```

### Factory Providers

```python
from aquilia.di import factory, provides

@factory(scope="singleton", name="db_pool")
async def create_db_pool(config: AppConfig) -> DatabasePool:
    return await DatabasePool.connect(config.db_url)


@provides(UserRepository, scope="app", tag="sql")
def create_sql_repo(db: Database) -> UserRepository:
    return SqlUserRepository(db)
```

### Provider Types

| Provider | Use Case |
|----------|----------|
| `ClassProvider` | Auto-resolves constructor deps from type hints |
| `FactoryProvider` | Custom factory function |
| `ValueProvider` | Fixed value (configs, constants) |
| `PoolProvider` | Pre-allocated pool of instances |
| `AliasProvider` | Alias one token to another |
| `LazyProxyProvider` | Lazy-initialized on first access |
| `ScopedProvider` | Provides different implementations per scope |

### Controller DI

Controllers automatically get dependencies injected via their constructor:

```python
class UsersController(Controller):
    prefix = "/"

    def __init__(self, user_service: UserService, auth: AuthManager):
        self.user_service = user_service
        self.auth = auth
```

### Testing with DI

```python
from aquilia.di import TestRegistry, MockProvider

test_registry = TestRegistry()
test_registry.register(MockProvider(UserRepository, mock_repo))
```

---

## 5. Configuration

### YAML Configuration

**`config/base.yaml`** — Shared defaults:

```yaml
app:
  name: myapp
  version: "0.1.0"

database:
  driver: sqlite
  name: myapp.db
```

**`config/dev.yaml`** — Development overrides:

```yaml
server:
  mode: dev
  debug: true
  host: 127.0.0.1
  port: 8000
  reload: true
  workers: 1
  access_log: true
```

**`config/prod.yaml`** — Production:

```yaml
server:
  mode: prod
  debug: false
  host: 0.0.0.0
  port: 8000
  workers: 4
  access_log: false
```

### Accessing Configuration

```python
from aquilia.config import ConfigLoader

config = ConfigLoader()
config.load("config/base.yaml")
config.load("config/dev.yaml")

# Dot-path access
debug = config.get("server.debug")        # True
host = config.get("server.host")          # "127.0.0.1"
db = config.get("database.driver")        # "sqlite"

# With defaults
timeout = config.get("server.timeout", 30)

# Environment variable overrides
# AQUILIA_SERVER__PORT=9000 → overrides server.port
```

### Python Configuration (Workspace Builder)

```python
from aquilia import Workspace, Module, Integration

workspace = (
    Workspace(name="myapp")
    .module(Module("users").route_prefix("/users"))
    .integrate(Integration.di(auto_wire=True))
)
```

---

## 6. Sessions

### Session Policy

```python
from aquilia.sessions import SessionPolicy, PersistencePolicy, TransportPolicy
from datetime import timedelta

policy = SessionPolicy(
    name="web",
    ttl=timedelta(days=7),
    idle_timeout=timedelta(hours=1),
    rotate_on_privilege_change=True,
    persistence=PersistencePolicy(
        enabled=True,
        store_name="memory",   # "memory" or "file"
        write_through=True,
    ),
    transport=TransportPolicy(
        adapter="cookie",       # "cookie" or "header"
        cookie_httponly=True,
        cookie_secure=True,     # True in production
        cookie_samesite="lax",
    ),
    scope="user",
)
```

### Session Stores

| Store | Description |
|-------|-------------|
| `MemoryStore` | In-memory (development) |
| `FileStore` | File-backed with variants: `.web_optimized()`, `.api_optimized()`, `.mobile_optimized()` |

### Session Transports

| Transport | Usage |
|-----------|-------|
| `CookieTransport` | Browser sessions via cookies |
| `HeaderTransport` | API clients via `X-Session-ID` header |

### Using Sessions in Controllers

```python
from aquilia.sessions import session, authenticated, stateful

class CartController(Controller):
    prefix = "/cart"

    @GET("/")
    @session.require(authenticated=True)
    async def view_cart(self, ctx: RequestCtx):
        cart = ctx.session.get("cart", [])
        return Response.json({"items": cart})

    @POST("/add")
    @session.ensure()
    async def add_to_cart(self, ctx: RequestCtx):
        data = await ctx.json()
        cart = ctx.session.get("cart", [])
        cart.append(data)
        ctx.session["cart"] = cart
        return Response.json({"added": True})
```

### Typed Session State

```python
from aquilia.sessions import SessionState, Field

class CartState(SessionState):
    items: list = Field(default_factory=list)
    total: float = Field(default=0.0)
    currency: str = Field(default="USD")

class UserPreferences(SessionState):
    theme: str = Field(default="light")
    language: str = Field(default="en")
    notifications: bool = Field(default=True)
```

### Session Decorators

| Decorator | Effect |
|-----------|--------|
| `@session.require(authenticated=True)` | Requires an active, authenticated session |
| `@session.ensure()` | Creates session if none exists |
| `@authenticated` | Shortcut for requiring authentication |
| `@stateful` | Marks handler as stateful (session-dependent) |

### Session Guards

```python
from aquilia.sessions import SessionGuard, AdminGuard, VerifiedEmailGuard

# Built-in guards
admin_guard = AdminGuard()             # Requires admin role in session
email_guard = VerifiedEmailGuard()     # Requires verified email
```

### Session Context Manager

```python
from aquilia.sessions import SessionContext

async def handler(ctx: RequestCtx):
    async with SessionContext(ctx) as session:
        session["last_visited"] = "/dashboard"
        # Automatically committed on exit
```

---

## 7. Authentication & Authorization

### Identity

Every authenticated request has an `Identity`:

```python
from aquilia.auth import Identity, IdentityType, IdentityStatus

identity = Identity(
    id="user_123",
    type=IdentityType.USER,          # USER, SERVICE, DEVICE, ANONYMOUS
    status=IdentityStatus.ACTIVE,    # ACTIVE, LOCKED, SUSPENDED
    attributes={
        "email": "user@example.com",
        "name": "John Doe",
        "roles": ["admin"],
        "scopes": ["read", "write"],
    },
    tenant_id="org_456",
)

# Check permissions
identity.has_role("admin")      # True
identity.has_scope("write")     # True
```

### Credentials

```python
from aquilia.auth import PasswordCredential, ApiKeyCredential

# Password (Argon2id hashing)
password_cred = PasswordCredential(
    identity_id="user_123",
    password_hash="$argon2id$...",
)

# API Key (SHA-256, scoped)
api_key = ApiKeyCredential(
    identity_id="service_456",
    key_hash="sha256:...",
    scopes=["read"],
    expires_at=datetime(2025, 12, 31),
)
```

### Auth Manager

```python
from aquilia.auth import AuthManager

auth = AuthManager()

# Register identity
await auth.register(
    identity_id="user_123",
    password="secure_password",
    attributes={"email": "user@example.com", "roles": ["user"]},
)

# Authenticate
result = await auth.authenticate("user_123", "secure_password")
if result.success:
    identity = result.identity
    tokens = result.tokens  # Access + refresh tokens
```

### Token Management

```python
from aquilia.auth import TokenManager, KeyRing, KeyDescriptor

# Generate key pair
key = KeyDescriptor.generate("key_001", algorithm="RS256")
keyring = KeyRing(keys=[key])

# Create token manager
token_mgr = TokenManager(keyring=keyring)

# Issue tokens
access_token = await token_mgr.issue_access_token(
    identity_id="user_123",
    scopes=["read", "write"],
    ttl=timedelta(hours=1),
)

# Validate tokens
claims = await token_mgr.validate(access_token)
```

### Guards

Guards protect routes from unauthorized access:

```python
from aquilia.auth import AuthGuard, RoleGuard, ScopeGuard

class AdminController(Controller):
    prefix = "/admin"
    pipeline = [AuthGuard(), RoleGuard("admin")]

    @GET("/dashboard")
    async def dashboard(self, ctx: RequestCtx):
        return Response.json({"message": "Admin dashboard"})

    @DELETE("/users/«id:int»")
    @ScopeGuard("admin:delete")
    async def delete_user(self, ctx: RequestCtx, id: int):
        ...
```

### Authorization Engines

```python
from aquilia.auth import RBACEngine, ABACEngine

# Role-Based Access Control
rbac = RBACEngine()
rbac.define_role("admin", permissions=["read", "write", "delete"])
rbac.define_role("viewer", permissions=["read"])
rbac.assign_role("user_123", "admin")
allowed = await rbac.check("user_123", "delete")  # True

# Attribute-Based Access Control
abac = ABACEngine()
abac.add_policy(
    name="same_org_access",
    condition=lambda subject, resource: subject.tenant_id == resource.org_id,
)
```

### Password Hashing

```python
from aquilia.auth import PasswordHasher, PasswordPolicy

hasher = PasswordHasher()
hashed = await hasher.hash("my_password")
valid = await hasher.verify("my_password", hashed)  # True

# Password policy
policy = PasswordPolicy(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digits=True,
    require_special=True,
)
policy.validate("Weak")  # Raises PolicyViolation
```

### Auth Middleware

```python
from aquilia.auth.integration import AquilAuthMiddleware

# Automatically extracts identity from JWT/session for every request
middleware = AquilAuthMiddleware(token_manager=token_mgr)
```

---

## 8. Faults (Error Handling)

Aquilia replaces traditional exceptions with structured **Faults**.

### Creating Faults

```python
from aquilia.faults import Fault, FaultDomain, Severity

class UserNotFoundFault(Fault):
    def __init__(self, user_id: str):
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"User '{user_id}' not found",
            domain=FaultDomain.IO,
            severity=Severity.ERROR,
            retryable=False,
            public=True,        # Safe to expose to client
            status_code=404,
            metadata={"user_id": user_id},
        )
```

### Fault Domains

| Domain | Purpose |
|--------|---------|
| `CONFIG` | Configuration errors |
| `REGISTRY` | Module registry failures |
| `DI` | Dependency injection failures |
| `ROUTING` | Route matching / compilation errors |
| `FLOW` | Pipeline / flow errors |
| `EFFECT` | Side-effect failures (DB, cache, queue) |
| `IO` | I/O and external service errors |
| `SECURITY` | Authentication / authorization failures |
| `SYSTEM` | Internal framework errors |
| `MODEL` | AMDL model / database errors |
| Custom | `FaultDomain.custom("BILLING")` |

### Severity Levels

| Level | Meaning |
|-------|---------|
| `INFO` | Informational, non-blocking |
| `WARN` | Warning, operation succeeded with caveats |
| `ERROR` | Operation failed |
| `FATAL` | System-level failure, may require restart |

### Recovery Strategies

| Strategy | Behavior |
|----------|----------|
| `PROPAGATE` | Re-raise to caller |
| `RETRY` | Retry the operation |
| `FALLBACK` | Use fallback value |
| `MASK` | Convert to safe public error |
| `CIRCUIT_BREAK` | Open circuit breaker |

### Fault Engine

```python
from aquilia.faults import FaultEngine

engine = FaultEngine()

# Register domain handler
engine.register_handler("BILLING", BillingFaultHandler())

# Process faults
try:
    result = await do_operation()
except Exception as e:
    await engine.process(e, app="myapp", route="/billing/charge")
```

### Using Faults in Controllers

```python
class ProductsController(Controller):
    prefix = "/"

    @GET("/«id:int»")
    async def get_product(self, ctx: RequestCtx, id: int):
        product = await self.service.find(id)
        if not product:
            raise ProductNotFoundFault(id)  # Returns 404 JSON automatically
        return Response.json(product)
```

---

## 9. WebSockets

### Socket Controller

```python
from aquilia.sockets import (
    SocketController, Socket, OnConnect, OnDisconnect,
    Event, AckEvent, Subscribe, Unsubscribe,
)

@Socket("/chat")
class ChatSocket(SocketController):
    namespace = "/chat"

    @OnConnect()
    async def on_connect(self, connection):
        """Called when a client connects."""
        await connection.send_json({"type": "welcome", "id": connection.id})
        await connection.join_room("general")

    @OnDisconnect()
    async def on_disconnect(self, connection):
        """Called when a client disconnects."""
        await connection.leave_room("general")

    @Event("message")
    async def on_message(self, connection, data):
        """Handle incoming message event."""
        username = connection.state.get("username", "anonymous")
        await self.broadcast_to_room("general", {
            "type": "message",
            "from": username,
            "text": data.get("text"),
        })

    @AckEvent("set_username")
    async def set_username(self, connection, data):
        """Handle event with acknowledgment."""
        connection.state["username"] = data["username"]
        return {"status": "ok", "username": data["username"]}

    @Subscribe("typing")
    async def on_typing(self, connection, data):
        """Handle typing indicator subscription."""
        await self.broadcast_to_room("general", {
            "type": "typing",
            "user": connection.state.get("username"),
        }, exclude=connection.id)
```

### Connection Object

```python
# Connection properties
connection.id           # Unique connection ID
connection.state        # Per-connection state dict
connection.identity     # Auth identity (if authenticated)
connection.session      # Session (if session-enabled)
connection.scope        # ConnectionScope (path, headers, query)

# Connection methods
await connection.send_json(data)
await connection.send_text(text)
await connection.send_bytes(data)
await connection.close(code=1000)

# Rooms
await connection.join_room("room_name")
await connection.leave_room("room_name")
```

### Socket Guards

```python
from aquilia.sockets import HandshakeAuthGuard, OriginGuard, RateLimitGuard

@Socket("/admin", guards=[
    HandshakeAuthGuard(),
    OriginGuard(allowed=["https://myapp.com"]),
    RateLimitGuard(max_messages=60, window_seconds=60),
])
class AdminSocket(SocketController):
    ...
```

### Scaling Adapters

```python
from aquilia.sockets import InMemoryAdapter, RedisAdapter

# Single-server (default)
adapter = InMemoryAdapter()

# Multi-server with Redis pub/sub
adapter = RedisAdapter(redis_url="redis://localhost:6379")
```

### WebSocket in Workspace

Register socket controllers alongside HTTP controllers:

```python
.module(Module("chat")
    .route_prefix("/chat")
    .register_controllers("modules.chat.sockets:ChatSocket"))
```

---

## 10. Templates

### Engine Setup

Templates use Jinja2 under the hood:

```python
from aquilia.templates import TemplateEngine, TemplateLoader

engine = TemplateEngine(
    loader=TemplateLoader(search_paths=["templates"]),
    auto_reload=True,  # Dev mode
)
```

### Rendering in Controllers

```python
class PagesController(Controller):
    prefix = "/"

    @GET("/home")
    async def home(self, ctx: RequestCtx):
        return self.render("pages/home.html", {
            "title": "Home",
            "user": ctx.identity,
            "session": ctx.session,
        })
```

### Template Files

```html
<!-- templates/pages/home.html -->
{% extends "layouts/base.html" %}

{% block content %}
<h1>{{ title }}</h1>
{% if user %}
    <p>Welcome, {{ user.attributes.name }}!</p>
{% else %}
    <p>Please <a href="/login">sign in</a>.</p>
{% endif %}
{% endblock %}
```

### Integration with Sessions & Auth

Templates automatically get session and identity context via proxies:

```html
<!-- Access session data in templates -->
{% if session.authenticated %}
    <span>Logged in as {{ identity.attributes.name }}</span>
{% endif %}

<!-- Flash messages -->
{% for msg in flash_messages %}
    <div class="alert alert-{{ msg.type }}">{{ msg.text }}</div>
{% endfor %}
```

### Workspace Integration

```python
.integrate(
    Integration.templates
    .source("templates")        # Template directory
    .scan_modules()             # Also scan module template dirs
    .cached("memory")           # BytecodeCache type
    .secure()                   # Enable sandboxing
)
```

### DI Providers

```python
from aquilia.templates import (
    create_development_engine,
    create_production_engine,
    create_testing_engine,
)

# Auto-configures based on environment
dev_engine = create_development_engine(search_paths=["templates"])
prod_engine = create_production_engine(search_paths=["templates"])
```

---

## 11. AMDL Models

AMDL (Aquilia Model Definition Language) defines data models in `.amdl` files.

### Model Definition

```amdl
# models/user.amdl
model User {
    slot id: uuid @primary
    slot email: string @unique @indexed
    slot name: string
    slot password_hash: string
    slot role: string = "user"
    slot is_active: bool = true
    slot created_at: datetime @auto_now_add
    slot updated_at: datetime @auto_now

    link posts: Post[] @cascade
    link profile: Profile? @set_null

    index idx_email_active on (email, is_active)

    hook before_save {
        validate_email(self.email)
    }

    meta {
        table = "users"
        ordering = ["-created_at"]
    }

    note "Core user model for authentication and profiles"
}
```

### AMDL Syntax Reference

#### Slots (Fields)

```amdl
slot name: type [= default] [@decorator...]
```

| Type | Description |
|------|-------------|
| `string` | Text field |
| `int` | Integer |
| `float` | Floating point |
| `bool` | Boolean |
| `uuid` | UUID |
| `datetime` | DateTime |
| `date` | Date |
| `json` | JSON blob |
| `text` | Long text |
| `binary` | Binary data |

#### Slot Decorators

| Decorator | Effect |
|-----------|--------|
| `@primary` | Primary key |
| `@unique` | Unique constraint |
| `@indexed` | Database index |
| `@nullable` | Allow NULL |
| `@auto_now` | Set on every save |
| `@auto_now_add` | Set on creation |
| `@max_length(n)` | Max length constraint |
| `@min_value(n)` | Min value constraint |
| `@max_value(n)` | Max value constraint |

#### Links (Relationships)

```amdl
link field_name: Model      # One-to-one
link field_name: Model?     # Optional one-to-one
link field_name: Model[]    # One-to-many
```

| Link Decorator | Effect |
|----------------|--------|
| `@cascade` | Delete linked records on parent delete |
| `@set_null` | Set to NULL on parent delete |
| `@restrict` | Prevent parent deletion |
| `@protect` | Raise error on parent deletion |

### Parsing AMDL

```python
from aquilia.models import parse_amdl, parse_amdl_file, parse_amdl_directory

# Parse string
ast = parse_amdl("""
model Product {
    slot id: uuid @primary
    slot name: string
    slot price: float
}
""")

# Parse file
ast = parse_amdl_file("models/user.amdl")

# Parse entire directory
models = parse_amdl_directory("models/")
```

### ModelProxy (Runtime CRUD)

```python
from aquilia.models import ModelProxy, ModelRegistry, Q

# Register model
registry = ModelRegistry()
registry.register_from_ast(ast)

# Create proxy
User = ModelProxy("User", registry=registry)

# CRUD operations
user = await User.create(name="John", email="john@example.com")
user = await User.find_by_id("uuid-here")
users = await User.find_all()
users = await User.filter(Q.eq("role", "admin") & Q.gt("created_at", cutoff))
await User.update("uuid-here", name="Jane")
await User.delete("uuid-here")
```

### Query Builder (Q)

```python
from aquilia.models import Q

# Comparison operators
Q.eq("status", "active")       # field == value
Q.ne("status", "deleted")      # field != value
Q.gt("age", 18)                # field > value
Q.gte("age", 18)               # field >= value
Q.lt("price", 100)             # field < value
Q.lte("price", 100)            # field <= value

# String operators
Q.contains("name", "john")     # LIKE %john%
Q.starts_with("email", "admin")
Q.ends_with("email", ".com")

# Logical operators
Q.eq("a", 1) & Q.eq("b", 2)   # AND
Q.eq("a", 1) | Q.eq("b", 2)   # OR
~Q.eq("status", "deleted")     # NOT

# Collection
Q.in_("role", ["admin", "mod"])
Q.between("price", 10, 100)
```

### Migrations

```python
from aquilia.models import MigrationRunner, generate_migration_file, op

# Generate migration
generate_migration_file(
    name="create_users",
    models_dir="models/",
    output_dir="migrations/",
)

# Run migrations
runner = MigrationRunner(db_url="sqlite:///myapp.db")
await runner.migrate()

# Migration operations
class CreateUsersTable:
    async def up(self):
        op.create_table("users", [
            op.column("id", "uuid", primary=True),
            op.column("email", "string", unique=True),
            op.column("name", "string"),
        ])

    async def down(self):
        op.drop_table("users")
```

---

## 12. Effects

Effects represent controlled side-effects (database transactions, cache operations, queue messages).

### Effect Types

| Kind | Purpose |
|------|---------|
| `DB` | Database transactions |
| `CACHE` | Cache operations |
| `QUEUE` | Message queue operations |
| `HTTP` | External HTTP calls |
| `STORAGE` | File/object storage |
| `CUSTOM` | Custom side-effects |

### DBTx (Database Transaction)

```python
from aquilia.effects import DBTx, DBTxProvider, EffectRegistry

# Register provider
registry = EffectRegistry()
registry.register(DBTxProvider(db_url="sqlite:///myapp.db"))

# Use in handler
async def create_order(ctx: RequestCtx):
    async with DBTx() as tx:
        await tx.execute("INSERT INTO orders ...")
        await tx.execute("UPDATE inventory ...")
        # Auto-commits on success, rolls back on error
```

### Cache Effect

```python
from aquilia.effects import CacheEffect, CacheProvider, CacheHandle

# Register cache
registry.register(CacheProvider(backend="memory"))

# Use cache
async def get_product(ctx: RequestCtx, id: int):
    cache = CacheHandle(namespace="products")
    
    cached = await cache.get(f"product:{id}")
    if cached:
        return Response.json(cached)
    
    product = await db.find(id)
    await cache.set(f"product:{id}", product, ttl=300)
    return Response.json(product)
```

### Effect Provider Lifecycle

```python
from aquilia.effects import Effect, EffectKind, EffectProvider

class EmailProvider(EffectProvider):
    kind = EffectKind.CUSTOM

    async def initialize(self):
        """Called on startup."""
        self.client = await create_email_client()

    async def acquire(self):
        """Get effect handle for a request."""
        return self.client

    async def release(self, handle):
        """Release after request."""
        pass

    async def finalize(self):
        """Called on shutdown."""
        await self.client.close()
```

---

## 13. URL Patterns

Aquilia uses a formal EBNF-based pattern syntax for URLs.

### Syntax

```
/static                     # Static segment
/users/«id:int»             # Typed parameter
/files/«path:path»          # Catch-all (splat)
/items[/«category:str»]     # Optional group
/search?«q:str»&«page:int»  # Query parameters
```

### Built-in Types

| Type | Matches | Example |
|------|---------|---------|
| `str` | Any string | `«name:str»` |
| `int` | Integer | `«id:int»` |
| `float` | Float | `«price:float»` |
| `uuid` | UUID | `«token:uuid»` |
| `slug` | URL slug | `«slug:slug»` |
| `path` | Path segments (greedy) | `«filepath:path»` |

### Custom Types

```python
from aquilia.patterns import TypeRegistry

TypeRegistry.register(
    name="date",
    pattern=r"\d{4}-\d{2}-\d{2}",
    converter=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
)

# Usage: /events/«date:date»
```

### Pattern Compiler

```python
from aquilia.patterns import PatternCompiler, PatternMatcher

compiler = PatternCompiler()
compiled = compiler.compile("/users/«id:int»/posts/«slug:slug»")

matcher = PatternMatcher()
result = matcher.match(compiled, "/users/42/posts/hello-world")
# result.matched = True
# result.params = {"id": 42, "slug": "hello-world"}
```

---

## 14. Middleware

### Middleware Stack

```python
from aquilia.middleware import MiddlewareStack, Middleware, Handler

class TimingMiddleware(Middleware):
    async def __call__(self, request, handler: Handler) -> Response:
        start = time.time()
        response = await handler(request)
        elapsed = time.time() - start
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
        return response
```

### Middleware Scoping

| Scope | Applied To |
|-------|-----------|
| `global` | All requests |
| `app` | All routes in a module |
| `controller` | All routes in a controller |
| `route` | Specific route only |

### Built-in Middleware

| Middleware | Purpose |
|-----------|---------|
| `RequestIdMiddleware` | Adds `X-Request-ID` header |
| `ExceptionMiddleware` | Catches errors, renders debug pages in dev |
| `LoggingMiddleware` | Request/response logging |

### Priority

Lower priority numbers execute first:

```python
stack = MiddlewareStack()
stack.add(RequestIdMiddleware(), priority=1)      # Runs first
stack.add(LoggingMiddleware(), priority=10)
stack.add(AuthMiddleware(), priority=50)
stack.add(TimingMiddleware(), priority=100)        # Runs last (outermost)
```

---

## 15. Lifecycle Management

### Lifecycle Coordinator

```python
from aquilia.lifecycle import LifecycleCoordinator, LifecyclePhase

coordinator = LifecycleCoordinator()

# Register components with dependencies
coordinator.register(
    name="database",
    startup=db.connect,
    shutdown=db.disconnect,
    phase=LifecyclePhase.INFRASTRUCTURE,
)

coordinator.register(
    name="cache",
    startup=cache.connect,
    shutdown=cache.close,
    phase=LifecyclePhase.INFRASTRUCTURE,
    depends_on=["database"],
)

coordinator.register(
    name="user_service",
    startup=user_service.init,
    shutdown=user_service.cleanup,
    phase=LifecyclePhase.SERVICE,
    depends_on=["database", "cache"],
)

# Startup (respects dependency order)
await coordinator.startup()

# Shutdown (reverse order, with rollback on failure)
await coordinator.shutdown()
```

### Lifecycle Phases

| Phase | Order | Purpose |
|-------|-------|---------|
| `INFRASTRUCTURE` | 1 | DB, cache, message queue connections |
| `SERVICE` | 2 | Business services initialization |
| `CONTROLLER` | 3 | Controller startup hooks |
| `APPLICATION` | 4 | Application-level startup |

---

## 16. Request & Response

### Request

```python
@GET("/example")
async def handler(self, ctx: RequestCtx):
    request = ctx.request

    # URL & method
    request.method          # "GET"
    request.path            # "/example"
    request.url             # Full URL object
    request.query_params    # {"key": "value"}

    # Headers
    request.headers         # Headers dict
    request.content_type    # "application/json"
    request.accept          # Accept header parsing

    # Body
    body = await request.body()         # Raw bytes
    json = await request.json()         # Parsed JSON
    form = await request.form()         # Form data
    text = await request.text()         # Text body

    # File uploads
    files = await request.files()       # Uploaded files
    file = files["avatar"]
    file.filename                       # Original filename
    file.content_type                   # MIME type
    content = await file.read()         # File content

    # Client info
    request.client          # Client IP & port
    request.cookies         # Cookie dict

    # Streaming
    async for chunk in request.stream():
        process(chunk)
```

### Response

```python
from aquilia import Response

# JSON
Response.json({"key": "value"})
Response.json(data, status=201)

# HTML
Response.html("<h1>Hello</h1>")

# Text
Response.text("Hello, World!")

# Redirect
Response.redirect("/login")
Response.redirect("/new-url", status=301)  # Permanent

# File download
Response.file("path/to/file.pdf", filename="report.pdf")

# Streaming
async def generate():
    for i in range(100):
        yield f"data: {i}\n\n"
        await asyncio.sleep(0.1)
Response.stream(generate(), media_type="text/event-stream")

# SSE (Server-Sent Events)
Response.sse(event_generator)

# Headers & cookies
response = Response.json({"ok": True})
response.headers["X-Custom"] = "value"
response.set_cookie("session_id", "abc123", httponly=True, secure=True)
response.delete_cookie("old_cookie")

# Caching
response.cache_control(max_age=3600, public=True)

# Background tasks
response.background(send_email, to="user@example.com")
```

---

## 17. Debug Pages

In debug mode (`server.debug: true`), Aquilia provides:

### Exception Page
When an unhandled exception occurs, a React-style interactive debug page with:
- Full traceback with syntax-highlighted source code
- Request details (method, path, headers, body)
- Local variables at each frame
- Dark/light mode toggle

### HTTP Error Pages
Styled error pages for 400, 401, 403, 404, 405, 408, 429, 500, 502, 503, 504.

### Welcome Page
When no routes are registered, a starter page at `/` with:
- MongoDB Atlas-inspired design (colors: `#00ED64`, `#001E2B`)
- Quick-start instructions
- Dark/light mode toggle

These are automatically disabled in production mode.

---

## 18. CLI Reference

### Commands

```bash
# Initialize workspace
aq init workspace <name>

# Add module
aq add module <name>

# Run server
aq run dev                # Development mode
aq run prod               # Production mode

# Generate components
aq generate controller <module> <name>
aq generate service <module> <name>

# Discovery
aq discover               # Show registered modules, controllers, services

# Models
aq model parse <file>     # Parse AMDL file
aq model migrate          # Run migrations
```

---

## 19. Testing

### Testing Controllers

```python
import pytest
from aquilia.testing import TestClient

@pytest.fixture
def client():
    from myapp.workspace import workspace
    return TestClient(workspace)

async def test_list_blogs(client):
    response = await client.get("/blogs/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
```

### Testing with DI Mocks

```python
from aquilia.di import TestRegistry, MockProvider

def test_with_mock():
    registry = TestRegistry()
    registry.register(MockProvider(
        UserRepository,
        FakeUserRepository(),
    ))
    # Inject registry into test client
```

### Testing WebSockets

```python
async def test_chat():
    async with client.websocket("/chat") as ws:
        await ws.send_json({"event": "message", "data": {"text": "Hello"}})
        response = await ws.receive_json()
        assert response["type"] == "message"
```

---

## 20. Deployment

### Production Configuration

```yaml
# config/prod.yaml
server:
  mode: prod
  debug: false
  host: 0.0.0.0
  port: 8000
  workers: 4
  access_log: false
```

### Running with Uvicorn

```bash
# Direct
uvicorn myapp.asgi:app --host 0.0.0.0 --port 8000 --workers 4

# Via CLI
aq run prod
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["aq", "run", "prod"]
```

### Environment Variables

```bash
# Override any config with AQUILIA_ prefix
AQUILIA_SERVER__HOST=0.0.0.0
AQUILIA_SERVER__PORT=8000
AQUILIA_SERVER__WORKERS=4
AQUILIA_SERVER__DEBUG=false

# Or set environment
AQUILIA_ENV=prod
```

---

## Quick Reference

### Imports Cheat Sheet

```python
# Core
from aquilia import (
    Controller, RequestCtx, Response,
    GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, WS, route,
    Workspace, Module, Integration, AppManifest,
)

# DI
from aquilia.di import service, factory, inject, Inject, provides, auto_inject

# Sessions
from aquilia.sessions import (
    SessionPolicy, PersistencePolicy, TransportPolicy,
    SessionState, Field,
    session, authenticated, stateful,
)

# Auth
from aquilia.auth import (
    Identity, IdentityType, AuthManager, TokenManager,
    PasswordHasher, PasswordPolicy,
    AuthGuard, RoleGuard, ScopeGuard,
    RBACEngine, ABACEngine,
)

# Faults
from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy, FaultEngine

# WebSockets
from aquilia.sockets import (
    SocketController, Socket, OnConnect, OnDisconnect,
    Event, AckEvent, Subscribe, Unsubscribe, Guard,
    Connection,
)

# Models
from aquilia.models import (
    parse_amdl, parse_amdl_file, parse_amdl_directory,
    ModelProxy, ModelRegistry, Q,
    MigrationRunner, generate_migration_file,
)

# Templates
from aquilia.templates import TemplateEngine, TemplateLoader

# Effects
from aquilia.effects import (
    Effect, EffectKind, EffectProvider, EffectRegistry,
    DBTx, DBTxProvider, CacheEffect, CacheProvider,
)

# Patterns
from aquilia.patterns import PatternCompiler, PatternMatcher, TypeRegistry

# Middleware
from aquilia.middleware import MiddlewareStack, Middleware

# Lifecycle
from aquilia.lifecycle import LifecycleCoordinator, LifecyclePhase

# Config
from aquilia.config import ConfigLoader
```

---

*Built with ❤️ using Aquilia v0.2.0*
