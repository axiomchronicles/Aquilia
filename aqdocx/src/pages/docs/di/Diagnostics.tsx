import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Package } from 'lucide-react'

export function DIDiagnostics() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Package className="w-4 h-4" />
          Dependency Injection / Diagnostics
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          DI Diagnostics
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Tools for inspecting, debugging, and testing the dependency graph. <code className="text-aquilia-400">DependencyGraph</code> visualizes resolution order, and <code className="text-aquilia-400">TestRegistry</code> simplifies mocking in tests.
        </p>
      </div>

      {/* DependencyGraph */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DependencyGraph</h2>
        <CodeBlock language="python" filename="graph.py">{`from aquilia.di import DependencyGraph

graph = DependencyGraph(container)

# Print resolution order
for node in graph.topological_sort():
    print(f"{node.name} (lifecycle={node.lifecycle})")
    for dep in node.dependencies:
        print(f"  ← {dep.name}")

# Detect circular dependencies
cycles = graph.detect_cycles()
if cycles:
    for cycle in cycles:
        print(f"Cycle: {' → '.join(cycle)}")

# Visualization (requires graphviz)
graph.render("dependency_graph.svg")`}</CodeBlock>
      </section>

      {/* Container Inspection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Container Inspection</h2>
        <CodeBlock language="python" filename="inspect.py">{`# List all registrations
for reg in container.registrations:
    print(f"{reg.service_type.__name__}")
    print(f"  lifecycle: {reg.lifecycle}")
    print(f"  factory:   {reg.factory}")
    print(f"  instance:  {reg.instance is not None}")

# Check if a service is registered
container.is_registered(EmailService)  # True

# Get registration info
info = container.get_registration(EmailService)
print(info.lifecycle)   # Lifecycle.SINGLETON
print(info.created_at)  # datetime`}</CodeBlock>
      </section>

      {/* TestRegistry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TestRegistry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">TestRegistry</code> provides a sandboxed container for unit tests with easy mocking.
        </p>
        <CodeBlock language="python" filename="testing.py">{`from aquilia.di import TestRegistry
from unittest.mock import AsyncMock

# Create test registry from production container
test = TestRegistry(container)

# Override specific services with mocks
mock_mail = AsyncMock(spec=EmailService)
test.override(EmailService, mock_mail)

mock_db = AsyncMock(spec=DatabasePool)
test.override(DatabasePool, mock_db)

# Resolve uses mocks where overridden, real for the rest
order_service = test.resolve(OrderService)
# order_service.mail → mock_mail
# order_service.db → mock_db

# Reset all overrides
test.reset()`}</CodeBlock>
      </section>

      {/* DI Faults */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI Faults</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Fault Code</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['DI_NOT_REGISTERED', 'Requested service type has no registration'],
                ['DI_CIRCULAR_DEPENDENCY', 'Circular dependency detected during resolution'],
                ['DI_LIFECYCLE_MISMATCH', 'Singleton depends on scoped/transient service'],
                ['DI_FACTORY_ERROR', 'Factory function raised an exception'],
                ['DI_SCOPE_NOT_ACTIVE', 'Scoped service resolved outside of a scope'],
                ['DI_DISPOSAL_ERROR', 'Error during service disposal'],
              ].map(([code, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{code}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
