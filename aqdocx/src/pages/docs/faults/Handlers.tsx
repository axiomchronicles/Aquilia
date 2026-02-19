import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { AlertTriangle } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function FaultsHandlers() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <AlertTriangle className="w-4 h-4" />
          Faults / Handlers
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Fault Handlers
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-400">FaultEngine</code> dispatches faults to registered handlers in priority order. Aquilia ships with 7 default handlers and supports custom handler registration.
        </p>
      </div>

      {/* FaultEngine */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FaultEngine</h2>
        <CodeBlock language="python" filename="engine.py">{`from aquilia.faults import FaultEngine, FaultHandler

engine = FaultEngine()

# Register a handler for specific domains
engine.register(
    handler=my_handler,
    domains=["MODEL", "SERIALIZER"],
    priority=10,  # Lower = higher priority
)

# Register a catch-all handler
engine.register(handler=fallback_handler, domains=["*"], priority=99)

# Process a fault
result = await engine.handle(fault)
# result is a FaultResult: continue, abort, retry, or propagate`}</CodeBlock>
      </section>

      {/* Default Handlers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Default Handlers</h2>
        <div className="space-y-4">
          {[
            { name: 'ValidationFaultHandler', domain: 'SERIALIZER', desc: 'Converts validation faults to 422 responses with field-level error details.', priority: 10 },
            { name: 'AuthFaultHandler', domain: 'SECURITY', desc: 'Returns 401/403 responses. Strips sensitive details in production.', priority: 10 },
            { name: 'NotFoundFaultHandler', domain: 'MODEL, ROUTING', desc: 'Returns 404 with resource identification. Suggests similar routes.', priority: 15 },
            { name: 'RateLimitFaultHandler', domain: 'MIDDLEWARE', desc: 'Returns 429 with Retry-After header. Logs abuse patterns.', priority: 20 },
            { name: 'DatabaseFaultHandler', domain: 'MODEL', desc: 'Handles constraint violations, deadlocks, connection failures. May retry.', priority: 25 },
            { name: 'LoggingFaultHandler', domain: '*', desc: 'Logs all faults with structured metadata. Configurable severity filter.', priority: 50 },
            { name: 'FallbackFaultHandler', domain: '*', desc: 'Catch-all returning 500. Hides stack traces in production.', priority: 99 },
          ].map((h, i) => (
            <div key={i} className={box}>
              <div className="flex items-center justify-between mb-2">
                <h3 className={`font-mono font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{h.name}</h3>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-mono px-2 py-0.5 rounded ${isDark ? 'bg-aquilia-500/20 text-aquilia-400' : 'bg-aquilia-50 text-aquilia-600'}`}>{h.domain}</span>
                  <span className={`text-xs font-mono px-2 py-0.5 rounded ${isDark ? 'bg-white/5 text-gray-400' : 'bg-gray-100 text-gray-500'}`}>p={h.priority}</span>
                </div>
              </div>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{h.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Custom Handler */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Handler</h2>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.faults import FaultHandler, Fault, FaultResult

class SlackAlertHandler(FaultHandler):
    """Send critical faults to Slack."""
    
    async def handle(self, fault: Fault) -> FaultResult:
        if fault.severity >= Severity.CRITICAL:
            await self.slack_client.send(
                channel="#alerts",
                text=f"🚨 {fault.code}: {fault.message}",
                attachments=[{
                    "fields": [
                        {"title": k, "value": str(v)}
                        for k, v in fault.context.items()
                    ]
                }],
            )
        # Always propagate — this handler only observes
        return FaultResult.propagate(fault)

engine.register(
    handler=SlackAlertHandler(slack_client),
    domains=["*"],
    priority=5,  # Run before default handlers
)`}</CodeBlock>
      </section>

      {/* FaultMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FaultMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-400">FaultMiddleware</code> catches unhandled exceptions and converts them to faults automatically.
        </p>
        <CodeBlock language="python" filename="middleware.py">{`from aquilia.faults import FaultMiddleware

# Added automatically by AquiliaServer
# Wraps every request in a try/except that converts
# exceptions → Fault objects → FaultEngine.handle()

# Configuration
FaultMiddleware(
    engine=fault_engine,
    expose_details=False,      # Hide internals in production
    log_unhandled=True,        # Log exceptions before conversion
    default_status=500,        # Default HTTP status for unknown faults
)`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}