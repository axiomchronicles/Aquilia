import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Blocks, FolderOpen, FileCode, Settings, Database, Terminal } from 'lucide-react'

export function ProjectStructurePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Blocks className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Project Structure
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>File layout, conventions, and generated artifacts</p>
          </div>
        </div>
      </div>

      {/* Standard Layout */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <FolderOpen className="w-5 h-5 text-aquilia-400" />
          Standard Workspace Layout
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          A workspace created with <code>aq init workspace my-api</code> produces the following structure.
          Every directory and file has a specific purpose:
        </p>

        <CodeBlock
          code={`my-api/
├── workspace.py              # Root configuration (Workspace/Module/Integration)
├── aquilia.yaml              # Alternative YAML config (optional, lower priority)
├── .env                      # Environment variables (AQ_ prefix)
│
├── modules/                  # Application modules (one per bounded context)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── controllers.py    # Controller classes with route decorators
│   │   ├── services.py       # Business logic services (@service decorated)
│   │   ├── models.py         # ORM model definitions
│   │   ├── serializers.py    # Request/response serializers (optional)
│   │   ├── blueprints.py     # Blueprint contracts (optional)
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_controllers.py
│   │       └── test_services.py
│   │
│   └── users/                # Another module
│       ├── __init__.py
│       ├── controllers.py
│       ├── services.py
│       └── models.py
│
├── templates/                # Jinja2 template files
│   ├── base.html
│   ├── layouts/
│   └── partials/
│
├── static/                   # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── img/
│
├── migrations/               # Auto-generated database migrations
│   ├── 0001_initial.py
│   └── 0002_add_users.py
│
├── .aquilia/                 # Trace directory (auto-generated, gitignore)
│   ├── manifest.json         # Compiled app manifest
│   ├── route_map.json        # All registered routes
│   ├── di_graph.json         # DI dependency graph
│   ├── schema_ledger.json    # Model schema snapshots
│   ├── lifecycle.log         # Lifecycle event journal
│   ├── config_snapshot.json  # Active configuration
│   └── diagnostics.json      # Health and diagnostic data
│
├── tests/                    # Top-level test directory
│   ├── conftest.py
│   └── test_integration.py
│
├── Dockerfile                # Auto-generated if --no-docker not set
├── docker-compose.yml        # Auto-generated if --no-docker not set
├── requirements.txt          # Frozen dependencies (aq freeze)
└── pyproject.toml            # Project metadata`}
          language="text"
        />
      </section>

      {/* Key Files */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <FileCode className="w-5 h-5 text-aquilia-400" />
          Key Files Explained
        </h2>

        <div className="space-y-6">
          {/* workspace.py */}
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold text-lg mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <code>workspace.py</code>
            </h3>
            <p className={`mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              The root configuration file. Aquilia's ConfigLoader looks for this file first (Python-first config).
              It must export an <code>app</code> variable containing the Workspace build result.
            </p>
            <CodeBlock
              code={`from aquilia import Workspace, Module, Integration

app = (
    Workspace("my-api")
    .module(
        Module("core")
        .auto_discover("modules/core")
        .route_prefix("/api")
    )
    .module(
        Module("users")
        .auto_discover("modules/users")
        .route_prefix("/api/users")
        .depends_on(["core"])
    )
    .integrate(
        Integration.database(url="sqlite:///db.sqlite3"),
        Integration.sessions(),
        Integration.auth(),
        Integration.cors(allow_origins=["*"]),
        Integration.cache(backend="memory"),
    )
    .runtime(debug=True, host="0.0.0.0", port=8000)
    .build()
)`}
              language="python"
            />
          </div>

          {/* aquilia.yaml */}
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold text-lg mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <code>aquilia.yaml</code> <span className={`text-sm font-normal ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>(alternative)</span>
            </h3>
            <p className={`mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              YAML-based configuration as an alternative to workspace.py. Lower priority — if both exist,
              workspace.py takes precedence. Useful for deployment environments where Python config isn't ideal.
            </p>
            <CodeBlock
              code={`# aquilia.yaml
name: my-api
debug: true

runtime:
  host: 0.0.0.0
  port: 8000

database:
  url: sqlite:///db.sqlite3

sessions:
  enabled: true
  secret_key: "change-in-production"
  max_age: 3600

auth:
  enabled: true
  secret_key: "jwt-secret"
  algorithm: RS256

cors:
  allow_origins:
    - "http://localhost:3000"
  allow_methods:
    - GET
    - POST
    - PUT
    - DELETE`}
              language="yaml"
            />
          </div>

          {/* .env */}
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold text-lg mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <code>.env</code>
            </h3>
            <p className={`mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Environment variables with the <code>AQ_</code> prefix are automatically loaded. Nested keys
              use double underscores. Higher priority than config files but lower than CLI arguments.
            </p>
            <CodeBlock
              code={`# .env
AQ_DEBUG=false
AQ_PORT=9000
AQ_DATABASE__URL=postgres://user:pass@localhost/mydb
AQ_AUTH__SECRET_KEY=production-secret
AQ_SESSIONS__SECRET_KEY=session-secret
AQ_CORS__ALLOW_ORIGINS=https://myapp.com`}
              language="bash"
            />
          </div>
        </div>
      </section>

      {/* Module Structure */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 text-aquilia-400" />
          Module Conventions
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Each module directory follows conventions that <code>Module.auto_discover()</code> uses to find components:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>File</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Discovery Scans For</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Registration</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['controllers.py', 'Classes extending Controller', 'Compiled routes registered with ControllerRouter'],
                ['services.py', 'Classes decorated with @service or @factory', 'Providers registered in DI Container'],
                ['models.py', 'Classes extending Model (ModelMeta metaclass)', 'Schemas compiled, tables validated/created'],
                ['serializers.py', 'Classes extending Serializer / ModelSerializer', 'Available for controller decorator binding'],
                ['blueprints.py', 'Classes extending Blueprint', 'Available for controller decorator binding'],
                ['middleware.py', 'Callable middleware functions', 'Added to module-scoped middleware stack'],
              ].map(([file, scans, reg], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{file}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>{scans}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{reg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            <strong>Explicit registration:</strong> If you prefer not to use <code>auto_discover()</code>,
            you can explicitly register components with <code>Module.register_controllers([...])</code>,
            <code>.register_services([...])</code>, and <code>.register_models([...])</code>.
          </p>
        </div>
      </section>

      {/* Trace Directory */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 text-aquilia-400" />
          The .aquilia/ Trace Directory
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>.aquilia/</code> directory is automatically generated at boot and contains
          diagnostic artifacts. It should be added to <code>.gitignore</code>:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>File</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Contents</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['manifest.json', 'Full compiled manifest — all apps, controllers, services, and configuration'],
                ['route_map.json', 'Every registered route with HTTP method, pattern, controller, and handler'],
                ['di_graph.json', 'Complete DI dependency graph with providers, scopes, and resolution chains'],
                ['schema_ledger.json', 'Model schema snapshots for migration diffing and validation'],
                ['lifecycle.log', 'Timestamped journal of lifecycle events (startup, shutdown, errors)'],
                ['config_snapshot.json', 'Active merged configuration at boot time'],
                ['diagnostics.json', 'Health check results, latency metrics, and provider statistics'],
              ].map(([file, contents], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{file}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{contents}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Use <code>aq inspect</code> to query trace artifacts from the command line, or use
          <code>aq trace</code> for interactive exploration.
        </p>
      </section>

      {/* CLI-generated files */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Terminal className="w-5 h-5 text-aquilia-400" />
          CLI-Generated Files
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>aq</code> CLI generates various files. Understanding where they go:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Command</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Generates</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['aq init workspace <name>', 'Full project scaffolding with workspace.py, modules/, templates/, static/'],
                ['aq add module <name>', 'modules/<name>/ with __init__.py, controllers.py, services.py, models.py'],
                ['aq generate controller <Name>', 'controllers/<name>.py with boilerplate Controller class'],
                ['aq generate service <Name>', 'services/<name>.py with @service-decorated class'],
                ['aq compile', '.aquilia/ trace artifacts (manifest, route_map, di_graph, etc.)'],
                ['aq freeze', 'requirements.txt with pinned dependency versions'],
                ['aq migrate makemigrations', 'migrations/ directory with numbered migration files'],
                ['aq deploy all', 'Dockerfile and docker-compose.yml for containerized deployment'],
              ].map(([cmd, gen], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{cmd}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{gen}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Next Steps */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Next Steps</h2>
        <div className="flex flex-col gap-2">
          <Link to="/docs/config/workspace" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Workspace Builder: All configuration options
          </Link>
          <Link to="/docs/controllers/overview" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Controllers: Writing request handlers
          </Link>
          <Link to="/docs/cli/commands" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → CLI Reference: All commands in detail
          </Link>
        </div>
      </section>
    </div>
  )
}
