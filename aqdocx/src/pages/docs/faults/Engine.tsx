import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { AlertTriangle } from 'lucide-react'

export function FaultsEngine() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><AlertTriangle className="w-4 h-4" />Advanced</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Engine</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Fault Engine processes faults based on their recovery strategy, manages circuit breakers, and converts faults into HTTP responses for the client.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Processing Flow</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 660 250" className="w-full h-auto">
            <rect width="660" height="250" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {/* Flow */}
            {[
              { x: 30, y: 40, w: 110, label: 'Fault Raised', color: '#ef4444' },
              { x: 170, y: 40, w: 110, label: 'Classify', color: '#f59e0b' },
              { x: 310, y: 40, w: 110, label: 'Strategy', color: '#3b82f6' },
              { x: 450, y: 40, w: 110, label: 'Execute', color: '#22c55e' },
              { x: 570, y: 40, w: 70, label: 'Result', color: '#8b5cf6' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y={b.y} width={b.w} height="45" rx="10" fill={b.color + '15'} stroke={b.color} strokeWidth="1.5" />
                <text x={b.x + b.w / 2} y={b.y + 28} textAnchor="middle" fill={b.color} fontSize="12" fontWeight="700">{b.label}</text>
                {i < 4 && <line x1={b.x + b.w} y1={b.y + 22} x2={b.x + b.w + 30} y2={b.y + 22} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#faultArrow)" />}
              </g>
            ))}

            {/* Strategy branches */}
            {[
              { x: 80, y: 130, label: 'PROPAGATE', desc: 'Bubble up', color: '#ef4444' },
              { x: 220, y: 130, label: 'RETRY', desc: 'Backoff + retry', color: '#f59e0b' },
              { x: 340, y: 130, label: 'FALLBACK', desc: 'Use default', color: '#22c55e' },
              { x: 460, y: 130, label: 'MASK', desc: 'Log & suppress', color: '#3b82f6' },
              { x: 540, y: 130, label: 'BREAK', desc: 'Circuit breaker', color: '#8b5cf6' },
            ].map((s, i) => (
              <g key={i}>
                <rect x={s.x} y={s.y} width={100} height="40" rx="8" fill={isDark ? '#111' : '#f1f5f9'} stroke={s.color} strokeWidth="1" />
                <text x={s.x + 50} y={s.y + 18} textAnchor="middle" fill={s.color} fontSize="10" fontWeight="700">{s.label}</text>
                <text x={s.x + 50} y={s.y + 32} textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="9">{s.desc}</text>
              </g>
            ))}

            {/* Output */}
            <rect x="180" y="200" width="300" height="35" rx="8" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#22c55e" strokeWidth="1.5" />
            <text x="330" y="222" textAnchor="middle" fill="#22c55e" fontSize="12" fontWeight="600">HTTP Response (JSON or Debug Page)</text>

            <defs>
              <marker id="faultArrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#333' : '#cbd5e1'} /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault → HTTP Response</h2>
        <CodeBlock language="python" filename="Response Mapping">{`# Faults with status are mapped directly to HTTP responses:
# Fault(code="NOT_FOUND", status=404, public=True)
# → {"error": {"code": "NOT_FOUND", "message": "..."}, "status": 404}

# Faults with public=False hide internal details:
# → {"error": {"code": "INTERNAL_ERROR", "message": "An error occurred"}}

# In debug mode, full fault details are exposed:
# → {"error": {"code": "...", "message": "...", "domain": "...", 
#     "severity": "...", "context": {...}, "traceback": "..."}}`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Retry with Backoff</h2>
        <CodeBlock language="python" filename="Retry Strategy">{`from aquilia.faults import Fault, RecoveryStrategy, Severity, FaultDomain

# Mark a fault as retryable
raise Fault(
    code="DB_TIMEOUT",
    message="Database connection timed out",
    domain=FaultDomain.IO,
    severity=Severity.WARN,
    retryable=True,
    recovery=RecoveryStrategy.RETRY,
    context={"max_retries": 3, "backoff_factor": 2.0},
)

# The fault engine will:
# 1. Wait 1s, retry
# 2. Wait 2s, retry
# 3. Wait 4s, retry
# 4. If still failing, propagate as ERROR`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Circuit Breaker</h2>
        <CodeBlock language="python" filename="Circuit Breaker">{`# When recovery=CIRCUIT_BREAK, the fault engine tracks failures
# for the affected service and trips the circuit after a threshold

raise Fault(
    code="SERVICE_UNAVAILABLE",
    message="Payment service is down",
    domain=FaultDomain.IO,
    severity=Severity.ERROR,
    recovery=RecoveryStrategy.CIRCUIT_BREAK,
    context={"service": "payments", "threshold": 5, "timeout": 60},
)

# After 5 failures within the window:
# - Circuit opens → immediate FALLBACK for subsequent calls
# - After 60s → half-open → next call is a probe
# - If probe succeeds → circuit closes`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Domain-Specific Faults</h2>
        <CodeBlock language="python" filename="Domain Faults">{`from aquilia.faults.domains import (
    QueryFault,           # Model queries
    ValidationFault,      # Serializer validation
    MigrationFault,       # Migration errors
    MigrationConflictFault,
    SchemaFault,          # Schema issues
)

# These inherit from Fault with pre-set domains:
raise QueryFault(
    model="User",
    operation="create",
    reason="Cannot create record with empty data",
)
# → Fault(code="QUERY_ERROR", domain=FaultDomain.MODEL, ...)`}</CodeBlock>
      </section>
    </div>
  )
}
