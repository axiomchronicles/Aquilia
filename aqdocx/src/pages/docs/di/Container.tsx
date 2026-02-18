import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DIContainer() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Container</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Container</code> is the heart of the DI system. It manages provider registration, instance caching, hierarchical scope delegation, lifecycle hooks, and LIFO shutdown finalizers. Defined in <code className="text-aquilia-500">aquilia/di/core.py</code> with <code className="text-aquilia-500">__slots__</code> for memory efficiency.
        </p>
      </div>

      {/* Slots / Internal Structure */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Internal Structure</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Container uses <code className="text-aquilia-500">__slots__</code> with 8 slot attributes for zero-overhead attribute access:
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Slot</th>
              <th className="text-left py-3 pr-4">Type</th>
              <th className="text-left py-3">Purpose</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['_providers', 'dict[str, Provider]', 'Token → Provider mapping. Shared by reference with child containers.'],
                ['_cache', 'dict[str, Any]', 'Cache key → resolved instance. Each container gets its own cache.'],
                ['_scope', 'str', 'Container scope ("app", "request", etc). Determines cache behavior.'],
                ['_parent', 'Container | None', 'Parent container for scope delegation. Singleton/app lookups bubble up.'],
                ['_finalizers', 'list[Callable]', 'LIFO finalizer stack — shutdown() drains in reverse order.'],
                ['_resolve_plans', 'dict', 'Cached resolution plans for hot-path optimization.'],
                ['_diagnostics', 'DIDiagnostics', 'Event emitter for tracing registrations and resolutions.'],
                ['_lifecycle', 'Lifecycle', 'Manages on_startup/on_shutdown hooks and disposal strategy.'],
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
      </section>

      {/* Creating Containers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating Containers</h2>
        <CodeBlock language="python" filename="Container Initialization">{`from aquilia.di.core import Container

# Root app container (created by Registry.build_container() internally)
container = Container(scope="app")

# With explicit parent (for manual hierarchies)
request_container = Container(scope="request", parent=container)

# Preferred: use the factory method for request scoping
request_container = container.create_request_scope()
# → Creates child with shared _providers (by reference), fresh _cache,
#   and _NullLifecycle (no-op lifecycle for lightweight request containers)`}</CodeBlock>

        <div className={`mt-6 p-4 rounded-xl border ${isDark ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'}`}>
          <p className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-800'}`}>
            <strong>Note:</strong> In production, you almost never create containers manually. The <code className="text-aquilia-500">Registry.build_container()</code> method creates the root container, and the ASGI middleware calls <code className="text-aquilia-500">create_request_scope()</code> per-request automatically. The child container shares the parent's provider dict by reference — no copy overhead.
          </p>
        </div>
      </section>

      {/* API Reference */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h2>

        {/* register */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>register(provider, *, tag=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Register a <code className="text-aquilia-500">Provider</code> instance. Raises on duplicate token+tag combinations. Emits a <code className="text-aquilia-500">REGISTRATION</code> diagnostic event.
          </p>
          <CodeBlock language="python">{`from aquilia.di import ClassProvider

provider = ClassProvider(UserService, scope="request")
container.register(provider)

# With a tag for disambiguation
container.register(redis_provider, tag="redis")
container.register(memcached_provider, tag="memcached")`}</CodeBlock>
        </div>

        {/* bind */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>bind(interface, implementation, *, scope="app", tag=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Bind an interface type to a concrete implementation. Creates a <code className="text-aquilia-500">ClassProvider</code> internally and registers it under the interface token.
          </p>
          <CodeBlock language="python">{`from abc import ABC, abstractmethod

class IUserRepo(ABC):
    @abstractmethod
    async def find(self, id: int): ...

class PostgresUserRepo(IUserRepo):
    def __init__(self, pool: DatabasePool):
        self.pool = pool
    
    async def find(self, id: int):
        return await self.pool.fetch_one("SELECT * FROM users WHERE id=$1", id)

# Bind interface → implementation
container.bind(IUserRepo, PostgresUserRepo, scope="app")

# Consumers depend on the interface:
class UserService:
    def __init__(self, repo: IUserRepo):  # ← resolved to PostgresUserRepo
        self.repo = repo`}</CodeBlock>
        </div>

        {/* register_instance */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>register_instance(token, instance, *, scope="app", tag=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Register a pre-built object. Creates a <code className="text-aquilia-500">ValueProvider</code> internally. Useful for configuration objects, database pools, or anything initialized outside the DI system.
          </p>
          <CodeBlock language="python">{`import asyncpg

pool = await asyncpg.create_pool(dsn="postgresql://localhost/mydb")
container.register_instance(asyncpg.Pool, pool, scope="singleton")`}</CodeBlock>
        </div>

        {/* resolve_async */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>resolve_async(token, *, tag=None, optional=False)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Primary async resolution path.</strong> This is the hot path — optimized for &lt;3&micro;s cached lookups with inlined token-to-key conversion. The resolution flow:
          </p>
          <ol className={`list-decimal pl-6 mb-4 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Inline token → key conversion via <code className="text-aquilia-500">_type_key_cache</code> (avoids function call overhead)</li>
            <li>Check <code className="text-aquilia-500">_cache</code> — O(1) dict lookup returns immediately on hit</li>
            <li>Scope delegation — singleton/app tokens delegate to <code className="text-aquilia-500">_parent.resolve_async()</code></li>
            <li>Provider instantiation via <code className="text-aquilia-500">provider.instantiate(ctx)</code></li>
            <li>Cache result if scope is cacheable, register shutdown finalizer</li>
          </ol>
          <CodeBlock language="python">{`# Standard resolution
user_svc = await container.resolve_async(UserService)

# Tagged resolution (disambiguate multiple providers)
redis = await container.resolve_async(CacheBackend, tag="redis")

# Optional resolution (returns None instead of raising)
metrics = await container.resolve_async(MetricsCollector, optional=True)
if metrics:
    metrics.record("request_count", 1)`}</CodeBlock>
        </div>

        {/* resolve (sync) */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>resolve(token, *, tag=None, optional=False)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Synchronous resolution wrapper. Creates an event loop if one is not running. <strong>Prefer <code className="text-aquilia-500">resolve_async()</code> in async contexts</strong> — the sync version exists for backwards compatibility and startup code.
          </p>
          <CodeBlock language="python">{`# Only use in synchronous contexts (startup, CLI, tests)
config = container.resolve(AppConfig)`}</CodeBlock>
        </div>

        {/* is_registered */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>is_registered(token, *, tag=None)</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Check whether a provider exists for the given token. Checks both the current container and the parent chain.
          </p>
          <CodeBlock language="python">{`if container.is_registered(MetricsCollector):
    metrics = await container.resolve_async(MetricsCollector)
    metrics.track("event")`}</CodeBlock>
        </div>

        {/* create_request_scope */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>create_request_scope()</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Create a lightweight child container for request-scoped isolation. The child:
          </p>
          <ul className={`list-disc pl-6 mb-4 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Shares <code className="text-aquilia-500">_providers</code> dict by reference (zero copy overhead)</li>
            <li>Gets its own empty <code className="text-aquilia-500">_cache</code> (request-scoped instances isolated)</li>
            <li>Uses <code className="text-aquilia-500">_NullLifecycle</code> — a singleton no-op lifecycle to avoid overhead</li>
            <li>Sets <code className="text-aquilia-500">_parent</code> to the app container for scope delegation</li>
          </ul>
          <CodeBlock language="python">{`# Typically called by ASGI middleware per-request:
async def di_middleware(scope, receive, send):
    request_container = app_container.create_request_scope()
    try:
        scope["container"] = request_container
        await app(scope, receive, send)
    finally:
        await request_container.shutdown()  # LIFO finalizers, clear cache`}</CodeBlock>
        </div>

        {/* startup */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>startup()</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Run all lifecycle startup hooks in priority order. Internally calls <code className="text-aquilia-500">_check_lifecycle_hooks()</code> to scan for providers that implement <code className="text-aquilia-500">on_startup</code>/<code className="text-aquilia-500">on_shutdown</code> methods and registers them as lifecycle hooks. Raises if any startup hook fails.
          </p>
          <CodeBlock language="python">{`container = registry.build_container()
await container.startup()
# All startup hooks executed in priority order
# Errors collected — raises if any fail`}</CodeBlock>
        </div>

        {/* shutdown */}
        <div className="mb-12">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>shutdown()</h3>
          <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Graceful shutdown sequence:
          </p>
          <ol className={`list-decimal pl-6 mb-4 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>Run all registered <strong>finalizers</strong> in LIFO order (connection pools, file handles, etc.)</li>
            <li>Execute lifecycle <strong>shutdown hooks</strong> in priority order (logs errors but continues)</li>
            <li><strong>Clear</strong> the cache and finalizer list</li>
          </ol>
          <CodeBlock language="python">{`# For app containers — called on server shutdown
await container.shutdown()

# For request containers — called at end of each request
await request_container.shutdown()
# Lightweight: only drains request-scoped cache + finalizers`}</CodeBlock>
        </div>
      </section>

      {/* Registry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Registry</code> is the build-time component that processes manifests and produces a validated Container. It performs static analysis before any runtime code executes.
        </p>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>from_manifests(manifests, config, *, enforce_cross_app=True)</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The four-phase pipeline:
        </p>
        <CodeBlock language="python" filename="Registry Build Pipeline">{`from aquilia.di import Registry

registry = Registry.from_manifests(
    manifests=[users_manifest, orders_manifest, payments_manifest],
    config=app_config,
    enforce_cross_app=True,  # Validate depends_on declarations
)

# Phase 1: Load manifest services
#   → Creates Provider instances from manifest.services lists
#   → Attaches ProviderMeta (scope, tags, module, line, version)

# Phase 2: Build dependency graph
#   → Inspects __init__ signatures for type-hinted dependencies
#   → Supports Annotated[Type, Inject(tag="...")] for tagged deps
#   → Populates DependencyGraph.adj_list

# Phase 3: Detect cycles (Tarjan's SCC algorithm)
#   → Finds all strongly connected components
#   → Filters trivial SCCs (single node, no self-loop)
#   → Raises DependencyCycleError with cycle trace + locations

# Phase 4: Validate cross-app dependencies
#   → Checks that inter-app deps are in depends_on
#   → Raises CrossAppDependencyError if violated

container = registry.build_container()  # → Container with all providers`}</CodeBlock>
      </section>

      {/* ResolveCtx */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ResolveCtx</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">ResolveCtx</code> is the resolution context passed to every <code className="text-aquilia-500">provider.instantiate(ctx)</code> call. It tracks the resolution stack for cycle detection at runtime and provides per-resolution caching.
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Attribute / Method</th>
              <th className="text-left py-3">Purpose</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['container', 'Reference to the Container performing the resolution.'],
                ['stack: list[str]', 'Token stack — tracks the current resolution chain for cycle detection.'],
                ['cache: dict', 'Per-resolution cache — avoids re-resolving the same token within a single resolution tree.'],
                ['push(token)', 'Push token onto the stack. Called before resolving a dependency.'],
                ['pop()', 'Pop the last token from the stack. Called after resolution completes.'],
                ['in_cycle(token) → bool', 'Check if the token is already in the stack (cycle detection).'],
                ['get_trace() → list[str]', 'Return a copy of the current resolution stack for error diagnostics.'],
              ].map(([attr, desc], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{attr}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ProviderMeta */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ProviderMeta</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">ProviderMeta</code> is a frozen dataclass with <code className="text-aquilia-500">__slots__</code> that carries metadata for every provider. Used by diagnostics, CLI tools, and error messages.
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Field</th>
              <th className="text-left py-3 pr-4">Type</th>
              <th className="text-left py-3">Description</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['name', 'str', 'Human-readable provider name (class or function name).'],
                ['token', 'str', 'Resolution token — usually the fully-qualified class name.'],
                ['scope', 'str', 'Service scope: singleton, app, request, transient, pooled, ephemeral.'],
                ['tags', 'tuple[str, ...]', 'Tags for disambiguation when multiple providers share a token.'],
                ['module', 'str', 'Python module where the provider was defined.'],
                ['qualname', 'str', 'Fully-qualified name including class path.'],
                ['line', 'int | None', 'Source line number for error diagnostics.'],
                ['version', 'str | None', 'Optional version string for the provider.'],
                ['allow_lazy', 'bool', 'If True, cycles involving this provider use LazyProxyProvider.'],
              ].map(([field, type_, desc], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{field}</code></td>
                  <td className="py-3 pr-4"><code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{type_}</code></td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python" filename="ProviderMeta Serialization">{`# to_dict() for CLI/LSP export:
meta = provider.meta
meta.to_dict()
# → {"name": "UserService", "token": "app.services.UserService",
#    "scope": "request", "tags": (), "module": "app.services",
#    "qualname": "UserService", "line": 42, "allow_lazy": False}`}</CodeBlock>
      </section>

      {/* Provider Protocol */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Provider Protocol</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          All providers implement the <code className="text-aquilia-500">Provider</code> protocol — a runtime-checkable <code className="text-aquilia-500">Protocol</code> class with three requirements:
        </p>
        <CodeBlock language="python" filename="Provider Protocol">{`from typing import Protocol, runtime_checkable

@runtime_checkable
class Provider(Protocol):
    @property
    def meta(self) -> ProviderMeta:
        """Provider metadata (name, token, scope, tags, etc.)."""
        ...
    
    async def instantiate(self, ctx: ResolveCtx) -> Any:
        """Create or retrieve the service instance."""
        ...
    
    async def shutdown(self) -> None:
        """Cleanup resources (called during container shutdown)."""
        ...`}</CodeBlock>
        <p className={`mt-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          You can implement custom providers by satisfying this protocol. The <code className="text-aquilia-500">runtime_checkable</code> decorator enables <code className="text-aquilia-500">isinstance(obj, Provider)</code> checks.
        </p>
      </section>

      {/* Token Resolution Internals */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Token Resolution Internals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Tokens are normalized to strings via <code className="text-aquilia-500">_token_to_key()</code>. For type tokens, the result is cached in the module-level <code className="text-aquilia-500">_type_key_cache</code> dict to avoid repeated <code className="text-aquilia-500">f"&#123;cls.__module__&#125;.&#123;cls.__qualname__&#125;"</code> string construction. Cache keys combine the token key with the optional tag:
        </p>
        <CodeBlock language="python" filename="Internal Key Functions">{`# _token_to_key: type → string (cached)
_type_key_cache: dict[type, str] = {}

def _token_to_key(token):
    if isinstance(token, type):
        key = f"{token.__module__}.{token.__qualname__}"
        _type_key_cache[token] = key
        return key
    return str(token)

# _make_cache_key: combines token key + tag
def _make_cache_key(token_key: str, tag: str | None) -> str:
    return f"{token_key}:{tag}" if tag else token_key

# _lookup_provider: searches current container, then parent chain
def _lookup_provider(token_key: str, tag: str | None):
    provider = self._providers.get(cache_key)
    if provider is None and self._parent:
        return self._parent._lookup_provider(token_key, tag)
    return provider`}</CodeBlock>
      </section>

      {/* _NullLifecycleType */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>_NullLifecycleType</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Request-scoped containers use <code className="text-aquilia-500">_NullLifecycleType</code> — a singleton no-op lifecycle that avoids the overhead of hook management for short-lived containers. All methods (<code className="text-aquilia-500">on_startup</code>, <code className="text-aquilia-500">on_shutdown</code>, <code className="text-aquilia-500">register_finalizer</code>, etc.) are no-ops.
        </p>
        <CodeBlock language="python" filename="No-op Lifecycle">{`class _NullLifecycleType:
    """Singleton no-op lifecycle for request-scoped containers."""
    def on_startup(self, *a, **kw): pass
    def on_shutdown(self, *a, **kw): pass
    def register_finalizer(self, *a, **kw): pass
    async def run_startup_hooks(self): pass
    async def run_shutdown_hooks(self): pass
    async def run_finalizers(self): pass
    def clear(self): pass

_NullLifecycle = _NullLifecycleType()  # Module-level singleton`}</CodeBlock>
      </section>

      {/* Cacheable Scopes */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Caching Behavior by Scope</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Scope</th>
              <th className="text-left py-3 pr-4">Cached?</th>
              <th className="text-left py-3 pr-4">Where Cached</th>
              <th className="text-left py-3">Behavior</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['singleton', 'Yes', 'Parent (root)', 'One instance for the entire process. Delegates to parent.'],
                ['app', 'Yes', 'Parent (root)', 'Same as singleton — cached at app level. Delegates to parent.'],
                ['request', 'Yes', 'Child', 'One instance per request container. Cleared on shutdown.'],
                ['transient', 'No', '—', 'New instance on every resolve_async() call.'],
                ['pooled', 'Yes', 'Pool queue', 'Managed by PoolProvider\'s asyncio.Queue. acquire/release.'],
                ['ephemeral', 'No', '—', 'Like transient but with request→ephemeral parent hierarchy.'],
              ].map(([scope, cached, where, behavior], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{scope}</code></td>
                  <td className="py-3 pr-4">{cached}</td>
                  <td className="py-3 pr-4">{where}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{behavior}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/overview" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> DI Overview
        </Link>
        <Link to="/docs/di/providers" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          Providers <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}