import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Globe } from 'lucide-react'

export function ServerASGI() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Globe className="w-4 h-4" />Server</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>ASGI Adapter</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ASGIAdapter</code> is the bridge between ASGI servers (uvicorn, hypercorn, daphne) and the Aquilia framework. It translates raw ASGI scope/receive/send tuples into Aquilia's Request and Response objects.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Protocol Handling</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The adapter handles three ASGI scope types:
        </p>
        <div className="space-y-4">
          {[
            { type: 'http', desc: 'Standard HTTP/1.1 and HTTP/2 requests. Parses headers, body, query string, and path. Creates a Request object and passes it through the middleware stack to the Controller Engine.' },
            { type: 'websocket', desc: 'WebSocket upgrade requests. Manages the connection lifecycle (connect, receive, send, disconnect) and delegates to WebSocket controllers.' },
            { type: 'lifespan', desc: 'Application startup and shutdown events. Triggers the LifecycleCoordinator phases: initializing, starting, running, shutting down, stopped.' },
          ].map((p, i) => (
            <div key={i} className={`p-5 rounded-xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
              <code className="text-aquilia-500 font-mono font-bold">{p.type}</code>
              <p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ASGI Interface</h2>
        <CodeBlock language="python" filename="aquilia/asgi.py">{`class ASGIAdapter:
    """
    Translates ASGI protocol into Aquilia abstractions.
    """

    def __init__(self, app: "AquiliaServer"):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """Main ASGI entry point."""
        scope_type = scope["type"]

        if scope_type == "http":
            await self._handle_http(scope, receive, send)
        elif scope_type == "websocket":
            await self._handle_websocket(scope, receive, send)
        elif scope_type == "lifespan":
            await self._handle_lifespan(scope, receive, send)

    async def _handle_http(self, scope, receive, send):
        # 1. Create Request from ASGI scope
        request = Request(scope, receive, send)

        # 2. Run through middleware stack
        response = await self.app.middleware_stack(request)

        # 3. Send response bytes back via ASGI
        await response.send(send)

    async def _handle_lifespan(self, scope, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await self.app.lifecycle.startup()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await self.app.lifecycle.shutdown()
                await send({"type": "lifespan.shutdown.complete"})
                return`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using with ASGI Servers</h2>
        <CodeBlock language="python" filename="Direct ASGI Usage">{`# With uvicorn (programmatic)
import uvicorn
from aquilia import AquiliaServer

app = AquiliaServer()
# ... register controllers, etc.

# app.asgi_app is the ASGI-compatible callable
uvicorn.run(app.asgi_app, host="0.0.0.0", port=8000)

# Or with CLI:
# uvicorn starter:app.asgi_app --host 0.0.0.0 --port 8000 --reload`}</CodeBlock>

        <CodeBlock language="bash" filename="Terminal">{`# Using app.run() (recommended — wraps uvicorn internally)
python starter.py

# Or use the Aquilia CLI
aquilia serve --host 0.0.0.0 --port 8000 --reload`}</CodeBlock>
      </section>
    </div>
  )
}
