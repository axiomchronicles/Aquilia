# Aquilia CLI (`aq`) - Complete Guide

The Aquilia CLI provides manifest-driven project orchestration with support for both modern **Controllers** and legacy **Flows**.

## Installation

```bash
pip install aquilia
```

## Quick Start

```bash
# Create a new workspace
aq init workspace my-api

# Add a module with controllers (modern)
cd my-api
aq add module users --use-controllers

# Or add a module with flows (legacy)
aq add module auth

# Generate a controller
aq generate controller Products --prefix=/api/products

# Run development server
aq run
```

---

## Commands Overview

### 🆕 **init** - Initialize Projects

Create new workspaces or modules.

#### Create Workspace

```bash
aq init workspace <name> [options]

Options:
  --minimal          Create minimal setup without examples
  --template=TYPE    Use template: api, service, monolith

Examples:
  aq init workspace my-api
  aq init workspace backend --minimal
  aq init workspace microservice --template=api
```

**Generated Structure:**
```
my-api/
├── aquilia.aq          # Workspace manifest
├── modules/            # Application modules
├── config/
│   ├── base.aq        # Base configuration
│   ├── dev.aq         # Development config
│   └── prod.aq        # Production config
├── artifacts/          # Compiled artifacts
└── runtime/            # Runtime data
```

---

### 📦 **add** - Add Modules

Add new modules to your workspace with controllers or flows.

```bash
aq add module <name> [options]

Options:
  --depends-on=MODULE     Module dependencies (can be repeated)
  --fault-domain=DOMAIN   Custom fault domain
  --route-prefix=PREFIX   Route prefix
  --use-controllers       Use modern controllers (recommended)

Examples:
  # Modern controller-based module
  aq add module users --use-controllers
  
  # Legacy flow-based module
  aq add module auth
  
  # Module with dependencies
  aq add module orders --depends-on=users --depends-on=products
  
  # Custom routing and fault handling
  aq add module admin --fault-domain=ADMIN --route-prefix=/admin
```

**Module with Controllers:**
```
modules/users/
├── module.aq         # Module manifest
├── controllers.py    # HTTP endpoints (modern)
├── services.py       # Business logic
├── faults.py         # Error handling
└── __init__.py
```

**Module with Flows (Legacy):**
```
modules/auth/
├── module.aq         # Module manifest
├── flows.py          # HTTP endpoints (legacy)
├── services.py       # Business logic
├── faults.py         # Error handling
└── __init__.py
```

---

### 🎯 **generate** - Code Generation

Generate controllers, flows, and other boilerplate code.

#### Generate Controller (Recommended)

```bash
aq generate controller <name> [options]

Options:
  --prefix=PATH       Route prefix (default: /name)
  --resource=NAME     Resource name (default: name)
  --simple            Generate simple controller (single route)
  --output=DIR        Output directory (default: controllers)

Examples:
  # Full CRUD controller
  aq generate controller Users
  
  # Controller with custom prefix
  aq generate controller Products --prefix=/api/products
  
  # Simple controller (single route)
  aq generate controller Health --simple
  
  # Custom output directory
  aq generate controller Admin --output=apps/admin/
```

**Generated Controller (Full CRUD):**
```python
from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"
    tags = ["users"]
    
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        return Response.json({"users": []})
    
    @POST("/")
    async def create_user(self, ctx: RequestCtx):
        data = await ctx.json()
        return Response.json(data, status=201)
    
    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        return Response.json({"id": id})
    
    @PUT("/«id:int»")
    async def update_user(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        return Response.json({"id": id, **data})
    
    @DELETE("/«id:int»")
    async def delete_user(self, ctx: RequestCtx, id: int):
        return Response(status=204)
```

#### Generate Flow (Legacy)

```bash
aq generate flow <name> [options]

Options:
  --method=METHOD     HTTP method (GET, POST, PUT, DELETE, PATCH)
  --path=PATH         Route path
  --output=DIR        Output directory (default: flows)

Examples:
  aq generate flow get_users
  aq generate flow create_user --method=POST --path=/users
  aq generate flow update_user --method=PUT --path=/users/{id}
```

---

### ✅ **validate** - Validate Manifests

Validate workspace configuration and manifests.

```bash
aq validate [options]

Options:
  --strict            Strict validation (production-level)
  --module=NAME       Validate single module

Examples:
  aq validate
  aq validate --strict
  aq validate --module=users
```

**What it checks:**
- Manifest syntax and structure
- Module dependencies
- Route conflicts
- DI provider configuration
- Fault domain definitions

---

### 🔨 **compile** - Compile Artifacts

Compile manifests to optimized artifacts.

```bash
aq compile [options]

Options:
  --watch             Watch for changes and recompile
  --output=DIR        Output directory

Examples:
  aq compile
  aq compile --watch
  aq compile --output=dist/
```

**Generated Artifacts:**
- Compiled routing table
- DI dependency graph
- Fault handler registry
- Configuration merged by environment

---

### 🚀 **run** - Development Server

Start development server with hot-reload.

```bash
aq run [options]

Options:
  --mode=MODE         Runtime mode: dev, test (default: dev)
  --port=PORT         Server port (default: 8000)
  --host=HOST         Server host (default: 127.0.0.1)
  --reload/--no-reload  Enable/disable hot-reload (default: enabled)

Examples:
  aq run
  aq run --port=3000
  aq run --mode=test --no-reload
  aq run --host=0.0.0.0 --port=8080
```

**Features:**
- Hot-reload on file changes
- Auto-discovery of controllers and flows
- DI container initialization
- Fault handling active
- Request logging

---

### 🎭 **serve** - Production Server

Start production server with frozen artifacts.

```bash
aq serve [options]

Options:
  --workers=NUM       Number of workers (default: 1)
  --bind=ADDRESS      Bind address (default: 0.0.0.0:8000)

Examples:
  aq serve
  aq serve --workers=4
  aq serve --bind=0.0.0.0:8080

Note: Requires frozen artifacts (run `aq freeze` first)
```

---

### ❄️ **freeze** - Freeze Artifacts

Generate immutable artifacts for production deployment.

```bash
aq freeze [options]

Options:
  --output=DIR        Output directory
  --sign              Sign artifacts for verification

Examples:
  aq freeze
  aq freeze --output=dist/
  aq freeze --sign
```

**What gets frozen:**
- Compiled routes and patterns
- DI dependency graph
- Fault handlers
- Configuration (merged)
- Static assets

---

### 🔍 **inspect** - Inspect Artifacts

Query and inspect compiled artifacts.

```bash
aq inspect <target>

Targets:
  routes              Show compiled routes
  di                  Show DI graph
  modules             List all modules
  faults              Show fault domains
  config              Show resolved configuration

Examples:
  aq inspect routes
  aq inspect di
  aq inspect modules
  aq inspect faults
  aq inspect config
```

**Sample Output (routes):**
```
╔═══════════════════════════════════════════════════════════════╗
║ Compiled Routes                                               ║
╠═══════════════════════════════════════════════════════════════╣
║ GET     /users                    → UsersController.list      ║
║ POST    /users                    → UsersController.create    ║
║ GET     /users/«id:int»          → UsersController.get       ║
║ PUT     /users/«id:int»          → UsersController.update    ║
║ DELETE  /users/«id:int»          → UsersController.delete    ║
║ GET     /health                   → HealthController.check    ║
╚═══════════════════════════════════════════════════════════════╝
```

---

### 🔄 **migrate** - Migrate Projects

Migrate from legacy Django-style projects to Aquilia.

```bash
aq migrate <source> [options]

Sources:
  legacy              Migrate from Django-style layout

Options:
  --dry-run           Preview migration without changes

Examples:
  aq migrate legacy --dry-run
  aq migrate legacy
```

---

### 🏥 **doctor** - Diagnose Issues

Diagnose workspace configuration and health.

```bash
aq doctor

Examples:
  aq doctor
```

**Checks:**
- Manifest validity
- Module structure
- Dependency resolution
- Configuration issues
- Common misconfigurations

---

## Architecture Comparison

### Modern: Controllers (Recommended)

✅ **Advantages:**
- Pattern-based routing with type safety (`/users/«id:int»`)
- Clean class-based structure
- Built-in DI support via `Annotated[T, Inject()]`
- Better IDE support and autocomplete
- Easier testing with controller instances
- Automatic parameter binding

```python
from aquilia import Controller, GET, POST, RequestCtx, Response
from typing import Annotated
from aquilia.di import Inject

class UsersController(Controller):
    prefix = "/users"
    
    def __init__(self, service: Annotated[UserService, Inject()]):
        self.service = service
    
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        users = await self.service.get_all()
        return Response.json({"users": users})
    
    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        user = await self.service.get_by_id(id)
        return Response.json(user)
```

### Legacy: Flows

⚠️ **For backwards compatibility:**
- Function-based routing
- Manual DI resolution via `ctx.resolve()`
- String-based route paths
- Less type safety

```python
from aquilia.routing import route, GET
from aquilia.core import Context

@route("/users/", methods=[GET])
async def get_users(ctx: Context) -> dict:
    service = await ctx.resolve(UserService)
    users = await service.get_all()
    return {"users": users}
```

---

## Best Practices

### 1. Use Controllers for New Projects

```bash
aq add module users --use-controllers
aq generate controller Users
```

### 2. Organize by Domain

```
modules/
├── users/          # User management
├── products/       # Product catalog
├── orders/         # Order processing
└── notifications/  # Notification system
```

### 3. Use DI for Dependencies

```python
class UsersController(Controller):
    def __init__(
        self,
        user_service: Annotated[UserService, Inject()],
        auth_service: Annotated[AuthService, Inject()],
    ):
        self.user_service = user_service
        self.auth_service = auth_service
```

### 4. Define Custom Faults

```python
from aquilia.faults import Fault, FaultDomain, Severity

USER_DOMAIN = FaultDomain(name="USER", description="User faults")

class UserNotFoundFault(Fault):
    domain = USER_DOMAIN
    severity = Severity.LOW
    code = "USER_NOT_FOUND"
```

### 5. Environment-Specific Config

```
config/
├── base.aq      # Common settings
├── dev.aq       # Development overrides
├── test.aq      # Test overrides
└── prod.aq      # Production overrides
```

---

## Workflow Examples

### Creating a REST API

```bash
# 1. Create workspace
aq init workspace my-api

# 2. Add modules with controllers
cd my-api
aq add module users --use-controllers
aq add module products --use-controllers
aq add module orders --depends-on=users --depends-on=products --use-controllers

# 3. Generate controllers
aq generate controller Users
aq generate controller Products
aq generate controller Orders

# 4. Validate
aq validate --strict

# 5. Run
aq run --port=8000
```

### Migrating from Flows to Controllers

```bash
# 1. Generate new controller
aq generate controller Users --output=modules/users/

# 2. Copy logic from flows.py to controllers.py

# 3. Update module manifest (replace flows with controllers)

# 4. Test
aq run

# 5. Remove old flows.py when verified
```

---

## Troubleshooting

### "Module not found"
```bash
# Check module structure
aq inspect modules

# Validate manifests
aq validate --strict
```

### "Route conflict"
```bash
# Inspect routes
aq inspect routes

# Check route prefixes in module manifests
```

### "DI resolution failed"
```bash
# Inspect DI graph
aq inspect di

# Check service registration in services.py
```

### "Hot-reload not working"
```bash
# Ensure you're in development mode
aq run --reload

# Check file permissions
```

---

## Environment Variables

```bash
# Aquilia environment
export AQUILIA_ENV=dev|test|prod

# Server settings
export AQUILIA_HOST=0.0.0.0
export AQUILIA_PORT=8000

# Logging
export AQUILIA_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# Development
export AQUILIA_RELOAD=true|false
```

---

## Advanced Usage

### Custom Templates

Create custom workspace templates:

```bash
~/.aquilia/templates/
└── my-template/
    ├── aquilia.aq
    ├── modules/
    └── config/
```

Use with:
```bash
aq init workspace my-app --template=my-template
```

### Programmatic API

```python
from aquilia.cli.generators import generate_controller

# Generate controller programmatically
file_path = generate_controller(
    name="Users",
    output_dir="controllers",
    prefix="/api/users",
    simple=False,
)
```

---

## Summary

| Command | Purpose | Example |
|---------|---------|---------|
| `init workspace` | Create new project | `aq init workspace my-api` |
| `add module` | Add module | `aq add module users --use-controllers` |
| `generate controller` | Generate controller | `aq generate controller Users` |
| `generate flow` | Generate flow (legacy) | `aq generate flow get_users` |
| `validate` | Validate manifests | `aq validate --strict` |
| `compile` | Compile artifacts | `aq compile --watch` |
| `run` | Start dev server | `aq run --port=8000` |
| `serve` | Start prod server | `aq serve --workers=4` |
| `freeze` | Freeze artifacts | `aq freeze --sign` |
| `inspect` | Inspect artifacts | `aq inspect routes` |
| `migrate` | Migrate projects | `aq migrate legacy` |
| `doctor` | Diagnose issues | `aq doctor` |

---

## Getting Help

```bash
# General help
aq --help

# Command-specific help
aq init --help
aq add --help
aq generate --help

# Version
aq --version
```

---

**Ready to build modern APIs with Aquilia! 🚀**
