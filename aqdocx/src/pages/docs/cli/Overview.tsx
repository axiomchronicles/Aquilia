import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Terminal } from 'lucide-react'

export function CLIOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Terminal className="w-4 h-4" />
          Tooling / CLI
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          CLI — The <code className="text-aquilia-500">aq</code> Command
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilate (<code className="text-aquilia-500">aq</code>) is Aquilia's native CLI for manifest-driven, artifact-first project orchestration. It handles workspace initialization, module scaffolding, validation, compilation, development serving, and inspection.
        </p>
      </div>

      {/* Philosophy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Philosophy</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { title: 'Manifest-first', desc: 'The CLI reads workspace.py — not scattered settings files' },
            { title: 'Composition over centralization', desc: 'Modules are self-contained, composable units' },
            { title: 'Artifacts over runtime magic', desc: 'Compile once, deploy anywhere (.crous artifacts)' },
            { title: 'Explicit boundaries', desc: 'Module imports/exports are declared, not inferred' },
            { title: 'CLI as primary UX', desc: 'The CLI is the main interface for project management' },
            { title: 'Static-first validation', desc: 'Catch errors at compile time, not runtime' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <h3 className={`font-bold text-sm mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Commands */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Command Reference</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Command</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { cmd: 'aq init workspace <name>', desc: 'Scaffold a new Aquilia project with workspace.py, modules/, config/, and artifacts/' },
                { cmd: 'aq add module <name>', desc: 'Generate a new module with controller, models, and serializers stubs' },
                { cmd: 'aq validate', desc: 'Validate workspace manifest, module graph, and configuration without starting the server' },
                { cmd: 'aq compile', desc: 'Compile the workspace into .crous artifacts for production deployment' },
                { cmd: 'aq run', desc: 'Start the development server with hot-reload and debug toolbar' },
                { cmd: 'aq serve', desc: 'Start the production ASGI server (uvicorn/hypercorn)' },
                { cmd: 'aq freeze', desc: 'Freeze the current state — export all routes, providers, and schemas' },
                { cmd: 'aq inspect <target>', desc: 'Inspect compiled state: routes, providers, modules, fingerprint, config' },
                { cmd: 'aq migrate', desc: 'Run database migrations (generate, apply, rollback)' },
                { cmd: 'aq cache stats', desc: 'Show cache statistics (hit rate, size, evictions)' },
                { cmd: 'aq cache clear', desc: 'Clear all cache entries' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.cmd}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Workspace Init */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Creating a New Project</h2>
        <CodeBlock language="shell" filename="Terminal">{`# Create a new Aquilia workspace
aq init workspace myapp

# Output:
# ✓ Created myapp/
# ✓ Created myapp/workspace.py
# ✓ Created myapp/starter.py
# ✓ Created myapp/config/
# ✓ Created myapp/modules/
# ✓ Created myapp/artifacts/
# ✓ Created myapp/templates/
# ✓ Created myapp/migrations/
#
# 🎉 Workspace "myapp" created!
# Run: cd myapp && aq run`}</CodeBlock>
      </section>

      {/* Module Generation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Adding Modules</h2>
        <CodeBlock language="shell" filename="Terminal">{`# Generate a new module
aq add module products

# Output:
# ✓ Created modules/products/__init__.py
# ✓ Created modules/products/controller.py
# ✓ Created modules/products/models.py
# ✓ Created modules/products/serializers.py
# ✓ Created modules/products/services.py
# ✓ Updated workspace.py with Module("products", ...)
#
# Module "products" added to workspace`}</CodeBlock>
      </section>

      {/* Inspect */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Inspecting the Application</h2>
        <CodeBlock language="shell" filename="Terminal">{`# Inspect compiled routes
aq inspect routes

# Output:
# ┌─────────┬──────────────────────────┬──────────────────────┬─────────────┐
# │ Method  │ Path                     │ Handler              │ Specificity │
# ├─────────┼──────────────────────────┼──────────────────────┼─────────────┤
# │ GET     │ /api/users/              │ UserController.list  │ 100         │
# │ GET     │ /api/users/{id}          │ UserController.get   │ 150         │
# │ POST    │ /api/users/              │ UserController.create│ 100         │
# │ PUT     │ /api/users/{id}          │ UserController.update│ 150         │
# │ DELETE  │ /api/users/{id}          │ UserController.delete│ 150         │
# └─────────┴──────────────────────────┴──────────────────────┴─────────────┘
# Total: 5 routes | Fingerprint: sha256:a1b2c3...`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/mlops" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> MLOps
        </Link>
        <Link to="/docs/testing" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Testing <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
