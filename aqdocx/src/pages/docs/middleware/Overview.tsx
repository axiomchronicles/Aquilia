import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'

export function MiddlewareOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Layers className="w-4 h-4" />Middleware</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Middleware
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Middleware wraps every request/response cycle. Aquilia's <code className="text-aquilia-500">MiddlewareStack</code> supports scoped middleware (global, app, controller, route) with deterministic priority ordering.
        </p>
      </div>

      {/* Architecture SVG */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Middleware Pipeline</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 660 180" className="w-full h-auto">
            <rect width="660" height="180" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {/* Onion layers */}
            <rect x="30" y="20" width="600" height="140" rx="12" fill="#22c55e08" stroke="#22c55e" strokeWidth="1.5" strokeDasharray="6 3" />
            <text x="60" y="42" fill="#22c55e" fontSize="11" fontWeight="600">Global (priority 0–49)</text>

            <rect x="80" y="50" width="500" height="100" rx="10" fill="#3b82f608" stroke="#3b82f6" strokeWidth="1.5" strokeDasharray="6 3" />
            <text x="110" y="70" fill="#3b82f6" fontSize="11" fontWeight="600">App (priority 50)</text>

            <rect x="130" y="78" width="400" height="65" rx="8" fill="#f59e0b08" stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="6 3" />
            <text x="155" y="96" fill="#f59e0b" fontSize="11" fontWeight="600">Controller</text>

            <rect x="280" y="95" width="140" height="35" rx="8" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#8b5cf6" strokeWidth="2" />
            <text x="350" y="117" textAnchor="middle" fill="#8b5cf6" fontSize="13" fontWeight="700">Handler</text>

            {/* Flow arrows */}
            <path d="M 30 90 L 80 90" stroke="#22c55e" strokeWidth="1.5" markerEnd="url(#mwArrow)" />
            <path d="M 80 90 L 130 90" stroke="#3b82f6" strokeWidth="1.5" markerEnd="url(#mwArrow)" />
            <path d="M 130 112 L 280 112" stroke="#f59e0b" strokeWidth="1.5" markerEnd="url(#mwArrow)" />

            <defs>
              <marker id="mwArrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Writing Middleware</h2>
        <CodeBlock language="python" filename="Custom Middleware">{`from aquilia.request import Request
from aquilia.response import Response

# Middleware signature: (request, ctx, next) → Response
async def timing_middleware(request, ctx, next):
    """Measure request processing time."""
    import time
    start = time.perf_counter()

    # Call next handler in the chain
    response = await next(request, ctx)

    elapsed = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
    return response

# Class-based middleware
class CORSMiddleware:
    def __init__(self, allow_origins: list[str] = ["*"]):
        self.allow_origins = allow_origins

    async def __call__(self, request, ctx, next):
        response = await next(request, ctx)
        origin = request.header("Origin") or "*"
        if "*" in self.allow_origins or origin in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registering Middleware</h2>
        <CodeBlock language="python" filename="Registration">{`from aquilia.server import AquiliaServer
from aquilia.middleware import MiddlewareStack

server = AquiliaServer()

# Global middleware
server.middleware(timing_middleware)
server.middleware(CORSMiddleware(allow_origins=["https://example.com"]))

# With priority (lower = earlier in chain)
server.middleware(logging_middleware, priority=10)
server.middleware(auth_middleware, priority=20)

# Scoped middleware
server.middleware(admin_middleware, scope="controller:AdminController")

# MiddlewareStack API directly
stack = MiddlewareStack()
stack.add(timing_middleware, scope="global", priority=10, name="timing")
stack.add(auth_middleware, scope="global", priority=20, name="auth")

# Build the handler chain
handler = stack.build_handler(final_handler)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope &amp; Priority</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <p className={`mb-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Middleware is sorted by scope first, then by priority within each scope:
          </p>
          <ol className={`space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li><span className="text-aquilia-500 font-bold">1.</span> <code className="text-aquilia-400">global</code> — Runs on every request</li>
            <li><span className="text-aquilia-500 font-bold">2.</span> <code className="text-aquilia-400">app:name</code> — Runs for a specific app module</li>
            <li><span className="text-aquilia-500 font-bold">3.</span> <code className="text-aquilia-400">controller:name</code> — Runs for a specific controller</li>
            <li><span className="text-aquilia-500 font-bold">4.</span> <code className="text-aquilia-400">route:pattern</code> — Runs for a specific route pattern</li>
          </ol>
          <p className={`mt-3 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
            Within each scope, lower priority numbers execute first (outermost layer).
          </p>
        </div>
      </section>
    </div>
  )
}
