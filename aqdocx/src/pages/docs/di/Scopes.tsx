import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DIScopes() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Scopes
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Scopes control the lifetime and caching behavior of service instances. Aquilia defines 6 scope levels in <code className="text-aquilia-500">aquilia/di/scopes.py</code> with a strict parent hierarchy and injection validation rules that prevent scope mismatches at build time.
        </p>
      </div>

      {/* ServiceScope Enum */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ServiceScope Enum</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">ServiceScope</code> is a <code className="text-aquilia-500">str</code>-based <code className="text-aquilia-500">Enum</code>, so scope values can be used directly as strings in decorator arguments and manifest entries.
        </p>
        <CodeBlock language="python" filename="ServiceScope Definition">{`from aquilia.di.scopes import ServiceScope

class ServiceScope(str, Enum):
    SINGLETON = "singleton"   # One instance per process
    APP       = "app"         # One instance per app container
    REQUEST   = "request"     # One instance per request container
    TRANSIENT = "transient"   # New instance every resolve
    POOLED    = "pooled"      # Managed by PoolProvider queue
    EPHEMERAL = "ephemeral"   # Like transient, request-parented

# String compatibility:
scope = ServiceScope.REQUEST
assert scope == "request"     # True
assert scope.value == "request"  # True`}</CodeBlock>

        <div className="overflow-x-auto mt-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Scope</th>
              <th className="text-left py-3 pr-4">Lifetime</th>
              <th className="text-left py-3 pr-4">Cached</th>
              <th className="text-left py-3">Use Case</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['SINGLETON', 'Process-wide', 'Yes (root)', 'Database pools, config objects, shared caches. Created once at startup.'],
                ['APP', 'App container', 'Yes (root)', 'App-level services. Functionally identical to singleton in single-app setups.'],
                ['REQUEST', 'Per-request', 'Yes (child)', 'Request-scoped services — user sessions, request loggers, serializers. Cleared on request end.'],
                ['TRANSIENT', 'None', 'No', 'Stateless utilities, formatters, validators. New instance every resolution.'],
                ['POOLED', 'Pool-managed', 'Queue', 'Connection pools, worker threads. Acquired/released via PoolProvider.'],
                ['EPHEMERAL', 'None', 'No', 'Short-lived helpers. Like transient but with request as parent scope.'],
              ].map(([scope, lifetime, cached, usecase], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{scope}</code></td>
                  <td className="py-3 pr-4">{lifetime}</td>
                  <td className="py-3 pr-4">{cached}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{usecase}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Scope Dataclass */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500">Scope</code> Dataclass</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each scope is defined by a <code className="text-aquilia-500">Scope</code> dataclass instance, which configures its behavior:
        </p>
        <CodeBlock language="python" filename="Scope Dataclass">{`from dataclasses import dataclass
from typing import Optional

@dataclass
class Scope:
    name: str                        # Scope identifier
    cacheable: bool                  # Whether instances should be cached
    parent: Optional["Scope"] = None # Parent scope in hierarchy
    
    def can_inject_into(self, consumer_scope: "Scope") -> bool:
        """
        Check if a provider with this scope can be injected
        into a consumer with the given scope.
        
        Rules:
        - Longer-lived scopes can always inject into shorter-lived scopes
        - Shorter-lived scopes CANNOT inject into longer-lived scopes
        - Same scope can always inject into itself
        """
        ...`}</CodeBlock>
      </section>

      {/* SCOPES Registry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>The <code className="text-aquilia-500">SCOPES</code> Registry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia maintains a global registry of valid scopes in <code className="text-aquilia-500">aquilia.di.scopes.SCOPES</code>. This dictionary maps scope names (strings) to <code className="text-aquilia-500">Scope</code> definitions.
        </p>
        <CodeBlock language="python" filename="SCOPES Dict">{`from aquilia.di.scopes import SCOPES

# Pre-built scope instances with parent hierarchy:
SCOPES = {
    "singleton": Scope(name="singleton", cacheable=True),
    "app":       Scope(name="app",       cacheable=True),
    "request":   Scope(name="request",   cacheable=True,  parent=SCOPES["app"]),
    "transient": Scope(name="transient", cacheable=False),
    "pooled":    Scope(name="pooled",    cacheable=True),
    "ephemeral": Scope(name="ephemeral", cacheable=False, parent=SCOPES["request"]),
}

# Parent hierarchy:
#   singleton (no parent — root)
#   app (no parent — root)
#   request → app
#   transient (no parent)
#   pooled (no parent)
#   ephemeral → request → app`}</CodeBlock>
      </section>

      {/* Scope Hierarchy Visualization */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope Hierarchy</h2>
        <div className="w-full">
          <svg viewBox="0 0 600 280" className="w-full h-auto">
            <rect width="600" height="280" rx="16" fill="transparent" />

            {/* Longest-lived label */}
            <text x="20" y="30" fill={isDark ? '#555' : '#94a3b8'} fontSize="10" fontWeight="600">LONGEST-LIVED</text>

            {/* Singleton */}
            <rect x="50" y="45" width="500" height="40" rx="8" fill="#22c55e22" stroke="#22c55e" strokeWidth="1.5" />
            <text x="300" y="70" textAnchor="middle" fill="#22c55e" fontSize="13" fontWeight="700">singleton / app</text>

            {/* Request */}
            <rect x="100" y="100" width="400" height="40" rx="8" fill="#f59e0b22" stroke="#f59e0b" strokeWidth="1.5" />
            <text x="300" y="125" textAnchor="middle" fill="#f59e0b" fontSize="13" fontWeight="700">request</text>

            {/* Ephemeral */}
            <rect x="150" y="155" width="300" height="40" rx="8" fill="#ec489922" stroke="#ec4899" strokeWidth="1.5" />
            <text x="300" y="180" textAnchor="middle" fill="#ec4899" fontSize="13" fontWeight="700">ephemeral</text>

            {/* Transient */}
            <rect x="200" y="210" width="200" height="40" rx="8" fill="#ef444422" stroke="#ef4444" strokeWidth="1.5" />
            <text x="300" y="235" textAnchor="middle" fill="#ef4444" fontSize="13" fontWeight="700">transient</text>

            {/* Shortest-lived label */}
            <text x="20" y="265" fill={isDark ? '#555' : '#94a3b8'} fontSize="10" fontWeight="600">SHORTEST-LIVED</text>

            {/* Arrows */}
            <line x1="545" y1="85" x2="545" y2="100" stroke={isDark ? '#444' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#scope-arrow)" />
            <line x1="495" y1="140" x2="495" y2="155" stroke={isDark ? '#444' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#scope-arrow)" />

            {/* Pooled — separate */}
            <rect x="470" y="155" width="90" height="40" rx="8" fill="#8b5cf622" stroke="#8b5cf6" strokeWidth="1.5" />
            <text x="515" y="180" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="700">pooled</text>

            <defs>
              <marker id="scope-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={isDark ? '#444' : '#cbd5e1'} />
              </marker>
            </defs>
          </svg>
        </div>
        <p className={`mt-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Services can be injected <strong>downward</strong> (singleton → request → ephemeral) but NOT upward. A request-scoped service injected into a singleton would outlive its intended lifetime, leading to stale state.
        </p>
      </section>

      {/* ScopeValidator */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ScopeValidator</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ScopeValidator</code> enforces injection rules at build time (during <code className="text-aquilia-500">Registry.from_manifests()</code>). It prevents scope mismatches by checking whether a provider's scope can be injected into a consumer's scope.
        </p>
        <CodeBlock language="python" filename="ScopeValidator">{`from aquilia.di.scopes import ScopeValidator

class ScopeValidator:
    @staticmethod
    def validate_injection(
        provider_scope: str,
        consumer_scope: str,
    ) -> None:
        """
        Validate that provider_scope can be injected into consumer_scope.
        
        Raises ScopeViolationError if the injection is invalid.
        
        Rules:
        - singleton → anything: ✅ Always valid
        - app → anything: ✅ Always valid
        - request → request, transient, ephemeral: ✅ Valid
        - request → singleton, app: ❌ ScopeViolationError
        - transient → anything: ✅ (no state to leak)
        - ephemeral → ephemeral, transient: ✅ Valid
        - ephemeral → request, app, singleton: ❌ ScopeViolationError
        """
        ...
    
    @staticmethod
    def get_scope_hierarchy() -> list[str]:
        """
        Get scopes ordered from longest to shortest lifetime.
        
        Returns:
            ["singleton", "app", "request", "ephemeral", "transient"]
        """
        ...`}</CodeBlock>
      </section>

      {/* Injection Rules Matrix */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Injection Compatibility Matrix</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          This matrix shows which provider scopes (rows) can be injected into which consumer scopes (columns):
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm text-center ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Provider ↓ / Consumer →</th>
              <th className="py-3 px-2">singleton</th>
              <th className="py-3 px-2">app</th>
              <th className="py-3 px-2">request</th>
              <th className="py-3 px-2">transient</th>
              <th className="py-3 px-2">ephemeral</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['singleton', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
                ['app', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
                ['request', 'No', 'No', 'Yes', 'Yes', 'Yes'],
                ['transient', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
                ['pooled', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
                ['ephemeral', 'No', 'No', 'No', 'Yes', 'Yes'],
              ].map(([scope, ...cells], i) => (
                <tr key={i}>
                  <td className="text-left py-3 pr-4"><code className="text-aquilia-500 text-xs">{scope}</code></td>
                  {cells.map((cell, j) => (
                    <td key={j} className="py-3 px-2">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={`mt-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          No = <code className="text-red-400">ScopeViolationError</code> raised at build time. Transient and pooled providers are always injectable because they carry no cached state that could leak.
        </p>
      </section>

      {/* Scope Violation Examples */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope Violation Example</h2>
        <CodeBlock language="python" filename="Invalid — request-scoped into singleton">{`@service(scope="request")
class RequestLogger:
    def __init__(self, req: Request):
        self.req = req

@service(scope="singleton")
class GlobalAnalytics:
    def __init__(self, logger: RequestLogger):  # ← ScopeViolationError!
        self.logger = logger

# Error message:
# Scope violation: request-scoped provider 'RequestLogger'
# injected into singleton-scoped 'GlobalAnalytics'.
#
# Suggested fixes:
#   - Change 'GlobalAnalytics' to request scope
#   - Change 'RequestLogger' to singleton scope
#   - Use factory/provider pattern to defer instantiation`}</CodeBlock>

        <CodeBlock language="python" filename="Fix — use factory pattern">{`@service(scope="singleton")
class GlobalAnalytics:
    def __init__(self):
        pass
    
    async def track(self, container, event: str):
        # Resolve per-request logger lazily
        logger = await container.resolve_async(RequestLogger)
        logger.info(f"Analytics: {event}")`}</CodeBlock>
      </section>

      {/* Scope Delegation in Containers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope Delegation in Containers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When <code className="text-aquilia-500">resolve_async()</code> encounters a singleton or app-scoped provider in a request container, it automatically delegates to the parent container. This ensures a single shared instance:
        </p>
        <CodeBlock language="python" filename="Scope Delegation Flow">{`# Request container resolving a singleton:
async def resolve_async(self, token, *, tag=None, optional=False):
    provider = self._lookup_provider(token_key, tag)
    
    # Scope delegation: singleton/app → parent
    if provider.meta.scope in ("singleton", "app") and self._parent:
        return await self._parent.resolve_async(token, tag=tag)
    
    # request/transient/ephemeral → resolve in current container
    ...

# Result:
# - Singleton/app: Always resolved and cached in the root container
# - Request: Resolved and cached in the request container
# - Transient/ephemeral: New instance, not cached anywhere`}</CodeBlock>
      </section>

      {/* Choosing the Right Scope */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Choosing the Right Scope</h2>
        <div className="mb-0">
          <div className="space-y-4">
            {[
              { scope: 'singleton', when: 'When the service is expensive to create and stateless or thread-safe. Database pools, config loaders, HTTP clients.', example: '@service(scope="singleton")' },
              { scope: 'app', when: 'When the service should be shared across requests but could be different per app in multi-app setups. Functionally identical to singleton in single-app deployments.', example: '@service(scope="app")' },
              { scope: 'request', when: 'When the service needs per-request state. User sessions, request loggers, authenticated identity, serializers.', example: '@service(scope="request")' },
              { scope: 'transient', when: 'When a fresh instance is always needed. Stateless formatters, validators, DTOs. No caching overhead.', example: '@service(scope="transient")' },
              { scope: 'pooled', when: 'When you need to limit concurrent access to expensive resources. Database connections, worker threads, external API clients.', example: 'PoolProvider(factory=..., max_size=10)' },
              { scope: 'ephemeral', when: 'When you need transient-like behavior but want the scope validator to allow injection from request-scoped parents.', example: '@service(scope="ephemeral")' },
            ].map((item, i) => (
              <div key={i} className="flex gap-4">
                <div className="flex-shrink-0 w-24">
                  <code className="text-aquilia-500 text-xs font-bold">{item.scope}</code>
                </div>
                <div className="flex-1">
                  <p className={`text-sm mb-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.when}</p>
                  <code className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.example}</code>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/providers" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> Providers
        </Link>
        <Link to="/docs/di/decorators" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          Decorators <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}