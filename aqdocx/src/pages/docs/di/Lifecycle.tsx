import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DILifecycle() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The lifecycle system in <code className="text-aquilia-500">aquilia/di/lifecycle.py</code> manages startup hooks, shutdown hooks, and finalizers for DI containers. It supports three disposal strategies, priority-ordered execution, and an async context manager for clean resource management.
        </p>
      </div>

      {/* DisposalStrategy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DisposalStrategy</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Controls how finalizers are executed during container shutdown. Defined as a <code className="text-aquilia-500">str</code>-based <code className="text-aquilia-500">Enum</code>:
        </p>
        <CodeBlock language="python" filename="DisposalStrategy Enum">{`from aquilia.di import DisposalStrategy

class DisposalStrategy(str, Enum):
    LIFO     = "lifo"      # Last-in, first-out (default)
    FIFO     = "fifo"      # First-in, first-out
    PARALLEL = "parallel"  # All finalizers run concurrently via asyncio.gather`}</CodeBlock>

        <div className="overflow-x-auto mt-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Strategy</th>
              <th className="text-left py-3 pr-4">Order</th>
              <th className="text-left py-3">Use Case</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['LIFO', 'Last registered → first disposed', 'Default. Ensures dependent services are cleaned up before their dependencies. Database connections close before the pool.'],
                ['FIFO', 'First registered → first disposed', 'When cleanup order should match initialization order. Rarely needed.'],
                ['PARALLEL', 'All at once via asyncio.gather', 'When finalizers are independent and you want maximum shutdown speed. Risk: if finalizers have dependencies on each other, use LIFO instead.'],
              ].map(([strategy, order, usecase], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{strategy}</code></td>
                  <td className="py-3 pr-4">{order}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{usecase}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* LifecycleHook */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LifecycleHook</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A dataclass representing a single startup or shutdown hook:
        </p>
        <CodeBlock language="python" filename="LifecycleHook Dataclass">{`from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class LifecycleHook:
    name: str                    # Human-readable name for logging
    callback: Callable           # Async callable to execute
    priority: int = 0            # Lower = runs first (sorted ascending)
    phase: Optional[str] = None  # Optional phase label for grouping`}</CodeBlock>

        <div className="overflow-x-auto mt-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Field</th>
              <th className="text-left py-3">Behavior</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['name', 'Used in log messages during startup/shutdown. E.g., "database_pool_init".'],
                ['callback', 'An async callable. Receives no arguments. Exceptions are collected and handled per phase.'],
                ['priority', 'Hooks sorted by priority ascending before execution. Priority 0 runs before priority 10.'],
                ['phase', 'Optional string label. Not used for ordering — for organizational/logging purposes.'],
              ].map(([field, behavior], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{field}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{behavior}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Lifecycle Class */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Class</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Lifecycle</code> class manages three collections: startup hooks, shutdown hooks, and finalizers. It uses <code className="text-aquilia-500">__slots__</code> for memory efficiency.
        </p>

        <div className="overflow-x-auto mb-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Slot</th>
              <th className="text-left py-3 pr-4">Type</th>
              <th className="text-left py-3">Purpose</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['_startup_hooks', 'list[LifecycleHook]', 'Hooks executed during container startup.'],
                ['_shutdown_hooks', 'list[LifecycleHook]', 'Hooks executed during container shutdown.'],
                ['_finalizers', 'list[Callable]', 'Instance-level cleanup callbacks (e.g., close connections).'],
                ['_disposal_strategy', 'DisposalStrategy', 'How finalizers are executed: LIFO, FIFO, or PARALLEL.'],
              ].map(([slot, type_, desc], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{slot}</code></td>
                  <td className="py-3 pr-4"><code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{type_}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* on_startup */}
        <div className="mb-0">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>on_startup(name, callback, *, priority=0, phase=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Register a startup hook. Hooks are sorted by <code className="text-aquilia-500">priority</code> (ascending) before execution. The hook list is re-sorted on each addition.
          </p>
          <CodeBlock language="python">{`lifecycle = Lifecycle()

lifecycle.on_startup(
    name="database_pool",
    callback=init_database_pool,
    priority=0,  # Runs first
)

lifecycle.on_startup(
    name="cache_warmup",
    callback=warm_cache,
    priority=10,  # Runs after database
)

lifecycle.on_startup(
    name="background_workers",
    callback=start_workers,
    priority=20,  # Runs last
)`}</CodeBlock>
        </div>

        {/* on_shutdown */}
        <div className="mb-0">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>on_shutdown(name, callback, *, priority=0, phase=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Register a shutdown hook. Same priority-sorted behavior as startup hooks. Shutdown hooks <strong>log errors but continue</strong> — all hooks run even if one fails.
          </p>
          <CodeBlock language="python">{`lifecycle.on_shutdown(
    name="close_pool",
    callback=close_database_pool,
    priority=100,  # Run late — after dependent services
)

lifecycle.on_shutdown(
    name="flush_metrics",
    callback=flush_metrics,
    priority=0,  # Run early
)`}</CodeBlock>
        </div>

        {/* register_finalizer */}
        <div className="mb-0">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>register_finalizer(callback)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Register a finalizer callback. Finalizers are instance-level cleanup functions — the Container calls this automatically when caching resolved instances. Finalizers are executed according to the <code className="text-aquilia-500">_disposal_strategy</code>.
          </p>
          <CodeBlock language="python">{`# The container registers finalizers automatically:
# When a provider's instantiate() returns an instance with a
# close() or shutdown() method, the container adds it as a finalizer.

# Manual registration:
lifecycle.register_finalizer(lambda: pool.close())
lifecycle.register_finalizer(connection.disconnect)`}</CodeBlock>
        </div>
      </section>

      {/* Execution Behavior */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Execution Behavior</h2>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>run_startup_hooks()</h3>
        <div className="mb-6">
          <ul className={`list-disc pl-6 space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Sorts hooks by <code className="text-aquilia-500">priority</code> ascending (0 first)</li>
            <li>Executes each hook's <code className="text-aquilia-500">callback()</code> sequentially (awaited if async)</li>
            <li><strong>Collects errors</strong> during execution</li>
            <li><strong>Raises</strong> if any startup hook fails — startup is considered critical</li>
            <li>All hooks run regardless of individual failures (errors are collected, then raised together)</li>
          </ul>
        </div>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>run_shutdown_hooks()</h3>
        <div className="mb-6">
          <ul className={`list-disc pl-6 space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Sorts hooks by <code className="text-aquilia-500">priority</code> ascending</li>
            <li>Executes each hook's <code className="text-aquilia-500">callback()</code> sequentially</li>
            <li><strong>Logs errors but continues</strong> — shutdown must complete even if individual hooks fail</li>
            <li>This is the key difference from startup: shutdown is best-effort, startup is all-or-nothing</li>
          </ul>
        </div>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>run_finalizers()</h3>
        <div className="mb-6">
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Dispatches to the configured disposal strategy:
          </p>
          <CodeBlock language="python">{`async def run_finalizers(self):
    if self._disposal_strategy == DisposalStrategy.LIFO:
        # Reverse order — last registered, first finalized
        for finalizer in reversed(self._finalizers):
            await finalizer()
    
    elif self._disposal_strategy == DisposalStrategy.FIFO:
        # Registration order
        for finalizer in self._finalizers:
            await finalizer()
    
    elif self._disposal_strategy == DisposalStrategy.PARALLEL:
        # All at once
        await asyncio.gather(
            *(f() for f in self._finalizers),
            return_exceptions=True,
        )`}</CodeBlock>
        </div>
      </section>

      {/* Container Shutdown Flow */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Container Shutdown Sequence</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When <code className="text-aquilia-500">container.shutdown()</code> is called, three phases execute in order:
        </p>
        <div className="mb-0">
          <div className="space-y-4">
            {[
              { step: '1', title: 'Run Finalizers (LIFO)', desc: 'Execute all registered finalizers in LIFO order. These are instance-level cleanup callbacks — closing connections, flushing buffers, releasing file handles.' },
              { step: '2', title: 'Run Shutdown Hooks', desc: 'Execute lifecycle shutdown hooks in priority order. These are container-level cleanup — stopping background workers, shutting down pools, flushing metrics. Errors are logged but execution continues.' },
              { step: '3', title: 'Clear Cache', desc: 'Clear the _cache dict and _finalizers list. For request containers, this frees all request-scoped instances.' },
            ].map((phase, i) => (
              <div key={i} className="flex gap-4">
                <div className="flex-shrink-0">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500/20 text-aquilia-500 text-xs font-bold">{phase.step}</span>
                </div>
                <div>
                  <h4 className={`font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{phase.title}</h4>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{phase.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* LifecycleContext */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LifecycleContext</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          An async context manager that wraps <code className="text-aquilia-500">startup()</code> and <code className="text-aquilia-500">shutdown()</code> for clean resource management. Ensures shutdown always runs, even if an exception occurs during the context.
        </p>
        <CodeBlock language="python" filename="LifecycleContext">{`from aquilia.di import LifecycleContext

# As an async context manager:
async with LifecycleContext(container) as ctx:
    # startup() called automatically on __aenter__
    
    # Your application runs here
    await serve_requests()
    
    # shutdown() called automatically on __aexit__
    # Even if serve_requests() raises an exception

# Implementation:
class LifecycleContext:
    def __init__(self, container):
        self.container = container
    
    async def __aenter__(self):
        await self.container.startup()
        return self.container
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.container.shutdown()
        return False  # Don't suppress exceptions`}</CodeBlock>
      </section>

      {/* Auto-Detection of Lifecycle Methods */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Detection of Lifecycle Methods</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Container's <code className="text-aquilia-500">_check_lifecycle_hooks()</code> method scans all registered providers for services that implement <code className="text-aquilia-500">on_startup</code> or <code className="text-aquilia-500">on_shutdown</code> methods and automatically registers them as lifecycle hooks:
        </p>
        <CodeBlock language="python" filename="Auto-detected Lifecycle Methods">{`@service(scope="singleton")
class DatabasePool:
    def __init__(self, config: AppConfig):
        self.config = config
        self.pool = None
    
    async def on_startup(self):
        """Auto-detected by _check_lifecycle_hooks() → registered as startup hook."""
        self.pool = await asyncpg.create_pool(dsn=self.config.db_url)
    
    async def on_shutdown(self):
        """Auto-detected → registered as shutdown hook."""
        if self.pool:
            await self.pool.close()

# When container.startup() is called:
# 1. _check_lifecycle_hooks() scans providers
# 2. Finds DatabasePool.on_startup → registers as LifecycleHook
# 3. Finds DatabasePool.on_shutdown → registers as shutdown LifecycleHook
# 4. Executes all startup hooks in priority order`}</CodeBlock>
      </section>

      {/* Request vs App Lifecycle */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request vs App Lifecycle</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Aspect</th>
              <th className="text-left py-3 pr-4">App Container</th>
              <th className="text-left py-3">Request Container</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['Lifecycle instance', 'Full Lifecycle object', '_NullLifecycleType (no-op singleton)'],
                ['Startup hooks', 'Run on container.startup()', 'None — no startup for requests'],
                ['Shutdown hooks', 'Run on container.shutdown()', 'None — only finalizers run'],
                ['Finalizers', 'LIFO disposal of app instances', 'LIFO disposal of request-scoped instances'],
                ['Cache clearing', 'Clears all cached instances', 'Clears request-scoped cache only'],
                ['Typical lifetime', 'Process lifetime', 'Single HTTP request (~ms)'],
              ].map(([aspect, app, request], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><strong>{aspect}</strong></td>
                  <td className={`py-3 pr-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{app}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{request}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Complete Example */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full Lifecycle Example</h2>
        <CodeBlock language="python" filename="Complete Lifecycle Setup">{`from aquilia.di import (
    Container, Lifecycle, LifecycleHook,
    DisposalStrategy, LifecycleContext,
)

# Create lifecycle with parallel disposal
lifecycle = Lifecycle(disposal_strategy=DisposalStrategy.LIFO)

# Register hooks with priorities
lifecycle.on_startup("config", load_config, priority=0)
lifecycle.on_startup("database", init_database, priority=10)
lifecycle.on_startup("cache", init_cache, priority=20)
lifecycle.on_startup("workers", start_workers, priority=30)

lifecycle.on_shutdown("workers", stop_workers, priority=0)
lifecycle.on_shutdown("cache", flush_cache, priority=10)
lifecycle.on_shutdown("database", close_database, priority=20)

# Register instance-level finalizers
lifecycle.register_finalizer(pool.close)
lifecycle.register_finalizer(redis.disconnect)
lifecycle.register_finalizer(http_client.aclose)

# Use with container:
container = registry.build_container()

async with LifecycleContext(container):
    # Startup complete — all hooks executed in priority order
    # Application runs here
    await run_server()
    # Shutdown: finalizers (LIFO) → shutdown hooks (priority) → clear`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/decorators" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> Decorators
        </Link>
        <Link to="/docs/di/diagnostics" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          Diagnostics <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}