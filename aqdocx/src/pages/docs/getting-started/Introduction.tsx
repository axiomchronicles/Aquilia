import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, Zap, Shield, Database, Box, Globe, Layers, Cpu, Workflow, Terminal, BookOpen } from 'lucide-react'

export function IntroductionPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <BookOpen className="w-4 h-4" />
          Getting Started
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Introduction to <span className="gradient-text">Aquilia</span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia is a production-ready, full-featured, async-native Python web framework. It provides everything you need to build scalable web applications — from controllers and DI to ORM, auth, WebSockets, and MLOps — all in a single, cohesive package.
        </p>
      </div>

      {/* What is Aquilia */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>What is Aquilia?</h2>
        <div className={`p-6 rounded-2xl border mb-6 ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <p className={`leading-relaxed mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Aquilia is a <strong>batteries-included</strong> async Python web framework built from the ground up for modern web development. Unlike microframeworks that require you to assemble dozens of third-party packages, Aquilia ships with a comprehensive set of integrated subsystems:
          </p>
          <ul className={`space-y-2 ml-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            {[
              'Class-based controllers with compile-time route resolution',
              'Hierarchical dependency injection with scoped lifetimes',
              'Production-grade async ORM with migrations and relationships',
              'Built-in authentication (OAuth2/OIDC, MFA, API Keys)',
              'Cryptographic session management',
              'Multi-backend caching with stampede prevention',
              'WebSocket support with namespace controllers',
              'Jinja2 async template engine',
              'Mail service with SMTP/SES/SendGrid providers',
              'MLOps platform with model serving and drift detection',
              'Structured fault/error handling with domains and severity',
              'OpenAPI spec generation',
              'Full CLI with generators and scaffolding',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-aquilia-500 mt-1">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Quick Example */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Example</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Here's a taste of what an Aquilia application looks like:
        </p>
        <CodeBlock language="python" filename="app.py">{`from aquilia import AquiliaServer, Controller, Get, Post, Inject
from aquilia import Model, CharField, IntegerField
from aquilia.di import Container, Singleton


# Define a model
class Product(Model):
    name = CharField(max_length=200)
    price = IntegerField()

    class Meta:
        table_name = "products"


# Define a service
class ProductService:
    async def list_all(self):
        return await Product.objects.all()

    async def create(self, name: str, price: int):
        return await Product.objects.create(name=name, price=price)


# Define a controller
class ProductController(Controller):
    prefix = "/products"

    @Inject()
    def __init__(self, service: ProductService):
        self.service = service

    @Get("/")
    async def list_products(self, ctx):
        products = await self.service.list_all()
        return ctx.json({"products": [p.to_dict() for p in products]})

    @Post("/")
    async def create_product(self, ctx):
        body = await ctx.json_body()
        product = await self.service.create(body["name"], body["price"])
        return ctx.json({"product": product.to_dict()}, status=201)


# Bootstrap the application
app = AquiliaServer()
app.container.register(ProductService, lifetime=Singleton)
app.register_controller(ProductController)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)`}</CodeBlock>
      </section>

      {/* Philosophy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Design Philosophy</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { icon: <Layers className="w-6 h-6" />, title: 'Batteries Included', desc: 'Every subsystem is built-in and designed to work together. No need to hunt for compatible third-party packages.' },
            { icon: <Zap className="w-6 h-6" />, title: 'Async-Native', desc: 'Built from the ground up for async/await. Every I/O operation is non-blocking, powered by ASGI.' },
            { icon: <Shield className="w-6 h-6" />, title: 'Type-Safe', desc: 'Full type annotations throughout. Designed for great IDE support and static analysis.' },
            { icon: <Box className="w-6 h-6" />, title: 'Convention over Config', desc: 'Sensible defaults with layered configuration. Start fast, customize when you need to.' },
            { icon: <Workflow className="w-6 h-6" />, title: 'Manifest-First', desc: 'Controllers declare their dependencies, effects, and metadata upfront via manifests.' },
            { icon: <Terminal className="w-6 h-6" />, title: 'Production-Ready', desc: 'Structured error handling, observability, lifecycle management, and deployment tools built in.' },
          ].map((item, i) => (
            <div key={i} className={`p-6 rounded-xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
              <div className="text-aquilia-500 mb-3">{item.icon}</div>
              <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture Overview */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture at a Glance</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 800 400" className="w-full" fill="none">
            {/* Client Layer */}
            <rect x="300" y="10" width="200" height="50" rx="12" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="400" y="40" textAnchor="middle" className={`text-sm font-bold ${isDark ? 'fill-white' : 'fill-gray-800'}`}>HTTP / WS Client</text>

            {/* Arrow */}
            <line x1="400" y1="60" x2="400" y2="85" className={`${isDark ? 'stroke-zinc-600' : 'stroke-gray-400'}`} strokeWidth="1.5" markerEnd="url(#arrowhead)" />

            {/* ASGI Layer */}
            <rect x="200" y="85" width="400" height="45" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
            <text x="400" y="113" textAnchor="middle" className="fill-aquilia-500 text-sm font-semibold">ASGI Adapter → Middleware Stack</text>

            <line x1="400" y1="130" x2="400" y2="155" className={`${isDark ? 'stroke-zinc-600' : 'stroke-gray-400'}`} strokeWidth="1.5" />

            {/* Controller Layer */}
            <rect x="150" y="155" width="500" height="45" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
            <text x="400" y="183" textAnchor="middle" className="fill-aquilia-500 text-sm font-semibold">Controller Engine → Route Resolution → Handler</text>

            <line x1="400" y1="200" x2="400" y2="225" className={`${isDark ? 'stroke-zinc-600' : 'stroke-gray-400'}`} strokeWidth="1.5" />

            {/* Service Layer */}
            <rect x="100" y="225" width="600" height="45" rx="10" className={`${isDark ? 'fill-zinc-800/50 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="400" y="253" textAnchor="middle" className={`text-sm font-semibold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>DI Container → Services / Effects / Guards</text>

            <line x1="400" y1="270" x2="400" y2="295" className={`${isDark ? 'stroke-zinc-600' : 'stroke-gray-400'}`} strokeWidth="1.5" />

            {/* Data Layer */}
            <g>
              <rect x="50" y="295" width="140" height="40" rx="8" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1" />
              <text x="120" y="320" textAnchor="middle" className={`text-xs font-medium ${isDark ? 'fill-gray-400' : 'fill-gray-600'}`}>ORM / Models</text>

              <rect x="210" y="295" width="140" height="40" rx="8" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1" />
              <text x="280" y="320" textAnchor="middle" className={`text-xs font-medium ${isDark ? 'fill-gray-400' : 'fill-gray-600'}`}>Cache Service</text>

              <rect x="370" y="295" width="140" height="40" rx="8" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1" />
              <text x="440" y="320" textAnchor="middle" className={`text-xs font-medium ${isDark ? 'fill-gray-400' : 'fill-gray-600'}`}>Sessions / Auth</text>

              <rect x="530" y="295" width="140" height="40" rx="8" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1" />
              <text x="600" y="320" textAnchor="middle" className={`text-xs font-medium ${isDark ? 'fill-gray-400' : 'fill-gray-600'}`}>Templates / Mail</text>

              <rect x="690" y="295" width="90" height="40" rx="8" className={`${isDark ? 'fill-zinc-800 stroke-zinc-700' : 'fill-gray-100 stroke-gray-300'}`} strokeWidth="1" />
              <text x="735" y="320" textAnchor="middle" className={`text-xs font-medium ${isDark ? 'fill-gray-400' : 'fill-gray-600'}`}>MLOps</text>
            </g>

            {/* Lifecycle bar */}
            <rect x="50" y="360" width="730" height="30" rx="6" className="fill-aquilia-500/5 stroke-aquilia-500/20" strokeWidth="1" />
            <text x="400" y="380" textAnchor="middle" className="fill-aquilia-500/60 text-xs font-medium">Lifecycle Coordinator · Fault System · Observability · Config Loader</text>

            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" className="fill-aquilia-500/50" />
              </marker>
            </defs>
          </svg>
        </div>
        <p className={`mt-4 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
          Every layer in the Aquilia stack is designed to be async, composable, and observable. The <Link to="/docs/architecture" className="text-aquilia-500 hover:underline">Architecture</Link> page goes deep into each layer.
        </p>
      </section>

      {/* Feature Grid */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Subsystems</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { icon: <Layers />, label: 'Controllers', to: '/docs/controllers', desc: 'Class-based HTTP/WS controllers with decorators and DI' },
            { icon: <Box />, label: 'DI Container', to: '/docs/di', desc: 'Hierarchical scoped dependency injection system' },
            { icon: <Database />, label: 'Models & ORM', to: '/docs/models', desc: 'Async ORM with models, fields, queries, migrations' },
            { icon: <Shield />, label: 'Auth & Sessions', to: '/docs/auth', desc: 'Authentication, authorization, and session management' },
            { icon: <Globe />, label: 'WebSockets', to: '/docs/websockets', desc: 'Real-time socket controllers and adapters' },
            { icon: <Cpu />, label: 'MLOps', to: '/docs/mlops', desc: 'Model packaging, serving, and drift detection' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <div className="text-aquilia-500 mb-3 w-5 h-5">{item.icon}</div>
              <h3 className={`font-bold text-sm mb-1 group-hover:text-aquilia-500 transition-colors ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.label}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Next Steps */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Next Steps</h2>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/docs/installation" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Installation <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Install Aquilia and set up your development environment</p>
          </Link>
          <Link to="/docs/quickstart" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Quick Start <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Build your first Aquilia app in under 5 minutes</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
