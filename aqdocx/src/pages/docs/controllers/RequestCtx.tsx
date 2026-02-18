import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Box, Layers, Zap, Code, Database, Shield, ArrowRight } from 'lucide-react'

export function ControllersRequestCtx() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Box className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>RequestCtx</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.base.RequestCtx — Request context object</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>RequestCtx</code> is the request context object passed to every controller method.
          It wraps the low-level <code>Request</code> object and provides access to the current
          user identity, session, DI container, and a mutable <code>state</code> dict
          for middleware-to-handler communication.
        </p>
      </div>

      {/* Class definition */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          Class Definition
        </h2>

        <CodeBlock
          code={`class RequestCtx:
    """
    Request context provided to controller methods.

    Uses manual __init__ instead of @dataclass for faster construction.
    No __slots__ to allow dynamic attribute setting by middleware/plugins.
    """

    def __init__(
        self,
        request: "Request",
        identity: Optional["Identity"] = None,
        session: Optional["Session"] = None,
        container: Optional[Any] = None,
        state: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self.request = request
        self.identity = identity
        self.session = session
        self.container = container
        self.state = state if state is not None else {}
        self.request_id = request_id`}
          language="python"
        />

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Design note:</strong> <code>RequestCtx</code> deliberately does <em>not</em> use
            <code>__slots__</code>. This allows middleware and plugins to attach arbitrary
            attributes (e.g., <code>ctx.tenant</code>, <code>ctx.locale</code>) without
            modifying the class.
          </p>
        </div>
      </section>

      {/* Constructor parameters */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Constructor Parameters
        </h2>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['request', 'Request', '(required)', 'The low-level ASGI Request object. Always present.'],
                ['identity', 'Optional[Identity]', 'None', 'The authenticated user identity, set by auth middleware.'],
                ['session', 'Optional[Session]', 'None', 'The session object, set by session middleware.'],
                ['container', 'Optional[Any]', 'None', 'The request-scoped DI container for resolving dependencies.'],
                ['state', 'Optional[Dict[str, Any]]', '{}', 'Mutable dict for middleware-to-handler communication.'],
                ['request_id', 'Optional[str]', 'None', 'Unique request ID (set by RequestIdMiddleware).'],
              ].map(([param, type_, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{param}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type_}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{def_}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Properties */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Properties
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Convenience properties that delegate to <code>self.request</code>:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Property</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['ctx.path', 'str', 'Request URL path (e.g., "/api/users/42")'],
                ['ctx.method', 'str', 'HTTP method (e.g., "GET", "POST")'],
                ['ctx.headers', 'Dict[str, str]', 'Request headers as a dictionary'],
                ['ctx.query_params', 'Dict[str, list]', 'Parsed query parameters (multi-valued)'],
              ].map(([prop, ret, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{prop}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{ret}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Methods */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 text-aquilia-400" />
          Methods
        </h2>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          query_param(key, default=None)
        </h3>
        <p className={`mb-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Get a single query parameter value. Returns the first value if the key exists,
          otherwise returns <code>default</code>.
        </p>
        <CodeBlock
          code={`@GET("/search")
async def search(self, ctx: RequestCtx) -> Response:
    query = ctx.query_param("q", "")
    page = int(ctx.query_param("page", "1"))
    return Response.json({"query": query, "page": page})`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          async json() → Any
        </h3>
        <p className={`mb-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Parse the request body as JSON. Delegates to <code>self.request.json()</code>.
          Raises an exception if the body is not valid JSON.
        </p>
        <CodeBlock
          code={`@POST("/")
async def create(self, ctx: RequestCtx) -> Response:
    body = await ctx.json()
    # body is a dict/list parsed from JSON
    return Response.json({"received": body})`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          async form() → Dict[str, Any]
        </h3>
        <p className={`mb-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Parse the request body as form data (<code>application/x-www-form-urlencoded</code> or
          <code>multipart/form-data</code>). Delegates to <code>self.request.form()</code>.
        </p>
        <CodeBlock
          code={`@POST("/upload")
async def upload(self, ctx: RequestCtx) -> Response:
    form_data = await ctx.form()
    filename = form_data.get("file", {}).get("filename", "unknown")
    return Response.json({"uploaded": filename})`}
          language="python"
        />
      </section>

      {/* State dict */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          The state Dict
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>ctx.state</code> is a mutable dictionary shared between middleware and handlers.
          Middleware can write values into it, and controllers can read them:
        </p>

        <CodeBlock
          code={`# In middleware:
async def tenant_middleware(request, ctx, next_handler):
    tenant_id = request.headers.get("X-Tenant-ID")
    ctx.state["tenant_id"] = tenant_id
    return await next_handler(request, ctx)

# In controller:
@GET("/data")
async def get_data(self, ctx: RequestCtx) -> Response:
    tenant_id = ctx.state.get("tenant_id")
    # Or access request.state directly:
    request_id = ctx.request.state.get("request_id")
    return Response.json({"tenant": tenant_id})`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Common state keys set by built-in middleware:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Key</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Set By</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['identity', 'AuthenticationMiddleware', 'Identity'],
                ['session', 'SessionMiddleware', 'Session'],
                ['request_id', 'RequestIdMiddleware', 'str (UUID)'],
                ['timing_start', 'TimingMiddleware', 'float (timestamp)'],
              ].map(([key, middleware, type_], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{key}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{middleware}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type_}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Dynamic attributes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Dynamic Attributes
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Since <code>RequestCtx</code> has no <code>__slots__</code>, middleware can attach
          arbitrary attributes directly:
        </p>

        <CodeBlock
          code={`# Middleware sets a custom attribute
async def locale_middleware(request, ctx, next_handler):
    ctx.locale = request.headers.get("Accept-Language", "en-US")
    ctx.timezone = "UTC"
    return await next_handler(request, ctx)

# Controller reads it
@GET("/greeting")
async def greeting(self, ctx: RequestCtx) -> Response:
    locale = getattr(ctx, "locale", "en-US")
    return Response.json({"locale": locale})`}
          language="python"
        />
      </section>

      {/* How ctx is built */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>How RequestCtx Is Built</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ControllerEngine.execute()</code> method builds <code>RequestCtx</code> inline
          during request processing:
        </p>

        <CodeBlock
          code={`# Inside ControllerEngine.execute():
ctx = RequestCtx(
    request=request,
    identity=request.state.get("identity"),  # Set by AuthMiddleware
    session=request.state.get("session"),     # Set by SessionMiddleware
    container=container,                      # Request-scoped DI container
    state=request.state,                      # Shared mutable dict
)

# The engine then passes ctx to:
# 1. Pipeline nodes (guards, transforms)
# 2. Controller lifecycle hooks (on_request)
# 3. The handler method itself
# 4. Controller on_response hook`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/decorators" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← Route Decorators
          </Link>
          <Link to="/docs/controllers/factory" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ControllerFactory →
          </Link>
        </div>
      </section>
    </div>
  )
}
