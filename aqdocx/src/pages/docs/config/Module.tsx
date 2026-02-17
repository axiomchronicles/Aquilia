import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box } from 'lucide-react'

export function ConfigModule() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Config</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Module Config Builder</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ModuleConfigBuilder</code> lets you define per-module configuration — controllers, services, models, and settings that belong to a specific feature module.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage</h2>
        <CodeBlock language="python" filename="Module Configuration">{`from aquilia.config_builders import ModuleConfigBuilder, WorkspaceConfigBuilder

# Define module config
products_module = (
    ModuleConfigBuilder("products")
    .add_controller(ProductController)
    .add_service(ProductService, lifetime="singleton")
    .add_model(Product)
    .set_config({
        "default_page_size": 20,
        "max_upload_size": 10_000_000,
    })
    .build()
)

# Register in workspace
workspace = (
    WorkspaceConfigBuilder("My App")
    .add_module(products_module)
    .build()
)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Builder Methods</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'add_controller(cls)', d: 'Register a controller class in this module' },
                { m: 'add_service(cls, lifetime)', d: 'Register a service with a DI lifetime' },
                { m: 'add_model(cls)', d: 'Register a model class for DB operations' },
                { m: 'set_config(dict)', d: 'Set module-specific configuration key/values' },
                { m: 'set_prefix(prefix)', d: 'Override the URL prefix for all controllers in this module' },
                { m: 'add_middleware(cls)', d: 'Add module-scoped middleware' },
                { m: 'build()', d: 'Compile and return the module config object' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
