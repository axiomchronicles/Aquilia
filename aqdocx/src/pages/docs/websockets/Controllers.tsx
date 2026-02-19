import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Globe } from 'lucide-react'

export function WebSocketControllers() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Globe className="w-4 h-4" />
          WebSockets / Socket Controllers
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Socket Controllers
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          WebSocket handlers are defined using <code className="text-aquilia-400">SocketController</code> — a declarative, decorator-driven class similar to HTTP controllers. Each connection gets its own DI scope.
        </p>
      </div>

      {/* Decorators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Decorator Reference</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Decorator</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['@Socket(path)', 'Marks the class as a socket controller on a given path'],
                  ['@OnConnect', 'Called when a client establishes a WebSocket connection'],
                  ['@OnDisconnect', 'Called when a client disconnects'],
                  ['@Event(name)', 'Handles a named event message from the client'],
                  ['@AckEvent(name)', 'Handles an event that expects an acknowledgement response'],
                  ['@Subscribe(room)', 'Subscribes the connection to a pub/sub room'],
                  ['@Unsubscribe(room)', 'Unsubscribes the connection from a room'],
                  ['@Guard(guard_class)', 'Applies a guard to a specific handler or the entire controller'],
                ].map(([dec, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{dec}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Basic Controller */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Defining a Socket Controller</h2>
        <CodeBlock language="python" filename="chat.py">{`from aquilia.sockets import (
    SocketController, Socket, OnConnect, OnDisconnect,
    Event, AckEvent, Subscribe, Connection,
)

@Socket("/ws/chat")
class ChatController(SocketController):
    """Real-time chat controller."""

    @OnConnect
    async def on_connect(self, conn: Connection):
        print(f"Client connected: {conn.id}")
        await conn.send("welcome", {"message": "Hello!"})

    @OnDisconnect
    async def on_disconnect(self, conn: Connection):
        print(f"Client disconnected: {conn.id}")

    @Event("message")
    async def on_message(self, conn: Connection, data: dict):
        """Handle incoming chat messages."""
        room = data.get("room", "general")
        await conn.broadcast(room, "message", {
            "from": conn.id,
            "text": data["text"],
        })

    @AckEvent("typing")
    async def on_typing(self, conn: Connection, data: dict):
        """Handle typing indicator — client expects ack."""
        await conn.broadcast(data["room"], "typing", {
            "user": conn.id,
        })
        return {"ack": True}

    @Subscribe("room")
    async def join_room(self, conn: Connection, room: str):
        print(f"{conn.id} joined {room}")

    @Unsubscribe("room")
    async def leave_room(self, conn: Connection, room: str):
        print(f"{conn.id} left {room}")`}</CodeBlock>
      </section>

      {/* Connection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Connection Object</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each WebSocket connection is represented by a <code className="text-aquilia-400">Connection</code> object with its own state and DI scope.
        </p>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Property/Method</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['conn.id', 'Unique connection identifier'],
                  ['conn.state', 'ConnectionState enum (CONNECTING, OPEN, CLOSING, CLOSED)'],
                  ['conn.scope', 'ASGI scope with path, headers, query params'],
                  ['conn.identity', 'Authenticated identity (if auth guard applied)'],
                  ['conn.send(event, data)', 'Send a message to this connection'],
                  ['conn.broadcast(room, event, data)', 'Broadcast to all connections in a room'],
                  ['conn.join(room)', 'Join a pub/sub room'],
                  ['conn.leave(room)', 'Leave a pub/sub room'],
                  ['conn.close(code?, reason?)', 'Close the connection'],
                ].map(([prop, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{prop}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Message Envelope */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Message Envelope & Codecs</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Messages are wrapped in a <code className="text-aquilia-400">MessageEnvelope</code> with typed fields: event name, payload, message ID, and timestamp. <code className="text-aquilia-400">MessageCodec</code> handles serialization (JSON by default).
        </p>
        <CodeBlock language="python" filename="envelope.py">{`from aquilia.sockets import MessageEnvelope, MessageType, JSONCodec

# Envelope structure
envelope = MessageEnvelope(
    type=MessageType.EVENT,
    event="message",
    data={"text": "Hello!"},
    id="msg-uuid-123",
)

# Custom codec
codec = JSONCodec()
raw = codec.encode(envelope)   # bytes
parsed = codec.decode(raw)     # MessageEnvelope`}</CodeBlock>
      </section>

      {/* Guards */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Socket Guards</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Guards protect socket connections and messages. Apply them at the controller or handler level.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
          {[
            { name: 'HandshakeAuthGuard', desc: 'Validates authentication during the WebSocket handshake' },
            { name: 'OriginGuard', desc: 'Validates the Origin header against allowed origins' },
            { name: 'MessageAuthGuard', desc: 'Re-validates auth on each message (for long-lived connections)' },
            { name: 'RateLimitGuard', desc: 'Per-connection message rate limiting' },
          ].map((g, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{g.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{g.desc}</p>
            </div>
          ))}
        </div>
        <CodeBlock language="python" filename="guarded.py">{`from aquilia.sockets import (
    SocketController, Socket, Guard,
    HandshakeAuthGuard, RateLimitGuard,
)

@Socket("/ws/secure")
@Guard(HandshakeAuthGuard)
@Guard(RateLimitGuard(max_messages=100, window=60))
class SecureChatController(SocketController):
    """All handlers require authentication + rate limiting."""
    ...`}</CodeBlock>
      </section>
    </div>
  )
}
