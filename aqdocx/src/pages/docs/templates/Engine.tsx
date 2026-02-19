import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Palette } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function TemplatesEngine() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Palette className="w-4 h-4" />
          Templates / TemplateEngine
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            TemplateEngine
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">TemplateEngine</code> is the core rendering engine built on Jinja2. It supports async rendering, DI injection, automatic context population, and integrates with the manifest system for template discovery.
        </p>
      </div>

      {/* Core API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core API</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Method</th>
                  <th className="text-left pb-3 font-semibold">Returns</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['render(name, context)', 'str', 'Render a template to string'],
                  ['render_to_response(name, context, status?)', 'Response', 'Render and wrap in an HTTP response'],
                  ['render_string(source, context)', 'str', 'Render an inline template string'],
                  ['get_template(name)', 'Template', 'Load a template object for deferred rendering'],
                  ['template_exists(name)', 'bool', 'Check if a template file exists'],
                ].map(([method, ret, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{method}</td>
                    <td className="py-2 font-mono text-xs">{ret}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Usage in Controllers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage in Controllers</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, GET
from aquilia.templates import TemplateEngine

class ProfileController(Controller):
    prefix = "/profile"

    def __init__(self, templates: TemplateEngine):
        self.templates = templates

    @GET("/")
    async def view(self, ctx):
        user = ctx.identity
        return await self.templates.render_to_response(
            "users/profile.html",
            {"user": user, "title": "My Profile"},
        )

    @GET("/settings")
    async def settings(self, ctx):
        return await self.templates.render_to_response(
            "users/settings.html",
            {"user": ctx.identity},
            status=200,
        )`}</CodeBlock>
      </section>

      {/* Context */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template Context</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">TemplateContext</code> automatically populates common variables like the current request, session, flash messages, and CSRF tokens.
        </p>
        <CodeBlock language="python" filename="context.py">{`from aquilia.templates import TemplateContext, create_template_context

# Auto-populated context includes:
# - request: current request object
# - session: session data (if sessions enabled)
# - flash: flash messages (if sessions enabled)
# - csrf_token: CSRF token (if CSRF middleware active)
# - identity: authenticated user (if auth enabled)
# - config: app configuration subset

ctx = create_template_context(
    request=request,
    user_context={"products": products},
)
# Merges user data with auto-populated data`}</CodeBlock>
      </section>

      {/* Bytecode Cache */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Bytecode Cache</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Pre-compiles templates to bytecode for faster rendering. Two implementations available.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {[
            { name: 'InMemoryBytecodeCache', desc: 'Stores compiled templates in memory. Fast but lost on restart.' },
            { name: 'CrousBytecodeCache', desc: 'Stores in .crous artifact directory. Persistent across restarts.' },
          ].map((c, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{c.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* DI Providers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Environment Presets</h2>
        <CodeBlock language="python" filename="presets.py">{`from aquilia.templates import (
    create_development_engine,
    create_production_engine,
    create_testing_engine,
)

# Development: auto-reload, debug mode, no bytecode cache
dev_engine = create_development_engine(template_dirs=["templates/"])

# Production: bytecode cache, no auto-reload, strict undefined
prod_engine = create_production_engine(template_dirs=["templates/"])

# Testing: in-memory loader, strict undefined, no caching
test_engine = create_testing_engine()`}</CodeBlock>
      </section>

      {/* Session & Auth Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Session & Auth Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Template proxies expose session and auth data safely in templates.
        </p>
        <CodeBlock language="python" filename="integrations.py">{`# In your Jinja2 templates:
# {{ session.user_id }}
# {{ flash.messages }}
# {{ identity.username }}
# {{ identity.has_role("admin") }}

# Python-side registration:
from aquilia.templates import (
    SessionTemplateProxy,
    IdentityTemplateProxy,
    FlashMessages,
)

# These are auto-registered when sessions/auth integrations are active`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}