# Migration Guide

## Migrating from Flask

### Basic Application

**Flask:**
```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/users/<int:id>')
def get_user(id):
    return jsonify({"id": id})

if __name__ == '__main__':
    app.run()
```

**Aquilia:**
```python
from aquilia import AppManifest, flow, Response

class MyApp(AppManifest):
    name = "myapp"
    version = "1.0.0"
    controllers = ["myapp.controllers:UserController"]

class UserController:
    @flow("/users/{id}").GET
    async def get_user(self, id: int):
        return Response.json({"id": id})

# main.py
from aquilia import Registry, AquiliaServer
registry = Registry.from_manifests([MyApp])
server = AquiliaServer(registry=registry)
server.run()
```

### Key Differences

1. **Async by default**: All handlers are async
2. **Type hints**: Path parameters are typed
3. **Manifest-driven**: Apps declared as manifests
4. **Flow decorators**: `@flow(pattern).METHOD` instead of `@app.route`
5. **Response builders**: Explicit Response objects

## Migrating from FastAPI

### Basic Application

**FastAPI:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

@app.get("/users/{id}")
async def get_user(id: int):
    return {"id": id}

@app.post("/users")
async def create_user(user: User):
    return user
```

**Aquilia:**
```python
from aquilia import AppManifest, flow, Response
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str

class MyApp(AppManifest):
    name = "myapp"
    version = "1.0.0"
    controllers = ["myapp.controllers:UserController"]

class UserController:
    @flow("/users/{id}").GET
    async def get_user(self, id: int):
        return Response.json({"id": id})
    
    @flow("/users").POST
    async def create_user(self, request):
        user_data = await request.json(User)
        return Response.json(user_data)
```

### Key Differences

1. **Manifest system**: Apps structured as manifests
2. **Explicit DI**: Services injected by name/type
3. **Effects system**: Database/cache as effects
4. **Request object**: Explicit request parameter
5. **Registry**: Central orchestration

## Migrating from Django

### Views

**Django:**
```python
from django.http import JsonResponse
from django.views import View

class UserView(View):
    def get(self, request, id):
        return JsonResponse({"id": id})
    
    def post(self, request):
        data = json.loads(request.body)
        return JsonResponse(data, status=201)
```

**Aquilia:**
```python
from aquilia import flow, Response

class UserController:
    @flow("/users/{id}").GET
    async def get_user(self, id: int):
        return Response.json({"id": id})
    
    @flow("/users").POST
    async def create_user(self, request):
        data = await request.json()
        return Response.json(data, status=201)
```

### App Structure

**Django:**
- apps/
  - myapp/
    - models.py
    - views.py
    - urls.py
    - apps.py

**Aquilia:**
- apps/
  - myapp/
    - app.py (manifest)
    - controllers.py
    - services.py

## Common Patterns

### Dependency Injection

**Before (Flask/FastAPI):**
```python
# Global instance
db = Database()

@app.route('/users')
def get_users():
    return db.query_all()
```

**After (Aquilia):**
```python
# Service registration in manifest
class MyApp(AppManifest):
    services = ["myapp.services:Database"]

# DI in handler
@flow("/users").GET
async def get_users(self, Database: Database):
    return await Database.query_all()
```

### Middleware

**Before (Flask):**
```python
@app.before_request
def before():
    # Pre-processing
    pass

@app.after_request
def after(response):
    # Post-processing
    return response
```

**After (Aquilia):**
```python
async def my_middleware(request, ctx, next):
    # Pre-processing
    response = await next(request, ctx)
    # Post-processing
    return response

# Register in manifest
class MyApp(AppManifest):
    middlewares = [
        ("myapp.middleware:my_middleware", {}),
    ]
```

### Configuration

**Before (Flask/Django):**
```python
app.config['DATABASE_URL'] = 'postgresql://...'
```

**After (Aquilia):**
```python
from aquilia import Config

class MyConfig(Config):
    database_url: str = "postgresql://..."

class MyApp(AppManifest):
    config = MyConfig

# Access in handler
async def handler(self):
    cfg = self.config  # App-specific config
```

## Testing

**Before (pytest + Flask):**
```python
def test_endpoint():
    client = app.test_client()
    response = client.get('/users/1')
    assert response.status_code == 200
```

**After (Aquilia):**
```python
@pytest.mark.asyncio
async def test_endpoint():
    registry = Registry.from_manifests(
        [MyApp],
        overrides={"Database": MockDatabase}
    )
    server = AquiliaServer(registry=registry)
    await server.startup()
    
    # Test logic
    
    await server.shutdown()
```

## Benefits of Migration

1. **Type Safety**: Full type hints throughout
2. **Testability**: Scoped DI and overrides
3. **Modularity**: App manifests and dependencies
4. **Observability**: Built-in fingerprinting and tracing
5. **Performance**: Async-native, optimized routing
6. **Developer Experience**: Flow-first, explicit DI

## Migration Checklist

- [ ] Convert routes to flow decorators
- [ ] Create app manifests
- [ ] Move config to typed Config classes
- [ ] Register services in manifests
- [ ] Convert middleware to async
- [ ] Update tests to use Registry
- [ ] Update deployment scripts
- [ ] Run `aq validate` to check setup
