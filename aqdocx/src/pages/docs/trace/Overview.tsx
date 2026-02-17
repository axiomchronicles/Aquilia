import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, Activity } from 'lucide-react'

export function TraceOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Activity className="w-4 h-4" />
          Tooling / Trace & Debug
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Trace & Debug
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">.aquilia/</code> directory is a project-level trace directory that captures build manifests, DI graphs, route maps, schema ledgers, lifecycle journals, and diagnostics — written on every server startup and updated on shutdown.
        </p>
      </div>

      {/* What's Tracked */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>What's Tracked</h2>
        <div className="space-y-3">
          {[
            { name: 'TraceManifest', desc: 'Registry fingerprint, module graph, and route table — the compiled state of your application.' },
            { name: 'TraceDIGraph', desc: 'Resolved DI providers, scopes, and dependency tree — a complete picture of your container.' },
            { name: 'TraceRouteMap', desc: 'All compiled routes with specificity scores, methods, paths, and handler references.' },
            { name: 'TraceSchemaLedger', desc: 'Model registry snapshots and migration history — schema evolution tracking.' },
            { name: 'TraceLifecycleJournal', desc: 'Startup/shutdown events with precise timing — how long each phase took.' },
            { name: 'TraceConfigSnapshot', desc: 'Resolved configuration at boot time with secrets automatically redacted.' },
            { name: 'TraceDiagnostics', desc: 'Health probes, performance traces, error budgets, and cache statistics.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Directory Structure */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Directory Structure</h2>
        <CodeBlock language="structure" filename=".aquilia/">{`.aquilia/
├── manifest.json          # Build manifest & fingerprint
├── routes.json            # Compiled route table
├── di_graph.json          # DI provider dependency tree
├── schema_ledger.json     # Model schema snapshots
├── lifecycle.json         # Startup/shutdown journal
├── config_snapshot.json   # Resolved config (secrets redacted)
└── diagnostics.json       # Health, performance, error budget`}</CodeBlock>
      </section>

      {/* Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Programmatic Access</h2>
        <CodeBlock language="python" filename="trace_usage.py">{`from aquilia.trace import AquiliaTrace

# Auto-detects workspace root
trace = AquiliaTrace()

# Full snapshot from a running server
trace.snapshot(server)

# Access trace data
print(trace.manifest.fingerprint)     # "sha256:a1b2c3..."
print(trace.routes.count)             # 42
print(trace.di_graph.provider_count)  # 15
print(trace.lifecycle.startup_ms)     # 234.5
print(trace.diagnostics.error_rate)   # 0.001

# Access route details
for route in trace.routes.entries:
    print(f"{route['method']:6} {route['path']:30} → {route['handler']}")

# Access DI providers
for provider in trace.di_graph.providers:
    print(f"{provider['token']:30} scope={provider['scope']}")

# Check schema changes since last boot
changes = trace.schema_ledger.diff_since_last()
for change in changes:
    print(f"{change['model']}: {change['type']} — {change['details']}")`}</CodeBlock>
      </section>

      {/* Safe to Delete */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Safe to Delete</h2>
        <div className={`p-4 rounded-xl border flex items-start gap-3 ${isDark ? 'bg-green-500/5 border-green-500/20' : 'bg-green-50 border-green-200'}`}>
          <span className="text-2xl">✓</span>
          <p className={`text-sm ${isDark ? 'text-green-300' : 'text-green-700'}`}>
            The <code className="font-mono">.aquilia/</code> directory is safe to delete at any time. Aquilia regenerates it on the next server boot. Add it to <code className="font-mono">.gitignore</code> — it's a local development artifact, not a source file.
          </p>
        </div>
        <CodeBlock language="shell" filename=".gitignore">{`# Aquilia trace directory
.aquilia/

# Python
__pycache__/
*.pyc
*.egg-info/

# Environment
env/
.venv/`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/testing" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Testing
        </Link>
        <Link to="/docs" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Back to Docs
        </Link>
      </div>
    </div>
  )
}
