import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Tag, Layers, Zap, Code, ArrowRight, AlertCircle, Filter, List } from 'lucide-react'

export function ControllersDecorators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Tag className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Route Decorators
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.decorators — HTTP method decorators</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Route decorators attach metadata to controller methods without import-time side effects.
          The metadata is later extracted by the <code>ControllerCompiler</code> to generate
          compiled routes, URL patterns, and OpenAPI specs.
        </p>
      </div>

      {/* RouteDecorator base class */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          RouteDecorator Base
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          All HTTP method decorators (<code>GET</code>, <code>POST</code>, etc.) inherit from
          <code>RouteDecorator</code>. The base class accepts the full set of parameters and stores
          them as a dict on <code>func.__route_metadata__</code>:
        </p>

        <CodeBlock
          code={`class RouteDecorator:
    def __init__(
        self,
        path: Optional[str] = None,
        *,
        # ── Pipeline & Middleware ─────────────────────────────────
        pipeline: Optional[List[Any]] = None,

        # ── OpenAPI Documentation ─────────────────────────────────
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: bool = False,
        response_model: Optional[type] = None,
        status_code: int = 200,

        # ── Request / Response Serialization ──────────────────────
        request_serializer: Optional[type] = None,
        response_serializer: Optional[type] = None,

        # ── Blueprint Casting / Sealing ───────────────────────────
        request_blueprint: Optional[type] = None,
        response_blueprint: Optional[type] = None,

        # ── Filtering, Search, Ordering ───────────────────────────
        filterset_class: Optional[type] = None,
        filterset_fields: Optional[Union[List[str], Any]] = None,
        search_fields: Optional[List[str]] = None,
        ordering_fields: Optional[List[str]] = None,

        # ── Pagination ────────────────────────────────────────────
        pagination_class: Optional[type] = None,

        # ── Content Negotiation ───────────────────────────────────
        renderer_classes: Optional[List[Any]] = None,
    ): ...`}
          language="python"
        />
      </section>

      {/* Full parameter reference */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Parameter Reference
        </h2>

        <div className={`rounded-xl border overflow-x-auto ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['path', 'Optional[str]', 'URL path template. Supports «name:type» params. If None, derived from method name.'],
                ['pipeline', 'Optional[List[Any]]', 'Method-level FlowNode pipeline (guards, transforms). Merges with class-level pipeline.'],
                ['summary', 'Optional[str]', 'OpenAPI operation summary. Defaults to method name titlecased.'],
                ['description', 'Optional[str]', 'OpenAPI operation description. Defaults to docstring.'],
                ['tags', 'Optional[List[str]]', 'OpenAPI tags. Extends (does not replace) class-level tags.'],
                ['deprecated', 'bool', 'Mark route as deprecated in OpenAPI spec. Default: False.'],
                ['response_model', 'Optional[type]', 'Response type for OpenAPI schema generation ($ref).'],
                ['status_code', 'int', 'Default HTTP status code. Default: 200.'],
                ['request_serializer', 'Optional[type]', 'Serializer subclass for automatic request body parsing and validation.'],
                ['response_serializer', 'Optional[type]', 'Serializer subclass for automatic response serialization.'],
                ['request_blueprint', 'Optional[type]', 'Blueprint subclass (or Blueprint["projection"]) for request body casting and sealing.'],
                ['response_blueprint', 'Optional[type]', 'Blueprint subclass (or ProjectedRef) for response molding.'],
                ['filterset_class', 'Optional[type]', 'FilterSet subclass for declarative query-based filtering.'],
                ['filterset_fields', 'Optional[List[str] | Any]', 'List of field names for exact-match shorthand, or dict mapping fields to lookup lists.'],
                ['search_fields', 'Optional[List[str]]', 'Field names for text search via ?search=<term>.'],
                ['ordering_fields', 'Optional[List[str]]', 'Field names allowed for dynamic ordering via ?ordering=<field>.'],
                ['pagination_class', 'Optional[type]', 'Pagination backend: PageNumberPagination, LimitOffsetPagination, or CursorPagination.'],
                ['renderer_classes', 'Optional[List[Any]]', 'Renderer instances/classes for Accept-based content negotiation.'],
              ].map(([param, type_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs whitespace-nowrap ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{param}</td>
                  <td className={`px-4 py-2 font-mono text-xs whitespace-nowrap ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type_}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* HTTP Method Decorators */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          HTTP Method Decorators
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Each HTTP method has a dedicated decorator class that sets <code>self.method</code>
          to the corresponding verb. All accept the same keyword arguments as <code>RouteDecorator</code>:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Decorator</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>HTTP Method</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Typical Use</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['@GET(path)', 'GET', 'Retrieve resources, list endpoints'],
                ['@POST(path)', 'POST', 'Create resources, submit data'],
                ['@PUT(path)', 'PUT', 'Full resource replacement'],
                ['@PATCH(path)', 'PATCH', 'Partial resource update'],
                ['@DELETE(path)', 'DELETE', 'Remove resources'],
                ['@HEAD(path)', 'HEAD', 'Check resource existence (no body)'],
                ['@OPTIONS(path)', 'OPTIONS', 'CORS preflight, capability check'],
                ['@WS(path)', 'WS', 'WebSocket upgrade and bidirectional messaging'],
              ].map(([dec, method, use], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{dec}</td>
                  <td className={`px-4 py-2 font-mono text-xs font-bold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{method}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Usage examples */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Usage Examples
        </h2>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic CRUD</h3>

        <CodeBlock
          code={`from aquilia import Controller, GET, POST, PUT, PATCH, DELETE, RequestCtx, Response

class ArticlesController(Controller):
    prefix = "/api/articles"
    tags = ["Articles"]

    @GET("/")
    async def list(self, ctx: RequestCtx) -> Response:
        """List all articles."""
        return Response.json({"articles": []})

    @GET("/«id:int»")
    async def detail(self, ctx: RequestCtx, id: int) -> Response:
        """Get article by ID."""
        return Response.json({"id": id})

    @POST("/", status_code=201)
    async def create(self, ctx: RequestCtx) -> Response:
        """Create a new article."""
        data = await ctx.json()
        return Response.json(data, status=201)

    @PUT("/«id:int»")
    async def replace(self, ctx: RequestCtx, id: int) -> Response:
        """Full replacement of an article."""
        data = await ctx.json()
        return Response.json({"id": id, **data})

    @PATCH("/«id:int»")
    async def update(self, ctx: RequestCtx, id: int) -> Response:
        """Partial update of an article."""
        data = await ctx.json()
        return Response.json({"id": id, **data})

    @DELETE("/«id:int»", status_code=204)
    async def delete(self, ctx: RequestCtx, id: int) -> Response:
        """Delete an article."""
        return Response("", status=204)`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>With Serializers and Blueprints</h3>

        <CodeBlock
          code={`from aquilia import Controller, GET, POST, PUT, RequestCtx, Response
from aquilia.serializers import Serializer, StringField, IntField

class ArticleSerializer(Serializer):
    title = StringField(required=True, max_length=200)
    body = StringField(required=True)
    category_id = IntField(required=True)

class ArticlesController(Controller):
    prefix = "/api/articles"

    @POST(
        "/",
        status_code=201,
        request_serializer=ArticleSerializer,   # Auto-validates request body
        response_model=ArticleSerializer,        # OpenAPI response schema
    )
    async def create(self, ctx: RequestCtx) -> Response:
        # Body has already been validated by ArticleSerializer
        data = await ctx.json()
        article = await self.repo.create(data)
        return Response.json(article, status=201)

    @PUT(
        "/«id:int»",
        request_serializer=ArticleSerializer,
        response_serializer=ArticleSerializer,  # Auto-serializes response
    )
    async def update(self, ctx: RequestCtx, id: int) -> Response:
        data = await ctx.json()
        article = await self.repo.update(id, data)
        return article  # Auto-serialized by response_serializer`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>With Filtering and Pagination</h3>

        <CodeBlock
          code={`from aquilia import Controller, GET, RequestCtx, Response
from aquilia.controller.pagination import PageNumberPagination

class ProductsPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100

class ProductsController(Controller):
    prefix = "/api/products"

    @GET(
        "/",
        filterset_fields=["category", "brand", "in_stock"],
        search_fields=["name", "description"],
        ordering_fields=["price", "created_at", "name"],
        pagination_class=ProductsPagination,
    )
    async def list(self, ctx: RequestCtx) -> Response:
        """
        List products with filtering, search, and pagination.

        Query params:
          ?category=electronics     — exact match filter
          ?search=laptop            — text search in name/description
          ?ordering=-price          — sort by price descending
          ?page=2&page_size=20      — pagination
        """
        products = await self.repo.list_all()
        # Filtering, ordering, and pagination are applied
        # automatically by the engine before the response is sent.
        return products`}
          language="python"
        />
      </section>

      {/* Generic route() */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <List className="w-5 h-5 text-aquilia-400" />
          Generic route() Function
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          For multi-method routes or dynamic method binding, use the <code>route()</code>
          function instead of individual decorators:
        </p>

        <CodeBlock
          code={`from aquilia.controller.decorators import route

class ItemsController(Controller):
    prefix = "/items"

    @route("GET", "/")
    async def list_items(self, ctx: RequestCtx) -> Response:
        return Response.json({"items": []})

    @route(["GET", "POST"], "/bulk")
    async def bulk(self, ctx: RequestCtx) -> Response:
        """Handles both GET and POST on /items/bulk."""
        if ctx.method == "GET":
            return Response.json({"items": []})
        data = await ctx.json()
        return Response.json({"created": len(data)}, status=201)

    @route("PUT", "/«id:int»", tags=["Admin"], deprecated=True)
    async def legacy_update(self, ctx: RequestCtx, id: int) -> Response:
        return Response.json({"id": id})`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When a list of methods is provided, <code>route()</code> applies the corresponding
          decorator class for each method. This means the handler gets multiple entries in
          <code>__route_metadata__</code>, one per method.
        </p>
      </section>

      {/* Metadata internals */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          How Metadata Works
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When a decorator like <code>@GET("/users")</code> is applied, it doesn't execute
          any routing logic. Instead, it attaches a metadata dict to the function:
        </p>

        <CodeBlock
          code={`# What happens when you write:
@GET("/«id:int»", tags=["Users"], deprecated=True)
async def get_user(self, ctx, id: int): ...

# The decorator creates:
get_user.__route_metadata__ = [
    {
        "http_method": "GET",
        "path": "/«id:int»",
        "pipeline": [],
        "summary": "Get User",          # auto-generated from method name
        "description": "...",            # from docstring
        "tags": ["Users"],
        "deprecated": True,
        "response_model": None,
        "status_code": 200,
        "func_name": "get_user",
        "signature": <inspect.Signature>,
        "request_serializer": None,
        "response_serializer": None,
        "request_blueprint": None,
        "response_blueprint": None,
        "filterset_class": None,
        "filterset_fields": None,
        "search_fields": None,
        "ordering_fields": None,
        "pagination_class": None,
        "renderer_classes": None,
    }
]`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>__route_metadata__</code> list supports multiple entries — this is how
          a single method can handle multiple HTTP methods via <code>route()</code>.
          The <code>ControllerCompiler</code> iterates this list during <code>aq compile</code>
          to generate <code>CompiledRoute</code> objects.
        </p>
      </section>

      {/* Path parameter syntax */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Filter className="w-5 h-5 text-aquilia-400" />
          Path Parameter Syntax
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia uses the <code>«name:type»</code> chevron syntax for path parameters,
          compiled by the <code>aquilia.patterns</code> system:
        </p>

        <CodeBlock
          code={`# Typed path parameters
@GET("/users/«id:int»")        # Matches /users/42, not /users/abc
@GET("/price/«amount:float»")  # Matches /price/19.99
@GET("/posts/«slug:str»")      # Matches /posts/my-first-post
@GET("/active/«flag:bool»")    # Matches /active/true or /active/false

# Multiple parameters
@GET("/users/«user_id:int»/posts/«post_id:int»")

# Curly-brace syntax is also supported (auto-converted)
@GET("/users/{id}")             # Treated as «id:str» by default
@GET("/users/{id:int}")         # Explicit type

# Path derived from method name (when path is None)
@GET()
async def list_users(self, ctx): ...  # Matches /list_users`}
          language="python"
        />
      </section>

      {/* WebSocket */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          WebSocket Decorator
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>@WS</code> decorator marks a method as a WebSocket handler. The handler
          receives a WebSocket connection instead of returning an HTTP response:
        </p>

        <CodeBlock
          code={`from aquilia import Controller, WS, RequestCtx

class ChatController(Controller):
    prefix = "/ws"

    @WS("/chat/«room:str»")
    async def chat(self, ctx: RequestCtx, room: str) -> None:
        ws = ctx.request.websocket
        await ws.accept()

        try:
            while True:
                data = await ws.receive_json()
                await ws.send_json({
                    "room": room,
                    "message": data.get("message"),
                    "user": str(ctx.identity.id) if ctx.identity else "anon",
                })
        except Exception:
            await ws.close()`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/overview" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← Controller Overview
          </Link>
          <Link to="/docs/controllers/request-ctx" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            RequestCtx →
          </Link>
        </div>
      </section>
    </div>
  )
}
