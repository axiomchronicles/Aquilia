import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box } from 'lucide-react'

export function DIProviders() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Providers</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">Provider</code> is a protocol that knows how to instantiate a dependency. Aquilia includes four built-in provider types plus the ability to define custom ones.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Provider Protocol</h2>
        <CodeBlock language="python" filename="aquilia/di/core.py">{`@runtime_checkable
class Provider(Protocol):
    @property
    def meta(self) -> ProviderMeta:
        """Provider metadata (name, token, scope, tags, module, line)."""
        ...

    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Create the instance, resolving sub-dependencies via ctx.container."""
        ...

    async def shutdown(self) -> None:
        """Cleanup hook called in LIFO order on container.shutdown()."""
        ...`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ProviderMeta</h2>
        <CodeBlock language="python" filename="Metadata Dataclass">{`@dataclass(frozen=True, slots=True)
class ProviderMeta:
    name: str                          # Class name
    token: str                         # "module.ClassName"
    scope: str                         # "singleton"|"app"|"request"|"transient"|"pooled"|"ephemeral"
    tags: tuple[str, ...] = ()         # Disambiguation tags
    module: str = ""                   # Source module
    qualname: str = ""                 # Qualified name
    line: Optional[int] = None         # Source line number
    version: Optional[str] = None      # Semantic version
    allow_lazy: bool = False           # Lazy instantiation flag`}</CodeBlock>
        <p className={`mt-3 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
          ProviderMeta is serialized to <code>di_manifest.json</code> for IDE / LSP integration.
        </p>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ClassProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          The workhorse provider. Introspects the class <code>__init__</code> signature, resolves every typed parameter from the container, and instantiates the class. Supports <code>async_init()</code> for async setup.
        </p>
        <CodeBlock language="python" filename="ClassProvider">{`from aquilia.di.providers import ClassProvider

provider = ClassProvider(
    cls=UserService,
    scope="request",
    tags=("primary",),
    allow_lazy=True,
)

container.register(provider)

# How it works internally:
# 1. Inspect UserService.__init__ signature
# 2. For each parameter with a type hint:
#    - Check for Inject metadata (Annotated[Type, Inject(...)])
#    - Resolve dependency from container via resolve_async()
# 3. Call UserService(**resolved_deps)
# 4. If UserService has async_init(), call await instance.async_init()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ValueProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Wraps a pre-instantiated object. Useful for config objects, request objects, and anything created outside the DI system.
        </p>
        <CodeBlock language="python" filename="ValueProvider">{`from aquilia.di.providers import ValueProvider

provider = ValueProvider(
    token=AppConfig,
    value=loaded_config,
    scope="singleton",
    name="AppConfig",
)

# Or use the shorthand:
await container.register_instance(AppConfig, loaded_config, scope="singleton")`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FactoryProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Uses a custom callable (sync or async) to build the instance. The factory receives the <code>ResolveCtx</code> for manual dependency resolution.
        </p>
        <CodeBlock language="python" filename="FactoryProvider">{`from aquilia.di.providers import FactoryProvider

async def create_database_pool(ctx: ResolveCtx):
    config = await ctx.container.resolve_async(AppConfig)
    pool = await asyncpg.create_pool(dsn=config.database_url)
    return pool

provider = FactoryProvider(
    factory=create_database_pool,
    token="DatabasePool",
    scope="singleton",
)

# Or use the @factory decorator:
from aquilia.di.decorators import factory

@factory(scope="singleton")
async def database_pool(ctx: ResolveCtx):
    config = await ctx.container.resolve_async(AppConfig)
    return await asyncpg.create_pool(dsn=config.database_url)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Decorators</h2>
        <CodeBlock language="python" filename="DI Decorators">{`from aquilia.di.decorators import service, inject
from typing import Annotated

# @service — marks a class as a DI service
@service(scope="request", tag="primary")
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# @inject() — explicit injection metadata
class OrderService:
    def __init__(
        self,
        db: Annotated[Database, inject(tag="readonly")],
        cache: Annotated[Cache, inject(optional=True)],
    ):
        self.db = db
        self.cache = cache  # None if not registered`}</CodeBlock>
      </section>
    </div>
  )
}
