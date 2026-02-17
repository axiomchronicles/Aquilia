import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Plug } from 'lucide-react'

export function ConfigIntegrations() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Plug className="w-4 h-4" />Config</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Integration Config Builder</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">IntegrationConfigBuilder</code> configures third-party service integrations — databases, caches, mail providers, and external APIs — with connection pooling, retry logic, and health checks.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage</h2>
        <CodeBlock language="python" filename="Integration Configuration">{`from aquilia.config_builders import IntegrationConfigBuilder, WorkspaceConfigBuilder

# Redis integration
redis_integration = (
    IntegrationConfigBuilder("redis")
    .set_url("redis://localhost:6379/0")
    .set_pool_size(10)
    .set_retry_policy(max_retries=3, backoff=0.5)
    .set_health_check(interval=30)
    .build()
)

# S3 integration
s3_integration = (
    IntegrationConfigBuilder("s3")
    .set_config({
        "bucket": "my-bucket",
        "region": "us-east-1",
        "access_key": "...",
        "secret_key": "...",
    })
    .build()
)

# Register in workspace
workspace = (
    WorkspaceConfigBuilder("My App")
    .add_integration(redis_integration)
    .add_integration(s3_integration)
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
                { m: 'set_url(url)', d: 'Set the connection URL for the integration' },
                { m: 'set_pool_size(n)', d: 'Configure connection pool size' },
                { m: 'set_retry_policy(**kw)', d: 'Set retry max, backoff, and jitter' },
                { m: 'set_health_check(interval)', d: 'Enable periodic health checks' },
                { m: 'set_config(dict)', d: 'Set arbitrary key/value configuration' },
                { m: 'set_timeout(seconds)', d: 'Set connection/operation timeout' },
                { m: 'build()', d: 'Compile and return the integration config' },
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
