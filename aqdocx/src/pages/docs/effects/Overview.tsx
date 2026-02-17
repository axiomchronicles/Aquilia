import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react'

export function EffectsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Sparkles className="w-4 h-4" />
          Advanced / Effects
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Effect System
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Effects are typed capability tokens that handlers declare to express side-effects (database transactions, cache, queues). Effect providers implement the actual resource acquisition and release, enabling compile-time visibility of what each handler needs.
        </p>
      </div>

      {/* How Effects Work */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How Effects Work</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 600 120" className="w-full" fill="none">
            <rect x="10" y="30" width="130" height="50" rx="10" stroke={isDark ? '#22c55e' : '#16a34a'} strokeWidth="2" fill={isDark ? '#22c55e10' : '#16a34a08'} />
            <text x="75" y="60" textAnchor="middle" fill={isDark ? '#4ade80' : '#16a34a'} fontSize="12" fontWeight="bold">Effect Token</text>
            <text x="75" y="73" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="9">DBTx["read"]</text>
            <path d="M140 55 L190 55" stroke={isDark ? '#4ade80' : '#16a34a'} strokeWidth="1.5" markerEnd="url(#ea)" />
            <rect x="190" y="30" width="130" height="50" rx="10" stroke={isDark ? '#60a5fa' : '#2563eb'} strokeWidth="2" fill={isDark ? '#60a5fa10' : '#2563eb08'} />
            <text x="255" y="60" textAnchor="middle" fill={isDark ? '#93c5fd' : '#2563eb'} fontSize="12" fontWeight="bold">Provider</text>
            <text x="255" y="73" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="9">acquire() / release()</text>
            <path d="M320 55 L370 55" stroke={isDark ? '#60a5fa' : '#2563eb'} strokeWidth="1.5" markerEnd="url(#ea)" />
            <rect x="370" y="30" width="130" height="50" rx="10" stroke={isDark ? '#fbbf24' : '#d97706'} strokeWidth="2" fill={isDark ? '#fbbf2410' : '#d9770608'} />
            <text x="435" y="60" textAnchor="middle" fill={isDark ? '#fde047' : '#d97706'} fontSize="12" fontWeight="bold">Resource</text>
            <text x="435" y="73" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="9">DB connection, cache, etc.</text>
            <defs><marker id="ea" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill={isDark ? '#4ade80' : '#16a34a'} /></marker></defs>
          </svg>
        </div>
      </section>

      {/* Built-in Effects */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Built-in Effects</h2>
        <div className="space-y-3">
          {[
            { name: 'DBTx', kind: 'EffectKind.DB', desc: 'Database transaction effect. Modes: "read" (read-only), "write" (read-write with commit/rollback).' },
            { name: 'CacheEffect', kind: 'EffectKind.CACHE', desc: 'Cache namespace effect. Acquires a cache handle scoped to a namespace.' },
            { name: 'QueueEffect', kind: 'EffectKind.QUEUE', desc: 'Message queue effect. Acquires a publisher for a specific topic.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <div className="flex items-center gap-3">
                <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
                <span className={`text-xs px-2 py-0.5 rounded-full ${isDark ? 'bg-zinc-800 text-gray-400' : 'bg-gray-100 text-gray-500'}`}>{item.kind}</span>
              </div>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using Effects</h2>
        <CodeBlock language="python" filename="effects_usage.py">{`from aquilia.effects import DBTx, CacheEffect, QueueEffect


class OrderController(Controller):
    prefix = "/api/orders"

    # Declare effects that this handler requires
    effects = [DBTx("write"), CacheEffect("orders")]

    @Post("/")
    async def create_order(self, ctx):
        # The engine acquires resources BEFORE the handler runs:
        #   db_conn = await DBTxProvider.acquire(mode="write")
        #   cache   = await CacheProvider.acquire(mode="orders")

        order = await Order.objects.create(
            customer_id=ctx.identity.id,
            items=await ctx.json(),
        )

        # Invalidate the cache
        await ctx.effects.cache.delete("orders:list")

        return ctx.json(order.to_dict(), status=201)

        # After the handler, the engine releases resources:
        #   await DBTxProvider.release(db_conn, success=True)   → COMMIT
        #   await CacheProvider.release(cache)`}</CodeBlock>
      </section>

      {/* Custom Providers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Effect Providers</h2>
        <CodeBlock language="python" filename="custom_provider.py">{`from aquilia.effects import Effect, EffectKind, EffectProvider


# Define a custom effect
class StorageEffect(Effect):
    """Cloud storage effect."""
    def __init__(self, bucket: str = "default"):
        super().__init__("Storage", mode=bucket, kind=EffectKind.STORAGE)


# Implement the provider
class S3StorageProvider(EffectProvider):
    def __init__(self, aws_region: str, bucket: str):
        self.region = aws_region
        self.bucket = bucket
        self.client = None

    async def initialize(self):
        """Called once at startup."""
        import boto3
        self.client = boto3.client("s3", region_name=self.region)

    async def acquire(self, mode=None):
        """Called per-request — return a scoped handle."""
        bucket = mode or self.bucket
        return S3Handle(self.client, bucket)

    async def release(self, resource, success=True):
        """Called after request completes."""
        pass  # S3 connections are stateless

    async def finalize(self):
        """Called at shutdown."""
        self.client = None`}</CodeBlock>
      </section>

      {/* Effect Lifecycle */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Effect Lifecycle</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Phase</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>When</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { phase: 'Startup', method: 'initialize()', when: 'Server boot — one-time setup (e.g., create connection pool)' },
                { phase: 'Request', method: 'acquire(mode)', when: 'Before handler runs — get scoped resource' },
                { phase: 'Post-Request', method: 'release(resource, success)', when: 'After handler — commit/rollback, return to pool' },
                { phase: 'Shutdown', method: 'finalize()', when: 'Server shutdown — cleanup resources' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className={`py-3 px-4 font-bold text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{row.phase}</td>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.method}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/aquilary" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Aquilary
        </Link>
        <Link to="/docs/faults" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Faults <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
