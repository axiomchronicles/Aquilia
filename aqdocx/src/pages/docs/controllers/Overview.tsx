import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, Layers, Zap, Shield, FileCode, Settings } from 'lucide-react'

export function ControllersOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Core / Controllers
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Controllers
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Controllers are class-based request handlers that map HTTP methods to Python methods using decorators. They support constructor dependency injection, pipelines, lifecycle hooks, template rendering, and OpenAPI generation.
        </p>
      </div>

      {/* Controller class */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>The Controller Base Class</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every controller extends the <code className="text-aquilia-500">Controller</code> base class from <code className="text-aquilia-500">aquilia</code>. The base class provides:
        </p>
        <ul className={`space-y-2 mb-6 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>prefix</strong> — URL prefix for all routes in this controller</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>pipeline</strong> — Class-level pipeline nodes applied to all methods</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>tags</strong> — OpenAPI tags for documentation</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>instantiation_mode</strong> — <code>"per_request"</code> (default) or <code>"singleton"</code></li>
        </ul>

        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Post, Put, Delete, Inject


class UserController(Controller):
    """Handles all user-related HTTP endpoints."""

    prefix = "/api/users"
    tags = ["Users"]
    pipeline = []  # Optional: class-level middleware
    instantiation_mode = "per_request"  # New instance per request

    @Inject()
    def __init__(self, user_service: UserService, auth: AuthService):
        self.user_service = user_service
        self.auth = auth

    @Get("/")
    async def list_users(self, ctx):
        """List all users."""
        users = await self.user_service.list_all()
        return ctx.json({"users": [u.to_dict() for u in users]})

    @Get("/{user_id:int}")
    async def get_user(self, ctx, user_id: int):
        """Get a single user by ID."""
        user = await self.user_service.get(user_id)
        return ctx.json({"user": user.to_dict()})

    @Post("/")
    async def create_user(self, ctx):
        """Create a new user."""
        body = await ctx.json()
        user = await self.user_service.create(body)
        return ctx.json({"user": user.to_dict()}, status=201)

    @Put("/{user_id:int}")
    async def update_user(self, ctx, user_id: int):
        """Update a user."""
        body = await ctx.json()
        user = await self.user_service.update(user_id, body)
        return ctx.json({"user": user.to_dict()})

    @Delete("/{user_id:int}")
    async def delete_user(self, ctx, user_id: int):
        """Delete a user."""
        await self.user_service.delete(user_id)
        return ctx.json({"deleted": True}, status=204)`}</CodeBlock>
      </section>

      {/* Class Attributes Reference */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Class Attributes Reference</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Attribute</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { attr: 'prefix', type: 'str', def: '""', desc: 'URL prefix prepended to all routes (e.g., "/api/users")' },
                { attr: 'pipeline', type: 'List[Any]', def: '[]', desc: 'Pipeline nodes (guards, interceptors) applied to all methods' },
                { attr: 'tags', type: 'List[str]', def: '[]', desc: 'OpenAPI tags for grouping endpoints in documentation' },
                { attr: 'instantiation_mode', type: 'str', def: '"per_request"', desc: '"per_request" creates a new instance per request; "singleton" reuses one instance' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.attr}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.type}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.def}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Lifecycle Hooks */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Hooks</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Controllers can override lifecycle hooks to perform setup/teardown or per-request logic:
        </p>
        <div className="space-y-4 mb-6">
          {[
            { name: 'on_startup(ctx)', desc: 'Called once at app startup. Only for singleton controllers. Use for initializing connections, caches, etc.' },
            { name: 'on_shutdown(ctx)', desc: 'Called once at app shutdown. Only for singleton controllers. Use for cleanup.' },
            { name: 'on_request(ctx)', desc: 'Called before every request. Use for per-request validation, logging, or setup.' },
            { name: 'on_response(ctx, response)', desc: 'Called after every request. Can modify the response before it is sent.' },
          ].map((hook, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{hook.name}</code>
              <p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{hook.desc}</p>
            </div>
          ))}
        </div>
        <CodeBlock language="python" filename="Example: Lifecycle Hooks">{`class MetricsController(Controller):
    prefix = "/api/metrics"
    instantiation_mode = "singleton"

    @Inject()
    def __init__(self, metrics: MetricsService):
        self.metrics = metrics

    async def on_startup(self, ctx):
        """Initialize metrics collectors on app start."""
        await self.metrics.init_collectors()
        print("MetricsController ready")

    async def on_shutdown(self, ctx):
        """Flush remaining metrics on shutdown."""
        await self.metrics.flush()

    async def on_request(self, ctx):
        """Log every incoming request."""
        self.metrics.increment("requests_total")

    async def on_response(self, ctx, response):
        """Add timing header to every response."""
        response.headers["X-Response-Time"] = str(self.metrics.elapsed())
        return response

    @Get("/health")
    async def health(self, ctx):
        return ctx.json({"status": "ok"})`}</CodeBlock>
      </section>

      {/* Template Rendering */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template Rendering</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Controllers have a built-in <code className="text-aquilia-500">render()</code> method for returning HTML responses using Jinja2 templates:
        </p>
        <CodeBlock language="python" filename="Template Controller">{`class PageController(Controller):
    prefix = ""

    @Inject()
    def __init__(self, templates: TemplateEngine, products: ProductService):
        self.templates = templates
        self.products = products

    @Get("/")
    async def home(self, ctx):
        """Render the home page."""
        products = await self.products.featured()
        return await self.render("home.html", {
            "title": "Welcome",
            "products": products,
        }, ctx)

    @Get("/about")
    async def about(self, ctx):
        return await self.render("about.html", {"title": "About Us"}, ctx)`}</CodeBlock>
        <p className={`mt-4 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
          The <code className="text-aquilia-500">render()</code> method automatically injects the request, session, and identity into the template context.
        </p>
      </section>

      {/* Architecture Diagram */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Controller Architecture</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 700 300" className="w-full" fill="none">
            <defs>
              <marker id="ctrl-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0,8 3,0 6" className="fill-aquilia-500/50" />
              </marker>
            </defs>
            {/* Compiler */}
            <rect x="20" y="20" width="180" height="50" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5">
              <animate attributeName="stroke-opacity" values="0.3;0.7;0.3" dur="3s" repeatCount="indefinite" />
            </rect>
            <text x="110" y="50" textAnchor="middle" className="fill-aquilia-500 text-xs font-bold">ControllerCompiler</text>

            <line x1="200" y1="45" x2="240" y2="45" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#ctrl-arrow)" />

            {/* Router */}
            <rect x="245" y="20" width="180" height="50" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
            <text x="335" y="50" textAnchor="middle" className="fill-aquilia-500 text-xs font-bold">ControllerRouter</text>

            <line x1="425" y1="45" x2="465" y2="45" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#ctrl-arrow)" />

            {/* Engine */}
            <rect x="470" y="20" width="180" height="50" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
            <text x="560" y="50" textAnchor="middle" className="fill-aquilia-500 text-xs font-bold">ControllerEngine</text>

            {/* Factory */}
            <line x1="560" y1="70" x2="560" y2="110" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#ctrl-arrow)" />
            <rect x="470" y="115" width="180" height="50" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="560" y="145" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>ControllerFactory</text>

            {/* Controller Instance */}
            <line x1="560" y1="165" x2="560" y2="205" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#ctrl-arrow)" />
            <rect x="420" y="210" width="280" height="70" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="560" y="240" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>Controller Instance</text>
            <text x="560" y="260" textAnchor="middle" className={`text-[9px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}>@Get, @Post, @Put, @Delete handlers</text>

            {/* RequestCtx */}
            <rect x="20" y="120" width="160" height="50" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="100" y="150" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>RequestCtx</text>

            <line x1="180" y1="145" x2="465" y2="240" stroke="#22c55e" strokeOpacity="0.2" strokeWidth="1" strokeDasharray="4 4" markerEnd="url(#ctrl-arrow)" />

            {/* DI Container */}
            <rect x="20" y="210" width="160" height="50" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="100" y="240" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>DI Container</text>

            <line x1="180" y1="235" x2="465" y2="235" stroke="#22c55e" strokeOpacity="0.2" strokeWidth="1" strokeDasharray="4 4" markerEnd="url(#ctrl-arrow)" />

            {/* Annotations */}
            <text x="210" y="125" className={`text-[9px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>compile-time</text>
            <text x="465" y="95" className={`text-[9px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>runtime</text>
          </svg>
        </div>
      </section>

      {/* Sub-Pages */}
      <section>
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Deep Dives</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { icon: <FileCode />, title: 'Decorators', desc: 'GET, POST, PUT, DELETE, WS and route metadata', to: '/docs/controllers/decorators' },
            { icon: <Zap />, title: 'RequestCtx', desc: 'The context object passed to every handler', to: '/docs/controllers/request-ctx' },
            { icon: <Settings />, title: 'Factory', desc: 'How controllers are instantiated and managed', to: '/docs/controllers/factory' },
            { icon: <Shield />, title: 'Engine', desc: 'Runtime dispatch and route matching', to: '/docs/controllers/engine' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <div className="text-aquilia-500 mb-2 w-5 h-5">{item.icon}</div>
              <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {item.title}
                <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" />
              </h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
