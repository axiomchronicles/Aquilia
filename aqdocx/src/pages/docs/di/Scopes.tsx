import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box } from 'lucide-react'

export function DIScopes() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const scopes = [
    { name: 'singleton', color: '#22c55e', cacheable: true, desc: 'One instance for the entire application lifecycle. Shared across all requests. Ideal for database pools, config objects.' },
    { name: 'app', color: '#3b82f6', cacheable: true, desc: 'Alias for singleton — one instance per app. Semantically distinct for clarity.' },
    { name: 'request', color: '#f59e0b', cacheable: true, desc: 'One instance per HTTP request. Automatically cleaned up when the request container shuts down. Parent scope: app.' },
    { name: 'transient', color: '#ef4444', cacheable: false, desc: 'New instance on every resolve() call. Never cached. Use for stateless utilities or lightweight objects.' },
    { name: 'pooled', color: '#8b5cf6', cacheable: false, desc: 'Drawn from a managed pool of pre-created instances. Useful for expensive resources like connections.' },
    { name: 'ephemeral', color: '#ec4899', cacheable: true, desc: 'Short-lived, request-scoped. Same injection rules as request. Parent scope: request.' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scopes &amp; Lifetimes</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Scopes control how long an instance lives and where it can be injected. Aquilia enforces scope rules at resolution time — a request-scoped provider can never be injected into a singleton.
        </p>
      </div>

      {/* Scope hierarchy SVG */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope Hierarchy</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 600 280" className="w-full h-auto">
            <rect width="600" height="280" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {/* Singleton/App layer */}
            <rect x="30" y="20" width="540" height="70" rx="12" fill="#22c55e11" stroke="#22c55e" strokeWidth="2" />
            <text x="300" y="45" textAnchor="middle" fill="#22c55e" fontSize="14" fontWeight="700">singleton / app</text>
            <text x="300" y="65" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="11">Cached • Lives for entire application</text>

            {/* Request layer */}
            <rect x="80" y="110" width="440" height="70" rx="12" fill="#f59e0b11" stroke="#f59e0b" strokeWidth="2" />
            <text x="300" y="135" textAnchor="middle" fill="#f59e0b" fontSize="14" fontWeight="700">request</text>
            <text x="300" y="155" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="11">Cached • Lives for one HTTP request • Parent: app</text>

            {/* Ephemeral */}
            <rect x="130" y="200" width="160" height="55" rx="12" fill="#ec489911" stroke="#ec4899" strokeWidth="1.5" />
            <text x="210" y="225" textAnchor="middle" fill="#ec4899" fontSize="13" fontWeight="700">ephemeral</text>
            <text x="210" y="242" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">Parent: request</text>

            {/* Transient (outside) */}
            <rect x="340" y="200" width="120" height="55" rx="12" fill="#ef444411" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 3" />
            <text x="400" y="225" textAnchor="middle" fill="#ef4444" fontSize="13" fontWeight="700">transient</text>
            <text x="400" y="242" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">Never cached</text>

            {/* Arrows */}
            <line x1="300" y1="90" x2="300" y2="110" stroke={isDark ? '#444' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#scopeArrow)" />
            <line x1="210" y1="180" x2="210" y2="200" stroke={isDark ? '#444' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#scopeArrow)" />

            <defs>
              <marker id="scopeArrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#444' : '#cbd5e1'} /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope Reference</h2>
        <div className="space-y-4">
          {scopes.map((s, i) => (
            <div key={i} className={`p-5 rounded-xl border ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-3 mb-2">
                <span className="px-3 py-1 rounded-full text-xs font-bold" style={{ background: s.color + '22', color: s.color }}>{s.name}</span>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{s.cacheable ? '● Cached' : '○ Not cached'}</span>
              </div>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Injection Rules</h2>
        <CodeBlock language="python" filename="aquilia/di/scopes.py">{`class Scope:
    def can_inject_into(self, other: "Scope") -> bool:
        # Singleton/app/transient/pooled → can inject into anything
        if self.name in ("singleton", "app", "transient", "pooled"):
            return True

        # Request/ephemeral → CANNOT inject into singleton/app
        if self.name in ("request", "ephemeral"):
            return other.name not in ("singleton", "app")

        return True

# ✅ OK: singleton → request (long-lived into short-lived)
# ✅ OK: transient → anything
# ❌ ERROR: request → singleton (short-lived into long-lived)`}</CodeBlock>
        <div className={`mt-4 p-4 rounded-xl border-l-4 border-red-500 ${isDark ? 'bg-red-500/10' : 'bg-red-50'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <strong>Scope violation:</strong> Injecting a request-scoped service into a singleton would cause the singleton to hold a stale reference after the request ends. The <code>ScopeValidator</code> prevents this at registration time.
          </p>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using Scopes</h2>
        <CodeBlock language="python" filename="Scope Examples">{`from aquilia.di.decorators import service

# Singleton — database pool, shared config
@service(scope="singleton")
class DatabasePool:
    async def async_init(self):
        self.pool = await asyncpg.create_pool(...)

# Request — per-request unit of work
@service(scope="request")
class UnitOfWork:
    def __init__(self, db: DatabasePool):  # ✅ singleton into request
        self.db = db
        self.changes = []

# Transient — always fresh
@service(scope="transient")
class UUIDGenerator:
    def __init__(self):
        self.value = uuid.uuid4()

# Ephemeral — short burst within request
@service(scope="ephemeral")
class TempCalculator:
    pass`}</CodeBlock>
      </section>
    </div>
  )
}
