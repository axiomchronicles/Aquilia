import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { HardDrive } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CacheBackends() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <HardDrive className="w-4 h-4" />
          Cache / Backends
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Cache Backends
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides four cache backends. All implement the <code className="text-aquilia-400">CacheBackend</code> abstract interface, making them interchangeable.
        </p>
      </div>

      {/* Backend Comparison */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Backend Comparison</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Backend</th>
                  <th className="text-left pb-3 font-semibold">Persistence</th>
                  <th className="text-left pb-3 font-semibold">Distributed</th>
                  <th className="text-left pb-3 font-semibold">Eviction</th>
                  <th className="text-left pb-3 font-semibold">Best For</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['MemoryBackend', 'No', 'No', 'LRU/LFU/TTL', 'Dev, single-process, tests'],
                  ['RedisBackend', 'Yes', 'Yes', 'Redis-native', 'Production, multi-process'],
                  ['CompositeBackend', 'Mixed', 'Mixed', 'Per-layer', 'L1 memory + L2 Redis'],
                  ['NullBackend', 'No', 'No', 'N/A', 'Testing, disabled cache'],
                ].map(([name, persist, dist, evict, best], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{name}</td>
                    <td className="py-2 text-xs">{persist}</td>
                    <td className="py-2 text-xs">{dist}</td>
                    <td className="py-2 text-xs">{evict}</td>
                    <td className="py-2 text-xs">{best}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* MemoryBackend */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MemoryBackend</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          In-process cache with configurable eviction policy (LRU, LFU, or TTL-only). Zero external dependencies.
        </p>
        <CodeBlock language="python" filename="memory.py">{`from aquilia.cache import MemoryBackend, CacheService, EvictionPolicy

backend = MemoryBackend(
    max_size=10_000,                   # Max entries
    eviction_policy=EvictionPolicy.LRU, # LRU | LFU | TTL
    default_ttl=300,                   # 5 minutes
)

cache = CacheService(backend=backend)
await cache.initialize()`}</CodeBlock>
      </section>

      {/* RedisBackend */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RedisBackend</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Production-ready Redis backend with connection pooling, pipeline support, and cluster awareness.
        </p>
        <CodeBlock language="python" filename="redis.py">{`from aquilia.cache import RedisBackend, CacheService

backend = RedisBackend(
    url="redis://localhost:6379/0",
    pool_size=20,
    prefix="myapp:",
    socket_timeout=5.0,
    retry_on_timeout=True,
)

cache = CacheService(backend=backend)
await cache.initialize()`}</CodeBlock>
      </section>

      {/* CompositeBackend */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CompositeBackend (L1/L2)</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Two-tier caching: fast in-memory L1 backed by persistent L2 (Redis). On miss in L1, falls through to L2 and promotes the value back to L1.
        </p>
        <CodeBlock language="python" filename="composite.py">{`from aquilia.cache import (
    CompositeBackend, MemoryBackend, RedisBackend, CacheService,
)

l1 = MemoryBackend(max_size=1_000, default_ttl=60)
l2 = RedisBackend(url="redis://localhost:6379/0")

backend = CompositeBackend(l1=l1, l2=l2)
cache = CacheService(backend=backend)

# Reads: L1 → L2 → miss
# Writes: L1 + L2 simultaneously`}</CodeBlock>
      </section>

      {/* NullBackend */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>NullBackend</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A no-op backend that never caches anything. Useful for tests and environments where caching should be disabled.
        </p>
        <CodeBlock language="python" filename="null.py">{`from aquilia.cache import NullBackend, CacheService

cache = CacheService(backend=NullBackend())
# All gets return None, all sets are no-ops`}</CodeBlock>
      </section>

      {/* Serializers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Serializers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Values are serialized before storage. Three serializer implementations are available.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'JsonCacheSerializer', desc: 'JSON — human-readable, cross-language, largest size' },
            { name: 'MsgpackCacheSerializer', desc: 'MessagePack — compact binary, fast, smaller size' },
            { name: 'PickleCacheSerializer', desc: 'Pickle — full Python object support, not cross-language' },
          ].map((s, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{s.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CacheBackend Interface */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Backend</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implement <code className="text-aquilia-400">CacheBackend</code> to create your own backend.
        </p>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.cache import CacheBackend, CacheEntry, CacheStats

class DynamoBackend(CacheBackend):
    async def get(self, key: str) -> CacheEntry | None: ...
    async def set(self, key: str, entry: CacheEntry) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    async def clear(self) -> None: ...
    async def stats(self) -> CacheStats: ...
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}