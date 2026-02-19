import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function MiddlewareStack() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Middleware / Stack & Composition
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Middleware Stack
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">MiddlewareStack</code> manages the ordered chain of middleware. Middleware execute in LIFO order — the last added runs first (outermost wrapper).
        </p>
      </div>

      {/* Stack Basics */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Building the Stack</h2>
        <CodeBlock language="python" filename="stack.py">{`from aquilia.middleware import MiddlewareStack

stack = MiddlewareStack()

# Add middleware (LIFO order)
stack.add(FaultMiddleware)         # Runs 1st (outermost)
stack.add(SecurityHeadersMiddleware)
stack.add(CORSMiddleware)
stack.add(SessionMiddleware)
stack.add(RateLimitMiddleware)
stack.add(RequestScopeMiddleware)  # Runs last (innermost)

# Conditional middleware
stack.add(DebugToolbarMiddleware, condition=lambda: settings.DEBUG)

# Priority-based insertion
stack.add(LoggingMiddleware, priority=0)  # Always first`}</CodeBlock>
      </section>

      {/* Custom Middleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Writing Middleware</h2>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.middleware import Middleware

class TimingMiddleware(Middleware):
    async def __call__(self, request, call_next):
        start = time.perf_counter()
        
        # Pre-processing
        request.state.start_time = start
        
        # Call next middleware / handler
        response = await call_next(request)
        
        # Post-processing
        duration = time.perf_counter() - start
        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        
        return response`}</CodeBlock>
      </section>

      {/* RequestScopeMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RequestScopeMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Creates a DI scope for each request. Scoped services are created once per request and disposed when the request completes.
        </p>
        <CodeBlock language="python" filename="scope.py">{`from aquilia.middleware import RequestScopeMiddleware

# Automatically added by AquiliaServer
# Creates container.create_scope() per request
# Attaches scope to request.state.scope
# Disposes scope after response is sent

class RequestScopeMiddleware(Middleware):
    async def __call__(self, request, call_next):
        async with self.container.create_scope() as scope:
            request.state.scope = scope
            return await call_next(request)`}</CodeBlock>
      </section>

      {/* Built-in Middleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Built-in Middleware</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Middleware</th>
                <th className="py-3 px-4 text-left font-semibold">Module</th>
                <th className="py-3 px-4 text-left font-semibold">Purpose</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['FaultMiddleware', 'faults', 'Catches exceptions → faults'],
                ['CORSMiddleware', 'middleware_ext', 'Cross-origin resource sharing'],
                ['CSRFMiddleware', 'middleware_ext', 'CSRF token validation'],
                ['CSPMiddleware', 'middleware_ext', 'Content Security Policy headers'],
                ['HSTSMiddleware', 'middleware_ext', 'HTTP Strict Transport Security'],
                ['RateLimitMiddleware', 'middleware_ext', 'Request rate limiting'],
                ['SecurityHeadersMiddleware', 'middleware_ext', 'X-Frame, X-Content-Type, etc.'],
                ['SessionMiddleware', 'sessions', 'Session management'],
                ['StaticMiddleware', 'middleware_ext', 'Static file serving'],
                ['RequestScopeMiddleware', 'middleware', 'DI scope per request'],
                ['CacheMiddleware', 'cache', 'HTTP response caching'],
              ].map(([mw, mod, purpose], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{mw}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{mod}</td>
                  <td className="py-2.5 px-4 text-xs">{purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}