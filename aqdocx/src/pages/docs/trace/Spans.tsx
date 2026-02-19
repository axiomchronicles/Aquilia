import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Activity } from 'lucide-react'

export function TraceSpans() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Activity className="w-4 h-4" />
          Trace / Spans & Exporters
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Tracing — Spans & Exporters
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">AquiliaTracer</code> provides distributed tracing with automatic span creation for requests, DB queries, cache operations, and template rendering. Export to Jaeger, Zipkin, or any OpenTelemetry-compatible backend.
        </p>
      </div>

      {/* AquiliaTracer */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquiliaTracer</h2>
        <CodeBlock language="python" filename="tracer.py">{`from aquilia.trace import AquiliaTracer, Span, SpanKind

tracer = AquiliaTracer(
    service_name="myapp",
    sample_rate=1.0,           # 100% sampling (dev)
    # sample_rate=0.01,        # 1% sampling (prod)
)

# Manual span creation
async with tracer.span("process_order", kind=SpanKind.INTERNAL) as span:
    span.set_attribute("order_id", 42)
    span.set_attribute("user_id", 7)
    
    # Nested span
    async with tracer.span("validate_inventory") as child:
        child.set_attribute("product_count", 3)
        await check_inventory(items)
    
    await charge_payment(order)
    span.set_attribute("status", "completed")`}</CodeBlock>
      </section>

      {/* Auto-instrumentation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Instrumentation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The tracing middleware automatically creates spans for every request, with child spans for DB, cache, and template operations.
        </p>
        <CodeBlock language="python" filename="auto.py">{`from aquilia.trace import TracingMiddleware

# Automatically creates spans:
# - HTTP request (method, path, status, duration)
# - Database queries (query type, table, duration)
# - Cache operations (hit/miss, key, backend)
# - Template rendering (template name, duration)
# - Mail sending (provider, recipient count)

stack.add(TracingMiddleware(tracer=tracer))`}</CodeBlock>
      </section>

      {/* Exporters */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Exporters</h2>
        <div className="space-y-4">
          {[
            { name: 'ConsoleExporter', code: `from aquilia.trace import ConsoleExporter\ntracer.add_exporter(ConsoleExporter(verbose=True))` },
            { name: 'JaegerExporter', code: `from aquilia.trace import JaegerExporter\ntracer.add_exporter(JaegerExporter(\n    endpoint="http://localhost:14268/api/traces"\n))` },
            { name: 'ZipkinExporter', code: `from aquilia.trace import ZipkinExporter\ntracer.add_exporter(ZipkinExporter(\n    endpoint="http://localhost:9411/api/v2/spans"\n))` },
            { name: 'OTLPExporter', code: `from aquilia.trace import OTLPExporter\ntracer.add_exporter(OTLPExporter(\n    endpoint="http://localhost:4317",\n    protocol="grpc",\n))` },
          ].map((e, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-sm mb-3 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{e.name}</h3>
              <CodeBlock language="python" filename="exporter.py">{e.code}</CodeBlock>
            </div>
          ))}
        </div>
      </section>

      {/* Span Attributes */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Standard Attributes</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Attribute</th>
                <th className="py-3 px-4 text-left font-semibold">Span Type</th>
                <th className="py-3 px-4 text-left font-semibold">Example</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['http.method', 'Request', '"GET"'],
                ['http.path', 'Request', '"/api/users/42"'],
                ['http.status_code', 'Request', '200'],
                ['db.system', 'Database', '"sqlite"'],
                ['db.statement', 'Database', '"SELECT * FROM users"'],
                ['cache.operation', 'Cache', '"get"'],
                ['cache.hit', 'Cache', 'true'],
                ['template.name', 'Template', '"users/list.html"'],
              ].map(([attr, type, ex], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{attr}</td>
                  <td className="py-2.5 px-4 text-xs">{type}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{ex}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
