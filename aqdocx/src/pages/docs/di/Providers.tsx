import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DIProviders() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Providers</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Providers are the building blocks of the DI system. Each provider knows how to create one type of service instance. Aquilia ships 8 provider types in <code className="text-aquilia-500">aquilia/di/providers.py</code>, all implementing the <code className="text-aquilia-500">Provider</code> protocol with <code className="text-aquilia-500">__slots__</code> for memory efficiency.
        </p>
      </div>

      {/* ClassProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}><p className="text-aquilia-500">ClassProvider</p></h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The default provider type. Instantiates a class by auto-resolving constructor dependencies via <code className="text-aquilia-500">inspect.signature()</code> and type hints. Supports <code className="text-aquilia-500">Annotated[Type, Inject(...)]</code> for tagged dependencies and the <code className="text-aquilia-500">async_init()</code> convention for post-construction async initialization.
        </p>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Extraction</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">_extract_dependencies()</code> inspects the class constructor at registration time:
        </p>
        <ol className={`list-decimal pl-6 mb-4 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <li>Calls <code className="text-aquilia-500">inspect.signature(cls.__init__)</code> to get parameter list</li>
          <li>Skips <code className="text-aquilia-500">self</code> and bare <code className="text-aquilia-500">*args</code>/<code className="text-aquilia-500">**kwargs</code></li>
          <li>For each parameter, checks the type annotation</li>
          <li>If the annotation is <code className="text-aquilia-500">Annotated[Type, Inject(tag="...")]</code>, extracts both the type and the tag</li>
          <li>Plain type hints become untagged dependencies</li>
        </ol>

        <CodeBlock language="python" filename="ClassProvider Usage">{`from aquilia.di.providers import ClassProvider
from aquilia.di import Inject
from typing import Annotated

class OrderService:
    def __init__(
        self,
        repo: OrderRepository,                              # Untagged dep
        cache: Annotated[CacheBackend, Inject(tag="redis")], # Tagged dep
        logger: Annotated[Logger, Inject(optional=True)],    # Optional dep
    ):
        self.repo = repo
        self.cache = cache
        self.logger = logger
    
    async def async_init(self):
        """Called after __init__ if present. Perfect for async setup."""
        await self.cache.ping()

# Create provider manually (usually done by Registry)
provider = ClassProvider(
    cls=OrderService,
    scope="request",
    name="OrderService",
    tags=(),
)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Instantiation Flow</h3>
        <div className="mb-8">
          <ol className={`list-decimal pl-6 space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Iterate extracted dependencies, resolve each via <code className="text-aquilia-500">ctx.container.resolve_async()</code></li>
            <li>Check <code className="text-aquilia-500">ctx.in_cycle(dep_token)</code> — if True, raise or use LazyProxy</li>
            <li>Call <code className="text-aquilia-500">cls(**resolved_deps)</code></li>
            <li>If <code className="text-aquilia-500">hasattr(instance, 'async_init')</code>, call <code className="text-aquilia-500">await instance.async_init()</code></li>
            <li>Return the fully-initialized instance</li>
          </ol>
        </div>
      </section>

      {/* FactoryProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500">FactoryProvider</code></h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Calls a sync or async factory function to create the service instance. Dependencies are auto-resolved from the factory's parameter signature, just like <code className="text-aquilia-500">ClassProvider</code>. Use this when construction logic doesn't fit a simple <code className="text-aquilia-500">__init__</code>.
        </p>
        <CodeBlock language="python" filename="FactoryProvider Usage">{`from aquilia.di.providers import FactoryProvider

async def create_database_pool(config: AppConfig) -> DatabasePool:
    """Factory with auto-resolved dependencies."""
    pool = await asyncpg.create_pool(
        dsn=config.database_url,
        min_size=config.pool_min,
        max_size=config.pool_max,
    )
    return pool

provider = FactoryProvider(
    factory=create_database_pool,
    token=DatabasePool,
    scope="singleton",
    name="create_database_pool",
)

# Using the @factory decorator (preferred):
from aquilia.di import factory

@factory(scope="singleton")
async def create_database_pool(config: AppConfig) -> DatabasePool:
    pool = await asyncpg.create_pool(dsn=config.database_url)
    return pool`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-400' : 'text-blue-800'}`}>
            <strong>Sync vs Async:</strong> The factory function can be either sync or async. If it's a coroutine function (<code className="text-aquilia-500">asyncio.iscoroutinefunction</code>), the provider awaits the result. Otherwise it calls synchronously.
          </p>
        </div>
      </section>

      {/* ValueProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ValueProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Returns a pre-built constant value on every resolution. No dependency resolution or instantiation — just returns the bound value. Used for configuration objects, external resources initialized outside the DI system, and test mocks.
        </p>
        <CodeBlock language="python" filename="ValueProvider Usage">{`from aquilia.di.providers import ValueProvider

# Pre-built config object
config = AppConfig.from_env()
provider = ValueProvider(
    value=config,
    token=AppConfig,
    name="AppConfig",
)

# Pre-initialized external resource
redis = aioredis.from_url("redis://localhost")
provider = ValueProvider(value=redis, token=aioredis.Redis, name="redis")

# Equivalent to container.register_instance():
container.register_instance(AppConfig, config, scope="singleton")`}</CodeBlock>
      </section>

      {/* PoolProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PoolProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Manages an <code className="text-aquilia-500">asyncio.Queue</code>-based object pool with configurable ordering (FIFO/LIFO) and maximum size. Objects are acquired via <code className="text-aquilia-500">instantiate()</code> and returned to the pool via <code className="text-aquilia-500">release()</code>. On shutdown, all pooled objects are drained and finalized.
        </p>
        <CodeBlock language="python" filename="PoolProvider Usage">{`from aquilia.di.providers import PoolProvider

# Pool of database connections
provider = PoolProvider(
    factory=create_db_connection,
    token=DatabaseConnection,
    scope="pooled",
    name="db_pool",
    max_size=10,     # Maximum pool size
    order="fifo",    # FIFO (default) or "lifo"
)

# Lazy pool creation — objects created on first acquire
# Pool grows up to max_size, then blocks on acquire until released

# Usage in a service:
class OrderProcessor:
    async def process(self, container):
        # Acquire from pool
        conn = await container.resolve_async(DatabaseConnection)
        try:
            await conn.execute("INSERT INTO orders ...")
        finally:
            # Return to pool
            provider = container._lookup_provider(...)
            await provider.release(conn)

# Shutdown drains the pool:
await container.shutdown()
# → All pooled objects finalized`}</CodeBlock>

        <div className="overflow-x-auto mt-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Parameter</th>
              <th className="text-left py-3 pr-4">Type</th>
              <th className="text-left py-3">Description</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['factory', 'Callable', 'Factory function to create pool objects.'],
                ['max_size', 'int', 'Maximum number of objects in the pool.'],
                ['order', '"fifo" | "lifo"', 'Queue ordering strategy.'],
                ['release(instance)', 'async method', 'Return an instance to the pool queue.'],
                ['shutdown()', 'async method', 'Drain queue and finalize all pooled objects.'],
              ].map(([param, type_, desc], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{param}</code></td>
                  <td className="py-3 pr-4"><code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{type_}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* AliasProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AliasProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aliases one token to another. When resolved, it delegates to the target token's provider. Useful for interface binding, legacy token migration, or providing multiple names for the same service.
        </p>
        <CodeBlock language="python" filename="AliasProvider Usage">{`from aquilia.di.providers import AliasProvider

# Alias an interface to its implementation
alias = AliasProvider(
    token=IUserRepo,           # The alias token
    target_token=PostgresUserRepo,  # The real provider
    scope="app",
    name="IUserRepo_alias",
)

# Now resolving IUserRepo returns the PostgresUserRepo instance:
repo = await container.resolve_async(IUserRepo)
# → Same as: await container.resolve_async(PostgresUserRepo)`}</CodeBlock>
      </section>

      {/* LazyProxyProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LazyProxyProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Creates a dynamic proxy class that breaks circular dependency cycles. The proxy defers all attribute access and method calls to the real instance, which is resolved lazily on first access. Enabled by setting <code className="text-aquilia-500">allow_lazy=True</code> in the manifest entry.
        </p>
        <CodeBlock language="python" filename="LazyProxyProvider Internals">{`from aquilia.di.providers import LazyProxyProvider

# Created automatically by Registry when a cycle involves allow_lazy=True providers

# The proxy class generated at runtime:
class _LazyProxy:
    """Dynamic proxy — defers to real instance on first access."""
    
    def __getattr__(self, name):
        # Resolve the real instance on first attribute access
        if self._real_instance is None:
            self._real_instance = self._resolve()
        return getattr(self._real_instance, name)
    
    def __call__(self, *args, **kwargs):
        if self._real_instance is None:
            self._real_instance = self._resolve()
        return self._real_instance(*args, **kwargs)

# In manifest:
users = Manifest(
    name="users",
    services=[
        {"class": ServiceA, "allow_lazy": True},  # Can break cycles
        {"class": ServiceB},
    ],
)`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'}`}>
          <p className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-800'}`}>
            <strong>When to use:</strong> Only when you have a genuine circular dependency that can't be resolved by restructuring. The proxy adds a layer of indirection — each attribute access goes through <code className="text-aquilia-500">__getattr__</code>. Prefer extracting an interface or using events to break cycles.
          </p>
        </div>
      </section>

      {/* ScopedProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ScopedProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Wraps an inner provider with a different scope. All other behavior (instantiation, shutdown) is delegated to the inner provider. The meta is replaced with the overridden scope.
        </p>
        <CodeBlock language="python" filename="ScopedProvider Usage">{`from aquilia.di.providers import ScopedProvider, ClassProvider

# Take a normally app-scoped provider and make it request-scoped
inner = ClassProvider(UserCache, scope="app", name="UserCache")
scoped = ScopedProvider(inner=inner, scope="request")

# scoped.meta.scope == "request"
# scoped.instantiate(ctx) → inner.instantiate(ctx)
# scoped.shutdown() → inner.shutdown()`}</CodeBlock>
      </section>

      {/* SerializerProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SerializerProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A specialized provider for Aquilia's serializer system. Creates <code className="text-aquilia-500">Serializer</code> instances with full request context. During instantiation, it:
        </p>
        <ol className={`list-decimal pl-6 mb-4 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <li>Extracts the request from the resolution context</li>
          <li>Auto-parses the request body (JSON via <code className="text-aquilia-500">await request.json()</code> or form data via <code className="text-aquilia-500">await request.form()</code>)</li>
          <li>Builds a serializer context dict with <code className="text-aquilia-500">request</code>, <code className="text-aquilia-500">container</code>, and <code className="text-aquilia-500">identity</code></li>
          <li>Instantiates the serializer class with <code className="text-aquilia-500">data=parsed_body</code> and <code className="text-aquilia-500">context=ctx_dict</code></li>
        </ol>
        <CodeBlock language="python" filename="SerializerProvider Usage">{`from aquilia.di.providers import SerializerProvider

provider = SerializerProvider(
    serializer_cls=CreateUserSerializer,
    token=CreateUserSerializer,
    scope="request",
    name="CreateUserSerializer",
)

# In a controller, the serializer is resolved with request context:
@post("/users")
async def create_user(self, req):
    serializer = await req.container.resolve_async(CreateUserSerializer)
    # serializer.data contains the parsed request body
    # serializer.context has {"request": req, "container": ..., "identity": ...}
    if serializer.is_valid():
        user = await serializer.save()
        return Response.json(user, status=201)`}</CodeBlock>
      </section>

      {/* Creating Custom Providers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating Custom Providers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implement the <code className="text-aquilia-500">Provider</code> protocol to create custom provider types:
        </p>
        <CodeBlock language="python" filename="Custom Provider">{`from aquilia.di.core import Provider, ProviderMeta, ResolveCtx

class EnvironmentProvider:
    """Provider that reads values from environment variables."""
    __slots__ = ("_meta", "_env_key", "_default")
    
    def __init__(self, env_key: str, token: str, default=None):
        self._meta = ProviderMeta(
            name=f"env:{env_key}",
            token=token,
            scope="singleton",
            tags=(),
            module=__name__,
            qualname=f"EnvironmentProvider({env_key})",
            line=None,
            version=None,
            allow_lazy=False,
        )
        self._env_key = env_key
        self._default = default
    
    @property
    def meta(self) -> ProviderMeta:
        return self._meta
    
    async def instantiate(self, ctx: ResolveCtx):
        import os
        value = os.environ.get(self._env_key, self._default)
        if value is None:
            raise ValueError(f"Environment variable {self._env_key} not set")
        return value
    
    async def shutdown(self):
        pass  # Nothing to clean up

# Register:
container.register(EnvironmentProvider("DATABASE_URL", "database_url"))`}</CodeBlock>
      </section>

      {/* Provider Selection Logic */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Provider Selection Logic</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When the Registry processes a manifest service entry, it selects the appropriate provider type:
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Condition</th>
              <th className="text-left py-3">Provider Created</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['Entry is a class with __di_factory__ attribute', 'FactoryProvider'],
                ['Entry is a callable (function)', 'FactoryProvider'],
                ['Entry is a class (standard)', 'ClassProvider'],
                ['Entry has "allow_lazy": True and is in a cycle', 'LazyProxyProvider wrapping ClassProvider'],
                ['Entry has "scope" override', 'ScopedProvider wrapping the inner provider'],
                ['Entry is a pre-built value', 'ValueProvider'],
                ['Entry is a Serializer subclass', 'SerializerProvider'],
              ].map(([condition, provider], i) => (
                <tr key={i}>
                  <td className={`py-3 pr-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{condition}</td>
                  <td className="py-3"><code className="text-aquilia-500 text-xs">{provider}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/container" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> Container
        </Link>
        <Link to="/docs/di/scopes" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          Scopes <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}