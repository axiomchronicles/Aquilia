import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Globe } from 'lucide-react'

export function WebSocketAdapters() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Globe className="w-4 h-4" />
          WebSockets / Adapters
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            WebSocket Adapters
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Adapters enable horizontal scaling by synchronizing room memberships and broadcast messages across multiple server instances. Aquilia provides three adapters out of the box.
        </p>
      </div>

      {/* Adapter Comparison */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Adapter Comparison</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Adapter</th>
                  <th className="text-left pb-3 font-semibold">Scaling</th>
                  <th className="text-left pb-3 font-semibold">Dependencies</th>
                  <th className="text-left pb-3 font-semibold">Best For</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['InMemoryAdapter', 'Single process', 'None', 'Development, testing, single-instance deploys'],
                  ['RedisAdapter', 'Multi-process', 'Redis 5+', 'Production horizontal scaling with Redis Pub/Sub'],
                  ['Adapter (base)', '-', '-', 'Subclass to implement custom adapters (NATS, Kafka, etc.)'],
                ].map(([name, scale, deps, best], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{name}</td>
                    <td className="py-2 text-xs">{scale}</td>
                    <td className="py-2 text-xs">{deps}</td>
                    <td className="py-2 text-xs">{best}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* InMemoryAdapter */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>InMemoryAdapter</h2>
        <CodeBlock language="python" filename="memory.py">{`from aquilia.sockets import AquilaSockets, InMemoryAdapter

sockets = AquilaSockets(adapter=InMemoryAdapter())
# All rooms and broadcasts are in-process only.
# Perfect for development and testing.`}</CodeBlock>
      </section>

      {/* RedisAdapter */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RedisAdapter</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Uses Redis Pub/Sub to synchronize broadcast messages across multiple server instances. Room membership is tracked in Redis Sets.
        </p>
        <CodeBlock language="python" filename="redis.py">{`from aquilia.sockets import AquilaSockets, RedisAdapter

sockets = AquilaSockets(
    adapter=RedisAdapter(
        url="redis://localhost:6379/0",
        channel_prefix="ws:",
        pool_size=10,
    ),
)

# When Server A broadcasts to room "chat:general":
# 1. Publishes to Redis channel "ws:chat:general"
# 2. Server B, C, etc. receive and forward to their local connections`}</CodeBlock>
      </section>

      {/* Custom Adapter */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Adapter</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Subclass <code className="text-aquilia-400">Adapter</code> to integrate with any message broker.
        </p>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.sockets import Adapter

class NATSAdapter(Adapter):
    def __init__(self, nats_url: str):
        self.url = nats_url

    async def initialize(self):
        """Connect to NATS."""
        ...

    async def publish(self, channel: str, message: bytes):
        """Publish a message to all instances."""
        ...

    async def subscribe(self, channel: str, callback):
        """Subscribe to receive messages from other instances."""
        ...

    async def join_room(self, room: str, connection_id: str):
        """Track room membership."""
        ...

    async def leave_room(self, room: str, connection_id: str):
        """Remove room membership."""
        ...

    async def get_room_members(self, room: str) -> set[str]:
        """Get all connection IDs in a room."""
        ...

    async def shutdown(self):
        """Disconnect from NATS."""
        ...`}</CodeBlock>
      </section>
    </div>
  )
}
