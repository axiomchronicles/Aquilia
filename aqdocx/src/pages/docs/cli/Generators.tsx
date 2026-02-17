import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Terminal } from 'lucide-react'

export function CLIGenerators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Terminal className="w-4 h-4" />
          CLI / Generators
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Code Generators
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's CLI includes code generators for scaffolding modules, controllers, models, serializers, and custom commands. All generators use the <code className="text-aquilia-400">.crous</code> template system.
        </p>
      </div>

      {/* Module Generator */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Module Generator</h2>
        <CodeBlock language="bash" filename="terminal">{`# Full module with all components
aq add products --with-models --with-auth --with-templates

# Generated structure:
# modules/products/
# ├── __init__.py
# ├── manifest.py          # Module manifest
# ├── controller.py        # ProductController
# ├── models.py            # Product model
# ├── serializers.py       # ProductSerializer
# ├── urls.py              # Route definitions
# ├── permissions.py       # Auth guards
# ├── templates/           # Jinja2 templates
# │   └── products/
# │       ├── list.html
# │       └── detail.html
# └── tests/
#     ├── __init__.py
#     ├── test_controller.py
#     └── test_models.py`}</CodeBlock>
      </section>

      {/* Custom Commands */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom CLI Commands</h2>
        <CodeBlock language="python" filename="commands.py">{`from aquilia.cli import cli_command, Argument, Option

@cli_command("seed_db")
async def seed_database(
    count: Argument[int] = 100,
    model: Option[str] = "all",
    clear: Option[bool] = False,
):
    """Seed the database with test data."""
    if clear:
        await clear_database()
    
    if model == "all":
        await seed_users(count)
        await seed_products(count)
    else:
        await seed_model(model, count)
    
    print(f"Seeded {count} records")

# Usage: aq run seed_db --count 50 --model users --clear`}</CodeBlock>
      </section>

      {/* Template Engine (.crous) */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>.crous Templates</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Generator templates use the <code className="text-aquilia-400">.crous</code> format — a simple templating syntax for code generation.
        </p>
        <CodeBlock language="python" filename="artifacts/templates.crous">{`# Template variables: {{module_name}}, {{class_name}}, {{fields}}
# Conditionals: {% if with_auth %}...{% endif %}
# Loops: {% for field in fields %}...{% endfor %}

# Example controller template:
from aquilia.controller import Controller, route

class {{class_name}}Controller(Controller):
    prefix = "/{{module_name}}"
    
    @route.get("/")
    async def list(self, request):
        items = await {{class_name}}.objects.all()
        return self.json(items)
    
    {% if with_auth %}
    @route.post("/")
    @requires_auth
    async def create(self, request):
        ...
    {% endif %}`}</CodeBlock>
      </section>

      {/* Generator API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Programmatic API</h2>
        <CodeBlock language="python" filename="api.py">{`from aquilia.cli import Generator

gen = Generator(
    template_dir="artifacts/",
    output_dir="modules/",
)

# Generate a module programmatically
gen.generate("module", context={
    "module_name": "billing",
    "class_name": "Billing",
    "with_models": True,
    "with_auth": True,
    "fields": [
        {"name": "amount", "type": "DecimalField"},
        {"name": "currency", "type": "CharField"},
    ],
})`}</CodeBlock>
      </section>
    </div>
  )
}
