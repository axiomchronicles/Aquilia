import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Activity } from 'lucide-react'

export function ServerLifecycle() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Activity className="w-4 h-4" />Server</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Coordinator</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">LifecycleCoordinator</code> manages the application lifecycle through well-defined phases: initializing, starting, running, stopping, and stopped.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle Phases</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 800 120" className="w-full" fill="none">
            <defs><marker id="lc-a" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" className="fill-aquilia-500/50" /></marker></defs>
            {[
              { x: 10, label: 'INITIALIZING', color: 'text-yellow-500' },
              { x: 170, label: 'STARTING', color: 'text-blue-500' },
              { x: 330, label: 'RUNNING', color: 'text-aquilia-500' },
              { x: 490, label: 'STOPPING', color: 'text-orange-500' },
              { x: 650, label: 'STOPPED', color: 'text-red-500' },
            ].map((p, i) => (
              <g key={i}>
                <rect x={p.x} y="30" width="140" height="50" rx="10" className="fill-aquilia-500/5 stroke-aquilia-500/20" strokeWidth="1.5">
                  <animate attributeName="stroke-opacity" values="0.15;0.4;0.15" dur="3s" begin={`${i*0.6}s`} repeatCount="indefinite" />
                </rect>
                <text x={p.x+70} y="60" textAnchor="middle" className={`text-[10px] font-bold ${p.color}`}>{p.label}</text>
                {i < 4 && <line x1={p.x+145} y1="55" x2={p.x+165} y2="55" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#lc-a)" />}
              </g>
            ))}
          </svg>
        </div>
        <div className="space-y-3 mt-6">
          {[
            { phase: 'INITIALIZING', desc: 'Validates configuration, registers default providers, sets up the DI container, compiles controllers.' },
            { phase: 'STARTING', desc: 'Runs startup hooks, opens database connections, initializes singleton controllers, warms caches.' },
            { phase: 'RUNNING', desc: 'Server is accepting requests. All subsystems are operational.' },
            { phase: 'STOPPING', desc: 'Runs shutdown hooks, closes database connections, flushes caches, shuts down singleton controllers.' },
            { phase: 'STOPPED', desc: 'All resources released. Server is no longer accepting requests.' },
          ].map((p, i) => (
            <div key={i} className={`flex gap-3 p-4 rounded-xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
              <code className="text-aquilia-500 font-mono text-xs font-bold shrink-0">{p.phase}</code>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{p.desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registering Lifecycle Hooks</h2>
        <CodeBlock language="python" filename="Lifecycle Hooks">{`from aquilia import AquiliaServer

app = AquiliaServer()

# Decorator style
@app.on_startup
async def on_startup():
    print("Starting up...")
    # Open connections, warm caches, etc.

@app.on_shutdown
async def on_shutdown():
    print("Shutting down...")
    # Close connections, flush buffers, etc.

# Or register programmatically
async def init_metrics():
    await metrics.init()

app.lifecycle.add_startup_hook(init_metrics)
app.lifecycle.add_shutdown_hook(metrics.close)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Startup Order</h2>
        <div className={boxClass}>
          <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>During the STARTING phase, operations happen in this order:</p>
          <ol className={`space-y-2 list-decimal list-inside ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li>Configuration loaded and validated</li>
            <li>DI container finalized (all providers registered)</li>
            <li>Database connections opened</li>
            <li>Models tables created/migrated (if auto_migrate=True)</li>
            <li>Controllers compiled (route tree built)</li>
            <li>Singleton controllers instantiated and on_startup() called</li>
            <li>User-registered startup hooks executed</li>
            <li>Middleware stack initialized</li>
            <li>Server marked as RUNNING</li>
          </ol>
        </div>
      </section>
    </div>
  )
}
