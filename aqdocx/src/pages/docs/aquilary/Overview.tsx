import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Archive } from 'lucide-react'

export function AquilaryOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Archive className="w-4 h-4" />
          Advanced / Aquilary
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Aquilary Registry
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Aquilary is Aquilia's manifest-driven artifact and module registry. It tracks modules, controllers, providers, routes, and configuration as a deterministic dependency graph with content-addressable fingerprinting — ensuring reproducible builds and safe hot-reloads.
        </p>
      </div>

      {/* Core Concepts */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core Concepts</h2>
        <div className="space-y-3">
          {[
            { name: 'Aquilary', desc: 'Central registry class. Collects modules, resolves dependencies, compiles manifests, and generates fingerprints.' },
            { name: 'RuntimeRegistry', desc: 'Runtime counterpart — holds live references to compiled controllers, DI containers, and route tables.' },
            { name: 'Manifest', desc: 'Static declaration of a module\'s controllers, providers, integrations, and dependencies.' },
            { name: 'Fingerprint', desc: 'SHA-256 hash of the compiled state — used for change detection, cache invalidation, and deployment verification.' },
            { name: 'ArtifactStore', desc: 'Persistent storage for compiled artifacts (.crous files). Used by the CLI for compile-once-run-many deployments.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How the Aquilary Works</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Module

# The workspace declares the module graph
workspace = Workspace(
    modules=[
        Module("users", controllers=[UserController], providers=[UserService]),
        Module("products", controllers=[ProductController], providers=[ProductService]),
        Module("orders",
            controllers=[OrderController],
            providers=[OrderService],
            imports=["users", "products"],  # Explicit dependencies
        ),
    ],
)

# At startup, the Aquilary:
# 1. Collects all modules from the workspace
# 2. Resolves import/export dependencies
# 3. Compiles controllers into route tables
# 4. Registers DI providers in scoped containers
# 5. Generates a fingerprint of the compiled state
# 6. Writes the manifest to .aquilia/manifest.json`}</CodeBlock>
      </section>

      {/* Fingerprinting */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fingerprinting</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The fingerprint is a SHA-256 hash of the entire compiled state. It changes when:
        </p>
        <ul className={`space-y-2 mb-6 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>A controller, provider, or module is added, removed, or modified</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Route paths or methods change</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Integration configuration changes</li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Model schemas are updated</li>
        </ul>
        <CodeBlock language="python" filename="fingerprint.py">{`from aquilia.aquilary import Aquilary

registry = Aquilary(workspace)
await registry.compile()

print(registry.fingerprint)
# → "sha256:a1b2c3d4e5f6..."

# Compare with stored fingerprint
if registry.fingerprint != stored_fingerprint:
    print("Application has changed — recompile artifacts")
    await registry.emit_artifacts("./artifacts/")`}</CodeBlock>
      </section>

      {/* CLI Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CLI Integration</h2>
        <CodeBlock language="shell" filename="Terminal">{`# Validate the workspace manifest
aq validate

# Compile to artifacts (for production deployment)
aq compile

# Inspect the compiled state
aq inspect routes        # Show all compiled routes
aq inspect providers     # Show DI provider registry
aq inspect modules       # Show module dependency graph
aq inspect fingerprint   # Show current fingerprint`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/middleware" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Middleware
        </Link>
        <Link to="/docs/effects" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Effects <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
