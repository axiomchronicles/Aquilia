import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Server, ArrowRight } from 'lucide-react'

export function ServerOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Server className="w-4 h-4" />Core</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquiliaServer</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">AquiliaServer</code> is the central orchestrator of the framework. It manages the DI container, controller compilation, middleware stack, database connections, lifecycle events, and the ASGI adapter.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating a Server</h2>
        <CodeBlock language="python" filename="Basic Server">{`from aquilia import AquiliaServer

app = AquiliaServer(
    debug=True,                    # Enable debug mode
    title="My API",                # OpenAPI title
    version="1.0.0",              # API version
    description="My Aquilia App",  # OpenAPI description
)

# Register components
app.use_database("sqlite:///db.sqlite3")
app.register_controller(MyController)
app.container.register(MyService, lifetime=Singleton)

# Run the server
app.run(host="0.0.0.0", port=8000, reload=True)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key APIs</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'register_controller(cls)', d: 'Register a controller class for compilation. Extracts route metadata and adds to the route tree.' },
                { m: 'register_model(cls)', d: 'Register a Model class for database table creation and migration tracking.' },
                { m: 'use_database(url)', d: 'Configure the database engine with a connection URL (sqlite, postgres, mysql).' },
                { m: 'use_middleware(cls, **opts)', d: 'Add a middleware class to the stack. Middleware runs in FIFO order.' },
                { m: 'use_sessions(config)', d: 'Enable session middleware with the given SessionConfig.' },
                { m: 'use_static(path, dir)', d: 'Serve static files from a directory at a URL prefix.' },
                { m: 'use_templates(dir)', d: 'Initialize the Jinja2 template engine with a templates directory.' },
                { m: 'container', d: 'The root DI Container instance. Use container.register() to add providers.' },
                { m: 'run(host, port, reload)', d: 'Start the uvicorn server. Compiles routes, runs lifecycle startup, and begins serving.' },
                { m: 'on_startup(fn)', d: 'Register a callback to run during the startup lifecycle phase.' },
                { m: 'on_shutdown(fn)', d: 'Register a callback to run during the shutdown lifecycle phase.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full Example</h2>
        <CodeBlock language="python" filename="starter.py">{`from aquilia import AquiliaServer
from aquilia.di import Singleton
from aquilia.middleware import CORSMiddleware, RateLimitMiddleware

from modules.products import ProductController, Product, ProductService
from modules.auth import AuthController, AuthService, AuthGuard


app = AquiliaServer(debug=True, title="E-Commerce API")

# Database
app.use_database("sqlite:///store.sqlite3")

# Models
app.register_model(Product)

# Middleware (order matters!)
app.use_middleware(CORSMiddleware, allow_origins=["*"])
app.use_middleware(RateLimitMiddleware, max_requests=100, window=60)

# Templates & Static
app.use_templates("artifacts/templates")
app.use_static("/static", "artifacts/static")

# Sessions
app.use_sessions({
    "secret": "my-secret-key",
    "max_age": 3600,
    "cookie_name": "session_id",
})

# DI
app.container.register(ProductService, lifetime=Singleton)
app.container.register(AuthService, lifetime=Singleton)

# Controllers
app.register_controller(ProductController)
app.register_controller(AuthController)

# Lifecycle hooks
@app.on_startup
async def startup():
    print("🦅 Application starting...")

@app.on_shutdown
async def shutdown():
    print("🦅 Application shutting down...")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)`}</CodeBlock>
      </section>

      <section>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link to="/docs/server/asgi" className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>ASGI Adapter <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" /></h3>
            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>How Aquilia interfaces with ASGI servers</p>
          </Link>
          <Link to="/docs/server/lifecycle" className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" /></h3>
            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Startup, shutdown, and lifecycle coordination</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
