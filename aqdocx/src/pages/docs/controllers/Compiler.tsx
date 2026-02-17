import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Wrench } from 'lucide-react'

export function ControllersCompiler() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Wrench className="w-4 h-4" />Controllers</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Controller Compiler</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ControllerCompiler</code> runs at application startup, inspecting all registered controller classes, extracting route metadata from decorators, and building an optimized route tree for the Engine.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Compilation Process</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <ol className={`space-y-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            {[
              { step: 'Scan Controllers', desc: 'Iterates over all registered controller classes.' },
              { step: 'Extract Metadata', desc: 'For each method, reads __route_metadata__ attached by decorators (@Get, @Post, etc.).' },
              { step: 'Resolve Paths', desc: 'Combines controller prefix with method path. E.g., prefix="/api/users" + path="/{id:int}" → "/api/users/{id:int}".' },
              { step: 'Parse Parameters', desc: 'Extracts path parameter names and type converters from path templates.' },
              { step: 'Build Route Tree', desc: 'Constructs a radix-tree (trie) with all compiled routes for O(log n) lookup.' },
              { step: 'Register Pipelines', desc: 'Merges class-level and method-level pipeline nodes for each route.' },
              { step: 'Generate OpenAPI', desc: 'Produces OpenAPI spec entries from metadata (summary, description, tags, response_model).' },
            ].map((s, i) => (
              <li key={i} className="flex gap-4">
                <span className="flex items-center justify-center w-7 h-7 shrink-0 rounded-full bg-aquilia-500 text-black font-bold text-xs">{i + 1}</span>
                <div>
                  <strong className={isDark ? 'text-white' : 'text-gray-900'}>{s.step}</strong>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{s.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Compiled Route Entry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each compiled route contains all the information the Engine needs to dispatch a request:
        </p>
        <CodeBlock language="python" filename="Compiled Route Structure">{`# Internal representation of a compiled route:
CompiledRoute = {
    "pattern": "/api/users/{id:int}",     # Full path pattern
    "http_method": "GET",                  # HTTP method
    "controller_class": UserController,    # Controller class ref
    "handler_name": "get_user",            # Method name
    "handler": <bound method>,             # Method reference
    "path_params": [                       # Extracted parameters
        {"name": "id", "type": int, "converter": int_converter}
    ],
    "pipeline": [AuthGuard()],             # Merged pipeline
    "metadata": {                          # OpenAPI metadata
        "summary": "Get User",
        "description": "Get a single user by ID.",
        "tags": ["Users"],
        "deprecated": False,
        "response_model": UserResponse,
        "status_code": 200,
    },
    "instantiation_mode": "per_request",   # From controller class
    "signature": <inspect.Signature>,      # Function signature
}`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Debug Output</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          In debug mode, the compiler logs all compiled routes at startup:
        </p>
        <CodeBlock language="text" filename="Startup Log">{`🦅 Aquilia v0.2.0 — Compiling routes...
  ├─ ProductController
  │  ├─ GET    /api/products/          → list_products
  │  ├─ GET    /api/products/{id:int}  → get_product
  │  ├─ POST   /api/products/          → create_product
  │  ├─ PUT    /api/products/{id:int}  → update_product
  │  └─ DELETE /api/products/{id:int}  → delete_product
  ├─ AuthController
  │  ├─ POST   /api/auth/login         → login
  │  ├─ POST   /api/auth/register      → register
  │  └─ POST   /api/auth/logout        → logout
  └─ 8 routes compiled in 0.003s`}</CodeBlock>
      </section>
    </div>
  )
}
