import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Zap, Rocket } from 'lucide-react'

export function QuickStartPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Zap className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Quick Start
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Build a working API in 5 minutes</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          This guide walks you through creating, configuring, and running an Aquilia application from scratch.
          By the end, you'll have a multi-endpoint REST API with dependency injection, sessions, and authentication.
        </p>
      </div>

      {/* Step 1: Create workspace */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">1</span>
          Create a Workspace
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>aq init workspace</code> command scaffolds a complete project structure:
        </p>

        <CodeBlock
          code={`# Create a new workspace
aq init workspace my-api

# Navigate into it
cd my-api`}
          language="bash"
        />

        <p className={`mt-4 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          This creates the following layout:
        </p>

        <CodeBlock
          code={`my-api/
├── workspace.py          # Workspace configuration (Python-first)
├── modules/
│   └── core/
│       ├── __init__.py
│       ├── controllers.py  # Controller classes
│       ├── services.py     # Business logic services
│       └── models.py       # ORM model definitions
├── templates/              # Jinja2 templates (optional)
├── static/                 # Static files (optional)
└── .aquilia/               # Trace directory (auto-generated)`}
          language="text"
        />

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            <strong>Templates:</strong> Use <code>aq init workspace my-api --template=api</code> for an API-only setup,
            or <code>--template=monolith</code> for a full-stack setup with templates and static files.
            Use <code>--minimal</code> for the bare minimum.
          </p>
        </div>
      </section>

      {/* Step 2: Configure workspace */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">2</span>
          Configure the Workspace
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Open <code>workspace.py</code>. This is your application's root configuration — Aquilia uses
          Python-first configuration through fluent builder classes:
        </p>

        <CodeBlock
          code={`# workspace.py
from aquilia import Workspace, Module, Integration

app = (
    Workspace("my-api")
    # Register modules
    .module(
        Module("core")
        .auto_discover("modules/core")  # Scans for controllers, services, models
    )
    # Enable integrations
    .integrate(
        Integration.database(url="sqlite:///db.sqlite3"),
        Integration.sessions(),
        Integration.auth(),
        Integration.cache(backend="memory"),
        Integration.cors(
            allow_origins=["http://localhost:3000"],
            allow_methods=["GET", "POST", "PUT", "DELETE"],
        ),
    )
    # Runtime settings
    .runtime(
        debug=True,
        host="0.0.0.0",
        port=8000,
    )
    .build()
)`}
          language="python"
        />

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <strong>Key concepts:</strong>
          </p>
          <ul className={`text-sm mt-2 space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <li>• <code>Workspace</code> — top-level container for the entire application</li>
            <li>• <code>Module</code> — a logical grouping of controllers, services, and models</li>
            <li>• <code>Integration</code> — static methods that configure cross-cutting concerns</li>
            <li>• <code>.auto_discover()</code> — scans a directory for controller/service/model classes</li>
            <li>• <code>.build()</code> — finalizes and returns the configuration dict</li>
          </ul>
        </div>
      </section>

      {/* Step 3: Create controller */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">3</span>
          Write a Controller
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Controllers are class-based handlers. Each class has a <code>prefix</code> and decorated
          methods for each HTTP endpoint:
        </p>

        <CodeBlock
          code={`# modules/core/controllers.py
from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response

class TasksController(Controller):
    """CRUD controller for tasks."""
    prefix = "/api/tasks"
    tags = ["Tasks"]

    def __init__(self, task_service: "TaskService"):
        """Constructor DI — the container injects TaskService automatically."""
        self.task_service = task_service

    @GET("/")
    async def list_tasks(self, ctx: RequestCtx) -> Response:
        """List all tasks, with optional filtering."""
        status_filter = ctx.query_param("status")
        tasks = await self.task_service.list(status=status_filter)
        return Response.json({"tasks": tasks})

    @GET("/«id:int»")
    async def get_task(self, ctx: RequestCtx, id: int) -> Response:
        """Get a single task by ID."""
        task = await self.task_service.get(id)
        if not task:
            return Response.json({"error": "Task not found"}, status=404)
        return Response.json(task)

    @POST("/")
    async def create_task(self, ctx: RequestCtx) -> Response:
        """Create a new task from JSON body."""
        data = await ctx.json()
        task = await self.task_service.create(data)
        return Response.json(task, status=201)

    @PUT("/«id:int»")
    async def update_task(self, ctx: RequestCtx, id: int) -> Response:
        """Update an existing task."""
        data = await ctx.json()
        task = await self.task_service.update(id, data)
        return Response.json(task)

    @DELETE("/«id:int»")
    async def delete_task(self, ctx: RequestCtx, id: int) -> Response:
        """Delete a task."""
        await self.task_service.delete(id)
        return Response.json({"deleted": True})`}
          language="python"
        />

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <strong>Route parameters:</strong> Aquilia uses <code>«name:type»</code> syntax for URL
            parameters. Supported types: <code>int</code>, <code>str</code>, <code>uuid</code>, <code>slug</code>, <code>path</code>.
            Parameters are automatically extracted and passed as keyword arguments.
          </p>
        </div>
      </section>

      {/* Step 4: Create service */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">4</span>
          Write a Service
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Services contain business logic and are injected into controllers via the DI container.
          Mark them with <code>@service</code> to register them automatically:
        </p>

        <CodeBlock
          code={`# modules/core/services.py
from aquilia import service

@service(scope="app")
class TaskService:
    """Business logic for task management.

    Scoped as "app" — one instance shared across all requests.
    """
    def __init__(self):
        # In a real app, inject a database or repository
        self._tasks: dict[int, dict] = {}
        self._next_id = 1

    async def list(self, status: str | None = None) -> list[dict]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    async def get(self, task_id: int) -> dict | None:
        return self._tasks.get(task_id)

    async def create(self, data: dict) -> dict:
        task = {
            "id": self._next_id,
            "title": data.get("title", "Untitled"),
            "status": data.get("status", "pending"),
        }
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    async def update(self, task_id: int, data: dict) -> dict:
        task = self._tasks.get(task_id, {})
        task.update(data)
        task["id"] = task_id
        self._tasks[task_id] = task
        return task

    async def delete(self, task_id: int) -> None:
        self._tasks.pop(task_id, None)`}
          language="python"
        />
      </section>

      {/* Step 5: Run */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">5</span>
          Run the Development Server
        </h2>

        <CodeBlock
          code={`# Start the development server (auto-reload enabled)
aq run

# Or with explicit options
aq run --host 0.0.0.0 --port 8000 --reload`}
          language="bash"
        />

        <p className={`mt-4 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          You'll see the startup sequence:
        </p>

        <CodeBlock
          code={`╔══════════════════════════════════════════╗
║     Aquilia v1.0.0  ✓  Development       ║
╚══════════════════════════════════════════╝

  → Loading workspace.py ...
  ✓ Module "core" discovered
    ├─ Controllers: TasksController
    ├─ Services: TaskService
    └─ Models: (none)
  ✓ Middleware stack compiled (5 layers)
  ✓ DI container ready (2 providers)
  ✓ Routes compiled:
    GET    /api/tasks/
    GET    /api/tasks/«id:int»
    POST   /api/tasks/
    PUT    /api/tasks/«id:int»
    DELETE /api/tasks/«id:int»

  Serving on http://0.0.0.0:8000 (Press Ctrl+C to stop)`}
          language="text"
        />
      </section>

      {/* Step 6: Test */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">6</span>
          Test with cURL
        </h2>

        <CodeBlock
          code={`# Create a task
curl -X POST http://localhost:8000/api/tasks/ \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Learn Aquilia", "status": "in_progress"}'
# → {"id": 1, "title": "Learn Aquilia", "status": "in_progress"}

# List tasks
curl http://localhost:8000/api/tasks/
# → {"tasks": [{"id": 1, "title": "Learn Aquilia", "status": "in_progress"}]}

# Get single task
curl http://localhost:8000/api/tasks/1
# → {"id": 1, "title": "Learn Aquilia", "status": "in_progress"}

# Filter by status
curl http://localhost:8000/api/tasks/?status=in_progress
# → {"tasks": [{"id": 1, "title": "Learn Aquilia", "status": "in_progress"}]}`}
          language="bash"
        />
      </section>

      {/* Step 7: Add a model */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">7</span>
          Add a Database Model (Optional)
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Replace the in-memory service with a proper ORM model:
        </p>

        <CodeBlock
          code={`# modules/core/models.py
from aquilia.models import Model, CharField, IntegerField, BooleanField, DateTimeField

class Task(Model):
    title = CharField(max_length=200)
    status = CharField(max_length=50, default="pending")
    priority = IntegerField(default=0)
    completed = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        table_name = "tasks"
        ordering = ["-created_at"]`}
          language="python"
        />

        <p className={`mt-4 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Then run migrations:
        </p>

        <CodeBlock
          code={`# Generate migration
aq migrate makemigrations

# Apply migration
aq migrate apply`}
          language="bash"
        />
      </section>

      {/* Step 8: Write tests */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="w-8 h-8 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">8</span>
          Write Tests
        </h2>

        <CodeBlock
          code={`# tests/test_tasks.py
from aquilia.testing import AquiliaTestCase, TestClient

class TestTasks(AquiliaTestCase):
    async def test_create_task(self):
        client = TestClient(self.app)
        response = await client.post("/api/tasks/", json={
            "title": "Test Task",
            "status": "pending",
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Test Task")

    async def test_list_tasks(self):
        client = TestClient(self.app)
        response = await client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("tasks", response.json())`}
          language="python"
        />

        <CodeBlock
          code={`# Run tests
aq test

# Or with pytest
pytest tests/`}
          language="bash"
        />
      </section>

      {/* Next Steps */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Rocket className="w-5 h-5 text-aquilia-400" />
          Next Steps
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { to: '/docs/controllers/overview', title: 'Controllers in Depth', desc: 'Lifecycle hooks, pipelines, OpenAPI generation' },
            { to: '/docs/di/container', title: 'Dependency Injection', desc: 'Scopes, providers, and the Container API' },
            { to: '/docs/models/defining', title: 'ORM & Models', desc: 'Define models, run queries, manage migrations' },
            { to: '/docs/auth/identity', title: 'Authentication', desc: 'JWT tokens, sessions, RBAC, guards' },
            { to: '/docs/config/workspace', title: 'Configuration', desc: 'Workspace, Module, and Integration builders' },
            { to: '/docs/cli/commands', title: 'CLI Reference', desc: 'All aq commands and their options' },
          ].map((link, i) => (
            <Link
              key={i}
              to={link.to}
              className={`p-4 rounded-xl border transition-all hover:scale-[1.01] ${isDark ? 'bg-zinc-900/50 border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-300'}`}
            >
              <div className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{link.title}</div>
              <div className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{link.desc}</div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
