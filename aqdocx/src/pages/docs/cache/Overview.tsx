import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Zap } from 'lucide-react'

export function CacheOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Zap className="w-4 h-4" />
          Advanced / Cache
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Cache System
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          AquilaCache is a production-grade, async-first caching layer with multiple backends (Memory, Redis, Composite L1/L2), pluggable serializers, DI integration, fault awareness, and declarative decorators.
        </p>
      </div>

      {/* Backends */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Backends</h2>
        <div className="space-y-3">
          {[
            { name: 'MemoryBackend', desc: 'In-process LRU/LFU/TTL cache. Fast, zero-latency. Ideal for single-instance deployments and development.', config: 'max_size=1000, eviction="lru", default_ttl=300' },
            { name: 'RedisBackend', desc: 'Redis-backed distributed cache. Supports clustering, pub/sub invalidation, and atomic operations.', config: 'url="redis://localhost:6379", db=0, prefix="aq:"' },
            { name: 'CompositeBackend', desc: 'Two-tier L1 (memory) + L2 (Redis) cache. Checks L1 first, falls back to L2, promotes on hit.', config: 'l1=MemoryBackend(...), l2=RedisBackend(...)' },
            { name: 'NullBackend', desc: 'No-op backend for testing and disabled-cache scenarios. Always misses.', config: '' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
              {item.config && <p className={`text-xs mt-2 font-mono ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>{item.config}</p>}
            </div>
          ))}
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.cache(
            backend="memory",          # "memory" | "redis" | "composite"
            max_size=5000,             # Max entries (memory backend)
            default_ttl=300,           # Default TTL in seconds
            eviction="lru",            # "lru" | "lfu" | "ttl"
            serializer="json",         # "json" | "msgpack" | "pickle"
            key_builder="default",     # "default" | "hash"
            redis_url="redis://localhost:6379/0",
            namespace="myapp",
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* CacheService */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CacheService API</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">CacheService</code> is injected via DI and provides the primary interface:
        </p>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Inject
from aquilia.cache import CacheService


class ProductController(Controller):
    prefix = "/api/products"

    @Inject()
    def __init__(self, cache: CacheService):
        self.cache = cache

    @Get("/")
    async def list_products(self, ctx):
        # Try cache first, compute and store on miss
        products = await self.cache.get_or_set(
            "products:all",
            lambda: Product.objects.all().to_list(),
            ttl=120,
        )
        return ctx.json({"products": products})

    @Get("/{id:int}")
    async def get_product(self, ctx, id: int):
        # Simple get/set pattern
        cached = await self.cache.get(f"product:{id}")
        if cached:
            return ctx.json(cached)

        product = await Product.objects.get(id=id)
        data = product.to_dict()
        await self.cache.set(f"product:{id}", data, ttl=300)
        return ctx.json(data)`}</CodeBlock>

        <div className={`mt-6 ${boxClass}`}>
          <h3 className={`font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full CacheService API</h3>
          <div className={`space-y-1 text-sm font-mono ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <p><span className="text-aquilia-500">get</span>(key) → value or None</p>
            <p><span className="text-aquilia-500">set</span>(key, value, ttl=None)</p>
            <p><span className="text-aquilia-500">delete</span>(key)</p>
            <p><span className="text-aquilia-500">exists</span>(key) → bool</p>
            <p><span className="text-aquilia-500">get_or_set</span>(key, default_factory, ttl=None) → value</p>
            <p><span className="text-aquilia-500">get_many</span>(*keys) → dict</p>
            <p><span className="text-aquilia-500">set_many</span>(mapping, ttl=None)</p>
            <p><span className="text-aquilia-500">delete_many</span>(*keys)</p>
            <p><span className="text-aquilia-500">clear</span>(namespace=None)</p>
            <p><span className="text-aquilia-500">stats</span>() → CacheStats</p>
          </div>
        </div>
      </section>

      {/* Decorators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Decorators</h2>
        <CodeBlock language="python" filename="decorators.py">{`from aquilia.cache import cached, cache_aside, invalidate


# @cached — Memoize function results
@cached(ttl=60, namespace="api")
async def get_popular_products():
    return await Product.objects.filter(popular=True).to_list()


# @cache_aside — Read-through + write-through
@cache_aside(ttl=300, key_func=lambda id: f"product:{id}")
async def get_product(id: int):
    return await Product.objects.get(id=id)


# @invalidate — Clear cache entries on mutation
@invalidate("products:all", "products:popular")
async def create_product(data: dict):
    return await Product.objects.create(**data)


# Custom key function
@cached(ttl=120, key_func=lambda ctx: f"user:{ctx.identity.id}:feed")
async def get_user_feed(ctx):
    return await Feed.objects.filter(user_id=ctx.identity.id).to_list()`}</CodeBlock>
      </section>

      {/* CacheMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response Caching Middleware</h2>
        <CodeBlock language="python" filename="middleware.py">{`from aquilia.cache import CacheMiddleware

# Automatically caches GET responses with ETag support
workspace = Workspace(
    middleware=[
        CacheMiddleware(
            ttl=60,
            include_paths=["/api/products/*"],
            exclude_paths=["/api/products/*/edit"],
            vary_on=["Authorization"],  # Vary cache by header
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/faults/engine" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Fault Engine
        </Link>
        <Link to="/docs/websockets" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          WebSockets <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
