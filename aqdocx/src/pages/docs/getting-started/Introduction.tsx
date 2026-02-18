import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { BookOpen, Zap, Shield, Layers, Database, Plug, Cpu, Rocket, Globe, Terminal, Box, Workflow, Brain, AlertCircle, Gauge } from 'lucide-react'

export function IntroductionPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const features = [
    {
      icon: <Layers className="w-5 h-5 text-aquilia-400" />,
      title: 'Manifest-Driven Architecture',
      desc: 'Declare your application topology through Python manifests. The framework compiles them into an immutable artifact graph — no magic, no discovery at import time.',
    },
    {
      icon: <Plug className="w-5 h-5 text-blue-400" />,
      title: 'Async-First DI Container',
      desc: 'Six scopes (singleton, app, request, transient, pooled, ephemeral), <3 µs cached lookups, cycle detection, and full graph diagnostics — all without annotations or XML.',
    },
    {
      icon: <Database className="w-5 h-5 text-emerald-400" />,
      title: 'Pure-Python ORM',
      desc: 'Django-grade metaclass-driven ORM with 30+ field types, Q-object query builder, Manager/QuerySet, migrations, signals, transactions, and aggregation.',
    },
    {
      icon: <Shield className="w-5 h-5 text-rose-400" />,
      title: 'Batteries-Included Security',
      desc: 'Identity model, JWT/RS256 token management, Argon2 password hashing, RBAC/ABAC authorization, OAuth2/OIDC, MFA, and session-based auth with policy enforcement.',
    },
    {
      icon: <AlertCircle className="w-5 h-5 text-amber-400" />,
      title: 'Typed Fault System',
      desc: 'Domain-specific fault taxonomy with severity levels, recovery strategies, and a FaultEngine that transforms unhandled exceptions into structured fault signals.',
    },
    {
      icon: <Globe className="w-5 h-5 text-cyan-400" />,
      title: 'WebSocket Controllers',
      desc: 'Decorator-based WebSocket handlers with per-connection DI, room management, namespace support, guards, and pluggable adapters (in-memory, Redis).',
    },
    {
      icon: <Gauge className="w-5 h-5 text-violet-400" />,
      title: 'Multi-Layer Caching',
      desc: 'Memory (LRU/LFU/TTL), Redis, and Composite (L1+L2) backends. Decorator-driven caching with @cached, @cache_aside, and @invalidate.',
    },
    {
      icon: <Brain className="w-5 h-5 text-pink-400" />,
      title: 'MLOps Integration',
      desc: 'Model packaging, versioned registry, HTTP serving, drift detection, and release management — bring ML models into your API with first-class support.',
    },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero */}
      <div className="relative mb-12">
        <div className="absolute -inset-4 bg-gradient-to-r from-aquilia-500/10 via-blue-500/5 to-purple-500/10 rounded-3xl blur-2xl" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-4">
            <img src="/logo.png" alt="Aquilia" className="w-12 h-12 rounded-2xl shadow-lg shadow-aquilia-500/20" />
            <div>
              <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Aquilia Framework
              </h1>
              <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>v0.2.0 · Production-ready async Python web framework</p>
            </div>
          </div>

          <p className={`text-lg leading-relaxed mb-6 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <strong>Stop writing routing, config, and deployment boilerplate. Focus only on business logic.</strong>
          </p>

          <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 mt-8`}>
            <div>
              <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>What is Aquilia?</h3>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                Aquilia is an async-first Python framework built on an <strong>auto-discovery architecture</strong>. It features a built-in ORM, production-ready infrastructure generation, and ML deployment built-in. It removes the friction of wiring components together manually.
              </p>
            </div>
            <div>
              <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Who is it for?</h3>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                Teams building data-intensive applications who want the speed of modern async Python without the fragility of micro-frameworks or the bloat of legacy monoliths.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Core Philosophy */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Brain className="w-5 h-5 text-aquilia-400" />
          Core Philosophy
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* The Problem */}
          <div className={`rounded-xl border p-6 ${isDark ? 'bg-red-500/5 border-red-500/10' : 'bg-red-50 border-red-100'}`}>
            <h3 className={`font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-red-400' : 'text-red-700'}`}>
              The Problem With Modern Frameworks
            </h3>
            <ul className={`space-y-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              <li className="flex items-start gap-3">
                <span className="text-red-400 mt-1">✕</span>
                <div>Too much configuration wiring components together</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-400 mt-1">✕</span>
                <div>Deployment infrastructure is an afterthought</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-400 mt-1">✕</span>
                <div>ML integration is painful and disjointed</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-400 mt-1">✕</span>
                <div>Boilerplate everywhere for basic features</div>
              </li>
            </ul>
          </div>

          {/* Aquilia's Approach */}
          <div className={`rounded-xl border p-6 ${isDark ? 'bg-emerald-500/5 border-emerald-500/10' : 'bg-emerald-50 border-emerald-100'}`}>
            <h3 className={`font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
              Aquilia's Approach
            </h3>
            <ul className={`space-y-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              <li className="flex items-start gap-3">
                <span className="text-emerald-400 mt-1">✓</span>
                <div><strong>Auto-discovery</strong> eliminates wiring boilerplate</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-emerald-400 mt-1">✓</span>
                <div><strong>Convention over configuration</strong> — sensible defaults</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-emerald-400 mt-1">✓</span>
                <div><strong>Infrastructure generation</strong> built-in</div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-emerald-400 mt-1">✓</span>
                <div><strong>ML-first mindset</strong> with integrated model registry</div>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Feature Overview
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((f, i) => (
            <div
              key={i}
              className={`rounded-xl border p-5 transition-all hover:scale-[1.01] ${isDark ? 'bg-zinc-900/50 border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-300'}`}
            >
              <div className="flex items-center gap-3 mb-2">
                {f.icon}
                <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.title}</h3>
              </div>
              <p className={`text-sm leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline overview */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Cpu className="w-5 h-5 text-aquilia-400" />
          Architecture at a Glance
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every Aquilia application follows a deterministic pipeline from boot to request handling:
        </p>

        <CodeBlock
          code={`# ──── Boot Pipeline ────────────────────────────────────────────
#
#   Manifests           →  Aquilary.from_manifests()
#   Aquilary            →  RuntimeRegistry.from_metadata()
#   RuntimeRegistry     →  DI containers + compiled routes + model schemas
#   AquiliaServer       →  MiddlewareStack + ControllerRouter + ASGIAdapter
#
# ──── Request Pipeline ────────────────────────────────────────
#
#   ASGI scope          →  ASGIAdapter.__call__()
#   Middleware chain     →  RequestId → Exception → Logging → Session → Auth → …
#   Pattern matching     →  ControllerRouter.match(path, method)
#   Controller engine    →  ControllerEngine.handle(compiled_route, ctx)
#   Controller factory   →  ControllerFactory.create(cls)   [per-request DI]
#   Handler method       →  controller.method(ctx: RequestCtx)
#   Response             →  Response.json() / .html() / .stream() / .sse() / .file()`}
          language="python"
        />
      </section>

      {/* Minimal Example */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Rocket className="w-5 h-5 text-aquilia-400" />
          Minimal Example
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          A complete Aquilia application in three files:
        </p>

        <div className="space-y-4">
          <div>
            <p className={`text-sm font-mono mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>workspace.py</p>
            <CodeBlock
              code={`from aquilia import Workspace, Module, Integration

app = (
    Workspace("my-api")
    .module(
        Module("core")
        .auto_discover("modules/core")
    )
    .integrate(
        Integration.auth(),
        Integration.sessions(),
        Integration.database(url="sqlite:///db.sqlite3"),
    )
    .build()
)`}
              language="python"
            />
          </div>

          <div>
            <p className={`text-sm font-mono mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>modules/core/controllers.py</p>
            <CodeBlock
              code={`from aquilia import Controller, GET, POST, RequestCtx, Response

class HealthController(Controller):
    prefix = "/health"

    @GET("/")
    async def check(self, ctx: RequestCtx) -> Response:
        return Response.json({"status": "ok"})


class UsersController(Controller):
    prefix = "/users"

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    @GET("/")
    async def list_users(self, ctx: RequestCtx) -> Response:
        users = await self.user_service.list_all()
        return Response.json({"users": users})

    @POST("/")
    async def create_user(self, ctx: RequestCtx) -> Response:
        data = await ctx.json()
        user = await self.user_service.create(data)
        return Response.json(user, status=201)`}
              language="python"
            />
          </div>

          <div>
            <p className={`text-sm font-mono mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>modules/core/services.py</p>
            <CodeBlock
              code={`from aquilia import service

@service(scope="app")
class UserService:
    def __init__(self, db: Database):
        self.db = db

    async def list_all(self):
        return await self.db.fetch_all("SELECT * FROM users")

    async def create(self, data: dict):
        return await self.db.execute(
            "INSERT INTO users (name, email) VALUES (:name, :email)",
            data,
        )`}
              language="python"
            />
          </div>
        </div>

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-emerald-50 border-emerald-200'}`}>
          <p className={`text-sm ${isDark ? 'text-emerald-300' : 'text-emerald-700'}`}>
            <strong>Run it:</strong> <code className="font-mono">aq run</code> or <code className="font-mono">python -m aquilia.cli run</code> — starts the development server with auto-reload on port 8000.
          </p>
        </div>
      </section>

      {/* Subsystem Map */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Box className="w-5 h-5 text-aquilia-400" />
          Subsystem Map
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia is organized into cohesive subsystems, each covered in depth by this documentation:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Subsystem</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Package</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Key Classes</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['Server', 'aquilia.server', 'AquiliaServer'],
                ['Config', 'aquilia.config, config_builders', 'ConfigLoader, Workspace, Module, Integration'],
                ['Controllers', 'aquilia.controller', 'Controller, GET/POST/PUT/PATCH/DELETE/WS'],
                ['DI', 'aquilia.di', 'Container, Provider, Inject, @service, @factory'],
                ['Models', 'aquilia.models', 'Model, Field types, Manager, QuerySet, Q'],
                ['Sessions', 'aquilia.sessions', 'SessionEngine, SessionPolicy, SessionState'],
                ['Auth', 'aquilia.auth', 'AuthManager, TokenManager, PasswordHasher, AuthzEngine'],
                ['Middleware', 'aquilia.middleware', 'MiddlewareStack, CORS, CSP, CSRF, RateLimit'],
                ['Serializers', 'aquilia.serializers', 'Serializer, ModelSerializer, ListSerializer'],
                ['Blueprints', 'aquilia.blueprints', 'Blueprint, Facet, Projection, Cast, Seal'],
                ['Cache', 'aquilia.cache', 'CacheService, MemoryBackend, RedisBackend'],
                ['Mail', 'aquilia.mail', 'AquilaMail, MailService, EmailMessage'],
                ['WebSockets', 'aquilia.sockets', 'AquilaSockets, SocketController, @Event'],
                ['Templates', 'aquilia.templates', 'TemplateEngine, TemplateLoader'],
                ['Faults', 'aquilia.faults', 'Fault, FaultEngine, FaultDomain, Severity'],
                ['Effects', 'aquilia.effects', 'Effect, EffectProvider, EffectRegistry'],
                ['CLI', 'aquilia.cli', 'aq init/add/generate/validate/run/serve'],
                ['Testing', 'aquilia.testing', 'TestClient, AquiliaTestCase'],
                ['Trace', 'aquilia.trace', 'AquiliaTrace, TraceManifest, TraceDIGraph'],
                ['MLOps', 'aquilia.mlops', 'ModelPack, ModelRegistry, ModelServer'],
              ].map(([name, pkg, classes], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{name}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{pkg}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{classes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Quick Navigation */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Terminal className="w-5 h-5 text-aquilia-400" />
          Where to Go Next
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { to: '/docs/installation', icon: <Rocket className="w-4 h-4" />, title: 'Installation', desc: 'Install Aquilia and set up your environment' },
            { to: '/docs/quickstart', icon: <Zap className="w-4 h-4" />, title: 'Quick Start', desc: 'Build your first API in 5 minutes' },
            { to: '/docs/architecture', icon: <Cpu className="w-4 h-4" />, title: 'Architecture', desc: 'Understand the manifest-driven pipeline' },
            { to: '/docs/controllers/overview', icon: <Layers className="w-4 h-4" />, title: 'Controllers', desc: 'Class-based request handlers with DI' },
            { to: '/docs/di/container', icon: <Plug className="w-4 h-4" />, title: 'Dependency Injection', desc: 'Six-scope DI container with async support' },
            { to: '/docs/models/defining', icon: <Database className="w-4 h-4" />, title: 'Models & ORM', desc: 'Metaclass-driven ORM with migrations' },
          ].map((link, i) => (
            <Link
              key={i}
              to={link.to}
              className={`flex items-start gap-3 p-4 rounded-xl border transition-all hover:scale-[1.01] ${isDark ? 'bg-zinc-900/50 border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-300'}`}
            >
              <div className="mt-0.5 text-aquilia-400">{link.icon}</div>
              <div>
                <div className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{link.title}</div>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{link.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
