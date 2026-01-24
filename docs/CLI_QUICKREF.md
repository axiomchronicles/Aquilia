# Aquilia CLI - Quick Reference

## 🚀 Getting Started (30 seconds)

```bash
# Create & run a new API
aq init workspace my-api
cd my-api
aq add module users --use-controllers
aq generate controller Users
aq run
```

---

## 📋 Essential Commands

### Project Setup
```bash
aq init workspace <name>              # Create new project
aq add module <name> --use-controllers # Add module with controllers
aq generate controller <Name>         # Generate CRUD controller
```

### Development
```bash
aq run                                # Start dev server (localhost:8000)
aq run --port=3000                    # Custom port
aq validate                           # Check configuration
aq inspect routes                     # View all routes
```

### Production
```bash
aq freeze                             # Freeze artifacts
aq serve --workers=4                  # Start production server
```

---

## 🎯 Controller Generation

### Full CRUD Controller
```bash
aq generate controller Users
```
Generates: `GET /`, `POST /`, `GET /:id`, `PUT /:id`, `DELETE /:id`

### Simple Controller
```bash
aq generate controller Health --simple
```
Generates: Single `GET /` route

### Custom Prefix
```bash
aq generate controller Products --prefix=/api/products
```
Routes: `/api/products/*`

---

## 📦 Module Creation

### Modern (Controllers)
```bash
aq add module users --use-controllers
```
✅ Pattern routing, type safety, DI support

### Legacy (Flows)
```bash
aq add module auth
```
⚠️ Backwards compatibility

### With Dependencies
```bash
aq add module orders --depends-on=users --depends-on=products
```

---

## 🔍 Inspection Commands

```bash
aq inspect routes                     # All routes
aq inspect di                         # DI graph
aq inspect modules                    # All modules
aq inspect faults                     # Fault domains
aq inspect config                     # Resolved config
```

---

## 🛠️ Development Workflow

```bash
# 1. Setup
aq init workspace my-api
cd my-api

# 2. Add modules
aq add module users --use-controllers
aq add module products --use-controllers

# 3. Generate controllers
aq generate controller Users
aq generate controller Products

# 4. Develop
aq run                                # Hot-reload enabled

# 5. Test
aq validate --strict

# 6. Deploy
aq freeze
aq serve --workers=4 --bind=0.0.0.0:8080
```

---

## 📝 Controller Template

```python
from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from typing import Annotated
from aquilia.di import Inject

class UsersController(Controller):
    prefix = "/users"
    tags = ["users"]
    
    # DI injection
    def __init__(self, service: Annotated[UserService, Inject()]):
        self.service = service
    
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        users = await self.service.get_all()
        return Response.json({"users": users})
    
    @POST("/")
    async def create_user(self, ctx: RequestCtx):
        data = await ctx.json()
        user = await self.service.create(data)
        return Response.json(user, status=201)
    
    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        user = await self.service.get_by_id(id)
        if not user:
            return Response.json({"error": "Not found"}, status=404)
        return Response.json(user)
    
    @PUT("/«id:int»")
    async def update_user(self, ctx: RequestCtx, id: int):
        data = await ctx.json()
        user = await self.service.update(id, data)
        return Response.json(user)
    
    @DELETE("/«id:int»")
    async def delete_user(self, ctx: RequestCtx, id: int):
        await self.service.delete(id)
        return Response(status=204)
```

---

## 🎨 Pattern Syntax

```python
# Path parameters with types
@GET("/«id:int»")              # Integer ID
@GET("/«slug:str»")            # String slug
@GET("/«price:float»")         # Float price
@GET("/«active:bool»")         # Boolean flag

# Multiple parameters
@GET("/«category:str»/«id:int»")

# Optional segments
@GET("/users/«id:int»/posts/«post_id:int»")
```

---

## ⚡ Common Tasks

### Add authentication
```bash
aq add module auth --use-controllers
aq generate controller Auth --simple
# Implement login/logout in controllers.py
```

### Add database
```bash
# In services.py
@injectable(scope=Scope.SINGLETON)
class UserService:
    def __init__(self, db: Annotated[Database, Inject()]):
        self.db = db
```

### Add middleware
```python
# In module.aq
middleware:
  - class: AuthMiddleware
  - class: LoggingMiddleware
```

### Handle errors
```python
# In faults.py
class UserNotFoundFault(Fault):
    domain = USER_DOMAIN
    severity = Severity.LOW
    code = "USER_NOT_FOUND"
```

---

## 🔧 Flags & Options

### Global Flags
```bash
--verbose, -v                         # Verbose output
--quiet, -q                           # Minimal output
--version                             # Show version
--help                                # Show help
```

### Run Options
```bash
--mode=dev|test                       # Runtime mode
--port=8000                           # Server port
--host=127.0.0.1                      # Server host
--reload / --no-reload                # Hot-reload
```

### Validation Options
```bash
--strict                              # Production-level validation
--module=<name>                       # Validate single module
```

---

## 📊 Status Codes

```python
Response.json(data)                   # 200 OK
Response.json(data, status=201)       # 201 Created
Response.json(data, status=204)       # 204 No Content
Response.json(error, status=400)      # 400 Bad Request
Response.json(error, status=404)      # 404 Not Found
Response.json(error, status=500)      # 500 Server Error
```

---

## 🐛 Troubleshooting

```bash
# Check configuration
aq doctor

# View detailed errors
aq validate --strict --verbose

# Inspect routing
aq inspect routes

# Check DI
aq inspect di

# Clean restart
rm -rf artifacts/
aq compile
aq run
```

---

## 📚 File Structure

```
my-api/
├── aquilia.aq                        # Workspace manifest
├── modules/
│   └── users/
│       ├── module.aq                 # Module manifest
│       ├── controllers.py            # HTTP endpoints
│       ├── services.py               # Business logic
│       ├── faults.py                 # Error handling
│       └── __init__.py
├── config/
│   ├── base.aq                       # Base config
│   ├── dev.aq                        # Dev overrides
│   └── prod.aq                       # Prod overrides
├── artifacts/                        # Compiled artifacts
└── runtime/                          # Runtime data
```

---

## 🔗 Resources

- **Full Guide**: `docs/CLI_GUIDE.md`
- **Controllers**: `docs/CONTROLLERS.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Examples**: `examples/controllers_modern.py`

---

## 💡 Pro Tips

1. **Always use controllers** for new projects (better type safety)
2. **Validate before deploying** with `aq validate --strict`
3. **Use DI** for testable, maintainable code
4. **Freeze artifacts** for production deployments
5. **Inspect routes** during development to catch conflicts early

---

## 🎓 Learn by Example

```bash
# See complete working example
cat examples/controllers_modern.py

# Generate and compare
aq generate controller Example
aq generate controller Simple --simple
diff controllers/example.py controllers/simple.py
```

---

**Cheat Sheet Version 1.0** | [Full Docs](docs/CLI_GUIDE.md) | [GitHub](https://github.com/embrake/Aquilify)
