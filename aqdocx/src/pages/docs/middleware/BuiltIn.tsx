import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'

export function MiddlewareBuiltIn() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Layers className="w-4 h-4" />Middleware</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Built-in Middleware
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia ships with production-ready middleware for error handling, request IDs, and more.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ExceptionMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Catches all exceptions and converts them to structured error responses. In <code className="text-aquilia-500">debug=True</code> mode, renders beautiful React-style debug pages with stack traces, local variables, and the MongoDB Atlas color palette.
        </p>
        <CodeBlock language="python" filename="ExceptionMiddleware">{`from aquilia.middleware import ExceptionMiddleware

# Register on server
server.middleware(ExceptionMiddleware(debug=True))

# What it handles:
# ValueError → 400 Bad Request
# PermissionError → 403 Forbidden
# FileNotFoundError → 404 Not Found
# NotImplementedError → 501 Not Implemented
# Fault (with status) → fault.status
# Any other Exception → 500 Internal Server Error

# In debug mode with Accept: text/html:
# → Renders full debug page with stack trace, frames, locals
# In production or JSON requests:
# → Returns {"error": "message", "code": "..."}`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RequestIdMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Assigns a unique request ID to every request. If the client sends an <code className="text-aquilia-500">X-Request-ID</code> header, that value is used; otherwise a new UUID is generated.
        </p>
        <CodeBlock language="python" filename="RequestIdMiddleware">{`from aquilia.middleware import RequestIdMiddleware

server.middleware(RequestIdMiddleware(header_name="X-Request-ID"))

# In your handler, access via:
request_id = ctx.request_id
# or
request_id = request.state["request_id"]

# The ID is also added to the response header:
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Recommended Stack</h2>
        <CodeBlock language="python" filename="Production Middleware Stack">{`from aquilia.server import AquiliaServer
from aquilia.middleware import ExceptionMiddleware, RequestIdMiddleware

server = AquiliaServer()

# Order matters! First added = outermost layer
server.middleware(RequestIdMiddleware(), priority=5)      # Always first
server.middleware(ExceptionMiddleware(debug=False), priority=10)
server.middleware(cors_middleware, priority=15)
server.middleware(auth_middleware, priority=20)
server.middleware(rate_limit_middleware, priority=25)
server.middleware(timing_middleware, priority=30)

# Request flow:
# RequestID → Exception → CORS → Auth → RateLimit → Timing → Handler
# Response flows back in reverse order`}</CodeBlock>
      </section>
    </div>
  )
}
