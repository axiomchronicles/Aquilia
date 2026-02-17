import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Gauge } from 'lucide-react'

export function CacheService() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Gauge className="w-4 h-4" />
          Cache / CacheService
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          CacheService
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">CacheService</code> is the primary DI-injectable interface for all caching operations. It wraps a backend, handles serialization, key building, and integrates with the fault system.
        </p>
      </div>

      {/* Core API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core API</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Method</th>
                  <th className="text-left pb-3 font-semibold">Returns</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['get(key, default?)', 'T | None', 'Retrieve a cached value by key'],
                  ['set(key, value, ttl?)', 'None', 'Store a value with optional TTL in seconds'],
                  ['delete(key)', 'bool', 'Remove a key, returns True if existed'],
                  ['exists(key)', 'bool', 'Check if key exists without fetching'],
                  ['get_or_set(key, factory, ttl?)', 'T', 'Get existing or call factory to compute and cache'],
                  ['get_many(keys)', 'dict[str, T]', 'Batch get multiple keys'],
                  ['set_many(mapping, ttl?)', 'None', 'Batch set multiple key-value pairs'],
                  ['delete_many(keys)', 'int', 'Batch delete, returns count removed'],
                  ['clear(namespace?)', 'None', 'Clear all keys or a namespace'],
                  ['stats()', 'CacheStats', 'Return hit/miss/eviction statistics'],
                  ['initialize()', 'None', 'Lifecycle: open connections, warm up'],
                  ['shutdown()', 'None', 'Lifecycle: flush and close connections'],
                ].map(([method, ret, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{method}</td>
                    <td className="py-2 font-mono text-xs">{ret}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* DI Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Inject <code className="text-aquilia-400">CacheService</code> into controllers or services via the DI container.
        </p>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, GET
from aquilia.cache import CacheService

class ProductController(Controller):
    prefix = "/products"

    def __init__(self, cache: CacheService):
        self.cache = cache

    @GET("/{id}")
    async def get_product(self, ctx, id: int):
        # get_or_set: cache hit → return, miss → call factory
        product = await self.cache.get_or_set(
            f"product:{id}",
            lambda: self.repo.find(id),
            ttl=300,
        )
        return product`}</CodeBlock>
      </section>

      {/* CacheStats */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CacheStats</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">CacheStats</code> provides observability into cache performance.
        </p>
        <CodeBlock language="python" filename="stats.py">{`stats = await cache.stats()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2%}")
print(f"Evictions: {stats.evictions}")
print(f"Size: {stats.current_size} / {stats.max_size}")`}</CodeBlock>
      </section>

      {/* Key Building */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Builders</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides deterministic, collision-free key generation via <code className="text-aquilia-400">DefaultKeyBuilder</code> and <code className="text-aquilia-400">HashKeyBuilder</code>.
        </p>
        <CodeBlock language="python" filename="keys.py">{`from aquilia.cache import DefaultKeyBuilder, HashKeyBuilder

# DefaultKeyBuilder: namespace:prefix:key
builder = DefaultKeyBuilder(namespace="myapp")
key = builder.build("user", user_id)  # "myapp:user:42"

# HashKeyBuilder: namespace:sha256(key) — for long/complex keys
hbuilder = HashKeyBuilder(namespace="myapp")
key = hbuilder.build("search", complex_query)  # "myapp:a1b2c3..."`}</CodeBlock>
      </section>

      {/* Fault Types */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Faults</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'CacheFault', desc: 'Base cache fault' },
            { name: 'CacheMissFault', desc: 'Key not found in cache' },
            { name: 'CacheConnectionFault', desc: 'Backend connection failure' },
            { name: 'CacheSerializationFault', desc: 'Serialization/deserialization error' },
            { name: 'CacheCapacityFault', desc: 'Cache is at capacity' },
            { name: 'CacheBackendFault', desc: 'Backend-specific error' },
            { name: 'CacheConfigFault', desc: 'Invalid configuration' },
            { name: 'CacheStampedeFault', desc: 'Thundering herd detected' },
            { name: 'CacheHealthFault', desc: 'Health check failure' },
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
