import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DIDecorators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Decorators</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides 6 decorators and 1 dataclass in <code className="text-aquilia-500">aquilia/di/decorators.py</code> for declarative DI configuration. These decorators attach metadata to classes and functions that the <code className="text-aquilia-500">Registry</code> reads during manifest processing.
        </p>
      </div>

      {/* Inject Dataclass */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Inject</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">Inject</code> is a dataclass used as metadata in <code className="text-aquilia-500">typing.Annotated</code> type hints. It tells the <code className="text-aquilia-500">ClassProvider</code> and <code className="text-aquilia-500">FactoryProvider</code> how to resolve a specific parameter — with a tag, an explicit token, or as optional.
        </p>
        <CodeBlock language="python" filename="Inject Dataclass">{`from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Inject:
    token: Optional[Any] = None     # Explicit resolution token (overrides type hint)
    tag: Optional[str] = None       # Tag for disambiguating multiple providers
    optional: bool = False          # If True, resolves to None instead of raising`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage with Annotated</h3>
        <CodeBlock language="python" filename="Inject in Type Hints">{`from typing import Annotated
from aquilia.di import Inject

class OrderService:
    def __init__(
        self,
        # Standard — resolved by type hint alone
        repo: OrderRepository,
        
        # Tagged — disambiguate between multiple CacheBackend providers
        cache: Annotated[CacheBackend, Inject(tag="redis")],
        
        # Optional — None if not registered
        metrics: Annotated[MetricsClient, Inject(optional=True)],
        
        # Explicit token — override the type hint entirely
        notifier: Annotated[Any, Inject(token="email_notifier")],
    ):
        self.repo = repo
        self.cache = cache
        self.metrics = metrics
        self.notifier = notifier`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-400' : 'text-blue-800'}`}>
            <strong>How it works internally:</strong> <code className="text-aquilia-500">ClassProvider._extract_dependencies()</code> iterates <code className="text-aquilia-500">inspect.signature(cls.__init__)</code> parameters. For each parameter with a <code className="text-aquilia-500">typing.get_type_hints()</code> annotation, it checks if the annotation is <code className="text-aquilia-500">Annotated[T, Inject(...)]</code>. If so, it extracts the token (type T or explicit token), tag, and optional flag.
          </p>
        </div>
      </section>

      {/* inject() factory */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>inject()</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A convenience factory function that creates <code className="text-aquilia-500">Inject</code> instances. Syntactic sugar for <code className="text-aquilia-500">Inject(...)</code>.
        </p>
        <CodeBlock language="python" filename="inject() Factory">{`from aquilia.di import inject

# These are equivalent:
cache: Annotated[CacheBackend, inject(tag="redis")]
cache: Annotated[CacheBackend, Inject(tag="redis")]

# With explicit token:
config: Annotated[Any, inject(token="app_config")]

# Optional:
logger: Annotated[Logger, inject(optional=True)]`}</CodeBlock>
      </section>

      {/* @service */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@service()</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Class decorator that marks a class as a DI service. Attaches three dunder attributes that the Registry reads during manifest processing:
        </p>
        <div className="overflow-x-auto mb-4">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Attribute</th>
              <th className="text-left py-3 pr-4">Type</th>
              <th className="text-left py-3">Description</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['__di_scope__', 'str', 'Service scope: "singleton", "app", "request", "transient", "pooled", "ephemeral"'],
                ['__di_tag__', 'str | None', 'Optional tag for provider disambiguation'],
                ['__di_name__', 'str | None', 'Optional custom name (defaults to class name)'],
              ].map(([attr, type_, desc], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{attr}</code></td>
                  <td className="py-3 pr-4"><code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{type_}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python" filename="@service Examples">{`from aquilia.di import service

# Basic usage — defaults to "app" scope
@service()
class UserRepository:
    def __init__(self, pool: DatabasePool):
        self.pool = pool

# With explicit scope
@service(scope="request")
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# With tag for disambiguation
@service(scope="app", tag="postgres")
class PostgresUserRepo:
    ...

@service(scope="app", tag="mongo")
class MongoUserRepo:
    ...

# With custom name
@service(scope="singleton", name="primary_cache")
class RedisCacheBackend:
    ...

# The decorator returns the class unchanged — only adds attributes:
assert hasattr(UserRepository, "__di_scope__")  # True
assert UserRepository.__di_scope__ == "app"     # True`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-green-500/5 border-green-500/20' : 'bg-green-50 border-green-200'}`}>
          <p className={`text-sm ${isDark ? 'text-green-400' : 'text-green-800'}`}>
            <strong>Alias:</strong> <code className="text-aquilia-500">injectable</code> is an alias for <code className="text-aquilia-500">service</code>. They are interchangeable: <code className="text-aquilia-500">@injectable(scope="request")</code> is identical to <code className="text-aquilia-500">@service(scope="request")</code>.
          </p>
        </div>
      </section>

      {/* @factory */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@factory()</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Function decorator that marks a function as a DI factory. Sets the same three attributes as <code className="text-aquilia-500">@service</code> plus <code className="text-aquilia-500">__di_factory__ = True</code>, which tells the Registry to create a <code className="text-aquilia-500">FactoryProvider</code> instead of a <code className="text-aquilia-500">ClassProvider</code>.
        </p>
        <CodeBlock language="python" filename="@factory Examples">{`from aquilia.di import factory

@factory(scope="singleton")
async def create_database_pool(config: AppConfig) -> DatabasePool:
    """Async factory — dependencies auto-resolved from signature."""
    pool = await asyncpg.create_pool(
        dsn=config.database_url,
        min_size=config.pool_min,
        max_size=config.pool_max,
    )
    return pool

@factory(scope="app")
def create_http_client(config: AppConfig) -> httpx.AsyncClient:
    """Sync factory — also supported."""
    return httpx.AsyncClient(
        base_url=config.api_base_url,
        timeout=config.http_timeout,
    )

# Attributes set:
assert create_database_pool.__di_factory__ == True
assert create_database_pool.__di_scope__ == "singleton"`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-400' : 'text-blue-800'}`}>
            <strong>@service vs @factory:</strong> Use <code className="text-aquilia-500">@service</code> for classes with standard <code className="text-aquilia-500">__init__</code> constructors. Use <code className="text-aquilia-500">@factory</code> when creation requires custom logic, async setup, or the return type differs from the function itself (e.g., a factory function that returns a pool object).
          </p>
        </div>
      </section>

      {/* @provides */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500">@provides()</code></h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Function decorator that explicitly declares which token the factory provides. Sets <code className="text-aquilia-500">__di_provides__</code> on the function along with the standard factory attributes. Use this when the token should be different from the function or return type.
        </p>
        <CodeBlock language="python" filename="@provides Examples">{`from aquilia.di import provides

@provides(DatabasePool, scope="singleton")
async def create_pool(config: AppConfig):
    """
    The token registered in the container is DatabasePool,
    not "create_pool" — explicitly declared via @provides.
    """
    return await asyncpg.create_pool(dsn=config.database_url)

# When resolved:
pool = await container.resolve_async(DatabasePool)
# → Calls create_pool(config=...) internally

# Attributes set:
assert create_pool.__di_provides__ == DatabasePool
assert create_pool.__di_factory__ == True`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'}`}>
          <p className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-800'}`}>
            <strong>When to use @provides vs @factory:</strong> Use <code className="text-aquilia-500">@factory</code> when the function name or return annotation is sufficient as the token. Use <code className="text-aquilia-500">@provides(Token)</code> when you want an explicit, unambiguous token — especially for interface binding (e.g., <code className="text-aquilia-500">@provides(IUserRepo)</code>).
          </p>
        </div>
      </section>

      {/* @auto_inject */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500">@auto_inject()</code></h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Function decorator that automatically resolves dependencies from the request container when the function is called. It inspects the function's parameter signature and resolves each type-hinted parameter that the caller didn't provide.
        </p>
        <CodeBlock language="python" filename="@auto_inject Usage">{`from aquilia.di import auto_inject

@auto_inject()
async def process_order(
    order_id: int,                    # Provided by caller
    service: OrderService,            # Auto-resolved from container
    logger: Annotated[Logger, Inject(tag="order")],  # Auto-resolved with tag
):
    logger.info(f"Processing order {order_id}")
    return await service.process(order_id)

# Call site — only pass the non-injectable args:
result = await process_order(order_id=42)
# → OrderService and Logger auto-resolved from request container`}</CodeBlock>

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-red-500/5 border-red-500/20' : 'bg-red-50 border-red-200'}`}>
          <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-800'}`}>
            <strong>⚠️ Performance Warning:</strong> <code className="text-aquilia-500">@auto_inject</code> adds overhead on every call — it must inspect the function signature, determine which parameters need resolution, and resolve each from the container. <strong>Prefer explicit resolution</strong> via <code className="text-aquilia-500">container.resolve_async()</code> in performance-critical paths. Reserve <code className="text-aquilia-500">@auto_inject</code> for convenience in non-hot-path code like CLI commands or background tasks.
          </p>
        </div>
      </section>

      {/* Decorator Summary Table */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Decorator Summary</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Decorator</th>
              <th className="text-left py-3 pr-4">Target</th>
              <th className="text-left py-3 pr-4">Attributes Set</th>
              <th className="text-left py-3">Provider Type</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['@service()', 'Class', '__di_scope__, __di_tag__, __di_name__', 'ClassProvider'],
                ['@injectable()', 'Class', 'Same as @service (alias)', 'ClassProvider'],
                ['@factory()', 'Function', '__di_scope__, __di_tag__, __di_name__, __di_factory__', 'FactoryProvider'],
                ['@provides(token)', 'Function', '__di_provides__ + factory attrs', 'FactoryProvider'],
                ['@auto_inject()', 'Function', 'Wrapper function (no dunder attrs)', 'N/A (runtime)'],
              ].map(([dec, target, attrs, provider], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{dec}</code></td>
                  <td className="py-3 pr-4">{target}</td>
                  <td className={`py-3 pr-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{attrs}</td>
                  <td className="py-3"><code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{provider}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Complete Example */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Complete Example</h2>
        <CodeBlock language="python" filename="Full Decorator Usage">{`from aquilia.di import service, factory, provides, inject, Inject, auto_inject
from typing import Annotated

# 1. Service decorator on classes
@service(scope="singleton")
class AppConfig:
    def __init__(self):
        self.db_url = os.environ["DATABASE_URL"]
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost")

# 2. Factory for complex initialization
@factory(scope="singleton")
async def create_pool(config: AppConfig) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=config.db_url)

# 3. Provides for explicit token binding
@provides(CacheBackend, scope="singleton", tag="redis")
async def create_redis_cache(config: AppConfig):
    return aioredis.from_url(config.redis_url)

# 4. Service with Inject metadata
@service(scope="request")
class UserService:
    def __init__(
        self,
        pool: asyncpg.Pool,                              # From factory
        cache: Annotated[CacheBackend, Inject(tag="redis")],  # Tagged
        metrics: Annotated[MetricsClient, Inject(optional=True)],  # Optional
    ):
        self.pool = pool
        self.cache = cache
        self.metrics = metrics

# 5. Register in manifest
users = Manifest(
    name="users",
    services=[AppConfig, create_pool, create_redis_cache, UserService],
)`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/scopes" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> Scopes
        </Link>
        <Link to="/docs/di/lifecycle" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          Lifecycle <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}