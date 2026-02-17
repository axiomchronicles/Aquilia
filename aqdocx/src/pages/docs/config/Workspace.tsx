import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Wrench } from 'lucide-react'

export function ConfigWorkspace() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Wrench className="w-4 h-4" />Config</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Workspace Config Builder</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">WorkspaceConfigBuilder</code> provides a fluent API for defining workspace-level configuration programmatically in Python, as an alternative to YAML files.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fluent API</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia.config_builders import WorkspaceConfigBuilder

config = (
    WorkspaceConfigBuilder("My App")
    .set_version("1.0.0")
    .set_debug(True)
    .set_database_url("sqlite:///db.sqlite3")
    .set_secret_key("my-secret-key")
    .set_allowed_hosts(["localhost", "*.example.com"])
    .set_session_config(
        backend="cookie",
        max_age=3600,
        secure=False,
    )
    .set_cache_config(
        backend="memory",
        default_ttl=300,
    )
    .set_mail_config(
        provider="smtp",
        host="smtp.example.com",
        port=587,
    )
    .set_static_dir("artifacts/static")
    .set_template_dir("artifacts/templates")
    .build()
)

# Use with AquiliaServer
app = AquiliaServer(config=config)`}</CodeBlock>
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
                { m: 'set_version(v)', d: 'Set application version string' },
                { m: 'set_debug(bool)', d: 'Enable/disable debug mode' },
                { m: 'set_database_url(url)', d: 'Set the database connection URL' },
                { m: 'set_secret_key(key)', d: 'Set the cryptographic secret key' },
                { m: 'set_allowed_hosts(hosts)', d: 'Set allowed host patterns for security' },
                { m: 'set_session_config(**kw)', d: 'Configure session backend, TTL, cookie settings' },
                { m: 'set_cache_config(**kw)', d: 'Configure cache backend and defaults' },
                { m: 'set_mail_config(**kw)', d: 'Configure mail provider and credentials' },
                { m: 'set_static_dir(path)', d: 'Set the static files directory' },
                { m: 'set_template_dir(path)', d: 'Set the Jinja2 templates directory' },
                { m: 'add_module(builder)', d: 'Add a ModuleConfigBuilder instance' },
                { m: 'add_integration(builder)', d: 'Add an IntegrationConfigBuilder' },
                { m: 'build()', d: 'Compile and return the final config object' },
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
