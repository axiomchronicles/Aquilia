import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { AlertTriangle } from 'lucide-react'

export function FaultsTaxonomy() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <AlertTriangle className="w-4 h-4" />
          Faults / Taxonomy
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Fault Taxonomy
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia replaces exceptions with a typed fault system. Every error is a <code className="text-aquilia-400">Fault</code> with a domain, severity, context, and optional remediation. The <code className="text-aquilia-400">FaultEngine</code> processes faults through registered handlers.
        </p>
      </div>

      {/* Fault Base */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Class</h2>
        <CodeBlock language="python" filename="fault.py">{`from aquilia.faults import Fault, FaultDomain, Severity

fault = Fault(
    code="MODEL_NOT_FOUND",
    message="Model 'User' does not exist",
    domain=FaultDomain.MODEL,
    severity=Severity.ERROR,
    context={
        "model_name": "User",
        "operation": "lookup",
    },
    remediation="Check that the model is registered in the module manifest.",
)

print(fault.code)          # "MODEL_NOT_FOUND"
print(fault.domain)        # FaultDomain.MODEL
print(fault.severity)      # Severity.ERROR
print(fault.context)       # {"model_name": "User", ...}
print(fault.is_retryable)  # False`}</CodeBlock>
      </section>

      {/* FaultDomain */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FaultDomain</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { name: 'MODEL', desc: 'Model / ORM errors' },
            { name: 'SERIALIZER', desc: 'Validation / serialization' },
            { name: 'SECURITY', desc: 'Auth, authz, CSRF, CORS' },
            { name: 'ROUTING', desc: 'URL resolution failures' },
            { name: 'MIDDLEWARE', desc: 'Middleware chain errors' },
            { name: 'DI', desc: 'Dependency injection failures' },
            { name: 'CACHE', desc: 'Cache operations' },
            { name: 'SOCKET', desc: 'WebSocket errors' },
            { name: 'MAIL', desc: 'Email delivery' },
            { name: 'TEMPLATE', desc: 'Template rendering' },
            { name: 'SESSION', desc: 'Session management' },
            { name: 'CONFIG', desc: 'Configuration loading' },
            { name: 'REGISTRY', desc: 'Module registry' },
            { name: 'EFFECT', desc: 'Effect system' },
            { name: 'SERVER', desc: 'ASGI server errors' },
          ].map((d, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{d.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{d.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Severity */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Severity Levels</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Level</th>
                <th className="py-3 px-4 text-left font-semibold">Behavior</th>
                <th className="py-3 px-4 text-left font-semibold">Retryable</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['DEBUG', 'Logged only, no user impact', 'N/A'],
                ['INFO', 'Informational, may be surfaced', 'N/A'],
                ['WARNING', 'Degraded behavior, continues', 'Sometimes'],
                ['ERROR', 'Operation failed, request aborted', 'Sometimes'],
                ['CRITICAL', 'System-level failure', 'No'],
              ].map(([level, behavior, retry], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className={`py-2.5 px-4 font-mono text-xs font-bold ${
                    level === 'CRITICAL' ? 'text-red-400' :
                    level === 'ERROR' ? 'text-orange-400' :
                    level === 'WARNING' ? 'text-yellow-400' :
                    level === 'INFO' ? 'text-blue-400' : 'text-gray-400'
                  }`}>{level}</td>
                  <td className="py-2.5 px-4 text-xs">{behavior}</td>
                  <td className="py-2.5 px-4 text-xs">{retry}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* FaultResult */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FaultResult</h2>
        <CodeBlock language="python" filename="result.py">{`from aquilia.faults import FaultResult

# FaultResult is a union type for handler outcomes:

# Continue — fault handled, proceed normally
result = FaultResult.continue_()

# Abort — stop processing, return error response
result = FaultResult.abort(status=422, body={"error": "Validation failed"})

# Retry — retry the operation (for retryable faults)
result = FaultResult.retry(delay_ms=100, max_retries=3)

# Propagate — re-raise to the next handler
result = FaultResult.propagate(fault)`}</CodeBlock>
      </section>
    </div>
  )
}
