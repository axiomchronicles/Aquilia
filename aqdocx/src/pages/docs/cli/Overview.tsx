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

      {/* Sections Grid */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Documentation Sections</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link to="/docs/cli/core" className={`group p-6 rounded-xl border transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/50' : 'bg-white border-gray-200 hover:border-aquilia-500/50'}`}>
            <div className="flex items-center gap-3 mb-2">
              <Terminal className="w-5 h-5 text-aquilia-500" />
              <h3 className={`font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Core Commands</h3>
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>lifecycle management: init, run, serve, deploy.</p>
          </Link>

          <Link to="/docs/cli/database" className={`group p-6 rounded-xl border transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-purple-500/50' : 'bg-white border-gray-200 hover:border-purple-500/50'}`}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-5 h-5 rounded bg-purple-500/20 flex items-center justify-center text-purple-500">DB</div>
              <h3 className={`font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Database</h3>
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Migrations, introspection, schema dumps, and shell.</p>
          </Link>

          <Link to="/docs/cli/mlops" className={`group p-6 rounded-xl border transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-blue-500/50' : 'bg-white border-gray-200 hover:border-blue-500/50'}`}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-5 h-5 rounded bg-blue-500/20 flex items-center justify-center text-blue-500">ML</div>
              <h3 className={`font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>MLOps</h3>
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Pack, deploy, observe, lineage, and experiments.</p>
          </Link>

          <Link to="/docs/cli/inspection" className={`group p-6 rounded-xl border transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-green-500/50' : 'bg-white border-gray-200 hover:border-green-500/50'}`}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-5 h-5 rounded bg-green-500/20 flex items-center justify-center text-green-500">In</div>
              <h3 className={`font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Inspection</h3>
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>DI graph, routes, analytics, caching & mail diagnosis.</p>
          </Link>

          <Link to="/docs/cli/generators" className={`group p-6 rounded-xl border transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-orange-500/50' : 'bg-white border-gray-200 hover:border-orange-500/50'}`}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-5 h-5 rounded bg-orange-500/20 flex items-center justify-center text-orange-500">Gn</div>
              <h3 className={`font-bold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>Generators</h3>
            </div>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Code scaffolding and custom templates.</p>
          </Link>
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
