import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box } from 'lucide-react'

export function DIOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Injection Overview</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia ships with a full-featured DI container — hierarchical scopes, async resolution, cycle detection via Tarjan's algorithm, provider manifests, and diagnostics. Cached lookups run in under 3µs.
        </p>
      </div>

      {/* Architecture SVG */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>System Architecture</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 720 360" className="w-full h-auto">
            {/* Background */}
            <rect width="720" height="360" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {/* Registry */}
            <rect x="40" y="30" width="200" height="60" rx="12" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#22c55e" strokeWidth="2">
              <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite" />
            </rect>
            <text x="140" y="57" textAnchor="middle" fill="#22c55e" fontSize="14" fontWeight="700">Registry</text>
            <text x="140" y="77" textAnchor="middle" fill={isDark ? '#888' : '#64748b'} fontSize="11">Manifests → Graph → Validate</text>

            {/* Container */}
            <rect x="260" y="30" width="200" height="60" rx="12" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#22c55e" strokeWidth="2" />
            <text x="360" y="57" textAnchor="middle" fill="#22c55e" fontSize="14" fontWeight="700">Container (App)</text>
            <text x="360" y="77" textAnchor="middle" fill={isDark ? '#888' : '#64748b'} fontSize="11">register / resolve_async</text>

            {/* Arrow Registry → Container */}
            <line x1="240" y1="60" x2="260" y2="60" stroke="#22c55e" strokeWidth="2" markerEnd="url(#arrow)" />

            {/* Child Container */}
            <rect x="480" y="30" width="200" height="60" rx="12" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#22c55e" strokeWidth="1.5" strokeDasharray="6 3" />
            <text x="580" y="57" textAnchor="middle" fill="#22c55e" fontSize="14" fontWeight="700">Request Container</text>
            <text x="580" y="77" textAnchor="middle" fill={isDark ? '#888' : '#64748b'} fontSize="11">create_request_scope()</text>

            {/* Arrow Container → Child */}
            <line x1="460" y1="60" x2="480" y2="60" stroke="#22c55e" strokeWidth="2" markerEnd="url(#arrow)" />

            {/* Providers row */}
            {[
              { x: 40, label: 'ClassProvider', desc: 'Resolves __init__ deps' },
              { x: 200, label: 'ValueProvider', desc: 'Pre-built instances' },
              { x: 360, label: 'FactoryProvider', desc: 'Custom factories' },
              { x: 520, label: 'AliasProvider', desc: 'Token aliases' },
            ].map((p, i) => (
              <g key={i}>
                <rect x={p.x} y="130" width="150" height="50" rx="10" fill={isDark ? '#111' : '#f1f5f9'} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1" />
                <text x={p.x + 75} y="152" textAnchor="middle" fill={isDark ? '#e5e5e5' : '#334155'} fontSize="12" fontWeight="600">{p.label}</text>
                <text x={p.x + 75} y="168" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">{p.desc}</text>
              </g>
            ))}

            {/* Scopes row */}
            {[
              { x: 60, label: 'singleton', color: '#22c55e' },
              { x: 180, label: 'app', color: '#3b82f6' },
              { x: 280, label: 'request', color: '#f59e0b' },
              { x: 390, label: 'transient', color: '#ef4444' },
              { x: 510, label: 'pooled', color: '#8b5cf6' },
              { x: 620, label: 'ephemeral', color: '#ec4899' },
            ].map((s, i) => (
              <g key={i}>
                <rect x={s.x} y="220" width="90" height="32" rx="16" fill={s.color + '22'} stroke={s.color} strokeWidth="1.5" />
                <text x={s.x + 45} y="241" textAnchor="middle" fill={s.color} fontSize="11" fontWeight="600">{s.label}</text>
              </g>
            ))}

            <text x="360" y="210" textAnchor="middle" fill={isDark ? '#555' : '#94a3b8'} fontSize="12" fontWeight="600">SCOPES</text>

            {/* Diagnostics */}
            <rect x="200" y="290" width="320" height="45" rx="10" fill={isDark ? '#111' : '#f1f5f9'} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1" />
            <text x="360" y="318" textAnchor="middle" fill={isDark ? '#aaa' : '#475569'} fontSize="12" fontWeight="600">DIDiagnostics — Events • Metrics • Manifest</text>

            <defs>
              <marker id="arrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Start</h2>
        <CodeBlock language="python" filename="DI in Action">{`from aquilia.di.decorators import service, inject
from aquilia.di.core import Container
from typing import Annotated

# 1. Define services
@service(scope="app")
class DatabasePool:
    async def async_init(self):
        self.pool = await create_pool(dsn="postgres://...")

@service(scope="request")
class UserRepository:
    def __init__(self, db: DatabasePool):
        self.db = db

    async def find(self, user_id: int):
        return await self.db.pool.fetchrow("SELECT * FROM users WHERE id=$1", user_id)

# 2. Build container
container = Container(scope="app")
container.register(ClassProvider(DatabasePool, scope="app"))
container.register(ClassProvider(UserRepository, scope="request"))

# 3. Resolve
repo = await container.resolve_async(UserRepository)
user = await repo.find(42)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Concepts</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { title: 'Provider', desc: 'Protocol that knows how to instantiate a dependency — ClassProvider, ValueProvider, FactoryProvider, AliasProvider.' },
            { title: 'ProviderMeta', desc: 'Frozen dataclass with name, token, scope, tags, module, line number. Serialized to di_manifest.json for LSP.' },
            { title: 'Container', desc: 'Manages provider instances and scopes. Supports register(), resolve_async(), bind(), create_request_scope(), shutdown().' },
            { title: 'Registry', desc: 'Builds the provider graph from manifests, detects cycles via Tarjan\'s algorithm, validates cross-app dependencies.' },
            { title: 'ResolveCtx', desc: 'Resolution context tracking the call stack for cycle detection and per-resolution caching.' },
            { title: 'Lifecycle', desc: 'Hooks discovered on resolved instances — on_startup / on_shutdown — run automatically by the container.' },
          ].map((item, i) => (
            <div key={i} className={`p-5 rounded-xl border ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
              <h3 className="text-aquilia-500 font-bold mb-1">{item.title}</h3>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
