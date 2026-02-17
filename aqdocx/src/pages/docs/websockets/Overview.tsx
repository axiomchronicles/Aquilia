import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Radio } from 'lucide-react'

export function WebSocketsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Radio className="w-4 h-4" />
          Advanced / WebSockets
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          WebSockets
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          AquilaSockets provides production-grade WebSocket support with controller-based declarative syntax, DI-scoped connections, typed message envelopes, room-based pub/sub, horizontal scaling adapters, and auth-first handshake guards.
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <div className="space-y-3">
          {[
            { name: 'SocketController', desc: 'Class-based WebSocket handler. Compiled at build time, instantiated per-connection with its own DI scope.' },
            { name: 'Connection', desc: 'Represents a WebSocket connection with state tracking, send/receive methods, and room membership.' },
            { name: 'MessageEnvelope', desc: 'Typed message wrapper with event name, payload, metadata, and codec (JSON by default).' },
            { name: 'AquilaSockets', desc: 'Runtime that manages socket controllers, routing, connection lifecycle, and adapter bridging.' },
            { name: 'Adapter', desc: 'Pluggable transport for horizontal scaling: InMemoryAdapter (default), RedisAdapter, or custom.' },
            { name: 'SocketGuard', desc: 'Security guards for handshake auth, origin validation, message auth, and rate limiting.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SocketController */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Socket Controllers</h2>
        <CodeBlock language="python" filename="chat_controller.py">{`from aquilia.sockets import (
    SocketController, Socket, OnConnect, OnDisconnect,
    Event, AckEvent, Subscribe, Unsubscribe, Guard,
    Schema, Connection,
)
from aquilia import Inject


@Socket("/ws/chat")
class ChatController(SocketController):

    @Inject()
    def __init__(self, chat_service: ChatService):
        self.chat = chat_service

    @OnConnect
    async def on_connect(self, conn: Connection):
        """Called when a client connects."""
        user = conn.scope.get("identity")
        await conn.join_room("general")
        await conn.send_event("welcome", {
            "message": f"Welcome {user.username}!",
            "online": await self.chat.online_count(),
        })

    @OnDisconnect
    async def on_disconnect(self, conn: Connection):
        """Called when a client disconnects."""
        await self.chat.set_offline(conn.scope["identity"].id)

    @Event("message")
    @Schema({"text": str, "room": str})
    async def on_message(self, conn: Connection, data: dict):
        """Handle incoming chat messages."""
        message = await self.chat.save_message(
            user_id=conn.scope["identity"].id,
            room=data["room"],
            text=data["text"],
        )
        # Broadcast to all connections in the room
        await conn.broadcast_to_room(data["room"], "message", {
            "id": message.id,
            "text": message.text,
            "user": message.user.username,
            "timestamp": message.created_at.isoformat(),
        })

    @AckEvent("typing")
    async def on_typing(self, conn: Connection, data: dict):
        """Acknowledged event — client receives confirmation."""
        await conn.broadcast_to_room(data["room"], "typing", {
            "user": conn.scope["identity"].username,
        })
        return {"ack": True}  # Sent back to the sender

    @Subscribe
    async def on_subscribe(self, conn: Connection, room: str):
        """Client subscribes to a room."""
        await conn.join_room(room)

    @Unsubscribe
    async def on_unsubscribe(self, conn: Connection, room: str):
        """Client unsubscribes from a room."""
        await conn.leave_room(room)`}</CodeBlock>
      </section>

      {/* Guards */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WebSocket Guards</h2>
        <CodeBlock language="python" filename="guards.py">{`from aquilia.sockets import (
    HandshakeAuthGuard, OriginGuard,
    MessageAuthGuard, RateLimitGuard,
)


# Auth-first handshake — reject unauthenticated connections
@Socket("/ws/notifications", guards=[
    HandshakeAuthGuard(),             # JWT/session auth during upgrade
    OriginGuard(["https://myapp.com"]),  # Restrict origins
])
class NotificationController(SocketController):

    @Event("subscribe")
    @Guard(MessageAuthGuard())          # Per-message auth
    @Guard(RateLimitGuard(max_rate=10))  # 10 messages per second
    async def subscribe_topic(self, conn: Connection, data: dict):
        await conn.join_room(data["topic"])
        return {"subscribed": data["topic"]}`}</CodeBlock>
      </section>

      {/* Adapters */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Horizontal Scaling Adapters</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          For multi-instance deployments, adapters synchronize events across processes:
        </p>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.websockets(
            adapter="redis",            # "memory" | "redis"
            redis_url="redis://localhost:6379/1",
            ping_interval=25,           # Seconds between keepalive pings
            max_message_size=1_048_576, # 1MB max message
            max_connections=10_000,     # Per-instance limit
        ),
    ],
)`}</CodeBlock>
        <div className={`mt-4 ${boxClass}`}>
          <h3 className={`font-bold mb-2 text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>Available Adapters</h3>
          <ul className={`space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>• <code className="text-aquilia-500">InMemoryAdapter</code> — Single-instance, zero-dependency (default)</li>
            <li>• <code className="text-aquilia-500">RedisAdapter</code> — Redis Pub/Sub for multi-instance broadcasting</li>
          </ul>
        </div>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/cache" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Cache
        </Link>
        <Link to="/docs/templates" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Templates <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
