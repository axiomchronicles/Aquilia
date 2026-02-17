import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Palette } from 'lucide-react'

export function TemplatesLoaders() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Palette className="w-4 h-4" />
          Templates / Loaders
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Template Loaders
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Loaders control how templates are discovered and read from the filesystem or packages. Aquilia provides <code className="text-aquilia-400">TemplateLoader</code> for filesystem loading and <code className="text-aquilia-400">PackageLoader</code> for loading from installed Python packages.
        </p>
      </div>

      {/* TemplateLoader */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TemplateLoader</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Filesystem-based template loading with support for multiple directories, file extensions, and encoding options.
        </p>
        <CodeBlock language="python" filename="loader.py">{`from aquilia.templates import TemplateLoader

loader = TemplateLoader(
    search_dirs=[
        "templates/",           # App templates
        "shared/templates/",    # Shared templates
    ],
    extensions=[".html", ".jinja2", ".txt"],
    encoding="utf-8",
    follow_links=False,
)`}</CodeBlock>
      </section>

      {/* PackageLoader */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PackageLoader</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Loads templates from installed Python packages. Useful for reusable component libraries.
        </p>
        <CodeBlock language="python" filename="package.py">{`from aquilia.templates import PackageLoader

# Load templates from an installed package
loader = PackageLoader(
    package_name="aquilia_admin",
    package_path="templates",
)
# Resolves: aquilia_admin/templates/admin/dashboard.html`}</CodeBlock>
      </section>

      {/* Manifest-Aware Loader */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Manifest-Aware Loading</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The manifest integration auto-discovers template directories from registered Aquilary modules.
        </p>
        <CodeBlock language="python" filename="manifest.py">{`from aquilia.templates import (
    discover_template_directories,
    create_manifest_aware_loader,
    ModuleTemplateRegistry,
)

# Auto-discover from manifests
dirs = discover_template_directories(registry)
# → ["modules/users/templates", "modules/products/templates", ...]

# Create a loader that knows about all modules
loader = create_manifest_aware_loader(registry)

# Module template registry tracks which module owns which templates
mod_registry = ModuleTemplateRegistry(registry)
owner = mod_registry.get_owner("users/profile.html")
# → "users" module`}</CodeBlock>
      </section>

      {/* TemplateManager */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TemplateManager</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">TemplateManager</code> validates templates at build time, catching errors before deployment.
        </p>
        <CodeBlock language="python" filename="manager.py">{`from aquilia.templates import TemplateManager, TemplateLintIssue

manager = TemplateManager(engine)

# Lint all templates
issues: list[TemplateLintIssue] = manager.lint()
for issue in issues:
    print(f"{issue.template}:{issue.line} - {issue.message}")

# Precompile all templates to bytecode
await manager.precompile()

# List all available templates
templates = manager.list_templates()
# → ["base.html", "users/profile.html", ...]`}</CodeBlock>
      </section>

      {/* TemplateMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TemplateMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Automatically adds template context variables (request, session, CSRF token) to every template render.
        </p>
        <CodeBlock language="python" filename="middleware.py">{`from aquilia.templates import TemplateMiddleware

# Added automatically when templates integration is active
workspace.middleware([
    TemplateMiddleware(),
])`}</CodeBlock>
      </section>
    </div>
  )
}
