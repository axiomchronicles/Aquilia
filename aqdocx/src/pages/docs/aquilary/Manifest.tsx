import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Boxes } from 'lucide-react'

export function AquilaryManifest() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Boxes className="w-4 h-4" />
          Aquilary / Manifest System
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Manifest System
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The manifest system provides safe, import-free module discovery. <code className="text-aquilia-400">ManifestLoader</code> reads manifest files, validates them, and builds the module dependency graph without executing any module code.
        </p>
      </div>

      {/* ManifestLoader */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ManifestLoader</h2>
        <CodeBlock language="python" filename="loader.py">{`from aquilia.aquilary import ManifestLoader, ManifestSource

# Load manifests from a directory
loader = ManifestLoader()
manifests = loader.load(
    source=ManifestSource.DIRECTORY,
    path="modules/",
)

# Each manifest describes a module:
# - name, version, dependencies
# - controllers, models, services
# - middleware, effects, routes
# - config schema

for manifest in manifests:
    print(f"{manifest.name} v{manifest.version}")
    print(f"  deps: {manifest.dependencies}")
    print(f"  controllers: {manifest.controllers}")
    print(f"  models: {manifest.models}")`}</CodeBlock>
      </section>

      {/* RegistryValidator */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RegistryValidator</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Validates the entire manifest graph for conflicts, missing dependencies, and schema violations.
        </p>
        <CodeBlock language="python" filename="validator.py">{`from aquilia.aquilary import RegistryValidator, ValidationReport

validator = RegistryValidator()
report: ValidationReport = validator.validate(registry)

if report.is_valid:
    print("All manifests valid!")
else:
    for error in report.errors:
        print(f"ERROR: {error.message}")
    for warning in report.warnings:
        print(f"WARN: {warning.message}")`}</CodeBlock>
      </section>

      {/* DependencyGraph */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Graph</h2>
        <CodeBlock language="python" filename="graph.py">{`from aquilia.aquilary import DependencyGraph, GraphNode

graph = DependencyGraph(manifests)

# Topological sort — deterministic load order
order = graph.topological_sort()
# → ["core", "auth", "users", "products", "orders"]

# Detect cycles
cycles = graph.detect_cycles()
if cycles:
    raise DependencyCycleError(cycles)

# Get dependencies for a module
deps = graph.get_dependencies("orders")
# → {"users", "products"}`}</CodeBlock>
      </section>

      {/* Errors */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry Errors</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'RegistryError', desc: 'Base registry error' },
            { name: 'DependencyCycleError', desc: 'Circular dependency detected' },
            { name: 'RouteConflictError', desc: 'Duplicate route across modules' },
            { name: 'ConfigValidationError', desc: 'Manifest config schema invalid' },
            { name: 'CrossAppUsageError', desc: 'Module accessing another module\u0027s internals' },
            { name: 'ManifestValidationError', desc: 'Manifest file structure invalid' },
            { name: 'DuplicateAppError', desc: 'Two modules with same name' },
            { name: 'FrozenManifestMismatchError', desc: 'Frozen manifest differs from live' },
            { name: 'HotReloadError', desc: 'Error during hot-reload' },
          ].map((e, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-red-400' : 'text-red-600'}`}>{e.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{e.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
