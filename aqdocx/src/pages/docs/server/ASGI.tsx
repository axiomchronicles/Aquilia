import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Globe, Layers, Zap, ArrowRight, AlertCircle, Settings } from 'lucide-react'

export function ServerASGI() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Globe className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>ASGI Adapter</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.asgi — Bridging ASGI to Aquilia internals</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ASGIAdapter</code> is a 338-line class that converts raw ASGI protocol events
          into Aquilia's <code>Request</code>/<code>Response</code> abstractions and delegates to the
          controller router and middleware stack.
        </p>
      </div>

      {/* What is ASGI */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          ASGI Protocol
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          ASGI (Asynchronous Server Gateway Interface) is the Python standard for async web servers.
          Aquilia is a pure ASGI application — it works with any ASGI server: <strong>uvicorn</strong>,
          <strong>hypercorn</strong>, <strong>daphne</strong>, or <strong>granian</strong>.
        </p>

        <CodeBlock
          code={`# The ASGI contract:
async def application(scope: dict, receive: Callable, send: Callable) -> None:
    """
    scope:   Connection metadata (type, path, method, headers, ...)
    receive: Async callable to receive client events (body chunks, WS messages)
    send:    Async callable to send response events
    """
    ...

# Aquilia's ASGIAdapter implements this exact interface:
# server.app(scope, receive, send)`}
          language="python"
        />
      </section>

      {/* ASGIAdapter class */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 text-aquilia-400" />
          ASGIAdapter Class
        </h2>

        <CodeBlock
          code={`class ASGIAdapter:
    """ASGI application that bridges ASGI protocol to Aquilia internals."""

    def __init__(
        self,
        controller_router: ControllerRouter,
        controller_engine: ControllerEngine,
        socket_runtime: AquilaSockets,
        middleware_stack: MiddlewareStack,
        server: AquiliaServer,   # Back-reference for lifecycle
    ):
        self.controller_router = controller_router
        self.controller_engine = controller_engine
        self.socket_runtime = socket_runtime
        self.middleware_stack = middleware_stack
        self.server = server

        # Cache the built middleware chain for performance
        self._middleware_handler = None`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The adapter caches the compiled middleware chain after the first request, avoiding
          the overhead of rebuilding the chain on every request.
        </p>
      </section>

      {/* __call__ flow */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Request Flow
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When an ASGI scope arrives, <code>__call__</code> routes it based on the scope type:
        </p>

        <CodeBlock
          code={`async def __call__(self, scope: dict, receive, send):
    # 1. Ensure server startup (idempotent)
    if not self.server._startup_complete:
        await self.server.startup()

    scope_type = scope["type"]

    if scope_type == "http":
        await self._handle_http(scope, receive, send)

    elif scope_type == "websocket":
        await self._handle_websocket(scope, receive, send)

    elif scope_type == "lifespan":
        await self._handle_lifespan(scope, receive, send)


async def _handle_http(self, scope, receive, send):
    # 1. Wrap raw ASGI scope into a Request object
    request = Request(scope, receive, send)

    # 2. Build RequestCtx (identity/session filled by middleware)
    ctx = RequestCtx(
        request=request,
        container=self.server._get_base_container(),
    )

    # 3. Build middleware chain (cached after first call)
    if self._middleware_handler is None:
        final_handler = self._route_handler  # The controller dispatcher
        self._middleware_handler = self.middleware_stack.build_handler(final_handler)

    # 4. Execute middleware chain → controller → response
    response = await self._middleware_handler(request, ctx)

    # 5. Send response via ASGI
    await response.send(send)


async def _route_handler(self, request, ctx):
    """Final handler at the end of the middleware chain."""
    # Match route
    match = self.controller_router.match(request.path, request.method)
    if match is None:
        return Response.json({"error": "Not Found"}, status=404)

    compiled_route, path_params = match

    # Dispatch to controller engine
    return await self.controller_engine.handle(
        compiled_route, ctx, path_params
    )`}
          language="python"
        />
      </section>

      {/* WebSocket handling */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          WebSocket Handling
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          WebSocket connections are delegated to <code>AquilaSockets</code> runtime:
        </p>

        <CodeBlock
          code={`async def _handle_websocket(self, scope, receive, send):
    """Delegate WebSocket connections to the socket runtime."""
    if self.socket_runtime:
        await self.socket_runtime.handle(scope, receive, send)
    else:
        # No WebSocket runtime configured — reject
        await send({"type": "websocket.close", "code": 1000})`}
          language="python"
        />
      </section>

      {/* Lifespan */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          ASGI Lifespan Protocol
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The adapter handles the ASGI lifespan protocol for graceful startup/shutdown
          with ASGI servers that support it (uvicorn with <code>--lifespan on</code>):
        </p>

        <CodeBlock
          code={`async def _handle_lifespan(self, scope, receive, send):
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                await self.server.startup()
                await send({"type": "lifespan.startup.complete"})
            except Exception as exc:
                await send({
                    "type": "lifespan.startup.failed",
                    "message": str(exc),
                })
                return

        elif message["type"] == "lifespan.shutdown":
            await self.server.shutdown()
            await send({"type": "lifespan.shutdown.complete"})
            return`}
          language="python"
        />
      </section>

      {/* Deployment examples */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Globe className="w-5 h-5 text-aquilia-400" />
          Deployment with Different ASGI Servers
        </h2>

        <div className="space-y-4">
          <div>
            <p className={`text-sm font-semibold mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Uvicorn (recommended)</p>
            <CodeBlock
              code={`# Development
uvicorn my_app:server.app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn my_app:server.app --host 0.0.0.0 --port 8000 \\
    --workers 4 --lifespan on --access-log`}
              language="bash"
            />
          </div>

          <div>
            <p className={`text-sm font-semibold mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Hypercorn</p>
            <CodeBlock
              code={`hypercorn my_app:server.app --bind 0.0.0.0:8000 --workers 4`}
              language="bash"
            />
          </div>

          <div>
            <p className={`text-sm font-semibold mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Gunicorn with Uvicorn Workers</p>
            <CodeBlock
              code={`gunicorn my_app:server.app \\
    -k uvicorn.workers.UvicornWorker \\
    -w 4 --bind 0.0.0.0:8000`}
              language="bash"
            />
          </div>
        </div>
      </section>

      {/* Performance */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Performance Notes
        </h2>

        <ul className={`space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Middleware chain caching:</strong> The middleware handler is built once and cached. No chain reconstruction on subsequent requests.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Request object:</strong> Constructed from raw ASGI scope with zero-copy header access. Body is lazily read only when <code>await request.body()</code> is called.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Route matching:</strong> CompiledPattern uses pre-compiled regex for O(1) matching per pattern segment.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Response serialization:</strong> <code>Response.json()</code> uses <code>orjson</code> when available, falling back to stdlib <code>json</code>.</div>
          </li>
        </ul>
      </section>

      {/* Next */}
      <section className="mb-10">
        <div className="flex flex-col gap-2">
          <Link to="/docs/server/lifecycle" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Lifecycle: Startup/shutdown coordination
          </Link>
          <Link to="/docs/request-response/request" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Request: The Request object in depth
          </Link>
          <Link to="/docs/middleware/stack" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → MiddlewareStack: How the chain is built and ordered
          </Link>
        </div>
      </section>
    </div>
  )
}
