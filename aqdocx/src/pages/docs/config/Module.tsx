import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Package, Zap, Database, Layers, ArrowRight, AlertCircle, Search, Tag } from 'lucide-react'

export function ConfigModule() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Package className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Module Builder
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.config_builders.Module — Application unit configuration</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Module</code> class is a fluent builder for configuring individual application units
          within a workspace. Each module represents a logical grouping of controllers, services,
          routes, models, serializers, and middleware — analogous to Django apps or NestJS modules.
        </p>
      </div>

      {/* ModuleConfig dataclass */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 inline mr-2 text-aquilia-400" />
          ModuleConfig Dataclass
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Module</code> builder produces a <code>ModuleConfig</code> dataclass via <code>.build()</code>.
          This dataclass is what <code>Workspace.to_dict()</code> serializes into the final config.
        </p>

        <CodeBlock language="python" title="ModuleConfig (from config_builders.py)">
{`@dataclass
class ModuleConfig:
    """Module configuration produced by Module.build()."""
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    fault_domain: str = ""
    route_prefix: str = ""
    depends_on: List[str] = field(default_factory=list)
    controllers: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    middlewares: List[str] = field(default_factory=list)
    socket_controllers: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    serializers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    auto_discover: Optional[str] = None
    database: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        ...`}
        </CodeBlock>

        <div className={`overflow-x-auto mt-4 mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['name', 'str', '""', 'Module name (set by constructor)'],
                ['version', 'str', '"0.1.0"', 'Module version'],
                ['description', 'str', '""', 'Human-readable description'],
                ['fault_domain', 'str', '""', 'Fault isolation domain name'],
                ['route_prefix', 'str', '""', 'URL prefix for all routes in this module'],
                ['depends_on', 'List[str]', '[]', 'Names of modules this module depends on'],
                ['controllers', 'List[str]', '[]', 'Registered controller class names'],
                ['routes', 'List[str]', '[]', 'Registered route function names'],
                ['services', 'List[str]', '[]', 'Registered service class names'],
                ['providers', 'List[str]', '[]', 'Registered DI provider names'],
                ['middlewares', 'List[str]', '[]', 'Registered middleware names'],
                ['socket_controllers', 'List[str]', '[]', 'Registered WebSocket controller names'],
                ['models', 'List[str]', '[]', 'AMDL model file paths or class names'],
                ['serializers', 'List[str]', '[]', 'Registered serializer class names'],
                ['tags', 'List[str]', '[]', 'OpenAPI tags for grouping'],
                ['auto_discover', 'Optional[str]', 'None', 'Directory to scan for components'],
                ['database', 'Optional[Dict]', 'None', 'Module-specific database config'],
              ].map(([field_, type_, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{field_}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{type_}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{def_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Module Builder */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Module Builder
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Module</code> class wraps <code>ModuleConfig</code> in a fluent builder pattern.
          Every method returns <code>self</code> for chaining.
        </p>

        <CodeBlock language="python" title="Module class (from config_builders.py)">
{`class Module:
    """Fluent module builder."""
    
    def __init__(self, name: str, version: str = "0.1.0", description: str = ""):
        self._config = ModuleConfig(
            name=name,
            version=version,
            description=description,
        )
    
    def build(self) -> ModuleConfig:
        """Build module configuration."""
        return self._config`}
        </CodeBlock>
      </section>

      {/* auto_discover */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Search className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .auto_discover()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Tells the Aquilary discovery system to scan the specified directory for controllers,
          services, routes, models, and other components. This is the most common way to register
          components — you point the module at a directory and Aquilia finds everything.
        </p>

        <CodeBlock language="python" title="auto_discover()">
{`def auto_discover(self, path: str) -> "Module":
    """
    Set auto-discovery path.
    
    The Aquilary discovery system will scan this directory for:
    - Controllers (classes inheriting from Controller)
    - Services (classes decorated with @service)
    - Routes (functions decorated with @route)
    - Models (.amdl files)
    - Serializers (classes inheriting from Serializer)
    """
    self._config.auto_discover = path
    return self`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# Scan apps/users/ for all components
Module("users").auto_discover("apps/users")

# Combined with explicit registrations
Module("users")
    .auto_discover("apps/users")
    .register_services("ExtraService")  # Add extras not in the scan path`}
        </CodeBlock>
      </section>

      {/* route_prefix */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .route_prefix()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Sets a URL prefix for all controllers and routes in this module. Prefixed <em>before</em>
          the controller's own <code>prefix</code> attribute.
        </p>

        <CodeBlock language="python" title="route_prefix()">
{`def route_prefix(self, prefix: str) -> "Module":
    """Set URL prefix for all routes in this module."""
    self._config.route_prefix = prefix
    return self

# Example: Module prefix + Controller prefix
# Module("users").route_prefix("/api/v1")
# class UserController(Controller):
#     prefix = "/users"
# 
# Final route: /api/v1/users/{method_path}`}
        </CodeBlock>
      </section>

      {/* fault_domain */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .fault_domain()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Assigns this module to a fault isolation domain. Faults raised within this module
          are scoped to its domain, enabling domain-specific error handlers and preventing
          fault propagation across module boundaries.
        </p>

        <CodeBlock language="python" title="fault_domain()">
{`def fault_domain(self, domain: str) -> "Module":
    """Set fault isolation domain."""
    self._config.fault_domain = domain
    return self

# Usage:
Module("payments")
    .fault_domain("payments")   # Faults scoped to "payments" domain
    .route_prefix("/payments")`}
        </CodeBlock>
      </section>

      {/* depends_on */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .depends_on()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Declares dependencies on other modules. This is used for startup ordering and
          dependency validation — if module A depends on module B, B is initialized first.
        </p>

        <CodeBlock language="python" title="depends_on()">
{`def depends_on(self, *modules: str) -> "Module":
    """Declare module dependencies."""
    self._config.depends_on = list(modules)
    return self

# Usage:
Module("orders")
    .depends_on("users", "catalog", "payments")
    .route_prefix("/orders")`}
        </CodeBlock>
      </section>

      {/* tags */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Tag className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .tags()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Assigns OpenAPI tags to all controllers in this module. Tags are used for grouping
          endpoints in the Swagger UI and ReDoc documentation.
        </p>

        <CodeBlock language="python" title="tags()">
{`def tags(self, *tags: str) -> "Module":
    """Set OpenAPI tags for this module."""
    self._config.tags = list(tags)
    return self

# Usage:
Module("catalog")
    .tags("Products", "Categories", "Search")
    .route_prefix("/catalog")`}
        </CodeBlock>
      </section>

      {/* Registration Methods */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Registration Methods
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          These methods explicitly register component names. They accept <code>*args</code> (variadic
          string names) and return <code>self</code> for chaining. Use these when auto-discovery is
          insufficient or when you need explicit control over what's registered.
        </p>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Signature</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Registers To</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['register_controllers()', '(*names: str)', 'controllers list'],
                ['register_services()', '(*names: str)', 'services list'],
                ['register_providers()', '(*names: str)', 'providers list'],
                ['register_routes()', '(*names: str)', 'routes list'],
                ['register_sockets()', '(*names: str)', 'socket_controllers list'],
                ['register_middlewares()', '(*names: str)', 'middlewares list'],
                ['register_models()', '(*names: str)', 'models list'],
                ['register_serializers()', '(*names: str)', 'serializers list'],
              ].map(([method, sig, target], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{sig}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="Registration Method Pattern">
{`# All registration methods follow this pattern:
def register_controllers(self, *names: str) -> "Module":
    """Register controller class names."""
    self._config.controllers = list(names)
    return self

def register_services(self, *names: str) -> "Module":
    """Register service class names."""
    self._config.services = list(names)
    return self

# ... same pattern for all others`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`Module("users")
    .register_controllers("UserController", "ProfileController", "AdminController")
    .register_services("UserService", "AuthService", "TokenService")
    .register_providers("DatabaseProvider", "CacheProvider")
    .register_routes("health_check", "status")
    .register_sockets("ChatController")
    .register_middlewares("TenantMiddleware")
    .register_models("models/user.amdl", "models/profile.amdl")
    .register_serializers("UserSerializer", "ProfileSerializer")`}
        </CodeBlock>

        <div className={`p-4 rounded-lg border mt-4 ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
            <AlertCircle className="w-4 h-4 inline mr-1" />
            <strong>Note:</strong> Registration methods <strong>replace</strong> the list (they don't append).
            Calling <code>.register_controllers("A")</code> then <code>.register_controllers("B")</code>
            results in only <code>["B"]</code>. Include all names in a single call.
          </p>
        </div>
      </section>

      {/* database */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 inline mr-2 text-aquilia-400" />
          .database()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures a module-specific database. This overrides the workspace-level database
          for all models and queries within this module.
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
) -> "Module":`}
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
                ['url', 'str', '"sqlite:///db.sqlite3"', 'Database connection URL'],
                ['auto_connect', 'bool', 'True', 'Connect on server startup'],
                ['auto_create', 'bool', 'True', 'Create tables from AMDL models automatically'],
                ['auto_migrate', 'bool', 'False', 'Run pending migrations on startup'],
                ['migrations_dir', 'str', '"migrations"', 'Directory for migration files'],
                ['**kwargs', '—', '—', 'Additional database options (pool_size, echo, etc.)'],
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

        <CodeBlock language="python" title="Multi-Database Architecture">
{`workspace = (
    Workspace("multi-db-app")
    
    # Workspace-level default database
    .database(url="postgresql://main-db/app")
    
    # Module with its own database
    .module(
        Module("analytics")
        .route_prefix("/analytics")
        .database(
            url="postgresql://analytics-db/analytics",
            auto_connect=True,
            auto_create=True,
            pool_size=10,
        )
        .register_models("models/analytics.amdl")
    )
    
    # Module using the default database
    .module(
        Module("users")
        .route_prefix("/users")
        # No .database() → inherits workspace-level DB
    )
)`}
        </CodeBlock>
      </section>

      {/* build() and to_dict() */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          .build() &amp; Serialization
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>.build()</code> returns the underlying <code>ModuleConfig</code> dataclass. This is
          called automatically by <code>Workspace.module()</code>. The <code>ModuleConfig.to_dict()</code>
          method serializes it for the config pipeline:
        </p>

        <CodeBlock language="python" title="ModuleConfig.to_dict() output">
{`# Module("users")
#     .route_prefix("/users")
#     .auto_discover("apps/users")
#     .fault_domain("users")
#     .tags("Users")
#     .register_controllers("UserController")
#     .register_services("UserService")
#     .build().to_dict()

{
    "name": "users",
    "version": "0.1.0",
    "description": "",
    "fault_domain": "users",
    "route_prefix": "/users",
    "depends_on": [],
    "controllers": ["UserController"],
    "routes": [],
    "services": ["UserService"],
    "providers": [],
    "middlewares": [],
    "socket_controllers": [],
    "models": [],
    "serializers": [],
    "tags": ["Users"],
    "auto_discover": "apps/users",
    "database": None,
}`}
        </CodeBlock>
      </section>

      {/* Complete Example */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Complete Module Examples
        </h2>

        <CodeBlock language="python" title="Minimal Module">
{`# Just a name and auto-discovery — Aquilia finds everything
Module("blog").auto_discover("apps/blog")`}
        </CodeBlock>

        <CodeBlock language="python" title="Explicit Module">
{`# Full control over what's registered
Module("users", version="1.2.0", description="User management")
    .route_prefix("/api/v1/users")
    .fault_domain("identity")
    .depends_on("auth")
    .tags("Users", "Identity")
    .register_controllers("UserController", "ProfileController", "AvatarController")
    .register_services("UserService", "ProfileService", "EmailVerificationService")
    .register_providers("UserRepository", "ProfileRepository")
    .register_serializers("UserSerializer", "ProfileSerializer", "AvatarSerializer")
    .register_models("models/user.amdl", "models/profile.amdl")
    .register_middlewares("TenantIsolationMiddleware")
    .database(
        url="postgresql://identity-db/users",
        auto_migrate=True,
        pool_size=15,
    )`}
        </CodeBlock>

        <CodeBlock language="python" title="Hybrid Module (Auto-discover + Explicit)">
{`# Discover most things, explicitly add edge cases
Module("orders")
    .auto_discover("apps/orders")          # Finds controllers, services, etc.
    .route_prefix("/orders")
    .fault_domain("commerce")
    .depends_on("users", "catalog", "payments")
    .tags("Orders", "Commerce")
    .register_providers("StripePaymentProvider")  # Not in apps/orders/
    .register_middlewares("OrderValidationMiddleware")`}
        </CodeBlock>
      </section>

      {/* YAML Equivalent */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          YAML Equivalent
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The same module configuration in YAML format:
        </p>

        <CodeBlock language="yaml" title="aquilia.yaml — modules section">
{`modules:
  - name: users
    version: "1.2.0"
    description: User management
    route_prefix: /api/v1/users
    fault_domain: identity
    depends_on:
      - auth
    tags:
      - Users
      - Identity
    auto_discover: apps/users
    controllers:
      - UserController
      - ProfileController
    services:
      - UserService
      - ProfileService
    models:
      - models/user.amdl
      - models/profile.amdl
    database:
      url: postgresql://identity-db/users
      auto_connect: true
      auto_migrate: true
      pool_size: 15`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`mt-12 pt-6 border-t flex justify-between ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
        <Link
          to="/docs/config/workspace"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          ← Workspace Builder
        </Link>
        <Link
          to="/docs/config/integrations"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          Integrations <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
