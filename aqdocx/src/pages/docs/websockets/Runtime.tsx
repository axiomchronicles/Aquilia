import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Globe } from 'lucide-react'

export function WebSocketRuntime() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Globe className="w-4 h-4" />
          WebSockets / Runtime
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          WebSocket Runtime
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">AquilaSockets</code> is the WebSocket runtime engine that compiles socket controllers, manages connections, and handles the ASGI WebSocket protocol. <code className="text-aquilia-400">SocketRouter</code> matches incoming connections to the correct controller.
        </p>
      </div>

      {/* AquilaSockets */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquilaSockets</h2>
        <CodeBlock language="python" filename="runtime.py">{`from aquilia.sockets import AquilaSockets, InMemoryAdapter

# Create the runtime
sockets = AquilaSockets(
    adapter=InMemoryAdapter(),
    max_connections=10_000,
    heartbeat_interval=30,
    max_message_size=1024 * 1024,  # 1 MB
)

# Register controllers
sockets.register(ChatController)
sockets.register(NotificationController)

# Compile routes (called automatically at startup)
await sockets.compile()`}</CodeBlock>
      </section>

      {/* SocketRouter */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SocketRouter</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Routes incoming WebSocket connections to the correct controller based on the request path.
        </p>
        <CodeBlock language="python" filename="router.py">{`from aquilia.sockets import SocketRouter

router = SocketRouter()
router.add("/ws/chat", ChatController)
router.add("/ws/chat/{room}", RoomChatController)
router.add("/ws/notifications", NotificationController)

# Match a path
controller, params = router.match("/ws/chat/general")
# controller = RoomChatController, params = {"room": "general"}`}</CodeBlock>
      </section>

      {/* Server Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Server Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Register the WebSocket runtime with your Aquilia server via the Integration system.
        </p>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia.config_builders import WorkspaceBuilder, Integration

workspace = WorkspaceBuilder("myapp")
workspace.integrations([
    Integration.websockets(
        adapter="memory",       # or "redis", "nats"
        max_connections=5_000,
        heartbeat_interval=30,
        max_message_size=1024 * 1024,
    ),
])`}</CodeBlock>
      </section>

      {/* Middleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WebSocket Middleware</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {[
            { name: 'SocketMiddleware', desc: 'Base middleware class for WebSocket pipelines' },
            { name: 'MessageValidationMiddleware', desc: 'Validates message envelopes against Schema definitions' },
            { name: 'RateLimitMiddleware', desc: 'Per-connection rate limiting with configurable windows' },
          ].map((m, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{m.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Faults */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WebSocket Faults</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'WS_HANDSHAKE_FAILED', desc: 'WebSocket handshake rejected' },
            { name: 'WS_AUTH_REQUIRED', desc: 'Authentication required for connection' },
            { name: 'WS_MESSAGE_INVALID', desc: 'Message failed schema validation' },
            { name: 'WS_ROOM_FULL', desc: 'Room has reached max capacity' },
            { name: 'WS_RATE_LIMIT_EXCEEDED', desc: 'Connection exceeded message rate limit' },
            { name: 'WS_CONNECTION_CLOSED', desc: 'Connection was unexpectedly closed' },
            { name: 'WS_PAYLOAD_TOO_LARGE', desc: 'Message exceeds max payload size' },
          ].map((f, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-red-400' : 'text-red-600'}`}>{f.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
