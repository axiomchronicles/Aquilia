import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Key } from 'lucide-react'

export function SessionsPolicies() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Key className="w-4 h-4" />
          Sessions / Policies
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Session Policies
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Policies control session behavior — persistence rules, concurrency limits, expiration, and transport configuration.
        </p>
      </div>

      {/* SessionPolicy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SessionPolicy</h2>
        <CodeBlock language="python" filename="policy.py">{`from aquilia.sessions import SessionPolicy

policy = SessionPolicy(
    max_age=3600,                  # 1 hour
    idle_timeout=900,              # 15 minutes of inactivity
    regenerate_id_on_auth=True,    # Prevent session fixation
    require_https=True,            # Reject non-HTTPS sessions
    max_sessions_per_user=3,       # Concurrency limit
    cleanup_interval=300,          # Expired session cleanup
)`}</CodeBlock>
      </section>

      {/* PersistencePolicy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PersistencePolicy</h2>
        <CodeBlock language="python" filename="persistence.py">{`from aquilia.sessions import PersistencePolicy

# ON_CHANGE — write only when session data changes (default)
policy = PersistencePolicy.ON_CHANGE

# ON_EVERY_REQUEST — write on every request
policy = PersistencePolicy.ON_EVERY_REQUEST

# MANUAL — only write when session.save() is called
policy = PersistencePolicy.MANUAL`}</CodeBlock>
      </section>

      {/* ConcurrencyPolicy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ConcurrencyPolicy</h2>
        <CodeBlock language="python" filename="concurrency.py">{`from aquilia.sessions import ConcurrencyPolicy

# ALLOW — no limits
policy = ConcurrencyPolicy.ALLOW

# DENY_NEW — reject new sessions when limit reached
policy = ConcurrencyPolicy.DENY_NEW

# EVICT_OLDEST — destroy oldest session when limit reached
policy = ConcurrencyPolicy.EVICT_OLDEST

# EVICT_LRU — destroy least recently used session
policy = ConcurrencyPolicy.EVICT_LRU`}</CodeBlock>
      </section>

      {/* Policy Properties */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Policy Reference</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Property</th>
                <th className="py-3 px-4 text-left font-semibold">Type</th>
                <th className="py-3 px-4 text-left font-semibold">Default</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['max_age', 'int', '3600', 'Maximum session age in seconds'],
                ['idle_timeout', 'int | None', 'None', 'Max idle time before expiry'],
                ['regenerate_id_on_auth', 'bool', 'True', 'New session ID on login'],
                ['require_https', 'bool', 'False', 'Reject HTTP sessions'],
                ['max_sessions_per_user', 'int | None', 'None', 'Max concurrent sessions'],
                ['persistence', 'PersistencePolicy', 'ON_CHANGE', 'When to persist'],
                ['concurrency', 'ConcurrencyPolicy', 'ALLOW', 'What to do at limit'],
                ['cleanup_interval', 'int', '300', 'Seconds between cleanup runs'],
              ].map(([prop, type, def_, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{prop}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{type}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{def_}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
