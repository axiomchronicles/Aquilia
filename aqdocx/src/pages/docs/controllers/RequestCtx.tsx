import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Zap } from 'lucide-react'

export function ControllersRequestCtx() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Zap className="w-4 h-4" />
          Controllers
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          RequestCtx
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">RequestCtx</code> is a dataclass that wraps the request, identity, session, DI container, and arbitrary state into a single context object passed to every controller handler.
        </p>
      </div>

      {/* Definition */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Class Definition</h2>
        <CodeBlock language="python" filename="aquilia/controller/base.py">{`@dataclass
class RequestCtx:
    """
    Request context provided to controller methods.

    Provides unified access to request state, identity, session,
    and DI container.
    """
    request: Request            # The HTTP request object
    identity: Optional[Identity] = None  # Authenticated user (if auth successful)
    session: Optional[Session] = None    # Active session (if sessions enabled)
    container: Optional[Any] = None      # Request-scoped DI container
    state: Dict[str, Any] = field(default_factory=dict)  # Arbitrary state`}</CodeBlock>
      </section>

      {/* Properties */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Properties & Methods</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Member</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'ctx.request', r: 'Request', d: 'The full Aquilia Request object with headers, body, cookies, etc.' },
                { m: 'ctx.identity', r: 'Identity | None', d: 'The authenticated identity if auth middleware ran successfully.' },
                { m: 'ctx.session', r: 'Session | None', d: 'The active session object if sessions middleware is enabled.' },
                { m: 'ctx.container', r: 'Container | None', d: 'The request-scoped DI container for resolving dependencies.' },
                { m: 'ctx.state', r: 'Dict[str, Any]', d: 'Arbitrary state dictionary for passing data between middleware and handlers.' },
                { m: 'ctx.path', r: 'str', d: 'Shortcut for ctx.request.path.' },
                { m: 'ctx.method', r: 'str', d: 'Shortcut for ctx.request.method (GET, POST, etc.).' },
                { m: 'ctx.headers', r: 'Dict[str, str]', d: 'Shortcut for ctx.request.headers.' },
                { m: 'ctx.query_params', r: 'Dict[str, list]', d: 'Parsed query string parameters.' },
                { m: 'ctx.query_param(key, default)', r: 'str | None', d: 'Get a single query parameter by key.' },
                { m: 'await ctx.json()', r: 'Any', d: 'Parse request body as JSON.' },
                { m: 'await ctx.form()', r: 'Dict[str, Any]', d: 'Parse request body as form data.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.r}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Usage Examples */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage Examples</h2>

        <h3 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Reading Query Parameters</h3>
        <CodeBlock language="python" filename="Query Parameters">{`@Get("/search")
async def search(self, ctx):
    query = ctx.query_param("q", default="")
    page = int(ctx.query_param("page", default="1"))
    per_page = int(ctx.query_param("per_page", default="20"))

    results = await self.service.search(query, page, per_page)
    return ctx.json({
        "results": [r.to_dict() for r in results],
        "page": page,
        "per_page": per_page,
    })`}</CodeBlock>

        <h3 className={`text-lg font-bold mb-4 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Accessing the Authenticated Identity</h3>
        <CodeBlock language="python" filename="Identity Access">{`@Get("/profile")
async def profile(self, ctx):
    if not ctx.identity:
        return ctx.json({"error": "Unauthorized"}, status=401)

    user = await self.users.get(ctx.identity.id)
    return ctx.json({
        "user": user.to_dict(),
        "roles": ctx.identity.roles,
        "claims": ctx.identity.claims,
    })`}</CodeBlock>

        <h3 className={`text-lg font-bold mb-4 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Working with Sessions</h3>
        <CodeBlock language="python" filename="Session Access">{`@Post("/cart/add")
async def add_to_cart(self, ctx):
    body = await ctx.json()
    product_id = body["product_id"]

    # Read/write session data
    cart = ctx.session.get("cart", [])
    cart.append(product_id)
    ctx.session["cart"] = cart

    return ctx.json({"cart_count": len(cart)})`}</CodeBlock>

        <h3 className={`text-lg font-bold mb-4 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using the DI Container at Runtime</h3>
        <CodeBlock language="python" filename="Runtime DI">{`@Get("/notifications")
async def notifications(self, ctx):
    # Resolve a service from the request-scoped container
    notif_service = await ctx.container.resolve(NotificationService)
    notifications = await notif_service.get_for_user(ctx.identity.id)
    return ctx.json({"notifications": notifications})`}</CodeBlock>

        <h3 className={`text-lg font-bold mb-4 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Accessing Raw Request Features</h3>
        <CodeBlock language="python" filename="Raw Request">{`@Post("/upload")
async def upload(self, ctx):
    # Access multipart form data via the request object
    form = await ctx.request.multipart()
    file = form.get("file")

    if not file:
        return ctx.json({"error": "No file provided"}, status=400)

    content = await file.read()
    filename = file.filename

    await self.storage.save(filename, content)
    return ctx.json({"filename": filename, "size": len(content)})`}</CodeBlock>
      </section>

      {/* State */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>The state Dictionary</h2>
        <div className={boxClass}>
          <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            The <code className="text-aquilia-500">ctx.state</code> dictionary is a general-purpose bag for passing data between middleware and handlers. Middleware can attach data to state before the handler runs:
          </p>
          <CodeBlock language="python" filename="Middleware → Handler State">{`# In middleware
class TimingMiddleware:
    async def __call__(self, scope, receive, send):
        import time
        start = time.time()
        # ... forward to next middleware/handler
        scope["state"]["request_start"] = start

# In controller
@Get("/debug")
async def debug(self, ctx):
    start = ctx.state.get("request_start")
    return ctx.json({"timing": time.time() - start})`}</CodeBlock>
        </div>
      </section>
    </div>
  )
}
