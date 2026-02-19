import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Puzzle } from 'lucide-react'

export function DIAdvanced() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Puzzle className="w-4 h-4" />
          Dependency Injection / Decorators & Lifecycle
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            DI Decorators & Lifecycle
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides decorator-based registration, lifecycle hooks with deterministic disposal, and diagnostic tools for dependency graph inspection.
        </p>
      </div>

      {/* Decorators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registration Decorators</h2>

        <div className={`overflow-hidden rounded-xl border mb-6 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Decorator</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Scope</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { d: '@service', s: 'singleton', desc: 'Class-based provider, created once' },
                { d: '@service(scope="request")', s: 'request', desc: 'Per-request instance' },
                { d: '@service(scope="transient")', s: 'transient', desc: 'New instance every resolve' },
                { d: '@factory', s: 'configurable', desc: 'Factory function as provider' },
                { d: '@inject(Token)', s: 'n/a', desc: 'Constructor parameter injection' },
                { d: '@provides(Token)', s: 'n/a', desc: 'Mark method as provider for token' },
                { d: '@auto_inject', s: 'n/a', desc: 'Auto-resolve all type-hinted params' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.d}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.s}</td>
                  <td className={`py-3 px-4 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" filename="di_decorators.py">{`from aquilia.di import service, factory, inject, Inject, provides, auto_inject


# Basic singleton service
@service
class EmailService:
    async def send(self, to: str, subject: str, body: str): ...


# Request-scoped service
@service(scope="request")
class RequestLogger:
    def __init__(self):
        self.entries = []

    def log(self, msg: str):
        self.entries.append(msg)


# Factory provider
@factory
def create_db_pool():
    return asyncpg.create_pool(dsn="postgres://localhost/mydb")


# Explicit injection via Inject marker
class OrderService:
    def __init__(
        self,
        db: Inject[DatabasePool],
        mail: Inject[EmailService],
    ):
        self.db = db
        self.mail = mail


# Auto-inject all type-hinted parameters
@auto_inject
class UserController:
    def __init__(self, users: UserRepository, auth: AuthManager):
        self.users = users
        self.auth = auth`}</CodeBlock>
      </section>

      {/* Lifecycle */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Hooks</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Services can define <code className="text-aquilia-500">on_init</code> and <code className="text-aquilia-500">on_dispose</code> hooks. The DI container calls them in dependency order during startup and in reverse order during shutdown.
        </p>
        <CodeBlock language="python" filename="lifecycle.py">{`from aquilia.di import service, Lifecycle


@service
class DatabasePool(Lifecycle):
    async def on_init(self):
        """Called after construction, during container startup."""
        self.pool = await asyncpg.create_pool(dsn=self.dsn)
        print(f"Database pool opened: {self.dsn}")

    async def on_dispose(self):
        """Called during container shutdown (reverse order)."""
        await self.pool.close()
        print("Database pool closed")


@service
class CacheClient(Lifecycle):
    async def on_init(self):
        self.redis = await aioredis.from_url("redis://localhost")

    async def on_dispose(self):
        await self.redis.close()


# Disposal order is deterministic:
# Startup:  DatabasePool.on_init() → CacheClient.on_init()
# Shutdown: CacheClient.on_dispose() → DatabasePool.on_dispose()`}</CodeBlock>

        <div className="mt-6">
          <h3 className={`text-sm font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Disposal Strategies</h3>
          <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Strategy</th>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Behavior</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
                {[
                  { s: 'SEQUENTIAL', b: 'Dispose one at a time in reverse init order' },
                  { s: 'CONCURRENT', b: 'Dispose independent services concurrently' },
                  { s: 'BEST_EFFORT', b: 'Continue disposal even if one service fails' },
                ].map((row, i) => (
                  <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                    <td className="py-2.5 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.s}</code></td>
                    <td className={`py-2.5 px-4 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Dependency Graph */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Graph & Diagnostics</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia builds a <code className="text-aquilia-500">DependencyGraph</code> at startup for cycle detection, scope validation, and visualization.
        </p>
        <CodeBlock language="python" filename="diagnostics.py">{`from aquilia.di import Registry, DependencyGraph

registry = Registry()
# ... register providers ...

graph = DependencyGraph(registry)

# Detect cycles
cycles = graph.detect_cycles()
if cycles:
    print(f"Circular dependencies found: {cycles}")

# Validate scope rules (e.g., singleton → request is invalid)
violations = graph.validate_scopes()
for v in violations:
    print(f"Scope violation: {v.provider} ({v.scope}) → {v.dependency} ({v.dep_scope})")

# Topological sort for init order
init_order = graph.topological_sort()
# → [DatabasePool, CacheClient, UserRepository, OrderService]

# Pretty-print the graph
graph.print_tree()
# OrderService
#   ├── UserRepository
#   │   └── DatabasePool
#   └── CacheClient`}</CodeBlock>
      </section>

      {/* Test Registry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TestRegistry</h2>
        <CodeBlock language="python" filename="test_registry.py">{`from aquilia.di import TestRegistry, MockProvider

# Override real services in tests
test_reg = TestRegistry(base=production_registry)

# Replace with mock
test_reg.override(EmailService, MockProvider(
    send=AsyncMock(return_value=True)
))

# Or use a value directly
test_reg.override(DatabasePool, value=FakePool())

# Resolve gives mock
email = await test_reg.resolve(EmailService)
await email.send("test@example.com", "Hi", "Body")
email.send.assert_called_once()`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/di/scopes" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Scopes
        </Link>
        <Link to="/docs/models" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Models <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
