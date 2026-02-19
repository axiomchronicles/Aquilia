import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Workflow } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function EffectsCacheEffect() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Workflow className="w-4 h-4" />
          Effects / Cache Effect
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Cache Effect
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">CacheEffect</code> represents a cache namespace capability. The <code className="text-aquilia-400">CacheProvider</code> wraps the full <code className="text-aquilia-400">CacheService</code> to provide per-namespace handles with get/set/delete operations.
        </p>
      </div>

      {/* CacheEffect Token */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Effect Token</h2>
        <CodeBlock language="python" filename="token.py">{`from aquilia.effects import CacheEffect, EffectKind

# Declare a cache effect for a namespace
user_cache = CacheEffect(namespace="users")
product_cache = CacheEffect(namespace="products")

# Default namespace
default_cache = CacheEffect()  # namespace="default"

print(user_cache.name)     # "Cache"
print(user_cache.kind)     # EffectKind.CACHE
print(user_cache.mode)     # "users"`}</CodeBlock>
      </section>

      {/* CacheProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CacheProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">CacheProvider</code> delegates to a <code className="text-aquilia-400">CacheService</code> when available, otherwise falls back to an in-memory dict. This makes it usable in both production and tests.
        </p>
        <CodeBlock language="python" filename="provider.py">{`from aquilia.effects import CacheProvider
from aquilia.cache import CacheService, MemoryBackend

# With full CacheService (production)
cache_svc = CacheService(backend=MemoryBackend())
provider = CacheProvider("memory", cache_service=cache_svc)

# Without CacheService (testing fallback)
provider = CacheProvider("memory")  # uses internal dict

# Register
registry.register("Cache", provider)
await registry.initialize_all()`}</CodeBlock>
      </section>

      {/* Cache Handles */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Handles</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When you acquire a cache effect, you get a handle scoped to the namespace.
        </p>
        <CodeBlock language="python" filename="handle.py">{`# Acquire a handle for the "users" namespace
handle = await provider.acquire(mode="users")

# Operations are scoped to the namespace
await handle.set("42", {"name": "Asha", "email": "asha@test.com"})
user = await handle.get("42")     # {"name": "Asha", ...}
await handle.delete("42")

# Release (no-op for cache, but called for consistency)
await provider.release(handle, success=True)`}</CodeBlock>
      </section>

      {/* QueueEffect */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Other Built-in Effects</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia also provides <code className="text-aquilia-400">QueueEffect</code> for message queue capabilities.
        </p>
        <CodeBlock language="python" filename="queue.py">{`from aquilia.effects import QueueEffect

# Queue effect for publishing messages
notifications = QueueEffect(topic="notifications")
analytics = QueueEffect(topic="analytics")

print(notifications.name)   # "Queue"
print(notifications.kind)   # EffectKind.QUEUE
print(notifications.mode)   # "notifications"`}</CodeBlock>
      </section>

      {/* EffectKind */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>EffectKind Enum</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { name: 'DB', desc: 'Database transactions' },
            { name: 'CACHE', desc: 'Cache namespaces' },
            { name: 'QUEUE', desc: 'Message queues' },
            { name: 'HTTP', desc: 'External HTTP calls' },
            { name: 'STORAGE', desc: 'Object storage' },
            { name: 'CUSTOM', desc: 'User-defined effects' },
          ].map((k, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>EffectKind.{k.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{k.desc}</p>
            </div>
          ))}
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}