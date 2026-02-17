import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { FolderTree, ArrowRight, Folder, FileCode } from 'lucide-react'

export function ProjectStructurePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FolderTree className="w-4 h-4" />
          Getting Started
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Project Structure
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia follows a modular project structure with composable modules and Python packaging conventions. This guide shows how to organize your application for clarity and scalability.
        </p>
      </div>

      {/* Standard Layout */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Standard Project Layout</h2>
        <CodeBlock language="text" filename="Project Structure">{`my-aquilia-app/
├── starter.py                  # Application entry point
├── workspace.py                # Workspace-level configuration (optional)
├── pyproject.toml               # Python project metadata
├── requirements.txt             # Dependencies
│
├── config/                      # Configuration files
│   ├── workspace.yaml           # Main workspace config
│   ├── development.yaml         # Dev overrides
│   └── production.yaml          # Production overrides
│
├── modules/                     # Application modules
│   ├── __init__.py
│   ├── products/                # A feature module
│   │   ├── __init__.py
│   │   ├── controller.py        # HTTP controller
│   │   ├── model.py             # Database model(s)
│   │   ├── service.py           # Business logic
│   │   ├── serializer.py        # Request/response serializers
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_products.py
│   │
│   ├── auth/                    # Auth module
│   │   ├── __init__.py
│   │   ├── controller.py
│   │   ├── service.py
│   │   └── guards.py
│   │
│   └── notifications/           # Notifications module
│       ├── __init__.py
│       ├── service.py
│       └── templates/
│           └── welcome.html
│
├── migrations/                  # Database migrations
│   ├── 0001_initial.py
│   └── 0002_add_products.py
│
├── artifacts/                   # Templates, static, etc.
│   ├── templates/
│   │   ├── base.html
│   │   └── pages/
│   └── static/
│       ├── css/
│       └── js/
│
└── tests/                       # Integration tests
    ├── conftest.py
    ├── test_integration.py
    └── test_e2e.py`}</CodeBlock>
      </section>

      {/* Key Files */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Files Explained</h2>
        <div className="space-y-4">
          {[
            {
              icon: <FileCode className="w-5 h-5" />,
              file: 'starter.py',
              desc: 'The application entry point. Creates an AquiliaServer instance, registers controllers, services, models, and middleware, then calls app.run(). This is the file you execute to start your server.',
            },
            {
              icon: <FileCode className="w-5 h-5" />,
              file: 'workspace.py',
              desc: 'Optional workspace-level configuration using the WorkspaceConfigBuilder. Defines app-wide settings like database URLs, secret keys, allowed hosts, and middleware order.',
            },
            {
              icon: <Folder className="w-5 h-5" />,
              file: 'config/',
              desc: 'YAML configuration files loaded by ConfigLoader. Supports layered loading: workspace.yaml (base), then environment-specific overrides. Values are accessible via app.config.',
            },
            {
              icon: <Folder className="w-5 h-5" />,
              file: 'modules/',
              desc: 'Feature modules organized by domain. Each module contains its own controller, model, service, and tests. This keeps concerns separated and makes the codebase navigable.',
            },
            {
              icon: <Folder className="w-5 h-5" />,
              file: 'migrations/',
              desc: 'Auto-generated database migration files. Created by the Aquilia CLI (aquilia makemigrations). Applied with aquilia migrate.',
            },
            {
              icon: <Folder className="w-5 h-5" />,
              file: 'artifacts/',
              desc: 'Static assets and templates. The template engine looks here for Jinja2 templates. The static middleware serves files from artifacts/static/.',
            },
          ].map((item, i) => (
            <div key={i} className={`flex gap-4 p-5 rounded-xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
              <div className="text-aquilia-500 shrink-0 mt-0.5">{item.icon}</div>
              <div>
                <code className={`font-mono font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.file}</code>
                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Module Anatomy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Module Anatomy</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each feature module follows a consistent pattern. Here's what a typical module looks like:
        </p>
        <CodeBlock language="python" filename="modules/products/__init__.py">{`"""Products module — handles product CRUD operations."""

from .controller import ProductController
from .model import Product
from .service import ProductService

__all__ = ["ProductController", "Product", "ProductService"]`}</CodeBlock>

        <div className={`p-6 rounded-2xl border mt-6 ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Module Composition</h3>
          <svg viewBox="0 0 600 250" className="w-full" fill="none">
            <defs>
              <marker id="mod-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0,8 3,0 6" className="fill-aquilia-500/50" />
              </marker>
            </defs>

            {/* Controller */}
            <rect x="220" y="10" width="160" height="45" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
            <text x="300" y="38" textAnchor="middle" className="fill-aquilia-500 text-xs font-bold">Controller</text>

            {/* Arrows */}
            <line x1="260" y1="55" x2="160" y2="95" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#mod-arrow)" />
            <line x1="340" y1="55" x2="440" y2="95" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#mod-arrow)" />

            {/* Service */}
            <rect x="80" y="95" width="160" height="45" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="160" y="123" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>Service</text>

            {/* Serializer */}
            <rect x="360" y="95" width="160" height="45" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="440" y="123" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>Serializer</text>

            {/* Arrow to Model */}
            <line x1="160" y1="140" x2="260" y2="180" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#mod-arrow)" />

            {/* Model */}
            <rect x="220" y="175" width="160" height="45" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
            <text x="300" y="203" textAnchor="middle" className={`text-xs font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>Model</text>

            {/* Labels */}
            <text x="195" y="80" className={`text-[9px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>injects</text>
            <text x="380" y="80" className={`text-[9px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>validates</text>
            <text x="195" y="170" className={`text-[9px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>queries</text>
          </svg>
        </div>
      </section>

      {/* Registration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registering Modules</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Register your module's components in the starter file:
        </p>
        <CodeBlock language="python" filename="starter.py">{`from aquilia import AquiliaServer
from aquilia.di import Singleton

from modules.products import ProductController, Product, ProductService
from modules.auth import AuthController, AuthService


app = AquiliaServer()

# Database
app.use_database("sqlite:///db.sqlite3")

# Models
app.register_model(Product)

# Services (DI registration)
app.container.register(ProductService, lifetime=Singleton)
app.container.register(AuthService, lifetime=Singleton)

# Controllers
app.register_controller(ProductController)
app.register_controller(AuthController)

app.run()`}</CodeBlock>
      </section>

      {/* Next */}
      <section>
        <div className="flex gap-4">
          <Link to="/docs/controllers" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Controllers <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Learn about the controller architecture in depth</p>
          </Link>
          <Link to="/docs/server" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Server <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Understand AquiliaServer and lifecycle</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
