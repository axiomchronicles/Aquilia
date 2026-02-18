import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Box, Zap, Settings, Server, Layers, ArrowRight, AlertCircle } from 'lucide-react'

export function ConfigWorkspace() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Box className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Workspace Builder</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.config_builders.Workspace — Top-level fluent configuration</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Workspace</code> class is the top-level entry point for Python-based configuration.
          It provides a fluent builder API for defining runtime settings, modules, integrations,
          security, database, sessions, telemetry, and MLOps — all chained into a single
          immutable configuration object.
        </p>
      </div>

      {/* Constructor */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Box className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Class Definition
        </h2>

        <CodeBlock language="python" title="Workspace.__init__()">
{`class Workspace:
    """Fluent workspace builder."""
    
    def __init__(self, name: str, version: str = "0.1.0", description: str = ""):
        self._name = name
        self._version = version
        self._description = description
        self._runtime = RuntimeConfig()
        self._modules: List[ModuleConfig] = []
        self._integrations: Dict[str, Dict[str, Any]] = {}
        self._sessions_config: Optional[Dict[str, Any]] = None
        self._security_config: Optional[Dict[str, Any]] = None
        self._telemetry_config: Optional[Dict[str, Any]] = None
        self._database_config: Optional[Dict[str, Any]] = None
        self._mail_config: Optional[Dict[str, Any]] = None
        self._mlops_config: Optional[Dict[str, Any]] = None
        self._cache_config: Optional[Dict[str, Any]] = None`}
        </CodeBlock>

        <div className={`overflow-x-auto mt-4 mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['name', 'str', '—', 'Workspace name (required). Used in logging and traces.'],
                ['version', 'str', '"0.1.0"', 'Workspace version. Used in OpenAPI spec and metadata.'],
                ['description', 'str', '""', 'Human-readable description of the workspace.'],
              ].map(([param, type_, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{param}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{type_}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{def_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* runtime() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Server className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .runtime()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures the runtime environment. These settings control the ASGI server behavior
          and determine which environment-specific config files are loaded.
        </p>

        <CodeBlock language="python" title="runtime() signature">
{`def runtime(
    self,
    mode: str = "dev",
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
    workers: int = 1,
) -> "Workspace":`}
        </CodeBlock>

        <div className={`overflow-x-auto mt-4 mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['mode', 'str', '"dev"', 'Runtime mode. Determines config/{mode}.yaml loading. Common values: "dev", "prod", "test", "staging".'],
                ['host', 'str', '"127.0.0.1"', 'Bind address. Use "0.0.0.0" for external access.'],
                ['port', 'int', '8000', 'Bind port.'],
                ['reload', 'bool', 'True', 'Enable auto-reload on file changes (development only).'],
                ['workers', 'int', '1', 'Number of worker processes. Use CPU count for production.'],
              ].map(([param, type_, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{param}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{type_}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{def_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>RuntimeConfig</code> dataclass backs this method:
        </p>

        <CodeBlock language="python" title="RuntimeConfig dataclass">
{`@dataclass
class RuntimeConfig:
    """Runtime configuration."""
    mode: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    workers: int = 1`}
        </CodeBlock>
      </section>

      {/* module() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .module()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Registers a module (application unit) in the workspace. Each module is a <code>Module</code> builder
          that gets <code>.build()</code> called automatically to produce a <code>ModuleConfig</code> dataclass.
          See the <Link to="/docs/config/module" className="text-aquilia-400 hover:underline">Module Builder</Link> page for full details.
        </p>

        <CodeBlock language="python" title="module() method">
{`def module(self, module: Module) -> "Workspace":
    """Add a module to the workspace."""
    self._modules.append(module.build())
    return self`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`workspace = (
    Workspace("myapp")
    .module(
        Module("users")
        .route_prefix("/users")
        .auto_discover("apps/users")
        .register_controllers("UserController", "ProfileController")
        .register_services("UserService")
    )
    .module(
        Module("blog")
        .route_prefix("/blog")
        .auto_discover("apps/blog")
        .tags("Blog", "Articles")
    )
    .module(
        Module("admin")
        .route_prefix("/admin")
        .fault_domain("admin")
        .depends_on("users", "blog")
    )
)`}
        </CodeBlock>
      </section>

      {/* integrate() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .integrate()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Adds an integration configuration to the workspace. Integrations are dictionaries
          produced by <code>Integration.*</code> static methods. The workspace auto-detects
          the integration type and wires it to the correct config slot.
        </p>

        <CodeBlock language="python" title="integrate() method">
{`def integrate(self, integration: Dict[str, Any]) -> "Workspace":
    """Add an integration."""
    # Check for explicit _integration_type marker
    integration_type = integration.get("_integration_type")
    if integration_type:
        self._integrations[integration_type] = integration
        # Wire specific types to their config slots:
        #   "cors"         → self._security_config.cors
        #   "csp"          → self._security_config.csp
        #   "rate_limit"   → self._security_config.rate_limit
        #   "static_files" → self._integrations["static_files"]
        #   "openapi"      → self._integrations["openapi"]
        #   "mail"         → self._mail_config
        #   "mlops"        → self._mlops_config
        #   "cache"        → self._cache_config
        return self
    
    # Legacy detection from dict keys:
    #   "tokens" + "security"     → auth
    #   "policy" | "store"        → sessions
    #   "auto_wire"               → dependency_injection
    #   "strict_matching"         → routing
    #   "default_strategy"        → fault_handling
    #   "search_paths" + "cache"  → templates
    #   "url" + "auto_create"     → database`}
        </CodeBlock>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration Type Detection
        </h3>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Modern integrations (cache, cors, csp, csrf, logging, mail, mlops, openapi, rate_limit,
          serializers, static_files) include an <code>_integration_type</code> marker key that
          enables unambiguous detection. Legacy integrations (auth, sessions, di, routing,
          fault_handling, templates, database) are detected by heuristic key inspection.
        </p>

        <CodeBlock language="python" title="Usage with Integration builders">
{`workspace = (
    Workspace("myapp")
    .integrate(Integration.database(url="sqlite:///app.db"))
    .integrate(Integration.auth(secret_key="my-key"))
    .integrate(Integration.openapi(title="My API"))
    .integrate(Integration.cache(backend="redis"))
    .integrate(Integration.cors(allow_origins=["https://myapp.com"]))
    .integrate(Integration.mail(console_backend=True))
    .integrate(Integration.templates.source("templates").cached())
    .integrate(Integration.sessions(policy=my_policy))
)`}
        </CodeBlock>
      </section>

      {/* security() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .security()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          High-level security flags that control which security middleware are automatically
          added to the middleware stack during server startup. For fine-grained control,
          use <code>Integration.cors()</code>, <code>Integration.csp()</code>,
          <code>Integration.rate_limit()</code>, or <code>Integration.csrf()</code> instead.
        </p>

        <CodeBlock language="python" title="security() signature">
{`def security(
    self,
    cors_enabled: bool = False,
    csrf_protection: bool = False,
    helmet_enabled: bool = True,
    rate_limiting: bool = False,
    https_redirect: bool = False,
    hsts: bool = True,
    proxy_fix: bool = False,
    **kwargs
) -> "Workspace":`}
        </CodeBlock>

        <div className={`overflow-x-auto mt-4 mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Flag</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['cors_enabled', 'False', 'Enable CORS middleware (default origins: *)'],
                ['csrf_protection', 'False', 'Enable CSRF protection'],
                ['helmet_enabled', 'True', 'Enable Helmet-style security headers'],
                ['rate_limiting', 'False', 'Enable rate limiting (100 req/min default)'],
                ['https_redirect', 'False', 'Enable HTTP→HTTPS redirect'],
                ['hsts', 'True', 'Enable HSTS header (Strict-Transport-Security)'],
                ['proxy_fix', 'False', 'Enable X-Forwarded-* header processing'],
              ].map(([flag, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{flag}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{def_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="Usage">
{`workspace = (
    Workspace("myapp")
    .security(
        cors_enabled=True,
        csrf_protection=True,
        rate_limiting=True,
        https_redirect=True,  # Production
        proxy_fix=True,       # Behind reverse proxy
    )
)`}
        </CodeBlock>
      </section>

      {/* sessions() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .sessions()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures session management at the workspace level. Accepts a list of <code>SessionPolicy</code>
          instances and additional configuration.
        </p>

        <CodeBlock language="python" title="sessions() signature">
{`def sessions(
    self,
    policies: Optional[List[Any]] = None,
    **kwargs
) -> "Workspace":`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage with SessionPolicy">
{`from aquilia.sessions import SessionPolicy

workspace = (
    Workspace("myapp")
    .sessions(policies=[
        SessionPolicy.for_web_users()
            .lasting(days=14)
            .idle_timeout(hours=2)
            .rotating_on_privilege_change()
    ])
)`}
        </CodeBlock>
      </section>

      {/* database() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .database()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Sets the global default database for the workspace. Individual modules can override
          this with <code>Module.database()</code>.
        </p>

        <CodeBlock language="python" title="database() signature">
{`def database(
    self,
    url: str = "sqlite:///db.sqlite3",
    auto_connect: bool = True,
    auto_create: bool = True,
    auto_migrate: bool = False,
    migrations_dir: str = "migrations",
    **kwargs,
) -> "Workspace":`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`workspace = (
    Workspace("myapp")
    .database(
        url="postgresql://localhost/myapp",
        auto_create=True,
        auto_migrate=True,
        migrations_dir="db/migrations",
    )
    .module(
        Module("analytics")
        .database(
            url="postgresql://localhost/analytics",  # Module-specific DB
            auto_connect=True,
        )
    )
)`}
        </CodeBlock>
      </section>

      {/* telemetry() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .telemetry()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures observability: tracing, metrics, and logging.
        </p>

        <CodeBlock language="python" title="telemetry() signature">
{`def telemetry(
    self,
    tracing_enabled: bool = False,
    metrics_enabled: bool = True,
    logging_enabled: bool = True,
    **kwargs
) -> "Workspace":`}
        </CodeBlock>
      </section>

      {/* mlops() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .mlops()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Shorthand for <code>.integrate(Integration.mlops(...))</code>. Configures the MLOps
          platform at the workspace level.
        </p>

        <CodeBlock language="python" title="mlops() signature">
{`def mlops(
    self,
    enabled: bool = True,
    registry_db: str = "registry.db",
    blob_root: str = ".aquilia-store",
    drift_method: str = "psi",
    drift_threshold: float = 0.2,
    max_batch_size: int = 16,
    max_latency_ms: float = 50.0,
    plugin_auto_discover: bool = True,
    **kwargs,
) -> "Workspace":`}
        </CodeBlock>
      </section>

      {/* to_dict() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .to_dict() — Serialization
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Converts the workspace to a flat dictionary compatible with <code>ConfigLoader</code>.
          This is called automatically when <code>ConfigLoader</code> loads an <code>aquilia.py</code> file.
        </p>

        <CodeBlock language="python" title="to_dict() output structure">
{`def to_dict(self) -> Dict[str, Any]:
    config = {
        "workspace": {
            "name": self._name,
            "version": self._version,
            "description": self._description,
        },
        "runtime": {
            "mode": self._runtime.mode,
            "host": self._runtime.host,
            "port": self._runtime.port,
            "reload": self._runtime.reload,
            "workers": self._runtime.workers,
        },
        "modules": [m.to_dict() for m in self._modules],
        "integrations": self._integrations,
    }
    
    # Optional sections added only when configured:
    # config["sessions"]  ← from .sessions()
    # config["security"]  ← from .security()
    # config["telemetry"] ← from .telemetry()
    # config["database"]  ← from .database() (also integrations.database)
    # config["mail"]      ← from Integration.mail() (also integrations.mail)
    # config["mlops"]     ← from .mlops() (also integrations.mlops)
    # config["cache"]     ← from Integration.cache() (also integrations.cache)
    
    return config`}
        </CodeBlock>

        <div className={`p-4 rounded-lg border mt-4 ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
            <AlertCircle className="w-4 h-4 inline mr-1" />
            <strong>Dual registration:</strong> Subsystem configs like database, mail, mlops, and cache
            are stored both at the top level (<code>config["database"]</code>) and inside
            <code>config["integrations"]["database"]</code> for compatibility. The <code>ConfigLoader</code>
            accessor methods check both locations.
          </p>
        </div>
      </section>

      {/* Complete Example */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Complete Example
        </h2>

        <CodeBlock language="python" title="aquilia.py — Full Production Workspace">
{`from aquilia.config_builders import Workspace, Module, Integration

workspace = (
    Workspace("ecommerce", version="2.0.0", description="E-commerce Platform")
    
    # Runtime
    .runtime(mode="prod", host="0.0.0.0", port=80, reload=False, workers=4)
    
    # Global database
    .database(
        url="postgresql://db-host:5432/ecommerce",
        auto_connect=True,
        auto_migrate=True,
        pool_size=20,
    )
    
    # Modules
    .module(
        Module("catalog")
        .route_prefix("/catalog")
        .auto_discover("apps/catalog")
        .fault_domain("catalog")
        .tags("Products", "Categories")
    )
    .module(
        Module("orders")
        .route_prefix("/orders")
        .auto_discover("apps/orders")
        .fault_domain("orders")
        .depends_on("catalog", "users")
    )
    .module(
        Module("users")
        .route_prefix("/users")
        .auto_discover("apps/users")
        .register_controllers("UserController", "ProfileController")
        .register_services("UserService", "AuthService")
    )
    
    # Integrations
    .integrate(Integration.auth(
        secret_key="prod-secret-key-from-vault",
        store_type="memory",
    ))
    .integrate(Integration.openapi(
        title="E-commerce API",
        version="2.0.0",
        contact_email="api@ecommerce.com",
        swagger_ui_theme="dark",
    ))
    .integrate(Integration.cache(
        backend="composite",
        l1_max_size=500,
        l1_ttl=30,
        redis_url="redis://cache-host:6379/0",
    ))
    .integrate(Integration.cors(
        allow_origins=["https://ecommerce.com", "https://admin.ecommerce.com"],
        allow_credentials=True,
    ))
    .integrate(Integration.mail(
        default_from="noreply@ecommerce.com",
        providers=[
            {"name": "ses", "type": "ses", "region": "us-east-1"},
        ],
    ))
    .integrate(Integration.static_files(
        directories={"/static": "static", "/media": "uploads"},
        cache_max_age=86400,
    ))
    .integrate(Integration.rate_limit(
        limit=200,
        window=60,
        algorithm="token_bucket",
        burst=50,
    ))
    .integrate(Integration.logging(
        slow_threshold_ms=500,
        skip_paths=["/health", "/metrics"],
    ))
    
    # Security
    .security(
        cors_enabled=True,
        csrf_protection=True,
        helmet_enabled=True,
        https_redirect=True,
        proxy_fix=True,
    )
    
    # Telemetry
    .telemetry(
        tracing_enabled=True,
        metrics_enabled=True,
    )
)`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`mt-12 pt-6 border-t flex justify-between ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
        <Link
          to="/docs/config/loader"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          ← Config System Overview
        </Link>
        <Link
          to="/docs/config/module"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          Module Builder <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
