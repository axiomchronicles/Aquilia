import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { motion } from 'framer-motion'
import { Network, Layers, Cpu, Database, Box, Shield, Workflow, Plug, ArrowRight } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

const ArchitectureDiagram = ({ isDark }: { isDark: boolean }) => {
  const accentColor = '#22c55e' // aquilia-500
  const textColor = isDark ? '#e4e4e7' : '#1f2937'

  return (
    <div className="w-full overflow-hidden p-4 md:p-8 my-8 flex justify-center bg-transparent">
      <svg viewBox="0 0 1000 850" className="w-full max-w-5xl h-auto">
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="softGlow" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <marker id="arrow-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill={accentColor} />
          </marker>
        </defs>

        {/* --- ZONE 1: DEFINITION (Top Left) --- */}
        <motion.g initial={{ x: 50, y: 50 }} animate={{ y: [50, 45, 50] }} transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}>
          <rect x="0" y="0" width="220" height="140" rx="16" fill="transparent" stroke={accentColor} strokeWidth="1" strokeDasharray="4,4" opacity="0.4" />
          <text x="110" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold" className="font-mono opacity-60">I. Definition Layer</text>

          <g transform="translate(20, 20)">
            <rect x="0" y="0" width="180" height="30" rx="6" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="15" y="20" fill={accentColor} fontSize="11" fontWeight="bold">Manifests (declarative.py)</text>
          </g>
          <g transform="translate(20, 60)">
            <rect x="0" y="0" width="180" height="30" rx="6" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="15" y="20" fill={accentColor} fontSize="11" fontWeight="bold">Module Blueprints</text>
          </g>
          <g transform="translate(20, 100)">
            <rect x="0" y="0" width="180" height="30" rx="6" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="15" y="20" fill={accentColor} fontSize="11" fontWeight="bold">Component Meta</text>
          </g>
        </motion.g>

        {/* --- ZONE 2: CORE ENGINE (Top Center) --- */}
        <motion.g initial={{ x: 390, y: 50 }} animate={{ y: [50, 55, 50] }} transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}>
          <rect x="0" y="0" width="220" height="140" rx="16" fill={isDark ? "rgba(34, 197, 94, 0.05)" : "rgba(34, 197, 94, 0.02)"} stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
          <text x="110" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold" className="font-mono">II. Core Engine</text>

          <text x="110" y="30" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="bold">Aquilary Indexer</text>

          <motion.rect x="20" y="50" width="180" height="20" rx="4" fill={accentColor} opacity="0.1" animate={{ opacity: [0.1, 0.3, 0.1] }} transition={{ duration: 2, repeat: Infinity }} />
          <text x="30" y="64" fill={textColor} fontSize="9" fontWeight="medium">Lifecycle Coordinator</text>

          <motion.rect x="20" y="80" width="180" height="20" rx="4" fill={accentColor} opacity="0.1" animate={{ opacity: [0.1, 0.3, 0.1] }} transition={{ duration: 2, repeat: Infinity, delay: 0.6 }} />
          <text x="30" y="94" fill={textColor} fontSize="9" fontWeight="medium">Config Merging (AQ_*)</text>

          <motion.rect x="20" y="110" width="180" height="20" rx="4" fill={accentColor} opacity="0.1" animate={{ opacity: [0.1, 0.3, 0.1] }} transition={{ duration: 2, repeat: Infinity, delay: 1.2 }} />
          <text x="30" y="124" fill={textColor} fontSize="9" fontWeight="medium">Route Snapshoter</text>
        </motion.g>

        {/* --- ZONE 3: DI HUB (Center) --- */}
        <motion.g initial={{ x: 350, y: 250 }} animate={{ scale: [1, 1.02, 1] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}>
          <rect x="0" y="0" width="300" height="220" rx="24" fill={isDark ? "rgba(34, 197, 94, 0.08)" : "rgba(34, 197, 94, 0.04)"} stroke={accentColor} strokeWidth="3" filter="url(#glow)" />
          <text x="150" y="-20" textAnchor="middle" fill={textColor} fontSize="16" fontWeight="extrabold" className="font-mono tracking-tighter">DI HUB (CONTAINER)</text>

          <g transform="translate(20, 30)">
            <rect x="0" y="0" width="260" height="40" rx="8" fill={accentColor} opacity="0.15" stroke={accentColor} strokeWidth="1" />
            <text x="20" y="25" fill={textColor} fontSize="11" fontWeight="bold">SINGLETON SCOPE (Global)</text>
            <circle cx="240" cy="20" r="4" fill={accentColor} filter="url(#softGlow)" />
          </g>

          <g transform="translate(20, 85)">
            <rect x="0" y="0" width="260" height="60" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" strokeDasharray="3,3" />
            <text x="20" y="25" fill={textColor} fontSize="11" fontWeight="bold">APP SCOPE (Per-Module)</text>
            <text x="20" y="45" fill={accentColor} fontSize="9" opacity="0.7">Services, Providers, Managers</text>
          </g>

          <g transform="translate(20, 160)">
            <rect x="0" y="0" width="260" height="40" rx="8" fill={accentColor} opacity="0.2" stroke={accentColor} strokeWidth="2" />
            <text x="20" y="25" fill={textColor} fontSize="11" fontWeight="black">REQUEST SCOPE (Ephemera)</text>
            <motion.circle cx="240" cy="20" r="5" fill={accentColor} animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, repeat: Infinity }} filter="url(#glow)" />
          </g>
        </motion.g>

        {/* --- ZONE 4: REQUEST PIPELINE (Left column) --- */}
        <motion.g initial={{ x: 50, y: 250 }}>
          <rect x="0" y="0" width="220" height="450" rx="20" fill="transparent" stroke={accentColor} strokeWidth="1" opacity="0.3" />
          <text x="110" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold" className="font-mono opacity-60">III. Request Flow</text>

          <g transform="translate(20, 40)">
            <rect x="0" y="0" width="180" height="40" rx="10" fill={accentColor} stroke={accentColor} strokeWidth="2" opacity="0.15" />
            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="12" fontWeight="bold">ASGI ADAPTER</text>
          </g>

          {/* Middleware Tower */}
          <g transform="translate(30, 100)">
            <rect x="0" y="0" width="160" height="280" rx="12" fill={isDark ? "#121212" : "#f8f8f8"} stroke={accentColor} strokeWidth="1.5" />
            <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="10" fontWeight="black">MIDDLEWARE STACK</text>

            {['AUTH', 'SESSION', 'RATELIMIT', 'FAULT', 'TRACE'].map((mw, i) => (
              <g key={mw} transform={`translate(15, ${50 + i * 45})`}>
                <rect x="0" y="0" width="130" height="35" rx="6" fill={accentColor} opacity={0.1 + i * 0.05} />
                <text x="65" y="22" textAnchor="middle" fill={textColor} fontSize="9" fontWeight="bold">{mw}</text>
              </g>
            ))}
          </g>

          <g transform="translate(20, 400)">
            <rect x="0" y="0" width="180" height="40" rx="10" fill={accentColor} opacity="0.3" stroke={accentColor} strokeWidth="1" />
            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="12" fontWeight="black">ROUTER (MATCH)</text>
          </g>
        </motion.g>

        {/* --- ZONE 5: EXECUTION HUB (Right column) --- */}
        <motion.g initial={{ x: 730, y: 250 }} animate={{ y: [250, 260, 250] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}>
          <rect x="0" y="0" width="220" height="300" rx="24" fill={isDark ? "rgba(34, 197, 94, 0.05)" : "rgba(34, 197, 94, 0.02)"} stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
          <text x="110" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold" className="font-mono">IV. Execution Hub</text>

          <g transform="translate(20, 30)">
            <rect x="0" y="0" width="180" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">CONTROLLER FACTORY</text>
          </g>

          <g transform="translate(20, 85)">
            <rect x="0" y="0" width="180" height="130" rx="12" fill="transparent" stroke={accentColor} strokeWidth="1" opacity="0.4" />
            <text x="90" y="20" textAnchor="middle" fill={accentColor} fontSize="9" fontWeight="black">PIPELINE NODES</text>

            <rect x="20" y="35" width="140" height="25" rx="4" fill={accentColor} opacity="0.1" />
            <text x="90" y="52" textAnchor="middle" fill={textColor} fontSize="9">Guards (AuthZ)</text>

            <rect x="20" y="70" width="140" height="25" rx="4" fill={accentColor} opacity="0.1" />
            <text x="90" y="87" textAnchor="middle" fill={textColor} fontSize="9">Transformers (Pydantic)</text>

            <rect x="20" y="105" width="140" height="15" rx="2" fill={accentColor} opacity="0.4" filter="url(#softGlow)" />
            <text x="90" y="117" textAnchor="middle" fill={textColor} fontSize="9" fontWeight="bold">HANDLER</text>
          </g>

          <g transform="translate(20, 230)">
            <rect x="0" y="0" width="180" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">RESPONSE ENGINE</text>
          </g>
        </motion.g>

        {/* --- ZONE 6: PERIPHERAL SYSTEMS (Bottom) --- */}
        <motion.g initial={{ x: 50, y: 730 }}>
          <rect x="0" y="0" width="900" height="100" rx="20" fill="transparent" stroke={accentColor} strokeWidth="1" strokeDasharray="10,5" opacity="0.3" />
          <text x="450" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold" className="font-mono opacity-50">V. Satellite Subsystems</text>

          <g transform="translate(40, 30)">
            <rect x="0" y="0" width="150" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="75" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">EFFECTS (DB/CACHE)</text>
          </g>
          <g transform="translate(210, 30)">
            <rect x="0" y="0" width="150" height="40" rx="8" fill={accentColor} opacity="0.15" stroke={accentColor} strokeWidth="1" />
            <text x="75" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">MLOPS REGISTRY</text>
          </g>
          <g transform="translate(380, 30)">
            <rect x="0" y="0" width="150" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="75" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">MAIL / TEMPLATES</text>
          </g>
          <g transform="translate(550, 30)">
            <rect x="0" y="0" width="150" height="40" rx="8" fill={accentColor} opacity="0.15" stroke={accentColor} strokeWidth="1" />
            <text x="75" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">TASK QUEUE (CELERY)</text>
          </g>
          <g transform="translate(720, 30)">
            <rect x="0" y="0" width="140" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
            <text x="70" y="25" textAnchor="middle" fill={textColor} fontSize="11" fontWeight="bold">FAULT ENGINE</text>
          </g>
        </motion.g>

        {/* --- CONNECTIONS (Circuit Paths) --- */}
        <g opacity="0.4">
          {/* I -> II */}
          <path d="M 270 120 L 390 120" stroke={accentColor} strokeWidth="2" fill="none" strokeDasharray="5,5" />

          {/* II -> III */}
          <path d="M 500 190 L 500 250" stroke={accentColor} strokeWidth="2" fill="none" />

          {/* III -> IV (Middleware to DI) */}
          <path d="M 270 500 L 350 400" stroke={accentColor} strokeWidth="2" fill="none" strokeDasharray="3,3" />

          {/* Router -> Hub */}
          <path d="M 270 670 H 840 V 550" stroke={accentColor} strokeWidth="2" fill="none" />

          {/* Hub -> Subsystems */}
          <path d="M 840 550 V 730" stroke={accentColor} strokeWidth="2" fill="none" markerEnd="url(#arrow-green)" />
        </g>

        {/* DATA PACKETS (Pulses) */}
        <motion.circle r="4" fill={accentColor} filter="url(#glow)"
          animate={{ cx: [270, 390], cy: 120, opacity: [0, 1, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />

        <motion.circle r="5" fill={accentColor} filter="url(#glow)"
          animate={{ cx: [270, 840, 840], cy: [670, 670, 550], opacity: [0, 1, 1, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        />

        <motion.circle r="3" fill={accentColor} filter="url(#glow)"
          animate={{ cx: [30, 30, 140], cy: [290, 650, 650], opacity: [0, 1, 1, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    </div>
  )
}

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
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Architecture
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
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

        <p className={`mb-8 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia follows a <strong>manifest → compile → serve</strong> architecture. Unlike
          frameworks that discover components at import time, Aquilia separates declaration
          from execution through a two-phase pipeline:
        </p>

        <ArchitectureDiagram isDark={isDark} />
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

      <NextSteps />
    </div>
  )
}
