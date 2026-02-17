import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Settings, ArrowRight } from 'lucide-react'

export function ConfigOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Settings className="w-4 h-4" />Core</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia uses a layered configuration system powered by <code className="text-aquilia-500">ConfigLoader</code>. Configuration is loaded from YAML files, environment variables, and programmatic builders — with environment-specific overrides.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ConfigLoader</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ConfigLoader</code> loads configuration from multiple sources and merges them in priority order:
        </p>
        <div className={`p-6 rounded-2xl border mb-6 ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <ol className={`space-y-3 list-decimal list-inside ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li><strong>Default values</strong> — Built-in framework defaults</li>
            <li><strong>workspace.yaml</strong> — Base workspace configuration</li>
            <li><strong>{'<environment>.yaml'}</strong> — Environment-specific overrides (development.yaml, production.yaml)</li>
            <li><strong>Environment variables</strong> — <code className="text-aquilia-500">AQUILIA_*</code> prefixed env vars</li>
            <li><strong>Programmatic</strong> — WorkspaceConfigBuilder / ModuleConfigBuilder</li>
          </ol>
          <p className={`mt-4 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Later sources override earlier ones. Environment variables have highest priority.</p>
        </div>
        <CodeBlock language="python" filename="Using ConfigLoader">{`from aquilia.config import ConfigLoader

# Load config from the config/ directory
config = ConfigLoader.load("config/", environment="development")

# Access values
db_url = config.get("database.url", default="sqlite:///db.sqlite3")
secret = config.get("security.secret_key")
debug = config.get("app.debug", default=False)

# Nested access with dot notation
mail_host = config.get("mail.smtp.host")
mail_port = config.get("mail.smtp.port", default=587)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>YAML Configuration</h2>
        <CodeBlock language="yaml" filename="config/workspace.yaml">{`app:
  name: "My Aquilia App"
  debug: false
  version: "1.0.0"

database:
  url: "sqlite:///db.sqlite3"
  pool_size: 5
  echo: false

security:
  secret_key: "change-me-in-production"
  allowed_hosts:
    - "localhost"
    - "*.example.com"

sessions:
  backend: "cookie"
  max_age: 3600
  cookie_name: "session_id"
  secure: true

mail:
  provider: "smtp"
  smtp:
    host: "smtp.example.com"
    port: 587
    username: ""
    password: ""

cache:
  backend: "memory"
  default_ttl: 300`}</CodeBlock>

        <CodeBlock language="yaml" filename="config/development.yaml">{`# Overrides for development
app:
  debug: true

database:
  echo: true

security:
  secret_key: "dev-secret-not-secure"
  allowed_hosts:
    - "*"

sessions:
  secure: false`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Environment Variables</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Any configuration value can be overridden by environment variables with the <code className="text-aquilia-500">AQUILIA_</code> prefix. Nested keys use double underscores:
        </p>
        <CodeBlock language="bash" filename="Environment Variables">{`# Override database URL
export AQUILIA_DATABASE__URL="postgresql://user:pass@localhost/mydb"

# Override secret key
export AQUILIA_SECURITY__SECRET_KEY="my-production-secret"

# Override debug mode
export AQUILIA_APP__DEBUG=false`}</CodeBlock>
      </section>

      <section>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { title: 'Workspace Config', to: '/docs/config/workspace', desc: 'WorkspaceConfigBuilder API' },
            { title: 'Module Config', to: '/docs/config/module', desc: 'ModuleConfigBuilder API' },
            { title: 'Integrations', to: '/docs/config/integrations', desc: 'IntegrationConfigBuilder API' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title} <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" /></h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
