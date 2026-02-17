import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { AlertTriangle } from 'lucide-react'

export function FaultsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><AlertTriangle className="w-4 h-4" />Advanced</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquilaFaults — Fault System</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Faults are <em>not</em> bare exceptions — they are first-class structured values with machine-readable codes, severity levels, domain classification, and recovery strategies. They can be raised <em>or</em> returned.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating a Fault</h2>
        <CodeBlock language="python" filename="Fault Usage">{`from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy

# Raise a fault
raise Fault(
    code="USER_NOT_FOUND",
    message="No user with the given ID exists",
    domain=FaultDomain.MODEL,
    severity=Severity.ERROR,
    status=404,
    public=True,          # Safe to expose to client
    retryable=False,
    recovery=RecoveryStrategy.PROPAGATE,
    context={"user_id": 42},
)

# Or return it from a handler (Flow Engine supports both)
return Fault(code="RATE_LIMITED", message="Too many requests", status=429)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Severity Levels</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { level: 'INFO', color: '#3b82f6', desc: 'Informational, no action' },
            { level: 'WARN', color: '#f59e0b', desc: 'Should be reviewed' },
            { level: 'ERROR', color: '#ef4444', desc: 'Immediate attention' },
            { level: 'FATAL', color: '#dc2626', desc: 'Unrecoverable, abort' },
          ].map((s, i) => (
            <div key={i} className={`p-4 rounded-xl border text-center ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
              <div className="font-mono font-bold text-sm" style={{ color: s.color }}>{s.level}</div>
              <p className={`mt-1 text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Domains</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Domain</th>
              <th className="text-left py-3 pr-4 text-aquilia-500">Defaults</th>
              <th className="text-left py-3 text-aquilia-500">Description</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['CONFIG', 'FATAL, not retryable', 'Configuration errors'],
                ['REGISTRY', 'FATAL, not retryable', 'Aquilary registry errors'],
                ['DI', 'ERROR, not retryable', 'Dependency injection errors'],
                ['ROUTING', 'ERROR, not retryable', 'Route matching errors'],
                ['FLOW', 'ERROR, not retryable', 'Handler execution errors'],
                ['EFFECT', 'ERROR, retryable', 'Side effect failures'],
                ['IO', 'WARN, retryable', 'I/O operations'],
                ['SECURITY', 'ERROR, not retryable', 'Security and auth'],
                ['MODEL', 'ERROR, not retryable', 'Model ORM and database'],
                ['SERIALIZATION', 'WARN, not retryable', 'Serializer validation'],
                ['CACHE', 'ERROR, retryable', 'Cache subsystem'],
                ['SYSTEM', 'FATAL, not retryable', 'System level faults'],
              ].map(([domain, defaults, desc], i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400">{domain}</td>
                  <td className={`py-2 pr-4 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{defaults}</td>
                  <td className={`py-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Recovery Strategies</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { name: 'PROPAGATE', desc: 'Default — bubble up to the next handler in the chain.' },
            { name: 'RETRY', desc: 'Retry the operation with exponential backoff.' },
            { name: 'FALLBACK', desc: 'Return a fallback value instead of failing.' },
            { name: 'MASK', desc: 'Suppress the error (log only, don\'t propagate).' },
            { name: 'CIRCUIT_BREAK', desc: 'Trip the circuit breaker — stop calling the failing service.' },
          ].map((r, i) => (
            <div key={i} className={`p-4 rounded-xl border ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
              <span className="text-aquilia-500 font-mono font-bold text-sm">{r.name}</span>
              <p className={`mt-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{r.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Domains</h2>
        <CodeBlock language="python" filename="Custom Domain">{`# Create a module-specific domain
TASKS_DOMAIN = FaultDomain.custom("TASKS", "Background task errors")

# Use it
raise Fault(
    code="TASK_TIMEOUT",
    message="Background task exceeded deadline",
    domain=TASKS_DOMAIN,
    severity=Severity.ERROR,
    retryable=True,
    recovery=RecoveryStrategy.RETRY,
)`}</CodeBlock>
      </section>
    </div>
  )
}
