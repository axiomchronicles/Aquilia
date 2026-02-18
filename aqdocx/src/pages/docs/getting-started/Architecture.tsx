import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Network, Layers, Cpu, Database, Box, Shield, Workflow, Plug, ArrowRight } from 'lucide-react'

export function ArchitecturePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Network className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>How Aquilia boots, compiles, and serves requests</p>
          </div>
        </div>
      </div>

      {/* Overview */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Overview
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia follows a <strong>manifest → compile → serve</strong> architecture. Unlike
          frameworks that discover components at import time, Aquilia separates declaration
          from execution through a two-phase pipeline:
        </p>

        <div className={`rounded-xl border p-6 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
          <ol className={`space-y-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-xs font-bold flex-shrink-0">1</span>
              <div><strong>Declaration phase</strong> — You write manifests (or use Workspace/Module/Integration builders) that declare what exists: controllers, services, models, middleware, templates.</div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-xs font-bold flex-shrink-0">2</span>
              <div><strong>Compilation phase</strong> — The Aquilary registry validates manifests and compiles them into a RuntimeRegistry with DI containers, compiled routes, and model schemas.</div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-xs font-bold flex-shrink-0">3</span>
              <div><strong>Serving phase</strong> — AquiliaServer builds the middleware stack, ASGI adapter, and lifecycle coordinator, then serves requests through the compiled controller router.</div>
            </li>
          </ol>
        </div>
      </section>

      {/* Boot Pipeline */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Cpu className="w-5 h-5 text-aquilia-400" />
          Boot Pipeline
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When you call <code>aq run</code> or instantiate <code>AquiliaServer</code>, the following chain executes:
        </p>

        <CodeBlock
          code={`# 1. ConfigLoader reads workspace.py (Python-first) or aquilia.yaml (YAML fallback)
config = ConfigLoader()

# 2. Aquilary.from_manifests() validates and indexes all manifest classes
aquilary = Aquilary.from_manifests(
    manifests=[CoreManifest, UsersManifest],
    config=config,
    mode=RegistryMode.PROD,   # DEV, PROD, or TEST
)

# 3. RuntimeRegistry.from_metadata() compiles Aquilary into runtime artifacts
#    - Creates DI Container per app (scope: "app")
#    - Registers ClassProvider for each service
#    - Compiles ControllerCompiler routes for each controller
#    - Builds model schemas through ModelMeta
runtime = RuntimeRegistry.from_metadata(aquilary, config)

# 4. AquiliaServer wires everything together
server = AquiliaServer(
    manifests=[CoreManifest, UsersManifest],
    config=config,
    mode=RegistryMode.PROD,
)
# Internally:
#   → Creates FaultEngine
#   → Builds Aquilary + RuntimeRegistry
#   → Registers services in DI containers
#   → Sets up MiddlewareStack (12+ layers)
#   → Creates ControllerFactory, ControllerEngine, ControllerCompiler
#   → Creates ControllerRouter
#   → Builds ASGIAdapter
#   → Initializes AquiliaTrace (.aquilia/ directory)`}
          language="python"
        />
      </section>

      {/* Component Graph */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Workflow className="w-5 h-5 text-aquilia-400" />
          Component Graph
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The following components are initialized during boot and their relationships:
        </p>

        <CodeBlock
          code={`AquiliaServer
├── ConfigLoader                 # Layered config (CLI > env > .env > config files > defaults)
├── FaultEngine                  # Typed fault handling with domains and severity
├── Aquilary                     # Manifest registry
│   ├── AquilaryRegistry         # Validated app metadata indexed by name
│   └── Fingerprinter            # Content-addressed hashing of artifacts
├── RuntimeRegistry              # Compiled runtime state
│   ├── DI Containers            # One Container per app module (scope: "app")
│   │   └── Providers            # ClassProvider, FactoryProvider, ValueProvider, …
│   ├── Compiled Routes          # CompiledController → CompiledRoute[]
│   └── Model Schemas            # ModelMeta metaclass → table definitions
├── MiddlewareStack              # Priority-ordered middleware chain
│   ├── ExceptionMiddleware      # Global error → Response mapping (priority: 1)
│   ├── RequestIdMiddleware      # X-Request-ID header (priority: 2)
│   ├── LoggingMiddleware        # Structured request logging (priority: 3)
│   ├── FaultMiddleware          # Fault signal interception (priority: 4)
│   ├── SessionMiddleware        # Session load/save per request (priority: 5)
│   ├── AquilAuthMiddleware      # Identity extraction from token/session (priority: 10)
│   ├── TemplateMiddleware       # Template engine injection (priority: 15)
│   └── Security middleware      # CORS, CSP, CSRF, HSTS, etc. (priority: 20–30)
├── ControllerRouter             # URL pattern → CompiledRoute mapping
├── ControllerEngine             # Route dispatch + pipeline execution
├── ControllerFactory            # Controller instantiation with DI
├── ControllerCompiler           # Decorator metadata → CompiledRoute
├── ASGIAdapter                  # ASGI ↔ Aquilia bridge
├── LifecycleCoordinator         # Dependency-ordered startup/shutdown
├── AquilaSockets                # WebSocket runtime (if enabled)
└── AquiliaTrace                 # .aquilia/ diagnostic directory`}
          language="text"
        />
      </section>

      {/* Request Lifecycle */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Request Lifecycle
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every incoming ASGI request flows through this pipeline:
        </p>

        <CodeBlock
          code={`# 1. ASGI scope arrives at ASGIAdapter.__call__()
#    The adapter distinguishes between HTTP and WebSocket scopes.

# 2. For HTTP: ASGIAdapter wraps the raw ASGI scope into a Request object
request = Request(scope, receive, send)

# 3. RequestCtx is constructed with request, identity, session, container, state
ctx = RequestCtx(
    request=request,
    identity=None,         # Set by AuthMiddleware
    session=None,          # Set by SessionMiddleware
    container=container,   # Per-request DI container (child of app container)
    state={},              # Mutable state dict for middleware data
    request_id=None,       # Set by RequestIdMiddleware
)

# 4. Middleware chain executes (outermost → innermost):
#    RequestId → Exception → Logging → Fault → Session → Auth → Template → …
#    Each middleware calls: await next_handler(request, ctx)

# 5. ControllerRouter.match(path, method) → CompiledRoute
#    Pattern matching uses CompiledPattern with «name:type» syntax

# 6. ControllerEngine.handle(compiled_route, ctx)
#    a. ControllerFactory.create(controller_cls) — per-request DI injection
#    b. Execute pipeline nodes (guards → transforms → handler)
#    c. Call controller.on_request(ctx) lifecycle hook
#    d. Call handler method: response = await controller.method(ctx, **params)
#    e. Call controller.on_response(ctx, response) lifecycle hook

# 7. Response flows back through middleware chain (innermost → outermost)
#    Session middleware saves session, Auth middleware may set cookies, etc.

# 8. Response.send(send) serializes to ASGI and sends to client`}
          language="python"
        />
      </section>

      {/* Middleware ordering */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Middleware Ordering
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Middleware is ordered by <strong>scope</strong> (global {"<"} app {"<"} controller {"<"} route) and then
          by <strong>priority</strong> (lower number = outermost). The default stack:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-2 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Priority</th>
                <th className={`text-left px-4 py-2 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Middleware</th>
                <th className={`text-left px-4 py-2 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Purpose</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['1', 'ExceptionMiddleware', 'Catches unhandled exceptions, renders debug pages or JSON error'],
                ['2', 'RequestIdMiddleware', 'Generates X-Request-ID via os.urandom (no UUID overhead)'],
                ['3', 'LoggingMiddleware', 'Structured request/response logging with timing'],
                ['4', 'FaultMiddleware', 'Intercepts Fault signals and converts to HTTP responses'],
                ['5', 'SessionMiddleware', 'Loads session from store, saves after response'],
                ['10', 'AquilAuthMiddleware', 'Extracts Identity from JWT/session, sets ctx.identity'],
                ['15', 'TemplateMiddleware', 'Injects template engine into request context'],
                ['20', 'CORSMiddleware', 'Cross-origin resource sharing headers'],
                ['21', 'CSPMiddleware', 'Content-Security-Policy header'],
                ['22', 'CSRFMiddleware', 'Cross-site request forgery token validation'],
                ['23', 'HSTSMiddleware', 'HTTP Strict Transport Security header'],
                ['24', 'SecurityHeadersMiddleware', 'X-Frame-Options, X-Content-Type-Options, etc.'],
                ['25', 'HTTPSRedirectMiddleware', 'Redirect HTTP → HTTPS'],
                ['30', 'RateLimitMiddleware', 'Request rate limiting per IP/key'],
                ['40', 'StaticMiddleware', 'Serve static files from configured directory'],
              ].map(([pri, name, purpose], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{pri}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{name}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* DI Architecture */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Plug className="w-5 h-5 text-aquilia-400" />
          DI Container Hierarchy
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia creates a hierarchy of DI containers that mirror the scoping model:
        </p>

        <CodeBlock
          code={`# Container Hierarchy:
#
#   Root Container (scope: "singleton")
#       │
#       ├── App Container (scope: "app") — one per Module
#       │   ├── FaultEngine (singleton)
#       │   ├── EffectRegistry (singleton)
#       │   ├── CacheService (app)
#       │   ├── MailService (app)
#       │   └── UserService (app)
#       │
#       └── Request Container (scope: "request") — created per-request
#           ├── Session (request)
#           ├── Identity (request)
#           └── RequestCtx (request)
#
# Resolution flow:
#   1. Check request container cache
#   2. If not found, check app container
#   3. If scope is "singleton"/"app", delegate to parent
#   4. Instantiate via provider.instantiate(ctx)
#   5. Cache in appropriate scope container`}
          language="python"
        />
      </section>

      {/* Config layers */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 text-aquilia-400" />
          Configuration Layering
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configuration is resolved through a layered merge strategy (higher priority wins):
        </p>

        <CodeBlock
          code={`# Priority order (highest → lowest):
#
#   1. CLI arguments           (--port 9000)
#   2. Environment variables   (AQ_PORT=9000)
#   3. .env file               (AQ_PORT=9000)
#   4. workspace.py            (Workspace("app").runtime(port=9000))
#   5. aquilia.yaml            (runtime: { port: 9000 })
#   6. Framework defaults      (port: 8000)
#
# Environment variable prefix: AQ_
# Nested keys use double underscores: AQ_DATABASE__URL=postgres://...`}
          language="python"
        />
      </section>

      {/* Registry Modes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Box className="w-5 h-5 text-aquilia-400" />
          Registry Modes
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The Aquilary registry operates in one of three modes, affecting validation strictness and
          debug output:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Mode</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Behavior</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              <tr className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                <td className={`px-4 py-2 font-mono text-sm ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>DEV</td>
                <td className={`px-4 py-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Relaxed validation, debug error pages, auto-reload, verbose logging, trace writes enabled</td>
              </tr>
              <tr className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                <td className={`px-4 py-2 font-mono text-sm ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>PROD</td>
                <td className={`px-4 py-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Strict validation, JSON error responses, no debug pages, trace writes disabled, performance optimizations</td>
              </tr>
              <tr className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                <td className={`px-4 py-2 font-mono text-sm ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>TEST</td>
                <td className={`px-4 py-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Relaxed validation, test-specific providers, mock-friendly lifecycle, TransactionTestCase support</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Next Steps */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Next Steps</h2>
        <div className="flex flex-col gap-2">
          <Link to="/docs/project-structure" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Project Structure: File layout and conventions
          </Link>
          <Link to="/docs/server/aquilia-server" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → AquiliaServer: Server initialization in depth
          </Link>
          <Link to="/docs/aquilary/overview" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Aquilary Registry: Manifest compilation internals
          </Link>
        </div>
      </section>
    </div>
  )
}
