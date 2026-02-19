import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, FileText } from 'lucide-react'

export function TemplatesOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FileText className="w-4 h-4" />
          Advanced / Templates
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Template Engine
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          AquilaTemplates is a first-class Jinja2-based template rendering system with async support, sandboxed execution, bytecode caching, DI integration, session/auth context injection, and hot-reload in development.
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <div className="space-y-3">
          {[
            { name: 'TemplateEngine', desc: 'Core rendering engine. Loads templates, manages environment, renders to strings or responses.' },
            { name: 'TemplateLoader / PackageLoader', desc: 'Discovers templates from directories or module packages. Supports multi-directory resolution.' },
            { name: 'BytecodeCache', desc: 'Caches compiled template bytecode — InMemoryBytecodeCache or CrousBytecodeCache (artifact-backed).' },
            { name: 'TemplateManager', desc: 'Linting, validation, and administration of templates. Reports unused variables and syntax issues.' },
            { name: 'TemplateSandbox', desc: 'Sandboxed Jinja2 execution with SandboxPolicy for restricting what templates can access.' },
            { name: 'TemplateContext', desc: 'Auto-injected context variables: request, session, identity, flash messages, CSRF token.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.templates(
            dirs=["templates"],          # Template directories
            auto_reload=True,            # Hot-reload in dev mode
            auto_escape=True,            # HTML auto-escaping
            bytecode_cache="memory",     # "memory" | "crous" | None
            sandboxed=True,              # Enable sandbox mode
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Usage in Controllers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Rendering Templates</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Inject
from aquilia.templates import TemplateEngine


class PageController(Controller):
    prefix = ""

    @Inject()
    def __init__(self, templates: TemplateEngine):
        self.templates = templates

    @Get("/")
    async def home(self, ctx):
        """Render using Controller.render() helper."""
        products = await Product.objects.filter(featured=True).to_list()
        return await self.render("home.html", {
            "title": "Home",
            "products": products,
        }, ctx)

    @Get("/profile")
    async def profile(self, ctx):
        """Render using TemplateEngine directly."""
        html = await self.templates.render_to_string(
            "users/profile.html",
            {"user": ctx.identity},
        )
        return ctx.html(html)

    @Get("/dashboard")
    async def dashboard(self, ctx):
        """Render to response with custom status."""
        return await self.templates.render_to_response(
            "dashboard.html",
            {"stats": await get_stats()},
            status=200,
        )`}</CodeBlock>
      </section>

      {/* Template Syntax */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template Syntax</h2>
        <CodeBlock language="html" filename="templates/base.html">{`<!DOCTYPE html>
<html lang="en">
<head>
    <title>{% block title %}My App{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
    <nav>
        {% if identity %}
            <span>Welcome, {{ identity.username }}</span>
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
    </nav>

    {% for message in get_flashed_messages() %}
        <div class="flash flash-{{ message.category }}">
            {{ message.message }}
        </div>
    {% endfor %}

    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>`}</CodeBlock>

        <CodeBlock language="html" filename="templates/products/list.html">{`{% extends "base.html" %}

{% block title %}Products{% endblock %}

{% block content %}
<h1>Products</h1>
<div class="grid">
    {% for product in products %}
    <div class="card">
        <h2>{{ product.name }}</h2>
        <p class="price">\${{ "%.2f"|format(product.price) }}</p>
        <a href="{{ url_for('ProductController.detail', id=product.id) }}">
            View Details
        </a>
    </div>
    {% else %}
    <p>No products found.</p>
    {% endfor %}
</div>
{% endblock %}`}</CodeBlock>
      </section>

      {/* Auto-injected Context */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Injected Context</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Variable</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { v: 'request', d: 'The current AquiliaRequest object' },
                { v: 'identity', d: 'The authenticated user identity (or None)' },
                { v: 'session', d: 'The current session dict (if sessions enabled)' },
                { v: 'csrf_token', d: 'CSRF token for forms' },
                { v: 'get_flashed_messages()', d: 'Retrieve and clear flash messages' },
                { v: 'url_for(handler, **params)', d: 'Reverse URL generation' },
                { v: 'static(path)', d: 'Generate static file URL' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.v}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/websockets" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> WebSockets
        </Link>
        <Link to="/docs/mail" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Mail <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
