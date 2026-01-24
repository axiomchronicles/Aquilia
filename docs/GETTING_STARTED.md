# Getting Started with Aquilia

Welcome to Aquilia! This guide will walk you through creating your first Aquilia application.

## Prerequisites

- Python 3.10 or higher
- pip
- Virtual environment (recommended)

## Installation

### Option 1: Using pip (when published)

```bash
pip install aquilia uvicorn
```

### Option 2: From source

```bash
git clone https://github.com/yourusername/aquilia.git
cd aquilia
pip install -e .
```

## Your First Aquilia App

### 1. Create Project Structure

Use the CLI to scaffold a new project:

```bash
aq new project my-todo-app
cd my-todo-app
```

This creates:
```
my-todo-app/
├── apps/
│   └── hello/
│       ├── __init__.py
│       ├── app.py
│       └── controllers.py
├── config/
│   └── default.py
├── project/
│   ├── __init__.py
│   └── settings.py
├── main.py
├── .env
└── requirements.txt
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
python main.py
```

Visit http://localhost:8000/hello

## Understanding the Structure

### App Manifest (`apps/hello/app.py`)

The manifest is the heart of your app:

```python
from aquilia import AppManifest, Config

class HelloConfig(Config):
    greeting: str = "Hello"

class HelloApp(AppManifest):
    name = "hello"
    version = "1.0.0"
    config = HelloConfig
    controllers = ["apps.hello.controllers:HelloController"]
    services = []
    depends_on = []
    
    def on_startup(self, ctx):
        ctx.log.info("Hello app starting")
```

**Key Points:**
- Pure data declaration (no side effects)
- Typed configuration
- Explicit dependencies
- Lifecycle hooks

### Controllers (`apps.hello.controllers.py`)

Controllers define your API endpoints:

```python
from aquilia import flow, Response

class HelloController:
    @flow("/hello").GET
    async def greet(self):
        return Response.json({"message": "Hello, World!"})
    
    @flow("/hello/{name}").GET
    async def greet_user(self, name: str):
        return Response.json({"message": f"Hello, {name}!"})
```

**Key Points:**
- `@flow(pattern).METHOD` decorator
- Typed path parameters
- Async handlers
- Explicit Response objects

### Main Entry Point (`main.py`)

```python
from aquilia import ConfigLoader, Registry, AquiliaServer
from project.settings import AQ_APPS

def main():
    # Load configuration
    cfg = ConfigLoader.load(
        paths=["config/*.py"],
        env_prefix="AQ_",
    )
    
    # Create registry
    registry = Registry.from_manifests(AQ_APPS, config=cfg)
    
    # Create and run server
    server = AquiliaServer(registry=registry, config=cfg)
    server.run()

if __name__ == "__main__":
    main()
```

## Building a Real App: Todo API

Let's build a simple Todo API to demonstrate Aquilia's features.

### Step 1: Create the App

```bash
aq new app todos
```

### Step 2: Define the Service

**apps/todos/services.py:**

```python
class TodoService:
    def __init__(self):
        self.todos = {}
        self.next_id = 1
    
    async def list_todos(self):
        return list(self.todos.values())
    
    async def get_todo(self, todo_id: int):
        if todo_id not in self.todos:
            raise KeyError(f"Todo {todo_id} not found")
        return self.todos[todo_id]
    
    async def create_todo(self, title: str, completed: bool = False):
        todo = {
            "id": self.next_id,
            "title": title,
            "completed": completed,
        }
        self.todos[self.next_id] = todo
        self.next_id += 1
        return todo
```

### Step 3: Create Controllers

**apps/todos/controllers.py:**

```python
from aquilia import flow, Response
from .services import TodoService

class TodoController:
    @flow("/todos").GET
    async def list_todos(self, TodoService: TodoService):
        todos = await TodoService.list_todos()
        return Response.json(todos)
    
    @flow("/todos/{id}").GET
    async def get_todo(self, id: int, TodoService: TodoService):
        try:
            todo = await TodoService.get_todo(id)
            return Response.json(todo)
        except KeyError:
            return Response.json(
                {"error": "Not found"},
                status=404,
            )
    
    @flow("/todos").POST
    async def create_todo(self, request, TodoService: TodoService):
        data = await request.json()
        todo = await TodoService.create_todo(
            title=data["title"],
            completed=data.get("completed", False),
        )
        return Response.json(todo, status=201)
```

### Step 4: Define the Manifest

**apps/todos/app.py:**

```python
from aquilia import AppManifest, Config

class TodoConfig(Config):
    max_todos: int = 100

class TodoApp(AppManifest):
    name = "todos"
    version = "1.0.0"
    config = TodoConfig
    controllers = ["apps.todos.controllers:TodoController"]
    services = ["apps.todos.services:TodoService"]
```

### Step 5: Register the App

**project/settings.py:**

```python
from apps.todos.app import TodoApp

AQ_APPS = [TodoApp]
```

### Step 6: Run and Test

```bash
# Run server
python main.py

# Test endpoints
curl http://localhost:8000/todos

curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Aquilia"}'

curl http://localhost:8000/todos/1
```

## Key Concepts

### 1. Dependency Injection

Services are injected by name/type:

```python
@flow("/users/{id}").GET
async def get_user(self, id: int, UserService: UserService, Database: Database):
    # UserService and Database are auto-injected
    user = await UserService.get_user(id)
    return Response.json(user)
```

### 2. Configuration

Type-safe configuration with merge precedence:

```python
# Define config
class MyConfig(Config):
    database_url: str = "sqlite:///app.db"
    debug: bool = False

# Use in manifest
class MyApp(AppManifest):
    config = MyConfig
```

**Override via environment:**
```bash
export AQ_APPS__MYAPP__DEBUG=true
```

### 3. Effects

Declare capabilities in handler signatures:

```python
from aquilia import DBTx

@flow("/orders/{id}").POST
async def create_order(self, id: int, db: DBTx['write']):
    # db is automatically acquired and released
    order = await db.create_order(id)
    return Response.json(order)
```

### 4. Middleware

Composable request/response pipeline:

```python
async def timing_middleware(request, ctx, next):
    start = time.time()
    response = await next(request, ctx)
    duration = time.time() - start
    response.headers["X-Duration"] = str(duration)
    return response

# Register in manifest
class MyApp(AppManifest):
    middlewares = [
        ("myapp.middleware:timing_middleware", {}),
    ]
```

### 5. Testing

Test with registry overrides:

```python
import pytest
from aquilia import Registry

class MockTodoService:
    async def list_todos(self):
        return [{"id": 1, "title": "Test"}]

@pytest.mark.asyncio
async def test_list_todos():
    registry = Registry.from_manifests(
        [TodoApp],
        overrides={"TodoService": MockTodoService}
    )
    
    server = AquiliaServer(registry=registry)
    await server.startup()
    
    # Test logic
    
    await server.shutdown()
```

## CLI Commands

```bash
# Validate project
aq validate

# Inspect routes
aq inspect

# Show configuration
aq config

# Run with reload
aq run --reload

# Create new app
aq new app notifications
```

## Next Steps

1. **Explore Examples**: Check out `examples/` directory
2. **Read API Docs**: See `docs/API.md`
3. **Understand Architecture**: See `docs/ARCHITECTURE.md`
4. **Join Community**: GitHub Discussions

## Common Patterns

### REST API

```python
class UserController:
    @flow("/users").GET
    async def list_users(self, UserService: UserService):
        return Response.json(await UserService.list())
    
    @flow("/users/{id}").GET
    async def get_user(self, id: int, UserService: UserService):
        return Response.json(await UserService.get(id))
    
    @flow("/users").POST
    async def create_user(self, request, UserService: UserService):
        data = await request.json()
        return Response.json(await UserService.create(data), status=201)
```

### Authentication

```python
async def auth_middleware(request, ctx, next):
    token = request.header("authorization")
    if not token:
        return Response.json({"error": "Unauthorized"}, status=401)
    
    # Validate token
    user = validate_token(token)
    request.state["user"] = user
    
    return await next(request, ctx)
```

### Error Handling

```python
from aquilia.middleware import ExceptionMiddleware

# Built-in exception handling
class MyApp(AppManifest):
    # ExceptionMiddleware is added by default
    pass

# Custom error responses
@flow("/users/{id}").GET
async def get_user(self, id: int, UserService: UserService):
    try:
        return Response.json(await UserService.get(id))
    except KeyError:
        return Response.json({"error": "Not found"}, status=404)
    except ValueError as e:
        return Response.json({"error": str(e)}, status=400)
```

## Troubleshooting

### Import Errors

Make sure your project structure matches the import paths in manifests:
```python
controllers = ["apps.myapp.controllers:MyController"]
#              ^^^^^^^^^^^^^^^^^^^^^^^ must match directory structure
```

### Config Not Loading

Check environment variable format:
```bash
# Correct
export AQ_APPS__MYAPP__DEBUG=true

# Incorrect (missing double underscore)
export AQ_APPS_MYAPP_DEBUG=true
```

### Routes Not Working

Validate your project:
```bash
aq validate
aq inspect  # See registered routes
```

## Resources

- **Documentation**: `docs/`
- **Examples**: `examples/`
- **Tests**: `tests/`
- **GitHub**: https://github.com/yourusername/aquilia
- **Issues**: https://github.com/yourusername/aquilia/issues

---

Welcome to Aquilia! Happy coding! 🌊
