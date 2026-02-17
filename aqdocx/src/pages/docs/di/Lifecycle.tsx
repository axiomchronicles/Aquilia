import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Package } from 'lucide-react'

export function DILifecycle() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Package className="w-4 h-4" />
          Dependency Injection / Lifecycle
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Service Lifecycle
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each service has a lifecycle that determines when instances are created and destroyed. Aquilia supports singleton, transient, and scoped lifecycles with automatic disposal.
        </p>
      </div>

      {/* Lifecycle Types */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Types</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'SINGLETON', desc: 'One instance for the entire application. Created on first resolve, shared across all consumers. Default lifecycle.' },
            { name: 'TRANSIENT', desc: 'New instance on every resolve. No sharing. Useful for stateful objects or per-operation contexts.' },
            { name: 'SCOPED', desc: 'One instance per scope (typically per-request). Shared within the scope, disposed when scope ends.' },
          ].map((l, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-sm mb-2 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{l.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{l.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Specifying Lifecycle</h2>
        <CodeBlock language="python" filename="lifecycle.py">{`from aquilia.di import service, Lifecycle

@service(lifecycle=Lifecycle.SINGLETON)
class AppConfig:
    """Created once, shared everywhere."""
    pass

@service(lifecycle=Lifecycle.TRANSIENT)
class RequestId:
    """New UUID for every injection."""
    def __init__(self):
        self.id = uuid4()

@service(lifecycle=Lifecycle.SCOPED)
class DbSession:
    """One per request scope."""
    pass`}</CodeBlock>
      </section>

      {/* LifecycleHook */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Hooks</h2>
        <CodeBlock language="python" filename="hooks.py">{`from aquilia.di import service, LifecycleHook

@service
class DatabasePool(LifecycleHook):
    async def on_start(self):
        """Called after container builds the instance."""
        await self.connect()
    
    async def on_stop(self):
        """Called during container disposal."""
        await self.disconnect()

# Hooks are called automatically:
# container.initialize() → on_start for all singletons
# container.dispose()    → on_stop in reverse order`}</CodeBlock>
      </section>

      {/* DisposalStrategy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Disposal Strategy</h2>
        <CodeBlock language="python" filename="disposal.py">{`from aquilia.di import DisposalStrategy

# FIFO — dispose in creation order
container = Container(disposal=DisposalStrategy.FIFO)

# LIFO — dispose in reverse order (default, recommended)
container = Container(disposal=DisposalStrategy.LIFO)

# PARALLEL — dispose all concurrently
container = Container(disposal=DisposalStrategy.PARALLEL)

# The container tracks all created instances and
# calls on_stop/close/dispose based on the strategy`}</CodeBlock>
      </section>

      {/* Scope */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Scopes</h2>
        <CodeBlock language="python" filename="scope.py">{`# Scoped services are managed per-request automatically
# by the RequestScopeMiddleware

# Manual scope creation (for background tasks, CLI, etc.)
async with container.create_scope() as scope:
    # Scoped services created here are isolated
    session = scope.resolve(DbSession)
    ctx = scope.resolve(RequestContext)
    
    # Do work...
    
# Scope ends → all scoped services disposed`}</CodeBlock>
      </section>
    </div>
  )
}
