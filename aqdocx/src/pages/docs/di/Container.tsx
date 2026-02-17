import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box } from 'lucide-react'

export function DIContainer() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Container</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Container</code> is the heart of the DI system. It manages provider registration, instance caching, hierarchical scopes, lifecycle hooks, and shutdown finalizers.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating a Container</h2>
        <CodeBlock language="python" filename="Container Init">{`from aquilia.di.core import Container

# Root app container
container = Container(scope="app")

# With parent (for request scoping)
request_container = Container(scope="request", parent=container)

# Shortcut for request scope
request_container = container.create_request_scope()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Method</th>
              <th className="text-left py-3">Description</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['register(provider, tag?)', 'Register a Provider instance. Raises on duplicates.'],
                ['bind(interface, impl, scope?, tag?)', 'Bind an interface type to a concrete implementation.'],
                ['register_instance(token, instance, scope?, tag?)', 'Register a pre-built object (async).'],
                ['resolve(token, tag?, optional?)', 'Sync resolve — creates event loop if needed.'],
                ['resolve_async(token, tag?, optional?)', 'Primary async resolution path with caching & diagnostics.'],
                ['is_registered(token, tag?)', 'Check if a provider exists for the given token.'],
                ['create_request_scope()', 'Create a child container with inherited providers.'],
                ['startup()', 'Run all lifecycle startup hooks (async).'],
                ['shutdown()', 'Run shutdown hooks + finalizers in LIFO order (async).'],
              ].map(([method, desc], i) => (
                <tr key={i}>
                  <td className="py-2.5 pr-4 font-mono text-aquilia-400 text-xs">{method}</td>
                  <td className={`py-2.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registration Patterns</h2>
        <CodeBlock language="python" filename="Registration">{`from aquilia.di.providers import ClassProvider, ValueProvider

# Class provider — auto-resolves __init__ dependencies
container.register(ClassProvider(UserRepository, scope="request"))

# Value provider — pre-built instance
container.register(ValueProvider(
    token=Config,
    value=app_config,
    scope="singleton",
    name="AppConfig",
))

# Interface binding — resolve UserRepo → SqlUserRepo
container.bind(UserRepository, SqlUserRepository, scope="app")

# Register runtime instance (e.g. Session per request)
await container.register_instance(Session, session_obj, scope="request")

# Tagged registration for disambiguation
container.register(ClassProvider(RedisCache, scope="app"), tag="primary")
container.register(ClassProvider(MemoryCache, scope="app"), tag="fallback")

# Resolve tagged
primary = await container.resolve_async(Cache, tag="primary")`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Hierarchical Scopes</h2>
        <CodeBlock language="python" filename="Request Scope">{`# App container (long-lived)
app = Container(scope="app")
app.register(ClassProvider(DatabasePool, scope="singleton"))
app.register(ClassProvider(UserService, scope="request"))

# Per-request: create cheap child container
async def handle_request(request):
    req_container = app.create_request_scope()
    
    # Register request-specific values
    await req_container.register_instance(Request, request, scope="request")
    
    # Resolve — singleton deps come from parent, request deps are local
    service = await req_container.resolve_async(UserService)
    
    # After request, clean up request scope
    await req_container.shutdown()`}</CodeBlock>
        <div className={`mt-4 p-4 rounded-xl border-l-4 border-aquilia-500 ${isDark ? 'bg-aquilia-500/10' : 'bg-aquilia-50'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <strong>Scope delegation:</strong> When resolving a <code>singleton</code> or <code>app</code>-scoped provider from a child container, the resolution is automatically delegated to the parent container to ensure a single shared instance.
          </p>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Management</h2>
        <CodeBlock language="python" filename="Lifecycle">{`# Services with lifecycle hooks are auto-detected
class DatabasePool:
    async def on_startup(self):
        self.pool = await asyncpg.create_pool(...)

    async def on_shutdown(self):
        await self.pool.close()

# Container runs hooks automatically
await container.startup()   # calls on_startup for all resolved instances
# ... app runs ...
await container.shutdown()  # calls on_shutdown in LIFO order, then finalizers

# Also handles __aexit__ for context managers
class ManagedResource:
    async def __aexit__(self, *args):
        await self.close()`}</CodeBlock>
      </section>
    </div>
  )
}
