import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'

export function TemplatesSecurity() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Templates / Security
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Template Security
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia templates execute in a sandboxed environment by default. <code className="text-aquilia-400">TemplateSandbox</code> and <code className="text-aquilia-400">SandboxPolicy</code> control which Python objects, attributes, and functions are accessible from templates.
        </p>
      </div>

      {/* TemplateSandbox */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TemplateSandbox</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The sandbox prevents templates from accessing dangerous Python internals, modifying objects, or executing arbitrary code.
        </p>
        <CodeBlock language="python" filename="sandbox.py">{`from aquilia.templates import TemplateSandbox, SandboxPolicy

# Default policy: safe attributes only
sandbox = TemplateSandbox()

# Custom policy
policy = SandboxPolicy(
    allowed_attributes=["id", "name", "email", "created_at"],
    blocked_attributes=["password", "secret_key", "_internal"],
    allowed_functions=["len", "range", "enumerate"],
    blocked_modules=["os", "sys", "subprocess"],
    max_template_size=1024 * 1024,  # 1 MB
    max_render_time=5.0,            # 5 seconds
)

sandbox = TemplateSandbox(policy=policy)`}</CodeBlock>
      </section>

      {/* SandboxPolicy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SandboxPolicy Options</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Option</th>
                  <th className="text-left pb-3 font-semibold">Type</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['allowed_attributes', 'list[str]', 'Whitelist of object attributes accessible in templates'],
                  ['blocked_attributes', 'list[str]', 'Blacklist of attributes (overrides allowed)'],
                  ['allowed_functions', 'list[str]', 'Builtin functions available in templates'],
                  ['blocked_modules', 'list[str]', 'Python modules that cannot be imported'],
                  ['max_template_size', 'int', 'Maximum template file size in bytes'],
                  ['max_render_time', 'float', 'Maximum render time in seconds'],
                  ['auto_escape', 'bool', 'Auto-escape HTML output (default: True)'],
                ].map(([opt, type, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{opt}</td>
                    <td className="py-2 text-xs">{type}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Auto-Escaping */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Escaping</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          All template output is auto-escaped by default to prevent XSS attacks. Use the <code className="text-aquilia-400">|safe</code> filter only when you trust the content.
        </p>
        <CodeBlock language="html" filename="template.html">{`{# Escaped by default — safe from XSS #}
<p>{{ user.bio }}</p>

{# Explicitly mark as safe (use with caution) #}
<div>{{ trusted_html|safe }}</div>

{# CSRF token in forms #}
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    ...
</form>`}</CodeBlock>
      </section>
    </div>
  )
}
