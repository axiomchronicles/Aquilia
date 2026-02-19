import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../components/NextSteps'
import { Server, Layers, Settings, Shield, Database, Zap, Globe, AlertCircle } from 'lucide-react'

export function ServerOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Server className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                AquiliaServer
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.server — Main server orchestration</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>AquiliaServer</code> is the central orchestrator that wires together every subsystem —
          from Aquilary manifest compilation to ASGI request handling. It is a 2,400+ line class that
          serves as the single entry point for the entire framework.
        </p>
      </div>

      {/* Constructor */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 text-aquilia-400" />
          Constructor
        </h2>

        <CodeBlock
          code={`from aquilia.server import AquiliaServer
from aquilia.config import ConfigLoader
from aquilia.aquilary import RegistryMode

server = AquiliaServer(
    manifests=[CoreManifest, UsersManifest],  # List of manifest classes
    config=ConfigLoader(),                     # Optional: custom config loader
    mode=RegistryMode.PROD,                    # DEV, PROD, or TEST
    aquilary_registry=None,                    # Optional: pre-built AquilaryRegistry
)`}
          language="python"
        />

        <div className={`mt-4 rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['manifests', 'List[Any] | None', 'List of manifest classes. Required unless aquilary_registry is provided.'],
                ['config', 'ConfigLoader | None', 'Configuration loader instance. Created automatically if None.'],
                ['mode', 'RegistryMode', 'Registry mode: DEV (relaxed), PROD (strict), TEST (mocks). Default: PROD.'],
                ['aquilary_registry', 'AquilaryRegistry | None', 'Pre-built registry for advanced usage. Bypasses manifest compilation.'],
              ].map(([param, type, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{param}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Initialization sequence */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Initialization Sequence
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>__init__</code> method performs the following steps in order. Understanding this
          sequence is critical for debugging boot issues:
        </p>

        <CodeBlock
          code={`# AquiliaServer.__init__() sequence:

# 1. Load configuration
self.config = config or ConfigLoader()

# 2. Initialize fault engine
self.fault_engine = FaultEngine(debug=self._is_debug())

# 3. Apply fault integration patches to subsystems
from aquilia.faults.integrations import patch_all_subsystems
patch_all_subsystems()

# 4. Build Aquilary registry from manifests
self.aquilary = Aquilary.from_manifests(
    manifests=manifests,
    config=self.config,
    mode=mode,
)

# 5. Create RuntimeRegistry (lazy compilation)
self.runtime = RuntimeRegistry.from_metadata(self.aquilary, self.config)
self.runtime._register_services()  # Populate DI containers immediately

# 6. Register framework services in every DI container
#    - FaultEngine (scope: app)
#    - EffectRegistry (scope: app)

# 7. Create LifecycleCoordinator
self.coordinator = LifecycleCoordinator(self.runtime, self.config)

# 8. Setup middleware stack
#    - ExceptionMiddleware (priority: 1)
#    - RequestIdMiddleware (priority: 2)
#    - LoggingMiddleware (priority: 3)
#    - FaultMiddleware (priority: 4)
#    - SessionMiddleware (priority: 5)
#    - AquilAuthMiddleware (priority: 10)
#    - TemplateMiddleware (priority: 15)
#    - Security middleware (CORS, CSP, etc.) (priority: 20-30)
#    - RateLimitMiddleware (if configured) (priority: 30)
#    - StaticMiddleware (if configured) (priority: 40)

# 9. Create controller pipeline
#    - ControllerFactory (with base DI container)
#    - ControllerEngine (with fault engine)
#    - ControllerCompiler

# 10. Initialize trace directory (.aquilia/)
self.trace = AquiliaTrace()

# 11. Create ASGI adapter
self.app = ASGIAdapter(
    controller_router=self.controller_router,
    controller_engine=self.controller_engine,
    socket_runtime=self.aquila_sockets,
    middleware_stack=self.middleware_stack,
    server=self,
)`}
          language="python"
        />
      </section>

      {/* Key Attributes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 text-aquilia-400" />
          Key Attributes
        </h2>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Attribute</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['config', 'ConfigLoader', 'Merged configuration object with layered resolution'],
                ['fault_engine', 'FaultEngine', 'Fault signal processor with handler chain'],
                ['aquilary', 'AquilaryRegistry', 'Compiled manifest registry with app metadata'],
                ['runtime', 'RuntimeRegistry', 'DI containers, compiled routes, model schemas'],
                ['coordinator', 'LifecycleCoordinator', 'Dependency-ordered startup/shutdown manager'],
                ['controller_router', 'ControllerRouter', 'URL pattern → CompiledRoute matcher'],
                ['controller_engine', 'ControllerEngine', 'Route dispatch and pipeline execution'],
                ['controller_factory', 'ControllerFactory', 'Controller instantiation with DI'],
                ['controller_compiler', 'ControllerCompiler', 'Decorator metadata → CompiledRoute'],
                ['middleware_stack', 'MiddlewareStack', 'Priority-ordered middleware chain'],
                ['aquila_sockets', 'AquilaSockets', 'WebSocket runtime (if configured)'],
                ['app', 'ASGIAdapter', 'The callable ASGI application'],
                ['trace', 'AquiliaTrace', '.aquilia/ diagnostic writer'],
              ].map(([attr, type, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{attr}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Middleware Setup */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Middleware Setup
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>_setup_middleware()</code> method builds the middleware stack from configuration.
          Middleware is added conditionally based on what integrations are enabled:
        </p>

        <CodeBlock
          code={`# Always added:
ExceptionMiddleware(debug=True)      # Priority 1 — global error handling
RequestIdMiddleware()                 # Priority 2 — os.urandom-based request IDs
LoggingMiddleware()                   # Priority 3 — structured logging

# Added if faults configured:
FaultMiddleware(fault_engine)         # Priority 4 — fault signal interception

# Added if sessions configured:
SessionMiddleware(session_engine)     # Priority 5 — session load/save

# Added if auth configured:
AquilAuthMiddleware(auth_manager)     # Priority 10 — identity extraction

# Added if templates configured:
TemplateMiddleware(template_engine)   # Priority 15 — template engine injection

# Added if security configured (via _setup_security_middleware):
CORSMiddleware(...)                   # Priority 20
CSPMiddleware(...)                    # Priority 21
CSRFMiddleware(...)                   # Priority 22
HSTSMiddleware(...)                   # Priority 23
SecurityHeadersMiddleware(...)        # Priority 24
HTTPSRedirectMiddleware(...)          # Priority 25
ProxyFixMiddleware(...)               # Priority 26

# Added if rate limiting configured:
RateLimitMiddleware(...)              # Priority 30

# Added if static files configured:
StaticMiddleware(...)                 # Priority 40`}
          language="python"
        />
      </section>

      {/* Session Engine Creation */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Session & Auth Setup
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The server supports three configuration formats for sessions, handled by
          <code>_create_session_engine()</code>:
        </p>

        <CodeBlock
          code={`# Format 1: Flat dict (from YAML or simple Python config)
sessions:
  secret_key: "my-secret"
  max_age: 3600
  cookie_name: "aq_session"

# Format 2: Integration builder (recommended)
Integration.sessions(
    secret_key="my-secret",
    max_age=3600,
    store="memory",          # "memory" or "file"
    transport="cookie",      # "cookie" or "header"
)

# Format 3: Full policy objects (advanced)
from aquilia.sessions import SessionPolicy, PersistencePolicy, TransportPolicy
Integration.sessions(
    policy=SessionPolicy(
        max_age=3600,
        idle_timeout=900,
        max_sessions_per_user=5,
    ),
    persistence=PersistencePolicy(
        save_on_read=False,
        save_on_write=True,
    ),
    transport=TransportPolicy(
        cookie_name="aq_session",
        cookie_httponly=True,
        cookie_samesite="Lax",
    ),
)`}
          language="python"
        />
      </section>

      {/* startup/shutdown */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Startup & Shutdown
        </h2>

        <CodeBlock
          code={`# startup() is called automatically by the ASGI adapter on first request,
# or can be called manually:

await server.startup()
# 1. Idempotent: uses asyncio.Lock to prevent double startup
# 2. Loads controllers from RuntimeRegistry
# 3. Registers OpenAPI docs routes (if configured)
# 4. Loads WebSocket controllers
# 5. Registers AMDL models (legacy support, 5 phases)
# 6. Runs LifecycleCoordinator.startup() — executes all on_startup hooks
# 7. Writes trace artifacts to .aquilia/
# 8. Sets self._startup_complete = True

await server.shutdown()
# 1. Runs LifecycleCoordinator.shutdown() — reverse dependency order
# 2. Closes all DI container finalizers
# 3. Shuts down WebSocket connections
# 4. Logs shutdown summary`}
          language="python"
        />
      </section>

      {/* run() method */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Globe className="w-5 h-5 text-aquilia-400" />
          Running the Server
        </h2>

        <CodeBlock
          code={`# Using the run() convenience method (wraps uvicorn):
server.run(host="0.0.0.0", port=8000)

# Or use the ASGI adapter directly with any ASGI server:
import uvicorn
uvicorn.run(server.app, host="0.0.0.0", port=8000)

# Or with hypercorn:
import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config

config = Config()
config.bind = ["0.0.0.0:8000"]
asyncio.run(serve(server.app, config))`}
          language="python"
        />

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            <strong>Production tip:</strong> Use <code>aq serve</code> for production deployments. It
            runs uvicorn with production-optimized settings (no reload, access logs, worker configuration).
            Use <code>aq run</code> for development (auto-reload enabled).
          </p>
        </div>
      </section>

      {/* Debug mode */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Debug Mode
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When <code>debug=True</code> (via config, <code>AQ_DEBUG=true</code>, or <code>RegistryMode.DEV</code>),
          the server enables:
        </p>

        <ul className={`space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Debug error pages</strong> — ExceptionMiddleware renders rich HTML error pages with tracebacks, request details, and source code context</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Verbose logging</strong> — Full request/response body logging</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Trace writes</strong> — .aquilia/ artifacts are updated on every boot</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Relaxed validation</strong> — Missing optional providers don't cause boot failures</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-aquilia-400 mt-1">•</span>
            <div><strong>Auto-reload</strong> — File watcher restarts server on code changes (uvicorn --reload)</div>
          </li>
        </ul>
      </section>

      {/* Next */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Related</h2>
        <div className="flex flex-col gap-2">
          <Link to="/docs/server/asgi" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → ASGI Adapter: How Aquilia bridges ASGI and its internal pipeline
          </Link>
          <Link to="/docs/server/lifecycle" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Lifecycle: Dependency-ordered startup/shutdown coordination
          </Link>
          <Link to="/docs/middleware/stack" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → MiddlewareStack: How middleware ordering works
          </Link>
        </div>
      </section>

      <NextSteps />
    </div>
  )
}