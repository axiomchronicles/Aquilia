import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Shield } from 'lucide-react'

export function SessionsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Security / Sessions
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Sessions
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The session system provides server-side state management with pluggable stores (memory, file), configurable transport (cookie, header), security policies, and DI-integrated decorators for controller handlers.
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <div className="space-y-3">
          {[
            { name: 'SessionEngine', desc: 'Central orchestrator — creates sessions, binds transport and store, manages lifecycle' },
            { name: 'SessionID', desc: 'Cryptographically secure session identifier with entropy validation' },
            { name: 'Session', desc: 'Dict-like object holding per-user state with dirty tracking and flash messages' },
            { name: 'SessionPolicy', desc: 'Security configuration — TTL, rotation, cookie settings, idle timeout' },
            { name: 'MemoryStore / FileStore', desc: 'Pluggable backends for session persistence' },
            { name: 'CookieTransport / HeaderTransport', desc: 'How the session ID is sent to/from the client' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.sessions(
            store="memory",           # "memory" | "file"
            transport="cookie",       # "cookie" | "header"
            cookie_name="aq_session",
            cookie_path="/",
            cookie_httponly=True,
            cookie_secure=True,       # Requires HTTPS
            cookie_samesite="lax",    # "strict" | "lax" | "none"
            ttl=3600,                 # Session lifetime in seconds (1 hour)
            idle_timeout=1800,        # Expire after 30 min of inactivity
            rotate_id=True,           # Regenerate session ID on auth events
            max_size=4096,            # Maximum session data size in bytes
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using Sessions in Controllers</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Post
from aquilia.sessions import session, authenticated, stateful


class CartController(Controller):
    prefix = "/cart"

    @Get("/")
    @session  # Loads/creates session automatically
    async def view_cart(self, ctx):
        cart = ctx.session.get("cart", [])
        return ctx.json({"items": cart, "count": len(cart)})

    @Post("/add")
    @session
    async def add_to_cart(self, ctx):
        body = await ctx.json()
        cart = ctx.session.get("cart", [])
        cart.append(body["product_id"])
        ctx.session["cart"] = cart
        # Session auto-saves on response
        return ctx.json({"added": body["product_id"], "count": len(cart)})

    @Post("/clear")
    @session
    async def clear_cart(self, ctx):
        ctx.session.clear()
        return ctx.json({"cleared": True})`}</CodeBlock>
      </section>

      {/* Flash Messages */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Flash Messages</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Flash messages are one-time messages stored in the session and automatically cleared after being read. Perfect for post-redirect notifications.
        </p>
        <CodeBlock language="python" filename="flash.py">{`class AuthController(Controller):
    prefix = "/auth"

    @Post("/login")
    @session
    async def login(self, ctx):
        body = await ctx.json()
        user = await authenticate(body["email"], body["password"])
        if user:
            ctx.session["user_id"] = user.id
            ctx.session.flash("success", "Welcome back!")
            return ctx.redirect("/dashboard")
        else:
            ctx.session.flash("error", "Invalid credentials.")
            return ctx.redirect("/login")

    @Get("/dashboard")
    @session
    @authenticated  # Requires session with user_id
    async def dashboard(self, ctx):
        messages = ctx.session.get_flashed_messages()
        # messages = [{"category": "success", "message": "Welcome back!"}]
        return await self.render("dashboard.html", {
            "messages": messages,
        }, ctx)`}</CodeBlock>
      </section>

      {/* Decorators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Session Decorators</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Decorator</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { d: '@session', desc: 'Loads/creates a session for the request. Saves on response.' },
                { d: '@authenticated', desc: 'Requires an active session with identity. Returns 401 if not.' },
                { d: '@stateful', desc: 'Marks the handler as stateful — session is required and must have data.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.d}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SessionGuard */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SessionGuard</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Use <code className="text-aquilia-500">SessionGuard</code> in controller pipelines to enforce session requirements at the pipeline level rather than per-handler:
        </p>
        <CodeBlock language="python" filename="guard.py">{`from aquilia.sessions import SessionGuard


class DashboardController(Controller):
    prefix = "/dashboard"
    pipeline = [SessionGuard()]  # All handlers require session

    @Get("/")
    async def index(self, ctx):
        user_id = ctx.session["user_id"]
        return ctx.json({"user_id": user_id})

    @Get("/settings")
    async def settings(self, ctx):
        prefs = ctx.session.get("preferences", {})
        return ctx.json({"preferences": prefs})`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/auth/guards" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Auth Guards
        </Link>
        <Link to="/docs/middleware" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Middleware <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
