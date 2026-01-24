# Migrating to Controllers - Step by Step Guide

This guide helps you migrate from legacy **Flows** to modern **Controllers** in Aquilia.

---

## 🎯 Why Migrate?

### Controllers Offer:
- ✅ **Type Safety** - Pattern-based routing with type annotations (`/«id:int»`)
- ✅ **Better DI** - Constructor injection with `Annotated[T, Inject()]`
- ✅ **Cleaner Code** - Class-based organization
- ✅ **IDE Support** - Better autocomplete and refactoring
- ✅ **Testability** - Easy to instantiate and test
- ✅ **Modern** - Follows current best practices

### Flows Are:
- ⚠️ **Legacy** - Function-based, less type safety
- ⚠️ **Verbose** - Manual `ctx.resolve()` for DI
- ⚠️ **String Paths** - No compile-time validation
- ⚠️ **Maintenance Mode** - Not recommended for new code

---

## 📊 Quick Comparison

### Before (Flows)

```python
from aquilia.routing import route, GET, POST
from aquilia.core import Context

@route("/users/", methods=[GET])
async def get_users(ctx: Context) -> dict:
    service = await ctx.resolve(UserService)
    users = await service.get_all()
    return {"users": users}

@route("/users/{id}", methods=[GET])
async def get_user(ctx: Context) -> dict:
    user_id = ctx.params.get("id")
    service = await ctx.resolve(UserService)
    user = await service.get_by_id(user_id)
    if not user:
        raise UserNotFoundFault(user_id=user_id)
    return user
```

### After (Controllers)

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
        if not user:
            raise UserNotFoundFault(user_id=id)
        return Response.json(user)
```

**Benefits:**
- Parameters automatically typed and converted
- DI via constructor (cleaner)
- Pattern syntax catches errors at compile-time
- All routes in one class (organized)

---

## 🛠️ Migration Strategy

### Option 1: Gradual Migration (Recommended)

Migrate module by module while keeping the app running.

### Option 2: Big Bang

Migrate everything at once (risky, not recommended).

### Option 3: Hybrid

Keep legacy flows, add new features as controllers.

---

## 📋 Step-by-Step Migration

### Step 1: Choose a Module

Start with a simple, low-risk module:

```bash
# Good first candidates:
# - Small modules (few routes)
# - Well-tested modules
# - Non-critical features

# Bad first candidates:
# - Auth/security critical
# - Complex business logic
# - High-traffic endpoints
```

**Example:** Let's migrate the `users` module.

---

### Step 2: Generate Controller Scaffold

```bash
# Generate new controller in the module
cd your-project
aq generate controller Users --output=modules/users/
```

This creates: `modules/users/controllers.py`

---

### Step 3: Copy Routes

Open your existing `flows.py` and identify all routes:

**flows.py (old):**
```python
@route("/users/", methods=[GET])
async def get_users(ctx: Context):
    # ...

@route("/users/", methods=[POST])
async def create_user(ctx: Context):
    # ...

@route("/users/{id}", methods=[GET])
async def get_user(ctx: Context):
    # ...
```

**Map to controller methods:**
- `get_users` → `list_users` (GET /)
- `create_user` → `create_user` (POST /)
- `get_user` → `get_user` (GET /«id:int»)

---

### Step 4: Convert Each Route

#### Example 1: List Route

**Before (Flow):**
```python
@route("/users/", methods=[GET])
async def get_users(ctx: Context) -> dict:
    service = await ctx.resolve(UserService)
    users = await service.get_all()
    return {"users": users}
```

**After (Controller):**
```python
@GET("/")
async def list_users(self, ctx: RequestCtx):
    users = await self.service.get_all()  # DI via constructor
    return Response.json({"users": users})
```

**Changes:**
- ✅ `@route` → `@GET`
- ✅ `ctx: Context` → `ctx: RequestCtx`
- ✅ `ctx.resolve()` → `self.service` (DI)
- ✅ Return dict → `Response.json()`

---

#### Example 2: Create Route

**Before:**
```python
@route("/users/", methods=[POST])
async def create_user(ctx: Context) -> dict:
    data = await ctx.json()
    service = await ctx.resolve(UserService)
    user = await service.create(data)
    return user
```

**After:**
```python
@POST("/")
async def create_user(self, ctx: RequestCtx):
    data = await ctx.json()
    user = await self.service.create(data)
    return Response.json(user, status=201)
```

**Changes:**
- ✅ Added proper 201 status code
- ✅ DI via constructor

---

#### Example 3: Path Parameters

**Before:**
```python
@route("/users/{id}", methods=[GET])
async def get_user(ctx: Context) -> dict:
    user_id = ctx.params.get("id")  # Manual extraction
    user_id = int(user_id)           # Manual conversion
    service = await ctx.resolve(UserService)
    user = await service.get_by_id(user_id)
    return user
```

**After:**
```python
@GET("/«id:int»")
async def get_user(self, ctx: RequestCtx, id: int):  # Automatic!
    user = await self.service.get_by_id(id)
    return Response.json(user)
```

**Changes:**
- ✅ `/users/{id}` → `/«id:int»` (pattern syntax)
- ✅ Manual extraction → automatic parameter `id: int`
- ✅ Manual conversion → automatic type conversion
- ✅ Compile-time validation

---

### Step 5: Handle DI

**Set up constructor injection:**

```python
class UsersController(Controller):
    prefix = "/users"
    
    def __init__(
        self,
        user_service: Annotated[UserService, Inject()],
        auth_service: Annotated[AuthService, Inject()],  # Multiple services
    ):
        self.user_service = user_service
        self.auth_service = auth_service
```

**Replace all `ctx.resolve()` calls:**

```python
# Before
service = await ctx.resolve(UserService)
users = await service.get_all()

# After
users = await self.user_service.get_all()
```

---

### Step 6: Update Manifest

**Edit `modules/users/module.aq`:**

```yaml
# Before
routes:
  - path: /users/
    handler: get_users
    method: GET
  - path: /users/
    handler: create_user
    method: POST

# After
controllers:
  - modules.users.controllers:UsersController

# Remove old routes section entirely
```

---

### Step 7: Update __init__.py

**Edit `modules/users/__init__.py`:**

```python
# Before
from .flows import *
from .services import *
from .faults import *

# After
from .controllers import *  # Changed
from .services import *
from .faults import *
```

---

### Step 8: Test

```bash
# Validate
aq validate --strict

# Check routes
aq inspect routes

# Run tests
pytest tests/test_users.py

# Start dev server
aq run

# Manual testing
curl http://localhost:8000/users/
curl http://localhost:8000/users/1
```

---

### Step 9: Clean Up

**Once verified, remove old flows:**

```bash
# Backup first!
cp modules/users/flows.py modules/users/flows.py.bak

# Remove
rm modules/users/flows.py

# Test again
aq validate
aq run
```

---

### Step 10: Repeat

Migrate next module using the same process.

---

## 🔧 Common Patterns

### Pattern 1: Query Parameters

**Before:**
```python
@route("/users/", methods=[GET])
async def get_users(ctx: Context):
    page = ctx.query.get("page", "1")
    page = int(page)
    limit = ctx.query.get("limit", "10")
    limit = int(limit)
```

**After:**
```python
@GET("/")
async def list_users(self, ctx: RequestCtx):
    page = int(ctx.request.query_params.get("page", "1"))
    limit = int(ctx.request.query_params.get("limit", "10"))
    # Or use query parameter parsing in RequestCtx
```

---

### Pattern 2: Request Body

**Before:**
```python
data = await ctx.json()
name = data.get("name")
email = data.get("email")
```

**After:**
```python
data = await ctx.json()
name = data.get("name")
email = data.get("email")
# Same! No change needed
```

---

### Pattern 3: Headers

**Before:**
```python
auth_header = ctx.headers.get("Authorization")
```

**After:**
```python
auth_header = ctx.request.headers.get("Authorization")
```

---

### Pattern 4: Returning JSON

**Before:**
```python
return {"status": "ok", "data": result}
```

**After:**
```python
return Response.json({"status": "ok", "data": result})
```

---

### Pattern 5: Error Responses

**Before:**
```python
if not user:
    return {"error": "Not found"}, 404  # Tuple
```

**After:**
```python
if not user:
    return Response.json({"error": "Not found"}, status=404)
```

---

### Pattern 6: Multiple HTTP Methods

**Before:**
```python
@route("/users/{id}", methods=[GET, PUT, DELETE])
async def user_detail(ctx: Context):
    if ctx.method == "GET":
        # ...
    elif ctx.method == "PUT":
        # ...
    elif ctx.method == "DELETE":
        # ...
```

**After:**
```python
@GET("/«id:int»")
async def get_user(self, ctx: RequestCtx, id: int):
    # ...

@PUT("/«id:int»")
async def update_user(self, ctx: RequestCtx, id: int):
    # ...

@DELETE("/«id:int»")
async def delete_user(self, ctx: RequestCtx, id: int):
    # ...
```

**Better:** Separate methods for each HTTP verb.

---

## 🎯 Advanced Topics

### Nested Controllers

```python
class UsersController(Controller):
    prefix = "/users"
    
    @GET("/«user_id:int»/posts/«post_id:int»")
    async def get_user_post(
        self,
        ctx: RequestCtx,
        user_id: int,
        post_id: int,
    ):
        # Nested resources
        pass
```

### Controller Composition

```python
class BaseController(Controller):
    def __init__(self, auth: Annotated[AuthService, Inject()]):
        self.auth = auth
    
    async def check_auth(self, ctx: RequestCtx):
        # Shared authentication logic
        pass

class UsersController(BaseController):
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        await self.check_auth(ctx)
        # ...
```

---

## 🐛 Troubleshooting

### Issue: "Route not found"

**Check:**
1. Controller registered in manifest
2. Module imported in `__init__.py`
3. Server restarted after changes

```bash
aq inspect routes  # Verify route is registered
```

---

### Issue: "DI resolution failed"

**Check:**
1. Service registered in DI container
2. Type annotation correct: `Annotated[Service, Inject()]`
3. Service has `@injectable` decorator

```bash
aq inspect di  # Check DI graph
```

---

### Issue: "Parameter not bound"

**Check:**
1. Pattern syntax: `/«id:int»` not `/{id}`
2. Parameter name matches method argument
3. Type annotation on method parameter

```python
# Correct
@GET("/«id:int»")
async def get_user(self, ctx: RequestCtx, id: int):
    pass
```

---

### Issue: "Response type error"

**Check:**
1. Return `Response.json()` not dict
2. Status code is int, not string
3. Content type set correctly

```python
# Correct
return Response.json(data, status=200)

# Incorrect
return data  # Missing Response wrapper
```

---

## ✅ Migration Checklist

Per module:

- [ ] Generate controller scaffold
- [ ] Copy all routes to controller methods
- [ ] Convert decorators (`@route` → `@GET/POST/etc`)
- [ ] Update path parameters (`{id}` → `«id:int»`)
- [ ] Convert DI (`ctx.resolve()` → constructor injection)
- [ ] Update responses (dict → `Response.json()`)
- [ ] Update manifest (add controller entry)
- [ ] Update `__init__.py` imports
- [ ] Test thoroughly
- [ ] Remove old `flows.py`
- [ ] Update documentation

---

## 📚 Resources

- **CLI Guide**: `docs/CLI_GUIDE.md`
- **Quick Reference**: `docs/CLI_QUICKREF.md`
- **Controller Example**: `examples/controllers_modern.py`
- **Pattern Syntax**: `docs/PATTERNS.md`

---

## 🎉 Success!

You've migrated to modern controllers! Enjoy:
- Better type safety
- Cleaner code
- Easier testing
- Improved IDE support

**Welcome to the future of Aquilia! 🚀**
