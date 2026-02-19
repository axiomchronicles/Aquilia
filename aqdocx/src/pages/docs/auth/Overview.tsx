import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'

export function AuthOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Shield className="w-4 h-4" />Security &amp; Auth</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            AquilAuth — Authentication
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's auth system is built on three pillars: <code className="text-aquilia-500">Identity</code> (the principal), <code className="text-aquilia-500">Credential</code> (proof of identity), and <code className="text-aquilia-500">Guard</code> (policy enforcement). Everything is async-first and integrates with the DI system.
        </p>
      </div>

      {/* Architecture SVG */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auth Architecture</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 660 200" className="w-full h-auto">
            <rect width="660" height="200" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {[
              { x: 30, w: 120, label: 'Request', sub: 'Authorization header', color: '#3b82f6' },
              { x: 170, w: 120, label: 'Authenticator', sub: 'Extract credential', color: '#f59e0b' },
              { x: 310, w: 120, label: 'Identity', sub: 'Resolve principal', color: '#22c55e' },
              { x: 450, w: 100, label: 'Guard', sub: 'Check policy', color: '#ef4444' },
              { x: 570, w: 70, label: 'Handler', sub: '', color: '#8b5cf6' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y="40" width={b.w} height="55" rx="10" fill={b.color + '15'} stroke={b.color} strokeWidth="1.5" />
                <text x={b.x + b.w / 2} y="63" textAnchor="middle" fill={b.color} fontSize="13" fontWeight="700">{b.label}</text>
                {b.sub && <text x={b.x + b.w / 2} y="80" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">{b.sub}</text>}
                {i < 4 && <line x1={b.x + b.w} y1={67} x2={b.x + b.w + 20} y2={67} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#authArrow)" />}
              </g>
            ))}

            {/* Credential types */}
            <text x="330" y="130" textAnchor="middle" fill={isDark ? '#555' : '#94a3b8'} fontSize="11" fontWeight="600">CREDENTIAL TYPES</text>
            {[
              { x: 80, label: 'Password', desc: 'Argon2id' },
              { x: 230, label: 'API Key', desc: 'ak_live_...' },
              { x: 380, label: 'JWT Token', desc: 'Bearer ...' },
              { x: 520, label: 'Session', desc: 'Cookie-based' },
            ].map((c, i) => (
              <g key={i}>
                <rect x={c.x} y="145" width={120} height="35" rx="8" fill={isDark ? '#111' : '#f1f5f9'} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1" />
                <text x={c.x + 60} y="162" textAnchor="middle" fill={isDark ? '#ccc' : '#334155'} fontSize="11" fontWeight="600">{c.label}</text>
                <text x={c.x + 60} y="175" textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="9">{c.desc}</text>
              </g>
            ))}

            <defs>
              <marker id="authArrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#333' : '#cbd5e1'} /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Start</h2>
        <CodeBlock language="python" filename="Auth Usage">{`from aquilia.auth.core import Identity, IdentityType, IdentityStatus

# Create an identity (typically from your user database)
identity = Identity(
    id="user_42",
    type=IdentityType.USER,
    attributes={
        "email": "alice@example.com",
        "name": "Alice",
        "roles": ["admin", "editor"],
        "scopes": ["read", "write"],
    },
    status=IdentityStatus.ACTIVE,
    tenant_id="org_123",
)

# Check permissions
identity.has_role("admin")     # True
identity.has_scope("write")    # True
identity.is_active()           # True

# Access in controller via RequestCtx
@Get("/me")
async def me(self, ctx):
    identity = ctx.identity
    if not identity or not identity.is_active():
        return Response.json({"error": "Unauthorized"}, status=401)
    return ctx.json(identity.to_dict())`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Identity Model</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Field</th>
              <th className="text-left py-3 pr-4 text-aquilia-500">Type</th>
              <th className="text-left py-3 text-aquilia-500">Description</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['id', 'str', 'Stable unique identifier (never changes)'],
                ['type', 'IdentityType', 'USER, SERVICE, DEVICE, or ANONYMOUS'],
                ['attributes', 'dict[str, Any]', 'Flexible ABAC attributes — email, roles, scopes, etc.'],
                ['status', 'IdentityStatus', 'ACTIVE, SUSPENDED, DELETED, PENDING'],
                ['tenant_id', 'str | None', 'Multi-tenant organization ID'],
                ['created_at', 'datetime', 'Creation timestamp'],
                ['updated_at', 'datetime', 'Last update timestamp'],
              ].map(([f, t, d], i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400">{f}</td>
                  <td className="py-2 pr-4 font-mono text-xs text-gray-500">{t}</td>
                  <td className={`py-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
