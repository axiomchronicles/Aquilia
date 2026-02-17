import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Package } from 'lucide-react'

export function DIDecorators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Package className="w-4 h-4" />
          Dependency Injection / Decorators
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          DI Decorators
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's DI system uses decorators to mark services, factories, and injection points. All decorators are type-safe and work with the container's lifecycle management.
        </p>
      </div>

      {/* @service */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@service</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Registers a class as a singleton service. The container creates one instance and reuses it for all injections.
        </p>
        <CodeBlock language="python" filename="service.py">{`from aquilia.di import service, Lifecycle

@service
class EmailService:
    def __init__(self, config: AppConfig):
        self.smtp_host = config.smtp_host

# With explicit lifecycle
@service(lifecycle=Lifecycle.TRANSIENT)
class RequestLogger:
    """New instance per injection."""
    pass

@service(lifecycle=Lifecycle.SCOPED)
class RequestContext:
    """One instance per request scope."""
    pass`}</CodeBlock>
      </section>

      {/* @factory */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@factory</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Registers a function as a factory for creating service instances. Useful when construction requires async operations or complex logic.
        </p>
        <CodeBlock language="python" filename="factory.py">{`from aquilia.di import factory

@factory
async def create_db_pool(config: AppConfig) -> DatabasePool:
    pool = DatabasePool(config.db_url)
    await pool.connect()
    return pool

# The return type annotation determines the service type
# container.resolve(DatabasePool) → calls create_db_pool()`}</CodeBlock>
      </section>

      {/* @inject */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@inject</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Explicitly marks a parameter for injection. Usually not needed — Aquilia injects by type annotation automatically.
        </p>
        <CodeBlock language="python" filename="inject.py">{`from aquilia.di import inject, Inject

class OrderService:
    @inject
    def __init__(
        self,
        db: DatabasePool,
        cache: CacheService,
        logger: Inject[Logger, "order"],  # Named injection
    ):
        self.db = db
        self.cache = cache
        self.logger = logger`}</CodeBlock>
      </section>

      {/* @provides */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@provides</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Registers a method as a provider for a specific interface/protocol.
        </p>
        <CodeBlock language="python" filename="provides.py">{`from aquilia.di import provides

class InfraModule:
    @provides(IMailProvider)
    def mail_provider(self, config: AppConfig) -> SMTPProvider:
        return SMTPProvider(host=config.smtp_host)

    @provides(ICacheBackend)
    def cache_backend(self) -> MemoryBackend:
        return MemoryBackend(max_size=1000)`}</CodeBlock>
      </section>

      {/* @auto_inject */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>@auto_inject</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Enables automatic injection on any function, not just constructors.
        </p>
        <CodeBlock language="python" filename="auto.py">{`from aquilia.di import auto_inject

@auto_inject
async def send_welcome_email(
    user_id: int,
    mail: EmailService,    # auto-injected
    db: DatabasePool,      # auto-injected
):
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", user_id)
    await mail.send(to=user.email, template="welcome")

# Call with only the non-injected args
await send_welcome_email(user_id=42)`}</CodeBlock>
      </section>

      {/* Decorator Reference Table */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Reference</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Decorator</th>
                <th className="py-3 px-4 text-left font-semibold">Target</th>
                <th className="py-3 px-4 text-left font-semibold">Purpose</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['@service', 'Class', 'Register as singleton (default) service'],
                ['@factory', 'Function', 'Register factory for complex creation'],
                ['@inject', 'Method', 'Mark method for parameter injection'],
                ['Inject[T, name]', 'Type hint', 'Named injection qualifier'],
                ['@provides', 'Method', 'Bind implementation to interface'],
                ['@auto_inject', 'Function', 'Enable injection on any callable'],
              ].map(([dec, target, purpose], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{dec}</td>
                  <td className="py-2.5 px-4 text-xs">{target}</td>
                  <td className="py-2.5 px-4 text-xs">{purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
