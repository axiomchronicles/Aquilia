import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Brain } from 'lucide-react'

export function MLOpsRegistry() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Brain className="w-4 h-4" />
          MLOps / Registry
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Model Registry
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">RegistryService</code> is a versioned model registry with stage transitions (staging → production → archived), rollback capability, and integration with the <code className="text-aquilia-400">ContentStore</code>.
        </p>
      </div>

      {/* RegistryService */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RegistryService</h2>
        <CodeBlock language="python" filename="registry.py">{`from aquilia.mlops import RegistryService, ContentStore

store = ContentStore.local("./model_store/")
registry = RegistryService(store=store)

# Register a modelpack
entry = await registry.register(pack)
print(entry.content_id)   # "sha256:..."
print(entry.stage)         # "staging"

# Promote to production
await registry.promote(pack.name, version="1.2.0", stage="production")

# Get the production model
prod = await registry.get_production("sentiment-classifier")
print(prod.version)   # "1.2.0"

# Rollback to previous version
await registry.rollback("sentiment-classifier")

# List all versions
versions = await registry.list_versions("sentiment-classifier")
for v in versions:
    print(f"  v{v.version} — {v.stage}")`}</CodeBlock>
      </section>

      {/* Stages */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Stages</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { stage: 'staging', color: 'yellow', desc: 'Newly registered. Not yet serving traffic. Run validation tests here.' },
            { stage: 'production', color: 'green', desc: 'Actively serving. Only one version can be production at a time.' },
            { stage: 'archived', color: 'gray', desc: 'Retired. Kept for audit trail and rollback capability.' },
          ].map((s, i) => (
            <div key={i} className={box}>
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-bold mb-2 ${
                s.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                s.color === 'green' ? 'bg-green-500/20 text-green-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>{s.stage}</span>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Registry API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry API</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Method</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['register(pack)', 'Register a new modelpack version'],
                ['promote(name, version, stage)', 'Move model to a new stage'],
                ['get_production(name)', 'Get the active production model'],
                ['get_staging(name)', 'Get the current staging model'],
                ['rollback(name)', 'Revert to previous production version'],
                ['list_versions(name)', 'List all versions of a model'],
                ['delete_version(name, version)', 'Delete a specific version'],
                ['compare(name, v1, v2)', 'Compare metadata of two versions'],
              ].map(([method, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{method}</td>
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
