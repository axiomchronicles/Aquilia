import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Layout, Zap, Shield, Layers, Plug, Settings, ArrowRight, AlertCircle } from 'lucide-react'

export function ControllersOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Layout className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Controllers</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller — Class-based request handlers</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Controllers are the primary request handling abstraction in Aquilia. Unlike function-based
          route handlers, Aquilia controllers are <strong>classes</strong> with constructor-based DI injection,
          lifecycle hooks, class-level pipeline configuration, and OpenAPI metadata.
        </p>
      </div>

      {/* Controller class */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 text-aquilia-400" />
          The Controller Base Class
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          All controllers extend <code>aquilia.controller.Controller</code>. The base class provides:
        </p>

        <CodeBlock
          code={`from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response

class ProductsController(Controller):
    # ── Class-level configuration ─────────────────────────────
    prefix = "/api/products"           # URL prefix for all routes
    pipeline = []                       # Pipeline nodes (guards, transforms)
    tags = ["Products"]                 # OpenAPI tags
    instantiation_mode = "per_request"  # "per_request" or "singleton"

    # ── Constructor DI injection ──────────────────────────────
    def __init__(self, product_repo: ProductRepository, cache: CacheService):
        """Dependencies are injected by the DI container."""
        self.repo = product_repo
        self.cache = cache

    # ── Lifecycle hooks ───────────────────────────────────────
    async def on_startup(self, ctx: RequestCtx) -> None:
        """Called at server startup (singleton mode only)."""
        pass

    async def on_shutdown(self, ctx: RequestCtx) -> None:
        """Called at server shutdown (singleton mode only)."""
        pass

    async def on_request(self, ctx: RequestCtx) -> None:
        """Called before each request (both modes)."""
        pass

    async def on_response(self, ctx: RequestCtx, response: Response) -> Response:
        """Called after each request (both modes). Can modify the response."""
        return response

    # ── Route handlers ────────────────────────────────────────
    @GET("/")
    async def list_products(self, ctx: RequestCtx) -> Response:
        products = await self.repo.list_all()
        return Response.json({"products": products})

    @GET("/«id:int»")
    async def get_product(self, ctx: RequestCtx, id: int) -> Response:
        product = await self.repo.get(id)
        return Response.json(product)

    @POST("/")
    async def create_product(self, ctx: RequestCtx) -> Response:
        data = await ctx.json()
        product = await self.repo.create(data)
        return Response.json(product, status=201)

    @PUT("/«id:int»")
    async def update_product(self, ctx: RequestCtx, id: int) -> Response:
        data = await ctx.json()
        product = await self.repo.update(id, data)
        return Response.json(product)

    @DELETE("/«id:int»")
    async def delete_product(self, ctx: RequestCtx, id: int) -> Response:
        await self.repo.delete(id)
        return Response.json({"deleted": True})`}
          language="python"
        />
      </section>

      {/* Class attributes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Class Attributes
        </h2>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Attribute</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['prefix', 'str', '""', 'URL prefix for all routes in this controller (e.g., "/users")'],
                ['pipeline', 'List[FlowNode]', '[]', 'Class-level pipeline nodes applied to all methods'],
                ['tags', 'List[str]', '[]', 'OpenAPI tags for all routes in this controller'],
                ['instantiation_mode', 'str', '"per_request"', '"per_request" (new instance per request) or "singleton" (shared instance)'],
              ].map(([attr, type, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{attr}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{def_}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Template rendering */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Template Rendering
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The base <code>Controller</code> provides a <code>render()</code> convenience method that
          delegates to <code>Response.render()</code> with automatic template engine and context injection:
        </p>

        <CodeBlock
          code={`class PagesController(Controller):
    prefix = "/pages"

    def __init__(self, templates: TemplateEngine):
        self.templates = templates

    @GET("/home")
    async def home(self, ctx: RequestCtx) -> Response:
        # render() auto-injects request/session/identity from ctx
        return await self.render(
            "pages/home.html",
            {"title": "Home", "featured": await self.get_featured()},
            ctx,                    # Passes request context to template
            status=200,             # HTTP status code
            headers={"X-Page": "home"},  # Additional headers
        )`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The template engine is resolved from: (1) the <code>engine</code> parameter,
          (2) <code>self._template_engine</code>, or (3) <code>self.templates</code> (constructor-injected).
        </p>
      </section>

      {/* Instantiation modes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Plug className="w-5 h-5 text-aquilia-400" />
          Instantiation Modes
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>per_request <span className="text-xs font-normal text-gray-500">(default)</span></h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• New instance created for each HTTP request</li>
              <li>• Constructor runs every time (DI injection per request)</li>
              <li>• Instance is garbage-collected after response</li>
              <li>• <code>on_request</code> and <code>on_response</code> hooks work</li>
              <li>• <code>on_startup</code>/<code>on_shutdown</code> are <strong>not called</strong></li>
              <li>• Supports <code>__aenter__</code>/<code>__aexit__</code> context manager</li>
            </ul>
          </div>

          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>singleton</h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• Single instance shared across all requests</li>
              <li>• Constructor runs once at startup</li>
              <li>• Instance lives for the server's lifetime</li>
              <li>• All lifecycle hooks work</li>
              <li>• Use for stateful controllers (connection pools, caches)</li>
              <li>• <strong>Thread safety is your responsibility</strong></li>
            </ul>
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Pipeline System
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Pipelines are chains of <code>FlowNode</code> objects that run before the handler method.
          They can be set at the class level (applies to all routes) or at the method level
          (per-route override via the <code>pipeline</code> decorator parameter):
        </p>

        <CodeBlock
          code={`from aquilia.flow import FlowNode, FlowNodeType

# Guard: blocks requests that don't pass validation
def auth_guard():
    async def guard(request, ctx, next_handler):
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)
        return await next_handler(request, ctx)
    return FlowNode(
        type=FlowNodeType.GUARD,
        callable=guard,
        name="auth_guard",
    )

# Transform: modifies the request/context before the handler
def json_body_parser():
    async def transform(request, ctx, next_handler):
        if request.content_type == "application/json":
            ctx.state["parsed_body"] = await request.json()
        return await next_handler(request, ctx)
    return FlowNode(
        type=FlowNodeType.TRANSFORM,
        callable=transform,
        name="json_parser",
    )


class AdminController(Controller):
    prefix = "/admin"
    pipeline = [auth_guard()]  # Applied to ALL routes

    @GET("/dashboard")
    async def dashboard(self, ctx: RequestCtx) -> Response:
        return Response.json({"admin": True})

    @POST("/settings", pipeline=[json_body_parser()])  # Additional pipeline
    async def update_settings(self, ctx: RequestCtx) -> Response:
        body = ctx.state.get("parsed_body", {})
        return Response.json({"updated": body})`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Pipeline nodes have four types: <code>GUARD</code> (can reject), <code>TRANSFORM</code> (modifies context),
          <code>HANDLER</code> (replaces the handler), and <code>HOOK</code> (side effects). Each node has a
          <code>priority</code> (default: 50) that determines execution order within the same type.
        </p>
      </section>

      {/* Context manager */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Per-Request Lifecycle
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          In <code>per_request</code> mode, the controller supports async context manager protocol.
          The <code>ControllerFactory</code> uses <code>async with controller:</code> to ensure cleanup:
        </p>

        <CodeBlock
          code={`class TransactionalController(Controller):
    prefix = "/orders"

    def __init__(self, db: Database):
        self.db = db
        self.conn = None

    async def __aenter__(self):
        """Acquire a DB connection at request start."""
        self.conn = await self.db.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the connection at request end."""
        if self.conn:
            if exc_type:
                await self.conn.rollback()
            else:
                await self.conn.commit()
            await self.db.release(self.conn)

    @POST("/")
    async def create_order(self, ctx: RequestCtx) -> Response:
        data = await ctx.json()
        # self.conn is guaranteed to be available
        order = await self.conn.execute(
            "INSERT INTO orders ...", data
        )
        return Response.json(order, status=201)`}
          language="python"
        />
      </section>

      {/* Error handling */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Error Handling
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Exceptions thrown in controller methods are caught by the <code>ExceptionMiddleware</code>
          and converted to appropriate HTTP responses. You can also raise specific faults:
        </p>

        <CodeBlock
          code={`from aquilia.faults import Fault, FaultDomain, Severity

@GET("/«id:int»")
async def get_user(self, ctx: RequestCtx, id: int) -> Response:
    user = await self.repo.get(id)
    if not user:
        # Option 1: Return a Response directly
        return Response.json({"error": "Not found"}, status=404)

    # Option 2: Raise a Fault (caught by FaultMiddleware)
    # raise Fault(
    #     domain=FaultDomain.MODEL,
    #     message=f"User {id} not found",
    #     severity=Severity.WARNING,
    #     status=404,
    # )

    return Response.json(user)`}
          language="python"
        />
      </section>

      {/* Next */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>In This Section</h2>
        <div className="flex flex-col gap-2">
          <Link to="/docs/controllers/decorators" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Route Decorators: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, WS and all parameters
          </Link>
          <Link to="/docs/controllers/request-ctx" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → RequestCtx: The request context object and its properties
          </Link>
          <Link to="/docs/controllers/factory" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → ControllerFactory: How controllers are instantiated with DI
          </Link>
          <Link to="/docs/controllers/engine" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → ControllerEngine: Route dispatch and pipeline execution
          </Link>
          <Link to="/docs/controllers/compiler" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → ControllerCompiler: How decorator metadata is compiled into routes
          </Link>
        </div>
      </section>
    </div>
  )
}
