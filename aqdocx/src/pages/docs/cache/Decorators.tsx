import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Gauge } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CacheDecorators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Gauge className="w-4 h-4" />
          Cache / Decorators
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Cache Decorators
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Declarative caching decorators that wrap async functions with automatic cache get/set, cache-aside patterns, and targeted invalidation.
        </p>
      </div>

      {/* @cached */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@cached</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The primary decorator. On first call, executes the function and caches the result. Subsequent calls return the cached value until TTL expires.
        </p>
        <CodeBlock language="python" filename="cached.py">{`from aquilia.cache import cached

@cached(ttl=60, namespace="api")
async def get_popular_products():
    """Cached for 60 seconds in the 'api' namespace."""
    return await db.fetch_all(
        "SELECT * FROM products ORDER BY views DESC LIMIT 20"
    )

# With custom key function
@cached(ttl=300, key=lambda user_id: f"user:{user_id}")
async def get_user_profile(user_id: int):
    return await User.objects.get(id=user_id)

# First call: executes function, caches result
profile = await get_user_profile(42)

# Subsequent calls within TTL: returns cached
profile = await get_user_profile(42)  # instant, no DB query`}</CodeBlock>
      </section>

      {/* @cache_aside */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@cache_aside</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implements the cache-aside (lazy loading) pattern: check cache first, on miss call the function, then populate the cache. Similar to <code className="text-aquilia-400">@cached</code> but gives you explicit control over the cache key and error handling.
        </p>
        <CodeBlock language="python" filename="aside.py">{`from aquilia.cache import cache_aside

@cache_aside(ttl=120, namespace="products")
async def find_product(product_id: int):
    """
    Cache-aside pattern:
    1. Check cache for key "products:find_product:product_id"
    2. On miss → call this function
    3. Store result in cache
    4. Return result
    """
    return await Product.objects.get(id=product_id)`}</CodeBlock>
      </section>

      {/* @invalidate */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@invalidate</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Invalidates cache entries when data changes. Apply it to write operations to ensure stale data is purged.
        </p>
        <CodeBlock language="python" filename="invalidate.py">{`from aquilia.cache import cached, invalidate

@cached(ttl=300, namespace="products")
async def get_product(product_id: int):
    return await Product.objects.get(id=product_id)

@invalidate(namespace="products", key=lambda pid, **kw: f"get_product:{pid}")
async def update_product(product_id: int, data: dict):
    """Updating a product automatically invalidates its cache entry."""
    product = await Product.objects.get(id=product_id)
    for k, v in data.items():
        setattr(product, k, v)
    await product.save()
    return product`}</CodeBlock>
      </section>

      {/* CacheMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CacheMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          HTTP-level response caching middleware with ETag support and conditional request handling.
        </p>
        <CodeBlock language="python" filename="middleware.py">{`from aquilia.cache import CacheMiddleware

# In your workspace config
workspace = WorkspaceBuilder("myapp")
workspace.middleware([
    CacheMiddleware(
        default_ttl=60,
        methods=["GET", "HEAD"],
        exclude_paths=["/api/auth/*", "/api/ws/*"],
        vary_headers=["Accept", "Authorization"],
    ),
])`}</CodeBlock>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration via Integration</h2>
        <CodeBlock language="python" filename="config.py">{`from aquilia.config_builders import WorkspaceBuilder, Integration

workspace = WorkspaceBuilder("myapp")
workspace.integrations([
    Integration.cache(
        backend="redis",
        url="redis://localhost:6379/0",
        serializer="msgpack",
        default_ttl=300,
        max_size=50_000,
        key_prefix="myapp:",
    ),
])`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}